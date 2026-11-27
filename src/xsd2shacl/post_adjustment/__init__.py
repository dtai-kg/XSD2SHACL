import os

from rdflib import Graph

from .shape_adjustment_single import ShapeAdjustment


def mapping_files(rml_path):
    """The mapping file itself, or the mapping files of a directory sorted by file name"""
    if os.path.isdir(rml_path):
        return [os.path.join(rml_path, name) for name in sorted(os.listdir(rml_path))
                if name.endswith(".ttl") or name.endswith(".rml")]
    return [rml_path]


def post_adjust(shacl_input_path, rml_path, adjusted_path):
    """Adjust the shapes translated from an XSD with the RML mappings of the same XML source.
    The adjustment accumulates state over the mapping files, which are processed in the order
    of their file names"""
    adjustment = ShapeAdjustment("xml")
    shapes = Graph().parse(shacl_input_path, format="turtle")
    adjustment.parseRawDataSchemaShape(shapes)
    for mapping in mapping_files(rml_path):
        adjustment.parseRML(Graph().parse(mapping, format="turtle"))
        adjustment.adjust(Graph() + shapes)
    adjustment.writeShapeToFile(adjusted_path)
    return adjustment.adjusted_graph
