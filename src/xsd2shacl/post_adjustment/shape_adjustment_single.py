# Shape adjustment script that can be used to individually adjust the shape derived from XSD based on RML
# Input: RML graph, XSD-driven SHACL graph
# Output: Adjusted SHACL graph

from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL
from pyshacl import validate
from .graph_dfs import GrapDFS
import re
import os
import sys
import time

class ShapeAdjustment:
    def __init__(self, source_type):
        self.shaclNS = Namespace('http://www.w3.org/ns/shacl#')
        self.rdfSyntax = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        self.rmlNS = Namespace('http://semweb.mmlab.be/ns/rml#')
        self.r2rmlNS = Namespace('http://www.w3.org/ns/r2rml#')
        self.QLNS = Namespace('http://semweb.mmlab.be/ns/ql#')
        self.FNMLNS = Namespace('http://semweb.mmlab.be/ns/fnml#')
        self.LOGICAL_SOURCE = self.rmlNS.logicalSource
        self.SOURCE = self.rmlNS.source
        self.REFERENCE_FORMULATION = self.rmlNS.referenceFormulation
        self.ITERATOR = self.rmlNS.iterator
        self.TEMPLATE = self.r2rmlNS.template
        self.REFERENCE = self.rmlNS.reference
        self.CLASS = self.r2rmlNS["class"]
        self.POM = self.r2rmlNS.predicateObjectMap
        self.PREDICATE = self.r2rmlNS.predicate
        self.PRED_MAP = self.r2rmlNS.predicateMap
        self.TRIPLES_MAP_CLASS = self.r2rmlNS.TriplesMap
        self.SUBJECT_MAP = self.r2rmlNS.subjectMap
        self.OBJECT_MAP = self.r2rmlNS.objectMap
        self.DATATYPE = self.r2rmlNS.datatype
        self.CONSTANT = self.r2rmlNS.constant
        self.OBJECT = self.r2rmlNS.object
        self.PARENTTM = self.rmlNS.parentTriplesMap

        #self.XPathFunction = ["string","codepoints-to-string","string-to-codepoints","codepoint-equal","compare","concat","string-join","substring","string-length","normalize-space","normalize-unicode","upper-case","lower-case","translate","escape-uri","contains","starts-with","ends-with","substring-before","substring-after","matches","replace","tokenize"]
        
        self.source_type = source_type
        self.adjusted_graph = Graph()
        self.adjusted_identifier = []
        self.shared_sm_identifier = {}
        self.shared_pom_identifier = {}
        # deterministic suffixes for shape identifiers that have to be disambiguated
        self.identifier_counter = 0
    
    def next_identifier_suffix(self):
        self.identifier_counter += 1
        return self.identifier_counter

    def parseRML(self, rml_graph: Graph):
        """
        A function to parse the RML graph and return a list of dictionary of the triples maps 
        (path of subject map, predicate map, object map, logical source, and classes and properties)
        """
        self.rml_graph = rml_graph
        self.iterator = None
        self.findNS = []
        self.findPS = []
        self.adjusted_shape = []
        self.rml_parsed = {}
        for triples_map_identifier in self.rml_graph.subjects(RDF.type, self.TRIPLES_MAP_CLASS):
            source_identifier = self.rml_graph.value(triples_map_identifier, self.LOGICAL_SOURCE)
            source, reference_formulation, iterator = self.getSource(source_identifier)
            # an XPath union iterator ("a | b") iterates over each alternative
            iterators = [i.strip() for i in iterator.split("|")] if iterator else [None]
            for k, it in enumerate(iterators):
                key = triples_map_identifier if len(iterators) == 1 else (triples_map_identifier, k)
                self.iterator = "" if it is None else it
                self.rml_parsed[key] = {'source': source, 'reference_formulation': reference_formulation, 'iterator': it}

                subject_map_identifier = self.rml_graph.value(triples_map_identifier, self.SUBJECT_MAP)
                path, classes,template_length, shared_key = self.getSubjectMap(subject_map_identifier)
                subject_raw = str(self.rml_graph.value(subject_map_identifier, self.TEMPLATE) or self.rml_graph.value(subject_map_identifier, self.REFERENCE) or "")
                self.rml_parsed[key]['sm'] = {'path': path, 'classes': classes, 'template_length': template_length, 'shared_key': shared_key, 'subject_raw': subject_raw}

                pom_list = []
                for pom_identifier in self.rml_graph.objects(triples_map_identifier, self.POM):
                    pom_property = self.getPredicate(pom_identifier)
                    self.last_template_raw = None
                    self.last_reference_raw = None
                    pom_object_path, pom_object_datatype, pom_object_parent, pom_object_template_length, constant, termType = self.getObjectMap(pom_identifier)
                    if pom_property == RDF.type:
                        if constant:
                            self.rml_parsed[key]['sm']['classes'].extend(pom_object_path)
                        elif self.last_reference_raw is not None:
                            # classes given as IRI literals inside a conditional reference expression
                            self.rml_parsed[key]['sm']['classes'].extend(URIRef(u) for u in re.findall(r"'(https?://[^']+)'", self.last_reference_raw))
                    else:
                        pom_list.append({'property': pom_property, 'path': pom_object_path, 'datatype': pom_object_datatype, 'parent': pom_object_parent, 'template_length': pom_object_template_length, 'constant': constant, 'termType': termType, 'template_raw': self.last_template_raw, 'reference_raw': self.last_reference_raw})
                self.rml_parsed[key]['pom'] = pom_list

    def parseRawDataSchemaShape(self, initial_graph: Graph):
        self.initial_graph = initial_graph
        self.raw_graph = Graph() + initial_graph
        self.shape_path = {}
        getattr(self, f"parse_{self.source_type}", None)()

    def getSource(self, source_identifier):
        """
        A function to get the logical source of a triples map
        """
        source, reference_formulation, iterator = None, None, None
        for s, p, o in self.rml_graph:
            if s == source_identifier and p == self.SOURCE:
                source = re.sub(r'\[.*?\]', '', str(o))
            elif s == source_identifier and p == self.REFERENCE_FORMULATION:
                reference_formulation = o
            elif s == source_identifier and p == self.ITERATOR:
                iterator = re.sub(r'\[.*?\]', '', str(o))
        return source, reference_formulation, iterator

    # def setSourceType(self, reference_formulation, iterator):
    #     if reference_formulation == self.QLNS.CSV:
    #         self.source_type = 'csv'
    #     elif reference_formulation == self.QLNS.XPath:
    #         self.source_type = 'xml'
    #         self.iterator = iterator
    #     elif reference_formulation == self.QLNS.JSONPath:
    #         self.source_type = 'json'
    #         self.iterator = iterator

    def getSubjectMap(self, subject_map_identifier):
        """
        A function to get the subject map of a triples map
        """
        path, classes, template_length, shared_key = [], [], None, None
        for s, p, o in self.rml_graph:
            if s == subject_map_identifier and p == self.TEMPLATE:
                path.extend(getattr(self, f"parseTemplate_{self.source_type}", None)(o))
                template_length = 0
                for i in str(o).split("{"):
                    template_length+=len(i.split("}")[-1])
                shared_key = self.clean_shared_key(str(o))
            elif s == subject_map_identifier and p == self.REFERENCE:
                path.extend(getattr(self, f"parseReference_{self.source_type}", None)(o))
                shared_key = self.clean_shared_key(str(o))
            elif s == subject_map_identifier and p == self.CLASS:
                classes.append(o)
        return path, classes, template_length, shared_key

    def clean_shared_key(self, shared_key):
        # remove_list = ["parent::*/parent::", "parent::*/", "parent::",]
        shared_key = re.sub(r'parent::[^/]*\/', '', shared_key)
        shared_key = re.sub(r'{[^{]*?\[.*\]/', '{', shared_key)
        return shared_key

    def getPredicate(self, pom_identifier):
        """
        A function to get the predicate of a triples map
        """
        for s, p, o in self.rml_graph:
            if s == pom_identifier and p == self.PREDICATE:
                return o
            elif s == pom_identifier and p == self.CONSTANT:
                return o
            elif s == pom_identifier and p == self.PRED_MAP:
                o = self.getPredicate(o)
                return o

    def getObjectMap(self, pom_identifier, parent=False):
        """
        A function to get the object map of a triples map
        """
        path, datatype, parent, template_length, constant, termType = [], None, False, None, False, None
        for s, p, o in self.rml_graph:
            if s == pom_identifier and p == self.OBJECT:
                path.append(o)
            elif s == pom_identifier and p == self.OBJECT_MAP:
                path, datatype, parent, template_length, constant, termType = self.getObjectMap(o)
            elif s == pom_identifier and p == self.DATATYPE:
                datatype = o
            elif s == pom_identifier and p == self.r2rmlNS.termType:
                termType = self.shaclNS[str(o).split("#")[-1]]
            elif s == pom_identifier and p == self.TEMPLATE:
                path.extend(getattr(self, f"parseTemplate_{self.source_type}", None)(o))
                template_length = 0
                for i in str(o).split("{"):
                    template_length+=len(i.split("}")[-1])
                shared_key = str(o)
                self.last_template_raw = str(o)
            elif s == pom_identifier and p == self.REFERENCE:
                path.extend(getattr(self, f"parseReference_{self.source_type}", None)(o))
                shared_key = str(o)
                self.last_reference_raw = str(o)
            elif s == pom_identifier and p == self.CONSTANT:
                path.append(o)
                constant = True
            elif s == pom_identifier and p == self.PARENTTM:
                path.append(o)
            elif s == pom_identifier and p == self.FNMLNS.functionValue:
                path = self.getFunctionValue(o)
                #path.append("skip_function")
                return path, datatype, parent, template_length, constant, termType
        if termType is None and (pom_identifier, self.TEMPLATE, None) in self.rml_graph:
            termType = self.shaclNS.IRI
        return path, datatype, parent, template_length, constant, termType

    def getFunctionValue(self, function_identifier):
        """
        A function to get the function value of a triples map
        """
        path = []
        for s, p, o in self.rml_graph:
            if s == function_identifier and p == self.POM:
                path = self.getFunctionValue(o)
            elif s == function_identifier and p == self.OBJECT_MAP:
                path = self.getFunctionValue(o)
            elif s == function_identifier and p == self.REFERENCE:
                path.extend(getattr(self, f"parseReference_{self.source_type}", None)(o))
        return path
    
    def parseTemplate_csv(self, template):
        """
        A function to parse the template in a triples map and return path list
        """
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template)
        matches = [self.iterator+"/" + i for i in matches]

        return [matches]

    def parseReference_csv(self, reference):
        """
        A function to parse the reference in a triples map and return path list
        """
        pass
    
    def parseTemplate_xml(self, template):
        """
        A function to parse the template in a triples map and return path list
        """
        self.XPathFunction = {"string":'string\((.*?)\)',
        "substring":'substring\((.*?)\,',
        "string-length":'string-length\((.*?)\)',
        "upper-case":'upper-case\((.*?)\)',
        "lower-case":'lower-case\((.*?)\)',
        "substring-before":'substring-before\((.*?)\,',
        "substring-after":'substring-after\((.*?)\,',
        "replace":'replace\((.*?)\,'}
        
        template = re.sub(r'\[.*?\]', '', template)
        matches = re.findall(r'\{([^}]+)\}', template)
        for i in range(len(matches)):
            for function in self.XPathFunction:
                if re.search(r'(?<![\w-])' + re.escape(function) + r'\(', matches[i]):
                    m = re.search(r'(?<![\w-])' + self.XPathFunction[function], matches[i])
                    if m:
                        matches[i] = m.group(1)
        # matches = [self.iterator+"/"+i.replace("@","") for i in matches]
        matches = [self.iterator+"/"+i for i in matches]
  
        return [matches]

    def parseReference_xml(self, reference):
        """
        A function to parse the reference in a triples map and return path list
        """
        self.XPathFunction = {"string":'string\((.*?)\)',
        "substring":'substring\((.*?)\,',
        "string-length":'string-length\((.*?)\)',
        "upper-case":'upper-case\((.*?)\)',
        "lower-case":'lower-case\((.*?)\)',
        "substring-before":'substring-before\((.*?)\,',
        "substring-after":'substring-after\((.*?)\,',
        "replace":'replace\((.*?)\,'}

        for function in self.XPathFunction:
            if re.search(r'(?<![\w-])' + re.escape(function) + r'\(', reference):
                m = re.search(r'(?<![\w-])' + self.XPathFunction[function], reference)
                if m:
                    reference = m.group(1)
        reference = re.sub(r'\[.*?\]', '', reference)
        # return [[self.iterator+"/"+reference.replace("@","")]]
        return [[self.iterator+"/"+reference]]

    def parseTemplate_json(self, template):
        """
        A function to parse the template in a triples map and return path list
        """
        pass

    def parseReference_json(self, reference):
        """
        A function to parse the reference in a triples map and return path list
        """
        pass
    
    def parse_xml(self):
        """
        A function to parse XSD to return the identifier of shape and corresponding XPath
        """
        complex_type_list = self.getComplexType()
        self.getShapePath(complex_type_list)
        
    def getComplexType(self):
        """
        A function to get the identifier of the shape that translated from complex type
        """
        complex_type_list = []
        for s, p, o in self.initial_graph.triples((None, self.shaclNS.node, None)):
            if len(str(o).split("http://example.com/NodeShape/")[-1].split("/")) == 1:
                complex_type_list.append(str(o).split("http://example.com/NodeShape/")[-1])
        return list(set(complex_type_list))

    def getShapePath(self, complex_type_list):
        gdfs = GrapDFS()

        for s, p, o in self.initial_graph.triples((None, self.shaclNS.property, None)):
            gdfs.add_edge(str(o), str(s))
        for s, p, o in self.initial_graph.triples((None, self.shaclNS.node, None)):
            if "http://example.com/NodeShape/None" != str(o):
                gdfs.add_edge(str(o), str(s))
        result = gdfs.find_paths()

        for _, node_paths in result.items():
            for path in node_paths:
                l = self.shape_path.get(path[0],[])
                l.append(path)
                self.shape_path[path[0]] = l

        for identifier in self.shape_path:  
            for p in range(len(self.shape_path[identifier])):
                url_list = self.shape_path[identifier][p]
                paths = []
                for i in range(len(url_list)):
                    url = url_list[i]
                    if url.split('/')[-1] not in complex_type_list:
                        if i != len(url_list)-1:
                            paths.append(url.split('/')[-1])
                        elif "NodeShape" in url:
                            paths.append(url.split('NodeShape/')[-1])
                        elif "PropertyShape" in url:
                            paths.append(url.split('PropertyShape/')[-1])
                paths = paths[::-1]
                # paths = [url.split('/')[-1] for url in url_list if url.split('/')[-1] not in complex_type_list][::-1]
                result = '/'.join(paths)
                # result = re.sub(r'([^/]+)/\1', r'\1', result)
                result = re.sub(r'(/[^/]+)/\1', r'\1', result)
                # Remove duplicate path
                path_parts = result.split('/')
                result = path_parts[0]
                for i in range(1,len(path_parts)):
                    part = path_parts[i]
                    if part != path_parts[i-1]:
                        result += '/' + part

                if result[0] != '/':
                    result = '/'+result
                self.shape_path[identifier][p] = result


    def getPath(self, identifier, complex_type_list):
        identifier = str(identifier)
        if "NodeShape" in identifier:
            p = identifier.split("http://example.com/NodeShape/")[-1].split("/")
            p = [i for i in p if i not in complex_type_list]
            return "/".join(p)
        elif "PropertyShape" in identifier:
            p = identifier.split("http://example.com/PropertyShape/")[-1].split("/")
            p = [i for i in p if i not in complex_type_list]
            return "/".join(p)
    
    def adjust_sm(self, sm_path, sm_classes, shared_key):
        """
        Adjust target declarations of shape
        """

        if shared_key in self.shared_sm_identifier:
            for shape_identifier in self.shared_sm_identifier[shared_key]:
                for sm_class in sm_classes:
                    self.initial_graph.add((URIRef(shape_identifier), self.shaclNS.targetClass, URIRef(sm_class)))
                self.findNS.append(URIRef(shape_identifier))
            return None

        # if sm_classes == []:
        #     return None

        temp_pop = str(self.next_identifier_suffix())
        for path_list in sm_path:
            for path in path_list:
                for shape_identifier in self.shape_path:
                    if "PropertyShape" in shape_identifier:
                        continue
                    for initial_path in self.shape_path[shape_identifier]:
                        if initial_path == path or initial_path == self.iterator or path.endswith(initial_path) or ("parent:" in path and self.validatePath(path, initial_path)):
                            if URIRef(shape_identifier) in self.adjusted_shape:
                                #new_shape_identifier = shape_identifier + "/" + "/".join([i.split("/")[-1] for i in sm_classes])
                                new_shape_identifier = shape_identifier + "/" + "/".join([i.split("/")[-1] for i in sm_classes]) + temp_pop
                                self.updateShape(URIRef(shape_identifier), URIRef(new_shape_identifier))
                                shape_identifier = new_shape_identifier
                            
                            self.initial_graph.remove((URIRef(shape_identifier), self.shaclNS.targetClass, None))
                            self.findNode(URIRef(shape_identifier))
                            for sm_class in sm_classes:
                                self.initial_graph.add((URIRef(shape_identifier), self.shaclNS.targetClass, URIRef(sm_class)))
                            
                            l = self.shared_sm_identifier.get(shared_key,[])
                            l.append(shape_identifier)
                            self.shared_sm_identifier[shared_key] = l

                            self.findNS.append(URIRef(shape_identifier))
                            self.adjusted_shape.append(URIRef(shape_identifier))
        
        if self.findNS == []:
            shape_identifier = URIRef("http://example.com/NodeShape/" + "/".join([i.split("/")[-1] for i in sm_classes]))
            self.initial_graph.add((shape_identifier, RDF.type, self.shaclNS.NodeShape))
            for sm_class in sm_classes:
                self.initial_graph.add((shape_identifier, self.shaclNS.targetClass, URIRef(sm_class)))
            self.initial_graph.add((shape_identifier, self.shaclNS.nodeKind, self.shaclNS.IRI))

            l = self.shared_sm_identifier.get(shared_key,[])
            l.append(shape_identifier)
            self.shared_sm_identifier[shared_key] = l

            self.findNS.append(shape_identifier)
            self.adjusted_shape.append(shape_identifier)


    def updateShape(self, shape_identifier, new_shape_identifier):
        for s, p, o in self.initial_graph.triples((shape_identifier, None, None)):
            self.initial_graph.add((new_shape_identifier,p,o))
        for s, p, o in list(self.initial_graph.triples((None, None, shape_identifier))):
            self.initial_graph.add((s,p,new_shape_identifier))
            if p == RDF.first:
                # a list member is replaced, not duplicated (a list node has exactly one rdf:first)
                self.initial_graph.remove((s,p,o))

    def updateSharedShape(self):
        pass

    def findNode(self, node):
        for s, p, o in self.initial_graph.triples((node, self.shaclNS.node, None)):
            self.adjusted_shape.append(o)
            self.initial_graph.remove((o, self.shaclNS.targetClass, None))
            self.initial_graph.remove((o, self.shaclNS.targetNode, None))
            self.initial_graph.remove((o, self.shaclNS.targetObjectsOf, None))
            self.initial_graph.remove((o, self.shaclNS.targetSubjectsOf, None))
            self.findNode(o)

    def adjust_pom(self, pom_list):
        if self.findNS == []:
            return None  # Comment it and next one if you want to add targetSubjectsOf to the shape which doesn't referenced by a node shape that has target declaration
        for pom in pom_list:
            for path_list in pom["path"]:
                if len(path_list) == 1:
                    path = path_list[0]
                    for shape_identifier in self.shape_path:
                        if "NodeShape" in shape_identifier:
                            continue 
                        for initial_path in self.shape_path[shape_identifier]:   
                            if (initial_path == path) or path.endswith(initial_path) or (pom["constant"] == True and initial_path == self.iterator) or ("parent:" in path and self.validatePath(path, initial_path)):
                                shape_identifier = URIRef(shape_identifier)
                                original_identifier = shape_identifier
                                if shape_identifier in self.adjusted_shape:
                                    # new_shape_identifier = shape_identifier + "/" + pom["property"].split("/")[-1]
                                    new_shape_identifier = URIRef(str(shape_identifier) + "/" + pom["property"].split("/")[-1] + str(self.next_identifier_suffix()))
                                    self.updateShape(shape_identifier, new_shape_identifier)
                                    shape_identifier = new_shape_identifier
                                self.adjusted_shape.append(shape_identifier)
                                self.initial_graph.remove((shape_identifier, self.shaclNS.path, None))
                                self.initial_graph.add((shape_identifier, self.shaclNS.path, pom["property"]))
                                self.applyEffectiveCardinality(shape_identifier, original_identifier)
                                if pom["datatype"] is not None:
                                    self.initial_graph.remove((shape_identifier, self.shaclNS.nodeKind, None))
                                    self.initial_graph.remove((shape_identifier, self.shaclNS.datatype, None))
                                    self.initial_graph.add((shape_identifier, self.shaclNS.datatype, pom["datatype"]))
                                if pom["termType"] is not None:
                                    self.initial_graph.remove((shape_identifier, self.shaclNS.nodeKind, None))
                                    self.initial_graph.add((shape_identifier, self.shaclNS.nodeKind, pom["termType"]))
                                    self.removeLiteralConstraints(shape_identifier)
                                if pom["template_length"] is not None:
                                    value = self.initial_graph.value(shape_identifier, self.shaclNS.minLength)
                                    if value is not None:
                                        self.initial_graph.remove((shape_identifier, self.shaclNS.minLength, value))
                                        self.initial_graph.add((shape_identifier, self.shaclNS.minLength, Literal(int(pom["template_length"])+int(value))))
                                    value = self.initial_graph.value(shape_identifier, self.shaclNS.maxLength)
                                    if value is not None:
                                        self.initial_graph.remove((shape_identifier, self.shaclNS.maxLength, value))
                                        self.initial_graph.add((shape_identifier, self.shaclNS.maxLength, Literal(int(pom["template_length"])+int(value))))
                                # if self.findNS == []:
                                #     self.initial_graph.add((shape_identifier, self.shaclNS.targetSubjectsOf, pom["property"]))
                                self.findPS.append(shape_identifier)
                                for subject in self.findNS:
                                    self.initial_graph.add((subject, self.shaclNS.property, shape_identifier))
 
                else:
                    constraints = {}
                    for path in path_list:
                        for shape_identifier_temp in self.shape_path:
                            if "NodeShape" in shape_identifier_temp:
                                continue
                            for initial_path in self.shape_path[shape_identifier_temp]:
                                if (initial_path == path) or path.endswith(initial_path) or (pom["constant"] == True and initial_path == self.iterator) or ("parent:" in path and self.validatePath(path, initial_path)):
                                #if initial_path == path or path.endswith(initial_path) or ("parent:" in path and self.validatePath(path, initial_path)):
                                    shape_identifier = shape_identifier_temp
                                    constraints = self.getConstraints(URIRef(shape_identifier_temp), constraints)
                                    # cardinality of this path relative to the iterated element
                                    eff_min, eff_max = self.effectiveCardinality(URIRef(shape_identifier_temp))
                                    constraints.setdefault("_effective", []).append((eff_min, eff_max))
                    if constraints!={}:
                        # new_shape_identifier = shape_identifier + "/" + pom["property"].split("/")[-1]     
                        shape_identifier = shape_identifier + "/" + pom["property"].split("/")[-1] + str(self.next_identifier_suffix())
                        self.adjusted_shape.append(URIRef(shape_identifier))
                        self.updateCombinationShape(URIRef(shape_identifier), pom["property"], constraints,pom["template_length"])
                        self.findPS.append(URIRef(shape_identifier))
            
            if self.findPS == []:
                # shape_identifier = URIRef("http://example.com/PropertyShape/" + pom["property"].split("/")[-1])
                shape_identifier = URIRef("http://example.com/PropertyShape/" + pom["property"].split("/")[-1] + str(self.next_identifier_suffix()))
                
                self.initial_graph.add((shape_identifier, RDF.type, self.shaclNS.PropertyShape))
                self.initial_graph.add((shape_identifier, self.shaclNS.path, pom["property"]))
                if self.findNS:
                    for subject in self.findNS:
                        self.initial_graph.add((subject, self.shaclNS.property, shape_identifier))
                else:
                    # no node shape with a target declaration refers to the property shape:
                    # target the subjects that carry the property
                    self.initial_graph.add((shape_identifier, self.shaclNS.targetSubjectsOf, pom["property"]))
                if pom["datatype"] is not None:
                    self.initial_graph.add((shape_identifier, self.shaclNS.datatype, pom["datatype"]))
                if pom["termType"] is not None:
                    self.initial_graph.add((shape_identifier, self.shaclNS.nodeKind, pom["termType"]))
                    self.removeLiteralConstraints(shape_identifier)
                    
                self.findPS.append(shape_identifier)
                self.adjusted_shape.append(shape_identifier)

            self.findPS = []

    def validatePath(self, path_target, path):
        result = path_target.split("parent::")
        final_result = []
        for item in result:
            final_result.extend(item.split("*"))
        final_result = [i for i in final_result if i!=""]
        if path.endswith(final_result[-1]):
            for p in final_result[:-1]:
                if p not in path:
                    return False
            return True
        else:
            return False
    
    def generate_regex(self, paths):
        regex_pattern = ".*".join([re.escape(path) for path in paths])
        return ".*" + regex_pattern + "$"

    def getConstraints(self, shape_identifier, constraints):
        for s, p, o in self.initial_graph.triples((shape_identifier, None, None)):
            if p != RDF.type:
                l = constraints.get(p,[])
                l.append(o)
                constraints[p] = l
        return constraints

    def updateCombinationShape(self, shape_identifier, property, constraints, template_length):
        self.initial_graph.add((shape_identifier, RDF.type, self.shaclNS.PropertyShape))
        self.initial_graph.add((shape_identifier, self.shaclNS.nodeKind, self.shaclNS.IRI))
        self.initial_graph.add((shape_identifier, self.shaclNS.path, property))

        if self.findNS:
            for subject in self.findNS:
                self.initial_graph.add((subject, self.shaclNS.property, shape_identifier))
        else:
            # no node shape with a target declaration refers to the property shape:
            # target the subjects that carry the property
            self.initial_graph.add((shape_identifier, self.shaclNS.targetSubjectsOf, property))

        effective = constraints.get("_effective")
        for constraint, constraint_value in constraints.items():
            if constraint == "_effective":
                continue
            if constraint == self.shaclNS.minCount or constraint == self.shaclNS.maxCount:
                if effective:
                    # product of the effective bounds of the combined paths; unbounded if any is
                    values = [m for m, _ in effective] if constraint == self.shaclNS.minCount else [x for _, x in effective]
                    if constraint == self.shaclNS.maxCount and any(v is None for v in values):
                        continue
                    values = [v for v in values if v is not None]
                    if not values:
                        continue
                    current_number = 1
                    for v in values:
                        current_number *= int(v)
                    self.initial_graph.add((shape_identifier, constraint, Literal(current_number)))
                    continue
                current_number = 1
                for value in constraint_value:
                    current_number*=int(value)
                self.initial_graph.add((shape_identifier, constraint, Literal(current_number)))
            elif constraint == self.shaclNS.minLength or constraint == self.shaclNS.maxLength:
                current_number = template_length
                for value in constraint_value:
                    current_number+=int(value)
                self.initial_graph.add((shape_identifier, constraint, Literal(current_number)))

    def effectiveCardinality(self, shape_identifier):
        """(minCount, maxCount) of an XSD-driven property shape relative to the iterated element of
        the current triples map: the shape's own bounds multiplied by the minOccurs/maxOccurs of
        every nested element between the iterated element and the referenced node (read from the
        linking property shapes of the raw graph). maxCount None means unbounded."""
        g = self.raw_graph
        sid = str(shape_identifier)
        if "PropertyShape/" not in sid:
            return None, None
        rel = sid.split("PropertyShape/", 1)[1]
        iterator = (self.tm_iterator or "").strip("/")
        if iterator and rel.startswith(iterator + "/"):
            rel = rel[len(iterator) + 1:]
            base = "http://example.com/PropertyShape/" + iterator
        else:
            base = "http://example.com/PropertyShape"
        parts = rel.split("/")
        own_min, own_max = g.value(shape_identifier, self.shaclNS.minCount), g.value(shape_identifier, self.shaclNS.maxCount)
        min_c = int(own_min) if own_min is not None else None
        max_c = int(own_max) if own_max is not None else None
        for i in range(1, len(parts)):
            link = URIRef(base + "/" + "/".join(parts[:i]))
            if (link, self.shaclNS.node, None) not in g:
                continue
            lmin, lmax = g.value(link, self.shaclNS.minCount), g.value(link, self.shaclNS.maxCount)
            if min_c is not None and lmin is not None:
                min_c *= int(lmin)
            if max_c is not None:
                max_c = max_c * int(lmax) if lmax is not None else None
        return min_c, max_c

    def applyEffectiveCardinality(self, shape_identifier, original_identifier):
        min_c, max_c = self.effectiveCardinality(original_identifier)
        if min_c is None and max_c is None and (original_identifier, self.shaclNS.maxCount, None) not in self.raw_graph:
            return
        if min_c is not None:
            self.initial_graph.remove((shape_identifier, self.shaclNS.minCount, None))
            self.initial_graph.add((shape_identifier, self.shaclNS.minCount, Literal(min_c)))
        self.initial_graph.remove((shape_identifier, self.shaclNS.maxCount, None))
        if max_c is not None:
            self.initial_graph.add((shape_identifier, self.shaclNS.maxCount, Literal(max_c)))

    def originalShape(self, identifier):
        """The raw-graph node shape a (possibly renamed) shape identifier derives from: the longest
        prefix of the identifier that is a node shape of the raw graph"""
        sid = str(identifier)
        while sid and "NodeShape/" in sid:
            if (URIRef(sid), RDF.type, self.shaclNS.NodeShape) in self.raw_graph:
                return URIRef(sid)
            sid = sid.rsplit("/", 1)[0]
        return identifier

    def removeLiteralConstraints(self, shape_identifier):
        """Constraints that only apply to literals cannot hold once the node kind excludes literals"""
        kind = self.initial_graph.value(shape_identifier, self.shaclNS.nodeKind)
        if kind in (self.shaclNS.IRI, self.shaclNS.BlankNode, self.shaclNS.BlankNodeOrIRI):
            for c in [self.shaclNS.datatype, self.shaclNS.languageIn, self.shaclNS.minInclusive, self.shaclNS.maxInclusive, self.shaclNS.minExclusive, self.shaclNS.maxExclusive]:
                self.initial_graph.remove((shape_identifier, c, None))

    @staticmethod
    def _normalise_template(template, child_name=None):
        t = re.sub(r'\[[^\]]*\]', '', str(template))
        t = re.sub(r'parent::[^/{}]*/', '', t)
        if child_name:
            t = t.replace("{" + child_name + "/", "{")
        return t

    @staticmethod
    def _refs(template):
        return re.findall(r'\{([^{}]+)\}', str(template))

    @staticmethod
    def _references_child(ref, child_name):
        """True if a reference or template reads the content of the child element"""
        r = re.sub(r'\[[^\]]*\]', '', str(ref))
        return r.startswith(child_name + "/") or ("{" + child_name + "/") in r

    def _subject_refs(self, entry):
        return [re.sub(r'\[[^\]]*\]', '', r) for r in self._refs(entry["sm"].get("subject_raw", ""))]

    def _subject_is_parent(self, entry, parent_path, child_path, child_name):
        """The triples map generates the parent resource: it iterates over the parent and its
        subject does not read the child's content, or it iterates over the child with a subject
        built only from parent:: references"""
        it = (entry.get("iterator") or "").split("[")[0]
        refs = self._subject_refs(entry)
        if it == parent_path:
            # a subject built entirely from the child's content identifies the child, not the parent
            return not (refs != [] and all(self._references_child(r, child_name) for r in refs))
        return it == child_path and refs != [] and all("parent::" in r for r in refs)

    def _subject_is_child(self, entry, child_path, child_name):
        """The triples map generates a resource of its own for the child"""
        it = (entry.get("iterator") or "").split("[")[0]
        refs = self._subject_refs(entry)
        if it == child_path and not (refs != [] and all("parent::" in r for r in refs)):
            return True
        # a subject built entirely from the child's content identifies a resource of the child
        return refs != [] and all(self._references_child(r, child_name) for r in refs)

    def adjust_linking_shapes(self):
        """Property shapes linking a parent node shape to the node shape of a nested complex
        element: replace the path with the predicate the mapping uses when the child is an
        independent resource, fold back to sh:node when the mapping puts the child's values
        on the parent's subject, otherwise leave the shape to be removed as unadjusted."""
        self.linking_decisions = {"replace": 0, "fold": 0, "fold_node": 0, "delete": 0, "fold_conflicts": []}
        entries = list(self.rml_parsed.values())
        for ps in list(self.initial_graph.subjects(RDF.type, self.shaclNS.PropertyShape)):
            child = self.initial_graph.value(ps, self.shaclNS.node)
            path = self.initial_graph.value(ps, self.shaclNS.path)
            if child is None or path is None or ps in self.adjusted_shape or "PropertyShape/" not in str(ps):
                continue
            for parent in list(self.initial_graph.subjects(self.shaclNS.property, ps)):
                if "NodeShape/" not in str(parent):
                    continue
                # renamed copies of a node shape share the element path of the original shape
                parent_path = "/" + str(self.originalShape(parent)).split("NodeShape/")[1]
                child_name = str(ps).split("/")[-1]
                child_path = parent_path + "/" + child_name
                child_tms = [e for e in entries if self._subject_is_child(e, child_path, child_name)]
                parent_tms = [e for e in entries if self._subject_is_parent(e, parent_path, child_path, child_name)]
                child_subjects = {self._normalise_template(c["sm"].get("subject_raw", ""), child_name) for c in child_tms}
                decision = "delete"
                for e in parent_tms:
                    for pom in e.get("pom", []):
                        if pom.get("template_raw") and self._normalise_template(pom["template_raw"], child_name) in child_subjects:
                            self.initial_graph.remove((ps, self.shaclNS.path, None))
                            self.initial_graph.add((ps, self.shaclNS.path, pom["property"]))
                            self.initial_graph.remove((ps, self.shaclNS.nodeKind, None))
                            self.initial_graph.add((ps, self.shaclNS.nodeKind, self.shaclNS.IRI))
                            self.adjusted_shape.append(ps)
                            decision = "replace"
                            break
                    if decision == "replace":
                        break
                if decision == "delete":
                    # fold only when an object map of a parent triples map reads the child's content directly
                    refs = [pom.get("template_raw") or pom.get("reference_raw") or "" for e in parent_tms for pom in e.get("pom", [])]
                    if any(self._references_child(r, child_name) for r in refs):
                        self.initial_graph.remove((parent, self.shaclNS.property, ps))
                        decision = self.foldChildIntoParent(parent, child)
                self.linking_decisions[decision] += 1

    def foldChildIntoParent(self, parent, child):
        """Copy the child's node-level constraints (sh:property links, sh:nodeKind, sh:node to type
        definitions, sh:xone, ...) to the parent; target declarations, sh:name, sh:description and
        sh:order are not copied. A differing value of a single-valued parameter on the parent is a
        conflict: the child is then referenced with sh:node and the case is recorded."""
        sh = self.shaclNS
        not_folded = {RDF.type, sh.targetClass, sh.targetNode, sh.targetSubjectsOf, sh.targetObjectsOf, sh.name, sh.description, sh.order}
        single_valued = {sh.nodeKind, sh.closed, sh.datatype, sh.minLength, sh.maxLength, sh.pattern, sh.flags,
                         sh.minInclusive, sh.maxInclusive, sh.minExclusive, sh.maxExclusive, sh.minCount, sh.maxCount}
        to_copy = [(p, o) for p, o in self.initial_graph.predicate_objects(child) if p not in not_folded]
        for p, o in to_copy:
            if p in single_valued:
                existing = set(self.initial_graph.objects(parent, p))
                if existing and o not in existing:
                    self.linking_decisions.setdefault("fold_conflicts", []).append((str(parent), str(child), str(p), [str(e) for e in existing], str(o)))
                    self.initial_graph.add((parent, sh.node, child))
                    self.findNode(parent)
                    return "fold_node"
        for p, o in to_copy:
            self.initial_graph.add((parent, p, o))
        # nested node shapes reachable from the parent are kept and lose their own targets
        self.findNode(parent)
        return "fold"
    
    LOGICAL_CONSTRAINTS = None  # set in adjustLogicalMembers (needs self.shaclNS)

    def _removeBlank(self, node):
        """Remove a blank shape with everything reachable from it through blank nodes"""
        for _, p, o in list(self.initial_graph.triples((node, None, None))):
            self.initial_graph.remove((node, p, o))
            if isinstance(o, BNode):
                self._removeBlank(o)

    def _adjustLogicalMember(self, member, base):
        """Returns True if the (blank) member shape is kept"""
        g, sh = self.initial_graph, self.shaclNS
        path = g.value(member, sh.path)
        if path is not None:
            local = str(path).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            original_ps = URIRef(base + "/" + local)
            if self.raw_graph.value(original_ps, sh.path) != path:
                # a candidate referring to a global simple element uses the global property shape
                original_ps = URIRef(base.split("PropertyShape/")[0] + "PropertyShape/" + local)
                if self.raw_graph.value(original_ps, sh.path) != path:
                    return True  # not the XSD path of a candidate element of this node shape
            # the candidate's property shape after the adjustment: the same IRI with a new path,
            # or a renamed copy (an IRI below it that does not exist in the raw graph)
            new_paths = sorted({o for s, o in g.subject_objects(sh.path)
                                if isinstance(s, URIRef) and (s, sh.path, o) not in self.raw_graph
                                and (str(s) == str(original_ps)
                                     or (str(s).startswith(str(original_ps) + "/") and (s, None, None) not in self.raw_graph))}, key=str)
            if not new_paths:
                self._removeBlank(member)
                self.logical_decisions["dropped"] += 1
                return False
            if len(new_paths) > 1:
                self.logical_decisions["ambiguous"].append((str(original_ps), [str(x) for x in new_paths]))
            g.remove((member, sh.path, None))
            g.add((member, sh.path, new_paths[0]))
            self.logical_decisions["remapped"] += 1
            return True
        for p in self.LOGICAL_CONSTRAINTS:
            for head in list(g.objects(member, p)):
                if not self._adjustLogicalList(head, base):
                    g.remove((member, p, head))
        if not any(True for p in self.LOGICAL_CONSTRAINTS for _ in g.objects(member, p)):
            self._removeBlank(member)
            return False
        return True

    def _adjustLogicalList(self, head, base):
        """Adjust the members of an RDF list of shapes; returns True if any member is kept"""
        g, node, kept = self.initial_graph, head, 0
        while node is not None and node != RDF.nil:
            member = g.value(node, RDF.first)
            if isinstance(member, BNode):
                if self._adjustLogicalMember(member, base):
                    kept += 1
                else:
                    g.remove((node, RDF.first, member))  # spliced out by repair_lists
            elif member is not None:
                kept += 1
            node = g.value(node, RDF.rest)
        return kept > 0

    def adjustLogicalMembers(self):
        """The blank member shapes of the sh:xone / sh:or / sh:and lists generated for choices
        carry the XSD path of a candidate element. A member whose candidate's property shape
        (PropertyShape/<node shape path>/<element>) was re-pathed by the mapping takes that
        path; a member whose candidate was not adjusted is removed, and lists left empty are
        removed with their constraint."""
        sh = self.shaclNS
        self.LOGICAL_CONSTRAINTS = [sh.xone, sh["or"], sh["and"]]
        self.logical_decisions = {"remapped": 0, "dropped": 0, "ambiguous": []}
        g = self.initial_graph
        for node in sorted(set(g.subjects(RDF.type, sh.NodeShape)), key=str):
            if not isinstance(node, URIRef) or "NodeShape/" not in str(node):
                continue
            # renamed copies of a node shape share the element path of the original shape
            base = str(self.originalShape(node)).replace("NodeShape/", "PropertyShape/", 1)
            for p in self.LOGICAL_CONSTRAINTS:
                for head in list(g.objects(node, p)):
                    if not self._adjustLogicalList(head, base):
                        g.remove((node, p, head))
                        self._removeBlank(head)
        self.repair_lists()

    def clear_graph(self):
        identifier_to_remove = []
        for s,p,o in self.initial_graph:
            if p == RDF.type and (o == self.shaclNS.NodeShape or o == self.shaclNS.PropertyShape):
                if s not in self.adjusted_shape:
                    identifier_to_remove.append(s)
            if s == URIRef("http://example.com/NodeShape/None") or o == URIRef("http://example.com/NodeShape/None"):
                self.initial_graph.remove((s,p,o))
        self.remove_graph(identifier_to_remove)
        self.repair_lists()

    def repair_lists(self):
        """Remove list members whose rdf:first was deleted together with a removed shape, so that
        sh:xone / sh:or / sh:and lists stay well-formed; an emptied list is dropped altogether"""
        g = self.initial_graph
        changed = True
        while changed:
            changed = False
            for node in list(g.subjects(RDF.rest, None)):
                if g.value(node, RDF.first) is None:
                    rest = g.value(node, RDF.rest)
                    for s, p in list(g.subject_predicates(node)):
                        g.remove((s, p, node))
                        if rest == RDF.nil and p != RDF.rest:
                            continue
                        g.add((s, p, rest))
                    g.remove((node, None, None))
                    changed = True

    def remove_graph(self, old_subjects):
        """Remove the shapes in old_subjects with every triple that refers to them, and the blank
        nodes reachable from them (lists and their member shapes, to any depth) that no kept triple
        still refers to"""
        g = self.initial_graph
        old = set(old_subjects)
        pending = []
        for s, p, o in list(g):
            if s in old:
                g.remove((s, p, o))
                if isinstance(o, BNode):
                    pending.append(o)
            elif o in old:
                g.remove((s, p, o))
        seen = set()
        while pending:
            b = pending.pop()
            if b in seen:
                continue
            seen.add(b)
            if (None, None, b) in g:
                continue
            for s, p, o in list(g.triples((b, None, None))):
                g.remove((s, p, o))
                if isinstance(o, BNode):
                    pending.append(o)

    def reassign_identifier(self):
        current_adjusted_identifier = []    
        for s, p, o in self.initial_graph:
            if p == RDF.type and (o == self.shaclNS.NodeShape or o == self.shaclNS.PropertyShape):
                if s not in self.adjusted_identifier:
                    current_adjusted_identifier.append(s)
                else:
                    new_shape_identifier = URIRef(str(s)+str(self.next_identifier_suffix()))
                    current_adjusted_identifier.append(new_shape_identifier)
                    for s2, p2, o2 in self.initial_graph:
                        if s2 == s:
                            self.initial_graph.remove((s2,p2,o2))
                            self.initial_graph.add((new_shape_identifier,p2,o2))
                        elif o2 == s:
                            self.initial_graph.remove((s2,p2,o2))
                            self.initial_graph.add((s2,p2,new_shape_identifier))
        self.adjusted_identifier.extend(current_adjusted_identifier)

    def double_check(self):
        double_check_list = [self.shaclNS.datatype, self.shaclNS["in"], self.shaclNS.languageIn, self.shaclNS.minCount, self.shaclNS.maxCount, self.shaclNS.minLength, self.shaclNS.maxLength, self.shaclNS.maxExclusive, self.shaclNS.minExclusive, self.shaclNS.maxInclusive, self.shaclNS.minInclusive, self.shaclNS.pattern, self.shaclNS.uniqueLang]
        for identifier in self.adjusted_identifier:
            if "NodeShape" in identifier:
                for s, p, o in self.adjusted_graph.triples((identifier, None, None)):
                    if p in double_check_list:
                        self.adjusted_graph.remove((s,p,o))

    def adjust(self, initial_graph):
        self.initial_graph = initial_graph 
        for triples_map_identifier in self.rml_parsed:
            self.tm_iterator = self.rml_parsed[triples_map_identifier]["iterator"] or ""
            self.adjust_sm(self.rml_parsed[triples_map_identifier]["sm"]["path"], self.rml_parsed[triples_map_identifier]["sm"]["classes"], self.rml_parsed[triples_map_identifier]["sm"]["shared_key"])
            self.adjust_pom(self.rml_parsed[triples_map_identifier]["pom"])
            self.findNS = []
        self.adjust_linking_shapes()
        self.adjustLogicalMembers()
        self.clear_graph()
        self.reassign_identifier()
        self.adjusted_graph+=self.initial_graph

    def writeShapeToFile(self, output_file):
        self.double_check()

        # shacl-shacl.ttl is stored next to the package directory of this module
        shacl_shacl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shacl-shacl.ttl")
        validation_shape_graph = Graph().parse(shacl_shacl_path, format="turtle")
        r = validate(self.adjusted_graph, shacl_graph=validation_shape_graph, ont_graph=None,
                     inference='rdfs', abort_on_first=False, meta_shacl=False, debug=False)
        if not r[0]:
            print(r[2])
        else:
            print("Saved to adjusted SHACL shapes to file", output_file)
        self.adjusted_graph.serialize(destination=output_file, format='turtle')
