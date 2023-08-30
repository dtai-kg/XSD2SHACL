import argparse
import os
from src.XSDtoSHACL import XSDtoSHACL
from src.XSDtoSHACL_alignedShEx import XSDtoSHACL_alignedShEx
from src.adjustment import Adjustment
from src.adjustment_TED import Adjustment_TED
import time
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')
    parser.add_argument("-x", "--xsd", help='XSD file to be translated', type=str, default=None)
    parser.add_argument("-s", "--shacl", help='SHACL path to do adjustment', type=str, default=None)
    parser.add_argument("-r", "--rml", help='rml mapping file path to do adjustment', type=str, default=None)
    parser.add_argument("-a", "--aligned", help='aligned ShEx file path to do adjustment', type=str, default=None)
    parser.add_argument("-d", "--destination", help='aligned ShEx file path to do adjustment', type=str, default=None)
    args = parser.parse_args()

    if args.aligned:
        if args.xsd:
            print("##### Start translate XSD to aligned ShEx")
            start = time.time()
            X2S = XSDtoSHACL_alignedShEx()
            X2S.evaluate_file(args.xsd)
            end = time.time()
            print("##### Time cost: " + str(end - start))
            SHACL_path = args.xsd + ".shape.alignedShEx.ttl"
    else:
        if args.xsd:

            print("##### Start translate XSD to SHACL")
            start = time.time()
            X2S = XSDtoSHACL()
            X2S.evaluate_file(args.xsd)
            SHACL_path = args.xsd + ".shape.ttl"
            end = time.time()
            print("##### Time cost: " + str(end - start))

        else:
            SHACL_path = args.shacl

    if args.rml:
        if args.rml.endswith(".ttl"):
            destination_path = SHACL_path+"." +args.rml.split(".ttl")[0].split("\\")[-1].split("/")[-1] +".adjustment.ttl"
        else:
            # destination_path = SHACL_path+"." +args.rml.split("\\")[-1] +".adjustment.ttl"
            destination_path = args.destination
        if "TED" in args.rml:
            ADJ = Adjustment_TED()
        else:
            ADJ = Adjustment()
        print("##### Start load SHACL shape")
        if "TED" in args.rml:
            rml_path = [args.rml + "/" + i for i in os.listdir(args.rml)]
        else:
            rml_path = args.rml
        ADJ.loadMapping(SHACL_path, rml_path)
        print("##### Start adjust SHACL shape")
        SHACL_g = ADJ.adjust()
        SHACL_g.serialize(destination=destination_path, format='turtle')
        print("##### Saved adjusted SHACL shape to: " + destination_path)