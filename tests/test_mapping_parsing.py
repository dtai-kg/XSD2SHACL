"""Parsing of the mappings by the post-adjustment (XPath functions, term types, union iterators,
conditional classes) and removal of shapes with long lists."""
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.collection import Collection
from rdflib.namespace import RDF

from xsd2shacl.post_adjustment.shape_adjustment_single import ShapeAdjustment

SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.org/")

PREFIXES = """
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix ex: <http://example.org/> .
"""


def parsed(mapping):
    sa = ShapeAdjustment("xml")
    sa.parseRML(Graph().parse(data=PREFIXES + mapping, format="turtle"))
    return sa


def source(iterator):
    return f'rml:logicalSource [ rml:source "data.xml" ; rml:referenceFormulation ql:XPath ; rml:iterator "{iterator}" ]'


def test_xpath_function_names_are_matched_as_whole_names():
    sa = ShapeAdjustment("xml")
    sa.iterator = "/a"
    # "string" is not matched inside "substring" (or "substring-after")
    assert sa.parseReference_xml("substring(b, 1, 4)") == [["/a/b"]]
    assert sa.parseReference_xml("substring-after(c, '-')") == [["/a/c"]]
    assert sa.parseReference_xml("string(d)") == [["/a/d"]]
    assert sa.parseTemplate_xml("http://example.org/{substring(b, 1, 4)}/{string-length(c)}/{e}") == [["/a/b", "/a/c", "/a/e"]]


def test_template_object_map_without_term_type_is_an_iri():
    sa = parsed('ex:M a rr:TriplesMap ; ' + source("/a") + ' ; rr:subjectMap [ rr:template "http://example.org/a/{id}" ] ; '
                'rr:predicateObjectMap [ rr:predicate ex:p ; rr:objectMap [ rr:template "http://example.org/b/{b}" ] ] ; '
                'rr:predicateObjectMap [ rr:predicate ex:q ; rr:objectMap [ rr:template "{c} {d}" ; rr:termType rr:Literal ] ] ; '
                'rr:predicateObjectMap [ rr:predicate ex:r ; rr:objectMap [ rml:reference "e" ] ] .')
    term_types = {pom["property"]: pom["termType"] for pom in sa.rml_parsed[EX.M]["pom"]}
    assert term_types == {EX.p: SH.IRI, EX.q: SH.Literal, EX.r: None}


def test_union_iterator_is_parsed_once_per_alternative():
    sa = parsed('ex:M a rr:TriplesMap ; ' + source("/a/b | /a/c") + ' ; rr:subjectMap [ rr:template "http://example.org/x/{id}" ; rr:class ex:X ] ; '
                'rr:predicateObjectMap [ rr:predicate ex:p ; rr:objectMap [ rml:reference "v" ] ] .')
    assert sorted(sa.rml_parsed, key=str) == [(EX.M, 0), (EX.M, 1)]
    assert [sa.rml_parsed[(EX.M, k)]["iterator"] for k in (0, 1)] == ["/a/b", "/a/c"]
    assert [sa.rml_parsed[(EX.M, k)]["sm"]["path"] for k in (0, 1)] == [[["/a/b/id"]], [["/a/c/id"]]]
    assert [sa.rml_parsed[(EX.M, k)]["pom"][0]["path"] for k in (0, 1)] == [[["/a/b/v"]], [["/a/c/v"]]]


def test_classes_are_taken_from_a_conditional_type_expression():
    sa = parsed('ex:M a rr:TriplesMap ; ' + source("/a") + ' ; rr:subjectMap [ rr:template "http://example.org/a/{id}" ] ; '
                'rr:predicateObjectMap [ rr:predicate rdf:type ; rr:objectMap [ rml:reference '
                '"if (kind = \'x\') then \'http://example.org/X\' else \'http://example.org/Y\'" ; rr:termType rr:IRI ] ] ; '
                'rr:predicateObjectMap [ rr:predicate rdf:type ; rr:objectMap [ rr:constant ex:Z ] ] .')
    assert sorted(sa.rml_parsed[EX.M]["sm"]["classes"], key=str) == [EX.X, EX.Y, EX.Z]
    assert sa.rml_parsed[EX.M]["pom"] == []


def test_removing_a_shape_removes_its_long_lists_without_recursion():
    sa = ShapeAdjustment("xml")
    g = sa.initial_graph = Graph()
    removed, kept, shared = EX.removed, EX.kept, BNode()
    Collection(g, shared, [Literal("shared")])
    head = BNode()
    Collection(g, head, [Literal(i) for i in range(5000)])  # deeper than the recursion limit
    g.add((removed, SH["in"], head))
    g.add((removed, SH.languageIn, shared))
    g.add((kept, SH.languageIn, shared))
    g.add((kept, SH.node, removed))
    sa.remove_graph([removed])
    # only the shape that is kept and the list it shares are left
    assert set(g.subjects()) - set(g.subjects(RDF.first, None)) == {kept}
    assert (kept, SH.node, removed) not in g
    assert list(Collection(g, shared)) == [Literal("shared")]
    assert len(g) == 3
