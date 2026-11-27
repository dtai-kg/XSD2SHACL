"""Choices: every candidate keeps an ordinary property shape with a lower bound of 0; the
combination is an sh:xone (choice at most once) or sh:or (repeatable choice that must occur) of
"selected" shapes, with a "no candidate" shape when the choice may be absent. For the instances
below xmllint and pySHACL (on the RDF conversion) agree."""
import pytest
from pyshacl import validate
from rdflib import BNode, Literal, Namespace
from rdflib.collection import Collection

from helpers import translate
from xmlrdf import xml_to_rdf, xmllint_valid

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="plain">
    <xs:complexType>
      <xs:choice>
        <xs:element name="a" type="xs:string"/>
        <xs:element name="b" type="xs:string"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:element name="optional">
    <xs:complexType>
      <xs:choice minOccurs="0">
        <xs:element name="a" type="xs:string"/>
        <xs:element name="b" type="xs:string"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:element name="seq">
    <xs:complexType>
      <xs:choice>
        <xs:element name="a" type="xs:string"/>
        <xs:sequence>
          <xs:element name="b" type="xs:string"/>
          <xs:element name="c" type="xs:string" minOccurs="0"/>
        </xs:sequence>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:element name="nested">
    <xs:complexType>
      <xs:choice>
        <xs:element name="a" type="xs:string"/>
        <xs:choice>
          <xs:element name="b" type="xs:string"/>
          <xs:element name="c" type="xs:string"/>
        </xs:choice>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:element name="repeat">
    <xs:complexType>
      <xs:choice maxOccurs="unbounded">
        <xs:element name="a" type="xs:string"/>
        <xs:element name="b" type="xs:string"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:element name="grp">
    <xs:complexType>
      <xs:choice>
        <xs:element name="a" type="xs:string"/>
        <xs:group ref="G"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:group name="G">
    <xs:sequence>
      <xs:element name="b" type="xs:string"/>
      <xs:element name="c" type="xs:string"/>
    </xs:sequence>
  </xs:group>
</xs:schema>
"""

INSTANCES = {
    "plain a": "<plain><a>1</a></plain>",
    "plain b": "<plain><b>1</b></plain>",
    "plain none": "<plain/>",
    "plain both": "<plain><a>1</a><b>2</b></plain>",
    "optional none": "<optional/>",
    "optional a": "<optional><a>1</a></optional>",
    "optional both": "<optional><a>1</a><b>2</b></optional>",
    "seq a": "<seq><a>1</a></seq>",
    "seq b": "<seq><b>1</b></seq>",
    "seq b c": "<seq><b>1</b><c>2</c></seq>",
    "seq c": "<seq><c>1</c></seq>",
    "seq a b": "<seq><a>1</a><b>2</b></seq>",
    "nested a": "<nested><a>1</a></nested>",
    "nested c": "<nested><c>1</c></nested>",
    "nested b c": "<nested><b>1</b><c>2</c></nested>",
    "nested a b": "<nested><a>1</a><b>2</b></nested>",
    "nested none": "<nested/>",
    "repeat a a b": "<repeat><a>1</a><a>2</a><b>3</b></repeat>",
    "repeat none": "<repeat/>",
    "grp a": "<grp><a>1</a></grp>",
    "grp b c": "<grp><b>1</b><c>2</c></grp>",
    "grp b": "<grp><b>1</b></grp>",
    "grp a b c": "<grp><a>1</a><b>2</b><c>3</c></grp>",
}


@pytest.fixture(scope="module")
def schema(tmp_path_factory):
    directory = tmp_path_factory.mktemp("choice")
    xsd = directory / "choice.xsd"
    xsd.write_text(XSD_DOC)
    return xsd, translate(xsd, directory / "choice.ttl")


def test_candidates_have_optional_property_shapes(schema):
    _, g = schema
    for name in ("a", "b"):
        ps = EX[f"PropertyShape/plain/{name}"]
        assert (EX["NodeShape/plain"], SH.property, ps) in g
        assert g.value(ps, SH.minCount) == Literal(0)
        assert g.value(ps, SH.maxCount) == Literal(1)


def test_combination_structure(schema):
    _, g = schema
    members = list(Collection(g, g.value(EX["NodeShape/plain"], SH.xone)))
    assert len(members) == 2 and all(isinstance(m, BNode) for m in members)
    assert {g.value(m, SH.path) for m in members} == {EX.a, EX.b}
    assert all(g.value(m, SH.minCount) == Literal(1) for m in members)
    # an optional choice has an additional "no candidate" member (sh:and of maxCount 0)
    optional = list(Collection(g, g.value(EX["NodeShape/optional"], SH.xone)))
    assert len(optional) == 3
    none = [m for m in optional if g.value(m, SH["and"]) is not None]
    assert len(none) == 1
    assert all(g.value(m, SH.maxCount) == Literal(0) for m in Collection(g, g.value(none[0], SH["and"])))
    # a repeatable choice that must occur: sh:or
    assert g.value(EX["NodeShape/repeat"], SH.xone) is None
    assert len(list(Collection(g, g.value(EX["NodeShape/repeat"], SH["or"])))) == 2
    # the elements of a nested choice are not combined a second time on the node shape
    assert len(list(g.objects(EX["NodeShape/nested"], SH.xone))) == 1


@pytest.mark.parametrize("name", list(INSTANCES))
def test_agreement_with_xmllint(schema, name, tmp_path):
    xsd, g = schema
    xml = tmp_path / "instance.xml"
    xml.write_text(INSTANCES[name])
    expected = xmllint_valid(xsd, xml)
    conforms, _, text = validate(xml_to_rdf(xsd, xml), shacl_graph=g)
    assert conforms is expected, text


XSD_REPEAT_OPTIONAL = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType>
      <xs:choice maxOccurs="unbounded">
        <xs:element name="a" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
        <xs:element name="b" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


def test_repeatable_choice_with_optional_candidates_has_no_combination(tmp_path):
    # the choice must occur, but a candidate may occur zero times, so an empty root is valid in
    # the XSD; requiring a candidate would be stricter, so no sh:or is generated and no blank
    # shape is left behind
    xsd = tmp_path / "repeat.xsd"
    xsd.write_text(XSD_REPEAT_OPTIONAL)
    g = translate(xsd, tmp_path / "repeat.ttl")
    assert g.value(EX["NodeShape/root"], SH["or"]) is None
    assert not [s for s in g.subjects(SH.minCount, None) if isinstance(s, BNode)]
    xml = tmp_path / "empty.xml"
    xml.write_text("<root/>")
    assert xmllint_valid(xsd, xml)
    assert validate(xml_to_rdf(xsd, xml), shacl_graph=g)[0]
