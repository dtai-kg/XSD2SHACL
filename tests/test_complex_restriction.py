"""A complex type derived by restriction refers to the node shape of its base type (as an
extension does), so the attributes declared on the base type apply."""
from pyshacl import validate
from rdflib import Graph, Namespace

from helpers import translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:complexType name="Base">
    <xs:sequence>
      <xs:element name="a" type="xs:string" minOccurs="0"/>
      <xs:element name="b" type="xs:string" minOccurs="0"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:complexType name="Derived">
    <xs:complexContent>
      <xs:restriction base="Base">
        <xs:sequence>
          <xs:element name="a" type="xs:string"/>
        </xs:sequence>
      </xs:restriction>
    </xs:complexContent>
  </xs:complexType>
  <xs:element name="thing" type="Derived"/>
</xs:schema>
"""

DATA = """
@prefix : <http://example.com/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
:t a :thing ; :a "x"^^xsd:string %s .
"""


def test_complex_restriction_refers_to_base_shape(tmp_path):
    xsd = tmp_path / "restriction.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "restriction.ttl")
    assert (EX["NodeShape/Derived"], SH.node, EX["NodeShape/Base"]) in g
    assert validate(Graph().parse(data=DATA % '; :id "1"^^xsd:string', format="turtle"), shacl_graph=g)[0]
    # the required attribute of the base type is missing
    assert not validate(Graph().parse(data=DATA % "", format="turtle"), shacl_graph=g)[0]
