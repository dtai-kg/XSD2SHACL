import argparse
from src.XSDtoSHACL import XSDtoSHACL
from src.adjustment import Adjustment

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')
    parser.add_argument("xsd_file",  help='xsd_file', type=str)
    parser.add_argument("-r", "--rml", help='rml mapping file path to do adjustment', type=str, default=None)
    args = parser.parse_args()

    print("##### Start translate XSD to SHACL")
    X2S = XSDtoSHACL()
    X2S.evaluate_file(args.xsd_file)
    SHACL_path = args.xsd_file + ".shape.ttl"

    if args.rml:
        ADJ = Adjustment()
        ADJ.loadMapping(SHACL_path, args.rml)
        print("##### Start adjust SHACL shape")
        SHACL_g = ADJ.adjust()
        SHACL_g.serialize(destination=SHACL_path+"." +args.rml.split("\\")[-1] +".adjustment.ttl", format='turtle')