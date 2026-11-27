"""Post-adjustment of XSD-driven shapes with RML: repeatability within one process and target declarations."""
from rdflib import Graph, Namespace
from rdflib.compare import to_isomorphic
from rdflib.namespace import RDF

from helpers import translate
from xsd2shacl.post_adjustment.shape_adjustment_single import ShapeAdjustment

SH = Namespace("http://www.w3.org/ns/shacl#")

XSD_DOC = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Data">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Point" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Id"><xs:complexType><xs:attribute name="Value" type="xs:string" use="required"/></xs:complexType></xs:element>
              <xs:element name="Name"><xs:complexType><xs:attribute name="Value" type="xs:string" use="required"/></xs:complexType></xs:element>
              <xs:element name="Location" maxOccurs="unbounded">
                <xs:complexType><xs:attribute name="Km" type="xs:decimal" use="required"/></xs:complexType>
              </xs:element>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

RML_DOC = """
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PointMap a rr:TriplesMap ;
  rml:logicalSource [ rml:source "data.xml" ; rml:referenceFormulation ql:XPath ; rml:iterator "/Data/Point" ] ;
  rr:subjectMap [ rr:template "http://example.org/points/{Id/@Value}" ; rr:class ex:Point ] ;
  rr:predicateObjectMap [ rr:predicate ex:name ; rr:objectMap [ rml:reference "Name/@Value" ; rr:datatype xsd:string ] ] ;
  rr:predicateObjectMap [ rr:predicate ex:location ; rr:objectMap [ rr:template "http://example.org/locations/{Location/@Km}" ; rr:termType rr:IRI ] ] .

ex:LocationMap a rr:TriplesMap ;
  rml:logicalSource [ rml:source "data.xml" ; rml:referenceFormulation ql:XPath ; rml:iterator "/Data/Point/Location" ] ;
  rr:subjectMap [ rr:template "http://example.org/locations/{@Km}" ; rr:class ex:Location ] ;
  rr:predicateObjectMap [ rr:predicate ex:km ; rr:objectMap [ rml:reference "@Km" ; rr:datatype xsd:decimal ] ] .
"""


def run_adjustment(tmp_path, name):
    xsd = tmp_path / f"{name}.xsd"
    xsd.write_text(XSD_DOC)
    shapes = tmp_path / f"{name}.shape.ttl"
    translate(xsd, shapes)
    sa = ShapeAdjustment("xml")
    g = Graph().parse(str(shapes), format="turtle")
    sa.parseRawDataSchemaShape(g)
    sa.parseRML(Graph().parse(data=RML_DOC, format="turtle"))
    sa.adjust(Graph() + g)
    out = tmp_path / f"{name}.adjusted.ttl"
    sa.writeShapeToFile(str(out))
    return Graph().parse(str(out), format="turtle")


def test_adjustment_is_repeatable_within_a_process(tmp_path):
    # two adjustments in the same process give isomorphic graphs (no random identifiers)
    g1 = run_adjustment(tmp_path, "run1")
    g2 = run_adjustment(tmp_path, "run2")
    assert to_isomorphic(g1) == to_isomorphic(g2)


def test_property_shapes_attached_to_node_shape_have_no_self_target(tmp_path):
    g = run_adjustment(tmp_path, "targets")
    for ps in g.subjects(RDF.type, SH.PropertyShape):
        if any(True for _ in g.subjects(SH.property, ps)):
            assert g.value(ps, SH.targetObjectsOf) is None, ps
    # the linking shape Point -> Location is re-pathed to the mapping predicate
    links = [ps for ps in g.subjects(RDF.type, SH.PropertyShape) if g.value(ps, SH.node) is not None]
    assert any(g.value(ps, SH.path) == Namespace("http://example.org/").location for ps in links)
    # a property shape whose node kind is IRI carries no datatype
    for ps in links:
        assert g.value(ps, SH.datatype) is None


MAPPING = """
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix ex: <http://example.org/> .

ex:%(name)sMap a rr:TriplesMap ;
  rml:logicalSource [ rml:source "data.xml" ; rml:referenceFormulation ql:XPath ; rml:iterator "/Data/Point" ] ;
  rr:subjectMap [ rr:template "http://example.org/points/{Id/@Value}" ; rr:class ex:%(name)s ] ;
  rr:predicateObjectMap [ rr:predicate ex:%(predicate)s ; rr:objectMap [ rml:reference "Name/@Value" ] ] .
"""


def test_command_line_adjusts_with_a_file_or_a_sorted_directory(tmp_path):
    """python -m xsd2shacl -i SHAPES -r RML_FILE_OR_DIR [-a OUT], from any working directory"""
    import os
    import subprocess
    import sys
    from helpers import ROOT
    xsd = tmp_path / "data.xsd"
    xsd.write_text(XSD_DOC)
    shapes = tmp_path / "data.shape.ttl"
    translate(xsd, shapes)
    mappings = tmp_path / "mappings"
    mappings.mkdir()
    (mappings / "b.rml.ttl").write_text(MAPPING % {"name": "Second", "predicate": "label"})
    (mappings / "a.rml.ttl").write_text(MAPPING % {"name": "First", "predicate": "name"})
    (mappings / "notes.txt").write_text("not a mapping")
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))

    def run(*arguments):
        return subprocess.run([sys.executable, "-m", "xsd2shacl", *arguments], cwd=tmp_path, env=env, capture_output=True, text=True)

    assert run("-i", str(shapes), "-r", str(mappings), "-a", "directory.ttl").returncode == 0
    g = Graph().parse(str(tmp_path / "directory.ttl"), format="turtle")
    EX = Namespace("http://example.org/")
    assert {EX.name, EX.label} <= set(g.objects(None, SH.path))
    # a.rml.ttl is processed before b.rml.ttl: its shapes keep the original identifiers
    assert EX.First in set(g.objects(None, SH.targetClass))
    assert g.value(Namespace("http://example.com/")["PropertyShape/Data/Point/Name/@Value"], SH.path) == EX.name
    # one mapping file, default output name
    assert run("-i", str(shapes), "-r", str(mappings / "a.rml.ttl")).returncode == 0
    single = Graph().parse(str(shapes) + ".a.rml.adjustment.ttl", format="turtle")
    assert EX.First in set(single.objects(None, SH.targetClass)) and EX.label not in set(single.objects(None, SH.path))
    # the variant option of the former scripts no longer exists
    assert run("-t", "RINF", "-i", str(shapes), "-r", str(mappings)).returncode != 0


def test_mapping_files_of_a_directory_are_sorted_by_name(tmp_path):
    from xsd2shacl.post_adjustment import mapping_files
    for name in ("b.ttl", "a.ttl", "c.rml", "d.txt"):
        (tmp_path / name).write_text("")
    assert [p.split("/")[-1] for p in mapping_files(str(tmp_path))] == ["a.ttl", "b.ttl", "c.rml"]
    assert mapping_files(str(tmp_path / "b.ttl")) == [str(tmp_path / "b.ttl")]
