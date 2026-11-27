"""Test helpers: validate XML against an XSD with xmllint, and convert XML to RDF under the
assumptions of XSD2SHACL (every complex element is a resource typed with the element name,
simple elements and attributes become properties with literals typed by the XSD built-in type,
the text of a simple-content element is a property named after the element, nested complex
elements are linked by a property named after the child element)."""
import subprocess
import xml.etree.ElementTree as ET

import xmlschema
from rdflib import Graph, Literal, Namespace, RDF, XSD

XS = "{http://www.w3.org/2001/XMLSchema}"


def xmllint_valid(xsd_path, xml_path):
    result = subprocess.run(["xmllint", "--noout", "--schema", str(xsd_path), str(xml_path)], capture_output=True, text=True)
    return result.returncode == 0


def builtin_name(xsd_type):
    """Local name of the nearest built-in type a simple type derives from"""
    while xsd_type is not None:
        if xsd_type.name and xsd_type.name.startswith(XS):
            return xsd_type.name[len(XS):]
        xsd_type = getattr(xsd_type, "base_type", None)
    return None


def literal(text, xsd_type):
    name = builtin_name(xsd_type)
    if name is None or name in ("anySimpleType", "anyType", "string"):
        return Literal(text)  # xs:string values are plain literals, as the translator types them
    return Literal(text, datatype=XSD[name])


def local(tag):
    return tag.split("}")[-1]


def xml_to_rdf(xsd_path, xml_path, namespace="http://example.com/"):
    schema = xmlschema.XMLSchema(str(xsd_path))
    ns = Namespace(namespace)
    g = Graph()
    counter = [0]

    def find_child_declaration(xsd_element, name):
        content = getattr(xsd_element.type, "content", None)
        if content is None or not hasattr(content, "iter_elements"):
            return None
        for candidate in content.iter_elements():
            if local(candidate.name) == name:
                return candidate
        return None

    def visit(element, xsd_element):
        counter[0] += 1
        name = local(element.tag)
        subject = ns[f"{name}_{counter[0]}"]
        g.add((subject, RDF.type, ns[name]))
        attributes = getattr(xsd_element.type, "attributes", {})
        for attribute, value in element.attrib.items():
            declaration = attributes.get(local(attribute))
            g.add((subject, ns[local(attribute)], literal(value, declaration.type if declaration is not None else None)))
        if xsd_element.type.has_simple_content():
            g.add((subject, ns[name], literal(element.text or "", xsd_element.type.content)))
        for child in element:
            child_name = local(child.tag)
            declaration = find_child_declaration(xsd_element, child_name)
            if declaration is not None and declaration.type.is_simple():
                g.add((subject, ns[child_name], literal(child.text or "", declaration.type)))
            else:
                g.add((subject, ns[child_name], visit(child, declaration)))
        return subject

    root = ET.parse(str(xml_path)).getroot()
    visit(root, schema.elements[local(root.tag)])
    return g
