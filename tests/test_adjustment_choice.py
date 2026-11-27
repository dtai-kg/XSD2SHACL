"""Post-adjustment of the choice combinations: a "selected" member whose candidate element is
mapped takes the mapped predicate, a member whose candidate is not mapped is dropped."""
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.collection import Collection

from helpers import translate
from xsd2shacl.post_adjustment.shape_adjustment_single import ShapeAdjustment

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.com/")
ERA = Namespace("http://data.europa.eu/949/")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="doc">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="id" type="xs:string"/>
        <xs:choice minOccurs="0">
          <xs:element name="a" type="xs:string"/>
          <xs:element name="b" type="xs:string"/>
        </xs:choice>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

RML_DOC = """
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix era: <http://data.europa.eu/949/> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:DocMap a rr:TriplesMap ;
  rml:logicalSource [ rml:source "data.xml" ; rml:referenceFormulation ql:XPath ; rml:iterator "/doc" ] ;
  rr:subjectMap [ rr:template "http://example.org/docs/{id}" ; rr:class era:Doc ] ;
  rr:predicateObjectMap [ rr:predicate era:identifier ; rr:objectMap [ rml:reference "id" ; rr:datatype xsd:string ] ] ;
  rr:predicateObjectMap [ rr:predicate era:valueA ; rr:objectMap [ rml:reference "a" ; rr:datatype xsd:string ] ] .
"""


def test_choice_members_follow_the_adjusted_candidates(tmp_path):
    xsd = tmp_path / "doc.xsd"
    xsd.write_text(XSD_DOC)
    shapes = tmp_path / "doc.shape.ttl"
    translate(xsd, shapes)
    sa = ShapeAdjustment("xml")
    g0 = Graph().parse(str(shapes), format="turtle")
    sa.parseRawDataSchemaShape(g0)
    sa.parseRML(Graph().parse(data=RML_DOC, format="turtle"))
    sa.adjust(Graph() + g0)
    out = tmp_path / "doc.adjusted.ttl"
    sa.writeShapeToFile(str(out))
    g = Graph().parse(str(out), format="turtle")
    # a in the xone and a in the "no candidate" member are re-pathed; b is dropped from both
    assert sa.logical_decisions["remapped"] == 2
    assert sa.logical_decisions["dropped"] == 2
    # the adjustment builds the node shape of the subject from the mapping (NodeShape/Doc) and does not
    # carry the logical constraints of the original node shape over to it; no list member with
    # an XSD path and no blank shape may be left behind in the output
    for s in g.subjects(SH.path, None):
        if isinstance(s, BNode):
            assert list(g.subjects(None, s)), s
            assert not str(g.value(s, SH.path)).startswith(str(EX)), s
    assert EX.b not in set(g.objects(None, SH.path))
    for s in g.subjects(SH.path, None):
        if isinstance(s, BNode):
            assert list(g.subjects(None, s)), s
