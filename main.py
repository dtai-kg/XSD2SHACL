import argparse
from src.XSDtoSHACL import XSDtoSHACL
from src.adjustment import Adjustment

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')
    parser.add_argument("-x", "--xsd", help='XSD file to be translated', type=str, default=None)
    parser.add_argument("-s", "--shacl", help='SHACL path to do adjustment', type=str, default=None)
    parser.add_argument("-r", "--rml", help='rml mapping file path to do adjustment', type=str, default=None)
    args = parser.parse_args()

    if args.xsd:

        print("##### Start translate XSD to SHACL")
        X2S = XSDtoSHACL()
        X2S.evaluate_file(args.xsd_file)
        SHACL_path = args.xsd_file + ".shape.ttl"

    else:
        SHACL_path = args.shacl

    if args.rml:
        if args.rml.endswith(".ttl"):
            destination_path = SHACL_path+"." +args.rml.split(".ttl")[0].split("\\")[-1].split("/")[-1] +".adjustment.ttl"
        else:
            destination_path = SHACL_path+"." +args.rml.split("\\")[-1] +".adjustment.ttl"
        ADJ = Adjustment()
        print("##### Start load SHACL shape")
        ADJ.loadMapping(SHACL_path, args.rml)
        print("##### Start adjust SHACL shape")
        SHACL_g = ADJ.adjust()
        SHACL_g.serialize(destination=destination_path, format='turtle')
        print("##### Saved adjusted SHACL shape to: " + destination_path)