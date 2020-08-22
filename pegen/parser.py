import argparse
import sys
import time
import token
import tokenize
import traceback

from abc import abstractmethod
from typing import Any, Callable, cast, ClassVar, Dict, Optional, Set, Tuple, Type, TypeVar

from pegen.tokenizer import exact_token_types
from pegen.tokenizer import Mark
from pegen.tokenizer import Tokenizer

T = TypeVar("T")
P = TypeVar("P", bound="Parser")
F = TypeVar("F", bound=Callable[..., Any])


def logger(method: F) -> F:
    """For non-memoized functions that we want to be logged.

    (In practice this is only non-leader left-recursive functions.)
    """
    method_name = method.__name__

    def logger_wrapper(self: P, *args: object) -> T:
        if not self._verbose:
            return method(self, *args)
        argsr = ",".join(repr(arg) for arg in args)
        fill = "  " * self._level
        print(f"{fill}{method_name}({argsr}) .... (looking at {self.showpeek()})")
        self._level += 1
        tree = method(self, *args)
        self._level -= 1
        print(f"{fill}... {method_name}({argsr}) --> {tree!s:.200}")
        return tree

    logger_wrapper.__wrapped__ = method  # type: ignore
    return cast(F, logger_wrapper)


def memoize(method: F) -> F:
    """Memoize a symbol method."""
    method_name = method.__name__

    def memoize_wrapper(self: P, *args: object) -> T:
        mark = self.mark()
        key = mark, method_name, args
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark, farthest = self._cache[key]
            self.reset(endmark)
            self.update_farthest(farthest)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        argsr = ",".join(repr(arg) for arg in args)
        fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                print(f"{fill}{method_name}({argsr}) ... (looking at {self.showpeek()})")
            self._level += 1
            prior_farthest = self.reset_farthest(mark)
            tree = method(self, *args)
            farthest = self.reset_farthest(prior_farthest)
            self.update_farthest(farthest)
            self._level -= 1
            if verbose:
                print(f"{fill}... {method_name}({argsr}) -> {tree!s:.200}")
            endmark = self.mark()
            self._cache[key] = tree, endmark, farthest
        else:
            tree, endmark, farthest = self._cache[key]
            if verbose:
                print(f"{fill}{method_name}({argsr}) -> {tree!s:.200}")
            self.reset(endmark)
            self.update_farthest(farthest)
        return tree

    memoize_wrapper.__wrapped__ = method  # type: ignore
    return cast(F, memoize_wrapper)


def memoize_left_rec(method: Callable[[P], Optional[T]]) -> Callable[[P], Optional[T]]:
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    def memoize_left_rec_wrapper(self: P) -> Optional[T]:
        mark = self.mark()
        key = mark, method_name, ()
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark, farthest = self._cache[key]
            self.reset(endmark)
            self.update_farthest(farthest)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                print(f"{fill}{method_name} ... (looking at {self.showpeek()})")
            self._level += 1

            # For left-recursive rules we manipulate the cache and
            # loop until the rule shows no progress, then pick the
            # previous result.  For an explanation why this works, see
            # https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion
            # (But we use the memoization cache instead of a static
            # variable; perhaps this is similar to a paper by Warth et al.
            # (http://web.cs.ucla.edu/~todd/research/pub.php?id=pepm08).

            # Prime the cache with a failure.
            self._cache[key] = None, mark, mark
            lastresult, lastmark = None, mark
            depth = 0
            if verbose:
                print(f"{fill}Recursive {method_name} at {mark} depth {depth}")

            while True:
                self.reset(mark)
                prior_farthest = self.reset_farthest(mark)
                result = method(self)
                endmark = self.mark()
                farthest = self.reset_farthest(prior_farthest)
                self.update_farthest(farthest)
                depth += 1
                if verbose:
                    print(
                        f"{fill}Recursive {method_name} at {mark} depth {depth}: {result!s:.200} to {endmark}"
                    )
                if not result:
                    if verbose:
                        print(f"{fill}Fail with {lastresult!s:.200} to {lastmark}")
                    break
                if endmark <= lastmark:
                    if verbose:
                        print(f"{fill}Bailing with {lastresult!s:.200} to {lastmark}")
                    break
                self._cache[key] = lastresult, lastmark, farthest = result, endmark, farthest

            self.reset(lastmark)
            self.update_farthest(farthest)
            tree = lastresult

            self._level -= 1
            if verbose:
                print(f"{fill}{method_name}() -> {tree!s:.200} [cached]")
            if tree:
                endmark = self.mark()
            else:
                endmark = mark
                self.reset(endmark)
            self._cache[key] = tree, endmark, farthest
        else:
            tree, endmark, farthest = self._cache[key]
            if verbose:
                print(f"{fill}{method_name}() -> {tree!s:.200} [fresh]")
            if tree:
                self.reset(endmark)
        return tree

    memoize_left_rec_wrapper.__wrapped__ = method  # type: ignore
    return memoize_left_rec_wrapper


