import argparse
import os
import pegen
import sys

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
    verbose = args.verbose

    if not directory:
        print("You must specify a directory of files to test.")

    try:
        from pegen import parse
    except:
        print(f"An existing parser was not found. Please run `make`.")
        sys.exit()

    # For a given directory, traverse files and attempt to parse each one
    # - Output success/failure for each file
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Only attempt to parse Python files
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            try:
                t = parse.parse_file(file_path)
                report_status(succeeded=True, file=file_path, verbose=verbose)
            except Exception as error:
                report_status(
                    succeeded=False, file=file_path, verbose=verbose, error=error
                )


if __name__ == "__main__":
    main()
