"""Enumeration and fixed values are literals typed by the built-in type the declaration derives
from, the same datatype as the shape's sh:datatype; values of xs:string are plain literals.
Note: rdflib compares literals by lexical form and datatype, so "US", "US"^^xsd:string and
"US"^^xsd:NMTOKEN are different terms; the data of each test uses the literals of the declared type."""
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, XSD
from rdflib.collection import Collection

from helpers import translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
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
  <xs:simpleType name="Mode">
    <xs:restriction base="xs:token">
      <xs:enumeration value="fast"/>
      <xs:enumeration value="slow"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:element name="item">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="size" type="Small"/>
        <xs:element name="colour">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:enumeration value="red"/>
              <xs:enumeration value="blue"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
        <xs:element name="mode" type="Mode"/>
      </xs:sequence>
      <xs:attribute name="version" type="Smaller" fixed="1"/>
      <xs:attribute name="kind" fixed="plain">
        <xs:simpleType>
          <xs:restriction base="xs:token"/>
        </xs:simpleType>
      </xs:attribute>
      <xs:attribute name="country" type="xs:NMTOKEN" fixed="US"/>
      <xs:attribute name="label" type="xs:string" fixed="item" use="required"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

PREFIXES = """
@prefix : <http://example.com/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""
# valid instance: plain literals for the xs:string declarations, xsd:token / xsd:NMTOKEN literals
# for the declarations of those types, an integer for the integer enumeration
VALID = PREFIXES + ':i a :item ; :size 2 ; :colour "red" ; :mode "fast"^^xsd:token ; :version 1 ; :kind "plain"^^xsd:token ; :country "US"^^xsd:NMTOKEN ; :label "item" .'


def in_values(g, shape):
    return list(Collection(g, g.value(shape, SH["in"])))


def conforms(data, g):
    return validate(Graph().parse(data=data, format="turtle"), shacl_graph=g)[0]


def test_enumeration_and_fixed_values_are_typed_like_the_datatype(tmp_path):
    xsd = tmp_path / "typed.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "typed.ttl")
    size, colour, mode = EX["PropertyShape/item/size"], EX["PropertyShape/item/colour"], EX["PropertyShape/item/mode"]
    version, kind, country, label = (EX["PropertyShape/item/@version"], EX["PropertyShape/item/@kind"],
                                     EX["PropertyShape/item/@country"], EX["PropertyShape/item/@label"])
    assert g.value(size, SH.datatype) == XSD.integer
    assert in_values(g, size) == [Literal("1", datatype=XSD.integer), Literal("2", datatype=XSD.integer)]
    # xs:string: plain literals
    assert g.value(colour, SH.datatype) == XSD.string
    assert in_values(g, colour) == [Literal("red"), Literal("blue")]
    assert g.value(label, SH.datatype) == XSD.string
    assert in_values(g, label) == [Literal("item")]
    # string-derived types: the literal carries the same datatype as sh:datatype
    assert g.value(mode, SH.datatype) == XSD.token
    assert in_values(g, mode) == [Literal("fast", datatype=XSD.token), Literal("slow", datatype=XSD.token)]
    assert g.value(kind, SH.datatype) == XSD.token
    assert in_values(g, kind) == [Literal("plain", datatype=XSD.token)]
    assert g.value(country, SH.datatype) == XSD.NMTOKEN
    assert in_values(g, country) == [Literal("US", datatype=XSD.NMTOKEN)]
    # fixed values follow the type chain of the attribute (Smaller -> Small -> xs:integer)
    assert g.value(version, SH.datatype) == XSD.integer
    assert in_values(g, version) == [Literal("1", datatype=XSD.integer)]


def test_string_enumeration_and_fixed_accept_plain_literals(tmp_path):
    xsd = tmp_path / "typed.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "typed.ttl")
    assert conforms(VALID, g)
    assert conforms(VALID.replace('"red"', '"blue"'), g)
    # a value outside the enumeration, a different fixed value
    assert not conforms(VALID.replace('"red"', '"green"'), g)
    assert not conforms(VALID.replace('"item"', '"other"'), g)


def test_token_enumeration_satisfies_datatype_and_in_together(tmp_path):
    xsd = tmp_path / "typed.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "typed.ttl")
    assert conforms(VALID.replace('"fast"^^xsd:token', '"slow"^^xsd:token'), g)
    # the wrong datatype (a plain literal) or a value outside the enumeration is rejected
    assert not conforms(VALID.replace('"fast"^^xsd:token', '"fast"'), g)
    assert not conforms(VALID.replace('"fast"^^xsd:token', '"medium"^^xsd:token'), g)
    assert not conforms(VALID.replace('"US"^^xsd:NMTOKEN', '"FR"^^xsd:NMTOKEN'), g)
    assert not conforms(VALID.replace(':size 2', ':size 3'), g)
