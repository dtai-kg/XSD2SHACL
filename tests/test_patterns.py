"""xs:pattern facets: anchored so that the whole value must match."""
from pyshacl import validate
from rdflib import Graph, Literal, Namespace

from helpers import translate

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="part">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="code">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:pattern value="[A-Z]{2}\\d{3}"/>
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
:p1 a :part ; :code "%s" .
"""


def test_single_pattern_is_anchored(tmp_path):
    xsd = tmp_path / "pattern.xsd"
    xsd.write_text(XSD_DOC)
    g = translate(xsd, tmp_path / "pattern.ttl")
    assert g.value(EX["PropertyShape/part/code"], SH.pattern) == Literal("^([A-Z]{2}\\d{3})$")
    assert validate(Graph().parse(data=DATA % "AB123", format="turtle"), shacl_graph=g)[0]
    # a value that only contains a match is rejected
    assert not validate(Graph().parse(data=DATA % "xAB123y", format="turtle"), shacl_graph=g)[0]


XSD_TWO_PATTERNS = XSD_DOC.replace('<xs:pattern value="[A-Z]{2}\\d{3}"/>',
                                   '<xs:pattern value="[A-Z]{2}\\d{3}"/><xs:pattern value="X-\\d+"/>')


def test_several_patterns_of_one_restriction_are_alternatives(tmp_path):
    xsd = tmp_path / "patterns.xsd"
    xsd.write_text(XSD_TWO_PATTERNS)
    g = translate(xsd, tmp_path / "patterns.ttl")
    patterns = list(g.objects(EX["PropertyShape/part/code"], SH.pattern))
    assert patterns == [Literal("^([A-Z]{2}\\d{3}|X-\\d+)$")]
    for value, expected in [("AB123", True), ("X-7", True), ("AB123X-7", False), ("Q", False)]:
        assert validate(Graph().parse(data=DATA % value, format="turtle"), shacl_graph=g)[0] is expected, value
