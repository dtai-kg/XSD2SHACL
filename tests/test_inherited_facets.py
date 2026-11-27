"""Restrictions of user-defined simple types inherit the facets, enumerations and datatype of
their base types; the patterns of the derivation steps are combined with sh:and."""
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, XSD
from rdflib.collection import Collection

from helpers import translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:simpleType name="Base">
    <xs:restriction base="xs:string">
      <xs:minLength value="2"/>
      <xs:maxLength value="8"/>
      <xs:pattern value="[a-z]+"/>
      <xs:pattern value="[A-Z]+"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="Mid">
    <xs:restriction base="Base">
      <xs:maxLength value="5"/>
      <xs:pattern value=".*a.*"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="Leaf">
    <xs:restriction base="Mid">
      <xs:minLength value="3"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="Small">
    <xs:restriction base="xs:integer">
      <xs:enumeration value="1"/>
      <xs:enumeration value="2"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="Smaller">
    <xs:restriction base="Small">
      <xs:maxInclusive value="1"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:element name="item">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="code" type="Leaf"/>
        <xs:element name="size" type="Smaller"/>
        <xs:element name="price">
          <xs:simpleType>
            <xs:restriction base="xs:decimal">
              <xs:maxInclusive value="9.5"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

DATA = """
@prefix : <http://example.com/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
:i a :item ; :code "%s" ; :size %s ; :price 9.0 .
"""


def test_facets_are_inherited_along_the_type_chain(tmp_path):
    xsd = tmp_path / "chain.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "chain.ttl")
    code = EX["PropertyShape/item/code"]
    assert g.value(code, SH.datatype) == XSD.string
    assert g.value(code, SH.minLength) == Literal(3)  # the most derived value wins
    assert g.value(code, SH.maxLength) == Literal(5)
    # one pattern per derivation step, combined with sh:and
    assert g.value(code, SH.pattern) is None
    members = list(Collection(g, g.value(code, SH["and"])))
    assert sorted(str(g.value(m, SH.pattern)) for m in members) == ["^(.*a.*)$", "^([a-z]+|[A-Z]+)$"]
    size = EX["PropertyShape/item/size"]
    assert g.value(size, SH.datatype) == XSD.integer
    assert g.value(size, SH.maxInclusive) == Literal(1)
    assert list(Collection(g, g.value(size, SH["in"]))) == [Literal("1", datatype=XSD.integer), Literal("2", datatype=XSD.integer)]
    # a non-integer bound is typed with the base type
    assert g.value(EX["PropertyShape/item/price"], SH.maxInclusive) == Literal("9.5", datatype=XSD.decimal)
    for code_value, size_value, expected in [("aaa", 1, True), ("abcde", 1, True), ("ab", 1, False), ("abcdef", 1, False),
                                             ("bbb", 1, False), ("Aaa", 1, False), ("aaa", 2, False), ("aaa", 3, False)]:
        conforms = validate(Graph().parse(data=DATA % (code_value, size_value), format="turtle"), shacl_graph=g)[0]
        assert conforms is expected, (code_value, size_value)
