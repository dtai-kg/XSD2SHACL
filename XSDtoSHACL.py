import xml.etree.ElementTree as ET
import rdflib
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
import pyshacl


class XSDtoSHACL:
    def __init__(self):
        # self.xsdTree = 
        self.shaclNS = rdflib.Namespace('http://www.w3.org/ns/shacl#')
        self.rdfSyntax = rdflib.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        self.xsdNS = rdflib.Namespace('http://www.w3.org/2001/XMLSchema#')
        self.xsdTargetNS = xsdTargetNS = rdflib.Namespace('http://example.com/')
        self.NS = rdflib.Namespace('http://example.com/')
        self.xsdNSdict = dict()
        self.type_list = ['string', 'normalizedString', 'token', 'base64Binary', 'hexBinary', 'integer', 'positiveInteger', 'negativeInteger', 'nonNegativeInteger', 'nonPositiveInteger', 'long', 'unsignedLong', 'int', 'unsignedInt', 'short', 'unsignedShort', 'byte', 'unsignedByte', 'decimal', 'float', 'double', 'boolean', 'duration', 'dateTime', 'date', 'time', 'gYear', 'gYearMonth', 'gMonth', 'gMonthDay', 'gDay', 'Name', 'QName', 'NCName', 'anyURI', 'language', 'ID', 'IDREF', 'IDREFS', 'ENTITY', 'ENTITIES', 'NOTATION', 'NMTOKEN', 'NMTOKENS']
        # self.SHACL = SHACL()
        self.SHACL = Graph()


    def transRestriction(self,name,value,g,subject):

        if "type" in name or "restriction" in name:
            if value.split(":")[1] in self.type_list:
                p = self.shaclNS.datatype
                #o = rdflib.Namespace(self.xsdNSdict[value.split(":")[0]])[value.split(":")[1]]
                o = self.xsdNS[value.split(":")[1]]
                g.add((subject,p,o))
                return g
        elif "default" in name:
            p = self.shaclNS.defaultValue
            o = Literal(value)
            g.add((subject,p,o))
            return g
        elif "fixed" in name:
            p = self.shaclNS.hasValue
            o = Literal(value)
            g.add((subject,p,o))
            return g
        elif "pattern" in name:
            p = self.shaclNS.pattern
            o = Literal(value)
            g.add((subject,p,o))
            return g
        elif "maxExclusive" in name:
            p = self.shaclNS.maxExclusive
            o = Literal(int(value))
            g.add((subject,p,o))
            return g     
        elif "minExclusive" in name:
            p = self.shaclNS.minExclusive
            o = Literal(int(value))
            g.add((subject,p,o))
            return g     
        elif "maxInclusive" in name:
            p = self.shaclNS.maxInclusive
            o = Literal(int(value))
            g.add((subject,p,o))
            return g   
        elif "minInclusive" in name:
            p = self.shaclNS.minInclusive
            o = Literal(int(value))
            g.add((subject,p,o))
            return g
        elif "length" in name:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            g.add((subject,p,o))
            p = self.shaclNS.maxLength
            o = rdflib.Literal(int(value))
            g.add((subject,p,o))
            return g
        elif "minLength" in name:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            g.add((subject,p,o))
            return g
        elif "maxLength" in name:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            g.add((subject,p,o))
            return g

        return g

    def transEnumeration(self, xsd_element, g, subject):
        values = []
        for e in xsd_element.findall('.//xs:enumeration',self.xsdNSdict):
            if e.get("value"):
                values.append(e.get("value"))
        if values == []:
            return g
        else:
            current_BN = BNode()
            g.add((subject, self.shaclNS["in"], current_BN))
            for index in range(len(values))[0:-1]:
                g.add((current_BN, RDF.first, Literal(values[index]))) 
                next_BN = BNode()
                g.add((current_BN, RDF.rest, next_BN)) 
                current_BN = next_BN

            g.add((current_BN, RDF.first, Literal(values[-1]))) 
            g.add((current_BN, RDF.rest, RDF.nil)) 
            return g



    def transEleSimple(self, xsd_element):
        """
        Input: xs:element with simpleType/Built-in type/restriction
        Output: SHACL property shape with sh:targetSubjectOf and sh:path
        """
        g = Graph()

        element_name = xsd_element.get("name")
        element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        element_max_occurs = Literal(int(xsd_element.get("maxOccurs", "1")))
        subject = self.NS[f'shape/{element_name}']

        g.add((subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        g.add((subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        g.add((subject,self.shaclNS.targetSubjectsOf,self.xsdTargetNS[element_name]))
        g.add((subject,self.shaclNS.minCount,element_min_occurs))
        g.add((subject,self.shaclNS.maxCount,element_max_occurs))
        g.add((subject,self.shaclNS.name,Literal(element_name)))

        element_type = xsd_element.get("type")
        if element_type and ":" in element_type:
            for name in xsd_element.attrib:
                g = self.transRestriction(name, xsd_element.attrib[name], g, subject)
            #g = self.transRestriction("type",element_type,g,subject)
        else:
            if element_type in self.type_dict:
                sub_root = self.root.find(f'.//xs:simpleType[@name="{element_type}"]',self.xsdNSdict)
            elif element_type == None:
                sub_root = xsd_element.find(f'.//xs:simpleType',self.xsdNSdict)
            g = self.transEnumeration(sub_root, g, subject)
            
            for child in sub_root.findall('.//*'):
                for value in child.attrib.values():
                    g = self.transRestriction(child.tag, value, g, subject)

        return g


    def evaluate_file(self, xsd_file):
        self.xsdTree = ET.parse(xsd_file)
        self.root = self.xsdTree.getroot()

        self.xsdNSdict = dict([node for (_, node) in ET.iterparse(xsd_file, events=['start-ns'])])

        for key in self.root.attrib:
            if key == "targetNamespace":
                self.xsdTargetNS = Namespace(self.root.attrib[key])
    
        self.type_dict = {}
        for e in self.root.findall('.//xs:simpleType',self.xsdNSdict):
            if e.get("name"):
                self.type_dict[e.get("name")] = "simpleType"
        for e in self.root.findall('.//xs:complexType',self.xsdNSdict):
            if e.get("name"):
                self.type_dict[e.get("name")] = "complexType"

        # element_type = "SKU"
        # sub_root = self.root.find(f'.//xs:element[@name="quantity"]',XSDNS2)

        element_type = "SKU"
        sub_root = self.root.find(f'.//xs:element[@name="quantity"]',self.xsdNSdict)
        # g = self.transEleSimple(sub_root)
        g = self.transEleSimple(self.root[1])
        print(g.serialize(format="turtle"))
        

        # for _, triples_map in self.RML.tm_model_dict.items():
        #     subject_shape_node = self.createNodeShape(triples_map, self.SHACL.graph)

        #     for pom in triples_map.poms:
        #         self.transformPOM(subject_shape_node, pom, self.SHACL.graph)

        # outputfileName = f"{rml_mapping_file}-output-shape.ttl"
        # self.writeShapeToFile(outputfileName)

        # validation_shape_graph = rdflib.Graph()
        # validation_shape_graph.parse("shacl-shacl.ttl", format="turtle")

        # self.SHACL.Validation(validation_shape_graph, self.SHACL.graph)

        return None

X2S = XSDtoSHACL()
X2S.evaluate_file("xsd.example.xml")