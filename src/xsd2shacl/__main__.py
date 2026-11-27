import argparse, os
from .XSDtoSHACL import XSDtoSHACL
from .post_adjustment import post_adjust


def define_args():
    parser = argparse.ArgumentParser(description='Translate XSD to SHACL')

    parser.add_argument("--XSD_FILE","-x", type=str, help="XSD file to be converted into SHACL shapes.")
    parser.add_argument("--SHACL_OUTPUT_PATH", "-s", type=str, help="The path used to store the generated SHACL shapes, the default is XSD_FILE.shape.ttl")

    parser.add_argument("--SHACL_INPUT_PATH", "-i", type=str, help="SHACL file to be post-adjusted.")
    parser.add_argument("--RML_PATH", "-r", type=str, help="The RML file or directory used to conduct post-adjustment")
    parser.add_argument("--ADJUSTED_PATH", "-a", type=str, help="The path used to store the post-adjusted SHACL shapes, the default is SHACL_INPUT_PATH.RML_FILENAME.adjustment.ttl")

    return parser.parse_args()


def default_adjusted_path(shacl_input_path, rml_path):
    if rml_path.endswith(".ttl"):
        return shacl_input_path + "." + os.path.basename(rml_path).split(".ttl")[0] + ".adjustment.ttl"
    return shacl_input_path + "." + os.path.basename(rml_path.rstrip("/\\")) + ".adjustment.ttl"


if __name__ == "__main__":

    args = define_args()

    xsd2shacl = XSDtoSHACL()

    if args.XSD_FILE and args.SHACL_OUTPUT_PATH:
        xsd2shacl.evaluate_file(args.XSD_FILE, args.SHACL_OUTPUT_PATH)

    elif args.XSD_FILE:
        xsd2shacl.evaluate_file(args.XSD_FILE)

    elif args.SHACL_INPUT_PATH:
        if not args.RML_PATH:
            raise SystemExit("Post-adjustment requires --RML_PATH")
        destination_path = args.ADJUSTED_PATH or default_adjusted_path(args.SHACL_INPUT_PATH, args.RML_PATH)

        print("##### Start adjust SHACL shape")
        post_adjust(args.SHACL_INPUT_PATH, args.RML_PATH, destination_path)
        print("##### Saved adjusted SHACL shape to: " + destination_path)