class Parser:
    """Parsing base class."""

    def __init__(self, tokenizer: Tokenizer, *, verbose: bool = False):
        self._tokenizer = tokenizer
        self._verbose = verbose
        self._level = 0
        self._cache: Dict[Tuple[Mark, str, Tuple[Any, ...]], Tuple[Any, Mark]] = {}
        self._dummy_pos = None
        self._dummy_count = None
        self._dummy_inserted = None
        # Pass through common tokenizer methods.
        # TODO: Rename to _mark and _reset.
        self.mark = self._tokenizer.mark
        self.reset = self._tokenizer.reset
        self.update_farthest = self._tokenizer.update_farthest
        self.reset_farthest = self._tokenizer.reset_farthest

    _keywords: ClassVar[Optional[Set[str]]] = set()

    @abstractmethod
    def start(self) -> Any:
        raise NotImplementedError

    def showpeek(self) -> str:
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"

    @memoize
    def name(self) -> Optional[tokenize.TokenInfo]:
        self.check_for_dummy("NAME")
        tok = self._tokenizer.peek()
        if tok.type == token.NAME:
            if tok.string in self._keywords:
                return None
            return self._tokenizer.getnext()
        return None

    @memoize
    def number(self) -> Optional[tokenize.TokenInfo]:
        self.check_for_dummy("NUMBER")
        tok = self._tokenizer.peek()
        if tok.type == token.NUMBER:
            return self._tokenizer.getnext()
        return None

    @memoize
    def string(self) -> Optional[tokenize.TokenInfo]:
        self.check_for_dummy("STRING")
        tok = self._tokenizer.peek()
        if tok.type == token.STRING:
            return self._tokenizer.getnext()
        return None

    @memoize
    def op(self) -> Optional[tokenize.TokenInfo]:
        self.check_for_dummy("OP")
        tok = self._tokenizer.peek()
        if tok.type == token.OP:
            return self._tokenizer.getnext()
        return None

    @memoize
    def expect(self, type: str) -> Optional[tokenize.TokenInfo]:
        self.check_for_dummy(type)
        tok = self._tokenizer.peek()
        if tok.string == type:
            if tok.string in self._keywords:
                return None
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

    @memoize
    def expect_keyword(self, type: str) -> Optional[tokenize.TokenInfo]:
        self.check_for_dummy(type)
        tok = self._tokenizer.peek()
        if tok.string == type:
            return self._tokenizer.getnext()
        return None

    def positive_lookahead(self, func: Callable[..., T], *args: object) -> T:
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return ok

    def negative_lookahead(self, func: Callable[..., object], *args: object) -> bool:
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return not ok

    def make_syntax_error(self, filename: str = "<unknown>") -> SyntaxError:
        tok = self._tokenizer.diagnose()
        return SyntaxError(
            "pegen parse failure", (filename, tok.start[0], 1 + tok.start[1], tok.line)
        )

    def clear_excess(self, pos: Mark) -> None:
        """Delete cache entries with farthest > pos."""
        to_delete = [key for key, (tree, mark, farthest) in self._cache.items()
                     if farthest > pos]
        for key in to_delete:
            del self._cache[key]

    def insert_dummy(self, pos: Mark, count: int) -> None:
        """Pretend there's a dummy token at pos.

        The first count times expect() or similar is called it will fail;
        on the next call it will succeed.
        """
        assert self._dummy_inserted is None
        assert pos >= 0
        assert count >= 0
        self._dummy_pos = pos
        self._dummy_count = count
        self._dummy_inserted = None

    def check_for_dummy(self, type: str) -> None:
        """Check whether this is the position where we should insert a dummy token."""
        if self._dummy_pos is None or self._dummy_pos != self.mark():
            return
        if self._dummy_count > 0:
            self._dummy_count -= 1
            return
        pos = self._dummy_pos
        self._dummy_pos = None
        self._dummy_count = None
        tok = tokenize.TokenInfo(make_dummy_token_type(type), type, (0, 0), (0, 0), "")
        self._tokenizer._tokens.insert(pos, tok)  # TODO: Make an API for this
        self._dummy_inserted = pos

    def still_dummy(self) -> bool:
        return self._dummy_pos is not None

    def remove_dummy(self):
        if self._dummy_inserted is None:
            return None
        tok = self._tokenizer._tokens[self._dummy_inserted]
        del self._tokenizer._tokens[self._dummy_inserted]  # TODO: Make an API for this
        self._dummy_inserted = None
        return tok


def make_dummy_token_type(type: str) -> int:
    if type in token.EXACT_TOKEN_TYPES:
        return token.OP
    return getattr(token, type, token.ERRORTOKEN)


def simple_parser_main(parser_class: Type[Parser]) -> None:
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
        parser = parser_class(tokenizer, verbose=verbose_parser)
        tree = parser.start()
        try:
            if file.isatty():
                endpos = 0
            else:
                endpos = file.tell()
        except IOError:
            endpos = 0
        if not tree:
            err = parser.make_syntax_error(filename)
            traceback.print_exception(err.__class__, err, None)
            sys.exit(1)
    finally:
        if file is not sys.stdin:
            file.close()

    t1 = time.time()

    if not args.quiet:
        import pprint
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
        ## print_memstats()
