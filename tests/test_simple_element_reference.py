"""A reference to a global simple element reuses the global property shape, which holds the
constraints on the value but no cardinality. The cardinality of each reference is given by a
property shape of the referring shape, named like the shape of a local element. For the
instances below xmllint and pySHACL (on the RDF conversion) agree."""
import os

import pytest
from pyshacl import validate
from rdflib import Literal, Namespace, RDF, XSD

from helpers import COMPARISON, translate
from xmlrdf import xml_to_rdf, xmllint_valid

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")
POS = os.path.join(COMPARISON, "pos.xsd")

ADDRESS = "<name>n</name><street>s</street><city>c</city><state>st</state><zip>1</zip>"


def item(comments):
    return ('<item partNum="123-AB"><productName>p</productName><quantity>1</quantity><USPrice>1.5</USPrice>'
            + "".join(f"<comment>c{i}</comment>" for i in range(comments)) + "</item>")  # distinct values: distinct triples


def purchase_order(comment, items):
    return ('<purchaseOrder><shipTo country="US">' + ADDRESS + '</shipTo><billTo country="US">' + ADDRESS + "</billTo>"
            + ("<comment>order</comment>" if comment else "") + "<items>" + items + "</items></purchaseOrder>")


INSTANCES = {
    "order and item without comment": (purchase_order(False, item(0)), True),
    "order and item with one comment": (purchase_order(True, item(1)), True),
    "item with two comments": (purchase_order(False, item(2)), False),
}


@pytest.fixture(scope="module")
def shapes(tmp_path_factory):
    return translate(POS, tmp_path_factory.mktemp("pos") / "pos.ttl")


def test_global_shape_has_no_cardinality_and_references_have_their_own(shapes):
    g = shapes
    comment = EX["PropertyShape/comment"]
    assert (comment, SH.datatype, XSD.string) in g
    assert g.value(comment, SH.minCount) is None and g.value(comment, SH.maxCount) is None
    for parent, order in ((EX["NodeShape/PurchaseOrderType"], 2), (EX["NodeShape/Items/item"], 3)):
        site = EX[str(parent).replace("NodeShape/", "PropertyShape/", 1).split("http://example.com/")[1] + "/comment"]
        # the parent refers to the global shape for the value and to its own shape for the occurrence
        assert (parent, SH.property, comment) in g
        assert (parent, SH.property, site) in g
        assert set(g.predicate_objects(site)) == {
            (RDF.type, SH.PropertyShape), (SH.path, EX.comment), (SH.name, Literal("comment")),
            (SH.minCount, Literal(0)), (SH.maxCount, Literal(1)), (SH.order, Literal(order))}


@pytest.mark.parametrize("name", list(INSTANCES))
def test_agrees_with_xmllint(shapes, tmp_path, name):
    xml, expected = INSTANCES[name]
    path = tmp_path / "instance.xml"
    path.write_text(xml)
    assert xmllint_valid(POS, path) == expected
    assert validate(xml_to_rdf(POS, path), shacl_graph=shapes)[0] == expected


def test_reference_cardinality_follows_the_model_groups(tmp_path):
    xsd = tmp_path / "ref.xsd"
    xsd.write_text("""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="note" type="xs:string"/>
  <xs:element name="doc">
    <xs:complexType>
      <xs:sequence maxOccurs="2">
        <xs:element ref="note" maxOccurs="3"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="memo">
    <xs:complexType>
      <xs:all>
        <xs:element ref="note"/>
      </xs:all>
    </xs:complexType>
  </xs:element>
</xs:schema>
""")
    g = translate(xsd, tmp_path / "ref.ttl")
    in_sequence, in_all = EX["PropertyShape/doc/note"], EX["PropertyShape/memo/note"]
    assert (g.value(in_sequence, SH.minCount), g.value(in_sequence, SH.maxCount)) == (Literal(1), Literal(6))
    assert g.value(in_sequence, SH.order) == Literal(0)
    assert (g.value(in_all, SH.minCount), g.value(in_all, SH.maxCount)) == (Literal(1), Literal(1))
    assert g.value(in_all, SH.order) is None
    assert g.value(EX["PropertyShape/note"], SH.minCount) is None
