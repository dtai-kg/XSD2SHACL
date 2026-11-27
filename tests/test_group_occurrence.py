"""The occurrence of xs:sequence, xs:all and group references propagates to the cardinalities of
the elements inside them: lower bounds multiply (0 if any is 0), upper bounds multiply (none if
any is unbounded). The resulting shapes may be looser than the XSD but never stricter; for the
instances below xmllint and pySHACL (on the RDF conversion) agree."""
import pytest
from pyshacl import validate
from rdflib import Literal, Namespace

from helpers import translate
from xmlrdf import xml_to_rdf, xmllint_valid

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType>
      <xs:sequence>
        <xs:sequence minOccurs="0">
          <xs:element name="a" type="xs:string"/>
        </xs:sequence>
        <xs:sequence maxOccurs="3">
          <xs:element name="b" type="xs:string" maxOccurs="2"/>
        </xs:sequence>
        <xs:group ref="G" minOccurs="0"/>
        <xs:sequence maxOccurs="2">
          <xs:sequence maxOccurs="2">
            <xs:element name="d" type="xs:string" minOccurs="0"/>
          </xs:sequence>
        </xs:sequence>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="other">
    <xs:complexType>
      <xs:sequence>
        <xs:group ref="G" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:group name="G">
    <xs:sequence>
      <xs:element name="c" type="xs:string"/>
    </xs:sequence>
  </xs:group>
</xs:schema>
"""

def elements(name, count):
    return "".join(f"<{name}>{i}</{name}>" for i in range(count))  # distinct values: distinct triples


INSTANCES = {
    "one b": "<root>" + elements("b", 1) + "</root>",
    "six b": "<root><a/>" + elements("b", 6) + "</root>",
    "seven b": "<root><a/>" + elements("b", 7) + "</root>",
    "no b": "<root><a/></root>",
    "four d": "<root><b/><c/>" + elements("d", 4) + "</root>",
    "five d": "<root><b/><c/>" + elements("d", 5) + "</root>",
}


@pytest.fixture(scope="module")
def schema(tmp_path_factory):
    directory = tmp_path_factory.mktemp("occurrence")
    xsd = directory / "occurrence.xsd"
    xsd.write_text(XSD_DOC)
    return xsd, translate(xsd, directory / "occurrence.ttl")


def test_propagated_cardinalities(schema):
    _, g = schema
    assert (g.value(EX["PropertyShape/root/a"], SH.minCount), g.value(EX["PropertyShape/root/a"], SH.maxCount)) == (Literal(0), Literal(1))
    assert (g.value(EX["PropertyShape/root/b"], SH.minCount), g.value(EX["PropertyShape/root/b"], SH.maxCount)) == (Literal(1), Literal(6))
    assert (g.value(EX["PropertyShape/root/d"], SH.minCount), g.value(EX["PropertyShape/root/d"], SH.maxCount)) == (Literal(0), Literal(4))
    # the group is referenced optionally in one place and unboundedly in another: loosest bounds
    assert (g.value(EX["PropertyShape/G/c"], SH.minCount), g.value(EX["PropertyShape/G/c"], SH.maxCount)) == (Literal(0), None)


@pytest.mark.parametrize("name", list(INSTANCES))
def test_agreement_with_xmllint(schema, name, tmp_path):
    xsd, g = schema
    xml = tmp_path / "instance.xml"
    xml.write_text(INSTANCES[name])
    expected = xmllint_valid(xsd, xml)
    conforms, _, text = validate(xml_to_rdf(xsd, xml), shacl_graph=g)
    assert conforms is expected, text
