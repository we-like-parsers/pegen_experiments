import argparse
import os
import sys
import traceback

from pegen.build import build_parser_and_generator

SUCCESS = "\033[92m"
FAIL = "\033[91m"
ENDC = "\033[0m"

argparser = argparse.ArgumentParser(
    prog="test_parse_directory",
    description="Helper program to test directories or files for pegen",
)
argparser.add_argument(
    "-d", "--directory", help="Directory path containing files to test"
)
argparser.add_argument("-g", "--grammar-file", help="Grammar file path")
argparser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=0,
    help="Display detailed errors for failures",
)


def report_status(succeeded, file, verbose, error=None):
    if succeeded is True:
        status = "OK"
        COLOR = SUCCESS
    else:
        status = "Fail"
        COLOR = FAIL

    print(f"{COLOR}{file:50} {status}{ENDC}")

    if error and verbose:
        print(f"  {str(error.__class__.__name__)}: {error}")


def main():
    args = argparser.parse_args()
    directory = args.directory
    grammar_file = args.grammar_file
    verbose = args.verbose

    if not directory:
        print("You must specify a directory of files to test.")

    if grammar_file:
        if not os.path.exists(grammar_file):
            print(f"The specified grammar file, {grammar_file}, does not exist.")
            sys.exit(1)

        try:
            build_parser_and_generator(grammar_file, "pegen/parse.c", True)
        except Exception as err:
            print(
                f"{FAIL}The following error occurred when generating the parser. Please check your grammar file.\n{ENDC}"
            )
            traceback.print_exception(err.__class__, err, None)

            sys.exit(1)

    else:
        print("A grammar file was not provided - attempting to use existing file...\n")

    try:
        from pegen import parse
    except:
        print(
            "An existing parser was not found. Please run `make` or specify a grammar file with the `-g` flag."
        )
        sys.exit(1)

    # For a given directory, traverse files and attempt to parse each one
    # - Output success/failure for each file
    success = True
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Only attempt to parse Python files
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            try:
                parse.parse_file(file_path)
                report_status(succeeded=True, file=file_path, verbose=verbose)
            except Exception as error:
                report_status(
                    succeeded=False, file=file_path, verbose=verbose, error=error
                )
                success = False

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
