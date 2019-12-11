#!/usr/bin/env python3.8

"""Show the parse tree for a given program, nicely formatted.

Example:

$ scripts/show_parse.py a+b
Module(
    body=[
        Expr(
            value=BinOp(
                left=Name(id="a", ctx=Load()), op=Add(), right=Name(id="b", ctx=Load())
            )
        )
    ],
    type_ignores=[],
)
$

Use -v to show line numbers and column offsets.

The formatting is done using black.  You can also import this module
and call one of its functions.
"""

import argparse
import ast
import os
import sys
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="show line/column numbers")
parser.add_argument("program", nargs="+", help="program to parse (will be concatenated)")


def format_tree(tree: ast.AST, verbose: bool = False) -> str:
    with tempfile.NamedTemporaryFile("w+") as tf:
        tf.write(ast.dump(tree, include_attributes=verbose))
        tf.write("\n")
        tf.flush()
        os.system(f"black -q {tf.name}")
        tf.seek(0)
        return tf.read()


def show_parse(source: str, verbose: bool = False) -> str:
    tree = ast.parse(source)
    return format_tree(tree, verbose).rstrip("\n")


def print_parse(source: str, verbose: bool = False) -> None:
    print(show_parse(source, verbose))


def main() -> None:
    args = parser.parse_args()
    print_parse(" ".join(args.program), args.verbose)


if __name__ == "__main__":
    main()
