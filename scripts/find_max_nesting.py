#!/usr/bin/env python3.8
"""Find the maximum amount of nesting for an expression that can be parsed
without causing a parse error.

Starting at the INITIAL_NESTING_DEPTH, an expression containing n parenthesis
around a 0 is generated then tested with both the C and Python parsers. We
continue incrementing the number of parenthesis by 10 until both parsers have
failed. As soon as a single parser fails, we stop testing that parser.

The grammar file, initial nesting size, and amount by which the nested size is
incremented on each success can be controlled by changing the GRAMMAR_FILE,
INITIAL_NESTING_DEPTH, or NESTED_INCR_AMT variables.

Usage: python -m scripts.find_max_nesting
"""
import os
import sys
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")
from pegen.build import build_parser
from pegen.testutil import generate_parser, generate_parser_c_extension, make_parser, parse_string

GRAMMAR_FILE = "data/simpy.gram"
INITIAL_NESTING_DEPTH = 10
NESTED_INCR_AMT = 10


FAIL = "\033[91m"
ENDC = "\033[0m"


def check_nested_expr(nesting_depth: int, parser: Any, language: str) -> bool:
    expr = f"{'(' * nesting_depth}0{')' * nesting_depth}"

    try:
        if language == "Python":
            parse_string(expr, parser)
        else:
            parser.parse_string(expr)

        print(f"({language}) Nesting depth of {nesting_depth} is successful")

        return True
    except Exception as err:
        print(f"{FAIL}({language}) Failed with nesting depth of {nesting_depth}{ENDC}")
        print(f"{FAIL}\t{err}{ENDC}")
        return False


def main() -> None:
    print(f"Testing {GRAMMAR_FILE} starting at nesting depth of {INITIAL_NESTING_DEPTH}...")

    with TemporaryDirectory() as tmp_dir:
        nesting_depth = INITIAL_NESTING_DEPTH
        rules, parser, tokenizer = build_parser(GRAMMAR_FILE)
        python_parser = generate_parser(rules)
        c_parser = generate_parser_c_extension(rules, Path(tmp_dir))

        c_succeeded = True
        python_succeeded = True

        while c_succeeded or python_succeeded:
            expr = f"{'(' * nesting_depth}0{')' * nesting_depth}"

            if c_succeeded:
                c_succeeded = check_nested_expr(nesting_depth, c_parser, "C")
            if python_succeeded:
                python_succeeded = check_nested_expr(nesting_depth, python_parser, "Python")

            nesting_depth += NESTED_INCR_AMT

        sys.exit(1)


if __name__ == "__main__":
    main()
