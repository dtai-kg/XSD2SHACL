import argparse
import os
from src.XSDtoSHACL import XSDtoSHACL
import time


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')

    parser.add_argument("XSD_FILE", type=str,
                        help="XSD file to be converted into SHACL shapes.")
    parser.add_argument("--SHACL_PATH", "-s", type=str,
                        help="The path used to store the generated SHACL shapes, the default is XSD_FILE.shape.ttl")

    args = parser.parse_args()

    X2S = XSDtoSHACL()
    if args.SHACL_PATH:
        X2S.evaluate_file(args.XSD_FILE, args.SHACL_PATH)
    else:
        X2S.evaluate_file(args.XSD_FILE)
