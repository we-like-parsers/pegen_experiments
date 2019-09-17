#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

import argparse
import sys
import time
import token
import traceback

from typing import Final

from pegen.build import build_parser_and_generator
from pegen.testutil import print_memstats


argparser = argparse.ArgumentParser(
    prog="pegen", description="Experimental PEG-like parser generator"
)
argparser.add_argument("-q", "--quiet", action="store_true", help="Don't print the parsed grammar")
argparser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="Print timing stats; repeat for more debug output",
)
argparser.add_argument(
    "-c", "--cpython", action="store_true", help="Generate C code for inclusion into CPython"
)
argparser.add_argument(
    "--compile-extension",
    action="store_true",
    help="Compile generated C code into an extension module",
)
argparser.add_argument(
    "-o",
    "--output",
    metavar="OUT",
    help="Where to write the generated parser (default parse.py or parse.c)",
)
argparser.add_argument("filename", help="Grammar description")


def main() -> None:
    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4
    t0 = time.time()

    output_file = args.output
    if not output_file:
        if args.cpython:
            output_file = "parse.c"
        else:
            output_file = "parse.py"

    try:
        rules, parser, tokenizer, gen = build_parser_and_generator(
            args.filename,
            output_file,
            args.compile_extension,
            verbose_tokenizer,
            verbose_parser,
            args.verbose,
        )
    except Exception as err:
        if args.verbose:
            raise  # Show traceback
        traceback.print_exception(err.__class__, err, None)
        sys.exit(1)

    if not args.quiet:
        if args.verbose:
            print("Raw Grammar:")
            for rule in rules.rules.values():
                print(" ", repr(rule))
        print("Clean Grammar:")
        for rule in rules.rules.values():
            print(" ", rule)

    if args.verbose:
        print("First Graph:")
        for src, dsts in gen.first_graph.items():
            print(f"  {src} -> {', '.join(dsts)}")
        print("First SCCS:")
        for scc in gen.first_sccs:
            print(" ", scc, end="")
            if len(scc) > 1:
                print(
                    "  # Indirectly left-recursive; leaders:",
                    {name for name in scc if rules.rules[name].leader},
                )
            else:
                name = next(iter(scc))
                if name in gen.first_graph[name]:
                    print("  # Left-recursive")
                else:
                    print()

    t1 = time.time()

    if args.verbose:
        dt = t1 - t0
        diag = tokenizer.diagnose()
        nlines = diag.end[0]
        if diag.type == token.ENDMARKER:
            nlines -= 1
        print(f"Total time: {dt:.3f} sec; {nlines} lines", end="")
        if dt:
            print(f"; {nlines / dt:.0f} lines/sec")
        else:
            print()
        print("Caches sizes:")
        print(f"  token array : {len(tokenizer._tokens):10}")
        print(f"        cache : {len(parser._cache):10}")
        if not print_memstats():
            print("(Can't find psutil; install it for memory stats.)")


if __name__ == "__main__":
    main()
