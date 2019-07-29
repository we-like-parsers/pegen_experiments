from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import sys
import time
import token
import tokenize
from typing import TypeVar, Generic, Dict, Tuple, Callable, Optional, NoReturn

from pegen.tokenizer import CURLY_STUFF
from pegen.tokenizer import exact_token_types
from pegen.tokenizer import grammar_tokenizer
from pegen.tokenizer import Mark
from pegen.tokenizer import Tokenizer

T = TypeVar('T')


def memoize(method: Callable[[Parser], T]):
    """Memoize a symbol method."""
    method_name = method.__name__

    def symbol_wrapper(self: Parser) -> T:
        mark = self.mark()
        key = mark, method_name
        # Fast path: cache hit, and not verbose.
        if key in self._symbol_cache and not self._verbose:
            tree, endmark = self._symbol_cache[key]
            if tree:
                self.reset(endmark)
            else:
                assert mark == endmark
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        fill = '  ' * self._level
        if key not in self._symbol_cache:
            if verbose:
                print(f"{fill}{method_name} ... (looking at {self.showpeek()})")
            self._level += 1
            tree = method(self)
            self._level -= 1
            if verbose:
                print(f"{fill}... {method_name} -> {tree!s:.100}")
            if tree:
                endmark = self.mark()
            else:
                endmark = mark
                self.reset(endmark)
            self._symbol_cache[key] = tree, endmark
        else:
            tree, endmark = self._symbol_cache[key]
            if verbose:
                print(f"{fill}{method_name} -> {tree!s:.100}")
            if tree:
                self.reset(endmark)
        return tree

    symbol_wrapper.__wrapped__ = method
    return symbol_wrapper


def memoize_left_rec(method: Callable[[Parser], T]):
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    def symbol_wrapper(self: Parser) -> T:
        mark = self.mark()
        key = mark, method_name
        # Fast path: cache hit, and not verbose.
        if key in self._symbol_cache and not self._verbose:
            tree, endmark = self._symbol_cache[key]
            if tree:
                self.reset(endmark)
            else:
                assert mark == endmark
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        fill = '  ' * self._level
        if key not in self._symbol_cache:
            if verbose:
                print(f"{fill}{method_name} ... (looking at {self.showpeek()})")
            self._level += 1

            # For left-recursive rules we manipulate the cache and
            # loop until the rule shows no progress, then pick the
            # previous result.  For an explanation why this works, see
            # https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion
            # (But we use the memoization cache instead of a static
            # variable.)

            # Prime the cache with a failure.
            self._symbol_cache[key] = None, mark
            lastresult, lastmark = None, mark
            depth = 0
            if verbose:
                print(f"{fill}Recursive {method_name} at {mark} depth {depth}")

            while True:
                self.reset(mark)
                result = method(self)
                endmark = self.mark()
                depth += 1
                if verbose:
                    print(f"{fill}Recursive {method_name} at {mark} depth {depth}: {result!s:.100} to {endmark}")
                if not result:
                    if verbose:
                        print(f"{fill}Fail with {lastresult!s:.100} to {lastmark}")
                    break
                if endmark <= lastmark:
                    if verbose:
                        print(f"{fill}Bailing with {lastresult!s:.100} to {lastmark}")
                    break
                self._symbol_cache[key] = lastresult, lastmark = result, endmark

            self.reset(lastmark)
            tree = lastresult

            self._level -= 1
            if verbose:
                print(f"{fill}{method_name} -> {tree!s:.100}")
            if tree:
                endmark = self.mark()
            else:
                endmark = mark
                self.reset(endmark)
            self._symbol_cache[key] = tree, endmark
        else:
            tree, endmark = self._symbol_cache[key]
            if verbose:
                print(f"{fill}{method_name} -> {tree!s:.100}")
            if tree:
                self.reset(endmark)
        return tree

    symbol_wrapper.__wrapped__ = method
    return symbol_wrapper


