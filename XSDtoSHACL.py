import xml.etree.ElementTree as ET
import rdflib
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from pyshacl import validate
import argparse


class XSDtoSHACL:
    def __init__(self):
        """

        """
        self.shaclNS = rdflib.Namespace('http://www.w3.org/ns/shacl#')
        self.rdfSyntax = rdflib.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        self.xsdNS = rdflib.Namespace('http://www.w3.org/2001/XMLSchema#')
        self.xsdTargetNS = xsdTargetNS = rdflib.Namespace('http://example.com/')
        self.NS = rdflib.Namespace('http://example.com/')
        self.xsdNSdict = dict()
        self.type_list = ['string', 'normalizedString', 'token', 'base64Binary', 'hexBinary', 'integer', 'positiveInteger', 'negativeInteger', 'nonNegativeInteger', 'nonPositiveInteger', 'long', 'unsignedLong', 'int', 'unsignedInt', 'short', 'unsignedShort', 'byte', 'unsignedByte', 'decimal', 'float', 'double', 'boolean', 'duration', 'dateTime', 'date', 'time', 'gYear', 'gYearMonth', 'gMonth', 'gMonthDay', 'gDay', 'Name', 'QName', 'NCName', 'anyURI', 'language', 'ID', 'IDREF', 'IDREFS', 'ENTITY', 'ENTITIES', 'NOTATION', 'NMTOKEN', 'NMTOKENS']
        self.SHACL = Graph()
        self.shapes = []
        self.translatedShapes = {}
        self.enumerationShapes = []
        self.order_list = []

    def isSimpleComplex(self,xsd_element,xsd_type=None):
        """A function to determine whether the type of element is SimpleType or ComplexType"""
        if xsd_type == None:
            xsd_type = xsd_element.get("type")
        if xsd_type == None:
            for child in xsd_element.findall("./"):
                if "complexType" in child.tag:
                    return 1
                elif "simpleType" in child.tag:
                    return 0
        elif "xs" in xsd_type or "xsd" in xsd_type:
            return 0 #built-in type
        else:
            child = self.root.find(f".//*[@name='{xsd_type}']",self.xsdNSdict)
            if "complexType" in child.tag:
                return 1
            elif "simpleType" in child.tag:
                return 0
        return None

    def find_parent(self, element, parent):
        for child in parent:
            if child is element:
                return parent
            if len(child) > 0:
                result = self.find_parent(element, child)
                if result is not None:
                    return result
        return None

    def transRestriction(self,tag,value):
        subject = self.shapes[-1]

        if "type" in tag or "restriction" in tag:
            # print("value:",value)
            if (":" in value) and (value.split(":")[1] in self.type_list):
                p = self.shaclNS.datatype
                #o = rdflib.Namespace(self.xsdNSdict[value.split(":")[0]])[value.split(":")[1]]
                o = self.xsdNS[value.split(":")[1]]
                self.SHACL.add((subject,p,o))

        elif "default" in tag:
            p = self.shaclNS.defaultValue
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "fixed" in tag:
            p = self.shaclNS.hasValue
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "pattern" in tag:
            p = self.shaclNS.pattern
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "maxExclusive" in tag:
            p = self.shaclNS.maxExclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))

        elif "minExclusive" in tag:
            p = self.shaclNS.minExclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
  
        elif "maxInclusive" in tag:
            p = self.shaclNS.maxInclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))

        elif "minInclusive" in tag:
            p = self.shaclNS.minInclusive
            o = Literal(int(value))
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

        elif "maxLength" in tag:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
 

    def transEleSimple(self,xsd_element):
        """A function to translate XSD element with simple type to SHACL property shape"""
        element_name = xsd_element.get("name")
        element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        element_max_occurs = Literal(int(xsd_element.get("maxOccurs", "1")))
        subject = self.NS[f'PropertyShape/{element_name}']
        # self.translatedShapes[subject] = subject

        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        if self.shapes != []:
            self.SHACL.add((self.shapes[-1],self.shaclNS.property,subject))
        self.shapes.append(subject)
        self.SHACL.add((subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        self.SHACL.add((subject,self.shaclNS.targetSubjectsOf,self.xsdTargetNS[element_name]))
        self.SHACL.add((subject,self.shaclNS.minCount,element_min_occurs))
        self.SHACL.add((subject,self.shaclNS.maxCount,element_max_occurs))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        if self.order_list != []:
            self.SHACL.add((subject,self.shaclNS.order,Literal(self.order_list.pop())))

        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])

        element_type = xsd_element.get("type") #child type, built-in type or xsd simple type
        if element_type == None:
            return xsd_element
        elif (":" in element_type) and (element_type.split(":")[1] in self.type_list): #TODO: check if this is a built-in type
            return xsd_element #already translated
        else:
            next_node = self.root.find(f'.//xs:simpleType[@name="{element_type}"]',self.xsdNSdict)
            return next_node #redirect current process to the next root (simple type)
            
        return xsd_element

    def transEleComplex(self,xsd_element):
        """A function to translate XSD element with complex type to SHACL node shape"""
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        if self.shapes != []:
            self.SHACL.add((self.shapes[-1],self.shaclNS.node,subject))
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        
        self.SHACL.add((subject,self.shaclNS.targetClass,self.xsdTargetNS[element_name]))
        self.SHACL.add((subject,self.shaclNS.targetSubjectsOf,self.xsdTargetNS[element_name]))
        #complex type does not have target, element can

        for name in xsd_element.attrib:
            if "type" not in name:
                self.transRestriction(name, xsd_element.attrib[name])

        element_type = xsd_element.get("type")
        if element_type == None:
            return xsd_element
        else:
            self.SHACL.add((subject,self.shaclNS.node,self.NS[f'NodeShape/{element_type}'])) #Will be translated later
            return xsd_element
        return xsd_element

    def transComplexType(self,xsd_element):
        """A function to translate XSD complex type to SHACL node shape""" 
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        if self.shapes != []:
            self.SHACL.add((self.shapes[-1],self.shaclNS.node,subject))
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        #complex type does not have target, element can

        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])

        return xsd_element    

    def transExtension(self,xsd_element):
        """A function to translate XSD extension to SHACL node shape"""
        element_name = xsd_element.get("base")
        subject = self.NS[f'NodeShape/{element_name}']
        if self.shapes != []:
            self.SHACL.add((self.shapes[-1],self.shaclNS.node,subject))
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        #complex type does not have target, element can

        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])

        return xsd_element    

    def transEnumeration(self, xsd_element):
        values = []
        subject = self.shapes[-1]
        parent_element = self.find_parent(xsd_element, self.root)

        if parent_element not in self.enumerationShapes:
            self.enumerationShapes.append(parent_element)
        else:
            return xsd_element

        for e in parent_element.findall('.//xs:enumeration',self.xsdNSdict):
            if e.get("value"):
                values.append(e.get("value"))

        if values == []:
            return xsd_element
        else:
            current_BN = BNode()
            self.SHACL.add((subject, self.shaclNS["in"], current_BN))
            for index in range(len(values))[0:-1]:
                self.SHACL.add((current_BN, RDF.first, Literal(values[index]))) 
                next_BN = BNode()
                self.SHACL.add((current_BN, RDF.rest, next_BN)) 
                current_BN = next_BN

            self.SHACL.add((current_BN, RDF.first, Literal(values[-1]))) 
            self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
            return xsd_element  

    def transUnion(self, xsd_element):
        values = []
        subject = self.shapes[-1]

        memberTypes = xsd_element.get("memberTypes").split(" ")

        current_BN = BNode()
        self.SHACL.add((subject, self.shaclNS["or"], current_BN))

        for index in range(len(memberTypes)):
            memberType = memberTypes[index]
            if (":" in memberType) and (memberType.split(":")[1] in self.type_list):
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

        # self.SHACL.add((current_BN, RDF.first, Literal(memberTypes[-1])))
        # self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 

                

    def translate(self,current_node):
        """A function to iteratively translate XSD to SHACL"""
        for child in current_node.findall("*"):
            # Translate current node and associate this SHACL term/shape with its corresponding SHACL shape
            tag = child.tag
            next_node = child
            if ("element" in tag) or ("attribute" in tag):
                if child.get("ref"):
                    next_node = self.root.find(f".//*[@name='{child.get('ref')}']")
                else:
                    element_type = self.isSimpleComplex(child)
                    if element_type == 0:
                        next_node = self.transEleSimple(child)
                    elif element_type == 1:
                        next_node = self.transEleComplex(child)
            elif ("simpleType" in tag) and (self.shapes == []):
                continue
            elif ("extension" in tag):
                next_node = self.transExtension(child)
            elif ("complexType" in tag) and (child.get("name")):
                next_node = self.transComplexType(child)
            elif ("complexType" in tag) or ("simpleType" in tag):
                pass
            elif ("sequence" in tag):
                self.order_list = list(reversed(range(len(child.findall("./")))))
            elif ("all" in tag) or ("choice" in tag):
                pass
            elif ("union" in tag):
                memberTypes = child.get("memberTypes").split(" ")
                self.transUnion(child)
            elif ("restriction" in tag):
                value = child.get("base")
                self.transRestriction(tag,value)
            elif ("enumeration" in tag):
                self.transEnumeration(child)
            else:
                value = child.get("value")
                self.transRestriction(tag,value)

            self.translate(next_node)
            if (("element" in tag) and (child.get("name"))) or ("attribute" in tag) or (("complexType" in tag) and (child.get("name"))) or ("extension" in tag):
                self.shapes.pop()

    def writeShapeToFile(self, file_name):
        for prefix in self.xsdNSdict:
            self.SHACL.bind(prefix, self.xsdNSdict[prefix])

        self.SHACL.bind('sh', 'http://www.w3.org/ns/shacl#', False)
        # self.SHACL.bind(
        #     'rdfs', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')

        self.SHACL.serialize(destination=file_name, format='turtle')

    def evaluate_file(self, xsd_file):
        self.xsdTree = ET.parse(xsd_file)
        self.root = self.xsdTree.getroot()

        self.xsdNSdict = dict([node for (_, node) in ET.iterparse(xsd_file, events=['start-ns'])])

        for key in self.root.attrib:
            if key == "targetNamespace":
                self.xsdTargetNS = Namespace(self.root.attrib[key])
    
        shaclValidation = Graph()
        shaclValidation.parse("https://www.w3.org/ns/shacl-shacl")

        r = validate(self.SHACL, shacl_graph=shaclValidation)
        if not r[0]:
            print(r[2])

        self.translate(self.root)
        self.writeShapeToFile(xsd_file + ".shape.ttl")
        # print(self.SHACL.serialize(format="turtle"))
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')
    parser.add_argument("xsd_file",  help='xsd_file', type=str)
    args = parser.parse_args()

    X2S = XSDtoSHACL()
    X2S.evaluate_file(args.xsd_file)
