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
import sys
import tokenize
import traceback

from typing import Dict, Optional, Tuple

from pegen.testutil import recovery_by_insertions, describe_token
from pegen.tokenizer import Tokenizer

from parse import GeneratedParser  # type: ignore[attr-defined]

argparser = argparse.ArgumentParser()
argparser.add_argument(
    "-n", "--number", type=int, default=1, help="Number of cases to try (default 1; 0=all)"
)
argparser.add_argument("-s", "--start", type=int, default=0, help="First case to try (default 0)")
argparser.add_argument(
    "-m",
    "--mode",
    default="all",
    choices=("all", "indent", "syntax", "tab"),
    help="What kind of cases to handle (default all)",
)
argparser.add_argument(
    "-d",
    "--dataset",
    default="data/parse_errors.json",
    help="JSON file containing the dataset (default data/parse_errors.json)",
)
argparser.add_argument(
    "--verify",
    action="store_true",
    help="Print items in the dataset where ast.parse and the item disagree",
)


error_types = {
    "all": ["IndentationError", "TabError", "SyntaxError"],
    "indent": ["IndentationError"],
    "tab": ["TabError"],
    "syntax": ["SyntaxError"],
}


def main() -> None:
    args = argparser.parse_args()
    with open(args.dataset) as f:
        dataset = json.load(f)
    keys = list(dataset)
    start = args.start
    number = args.number
    if number == 0:
        number = len(keys)
    number = min(number, len(keys) - start)
    if number <= 0:
        sys.exit(f"No cases selected; there are only {len(keys)} cases")
    skip_counts: Dict[str, int] = {}
    error_counts: Dict[str, int] = {}
    for i in range(start, start + number):
        item = dataset[keys[i]]
        syntax_err_line_no = item["syntax_err_line_no"]
        error_type = item["error_type"]
        if error_type not in error_types[args.mode]:
            ## print(f"Skipping {error_type}", file=sys.stderr)
            skip_counts[error_type] = skip_counts.get(error_type, 0) + 1
            continue
        error_message = item["error_message"]
        content = item["content"]

        if args.verify:
            if compare_ast_errors(content, syntax_err_line_no, error_type, error_message):
                ## print(f"{i}: all good", file=sys.stderr)
                skip_counts[error_type] = skip_counts.get(error_type, 0) + 1
                continue

        error_counts[error_type] = error_counts.get(error_type, 0) + 1

        print()
        print(f"===== {i} =====")
        ## pprint.pprint(item)
        print(f"Line {syntax_err_line_no}: {error_type}: {error_message}")
        print("  +-------------------------")
        print(indent(content, syntax_err_line_no))
        print("  +-------------------------")
        tester(content, try_ours=(not args.verify))
        print()

    print("===== skips by type =====", skip_counts, sep="\n", file=sys.stderr)
    print("===== errors by type =====", error_counts, sep="\n", file=sys.stderr)


def compare_ast_errors(source: str, lineno: int, excname: str, message: str) -> bool:
    err = try_ast_parse(source)
    if err is None:
        return False
    if err.__class__.__name__ != excname:
        # NOTE: "IndentationError: expected an indented block" is new, this
        # used to be "SyntaxError: unexpected EOF while parsing".
        if (
            excname == "SyntaxError"
            and message == "unexpected EOF while parsing"
            and isinstance(err, IndentationError)
            and err.msg == "expected an indented block"
        ):
            return True
        return False
    error_line = source.splitlines()[lineno - 1].strip()

    # NOTE: If there's an error on a line with just a triple quote,
    # the line numbers won't match because of difference in error
    # reporting between 3.6 and 3.8+.
    if error_line not in ('"""', "'''"):
        if err.lineno != lineno:
            return False

    if err.msg == message:
        return True

    # NOTE: "can't" was replaced by "cannot" in Python 3.8.
    if err.msg == message.replace("can't", "cannot"):
        return True

    # NOTE: "unmatched ']'" (or ')', or '}') is new, this used to be a
    # plain "invalid syntax".  Ditto for "closing parenthesis 'x' does not
    # match opening parenthesis 'u'.
    if message == "invalid syntax" and (
        err.msg.startswith("unmatched ") or err.msg.startswith("closing parenthesis ")
    ):
        return True

    # NOTE: Python 3.8 reports more specifics for non-ASCII quotes.
    if message == "invalid character in identifier" and err.msg.startswith("invalid character"):
        return True

    return False


def compare_our_errors(source: str, ast_err: Exception) -> bool:
    ## # 2) Pass it to our parser
    ## err, parser = try_our_parser(source)
    ## if err is None:
    ##     return False
    ## if err.__class__.__name__ != excname:
    ##     # We don't always raise IndentationError or TabError where we should
    ##     if excname in ("IndentationError", "TabError") and not isinstance(err, SyntaxError):
    ##         return False
    ## if err.lineno != lineno:
    ##     return False
    ## # Our message is almost always "pegen parse failure"

    return True


def tester(source: str, try_ours: bool) -> None:
    # 1) Pass it to ast.parse()
    err = try_ast_parse(source)
    if err is None:
        print("ast.parse(): NO PROBLEM")
    else:
        print("ast.parse():")
        print_exception(err)

    if not try_ours:
        return

    # 2) Pass it to GeneratedParser
    err, parser = try_our_parser(source)
    if err is None:
        print("our parser: NO PROBLEM")
    else:
        print("our parser:")
        print_exception(err)

        # 3) Try error correction
        error_correction(parser)


def try_ast_parse(source: str) -> Optional[Exception]:
    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        return err
    else:
        return None


def try_our_parser(source: str) -> Tuple[Optional[Exception], GeneratedParser]:
    file = io.StringIO(source)
    tokengen = tokenize.generate_tokens(file.readline)
    tokenizer = Tokenizer(tokengen)
    parser = GeneratedParser(tokenizer)
    try:
        tree = parser.file()
    except Exception as err:
        return err, parser
    if tree:
        ## pprint.pprint(tree)
        return None, parser
    else:
        return parser.make_syntax_error("<string>"), parser


def error_correction(parser: GeneratedParser) -> None:  # type: ignore[no-any-unimported]
    try:
        got, farthest, expected, howfar = recovery_by_insertions(parser)
    except SyntaxError as err:
        print("error recovery crashed!")
        print_exception(err)
        return
    if expected:
        print(
            f"Got {describe_token(got, parser)}, expected one of the following:",
            ", ".join(describe_token(tok, parser) for tok in expected),
            ## f"[reached {farthest}]",
        )
    else:
        print("Inserting something didn't help")


def print_exception(err: Exception) -> None:
    traceback.print_exception(err.__class__, err, None, file=sys.stdout)


def indent(content: str, lineno: int) -> str:
    lines = content.splitlines()
    indented = []
    for i, line in enumerate(lines, 1):
        if i == lineno:
            prefix = "==> "
        else:
            prefix = "  | "
        indented.append(prefix + line)
    return "\n".join(indented)


if __name__ == "__main__":
    main()
