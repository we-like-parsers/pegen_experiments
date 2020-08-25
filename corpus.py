# Play with a corpus of syntax errors.
#
# Corpus: https://doi.org/10.6084/m9.figshare.8244686.v1
# Paper:
#   Alexander William Wong, Amir Salimi, Shaiful Chowdhury, Abram Hindle:
#   Syntax and Stack Overflow: A methodology for extracting a corpus of syntax errors and fixes
#   arXiv:1907.07803 [cs.SE]
#   https://arxiv.org/abs/1907.07803
#
# Prerequisites:
# - Copy the parse_errors.json file from the corpus in the data directory
#   (It is too large to commit into this repo -- 46M uncompressed, 12M compressed)
# - run pegen like this:
#   python -m pegen -q python --skip-actions data/python.gram
#
# You can then run this script like this:
# - python corpus.py [-h] [-n NUMBER] [-d DATASET]

import argparse
import ast
import io
import json
import pprint
import tokenize
import traceback

from typing import Dict

from pegen.testutil import recovery_by_insertions, describe_token
from pegen.tokenizer import Tokenizer

from parse import GeneratedParser  # type: ignore[attr-defined]

argparser = argparse.ArgumentParser()
argparser.add_argument(
    "-n", "--number", type=int, default=10, help="Number of cases to try (default 10; 0=all)"
)
argparser.add_argument(
    "-d",
    "--dataset",
    default="data/parse_errors.json",
    help="JSON file containing the dataset (default data/parse_errors.json)",
)
# TODO: Arguments to select a single case, or a range, or a random sample


def main() -> None:
    args = argparser.parse_args()
    with open(args.dataset) as f:
        dataset = json.load(f)
    keys = list(dataset)
    number = args.number
    if number == 0:
        number = len(keys)
    error_counts: Dict[str, int] = {}
    for i in range(number):
        item = dataset[keys[i]]
        syntax_err_line_no = item["syntax_err_line_no"]
        error_type = item["error_type"]
        ## if error_type != "SyntaxError":
        ##     continue
        error_message = item["error_message"]
        error_counts[error_type] = error_counts.get(error_type, 0) + 1
        content = item["content"]
        print("=====", i, "=====")
        ## pprint.pprint(item)
        print(f"Line {syntax_err_line_no}: {error_type}: {error_message}")
        print(indent(content, syntax_err_line_no))
        tester(content)

    print()
    print("===== errors by type =====")
    print(error_counts)


def tester(source: str) -> None:
    # TODO: Be silent if (1) and (2) produce matching error locations.

    # 1) Pass it to ast.parse()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        err = e
        print("ast.parse():")
        traceback.print_exception(err.__class__, err, None)
    else:
        print("ast.parse(): NO PROBLEM")

    # 2) Pass it to GeneratedParser
    file = io.StringIO(source)
    tokengen = tokenize.generate_tokens(file.readline)
    tokenizer = Tokenizer(tokengen)
    parser = GeneratedParser(tokenizer)
    tree = parser.file()
    if tree:
        print("our parser: NO PROBLEM")
        ## pprint.pprint(tree)
    else:
        print("our parser:")
        err = parser.make_syntax_error("<string>")
        traceback.print_exception(err.__class__, err, None)

    # 3) Try error correction
    if not tree:
        error_correction(parser)


def error_correction(parser: GeneratedParser) -> None:  # type: ignore[no-any-unimported]
    got, farthest, expected, howfar = recovery_by_insertions(parser)
    if expected:
        print(
            f"Got {describe_token(got, parser)}, expected one of the following:",
            ", ".join(describe_token(tok, parser) for tok in expected),
            ## f"[reached {farthest}]",
        )
    else:
        print("Inserting something didn't help")


def indent(content: str, lineno: int) -> str:
    lines = content.splitlines()
    indented = []
    for i, line in enumerate(lines, 1):
        if i == lineno:
            prefix = "==> "
        else:
            prefix = "    "
        indented.append(prefix + line)
    return "\n".join(indented)


if __name__ == "__main__":
    main()
