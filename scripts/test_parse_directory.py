#!/usr/bin/env python3.8

import argparse
import os
import sys
import time
import traceback
from glob import glob
from pathlib import PurePath

from typing import Optional

sys.path.insert(0, ".")
from pegen.build import build_parser_and_generator
from pegen.testutil import print_memstats

SUCCESS = "\033[92m"
FAIL = "\033[91m"
ENDC = "\033[0m"

argparser = argparse.ArgumentParser(
    prog="test_parse_directory",
    description="Helper program to test directories or files for pegen",
)
argparser.add_argument("-d", "--directory", help="Directory path containing files to test")
argparser.add_argument("-g", "--grammar-file", help="Grammar file path")
argparser.add_argument(
    "-e", "--exclude", action="append", default=[], help="Glob(s) for matching files to exclude"
)
argparser.add_argument(
    "-s", "--short", action="store_true", help="Only show errors, in a more Emacs-friendly format"
)
argparser.add_argument(
    "-v", "--verbose", action="store_true", default=0, help="Display detailed errors for failures"
)


def report_status(
    succeeded: bool,
    file: str,
    verbose: bool,
    error: Optional[Exception] = None,
    short: bool = False,
) -> None:
    if short and succeeded:
        return

    if succeeded is True:
        status = "OK"
        COLOR = SUCCESS
    else:
        status = "Fail"
        COLOR = FAIL

    if short:
        lineno = 0
        offset = 0
        if isinstance(error, SyntaxError):
            lineno = error.lineno or 1
            offset = error.offset or 1
            message = error.args[0]
        else:
            message = f"{error.__class__.__name__}: {error}"
        print(f"{file}:{lineno}:{offset}: {message}")
    else:
        print(f"{COLOR}{file:60} {status}{ENDC}")

        if error and verbose:
            print(f"  {str(error.__class__.__name__)}: {error}")


def main() -> None:
    args = argparser.parse_args()
    directory = args.directory
    grammar_file = args.grammar_file
    verbose = args.verbose
    excluded_files = args.exclude

    if not directory:
        print("You must specify a directory of files to test.", file=sys.stderr)
        sys.exit(1)

    if grammar_file:
        if not os.path.exists(grammar_file):
            print(f"The specified grammar file, {grammar_file}, does not exist.", file=sys.stderr)
            sys.exit(1)

        try:
            build_parser_and_generator(grammar_file, "pegen/parse.c", True)
        except Exception as err:
            print(
                f"{FAIL}The following error occurred when generating the parser. Please check your grammar file.\n{ENDC}",
                file=sys.stderr,
            )
            traceback.print_exception(err.__class__, err, None)

            sys.exit(1)

    else:
        print("A grammar file was not provided - attempting to use existing file...\n")

    try:
        from pegen import parse
    except:
        print(
            "An existing parser was not found. Please run `make` or specify a grammar file with the `-g` flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    # For a given directory, traverse files and attempt to parse each one
    # - Output success/failure for each file
    errors = 0
    files = []

    t0 = time.time()
    for file in sorted(glob(f"{directory}/**/*.py", recursive=True)):
        # Only attempt to parse Python files and files that are not excluded
        should_exclude_file = False
        for pattern in excluded_files:
            if PurePath(file).match(pattern):
                should_exclude_file = True
                break

        if not should_exclude_file:
            try:
                parse.parse_file(file)
                if not args.short:
                    report_status(succeeded=True, file=file, verbose=verbose)
            except Exception as error:
                report_status(
                    succeeded=False, file=file, verbose=verbose, error=error, short=args.short
                )
                errors += 1
            files.append(file)
    t1 = time.time()

    total_seconds = t1 - t0
    total_files = len(files)

    total_bytes = 0
    total_lines = 0
    for file in files:
        # Count lines and bytes separately
        with open(file, "rb") as f:
            total_lines += sum(1 for _ in f)
            total_bytes += f.tell()

    print(
        f"Checked {total_files:,} files, {total_lines:,} lines,",
        f"{total_bytes:,} bytes in {total_seconds:,.3f} seconds.",
    )
    if total_seconds > 0:
        print(
            f"That's {total_lines / total_seconds :,.0f} lines/sec,",
            f"or {total_bytes / total_seconds :,.0f} bytes/sec.",
        )

    if args.short:
        print_memstats()

    if errors:
        print(f"Encountered {errors} failures.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
