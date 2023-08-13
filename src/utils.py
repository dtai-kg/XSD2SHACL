import xml.etree.ElementTree as ET
import rdflib
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef

def identifyXSD(element):
    """
    A function to identify and check the type and correctness of XSD Element
    """
    tag = element.tag.split("}")[-1]
    if "all" == tag:
        allowed_tags = ["element"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: all should only contain element")
    elif "annotation" == tag:
        allowed_tags = ["appinfo", "documentation"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: annotation should only contain appinfo or documentation")
    elif "any" == tag or "anyAttribute" == tag or "field" == tag or "import" == tag or "include" == tag or "notation" == tag or "selector" == tag:
        allowed_tags = ["annotation"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: any or anyAttribute or field or import or include or notation or selector should only contain annotation")
    elif "appinfo" == tag or "documentation" == tag:
        for child in element:
            raise Exception("Invalid XSD file: appinfo or documentation should not contain any child")
    elif "attribute" == tag:
        allowed_tags = ["annotation", "simpleType"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: attribute should only contain annotation or simpleType")
    elif "attributeGroup" == tag:
        allowed_tags = ["annotation", "attribute", "attributeGroup", "anyAttribute"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: attributeGroup should only contain annotation, attribute, attributeGroup or anyAttribute")
    elif "choice" == tag:
        allowed_tags = ["annotation", "element", "group", "choice", "sequence", "any"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: choice should only contain annotation, element, group, choice, sequence or any")
    elif "complexContent" == tag:
        allowed_tags = ["annotation", "restriction", "extension"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: complexContent should only contain annotation, restriction or extension")
    elif "complexType" == tag:
        allowed_tags = ["annotation", "simpleContent", "complexContent", "group", "all", "choice", "sequence", "attribute", "attributeGroup", "anyAttribute"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: complexType should only contain annotation, simpleContent, complexContent, group, all, choice, sequence, attribute, attributeGroup or anyAttribute")
    elif "element" == tag:
        allowed_tags = ["annotation", "simpleType", "complexType", "unique", "key", "keyref"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: element should only contain annotation, simpleType, complexType, unique, key or keyref")
    elif "extension" == tag:
        allowed_tags = ["annotation", "group", "all", "choice", "sequence", "attribute", "attributeGroup", "anyAttribute"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: extension should only contain annotation, group, all, choice, sequence, attribute, attributeGroup or anyAttribute")
    elif "group" == tag:
        allowed_tags = ["annotation", "all", "choice", "sequence"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: group should only contain annotation, all, choice or sequence")
    elif "key" == tag or "keyref" == tag:
        allowed_tags = ["annotation", "selector", "field"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: key or keyref should only contain annotation, selector or field")
    elif "list" == tag:
        allowed_tags = ["annotation", "simpleType"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: list should only contain annotation or simpleType")
    elif "redefine" == tag:
        allowed_tags = ["annotation", "simpleType", "complexType", "group", "attributeGroup"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: redefine should only contain annotation, simpleType, complexType, group or attributeGroup")
    elif "restriction" == tag:
        # Distinguish between simpleType ,simpleContent, and complexContent
        pass
    elif "schema" == tag:
        allowed_tags = ["annotation", "include", "import", "redefine", "annotation", "simpleType", "complexType", "group", "attributeGroup", "element", "attribute", "notation"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: schema should only contain annotation, include, import, redefine, annotation, simpleType, complexType, group, attributeGroup, element, attribute or notation")
    elif "sequence" == tag:
        allowed_tags = ["annotation", "element", "group", "choice", "sequence", "any"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: sequence should only contain annotation, element, group, choice, sequence or any")
    elif "simpleContent" == tag:
        allowed_tags = ["annotation", "restriction", "extension"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: simpleContent should only contain annotation, restriction or extension")
    elif "simpleType" == tag:
        allowed_tags = ["annotation", "restriction", "list", "union"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: simpleType should only contain annotation, restriction, list or union")
    elif "union" == tag:
        allowed_tags = ["annotation", "simpleType"]
        if False in [child.tag.split("}")[-1] in allowed_tags for child in element.findall("*")]:
            raise Exception("Invalid XSD file: union should only contain annotation or simpleType")



def identifyElementType(root, element):
    """
    A function to identify the type of element: SimpleType or ComplexType
    And return the type of element: ComplexType, SimpleType, built-in, or None
    """
    element_type = element.get("type")

    if element_type == None:
        # Check if the element has child simpleType or complexType
        for child in element.findall("./"):
            if "complexType" in child.tag:
                return "complexType"
            elif "simpleType" in child.tag:
                return "simpleType"
    elif "xs" in element_type or "xsd" in element_type:
        # Check if the element is a built-in type
        return "built-in"
    else:
        # Check if the element is a simpleType or complexType defined in the XSD file
        child = self.root.find(f".//*[@name='{element_type}']")
        if "complexType" in child.tag:
            return "complexType"
        elif "simpleType" in child.tag:
            return "simpleType"
    # Might refer to another element
    return None


def identifyAttributeType(root, attribute):
    """
    A function to identify the type of attribute: SimpleType or ComplexType
    And return the type of attribute: ComplexType, SimpleType, built-in, or None
    """
    attribute_type = attribute.get("type")

    if attribute_type == None:
        # Check if the attribute has child simpleType or complexType
        for child in attribute.findall("./"):
            if "complexType" in child.tag:
                return "complexType"
            elif "simpleType" in child.tag:
                return "simpleType"
    elif "xs" in attribute_type or "xsd" in attribute_type:
        # Check if the attribute is a built-in type
        return "built-in"
    else:
        # Check if the attribute is a simpleType or complexType defined in the XSD file
        child = self.root.find(f".//*[@name='{attribute_type}']")
        if "complexType" in child.tag:
            return "complexType"
        elif "simpleType" in child.tag:
            return "simpleType"
    # Might refer to another attribute
    return None

def update_graph(g,old_subjects):
    bnodes = []
    for s,p,o in g:
        if s in old_subjects:
            g.remove((s,p,o))
            if isinstance(o,BNode):
                bnodes.append(o)
        elif o in old_subjects:
            g.remove((s,p,o))
        if (s in bnodes) or (o in bnodes):
            if isinstance(o,BNode):
                bnodes.append(o)
            if isinstance(s,BNode):
                bnodes.append(s)
    for s,p,o in g:
      if (s in bnodes) or (o in bnodes):
        g.remove((s,p,o))

    return g

def parseXSD(XSD_FILE, BASE_PATH, XSD_FILES = [], XSD_TYPES = {}):
    """
    Recursively parse XSD file and return a list of XSD files and a list of XSD types for solving xs:import and xs:include
    XSD_TYPES = {"ELEMENT NAME":{"ELEMENT TYPE": "COMPLEX TYPE NAME", "ELEMENT XPath":PATH}}
    """
    if XSD_FILE not in XSD_FILES:
        XSD_FILES.append(XSD_FILE)
    xsdTree = ET.parse(BASE_PATH + XSD_FILE)
    root = xsdTree.getroot()
    for child in root.findall("./"):
        if ("include" in child.tag) or ("import" in child.tag):
            ref_file = child.get("schemaLocation")
            if ref_file not in XSD_FILES:
                print("Current parsing Ref file", ref_file)
                XSD_FILES, XSD_TYPES = parseXSD(ref_file, BASE_PATH, XSD_FILES, XSD_TYPES)

    print("Current parsing file", XSD_FILE)

    return XSD_FILES, XSD_TYPES




def recursiceCheck(element):
    for child in element.findall("*"):
        identifyXSD(child)
        if "element" in child.tag:
            name = child.get("name")

            # print(child.tag, name, identifyElementType(element, child))
        recursiceCheck(child)

# xsdTree = ET.parse("usecase\RINF\RINF-metadata.xsd")
# root = xsdTree.getroot()

# XSD_FILES, XSD_TYPES = parseXSD("F03_2014.xsd", "usecase/TED/")
# print("XSD_FILES", XSD_FILES)
# print(root.find(f".//*[@name='RINFDataq']"))
# recursiceCheck(xsdTree.getroot())
# print("Valid XSD file")





