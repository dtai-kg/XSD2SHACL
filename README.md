# XSD2SHACL

## Done
- Element with simple type and built-in type -> sh:propertyShape + sh:path + sh:targetSubjectOf
- Attribute with simple type and built-in type -> sh:propertyShape + sh:path + sh:targetSubjectOf
- type -> sh:dataType
- cardinality -> sh:minMaxCount
- minMaxLength
- minMaxExInclusive
- Enumeration -> sh:in
- fixed -> sh:hasValue
- default -> sh:defaultValue
- name -> sh:name
- complexType -> NS
- simpleType -> PS
- xs:sequence -> sh:order
- xs:all
- xs:union -> sh:or

## To Do

- language
- sh:order
- Test XSD2ShEx

## To be discussed:

- xs:list it is not matched with RDF compared with XML
- xs:sequence, translated ShEx is weird
- language

