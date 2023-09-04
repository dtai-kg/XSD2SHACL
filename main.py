import argparse
import os
from src.XSDtoSHACL import XSDtoSHACL
# from src.adjustment_RINF import Adjustment_RINF
# from src.adjustment_TED import Adjustment_TED
import time


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')

    parser.add_argument("XSD_FILE", type=str,
                        help="XSD file to be converted into SHACL shapes.")
    parser.add_argument("--SHACL_PATH", "-s", type=str,
                        help="The path used to store the generated SHACL shapes, the default is XSD_FILE.shape.ttl")

    args = parser.parse_args()

    # if args.xsd:
    X2S = XSDtoSHACL()
    if args.SHACL_PATH:
        X2S.evaluate_file(args.XSD_FILE, args.SHACL_PATH)
    else:
        X2S.evaluate_file(args.XSD_FILE)
    # SHACL_path = args.xsd + ".shape.ttl"

    # else:
    #     SHACL_path = args.shacl

    # if args.rml:
    #     if args.rml.endswith(".ttl"):
    #         destination_path = SHACL_path+"." +args.rml.split(".ttl")[0].split("\\")[-1].split("/")[-1] +".adjustment.ttl"
    #     else:
    #         # destination_path = SHACL_path+"." +args.rml.split("\\")[-1] +".adjustment.ttl"
    #         destination_path = args.destination
    #     if "TED" in args.rml:
    #         ADJ = Adjustment_TED()
    #     else:
    #         ADJ = Adjustment()
    #     print("##### Start load SHACL shape")
    #     if "TED" in args.rml:
    #         rml_path = [args.rml + "/" + i for i in os.listdir(args.rml)]
    #     else:
    #         rml_path = args.rml
    #     ADJ.loadMapping(SHACL_path, rml_path)
    #     print("##### Start adjust SHACL shape")
    #     SHACL_g = ADJ.adjust()
    #     SHACL_g.serialize(destination=destination_path, format='turtle')
    #     print("##### Saved adjusted SHACL shape to: " + destination_path)