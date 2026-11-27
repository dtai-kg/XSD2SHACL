import xml.etree.ElementTree as ET
import os
import rdflib
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from pyshacl import validate
import argparse
from .utils import recursiceCheck, built_in_types
import time


class XSDtoSHACL:
    def __init__(self):
        """
        Initialize the XSDtoSHACL class
        """
        self.shaclNS = rdflib.Namespace('http://www.w3.org/ns/shacl#')
        self.rdfSyntax = rdflib.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        self.xsdNS = rdflib.Namespace('http://www.w3.org/2001/XMLSchema#')
        self.xsdTargetNS = rdflib.Namespace('http://example.com/')
        self.NS = rdflib.Namespace('http://example.com/')
        self.type_list = built_in_types()
        self.xsdNSdict = dict()
        self.SHACL = Graph()
        self.shapes = []
        self.extensionShapes = []
        # maps the property shape of a simpleContent element's text to the element's node shape
        self.simpleContentPS = {}
        # shapes of elements declared with maxOccurs="unbounded" (no sh:maxCount may be added later)
        self.unboundedShapes = set()
        self.enumerationShapes = []
        # position of the declaration currently being translated inside its xs:sequence
        self.pending_order = None
        self.backUp = None
        self.processed_files = []
        # built-in type of the declaration whose attributes are being translated (typed fixed values)
        self.currentBuiltin = None
        # parent of every element of the (merged) schema tree
        self.parent_map = {}
        # occurrence (min, max, in a choice) of the model groups enclosing the current declaration
        self.occurrenceStack = []
        # loosest occurrence over all references of each named group
        self.groupMultipliers = {}

    def isSimpleComplex(self,xsd_element,xsd_type=None):
        """A function to determine whether the type of element is SimpleType or ComplexType"""
        if xsd_type == None:
            xsd_type = xsd_element.get("type")
        if xsd_type == None:
            for child in xsd_element.findall("./"):
                if "complexType" in child.tag:
                    if child.attrib.get("mixed") == "true":
                        return "mixed"
                    for sub_child in child:
                        if "simpleContent" in sub_child.tag:
                            return "simpleContent"
                    return 1
                elif "simpleType" in child.tag:
                    return 0
            return 0
        # elif "xs" in xsd_type or "xsd" in xsd_type or xsd_type in self.type_list:
        elif xsd_type.split(":")[-1] in self.type_list:
            return 0 #built-in type
        else:
            child = self.root.find(f".//*[@name='{xsd_type}']",self.xsdNSdict)
            if "complexType" in child.tag:
                if child.attrib.get("mixed") == "true":
                    return "mixed"
                for sub_child in child:
                    if "simpleContent" in sub_child.tag:
                        return "simpleContent"
                return 1
            elif "simpleType" in child.tag:
                return 0
        return None

    def parentShape(self):
        """The shape to which a child declaration is attached: the top of the shape stack,
        except that the property shape of a simpleContent element's text resolves to the
        element's node shape"""
        top = self.shapes[-1]
        return self.simpleContentPS.get(top, top)

    def parentOf(self, element):
        """The parent element in the schema tree"""
        parent = self.parent_map.get(element)
        if parent is None:
            parent = self.find_parent(element, self.root)
        return parent

    def occurs(self, xsd_element):
        """(minOccurs, maxOccurs) of a particle; maxOccurs None means unbounded"""
        min_occurs = int(xsd_element.get("minOccurs", "1"))
        max_occurs = xsd_element.get("maxOccurs", "1")
        return min_occurs, (None if max_occurs == "unbounded" else int(max_occurs))

    @staticmethod
    def multiplyOccurrence(min_occurs, max_occurs, factor_min, factor_max, in_choice=False):
        """Occurrence of a particle inside a model group that occurs (factor_min, factor_max)
        times: the lower bounds multiply (zero in a choice), the upper bounds multiply
        (unbounded if either is)"""
        min_occurs = 0 if (in_choice or factor_min == 0) else min_occurs * factor_min
        max_occurs = None if (max_occurs is None or factor_max is None) else max_occurs * factor_max
        return min_occurs, max_occurs

    def effectiveOccurrence(self, min_occurs, max_occurs):
        """Occurrence of a particle relative to its enclosing element, through the model groups
        on the occurrence stack"""
        for factor_min, factor_max, in_choice in self.occurrenceStack:
            min_occurs, max_occurs = self.multiplyOccurrence(min_occurs, max_occurs, factor_min, factor_max, in_choice)
        return min_occurs, max_occurs

    def elementCardinality(self, xsd_element):
        """Effective (minCount, maxCount) of an element declaration or reference"""
        return self.effectiveOccurrence(*self.occurs(xsd_element))

    MODEL_GROUPS = ("sequence", "choice", "all")

    def computeGroupMultipliers(self):
        """For every named group, the loosest occurrence over all its references (minimum of the
        lower bounds, maximum of the upper bounds, unbounded if any is), each reference counted
        with the model groups enclosing it and the multiplier of the group definition it is in"""
        references = {}
        for element in self.root.iter():
            if element.tag.split("}")[-1] == "group" and element.get("ref"):
                references.setdefault(self.localName(element.get("ref")), []).append(element)
        memo = {}

        def site_occurrence(reference, visiting):
            min_occurs, max_occurs = self.occurs(reference)
            node = self.parentOf(reference)
            while node is not None:
                tag = node.tag.split("}")[-1]
                if tag in self.MODEL_GROUPS:
                    factor_min, factor_max = self.occurs(node)
                    min_occurs, max_occurs = self.multiplyOccurrence(min_occurs, max_occurs, factor_min, factor_max, tag == "choice")
                elif tag == "group" and (node.get("name") or node.get("id")):
                    factor_min, factor_max = multiplier(node.get("name") or node.get("id"), visiting)
                    return self.multiplyOccurrence(min_occurs, max_occurs, factor_min, factor_max)
                elif tag in ("element", "complexType", "schema"):
                    break
                node = self.parentOf(node)
            return min_occurs, max_occurs

        def multiplier(name, visiting):
            if name in memo:
                return memo[name]
            if name in visiting:
                return 0, None  # recursive group references: no bound
            sites = references.get(name, [])
            if not sites:
                memo[name] = (1, 1)
                return memo[name]
            occurrences = [site_occurrence(site, visiting | {name}) for site in sites]
            min_occurs = min(o[0] for o in occurrences)
            max_occurs = None if any(o[1] is None for o in occurrences) else max(o[1] for o in occurrences)
            memo[name] = (min_occurs, max_occurs)
            return memo[name]

        self.groupMultipliers = {name: multiplier(name, frozenset()) for name in references}

    def find_parent(self, element, parent):
        for child in parent:
            if child is element:
                return parent
            if len(child) > 0:
                result = self.find_parent(element, child)
                if result is not None:
                    return result
        return None

    def transRestriction(self,tag,value,subject=None):
        
        if subject == None:
            subject = self.shapes[-1]

        if "type" in tag or "restriction" in tag:
            if ((":" in value) and (value.split(":")[1] in self.type_list)):
                p = self.shaclNS.datatype
                o = self.xsdNS[value.split(":")[1]]
                self.SHACL.add((subject,p,o))
            elif value in self.type_list:
                p = self.shaclNS.datatype
                o = self.xsdNS[value]
                self.SHACL.add((subject,p,o))

        elif "default" in tag:
            p = self.shaclNS.defaultValue
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "fixed" in tag:
            p = self.shaclNS["in"]
            o = self.typedLiteral(value, self.currentBuiltin)
            bn = BNode()
            self.SHACL.add((subject,p,bn))
            self.SHACL.add((bn,RDF.first,o))
            self.SHACL.add((bn,RDF.rest,RDF.nil))

        elif "pattern" in tag:
            # an XSD pattern matches the whole value, sh:pattern only part of it
            p = self.shaclNS.pattern
            o = Literal(self.anchorPattern(value))
            self.SHACL.add((subject,p,o))

        elif "maxExclusive" in tag:
            p = self.shaclNS.maxExclusive
            o = self.boundLiteral(value)
            self.SHACL.add((subject,p,o))

        elif "minExclusive" in tag:
            p = self.shaclNS.minExclusive
            o = self.boundLiteral(value)
            self.SHACL.add((subject,p,o))
  
        elif "maxInclusive" in tag:
            p = self.shaclNS.maxInclusive
            o = self.boundLiteral(value)
            self.SHACL.add((subject,p,o))

        elif "minInclusive" in tag:
            p = self.shaclNS.minInclusive
            o = self.boundLiteral(value)
            self.SHACL.add((subject,p,o))

        elif "length" in tag:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            p = self.shaclNS.maxLength
            o = rdflib.Literal(int(value))
            self.SHACL.add((subject,p,o))

        elif "minLength" in tag:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))

        elif "maxLength" in tag:        
            p = self.shaclNS.maxLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
 
    # built-in types derived from xs:string (no ordered value space: bounds are plain literals)
    STRING_TYPES = {'string', 'normalizedString', 'token', 'language', 'Name', 'NCName', 'NMTOKEN', 'NMTOKENS',
                    'ID', 'IDREF', 'IDREFS', 'ENTITY', 'ENTITIES'}

    def localName(self, type_name):
        return type_name.split(":")[-1] if type_name else None

    def findSimpleType(self, type_name):
        """The global xs:simpleType declaration with the given (possibly prefixed) name"""
        name = self.localName(type_name)
        if name is None:
            return None
        return self.root.find(f'.//{{http://www.w3.org/2001/XMLSchema}}simpleType[@name="{name}"]')

    def simpleTypeChain(self, base, inline=None):
        """Follow the restriction chain of a simple type upwards. Returns the restriction
        elements of the user-defined base types (nearest first) and the name of the built-in
        type at the top of the chain (None for lists, unions and unknown types)."""
        chain, seen = [], set()
        restriction = inline
        while True:
            if restriction is None:
                name = self.localName(base)
                if name is None:
                    return chain, None
                if name in self.type_list:
                    return chain, name
                if name in seen:
                    return chain, None
                seen.add(name)
                simple_type = self.findSimpleType(name)
                if simple_type is None:
                    return chain, None
                restriction = simple_type.find("{http://www.w3.org/2001/XMLSchema}restriction")
                if restriction is None:
                    return chain, None  # list or union
                chain.append(restriction)
            base = restriction.get("base")
            if base is None:
                # anonymous base type inside the restriction
                nested = restriction.find("{http://www.w3.org/2001/XMLSchema}simpleType/{http://www.w3.org/2001/XMLSchema}restriction")
                if nested is None:
                    return chain, None
                chain.append(nested)
                restriction = nested
                continue
            restriction = None

    def builtinType(self, type_name):
        """The built-in type a (possibly user-defined) simple type derives from"""
        return self.simpleTypeChain(type_name)[1]

    def builtinOfRestriction(self, restriction):
        """The built-in type at the top of the chain starting at a restriction element"""
        return self.simpleTypeChain(restriction.get("base"), inline=restriction)[1]

    def builtinOfDeclaration(self, xsd_element):
        """The built-in type of the values of an element or attribute declaration: from its
        type attribute or from its anonymous simple type"""
        if xsd_element.get("type"):
            return self.builtinType(xsd_element.get("type"))
        restriction = xsd_element.find("{http://www.w3.org/2001/XMLSchema}simpleType/{http://www.w3.org/2001/XMLSchema}restriction")
        if restriction is not None:
            return self.builtinOfRestriction(restriction)
        return None

    def typedLiteral(self, value, builtin):
        """A literal typed with the built-in type its value derives from, i.e. the datatype the
        declaration's sh:datatype names (xsd:token, xsd:NMTOKEN, ... included); xsd:string
        gives a plain literal (the lexical form alone, as RDF mappings produce it), unknown
        types plain literals"""
        if builtin is None or builtin == "string":
            return Literal(value)
        return Literal(value, datatype=self.xsdNS[builtin])

    def boundLiteral(self, value):
        """A value-range bound: an integer literal when the value is an integer, otherwise a
        literal typed with the built-in type of the restriction"""
        try:
            return Literal(int(value))
        except ValueError:
            return self.typedLiteral(value, self.currentBuiltin) if self.currentBuiltin not in self.STRING_TYPES else Literal(value)

    def anchorPattern(self, value):
        """Regular expression of an xs:pattern facet anchored at both ends"""
        return "^(" + value + ")$"

    def patternValues(self, restriction):
        """The values of the xs:pattern facets of a restriction"""
        return [c.get("value") for c in restriction.findall("./") if c.tag.split("}")[-1] == "pattern" and c.get("value") is not None]

    def transPatterns(self, restriction, chain, subject=None):
        """Several patterns of one restriction are alternatives: they become one anchored
        sh:pattern. Patterns inherited from user-defined base types apply in addition, so the
        patterns of the different derivation steps are combined with sh:and"""
        if subject is None:
            subject = self.shapes[-1]
        levels = [self.patternValues(r) for r in [restriction] + chain]
        levels = [self.anchorPattern("|".join(values)) for values in levels if values]
        if len(levels) == 1:
            self.SHACL.add((subject, self.shaclNS.pattern, Literal(levels[0])))
        elif levels:
            members = []
            for level in levels:
                member = BNode()
                self.SHACL.add((member, self.shaclNS.pattern, Literal(level)))
                members.append(member)
            self.addList(subject, self.shaclNS["and"], members)

    def addList(self, subject, predicate, members):
        """Attach an RDF list of the given members to the subject"""
        current_BN = BNode()
        self.SHACL.add((subject, predicate, current_BN))
        for index, member in enumerate(members):
            self.SHACL.add((current_BN, RDF.first, member))
            if index == len(members) - 1:
                self.SHACL.add((current_BN, RDF.rest, RDF.nil))
            else:
                next_BN = BNode()
                self.SHACL.add((current_BN, RDF.rest, next_BN))
                current_BN = next_BN

    # facets translated per restriction element rather than per facet child
    SEPARATE_FACETS = {"pattern", "enumeration", "annotation", "simpleType"}

    def transRestrictionElement(self, restriction):
        """Translate a restriction: the built-in type at the top of its derivation chain, the
        facets inherited from user-defined base types (the most derived value of each facet
        wins; the own facets are translated afterwards from the child elements), inherited
        enumerations when the restriction has none, and the patterns of all steps"""
        subject = self.shapes[-1]
        parent = self.parentOf(restriction)
        if parent is not None and parent.tag.split("}")[-1] == "complexContent":
            # a restriction of a complex type keeps the attributes of its base type: refer to the
            # base type's node shape, as for an extension
            base = self.localName(restriction.get("base"))
            if base is not None and base not in self.type_list:
                self.SHACL.add((subject, self.shaclNS.node, self.NS[f'NodeShape/{base}']))
            return
        chain, builtin = self.simpleTypeChain(None, inline=restriction)
        self.currentBuiltin = builtin
        if builtin is not None:
            self.SHACL.add((subject, self.shaclNS.datatype, self.xsdNS[builtin]))
        own = {c.tag.split("}")[-1] for c in restriction.findall("./")}
        for level in chain:
            for facet in level.findall("./"):
                name = facet.tag.split("}")[-1]
                if name in self.SEPARATE_FACETS or name in own or facet.get("value") is None:
                    continue
                own.add(name)
                self.transRestriction(name, facet.get("value"), subject)
        if "enumeration" not in own:
            for level in chain:
                values = [e.get("value") for e in level.findall("./") if e.tag.split("}")[-1] == "enumeration" and e.get("value")]
                if values:
                    self.addEnumeration(subject, values, builtin)
                    break
        self.transPatterns(restriction, chain, subject)

    def transAnnotation(self,xsd_element,subject):
        for child in xsd_element.findall("./"):
            tag = child.tag
            if "annotation" in tag:
                for sub_child in child.findall("./"):
                    tag = sub_child.tag
                    if "appinfo" in tag:
                        p = self.shaclNS.description
                        o = Literal(sub_child.text)
                        self.SHACL.add((subject,p,o))
                    elif "documentation" in tag:
                        p = self.shaclNS.description
                        o = Literal(sub_child.text)
                        self.SHACL.add((subject,p,o))

    def transEleSimple(self,xsd_element):
        """A function to translate XSD element with simple type and attribute to SHACL property shape"""
        element_name = xsd_element.get("name")

        if "attribute" in xsd_element.tag:
            subject = self.NS[f'PropertyShape/@{element_name}']
        else:
            subject = self.NS[f'PropertyShape/{element_name}']

        if self.shapes != []:
            parent = self.parentShape()
            if "NodeShape" in str(parent):
                pre_subject_path = parent.split("NodeShape/")[1]
            elif "PropertyShape" in str(parent):
                pre_subject_path = parent.split("PropertyShape/")[1]
            if "attribute" in xsd_element.tag:
                subject = self.NS[f'PropertyShape/{pre_subject_path}/@{element_name}']
            else:
                subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
            self.SHACL.add((parent,self.shaclNS.property,subject))
        
        self.transAnnotation(xsd_element,subject)
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        # self.SHACL.add((subject,self.shaclNS.targetSubjectsOf,self.xsdTargetNS[element_name]))
        if "attribute" not in xsd_element.tag:
            # a global element declaration has no occurrence of its own: the cardinality is
            # given where the element is referenced (addReferencePropertyShape)
            if self.shapes[:-1] != []:
                self.addCardinality(subject, *self.elementCardinality(xsd_element))

        else:
            # an attribute occurs at most once; "use" defaults to optional
            use = xsd_element.get("use", "optional")
            if use == "required":
                self.SHACL.add((subject,self.shaclNS.minCount,Literal(1)))
                self.SHACL.add((subject,self.shaclNS.maxCount,Literal(1)))
            elif use == "prohibited":
                self.SHACL.add((subject,self.shaclNS.maxCount,Literal(0)))
            else:
                self.SHACL.add((subject,self.shaclNS.maxCount,Literal(1)))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        if self.pending_order is not None and "attribute" not in xsd_element.tag:
            self.SHACL.add((subject,self.shaclNS.order,Literal(self.pending_order)))

        self.currentBuiltin = self.builtinOfDeclaration(xsd_element)
        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])
        self.currentBuiltin = None

        element_type = xsd_element.get("type") 
        # child type, built-in type or xsd simple type
        if element_type == None:
            return xsd_element
        elif (":" in element_type) or (element_type.split(":")[-1] in self.type_list): #TODO: check if this is a built-in type
            # already translated
            return xsd_element 
        else:
            next_node = self.root.find(f'.//{{http://www.w3.org/2001/XMLSchema}}simpleType[@name="{element_type}"]')
            # redirect current process to the next root (simple type)
            return next_node 
            
        return xsd_element

    def transEleComplex(self,xsd_element):
        """A function to translate XSD element with complex type to SHACL node shape"""
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        ps_subject = self.NS[f'PropertyShape/{element_name}']

        if self.shapes != []:
            parent = self.parentShape()
            if "NodeShape" in str(parent):
                pre_subject_path = parent.split("NodeShape/")[1]
            elif "PropertyShape" in str(parent):
                pre_subject_path = parent.split("PropertyShape/")[1]
            subject = self.NS[f'NodeShape/{pre_subject_path}/{element_name}']
            ps_subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
            # A nested complex element is a separate resource: link the parent shape to the
            # child node shape through a property shape that carries the path and cardinality
            self.addLinkingPropertyShape(xsd_element, parent, ps_subject, subject)

        self.transAnnotation(xsd_element,subject)
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        self.SHACL.add((subject,self.shaclNS.nodeKind,self.shaclNS.IRI))
        self.SHACL.add((subject,self.shaclNS.targetClass,self.xsdTargetNS[element_name]))

        for name in xsd_element.attrib:
            if "type" not in name:
                self.transRestriction(name, xsd_element.attrib[name], ps_subject)

        element_type = xsd_element.get("type")
        if element_type is not None:
            # The element refers to a named complex type that is translated separately
            self.SHACL.add((subject,self.shaclNS.node,self.NS[f'NodeShape/{element_type}']))

        return xsd_element

    def addCardinality(self, subject, min_occurs, max_occurs):
        """Add sh:minCount / sh:maxCount for an element declaration (max_occurs None: unbounded).
        The same element name can be declared several times under one parent (same shape IRI):
        the bounds are then merged into the loosest ones (smallest minCount, largest maxCount,
        none if any is unbounded)"""
        existing_min = self.SHACL.value(subject, self.shaclNS.minCount)
        if existing_min is not None:
            min_occurs = min(min_occurs, int(existing_min))
            self.SHACL.remove((subject, self.shaclNS.minCount, None))
        self.SHACL.add((subject, self.shaclNS.minCount, Literal(min_occurs)))
        if max_occurs is None or subject in self.unboundedShapes:
            self.unboundedShapes.add(subject)
            self.SHACL.remove((subject, self.shaclNS.maxCount, None))
            return
        existing_max = self.SHACL.value(subject, self.shaclNS.maxCount)
        if existing_max is not None:
            max_occurs = max(max_occurs, int(existing_max))
            self.SHACL.remove((subject, self.shaclNS.maxCount, None))
        self.SHACL.add((subject, self.shaclNS.maxCount, Literal(max_occurs)))

    def addLinkingPropertyShape(self, xsd_element, parent, ps_subject, subject, element_name=None):
        """Link the parent shape to the node shape of a nested complex element (or of a referenced
        global complex element) through a property shape holding the element's path, cardinality
        and sh:node"""
        if element_name is None:
            element_name = xsd_element.get("name")
        self.SHACL.add((ps_subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((ps_subject,self.shaclNS.name,Literal(element_name)))
        self.SHACL.add((ps_subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        self.SHACL.add((ps_subject,self.shaclNS.node,subject))
        self.addCardinality(ps_subject, *self.elementCardinality(xsd_element))
        if self.pending_order is not None:
            self.SHACL.add((ps_subject,self.shaclNS.order,Literal(self.pending_order)))
        self.SHACL.add((parent,self.shaclNS.property,ps_subject))

    def addReferencePropertyShape(self, xsd_element, parent, element_name):
        """A reference to a global simple element reuses the global property shape for the
        constraints on the value. The occurrence of the reference is given by a property shape
        of the parent, named like the shape of a local element, that only holds the element's
        path, name, cardinality and, in a sequence, order"""
        if "NodeShape" in str(parent):
            pre_subject_path = parent.split("NodeShape/")[1]
        else:
            pre_subject_path = parent.split("PropertyShape/")[1]
        ps_subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
        self.SHACL.add((ps_subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((ps_subject,self.shaclNS.name,Literal(element_name)))
        self.SHACL.add((ps_subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        self.addCardinality(ps_subject, *self.elementCardinality(xsd_element))
        if self.pending_order is not None:
            self.SHACL.add((ps_subject,self.shaclNS.order,Literal(self.pending_order)))
        self.SHACL.add((parent,self.shaclNS.property,ps_subject))

    def transEleComplexSimpleContent(self,xsd_element):
        """A function to translate XSD element with complex type simple Content to SHACL node shape"""
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        ps_subject = self.NS[f'PropertyShape/{element_name}']

        if self.shapes != []:
            parent = self.parentShape()
            if "NodeShape" in str(parent):
                pre_subject_path = parent.split("NodeShape/")[1]
            elif "PropertyShape" in str(parent):
                pre_subject_path = parent.split("PropertyShape/")[1]
            subject = self.NS[f'NodeShape/{pre_subject_path}/{element_name}']
            link_subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
            # the property shape describing the text content hangs below the element's own shape
            ps_subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}/{element_name}']
            self.addLinkingPropertyShape(xsd_element, parent, link_subject, subject)
        else:
            ps_subject = self.NS[f'PropertyShape/{element_name}/{element_name}']

        self.transAnnotation(xsd_element,subject)
        # Two shapes are pushed: the node shape of the element and the property shape of its
        # simple content, so that restrictions of the content are attached to the latter.
        # translate() pops both after the element has been processed.
        self.shapes.append(subject)
        self.shapes.append(ps_subject)
        self.simpleContentPS[ps_subject] = subject
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        self.SHACL.add((subject,self.shaclNS.nodeKind,self.shaclNS.IRI))
        self.SHACL.add((subject,self.shaclNS.targetClass,self.xsdTargetNS[element_name]))

        # Property shape for the simple content (text) of the element
        self.SHACL.add((subject,self.shaclNS.property,ps_subject))
        self.SHACL.add((ps_subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((ps_subject,self.shaclNS.name,Literal(element_name)))
        self.SHACL.add((ps_subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        self.SHACL.add((ps_subject,self.shaclNS.minCount,Literal(1)))
        self.SHACL.add((ps_subject,self.shaclNS.maxCount,Literal(1)))

        self.currentBuiltin = self.simpleContentBuiltin(xsd_element)
        for name in xsd_element.attrib:
            if "type" not in name:
                self.transRestriction(name, xsd_element.attrib[name], ps_subject)
        self.currentBuiltin = None
        element_type = xsd_element.get("type")
        if element_type == None:
            for i in xsd_element.findall(f".//{{http://www.w3.org/2001/XMLSchema}}complexType/{{http://www.w3.org/2001/XMLSchema}}simpleContent/{{http://www.w3.org/2001/XMLSchema}}extension"):
                type_name = i.get("base")
                if type_name.split(":")[-1] in self.type_list:
                    self.SHACL.add((ps_subject,self.shaclNS.datatype,self.xsdNS[type_name.split(":")[1]]))
                else:
                    extension_node = self.root.find(f".//*[@name='{type_name}']")
                    extension_node_type = self.isSimpleComplex(extension_node)
                    if extension_node_type == 0:
                        # redirect current process to the base simple type
                        return extension_node
                    elif extension_node_type == 1:
                        self.SHACL.add((ps_subject,self.shaclNS.node,self.NS[f'NodeShape/{type_name}']))
            return xsd_element
        else:
            self.SHACL.add((subject,self.shaclNS.node,self.NS[f'NodeShape/{element_type}'])) #Will be translated later
  
            for i in self.root.findall(f".//*[@name='{element_type}']/{{http://www.w3.org/2001/XMLSchema}}simpleContent/{{http://www.w3.org/2001/XMLSchema}}restriction"):
                type_name = i.get("base")
                if type_name.split(":")[-1] in self.type_list:
                    self.SHACL.add((ps_subject,self.shaclNS.datatype,self.xsdNS[type_name.split(":")[1]]))
            for i in self.root.findall(f".//*[@name='{element_type}']/{{http://www.w3.org/2001/XMLSchema}}simpleContent/{{http://www.w3.org/2001/XMLSchema}}extension"):
                type_name = i.get("base")
                if type_name.split(":")[-1] in self.type_list:
                    self.SHACL.add((ps_subject,self.shaclNS.datatype,self.xsdNS[type_name.split(":")[-1]]))
                else:
                    extension_node = self.root.find(f".//*[@name='{type_name}']")
                    extension_node_type = self.isSimpleComplex(extension_node)
                    if extension_node_type == 0:
                        next_node = extension_node
                        # redirect current process to the next root (simple type)
                        return next_node 
                    elif extension_node_type == 1:
                        self.SHACL.add((ps_subject,self.shaclNS.node,self.NS[f'NodeShape/{type_name}']))

            return xsd_element
        return xsd_element

    def simpleContentBuiltin(self, xsd_element):
        """The built-in type of the text of a simple-content element (from the base of its
        simpleContent extension or restriction, possibly through a named complex type)"""
        type_name = xsd_element.get("type")
        if type_name is None:
            scope = xsd_element
        else:
            scope = self.root.find(f".//*[@name='{type_name}']")
            if scope is None:
                return None
        for tag in ("extension", "restriction"):
            for node in scope.findall(f".//{{http://www.w3.org/2001/XMLSchema}}simpleContent/{{http://www.w3.org/2001/XMLSchema}}{tag}"):
                return self.builtinType(node.get("base"))
        return None

    def transComplexType(self,xsd_element):
        """A function to translate XSD complex type to SHACL node shape""" 
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        if self.shapes != []:
            parent = self.parentShape()
            if "NodeShape" in str(parent):
                pre_subject_path = parent.split("NodeShape/")[1]
            elif "PropertyShape" in str(parent):
                pre_subject_path = parent.split("PropertyShape/")[1]
            subject = self.NS[f'NodeShape/{pre_subject_path}/{element_name}']
            # To solve that it is the child node of any element
            self.SHACL.add((parent,self.shaclNS.node,subject))

        self.transAnnotation(xsd_element,subject)
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        # complex type does not have target, element can

        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])

        return xsd_element   

    def transGroup(self,xsd_element):
        """A function to translate XSD complex type to SHACL node shape""" 
        element_name = xsd_element.get("name")
        if element_name == None:
            element_name = xsd_element.get("id")
        subject = self.NS[f'NodeShape/{element_name}']
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        # complex type does not have target, element can

        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])

        return xsd_element    

    def transExtension(self,xsd_element):
        """A function to translate XSD extension"""
        element_name = xsd_element.get("base")
        # xsd_type = xsd_element.get("type")
        if element_name in self.extensionShapes:
            return xsd_element
        elif element_name.split(":")[-1] in self.type_list:
            # if "PropertyShape" in str(self.shapes[-1]):
            #     subject = self.shapes[-1]
            # elif "NodeShape" in str(self.shapes[-1]):
            #     subject = URIRef(str(self.shapes[-1]).replace("NodeShape","PropertyShape"))
            if "PropertyShape" in str(self.shapes[-1]):
                self.SHACL.add((self.shapes[-1],self.shaclNS.datatype,self.xsdNS[element_name.split(":")[1]]))
            return xsd_element
        else:
            self.extensionShapes.append(element_name)
            sub_node = self.root.find(f'.//*[@name="{element_name}"]',self.xsdNSdict)
            element_type = self.isSimpleComplex(sub_node, element_name)
            subject = self.shapes[-1]

            if element_type == 1:
                # complexType will be translated seperatly so we just need to add the node shape
                self.SHACL.add((subject,self.shaclNS.node,self.NS[f'NodeShape/{element_name}'])) 
                # self.extensionShape = False
                return xsd_element

            # elif element_type == 0:
            #     # simpleType will not be translated seperatly so we need to redirect it here
            #     next_node = sub_node
            #     self.SHACL.add((subject,self.shaclNS.property,self.NS[f'PropertyShape/{element_name}'])) 
            #     subject = self.NS[f'PropertyShape/{element_name}']
            #     self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
            #     self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
            #     self.SHACL.add((subject,self.shaclNS.path,self.xsdTargetNS[element_name]))

            #     self.shapes.append(subject)
            #     self.backUp = xsd_element
            #     # self.extensionShape = True
                
            #     # redirect current process to the next root (simple type)       
            #     return next_node 
        return xsd_element

 

    def transEnumeration(self, xsd_element):
        values = []
        subject = self.shapes[-1]
        parent_element = self.find_parent(xsd_element, self.root)

        if parent_element not in self.enumerationShapes:
            self.enumerationShapes.append(parent_element)
        else:
            return xsd_element

        for e in parent_element.findall('.//xs:enumeration',namespaces={"xs": "http://www.w3.org/2001/XMLSchema"}):
            if e.get("value"):
                values.append(e.get("value"))

        if values == []:
            return xsd_element
        else:
            # the values are typed with the built-in type the restriction derives from
            self.addEnumeration(subject, values, self.builtinOfRestriction(parent_element))
            return xsd_element

    def addEnumeration(self, subject, values, builtin):
        """sh:in with the enumeration values as literals typed by the built-in base type. A
        shape that already has sh:in (from a fixed value, which must be one of the
        enumeration values) keeps the stricter one"""
        if (subject, self.shaclNS["in"], None) in self.SHACL:
            return
        current_BN = BNode()
        self.SHACL.add((subject, self.shaclNS["in"], current_BN))
        for index in range(len(values))[0:-1]:
            self.SHACL.add((current_BN, RDF.first, self.typedLiteral(values[index], builtin)))
            next_BN = BNode()
            self.SHACL.add((current_BN, RDF.rest, next_BN))
            current_BN = next_BN
        self.SHACL.add((current_BN, RDF.first, self.typedLiteral(values[-1], builtin)))
        self.SHACL.add((current_BN, RDF.rest, RDF.nil))

    def transUnion(self, xsd_element):
        values = []
        subject = self.shapes[-1]

        if xsd_element.get("memberTypes") and len(xsd_element)==0 :
            memberTypes = xsd_element.get("memberTypes").split(" ")

            current_BN = BNode()
            self.SHACL.add((subject, self.shaclNS["or"], current_BN))

            for index in range(len(memberTypes)):
                memberType = memberTypes[index]
                if (":" in memberType) and (memberType.split(":")[-1] in self.type_list):
                    shape_BN = BNode()
                    self.SHACL.add((current_BN, RDF.first, shape_BN)) 
                    self.SHACL.add((shape_BN, self.shaclNS.datatype, self.xsdNS[memberType.split(":")[1]])) 
                    next_BN = BNode()
                    if index == len(memberTypes)-1:
                        self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                    else:   
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                    current_BN = next_BN
                else:
                    sub_node = self.root.find(f'.//*[@name="{memberType}"]',self.xsdNSdict)
                    element_type = self.isSimpleComplex(sub_node, memberType)
                    if element_type == 1:
                        self.SHACL.add((current_BN, RDF.first, self.NS[f'NodeShape/{memberType}'])) 
                        next_BN = BNode()
                        if index == len(memberTypes)-1:
                            self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                        else:   
                            self.SHACL.add((current_BN, RDF.rest, next_BN))
                        current_BN = next_BN
                    elif element_type == 0:
                        sub_BN = BNode()
                        self.SHACL.add((current_BN, RDF.first, sub_BN))
                        self.shapes.append(sub_BN)
                        self.translate(sub_node)
                        self.shapes.pop()
                        next_BN = BNode()
                        if index == len(memberTypes)-1:
                            self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                        else:   
                            self.SHACL.add((current_BN, RDF.rest, next_BN))
                        current_BN = next_BN
        elif xsd_element.get("memberTypes") and len(xsd_element)>0 :
            memberTypes = xsd_element.get("memberTypes").split(" ")

            current_BN = BNode()
            self.SHACL.add((subject, self.shaclNS["or"], current_BN))

            for index in range(len(memberTypes)):
                memberType = memberTypes[index]
                if (":" in memberType) and (memberType.split(":")[-1] in self.type_list):
                    shape_BN = BNode()
                    self.SHACL.add((current_BN, RDF.first, shape_BN)) 
                    self.SHACL.add((shape_BN, self.shaclNS.datatype, self.xsdNS[memberType.split(":")[1]])) 
                    next_BN = BNode()
                    if index == len(memberTypes)-1:
                        self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                    else:   
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                    current_BN = next_BN
                else:
                    sub_node = self.root.find(f'.//*[@name="{memberType}"]',self.xsdNSdict)
                    element_type = self.isSimpleComplex(sub_node, memberType)
                    if element_type == 1:
                        self.SHACL.add((current_BN, RDF.first, self.NS[f'NodeShape/{memberType}'])) 
                        next_BN = BNode()  
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                        current_BN = next_BN
                    elif element_type == 0:
                        sub_BN = BNode()
                        self.SHACL.add((current_BN, RDF.first, sub_BN))
                        self.shapes.append(sub_BN)
                        self.translate(sub_node)
                        self.shapes.pop()
                        next_BN = BNode()
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                        current_BN = next_BN         
            index = 0
            for sub_node in xsd_element:
                index += 1
                element_type = self.isSimpleComplex(sub_node)
                if element_type == 1:
                    self.SHACL.add((current_BN, RDF.first, self.NS[f'NodeShape/{memberType}'])) 
                    next_BN = BNode()
                    if index == len(memberTypes)-1:
                        self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                    else:   
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                    current_BN = next_BN
                elif element_type == 0:
                    sub_BN = BNode()
                    self.SHACL.add((current_BN, RDF.first, sub_BN))
                    self.shapes.append(sub_BN)
                    self.translate(sub_node)
                    self.shapes.pop()
                    next_BN = BNode()
                    if index == len(xsd_element):
                        self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                    else:   
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                    current_BN = next_BN         
        else:
            current_BN = BNode()
            self.SHACL.add((subject, self.shaclNS["or"], current_BN))
            index = 0
            for sub_node in xsd_element:
                index += 1
                element_type = self.isSimpleComplex(sub_node)
                if element_type == 1:
                    self.SHACL.add((current_BN, RDF.first, self.NS[f'NodeShape/{memberType}'])) 
                    next_BN = BNode()
                    if index == len(memberTypes)-1:
                        self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                    else:   
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                    current_BN = next_BN
                elif element_type == 0:
                    sub_BN = BNode()
                    self.SHACL.add((current_BN, RDF.first, sub_BN))
                    self.shapes.append(sub_BN)
                    self.translate(sub_node)
                    self.shapes.pop()
                    next_BN = BNode()
                    if index == len(xsd_element):
                        self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
                    else:   
                        self.SHACL.add((current_BN, RDF.rest, next_BN))
                    current_BN = next_BN         

    PARTICLES = ("element", "sequence", "choice", "all", "group", "any")

    class Unexpressible(Exception):
        """A choice whose candidates include xs:any cannot be expressed"""

    def isNestedInChoice(self, particle):
        """True if the particle is inside another choice of the same content model"""
        node = self.parentOf(particle)
        while node is not None:
            tag = node.tag.split("}")[-1]
            if tag == "choice":
                return True
            if tag in ("element", "complexType", "schema") or (tag == "group" and not node.get("ref")):
                return False
            node = self.parentOf(node)
        return False

    def groupContent(self, reference, visiting):
        """The model group of a referenced group definition (None if recursive or missing)"""
        name = self.localName(reference.get("ref"))
        if name in visiting:
            return None, visiting
        definition = self.root.find(f'.//{{http://www.w3.org/2001/XMLSchema}}group[@name="{name}"]')
        if definition is None:
            return None, visiting
        for child in definition.findall("./"):
            if child.tag.split("}")[-1] in self.MODEL_GROUPS:
                return child, visiting | {name}
        return None, visiting

    def particleName(self, particle):
        return particle.get("name") or self.localName(particle.get("ref"))

    def choiceElements(self, particle, visiting=frozenset()):
        """Names of all elements that can appear through a particle (xs:any raises)"""
        tag = particle.tag.split("}")[-1]
        if tag == "element":
            name = self.particleName(particle)
            return [name] if name else []
        if tag == "any":
            raise self.Unexpressible()
        if tag == "group" and particle.get("ref"):
            content, visiting = self.groupContent(particle, visiting)
            return self.choiceElements(content, visiting) if content is not None else []
        names = []
        if tag in self.MODEL_GROUPS:
            for child in particle.findall("./"):
                for name in self.choiceElements(child, visiting):
                    if name not in names:
                        names.append(name)
        return names

    def selectedShape(self, particle, visiting=frozenset()):
        """The shape satisfied when a candidate of a choice is the chosen one, and whether the
        candidate can be chosen without any element appearing. An element candidate requires
        its path at least max(1, minOccurs) times; a sequence or all candidate requires its
        mandatory members (sh:and), or, if it has none, at least one of its members (sh:or);
        a nested choice is translated recursively; a group reference stands for its content."""
        tag = particle.tag.split("}")[-1]
        if tag == "element":
            name = self.particleName(particle)
            if name is None:
                return None, False
            min_occurs, _ = self.occurs(particle)
            shape = BNode()
            self.SHACL.add((shape, self.shaclNS.path, self.xsdTargetNS[name]))
            self.SHACL.add((shape, self.shaclNS.minCount, Literal(max(1, min_occurs))))
            return shape, min_occurs == 0
        if tag == "any":
            raise self.Unexpressible()
        if tag == "group" and particle.get("ref"):
            content, visiting = self.groupContent(particle, visiting)
            if content is None:
                return None, True
            shape, empty = self.selectedShape(content, visiting)
            return shape, empty or self.occurs(particle)[0] == 0
        if tag == "choice":
            shapes, empties = [], []
            for child in particle.findall("./"):
                if child.tag.split("}")[-1] not in self.PARTICLES:
                    continue
                shape, empty = self.selectedShape(child, visiting)
                if shape is not None:
                    shapes.append(shape)
                    empties.append(empty or self.occurs(child)[0] == 0)
            if not shapes:
                return None, True
            min_occurs, max_occurs = self.occurs(particle)
            if len(shapes) == 1:
                shape = shapes[0]
            else:
                shape = BNode()
                combination = self.shaclNS.xone if (max_occurs is not None and max_occurs <= 1) else self.shaclNS["or"]
                self.addList(shape, combination, shapes)
            return shape, min_occurs == 0 or any(empties)
        if tag in ("sequence", "all"):
            members = [child for child in particle.findall("./") if child.tag.split("}")[-1] in self.PARTICLES]
            if any(child.tag.split("}")[-1] == "any" for child in members):
                raise self.Unexpressible()
            mandatory = [child for child in members if self.occurs(child)[0] >= 1]
            chosen = mandatory if mandatory else members
            shapes, empties = [], []
            for child in chosen:
                shape, empty = self.selectedShape(child, visiting)
                if shape is not None:
                    shapes.append(shape)
                    empties.append(empty)
            if not shapes:
                return None, True
            if len(shapes) == 1:
                shape = shapes[0]
            else:
                shape = BNode()
                self.addList(shape, self.shaclNS["and"] if mandatory else self.shaclNS["or"], shapes)
            return shape, (all(empties) if mandatory else True)
        return None, False

    def noneShape(self, choice):
        """The shape satisfied when no element of the choice appears"""
        members = []
        for name in self.choiceElements(choice):
            member = BNode()
            self.SHACL.add((member, self.shaclNS.path, self.xsdTargetNS[name]))
            self.SHACL.add((member, self.shaclNS.maxCount, Literal(0)))
            members.append(member)
        if not members:
            return None
        if len(members) == 1:
            return members[0]
        shape = BNode()
        self.addList(shape, self.shaclNS["and"], members)
        return shape

    def transChoice(self, xsd_element):
        """Combination of the candidates of a choice (their cardinalities are on their own
        property shapes, with a lower bound of 0). A choice that occurs at most once: sh:xone of
        the selected shapes, plus the shape of "no candidate" when the choice is optional or a
        candidate can be empty. A repeatable choice that must occur: sh:or of the selected
        shapes (nothing when a candidate can be empty, as that would be stricter than the XSD)."""
        if self.isNestedInChoice(xsd_element):
            return  # part of the combination of the enclosing choice
        subject = self.parentShape()
        min_occurs, max_occurs = self.effectiveOccurrence(*self.occurs(xsd_element))
        try:
            self.choiceElements(xsd_element)  # raises before any shape is created if xs:any is involved
            shapes, empties = [], []
            for child in xsd_element.findall("./"):
                if child.tag.split("}")[-1] not in self.PARTICLES:
                    continue
                shape, empty = self.selectedShape(child)
                if shape is not None:
                    shapes.append(shape)
                    empties.append(empty or self.occurs(child)[0] == 0)
        except self.Unexpressible:
            return
        if not shapes:
            return
        if max_occurs is not None and max_occurs <= 1:
            if min_occurs == 0 or any(empties):
                none = self.noneShape(xsd_element)
                if none is not None:
                    shapes.append(none)
            self.addList(subject, self.shaclNS.xone, shapes)
        elif min_occurs >= 1 and not any(empties):
            self.addList(subject, self.shaclNS["or"], shapes)
        else:
            self.discardShapes(shapes)

    def discardShapes(self, nodes):
        """Remove blank shapes (and the lists and member shapes below them) that are not used"""
        for node in nodes:
            if not isinstance(node, BNode):
                continue
            for _, p, o in list(self.SHACL.triples((node, None, None))):
                self.SHACL.remove((node, p, o))
                if isinstance(o, BNode):
                    self.discardShapes([o])

    def translate(self,current_node):
        """A function to iteratively translate XSD to SHACL"""
        in_sequence = "sequence" in current_node.tag
        position = 0
        for child in current_node.findall("*"):
            # Translate current node and associate this SHACL term/shape with its corresponding SHACL shape
            tag = child.tag
            next_node = child
            pops = 1
            # sh:order: position of an element declaration or reference among the elements of the enclosing xs:sequence
            self.pending_order = None
            if in_sequence and ("element" in tag) and (child.get("name") or child.get("ref")):
                self.pending_order = position
                position += 1
            if ("element" in tag) or (("attribute" in tag) and ("attributeGroup" not in tag)):
                if child.get("ref"):
                    ref = child.get("ref")
                    if ":" in ref:
                        ref = ref.split(":")[-1]
                    ref_node = self.root.find(f".//*[@name='{ref}']")
                    if ref_node != None:
                        element_type = self.isSimpleComplex(ref_node)
                        if element_type == 0:
                            self.SHACL.add((self.parentShape(),self.shaclNS.property,self.NS[f'PropertyShape/{ref}']))
                            if "element" in tag:
                                self.addReferencePropertyShape(child, self.parentShape(), ref)
                        elif element_type in (1, "simpleContent", "mixed") and "element" in tag:
                            # a referenced global complex element is a nested resource: link it
                            # through a property shape with the cardinality of the reference
                            parent = self.parentShape()
                            if "NodeShape" in str(parent):
                                pre_subject_path = parent.split("NodeShape/")[1]
                            else:
                                pre_subject_path = parent.split("PropertyShape/")[1]
                            self.addLinkingPropertyShape(child, parent, self.NS[f'PropertyShape/{pre_subject_path}/{ref}'], self.NS[f'NodeShape/{ref}'], ref)
                else:
                    element_type = self.isSimpleComplex(child)
                    if element_type == 0:
                        next_node = self.transEleSimple(child)
                    elif element_type == 1:
                        next_node = self.transEleComplex(child)
                    elif element_type == "simpleContent" or element_type == "mixed":
                        next_node = self.transEleComplexSimpleContent(child)
                        pops = 2  # node shape and the property shape of the simple content
            elif ("simpleType" in tag) and (self.shapes == []):
                continue
            elif ("extension" in tag):
                next_node = self.transExtension(child)
            elif ("complexType" in tag) and (child.get("name")):
                next_node = self.transComplexType(child)
            elif ("attributeGroup" in tag):
                if child.get("ref"):
                    # next_node = self.root.find(f".//*[@name='{child.get('ref')}']")
                    self.SHACL.add((self.parentShape(),self.shaclNS.node,self.NS[f'NodeShape/{child.get("ref")}']))
                else:
                    next_node = self.transComplexType(child)
            elif ("group" in tag):
                ref = child.get("ref")
                if ref:
                    self.SHACL.add((self.parentShape(),self.shaclNS.node,self.NS[f'NodeShape/{self.localName(ref)}']))
                    # else:
                    #     next_node = self.root.find(f".//*[@id='{ref}']")
                    #     if next_node == None:
                    #         next_node = self.root.find(f".//*[@name='{ref}']")
                else:
                    next_node = self.transGroup(child)
            elif ("complexType" in tag) or ("simpleType" in tag): 
                #will be translated in the next iteration
                pass
            elif ("restriction" in tag):
                self.transRestrictionElement(child)
            elif ("enumeration" in tag):
                self.transEnumeration(child)
            elif ("sequence" in tag):
                pass
            elif ("choice" in tag):
                self.transChoice(child)
            elif ("all" in tag):
                pass
            elif ("union" in tag):
                # memberTypes = child.get("memberTypes").split(" ")
                self.transUnion(child)
                continue
            elif ("appinfo" in tag) or ("documentation" in tag) or ("annotation" in tag):
                continue
            elif ("pattern" in tag):
                continue  # the patterns of a restriction are translated together (transPatterns)
            else:
                value = child.get("value")
                self.transRestriction(tag,value)
            # Translate next node
            self.pending_order = None
            local_tag = tag.split("}")[-1]
            saved_stack = self.occurrenceStack
            if local_tag in self.MODEL_GROUPS:
                # the occurrence of a model group applies to the declarations inside it
                self.occurrenceStack = saved_stack + [self.occurs(child) + (local_tag == "choice",)]
            elif local_tag in ("element", "attribute", "complexType", "attributeGroup"):
                self.occurrenceStack = []  # a new content model starts
            elif local_tag == "group" and not child.get("ref"):
                # a group definition: the loosest occurrence of its references
                self.occurrenceStack = [self.groupMultipliers.get(child.get("name") or child.get("id"), (1, 1)) + (False,)]
            self.translate(next_node)
            self.occurrenceStack = saved_stack

            if (("element" in tag) and (child.get("name"))) or (("attribute" in tag) and ("attributeGroup" not in tag) and not child.get("ref")) or (("complexType" in tag) and (child.get("name"))) or (("attributeGroup" in tag) and (child.get("name"))) or (("group" in tag) and (child.get("name") or child.get("id"))):
                for _ in range(pops):
                    self.shapes.pop()
        if self.backUp != None:
            self.shapes.pop()
            temp = self.backUp
            self.backUp = None
            self.translate(temp)
            

    def writeShapeToFile(self, file_name):
        for prefix in self.xsdNSdict:
            self.SHACL.bind(prefix, self.xsdNSdict[prefix])
        self.SHACL.bind("ex", self.NS)

        self.SHACL.bind('sh', 'http://www.w3.org/ns/shacl#', False)
        # self.SHACL.bind(
        #     'rdfs', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')

        self.SHACL.serialize(destination=file_name, format='turtle')

    def parseXSD(self, ref_root):

        # Process xs:include
        for include_import_elem in ref_root.findall(".//xs:include", namespaces={"xs": "http://www.w3.org/2001/XMLSchema"}):
            self.root.remove(include_import_elem)
            included_imported_xsd_path = include_import_elem.get("schemaLocation")
            if included_imported_xsd_path and included_imported_xsd_path not in self.processed_files:
                try:
                    next_ref_root = ET.parse(os.path.join(self.BASE_PATH, included_imported_xsd_path)).getroot()
                    self.processed_files.append(included_imported_xsd_path)
                except:
                    print("Parse include error file:",included_imported_xsd_path)
                    self.processed_files.append(included_imported_xsd_path)
                    continue

                for child in next_ref_root.findall("./"):
                    if ("import" not in child.tag) or ("include" not in child.tag):
                        self.root.append(child)
                self.parseXSD(next_ref_root)

        # Process xs:import
        for include_import_elem in ref_root.findall(".//xs:import", namespaces={"xs": "http://www.w3.org/2001/XMLSchema"}):
            self.root.remove(include_import_elem)
            included_imported_xsd_path = include_import_elem.get("schemaLocation")
            if included_imported_xsd_path and included_imported_xsd_path not in self.processed_files:
                try:
                    next_ref_root = ET.parse(os.path.join(self.BASE_PATH, included_imported_xsd_path)).getroot()
                    self.processed_files.append(included_imported_xsd_path)
                except:
                    print("Parse error import file:",included_imported_xsd_path)
                    self.processed_files.append(included_imported_xsd_path)
                    continue

                for child in next_ref_root.findall("./"):
                    if ("import" not in child.tag) or ("include" not in child.tag):
                        self.root.append(child)
                self.parseXSD(next_ref_root)


    
    def evaluate_file(self, xsd_file, shacl_file=None):
        self.BASE_PATH = os.path.dirname(xsd_file)
        self.xsdTree = ET.parse(xsd_file)
        self.root = self.xsdTree.getroot()

        recursiceCheck(self.root)

        self.xsdNSdict = dict([node for (_, node) in ET.iterparse(xsd_file, events=['start-ns'])])

        # print("#########Start parsing XSD file")
        self.parseXSD(self.root)
        self.parent_map = {child: parent for parent in self.root.iter() for child in parent}
        self.computeGroupMultipliers()
        # tree = ET.ElementTree(self.root)
        # tree.write("parse_merge.xsd", encoding="utf-8", xml_declaration=True)
        # return None

        for key in self.root.attrib:
            if key == "targetNamespace":
                target_ns = self.root.attrib[key]
                # a namespace without a trailing separator would be concatenated with local names
                if not target_ns.endswith(("/", "#")):
                    target_ns += "#"
                self.xsdTargetNS = Namespace(target_ns)

        print("#########Start translating XSD to SHACL shapes")
        start = time.time()
        self.translate(self.root)
        end = time.time()
        # print("Translation time cost: " + str(end - start), "Seconds")

        print("#########Start validating SHACL shapes syntax")
        shaclValidation = Graph()
        shaclValidation.parse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shacl-shacl.ttl"), format="turtle")
        
        if len(self.SHACL) < 10000:
            r = validate(self.SHACL, shacl_graph=shaclValidation)
            if not r[0]:
                print(r[2])
            else:
                print("Well formed SHACL shapes!")
        else:
            print("Skip SHACL shape syntax check using pyshacl due to the size of SHACL shapes is too large! ")

        print("#########Start writing to file")
        if shacl_file:
            self.writeShapeToFile(shacl_file)
            print(f"Saved SHACL shapes in {shacl_file}!")
        else:
            self.writeShapeToFile(xsd_file + ".shape.ttl")
            print(f"Saved SHACL shapes in {xsd_file}.shape.ttl!")

        