#!/usr/bin/env python3

import argparse
import io
import pprint
import sys
import token
import tokenize
import traceback

from data.python_parser import GeneratedParser
from pegen.tokenizer import Tokenizer
from pegen.testutil import (
    describe_token,
    make_improved_syntax_error,
    recovery_by_deletions,
    recovery_by_insertions,
)


# A variation of simple_parser_main() in pegen/parser.py.
def main() -> None:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-c", dest="command", help="command to run (default read a file)")
    argparser.add_argument("-n", dest="nope", action="store_true", help="don't print AST")
    argparser.add_argument("filename", nargs="?", help="Input file ('-' to use stdin)")

    args = argparser.parse_args()

    if command := args.command:
        if args.filename:
            argparser.error("Use either -c or filename, not both")
        filename = "<string>"
        file = io.StringIO(command)
    else:
        filename = args.filename
        if not filename:
            argparser.error("Exactly one of -c and filename is required")
        if filename == "" or filename == "-":
            filename = "<stdin>"
            file = sys.stdin
        else:
            file = open(args.filename)
    try:
        tokengen = tokenize.generate_tokens(file.readline)
        tokenizer = Tokenizer(tokengen)
        parser = GeneratedParser(tokenizer)
        try:
            tree = parser.start()
        except Exception as err:
            traceback.print_exception(err.__class__, err, None)
            sys.exit(1)
        if not tree:
            print("----- raw error -----")
            err = parser.make_syntax_error(filename)
            traceback.print_exception(err.__class__, err, None)
            print("----- improved error -----")
            err = make_improved_syntax_error(parser, filename)
            traceback.print_exception(err.__class__, err, None)
            print("----- raw error correction by insertion -----")
            got, reach, expected, howfar = recovery_by_insertions(parser)
            if expected:
                print(
                    f"Got {describe_token(got, parser)}, expected one of the following:",
                    ", ".join(describe_token(tok, parser) for tok in expected),
                    f"[reached {reach}]",
                )
            print("----- raw error correction by deletion -----")
            results = recovery_by_deletions(parser)
            for tok, backup, pos, reach in results:
                print(f"Excess token {describe_token(tok, parser)} at pos-{backup} deleted")
            sys.exit(1)
    finally:
        if file is not sys.stdin:
            file.close()

    if not args.nope:
        pprint.pprint(tree, indent=2)


if __name__ == "__main__":
    main()
