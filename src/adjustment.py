import rdflib
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.plugins.sparql import prepareQuery
import os
import re
import json
from .utils import clear_graph, update_graph

class Adjustment:
    def __init__(self):
        """
        Adjust the vocabulary of SHACL shapes from the XSD against the vocabulary used in the relavant mapping file
        Input: SHACL shapes from XSD, RDF Mapping file
        Output: Adjusted SHACL shapes
        """
        self.RR = Namespace("http://www.w3.org/ns/r2rml#")
        self.RML = Namespace("http://semweb.mmlab.be/ns/rml#")
        self.RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        self.SHACL = Namespace("http://www.w3.org/ns/shacl#")
        self.NS = Namespace('http://example.com/')
        self.correctKind = False

        self.mapping_dicts = []


        self.query_yarrrml = prepareQuery("""
                                        SELECT ?tm ?iterator ?targetClass ?subjectTemplate ?subjectReference ?predicate ?objectReference ?objectTemplate 
                                        WHERE {
                                            ?tm a rr:TriplesMap ;
                                                rml:logicalSource [ rml:iterator ?iterator ] ;
                                                rr:subjectMap ?sm .
                                            {  { ?sm rr:template ?subjectTemplate } UNION { ?sm rml:reference ?subjectReference } }   
                                            OPTIONAL {
                                                ?tm rr:predicateObjectMap [rr:predicateMap [rr:constant <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ] ;
                                                                            rr:objectMap [rr:constant ?targetClass] ]. }
                                            OPTIONAL {
                                                ?tm rr:predicateObjectMap [rr:predicateMap ?pm ;
                                                                            rr:objectMap ?om ].
                                                ?pm rr:constant ?predicate.
                                            {  { ?om rml:reference ?objectReference } UNION { ?om rr:template ?objectTemplate } } }
                                        }
                                    """, initNs={"rr": self.RR, "rml": self.RML})
        self.query_rml = prepareQuery("""
                                        SELECT ?tm ?iterator ?targetClass_Position1 ?targetClass_Position2 ?subjectTemplate ?subjectReference ?predicate ?objectReference ?objectTemplate 
                                        WHERE {
                                            ?tm a rr:TriplesMap ;
                                                rml:logicalSource [ rml:iterator ?iterator ] ;
                                                rr:subjectMap ?sm .
                                            {  { ?sm rr:template ?subjectTemplate } UNION { ?sm rml:reference ?subjectReference } }
                                            OPTIONAL { ?sm rr:class ?targetClass_Position1. }
                                            OPTIONAL {
                                                ?tm rr:predicateObjectMap [rr:predicate <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ;
                                                                            rr:objectMap [rr:constant ?targetClass_Position2] ]. }
                                            OPTIONAL {      
                                                ?tm rr:predicateObjectMap [rr:predicate ?predicate ;
                                                                            rr:objectMap ?om ].
                                            {  { ?om rml:reference ?objectReference } UNION { ?om rr:template ?objectTemplate }} }
                                        }
                                    """, initNs={"rr": self.RR, "rml": self.RML})

    def adjust(self):

        def clearNodeShape(g, sub, shape_list, shape_adjusted = [], targetClass = []):
            if sub in shape_list:
                for s, p, o in g.triples((URIRef(sub), self.SHACL.targetClass, None)):
                    if sub not in shape_adjusted:
                        g.remove((s,p,o))
                # if targetClass != [None]:
                #     for c in targetClass:
                #         g.add((URIRef(sub),self.SHACL.targetClass,URIRef(c)))
                # shape_adjusted.append(sub)
            return g, shape_adjusted

        def clearPropertyShape(g, sub, shape_list, predicate, shape_adjusted = []):
            if sub in shape_list:
                if sub not in shape_adjusted:
                    g.remove((URIRef(sub), self.SHACL.path, None))
                    g.add((URIRef(sub),self.SHACL.path,URIRef(predicate)))
                else:
                    current_path_subject = (sub+"/"+(predicate.split("/")[-1])).replace("//","/")
                    # for s, p, o in g.triples((URIRef(sub), None, None)):
                    #     g.add((URIRef(current_path_subject),p,o))
                    # for s, p, o in g.triples((None, None, URIRef(sub))):
                    #     g.remove((s,p,URIRef(current_path_subject)))
                    g = update_graph(g,[URIRef(sub)],URIRef(current_path_subject))
                    g.remove((URIRef(current_path_subject), self.SHACL.path, None))
                    g.add((URIRef(current_path_subject),self.SHACL.path,URIRef(predicate)))

                if self.correctKind == True:
                    g.remove((URIRef(sub), self.SHACL.datatype, None))
                    g.remove((URIRef(sub), self.SHACL.minLength, None))
                    g.remove((URIRef(sub), self.SHACL.maxLength, None))              
                    g.add((URIRef(sub),self.SHACL.nodeKind,self.SHACL.IRI))          
                shape_adjusted.append(sub)
            return g, shape_adjusted

        shape_list = []
        for s, p, o in self.SHACL_g.triples((None, self.RDF.type, self.SHACL.NodeShape)):
            shape_list.append(str(s))
        for s, p, o in self.SHACL_g.triples((None, self.RDF.type, self.SHACL.PropertyShape)):
            shape_list.append(str(s))


        NStemplate = "http://example.com/NodeShape"
        PStemplate = "http://example.com/PropertyShape"
        shape_adjusted = []
        for mapping_dict in self.mapping_dicts:
            for m in mapping_dict:
                iterator = mapping_dict[m]["iterator"]
                targetClass = mapping_dict[m]["targetClass"]
                poms = mapping_dict[m]["pom"]
                    
                sub = NStemplate+iterator.replace("//","/")
                sub = URIRef(sub)
                self.SHACL_g, shape_adjusted = clearNodeShape(self.SHACL_g, str(sub), shape_list, shape_adjusted = shape_adjusted, targetClass = targetClass)
                self.targetClassAdd = False
                for pom in poms:
                    predicate = pom[0]
                    if predicate == "http://www.w3.org/2000/01/rdf-schema#label" or predicate ==None:
                        continue
                    if pom[2] == "IRI":
                        self.correctKind = True
                    else:
                        self.correctKind = False
                    NS_list = pom[1].split("/")

                    
                    for i in range(len(NS_list)-1):
                        NS_sub = NStemplate+iterator+"/"+"/".join(NS_list[0:i+1])
                        if NS_sub in shape_list:
                            self.targetClassAdd = NS_sub
                            self.SHACL_g, shape_adjusted = clearNodeShape(self.SHACL_g, NS_sub, shape_list, shape_adjusted = shape_adjusted)
                    if self.targetClassAdd != False:
                        shape_adjusted.append(self.targetClassAdd)
                        if targetClass != [None]:
                            for c in targetClass:
                                self.SHACL_g.add((URIRef(self.targetClassAdd),self.SHACL.targetClass,URIRef(c)))
                        self.targetClassAdd = False
                    else:
                        shape_adjusted.append(sub)
                        if targetClass != [None]:
                            for c in targetClass:
                                self.SHACL_g.add((URIRef(sub),self.SHACL.targetClass,URIRef(c)))
                    
                    NS_sub = PStemplate+iterator+"/"+"/".join(NS_list)
                    if NS_sub in shape_list:
                        self.SHACL_g, shape_adjusted = clearPropertyShape(self.SHACL_g, NS_sub, shape_list, predicate, shape_adjusted = shape_adjusted)
        remove_subjects =[URIRef(i) for i in shape_list if i not in shape_adjusted]  
        self.SHACL_g = clear_graph(self.SHACL_g, remove_subjects)
        return self.SHACL_g


        
    
    def loadMapping(self, SHACL_g_path, mapping_path):
        self.SHACL_g = Graph().parse(SHACL_g_path, format="ttl")
        if mapping_path.endswith(".ttl"):
            # Load the mapping file
            print("######Start parsing mapping file: " + mapping_path)
            g = Graph().parse(mapping_path, format="ttl")
            for ns_prefix, namespace in g.namespaces():
                self.SHACL_g.bind(ns_prefix, namespace, False)
            self.parseMapping(g, "yml" in mapping_path)
        else:
            # Load the mapping file from the directory
            for file in os.listdir(mapping_path):
                if file.endswith(".ttl"):
                    print("######Start parsing mapping file: " + file)
                    g = Graph().parse(mapping_path + "/" + file, format="ttl")
                    for ns_prefix, namespace in g.namespaces():
                        self.SHACL_g.bind(ns_prefix, namespace, False)
                    self.parseMapping(g, "yml" in file)
        # print(self.mapping_dicts)
            
    
    def parseMapping(self, g, yarrrml = False):
        mapping_dict = {}
        if yarrrml == True:
            result = g.query(self.query_yarrrml)
            for r in result:
                tm, iterator, targetClass, subjectTemplate, subjectReference, predicate, objectReference, objectTemplate = r
                current = mapping_dict.get(tm, {})

                iterator = str(iterator).split("[")[0]
                current["iterator"] = iterator

                current_targetClass = current.get("targetClass", [])
                if targetClass not in current_targetClass:
                    current_targetClass.append(targetClass)
                current["targetClass"] = current_targetClass
          

                if subjectTemplate is not None and current.get("subject") is None:
                    # subjectTemplate = self.extract_curly_braces_content(iterator, str(subjectTemplate))
                    subjectTemplate = self.extract_curly_braces_content("", str(subjectTemplate))
                    current["subject"] =  subjectTemplate
                    
                elif subjectReference is not None and current.get("subject") is None:
                    # subjectReference = (iterator + "/" + str(subjectReference)).replace("//","/").replace("@","")
                    # subjectReference = str(subjectReference).replace("//","/").replace("@","")
                    subjectReference = self.clearReference(str(subjectReference))
                    current["subject"] =  subjectReference
  

                current_pom  = current.get("pom", [])
                if objectReference is not None:
                    # objectReference = (iterator + "/" + str(objectReference)).replace("//","/").replace("@","")
                    # objectReference = str(objectReference).replace("//","/").replace("@","")
                    objectReference = self.clearReference(str(objectReference))
                    if (predicate, objectReference) not in current_pom:
                        current_pom.append((predicate, objectReference, "Literal"))
                        # self.path_dict["PS"+objectReference] = predicate
                else:
                    # objectTemplate = self.extract_curly_braces_content(iterator, str(objectTemplate))
                    objectTemplate = self.extract_curly_braces_content("", str(objectTemplate))
                    if (predicate, objectTemplate) not in current_pom:
                        current_pom.append((predicate, objectTemplate, "IRI"))
                        # self.path_dict["PS"+objectTemplate] = predicate
                current["pom"] = current_pom
                mapping_dict[tm] = current
        self.mapping_dicts.append(mapping_dict)

    def extractXPath(self):
        if path.startswith("http"):
            return path
        else:
            return path.split("/")[-1]

    def clearIterator(self, iterator):
        return iterator.split('[')[0]

    def clearReference(self, reference):
        matches = reference.split("/")
        matches = [self.clearIterator(match) for match in matches]
        result = "/".join(matches)
        return result.replace("//","/").replace("@","")

    def extract_curly_braces_content(self, iterator, input_string):
        pattern = r'\{([^{}]+)\}'  
        matches = re.findall(pattern, input_string)
        matches = [self.clearIterator(match) for match in matches]
        # result = iterator+"/"+"/".join(matches)
        result = "/".join(matches)
        return result.replace("//","/").replace("@","")


# ADJ = Adjustment()

# rml_path = "usecase\RINF\mappings"
# SHACL_g = Graph().parse("usecase\RINF\RINF-metadata.xsd.shape.ttl", format="ttl")
# ADJ.loadMapping(SHACL_g, rml_path)

# print("####Start adjust SHACL shape")
# SHACL_g = ADJ.adjust(SHACL_g)
# SHACL_g.serialize(destination="adjust2.ttl", format='turtle')

# with open(rml_path+".mapping-dict.json", "w") as outfile:
#     json.dump(mapping_dict, outfile)

# with open(rml_path+".path-dict.json", "w") as outfile:
#     json.dump(path_dict, outfile, indent=4)
