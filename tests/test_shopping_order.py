"""Nested complex elements are linked through property shapes, so a parent resource is not
required to carry the properties of its children (comparison/xmlschema2shex/example.xsd)."""
import os

import pytest
from pyshacl import validate
from rdflib import Graph

from helpers import COMPARISON, translate

PREFIXES = """
@prefix : <http://tempuri.org/po.xsd#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""
DATA_A = PREFIXES + """
:order1 a :items ; :item :i1 .
:i1 a :item ; :productName "Lapis necklace" ; :USPrice "99.95"^^xsd:decimal .
"""
DATA_B = PREFIXES + """
:order1 a :items ; :item :i1, :i2 .
:i1 a :item ; :productName "Lapis necklace" ; :USPrice "99.95"^^xsd:decimal .
:i2 a :item ; :productName "Baby Monitor" ; :USPrice "39.98"^^xsd:decimal .
"""
DATA_C = PREFIXES + """
:order1 a :items .
"""
DATA_D = PREFIXES + """
:order1 a :items ; :item :i1 .
:i1 a :item ; :productName "Lapis necklace" .
"""


@pytest.fixture(scope="module")
def shapes(tmp_path_factory):
    out = tmp_path_factory.mktemp("example") / "example.shape.ttl"
    return translate(os.path.join(COMPARISON, "xmlschema2shex", "example.xsd"), out)


@pytest.mark.parametrize("data, expected", [(DATA_A, True), (DATA_B, True), (DATA_C, True), (DATA_D, False)],
                         ids=["one item", "two items", "empty order", "item without price"])
def test_shopping_order_validation(shapes, data, expected):
    conforms, _, text = validate(Graph().parse(data=data, format="turtle"), shacl_graph=shapes)
    assert conforms is expected, text
