#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import sys
import time
import token
import tokenize
import traceback

from typing import Final

from pegen.parser_generator import ParserGenerator
from pegen.tokenizer import Tokenizer
from pegen.tokenizer import grammar_tokenizer
from pegen.grammar import GrammarParser


def print_memstats() -> bool:
    MiB: Final = 2 ** 20
    try:
        import psutil  # type: ignore
    except ImportError:
        return False
    print("Memory stats:")
    process = psutil.Process()
    meminfo = process.memory_info()
    res = {}
    res['rss'] = meminfo.rss / MiB
    res['vms'] = meminfo.vms / MiB
    if sys.platform == 'win32':
        res['maxrss'] = meminfo.peak_wset / MiB
    else:
        # See https://stackoverflow.com/questions/938733/total-memory-used-by-python-process
        import resource  # Since it doesn't exist on Windows.
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == 'darwin':
            factor = 1
        else:
            factor = 1024  # Linux
        res['maxrss'] = rusage.ru_maxrss * factor / MiB
    for key, value in res.items():
        print(f"  {key:12.12s}: {value:10.0f} MiB")
    return True



argparser = argparse.ArgumentParser(prog='pegen', description="Experimental PEG-like parser generator")
argparser.add_argument('-q', '--quiet', action='store_true', help="Don't print the parsed grammar")
argparser.add_argument('-v', '--verbose', action='count', default=0,
                       help="Print timing stats; repeat for more debug output")
argparser.add_argument('-c', '--cpython', action='store_true', help="Generate C code for inclusion into CPython")
argparser.add_argument('-o', '--output', metavar='OUT',
                       help="Where to write the generated parser (default parse.py)")
argparser.add_argument('filename', help="Grammar description")


def main() -> None:
    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4
    t0 = time.time()

    with open(args.filename) as file:
        tokenizer = Tokenizer(grammar_tokenizer(tokenize.generate_tokens(file.readline)),
                              verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        rules = parser.start()
        if not rules:
            err = parser.make_syntax_error(args.filename)
            traceback.print_exception(err.__class__, err, None)
            sys.exit(1)
        endpos = file.tell()

    if not args.quiet:
        if args.verbose:
            print("Raw Grammar:")
            for rule in rules.values():
                print(" ", repr(rule))
        print("Clean Grammar:")
        for rule in rules.values():
            print(" ", rule)

    output = args.output
    if not output:
        if args.cpython:
            output = "parse.c"
        else:
            output = "parse.py"
    with open(output, 'w') as file:
        genr = ParserGenerator(rules, file)
        if args.cpython:
            genr.generate_cpython_extension(args.filename)
        else:
            genr.generate_python_module(args.filename)

    if args.verbose:
        print("First Graph:")
        for src, dsts in genr.first_graph.items():
            print(f"  {src} -> {', '.join(dsts)}")
        print("First SCCS:")
        for scc in genr.first_sccs:
            print(" ", scc, end="")
            if len(scc) > 1:
                print("  # Indirectly left-recursive")
            else:
                name = next(iter(scc))
                if name in genr.first_graph[name]:
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
        if endpos:
            print(f" ({endpos} bytes)", end="")
        if dt:
            print(f"; {nlines / dt:.0f} lines/sec")
        else:
            print()
        print("Caches sizes:")
        print(f"  token array : {len(tokenizer._tokens):10}")
        print(f"  symbol cache: {len(parser._symbol_cache):10}")
        print(f"  token cache : {len(parser._token_cache):10}")
        if not print_memstats():
            print("(Can't find psutil; install it for memory stats.)")


if __name__ == '__main__':
    main()
