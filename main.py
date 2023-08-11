import argparse
from src.XSDtoSHACL import XSDtoSHACL

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')
    parser.add_argument("xsd_file",  help='xsd_file', type=str)
    args = parser.parse_args()

    X2S = XSDtoSHACL()
    X2S.evaluate_file(args.xsd_file)