def memoize_expect(method: Callable[[Parser], Optional[tokenize.TokenInfo]]) -> bool:
    """Memoize the expect() method."""

    def expect_wrapper(self: Parser, type: str) -> Optional[tokenize.TokenInfo]:
        mark = self.mark()
        key = mark, type
        # Fast path: cache hit.
        if key in self._token_cache:
            res, endmark = self._token_cache[key]
            if res:
                self.reset(endmark)
                # Uncomment these when parsing Python, to save
                # up to 80% of memory (though little time!).
                # self._token_cache.clear()
                # self._symbol_cache.clear()
            return res
        # Slow path.
        if key not in self._token_cache:
            res = method(self, type)
            if res:
                endmark = self.mark()
            else:
                endmark = mark
            self._token_cache[key] = res, endmark
        else:
            res, endmark = self._token_cache[key]
        self.reset(endmark)
        return res

    expect_wrapper.__wrapped__ = method
    return expect_wrapper


class Parser(Generic[T]):
    """Parsing base class."""

    def __init__(self, tokenizer: Tokenizer, *, verbose=False):
        self._tokenizer = tokenizer
        self._verbose = verbose
        self._level = 0
        self._symbol_cache: Dict[Tuple[Mark,
                                       Callable[[Parser], Optional[T]]],
                                 Tuple[Optional[T], Mark]] = {}
        self._token_cache: Dict[Tuple[Mark, str], bool] = {}
        # Pass through common tokeniser methods.
        # TODO: Rename to _mark and _reset.
        self.mark = self._tokenizer.mark
        self.reset = self._tokenizer.reset

    def showpeek(self):
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"

    def cut(self):
        if self._verbose:
            fill = '  ' * self._level
            print(f"{fill}CUT ... (looking at {self.showpeek()})")
        return True

    @memoize
    def name(self) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NAME:
            return self._tokenizer.getnext()
        return None

    @memoize
    def number(self) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NUMBER:
            return self._tokenizer.getnext()
        return None

    @memoize
    def string(self) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.STRING:
            return self._tokenizer.getnext()
        return None

    @memoize
    def curly_stuff(self) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == CURLY_STUFF:
            return self._tokenizer.getnext()
        return None

    @memoize_expect
    def expect(self, type: str) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.string == type:
            return self._tokenizer.getnext()
        if type in exact_token_types:
            if tok.type == exact_token_types[type]:
                return self._tokenizer.getnext()
        if type in token.__dict__:
            if tok.type == token.__dict__[type]:
                return self._tokenizer.getnext()
        if tok.type == token.OP and tok.string == type:
            return self._tokenizer.getnext()
        return None

    def positive_lookahead(self, func: Callable[..., T], *args) -> Optional[T]:
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return ok

    def negative_lookahead(self, func: Callable[..., T], *args) -> bool:
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return not ok

    def make_syntax_error(self, filename="<unknown>") -> NoReturn:
        tok = self._tokenizer.diagnose()
        return SyntaxError("pegen parse failure", (filename, tok.start[0], 1 + tok.start[1], tok.line))


def simple_parser_main(parser_class):
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-v', '--verbose', action='count', default=0,
                           help="Print timing stats; repeat for more debug output")
    argparser.add_argument('-q', '--quiet', action='store_true',
                           help="Don't print the parsed program")
    argparser.add_argument('-G', '--grammar-parser', action='store_true',
                           help="Recognize { ... } stuff; use for meta-grammar")
    argparser.add_argument('filename', help="Input file ('-' to use stdin)")

    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4

    t0 = time.time()

    filename = args.filename
    if filename == '' or filename == '-':
        filename = "<stdin>"
        file = sys.stdin
    else:
        file = open(args.filename)
    try:
        tokengen = tokenize.generate_tokens(file.readline)
        if args.grammar_parser:
            tokengen = grammar_tokenizer(tokengen)
        tokenizer = Tokenizer(tokengen, verbose=verbose_tokenizer)
        parser = parser_class(tokenizer, verbose=verbose_parser)
        tree = parser.start()
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

    if not tree:
        err = parser.make_syntax_error(filename)
        traceback.print_exception(err.__class__, err, None)
        sys.exit(1)

    if not args.quiet:
        print(tree)

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
        print(f"  symbol cache: {len(parser._symbol_cache):10}")
        print(f"  token cache : {len(parser._token_cache):10}")
        print_memstats()


