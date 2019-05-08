#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Google PEG Parsers for reference.

(The first version is actually a hand-crafter packrat parser.)
"""

from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import sys
import time
import token
import tokenize
from typing import *

exact_token_types = token.EXACT_TOKEN_TYPES  # type: ignore

Mark = int


class Tree:

    def __init__(self, type: str, *args: Optional['Tree'], value: Optional[str] = None):
        if value is not None:
            assert not args, args
        self.type = type
        self.args = args
        self.value = value

    def __repr__(self) -> str:
        if self.value is not None:
            return self.value
        return "%s(%s)" % (self.type, ", ".join(repr(arg) for arg in self.args))


class Tokenizer:

    _tokens: List[tokenize.TokenInfo]

    def __init__(self, input: TextIO):
        self._tokengen = tokenize.generate_tokens(input.readline)
        self._tokens = []
        self._index = 0

    def getnext(self) -> tokenize.TokenInfo:
        """Return the next token.

        Updates the current index.
        """
        if self._index == len(self._tokens):
            self._tokens.append(next(self._tokengen))
        tok = self._tokens[self._index]
        self._index += 1
        return tok

    def diagnose(self) -> tokenize.TokenInfo:
        if not self._tokens:
            self.getnext()
        return self._tokens[-1]

    def mark(self) -> Mark:
        return self._index

    def reset(self, index: Mark) -> None:
        assert 0 <= index <= len(self._tokens), (index, len(self._tokens))
        self._index = index


def memoize(method: Callable[['Parser'], Optional[Tree]]):
    """Memoize a symbol method."""

    def symbol_wrapper(self: 'Parser') -> Optional[Tree]:
        mark = self.mark()
        key = mark, method
        if key not in self._symbol_cache:
            tree = method(self)
            if tree:
                endmark = self.mark()
            else:
                endmark = mark
            self._symbol_cache[key] = tree, endmark
        tree, endmark = self._symbol_cache[key]
        self.reset(endmark)
        return tree

    return symbol_wrapper


def memoize_expect(method: Callable[['Parser'], bool]) -> bool:
    """Memoize the expect() method."""

    def expect_wrapper(self: 'Parser', type: str) -> bool:
        mark = self.mark()
        key = mark, type
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

    return expect_wrapper
    

class Parser:

    def __init__(self, tokenizer: Tokenizer):
        self._tokenizer = tokenizer
        self._symbol_cache: Dict[Tuple[Mark,
                                       Callable[['Parser'], Optional[Tree]]],
                                 Tuple[Optional[Tree], Mark]] = {}
        self._token_cache: Dict[Tuple[Mark, str], bool] = {}
        self.mark = self._tokenizer.mark
        self.reset = self._tokenizer.reset

    @memoize
    def start(self) -> Optional[Tree]:
        """
        start: '\n'* (sum '\n'*)+ EOF
        """
        trees = []
        while True:
            mark = self.mark()
            if self.expect('NL'):
                continue
            if (tree := self.sum()) and self.expect('NEWLINE'):
                trees.append(tree)
            else:
                self.reset(mark)
                if not self.expect('ENDMARKER'):
                    return None
                break

        if trees:
            return Tree('Sums', *trees)
        return None

    @memoize
    def sum(self) -> Optional[Tree]:
        """
        sum: term '+' sum | term
        """
        mark = self.mark()
        if (left := self.term()) and self.expect('+') and (right := self.sum()):
            # Note that 'a + b + c' is parsed as 'a + (b + c)'.
            # Also note that explicit parentheses are preserved.
            terms = [left]  # type: List[Optional[Tree]]
            if right.type == '+':
                terms.extend(right.args)
            else:
                terms.append(right)
            return Tree('+', *terms)
        self.reset(mark)
        if left := self.term():
            return left
        return None

    @memoize
    def term(self) -> Optional[Tree]:
        """
        term: factor '*' term | factor
        """
        mark = self.mark()
        if (left := self.factor()) and self.expect('*') and (right := self.term()):
            factors = [left]  # type: List[Optional[Tree]]
            if right.type == '*':
                factors.extend(right.args)
            else:
                factors.append(right)
            return Tree('*', *factors)
        self.reset(mark)
        if left := self.factor():
            return left
        return None

    @memoize
    def factor(self) -> Optional[Tree]:
        """
        factor: '(' sum ')' | NUMBER
        """
        mark = self.mark()
        if self.expect('(') and (sum := self.sum()) and self.expect(')'):
            return Tree('Group', sum)
        self.reset(mark)
        if number := self.number():
            return number
        return None

    @memoize
    def number(self) -> Optional[Tree]:
        toktup = self._tokenizer.getnext()
        if toktup.type == token.NUMBER:
            return Tree('NUMBER', value=toktup.string)
        return None

    @memoize_expect
    def expect(self, type: str) -> bool:
        toktup = self._tokenizer.getnext()
        if type in exact_token_types:
            if toktup.type == exact_token_types[type]:
                return True
        if type in token.__dict__:
            if toktup.type == token.__dict__[type]:
                return True
        if toktup.type == token.OP and toktup.string == type:
            return True
        return False


argparser = argparse.ArgumentParser(prog='pegen')
argparser.add_argument('-q', '--quiet', action='store_true')
argparser.add_argument('-v', '--verbose', action='store_true')
argparser.add_argument('filename')


def main() -> None:
    args = argparser.parse_args()
    t0 = time.time()
    with open(args.filename) as file:
        tokenizer = Tokenizer(file)
        parser = Parser(tokenizer)
        tree = parser.start()
        if not tree:
            print("Syntax error at:", tokenizer.diagnose(), file=sys.stderr)
            sys.exit(1)
        if not args.quiet:
            if tree.type == 'Sums':
                for arg in tree.args:
                    print(arg)
            else:
                print(tree)
        endpos = file.tell()
    t1 = time.time()
    dt = t1 - t0
    if args.verbose:
        diag = tokenizer.diagnose()
        nlines = diag.end[0]
        if diag.type == token.ENDMARKER:
            nlines -= 1
        print("Total time: %.3f sec; %d lines (%d bytes)" % (dt, nlines, endpos),
              end="", file=sys.stderr)
        if dt:
            print("; %.3f lines/sec" % (nlines / dt), file=sys.stderr)
        else:
            print(file=sys.stderr)


if __name__ == '__main__':
    main()
