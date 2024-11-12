
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


def recursiceCheck(element):
    for child in element.findall("*"):
        identifyXSD(child)
        if "element" in child.tag:
            name = child.get("name")
        recursiceCheck(child)

def built_in_types():
    return ['string', 'normalizedString', 'token', 'base64Binary', 'hexBinary', 'integer', 'positiveInteger', 'negativeInteger', 'nonNegativeInteger', 'nonPositiveInteger', 'long', 'unsignedLong', 'int', 'unsignedInt', 'short', 'unsignedShort', 'byte', 'unsignedByte', 'decimal', 'float', 'double', 'boolean', 'duration', 'dateTime', 'date', 'time', 'gYear', 'gYearMonth', 'gMonth', 'gMonthDay', 'gDay', 'Name', 'QName', 'NCName', 'anyURI', 'language', 'ID', 'IDREF', 'IDREFS', 'ENTITY', 'ENTITIES', 'NOTATION', 'NMTOKEN', 'NMTOKENS']




