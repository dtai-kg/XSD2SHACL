"""Structural properties of the generated shapes."""
import os

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from helpers import COMPARISON, translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

CARDINALITY_XSD = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="order">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="line" minOccurs="1" maxOccurs="3">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="sku" type="xs:string"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="note" minOccurs="0" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="text" type="xs:string"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


def test_linking_property_shape_cardinality(tmp_path):
    xsd = tmp_path / "cardinality.xsd"
    xsd.write_text(CARDINALITY_XSD)
    g = translate(xsd, tmp_path / "cardinality.ttl")
    link = EX["PropertyShape/order/line"]
    assert (EX["NodeShape/order"], SH.property, link) in g
    assert (link, SH.path, EX["line"]) in g
    assert (link, SH.node, EX["NodeShape/order/line"]) in g
    assert g.value(link, SH.minCount) == Literal(1)
    assert g.value(link, SH.maxCount) == Literal(3)
    # unbounded: no sh:maxCount
    unbounded = EX["PropertyShape/order/note"]
    assert g.value(unbounded, SH.minCount) == Literal(0)
    assert g.value(unbounded, SH.maxCount) is None
    # the parent is no longer required to satisfy the child's node shape itself
    assert (EX["NodeShape/order"], SH.node, EX["NodeShape/order/line"]) not in g


def test_sequence_order(tmp_path):
    g = translate(os.path.join(COMPARISON, "sequence.xsd"), tmp_path / "sequence.ttl")
    orders = {str(s).split("/")[-1]: int(o) for s, o in g.subject_objects(SH.order)}
    assert orders == {"name": 0, "street": 1, "city": 2, "state": 3, "zip": 4}


def test_anonymous_complex_type_has_no_dangling_node_reference(tmp_path):
    g = translate(os.path.join(COMPARISON, "xmlschema2shex", "example.xsd"), tmp_path / "example.ttl")
    assert URIRef("http://example.com/NodeShape/None") not in set(g.objects(None, SH.node))


def test_target_namespace_without_separator_gets_fragment(tmp_path):
    g = translate(os.path.join(COMPARISON, "xmlschema2shex", "example.xsd"), tmp_path / "example.ttl")
    paths = {str(p) for p in g.objects(None, SH.path)}
    assert "http://tempuri.org/po.xsd#item" in paths
    assert not any(p.startswith("http://tempuri.org/po.xsditem") for p in paths)


def test_simple_content_extension_runs(tmp_path):
    g = translate(os.path.join(COMPARISON, "extension.xsd"), tmp_path / "extension.ttl")
    text = EX["PropertyShape/address/address"]
    assert (EX["NodeShape/address"], SH.property, text) in g
    assert (text, SH.datatype, URIRef("http://www.w3.org/2001/XMLSchema#string")) in g
    assert g.value(text, SH["in"]) is not None
