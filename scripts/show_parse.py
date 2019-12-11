#!/usr/bin/env python3.8

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


def main():
    args = parser.parse_args()
    print_parse(" ".join(args.program), args.verbose)


if __name__ == "__main__":
    main()
