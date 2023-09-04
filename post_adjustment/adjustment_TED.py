import rdflib
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.plugins.sparql import prepareQuery
import os
import re
import json
from utils import clear_graph, update_graph

class Adjustment_TED:
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
        self.FnO_dict = {}
        self.parentTMs = {}


        self.query_yarrrml = prepareQuery("""
                                        SELECT ?tm ?iterator ?targetClass ?subjectTemplate ?subjectReference ?predicate ?objectReference ?objectTemplate ?objectFN ?parentTM ?om ?datatype 
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
                                            {  { ?om rml:reference ?objectReference } UNION { ?om rr:template ?objectTemplate } UNION { ?om <http://semweb.mmlab.be/ns/fnml#functionValue> ?objectFN } UNION { ?om rr:parentTriplesMap ?parentTM }} }
                                            OPTIONAL { ?om rr:datatype ?datatype. }
                                        }
                                    """, initNs={"rr": self.RR, "rml": self.RML})
        self.query_rml = prepareQuery("""
                                        SELECT ?tm ?iterator ?targetClass_Position1 ?targetClass_Position2 ?targetClass_Position3 ?subjectTemplate ?subjectReference ?predicate ?objectReference ?objectTemplate ?objectFN ?parentTM ?om ?datatype
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
                                                ?tm rr:predicateObjectMap [rr:predicate <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ;
                                                                            rr:objectMap [rml:reference ?targetClass_Position3] ]. }
                                            OPTIONAL {      
                                                ?tm rr:predicateObjectMap [rr:predicate ?predicate ;
                                                                            rr:objectMap ?om ].
                                            {  { ?om rml:reference ?objectReference } UNION { ?om rr:template ?objectTemplate } UNION { ?om <http://semweb.mmlab.be/ns/fnml#functionValue> ?objectFN} UNION { ?om rr:parentTriplesMap ?parentTM }} }
                                            OPTIONAL { ?om rr:datatype ?datatype. }
                                        }
                                    """, initNs={"rr": self.RR, "rml": self.RML})

    def parseFunction(self, g):
        RR = Namespace("http://www.w3.org/ns/r2rml#")
        def findFnObject(g,fm,datatype):
            RR = Namespace("http://www.w3.org/ns/r2rml#")
            RML = Namespace("http://semweb.mmlab.be/ns/rml#")
            new_datatype = None
            for pom in g.objects(fm,RR["predicateObjectMap"]):
                for om in g.objects(pom,RR["objectMap"]):
                    for obj in g.objects(om,RML["reference"]):
                        for new_datatype in g.triples((om,RR["datatype"],None)):
                            pass
                        if datatype != None:
                            return (str(obj), "Literal",datatype)
                        return (str(obj), "Literal",new_datatype)
                    for obj in g.objects(om,RR["template"]):
                        for new_datatype in g.triples((om,RR["datatype"],None)):
                            pass
                        if datatype != None:
                            return (str(obj), "IRI",datatype)
                        return (str(obj), "IRI",new_datatype)
                    for obj in g.objects(om,URIRef("http://semweb.mmlab.be/ns/fnml#functionValue")): 
                        for new_datatype in g.triples((om,RR["datatype"],None)):
                            pass
                        if datatype != None:
                            r = findFnObject(g,obj,datatype)
                        else:
                            r = findFnObject(g,obj,new_datatype)
                        return r
        
        for om,_,fm in g.triples((None,URIRef("http://semweb.mmlab.be/ns/fnml#functionValue"),None)):
            d = None
            for _,_,new_datatype in g.triples((om,RR["datatype"],None)):
                d = new_datatype
            obj = findFnObject(g,fm,d)
            if obj:
                if obj[1] == "Literal":
                    objectReference = self.clearReference(obj[0])
                    self.FnO_dict[om] = (objectReference, "Literal",obj[-1])
                elif obj[1] == "IRI":
                    objectTemplate = self.extract_curly_braces_content("", obj[0])
                    self.FnO_dict[om] = (objectTemplate, "IRI",obj[-1])

    def parseParentTM(self, g):
        for parentTM in g.objects(None, self.RR.parentTriplesMap):
            for logicalSource in g.objects(parentTM, self.RML.logicalSource):
                for iterator in g.objects(logicalSource, self.RML.iterator):
                    iterator = self.clearIterator_TED(str(iterator))
                    self.parentTMs[parentTM] = iterator
    
    def adjust(self):

        def clearNodeShape(g, sub, shape_list, shape_adjusted = [], targetClass = []):
            if sub in shape_list:
                for s, p, o in g.triples((sub, self.SHACL.targetClass, None)):
                    if sub not in shape_adjusted:
                        g.remove((s,p,o))

            return g, shape_adjusted

        def clearPropertyShape(g, sub, shape_list, predicate, shape_adjusted = []):
            if sub in shape_list:
                if sub not in shape_adjusted:
                    sub_new = sub
                    g.remove((sub, self.SHACL.path, None))
                    g.add((sub,self.SHACL.path,URIRef(predicate)))
                else:
                    current_path_subject = (str(sub)+"/"+(predicate.split("/")[-1])).replace("//","/")

                    sub_new = URIRef(current_path_subject)
                    g = update_graph(g,[sub],URIRef(current_path_subject))
                    g.remove((URIRef(current_path_subject), self.SHACL.path, None))
                    g.add((URIRef(current_path_subject),self.SHACL.path,URIRef(predicate)))
                
                if self.correctKind != False:
                    
                    # g.remove((sub_new, self.SHACL.datatype, None))
                    # g.remove((sub_new, self.SHACL.minLength, None))
                    # g.remove((sub_new, self.SHACL.maxLength, None))   
                    g.remove((sub_new, self.SHACL.nodeKind, None))           
                    g.add((sub_new,self.SHACL.nodeKind,self.correctKind))    

                if self.datatype != False:
                    g.remove((sub_new, self.SHACL.datatype, None))
                    g.add((sub_new,self.SHACL.datatype,self.datatype))
                     
                shape_adjusted.append(sub_new)
            return g, shape_adjusted

        def addExtraPS(g, predicate):
            sub = URIRef("http://example.com/PropertyShape/Extra/"+str(predicate).split("/")[-1])
            g.add((sub,self.RDF.type,self.SHACL.PropertyShape))
            g.add((sub,self.SHACL.path,URIRef(predicate)))
            if self.correctKind != False:
                g.add((sub,self.SHACL.nodeKind,self.correctKind))
            if self.datatype != False:
                g.add((sub,self.SHACL.datatype,self.datatype))
            g.add((sub,self.SHACL.minCount,Literal(1)))
            shape_adjusted.append(sub)
            self.addExtraPS = sub
            return g, shape_adjusted

        shape_list = []
        for s, p, o in self.SHACL_g.triples((None, self.RDF.type, self.SHACL.NodeShape)):
            shape_list.append(s)
        for s, p, o in self.SHACL_g.triples((None, self.RDF.type, self.SHACL.PropertyShape)):
            shape_list.append(s)


        NStemplate = "http://example.com/NodeShape"
        PStemplate = "http://example.com/PropertyShape"
        shape_adjusted = []
        for mapping_dict in self.mapping_dicts:
            for m in mapping_dict:
                for iterator in mapping_dict[m]["iterator"]:
                    targetClass = mapping_dict[m]["targetClass"]
                    poms = mapping_dict[m]["pom"]
                        
                    sub = NStemplate+iterator.replace("//","/").split("/")[-1]
                    sub = URIRef(sub)
                    self.SHACL_g, shape_adjusted = clearNodeShape(self.SHACL_g, sub, shape_list, shape_adjusted = shape_adjusted, targetClass = targetClass)
                    self.targetClassAdd = False
                    self.addExtraPS = False
                    self.datatype = False
                    if poms != []:
                        for pom in poms:
                            # iterator = mapping_dict[m]["iterator"]
                            predicate = pom[0]
                            if predicate == "http://www.w3.org/2000/01/rdf-schema#label" or predicate ==None:
                                continue
                            if pom[2] == "IRI":
                                self.correctKind = self.SHACL.IRI
                            elif pom[2] == "Literal":
                                self.correctKind = self.SHACL.Literal
                            else:
                                self.correctKind = False
                            if pom[1].startswith("ParentTM"):
                                p = pom[1].split("ParentTM")[-1].split("/")
                                iterator = ""
                            else:
                                p = pom[1].split("/")

                            NS_list = iterator.split("/")
                            NS_list.extend(p)

                            if pom[3] != None:
                                self.datatype = pom[3]
                            else:
                                self.datatype = False

                            # NS_sub = URIRef(PStemplate+iterator+"/"+"/".join(NS_list))
                            propertyFind = False
                            NS_sub = URIRef(PStemplate+iterator+"/"+NS_list[-1])
                            for i in range(len(p)+1):
                                if URIRef(PStemplate+iterator+"/"+"/".join(p[i:])) in shape_list:
                                    NS_sub = URIRef(PStemplate+iterator+"/"+"/".join(p[i:]))
                            if NS_sub in shape_list:
                                self.SHACL_g, shape_adjusted = clearPropertyShape(self.SHACL_g, NS_sub, shape_list, predicate, shape_adjusted = shape_adjusted)
                            else:
                                self.SHACL_g, shape_adjusted = addExtraPS(self.SHACL_g, predicate)


                            # For finding the minimum node shape to add targetClass 
                            for i in range(len(NS_list)):
                                NS_sub = URIRef(NStemplate+"/"+NS_list[i])
                                if NS_sub in shape_list:
                                    self.targetClassAdd = URIRef(NS_sub)
                                    self.SHACL_g, shape_adjusted = clearNodeShape(self.SHACL_g, NS_sub, shape_list, shape_adjusted = shape_adjusted)
                            if self.targetClassAdd != False:
                                shape_adjusted.append(self.targetClassAdd)
                                if targetClass != [None]:
                                    for c in targetClass:
                                        self.SHACL_g.add((URIRef(self.targetClassAdd),self.SHACL.targetClass,URIRef(c)))
                                if self.addExtraPS != False:
                                    self.SHACL_g.add((URIRef(self.targetClassAdd),self.SHACL.property,self.addExtraPS))
                                    self.addExtraPS = False
                                self.targetClassAdd = False
                            else:
                                self.SHACL_g, shape_adjusted = clearNodeShape(self.SHACL_g, sub, shape_list, shape_adjusted = shape_adjusted)
                                shape_adjusted.append(sub)
                                if targetClass != [None]:
                                    for c in targetClass:
                                        self.SHACL_g.add((URIRef(sub),self.SHACL.targetClass,URIRef(c)))
                                if self.addExtraPS != False:
                                    self.SHACL_g.add((URIRef(sub),self.SHACL.property,self.addExtraPS))
                                    self.addExtraPS = False

                    else:
                        #iterator = mapping_dict[m]["iterator"]
                        NS_list = iterator.split("/")
                        # For finding the minimum node shape to add targetClass 
                        for i in range(len(NS_list)):
                            NS_sub = URIRef(NStemplate+"/"+NS_list[i])
                            if NS_sub in shape_list:
                                self.targetClassAdd = URIRef(NS_sub)
                                self.SHACL_g, shape_adjusted = clearNodeShape(self.SHACL_g, NS_sub, shape_list, shape_adjusted = shape_adjusted)
                        if self.targetClassAdd != False:
                            shape_adjusted.append(self.targetClassAdd)
                            if targetClass != [None]:
                                for c in targetClass:
                                    try:
                                        self.SHACL_g.add((URIRef(self.targetClassAdd),self.SHACL.targetClass,URIRef(c)))
                                    except:
                                        print("targetClass: ",targetClass)
                                        print("cannot add targetClass: ",c)
                            self.targetClassAdd = False
        
        for s, p, o in self.SHACL_g.triples((None, self.RDF.nodeKind, self.SHACL.IRI)):
            g.remove((s, self.SHACL.datatype, None))
            g.remove((s, self.SHACL.minLength, None))
            g.remove((s, self.SHACL.maxLength, None))    

        
        remove_subjects =[i for i in shape_list if i not in shape_adjusted]  
        self.SHACL_g = clear_graph(self.SHACL_g, remove_subjects)
        return self.SHACL_g
        
    
    def loadMapping(self, SHACL_g_path, mapping_path):
        self.SHACL_g = Graph().parse(SHACL_g_path, format="ttl")
        if isinstance(mapping_path, list):
            g = Graph()
            for p in mapping_path:
                # Load the mapping file
                print("######Start parsing mapping file: " + p)
                g.parse(p, format="ttl")
                for ns_prefix, namespace in g.namespaces():
                    self.SHACL_g.bind(ns_prefix, namespace, False)
            self.parseParentTM(g)
            self.parseFunction(g)
            self.parseMapping(g, "yml" in p)
        elif mapping_path.endswith(".ttl"):
            # Load the mapping file
            print("######Start parsing mapping file: " + mapping_path)
            g = Graph().parse(mapping_path, format="ttl")
            for ns_prefix, namespace in g.namespaces():
                self.SHACL_g.bind(ns_prefix, namespace, False)
            self.parseParentTM(g)
            self.parseFunction(g)
            self.parseMapping(g, "yml" in mapping_path)
        else:
            # Load the mapping file from the directory
            for file in os.listdir(mapping_path):
                if file.endswith(".ttl"):
                    print("######Start parsing mapping file: " + file)
                    g = Graph().parse(mapping_path + "/" + file, format="ttl")
                    for ns_prefix, namespace in g.namespaces():
                        self.SHACL_g.bind(ns_prefix, namespace, False)
                    self.parseParentTM(g)
                    self.parseFunction(g)
                    self.parseMapping(g, "yml" in file)
        # print(self.mapping_dicts)
        # print(self.FnO_dict)
            
    
    def parseMapping(self, g, yarrrml = False):
        mapping_dict = {}
        if yarrrml == True:
            result = g.query(self.query_yarrrml)
            for r in result:
                tm, iterator, targetClass, subjectTemplate, subjectReference, predicate, objectReference, objectTemplate, objectFN, parentTM, om, datatype = r
                current = mapping_dict.get(tm, {})
                
                iterator = str(iterator).split("[")[0]
                current["iterator"] = self.clearIterator_TED(iterator)

                current_targetClass = current.get("targetClass", [])
                if targetClass not in current_targetClass:
                    current_targetClass.append(targetClass)
                current["targetClass"] = current_targetClass
          

                if subjectTemplate is not None and current.get("subject") is None:
                    subjectTemplate = self.extract_curly_braces_content("", str(subjectTemplate))
                    current["subject"] =  subjectTemplate
                    
                elif subjectReference is not None and current.get("subject") is None:
                    subjectReference = self.clearReference(str(subjectReference))
                    current["subject"] =  subjectReference
  

                current_pom  = current.get("pom", [])
                if objectReference is not None:

                    objectReference = self.clearReference(str(objectReference))
                    if (predicate, objectReference, "Literal", datatype) not in current_pom:
                        current_pom.append((predicate, objectReference, "Literal",datatype))
 
                elif objectTemplate is not None:

                    objectTemplate = self.extract_curly_braces_content("", str(objectTemplate))
                    if (predicate, objectTemplate, "IRI",datatype) not in current_pom:
                        current_pom.append((predicate, objectTemplate, "IRI",datatype))
   
                elif objectFN is not None:
                    if om:
                        objectFN = self.FnO_dict.get(om, None)
                        if objectFN:
                            if (predicate, objectFN[0], objectFN[1],objectFN[-1]) not in current_pom:
                                current_pom.append((predicate, objectFN[0], objectFN[1],objectFN[-1]))

                if parentTM is not None:
                    for parentTM in self.parentTMs.get(parentTM, []):
                        parentTM = "ParentTM"+parentTM
                        if (predicate, parentTM, "IRI", None) not in current_pom:
                            current_pom.append((predicate, parentTM, "IRI", None))

                current["pom"] = current_pom
                mapping_dict[tm] = current

        else:
            result = g.query(self.query_rml)
            for r in result:
                tm, iterator, targetClass, targetClass2, targetClass3, subjectTemplate, subjectReference, predicate, objectReference, objectTemplate, objectFN, parentTM, om, datatype = r
                current = mapping_dict.get(tm, {})
                
                iterator = str(iterator).split("[")[0]
                current["iterator"] = self.clearIterator_TED(iterator)

                current_targetClass = current.get("targetClass", [])
                if targetClass not in current_targetClass and targetClass != None:
                    current_targetClass.append(targetClass)
                if targetClass3 is not None and "if" in targetClass3:
                    url_pattern = r"http://[^']*"
                    url = re.findall(url_pattern, targetClass3)
                    for c in url:
                        if URIRef(c) not in current_targetClass:
                            current_targetClass.append(URIRef(c))
                if targetClass2 not in current_targetClass and targetClass2 != None:
                    current_targetClass.append(targetClass2)
                current["targetClass"] = current_targetClass
          

                if subjectTemplate is not None and current.get("subject") is None:
                    subjectTemplate = self.extract_curly_braces_content("", str(subjectTemplate))
                    current["subject"] =  subjectTemplate
                    
                elif subjectReference is not None and current.get("subject") is None:
                    subjectReference = self.clearReference(str(subjectReference))
                    current["subject"] =  subjectReference
  

                current_pom  = current.get("pom", [])
                if objectReference is not None:
                    if "|" in objectReference:
                        for objectRef in objectReference.split("|"):
                            objectRef = self.clearReference(objectRef.strip())
                            if (predicate, objectRef, "Literal", datatype) not in current_pom:
                                current_pom.append((predicate, objectRef, "Literal", datatype))
                    else:
                        objectReference = self.clearReference(str(objectReference))
                        if (predicate, objectReference, "Literal", datatype) not in current_pom:
                            current_pom.append((predicate, objectReference, "Literal",datatype))
 
                elif objectTemplate is not None:
                    if "|" in objectTemplate:
                        for objectTemp in objectTemplate.split("|"):
                            objectTemp = self.extract_curly_braces_content("", str(objectTemp.strip()))
                            if (predicate, objectTemp, "IRI",datatype) not in current_pom:
                                current_pom.append((predicate, objectTemp, "IRI",datatype))
                    else:
                        objectTemplate = self.extract_curly_braces_content("", str(objectTemplate))
                        if (predicate, objectTemplate, "IRI",datatype) not in current_pom:
                            current_pom.append((predicate, objectTemplate, "IRI",datatype))
   
                elif objectFN is not None:
                    if om:
                        objectFN = self.FnO_dict.get(om, None)
                        if objectFN:
                            if (predicate, objectFN[0], objectFN[1],objectFN[-1]) not in current_pom:
                                current_pom.append((predicate, objectFN[0], objectFN[1],objectFN[-1]))

                if parentTM is not None:
                    for parentTM in self.parentTMs.get(parentTM, []):                     
                        parentTM = "ParentTM"+parentTM
                        if (predicate, parentTM, "IRI", None) not in current_pom:
                            current_pom.append((predicate, parentTM, "IRI", None))

                current["pom"] = current_pom
                mapping_dict[tm] = current

        self.mapping_dicts.append(mapping_dict)

    def clearIterator_TED(self, iterator):
        iterators = []
        if "|" in iterator:
            iterators = [i.strip() for i in iterator.split("|")]
        else:
            iterators = [iterator]
        iterators = ["/".join([r.split('[')[0].split('(')[0].split("*")[0] for r in result.split("/")]) for result in iterators]
        return iterators

    def clearReference(self, reference):
        reference = reference.split("then")[-1].strip().split("else")[0].strip()
        reference = reference.split("replace(")[-1].strip().split(",")[0].strip()
        matches = reference.split("/")
        matches = [r.split('[')[0].split('(')[0].split("*")[0] for r in matches]
        matches = [r for r in matches if "parent:" not in r]
        matches = [r for r in matches if "ancestor:" not in r]
        result = "/".join(matches)
        return result.replace("//","/").replace("@","")

    def extract_curly_braces_content(self, iterator, input_string):
        input_string = input_string.split("then")[-1].strip().split("else")[0].strip()
        input_string = input_string.split("replace(")[-1].strip().split(",")[0].strip()
        pattern = r'\{([^{}]+)\}'  
        matches = re.findall(pattern, input_string)
        matches = [self.clearIterator(match) for match in matches]
        matches = [i for i in matches if "parent:" not in i]
        matches = [i for i in matches if "ancestor:" not in i]
        # result = iterator+"/"+"/".join(matches)
        result = "/".join(matches)
        return result.replace("//","/").replace("@","")

    def extractXPath(self):
        if path.startswith("http"):
            return path
        else:
            return path.split("/")[-1].split("*")[0]


    def clearIterator(self, iterator):
        result = iterator.split("/")
        return "/".join([r.split('[')[0].split('(')[0].split("*")[0] for r in result])



