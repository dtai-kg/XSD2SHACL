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
        #self.extension = False
        self.enumerationShapes = []
        self.choiceShapes = []
        self.order_list = []
        self.backUp = None
        self.processed_files = []

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
            xsd_type = xsd_type.split(":")[-1]
            elements = self.root.findall(f".//*[@name='{xsd_type}']", self.xsdNSdict)
            # can't combine both conditions as xmltree doesn't support the full xpath syntax
            # sometimes, some elements are named after their type, we need to find the element that contains the type definition
            # that means we need to find the complexType or the simpleType element with that name
            child = next((e for e in elements if ("complexType" in e.tag or "simpleType" in e.tag)), None)

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
            o = Literal(value)
            bn = BNode()
            self.SHACL.add((subject,p,bn))
            self.SHACL.add((bn,RDF.first,o))
            self.SHACL.add((bn,RDF.rest,RDF.nil))

        elif "pattern" in tag:
            p = self.shaclNS.pattern
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "maxExclusive" in tag:
            p = self.shaclNS.maxExclusive
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "minExclusive" in tag:
            p = self.shaclNS.minExclusive
            o = Literal(value)
            self.SHACL.add((subject,p,o))
  
        elif "maxInclusive" in tag:
            p = self.shaclNS.maxInclusive
            o = Literal(value)
            self.SHACL.add((subject,p,o))

        elif "minInclusive" in tag:
            p = self.shaclNS.minInclusive
            o = Literal(value)
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
            if "NodeShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("NodeShape/")[1]
            elif "PropertyShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("PropertyShape/")[1]
            if "attribute" in xsd_element.tag:
                subject = self.NS[f'PropertyShape/{pre_subject_path}/@{element_name}']
            else:
                subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
            if subject not in self.choiceShapes:
                self.SHACL.add((self.shapes[-1],self.shaclNS.property,subject))
        
        self.transAnnotation(xsd_element,subject)
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        # self.SHACL.add((subject,self.shaclNS.targetSubjectsOf,self.xsdTargetNS[element_name]))
        if "attribute" not in xsd_element.tag:
            element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
            self.SHACL.add((subject,self.shaclNS.minCount,element_min_occurs))
            element_max_occurs = xsd_element.get("maxOccurs", "1")
            if element_max_occurs != "unbounded" and (isinstance(element_max_occurs, int) or isinstance(element_max_occurs, str)):
                element_max_occurs = Literal(int(element_max_occurs))    
                self.SHACL.add((subject,self.shaclNS.maxCount,element_max_occurs))          

        elif xsd_element.get("use") == "required":
            self.SHACL.add((subject,self.shaclNS.minCount,Literal(1)))
            self.SHACL.add((subject,self.shaclNS.maxCount,Literal(1)))
        elif xsd_element.get("use") == "optional":
            self.SHACL.add((subject,self.shaclNS.minCount,Literal(0)))
            self.SHACL.add((subject,self.shaclNS.maxCount,Literal(1)))
        elif xsd_element.get("use") == "prohibited":
            self.SHACL.add((subject,self.shaclNS.minCount,Literal(0)))
            self.SHACL.add((subject,self.shaclNS.maxCount,Literal(0)))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))

        if self.order_list != []:
            self.SHACL.add((subject,self.shaclNS.order,Literal(self.order_list.pop())))

        for name in xsd_element.attrib:
            self.transRestriction(name, xsd_element.attrib[name])

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
            if "NodeShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("NodeShape/")[1]
            elif "PropertyShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("PropertyShape/")[1]
            subject = self.NS[f'NodeShape/{pre_subject_path}/{element_name}']
            ps_subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
            if subject not in self.choiceShapes:
                self.SHACL.add((self.shapes[-1],self.shaclNS.node,subject))

        self.transAnnotation(xsd_element,subject)
        self.shapes.append(subject)
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        
        self.SHACL.add((subject,self.shaclNS.nodeKind,self.shaclNS.IRI))
        self.SHACL.add((subject,self.shaclNS.targetClass,self.xsdTargetNS[element_name]))

        """Uncomment this if you want to add one more Property Shape for complex element which will be translated to Node Shape"""
        # self.SHACL.add((subject,self.shaclNS.property,ps_subject))
        # self.SHACL.add((ps_subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        # self.SHACL.add((ps_subject,self.shaclNS.name,Literal(element_name)))
        # self.SHACL.add((ps_subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        # element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        # self.SHACL.add((ps_subject,self.shaclNS.minCount,element_min_occurs))
        # element_max_occurs = xsd_element.get("maxOccurs", "1")
        # if element_max_occurs != "unbounded" and (isinstance(element_max_occurs, int) or isinstance(element_max_occurs, str)):
        #     element_max_occurs = Literal(int(element_max_occurs))    
        #     self.SHACL.add((ps_subject,self.shaclNS.maxCount,element_max_occurs))
    

        for name in xsd_element.attrib:
            if "type" not in name:
                self.transRestriction(name, xsd_element.attrib[name], ps_subject)

        element_type = xsd_element.get("type")
        if element_type != None:
            self.SHACL.add((subject,self.shaclNS.node,self.NS[f'NodeShape/{element_type}'])) #Will be translated later

        return xsd_element

    def transEleComplexSimpleContent(self,xsd_element):
        """A function to translate XSD element with complex type simple Content to SHACL node shape"""
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        ps_subject = self.NS[f'PropertyShape/{element_name}']

        if self.shapes != []:
            if "NodeShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("NodeShape/")[1]
            elif "PropertyShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("PropertyShape/")[1]
            subject = self.NS[f'NodeShape/{pre_subject_path}/{element_name}']
            ps_subject = self.NS[f'PropertyShape/{pre_subject_path}/{element_name}']
            if subject not in self.choiceShapes:
                self.SHACL.add((self.shapes[-1],self.shaclNS.node,subject))

        self.transAnnotation(xsd_element,subject)
        self.shapes.append(subject)
        # self.shapes.append(ps_subject)
        # self.simpleContent = subject
        #self.extension = True
        self.SHACL.add((subject,self.rdfSyntax['type'],self.shaclNS.NodeShape))
        self.SHACL.add((subject,self.shaclNS.name,Literal(element_name)))
        
        self.SHACL.add((subject,self.shaclNS.nodeKind,self.shaclNS.IRI))
        self.SHACL.add((subject,self.shaclNS.targetClass,self.xsdTargetNS[element_name]))

        # Add one more property shape
        self.SHACL.add((subject,self.shaclNS.property,ps_subject))
        self.SHACL.add((ps_subject,self.rdfSyntax['type'],self.shaclNS.PropertyShape))
        self.SHACL.add((ps_subject,self.shaclNS.name,Literal(element_name)))
        self.SHACL.add((ps_subject,self.shaclNS.path,self.xsdTargetNS[element_name]))
        element_min_occurs = Literal(int(xsd_element.get("minOccurs", "1")))
        self.SHACL.add((ps_subject,self.shaclNS.minCount,element_min_occurs))
        element_max_occurs = xsd_element.get("maxOccurs", "1")
        if element_max_occurs != "unbounded" and (isinstance(element_max_occurs, int) or isinstance(element_max_occurs, str)):
            element_max_occurs = Literal(int(element_max_occurs))    
            self.SHACL.add((ps_subject,self.shaclNS.maxCount,element_max_occurs))
    

        for name in xsd_element.attrib:
            if "type" not in name:
                self.transRestriction(name, xsd_element.attrib[name], ps_subject)
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
                        next_node = self.root.find(f'.//{{http://www.w3.org/2001/XMLSchema}}simpleType[@name="{type_name}"]')
                        # redirect current process to the next root (simple type)
                        return next_node 
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

    def transComplexType(self,xsd_element):
        """A function to translate XSD complex type to SHACL node shape""" 
        element_name = xsd_element.get("name")
        subject = self.NS[f'NodeShape/{element_name}']
        if self.shapes != []:
            if "NodeShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("NodeShape/")[1]
            elif "PropertyShape" in str(self.shapes[-1]):
                pre_subject_path = self.shapes[-1].split("PropertyShape/")[1]
            subject = subject = self.NS[f'NodeShape/{pre_subject_path}/{element_name}']
            # To solve that it is the child node of any element
            if subject not in self.choiceShapes:
                self.SHACL.add((self.shapes[-1],self.shaclNS.node,subject))

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

    def transChoice(self, xsd_element):

        values = []
        subject = self.shapes[-1]
        if "NodeShape" in str(subject):
            pre_subject_path = subject.split("NodeShape/")[1]
        elif "PropertyShape" in str(subject):
            pre_subject_path = subject.split("PropertyShape/")[1]

        for child in xsd_element.findall("./"):
            tag = child.tag
            if "element" in tag:
                element_type = self.isSimpleComplex(child)
                if element_type == 0:
                    # values.append(self.NS[f'PropertyShape/{child.get("name")}'])
                    temp = self.NS[f'PropertyShape/{pre_subject_path}/{child.get("name")}']
                    values.append(temp)
                else:
                    # values.append(self.NS[f'NodeShape/{child.get("name")}'])
                    temp = self.NS[f'NodeShape/{pre_subject_path}/{child.get("name")}']
                    values.append(temp)
                self.choiceShapes.append(temp)
            elif "group" in tag:
                temp = child.get("ref")
                if temp == None:
                    temp = child.get("id")
                if temp == None:
                    temp = child.get("name")
                self.choiceShapes.append(temp)
                values.append(self.NS[f'NodeShape/{temp}'])

        values = [i for i in values if not i.endswith("None")]
        if values == []:
            return xsd_element
        else:
            current_BN = BNode()
            self.SHACL.add((subject, self.shaclNS["xone"], current_BN))
            for index in range(len(values))[0:-1]:
                self.SHACL.add((current_BN, RDF.first, URIRef(values[index]))) 
                next_BN = BNode()
                self.SHACL.add((current_BN, RDF.rest, next_BN)) 
                current_BN = next_BN

            self.SHACL.add((current_BN, RDF.first, URIRef(values[-1]))) 
            self.SHACL.add((current_BN, RDF.rest, RDF.nil)) 
            return xsd_element 

    def translate(self,current_node):
        """A function to iteratively translate XSD to SHACL"""
        for child in current_node.findall("*"):
            # Translate current node and associate this SHACL term/shape with its corresponding SHACL shape
            tag = child.tag
            next_node = child
            if ("element" in tag) or (("attribute" in tag) and ("attributeGroup" not in tag)):
                if child.get("ref"):
                    ref = child.get("ref")
                    if ":" in ref:
                        ref = ref.split(":")[-1]
                    ref_node = self.root.find(f".//*[@name='{ref}']")
                    if ref_node != None:
                        element_type = self.isSimpleComplex(ref_node)
                        if element_type == 0:                            
                            if "attribute" in ref_node.tag:
                                object = self.NS[f'PropertyShape/@{ref}']
                            else:
                                object = self.NS[f'PropertyShape/{ref}']
                            self.SHACL.add((self.shapes[-1],self.shaclNS.property,object))
                        elif element_type == 1:
                            self.SHACL.add((self.shapes[-1],self.shaclNS.node,self.NS[f'NodeShape/{ref}']))
                else:
                    element_type = self.isSimpleComplex(child)
                    if element_type == 0:
                        next_node = self.transEleSimple(child)
                    elif element_type == 1:
                        next_node = self.transEleComplex(child)
                    elif element_type == "simpleContent" or element_type == "mixed":
                        next_node = self.transEleComplexSimpleContent(child)
            elif ("simpleType" in tag) and (self.shapes == []):
                continue
            elif ("extension" in tag):
                next_node = self.transExtension(child)
            elif ("complexType" in tag) and (child.get("name")):
                next_node = self.transComplexType(child)
            elif ("attributeGroup" in tag):
                if child.get("ref"):
                    # next_node = self.root.find(f".//*[@name='{child.get('ref')}']")
                    self.SHACL.add((self.shapes[-1],self.shaclNS.node,self.NS[f'NodeShape/{child.get("ref")}']))
                else:
                    next_node = self.transComplexType(child)
            elif ("group" in tag):
                ref = child.get("ref")
                if ref:
                    if ref in self.choiceShapes:
                        pass
                    else:
                        self.SHACL.add((self.shapes[-1],self.shaclNS.node,self.NS[f'NodeShape/{ref}']))
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
                value = child.get("base")
                self.transRestriction(tag,value)
            elif ("enumeration" in tag):
                self.transEnumeration(child)
            elif ("sequence" in tag):
                pass
                # self.order_list = list(reversed(range(len(child.findall("./")))))
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
            else:
                value = child.get("value")
                self.transRestriction(tag,value)
            # Translate next node
            self.translate(next_node)

            # removed: or self.extension
            # an <xs:extension> is always inside another case that will return true below
            # there is a proven risk (taf_cat_complexe.xsd from the TAF_TSI) that the self.extension=true will result in an unwanted 2x pop()
            if (("element" in tag) and (child.get("name"))) or (("attribute" in tag) and ("attributeGroup" not in tag) and not child.get("ref")) or (("complexType" in tag) and (child.get("name"))) or (("attributeGroup" in tag) and (child.get("name"))) or (("group" in tag) and (child.get("name") or child.get("id"))):
                self.shapes.pop()
                #self.extension = False
                # if (self.shapes!=[]) and (self.simpleContent == self.shapes[-1]):
                #     self.shapes.pop()
                #     self.simpleContent = False
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
        # tree = ET.ElementTree(self.root)
        # tree.write("parse_merge.xsd", encoding="utf-8", xml_declaration=True)
        # return None

        for key in self.root.attrib:
            if key == "targetNamespace":
                # Normalize namespace by removing trailing / (if present) and then adding it back
                normalized_ns = self.root.attrib[key].rstrip('/') + '/'
                self.xsdTargetNS = Namespace(normalized_ns)
                self.NS = Namespace(normalized_ns)           

        print("#########Start translating XSD to SHACL shapes")
        start = time.time()
        self.translate(self.root)
        end = time.time()
        # print("Translation time cost: " + str(end - start), "Seconds")

        print("#########Start validating SHACL shapes syntax")
        shaclValidation = Graph()
        shaclValidation.parse("https://www.w3.org/ns/shacl-shacl")
        
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

        