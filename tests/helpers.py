import os
import subprocess
import sys

from rdflib import Graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPARISON = os.path.join(ROOT, "comparison")


def translate(xsd_path, output_path):
    """Translate an XSD file in a subprocess (the translator keeps global state) and return the shapes graph"""
    code = ("import sys; sys.path.insert(0, %r); from xsd2shacl.XSDtoSHACL import XSDtoSHACL; "
            "XSDtoSHACL().evaluate_file(%r, %r)" % (os.path.join(ROOT, "src"), str(xsd_path), str(output_path)))
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)
    return Graph().parse(str(output_path), format="turtle")
