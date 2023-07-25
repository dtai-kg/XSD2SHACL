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
        self.translatedShapes = {}


    def transRestriction(self,name,value,subject):

        if "type" in name or "restriction" in name:
            if value.split(":")[1] in self.type_list:
                p = self.shaclNS.datatype
                #o = rdflib.Namespace(self.xsdNSdict[value.split(":")[0]])[value.split(":")[1]]
                o = self.xsdNS[value.split(":")[1]]
                self.SHACL.add((subject,p,o))
                # return g
        elif "default" in name:
            p = self.shaclNS.defaultValue
            o = Literal(value)
            self.SHACL.add((subject,p,o))
            # return g
        elif "fixed" in name:
            p = self.shaclNS.hasValue
            o = Literal(value)
            self.SHACL.add((subject,p,o))
            # return g
        elif "pattern" in name:
            p = self.shaclNS.pattern
            o = Literal(value)
            self.SHACL.add((subject,p,o))
            return g
        elif "maxExclusive" in name:
            p = self.shaclNS.maxExclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g     
        elif "minExclusive" in name:
            p = self.shaclNS.minExclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g     
        elif "maxInclusive" in name:
            p = self.shaclNS.maxInclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g   
        elif "minInclusive" in name:
            p = self.shaclNS.minInclusive
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g
        elif "length" in name:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            p = self.shaclNS.maxLength
            o = rdflib.Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g
        elif "minLength" in name:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g
        elif "maxLength" in name:        
            p = self.shaclNS.minLength
            o = Literal(int(value))
            self.SHACL.add((subject,p,o))
            # return g

        # return g

    def transEnumeration(self, xsd_element, subject):
        values = []
        for e in xsd_element.findall('.//xs:enumeration',self.xsdNSdict):
            if e.get("value"):
                values.append(e.get("value"))
        if values == []:
            return None
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
            # return g

    def transComplexType(self, xsd_element):
        """
        Input: xs:complexType
        Output: SHACL node shape 
        """

        element_name = xsd_element.get("name")
        # element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        # element_max_occurs = Literal(int(xsd_element.get("maxOccurs", "1")))
        subject = self.NS[f'NodeShape/{element_name}']
        self.translatedShapes[subject] = subject

        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        for child in xsd_element.findall('.//*xs:element',self.xsdNSdict):
            # sub_subject = self.transEleAttSimple(child)
            sub_subject = self.translatedShapes.get(self.NS[f'PropertyShape/{child.get("name")}'],self.transEleAttSimple(child))
            self.SHACL.add((subject,self.shaclNS.property,sub_subject))
        return subject

    def transEleComplex(self, xsd_element):
        """
        Input: xs:element with ComplexType
        Output: SHACL Node Shape with sh:targetSubjectOf and sh:targetClass
        """
        element_name = xsd_element.get("name")
        element_type = xsd_element.get("type")
        # element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        # element_max_occurs = Literal(int(xsd_element.get("maxOccurs", "1")))
        subject = self.NS[f'NodeShape/{element_name}']
        self.translatedShapes[subject] = subject

        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        # self.SHACL.add((subject,self.shaclNS.minCount,element_min_occurs))
        # self.SHACL.add((subject,self.shaclNS.maxCount,element_max_occurs))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        if self.translatedShapes.get(self.NS[f'NodeShape/{element_type}']):
            subject = self.NS[f'NodeShape/{element_type}']
            self.SHACL.add((subject,self.shaclNS.node,sub_subject))
        else:
            sub_root = self.root.find(f'.//xs:complexType[@name="{element_type}"]',self.xsdNSdict)
            sub_subject = self.transComplexType(sub_root)
            self.SHACL.add((subject,self.shaclNS.node,sub_subject))

    def transEleAttSimple(self, xsd_element):
        """
        Input: xs:element with simpleType/Built-in type/restriction OR xs:attribute with simpleType/Built-in type/restriction
        Output: SHACL property shape with sh:targetSubjectOf and sh:path
        """
        # g = Graph()

        element_name = xsd_element.get("name")
        element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        element_max_occurs = Literal(int(xsd_element.get("maxOccurs", "1")))
        subject = self.NS[f'PropertyShape/{element_name}']
        self.translatedShapes[subject] = subject

        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        self.SHACL.add((subject,self.shaclNS.targetSubjectsOf,self.xsdTargetNS[element_name]))
        self.SHACL.add((subject,self.shaclNS.minCount,element_min_occurs))
        self.SHACL.add((subject,self.shaclNS.maxCount,element_max_occurs))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        element_type = xsd_element.get("type")
        if element_type and ":" in element_type:
            for name in xsd_element.attrib:
                # g = self.transRestriction(name, xsd_element.attrib[name], g, subject)
                self.transRestriction(name, xsd_element.attrib[name], subject)
        else:
            if element_type in self.type_dict:
                sub_root = self.root.find(f'.//xs:simpleType[@name="{element_type}"]',self.xsdNSdict)
            elif element_type == None:
                sub_root = xsd_element.find(f'.//xs:simpleType',self.xsdNSdict)
            # g = self.transEnumeration(sub_root, g, subject)
            self.transEnumeration(sub_root, subject)
            
            for child in sub_root.findall('.//*'):
                for value in child.attrib.values():
                    # g = self.transRestriction(child.tag, value, g, subject)
                    self.transRestriction(child.tag, value, subject)

        return subject

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
        # sub_root = self.root.find(f'.//xs:element[@name="quantity"]',self.xsdNSdict)
        sub_root = self.root.find(f'.//xs:attribute[@name="country"]',self.xsdNSdict)
        # g = self.transEleAttSimple(sub_root)
        # self.transEleAttSimple(sub_root)
        # g = self.transEleAttSimple(self.root[1])

        # self.transComplexType(self.root[3])
        self.transEleComplex(self.root[0])
        print(self.SHACL.serialize(format="turtle"))
        

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