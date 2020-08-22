import argparse
import pprint
import sys
import time
import token
import tokenize
import traceback

from pegen.tokenizer import Tokenizer

from parse import GeneratedParser


def describe(tok: tokenize.TokenInfo, parser: GeneratedParser) -> str:
    if tok.type == token.ERRORTOKEN:
        return repr(tok.string)
    if tok.type == token.OP:
        return repr(tok.string)
    if tok.type == token.AWAIT:
        return "'await'"
    if tok.type == token.ASYNC:
        return "'async'"
    if tok.string in parser._keywords:
        return repr(tok.string)
    return token.tok_name[tok.type]


# A variation of simple_parser_main() in pegen/parser.py.
def main() -> None:
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Print timing stats; repeat for more debug output",
    )
    argparser.add_argument(
        "-q", "--quiet", action="store_true", help="Don't print the parsed program"
    )
    argparser.add_argument("filename", help="Input file ('-' to use stdin)")

    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4

    t0 = time.time()

    filename = args.filename
    if filename == "" or filename == "-":
        filename = "<stdin>"
        file = sys.stdin
    else:
        file = open(args.filename)
    try:
        tokengen = tokenize.generate_tokens(file.readline)
        tokenizer = Tokenizer(tokengen, verbose=verbose_tokenizer)
        parser = GeneratedParser(tokenizer, verbose=verbose_parser)
        tree = parser.file()
        if not tree:
            err = parser.make_syntax_error(filename)
            traceback.print_exception(err.__class__, err, None)
            # Error recovery
            howfar = {}
            pos = len(tokenizer._tokens) - 1
            got = tokenizer._tokens[pos]
            for i in range(100):
                parser.reset(0)
                parser.reset_farthest(0)
                parser.clear_excess(pos)
                parser.insert_dummy(pos, i)
                tree = parser.file()
                tok = parser.remove_dummy()
                if tok is None:
                    break
                farthest = parser.reset_farthest(0)
                if tree is not None or farthest > pos:
                    howfar.setdefault(farthest, []).append(tok)
            if howfar:
                # Only report those tokens that got the farthest
                expected = sorted(howfar[max(howfar)])
                print(
                    f"Got {describe(got, parser)}, expected one of the following:",
                    ", ".join(describe(tok, parser) for tok in expected),
                )
                ## pprint.pprint(howfar)
            sys.exit(1)

        try:
            if file.isatty():
                endpos = 0
            else:
                endpos = file.tell()
        except IOError:
            endpos = 0
    finally:
        if file is not sys.stdin:
            file.close()

    t1 = time.time()

    if not args.quiet:
        pprint.pprint(tree, indent=2)

    if verbose:
        dt = t1 - t0
        diag = tokenizer.diagnose()
        nlines = diag.end[0]
        if diag.type == token.ENDMARKER:
            nlines -= 1
        print(f"Total time: {dt:.3f} sec; {nlines} lines", end="")
        if endpos:
            print(f" ({endpos} bytes)", end="")
        if dt:
            print(f"; {nlines / dt:.0f} lines/sec")
        else:
            print()
        print("Caches sizes:")
        print(f"  token array : {len(tokenizer._tokens):10}")
        print(f"        cache : {len(parser._cache):10}")


if __name__ == "__main__":
    main()
