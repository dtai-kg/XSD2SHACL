"""Cardinality of attributes: "use" defaults to optional (at most one value), required attributes
need exactly one value and prohibited attributes none."""
from rdflib import Literal, Namespace

from helpers import translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="item">
    <xs:complexType>
      <xs:attribute name="id" type="xs:string" use="required"/>
      <xs:attribute name="note" type="xs:string"/>
      <xs:attribute name="label" type="xs:string" use="optional"/>
      <xs:attribute name="old" type="xs:string" use="prohibited"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


def cardinality(g, shape):
    return g.value(shape, SH.minCount), g.value(shape, SH.maxCount)


def test_attribute_use(tmp_path):
    xsd = tmp_path / "attributes.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "attributes.ttl")
    assert cardinality(g, EX["PropertyShape/item/@id"]) == (Literal(1), Literal(1))
    # no "use": optional, only an upper bound
    assert cardinality(g, EX["PropertyShape/item/@note"]) == (None, Literal(1))
    assert cardinality(g, EX["PropertyShape/item/@label"]) == (None, Literal(1))
    assert cardinality(g, EX["PropertyShape/item/@old"]) == (None, Literal(0))
