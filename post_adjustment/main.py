import argparse
import os
from adjustment_RINF import Adjustment_RINF
from adjustment_TED import Adjustment_TED

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SHACL shapes post-adjustment')

    parser.add_argument("SHACL_FILE", type=str,
                        help="SHACL file to be post-adjusted.")
    parser.add_argument("--RML_PATH", "-r", type=str,
                        help="The RML file or dictionary used to conduct post-adjustment")
    parser.add_argument("--ADJUSTED_PATH", "-a", type=str,
                        help="The path used to store the post-adjusted SHACL shapes, the default is SHACL_FILE.RML_FILENAME.adjustment.ttl")

    args = parser.parse_args()

    if args.ADJUSTED_PATH:
        destination_path = args.ADJUSTED_PATH
    else:
        if args.RML_PATH.endswith(".ttl"):
            destination_path = SHACL_path+"." +args.RML_PATH.split(".ttl")[0].split("\\")[-1].split("/")[-1] +".adjustment.ttl"
        else:
            destination_path = SHACL_path+"." +args.RML_PATH.split("\\")[-1] +".adjustment.ttl"

    if "TED" in args.RML_PATH:
        ADJ = Adjustment_TED()
    else:
        ADJ = Adjustment_RINF()
    print("##### Start load SHACL shape")
   
    if args.RML_PATH.endswith(".ttl"):
        rml_path = args.RML_PATH
    else:
        rml_path = [args.RML_PATH + "/" + i for i in os.listdir(args.RML_PATH)]

    ADJ.loadMapping(args.SHACL_FILE, rml_path)
    print("##### Start adjust SHACL shape")
    SHACL_g = ADJ.adjust()
    SHACL_g.serialize(destination=destination_path, format='turtle')
    print("##### Saved adjusted SHACL shape to: " + destination_path)