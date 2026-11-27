"""A reference to a global complex element is translated like a nested complex element: a
property shape with the element's path and the cardinality of the reference, pointing to the
global element's node shape."""
from pyshacl import validate
from rdflib import Graph, Literal, Namespace

from helpers import translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="address">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="city" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="order">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="address" minOccurs="0" maxOccurs="2"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

PREFIXES = """
@prefix : <http://example.com/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


def test_referenced_complex_element_is_linked_through_a_property_shape(tmp_path):
    xsd = tmp_path / "ref.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "ref.ttl")
    link = EX["PropertyShape/order/address"]
    assert (EX["NodeShape/order"], SH.property, link) in g
    assert (link, SH.path, EX.address) in g
    assert (link, SH.node, EX["NodeShape/address"]) in g
    assert g.value(link, SH.minCount) == Literal(0)
    assert g.value(link, SH.maxCount) == Literal(2)
    # the order is no longer validated against the address shape itself
    assert (EX["NodeShape/order"], SH.node, EX["NodeShape/address"]) not in g
    ok = PREFIXES + ':o a :order ; :address :a1 . :a1 a :address ; :city "Leuven"^^xsd:string .'
    assert validate(Graph().parse(data=ok, format="turtle"), shacl_graph=g)[0]
    assert validate(Graph().parse(data=PREFIXES + ":o a :order .", format="turtle"), shacl_graph=g)[0]
    missing_city = PREFIXES + ":o a :order ; :address :a1 . :a1 a :address ."
    assert not validate(Graph().parse(data=missing_city, format="turtle"), shacl_graph=g)[0]
    too_many = PREFIXES + ':o a :order ; :address :a1, :a2, :a3 . :a1 a :address ; :city "L"^^xsd:string . :a2 a :address ; :city "L"^^xsd:string . :a3 a :address ; :city "L"^^xsd:string .'
    assert not validate(Graph().parse(data=too_many, format="turtle"), shacl_graph=g)[0]
