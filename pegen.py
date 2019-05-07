#!/usr/bin/env python3.7

"""pegen -- PEG Generator.

Google PEG Parsers for reference.

(The first version is actually a hand-crafter packrat parser.)
"""

from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import sys
import token
import tokenize
from typing import *

exact_token_types = token.EXACT_TOKEN_TYPES  # type: ignore

Mark = NewType('Mark', int)


class Tree:

    def __init__(self, type: str, *args: Optional['Tree'], value: str = None):
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

    def mark(self) -> Mark:
        return Mark(self._index)

    def reset(self, index: Mark):
        assert 0 <= index < len(self._tokens)
        self._index = index


class Parser:

    def __init__(self, tokenizer: Tokenizer):
        self._tokenizer = tokenizer

    def mark(self) -> Mark:
        return self._tokenizer.mark()

    def reset(self, mark: Mark) -> None:
        self._tokenizer.reset(mark)

    def start(self) -> Optional[Tree]:
        """
        start: sum EOF
        """
        return self.sum()  # TODO: expect EOF

    def sum(self) -> Optional[Tree]:
        """
        sum: term '+' sum | term
        """
        mark = self.mark()
        left = self.term()
        if not left:
            self.reset(mark)
            return None
        mark = self.mark()
        if not self.expect('+'):
            self.reset(mark)
            return left
        right = self.sum()
        if not right:
            self.reset(mark)
            return left
        # Note that 'a + b + c' is parsed as 'a + (b + c)'.
        # Also note that explicit parentheses are preserved.
        terms = [left]  # type: List[Optional[Tree]]
        if right.type == '+':
            terms.extend(right.args)
        else:
            terms.append(right)
        return Tree('+', *terms)

    def term(self) -> Optional[Tree]:
        """
        term: factor '*' term | factor
        """
        mark = self.mark()
        left = self.factor()
        if not left:
            self.reset(mark)
            return left
        mark = self.mark()
        if not self.expect('*'):
            self.reset(mark)
            return left
        right = self.term()
        if not right:
            self.reset(mark)
            return left
        factors = [left]  # type: List[Optional[Tree]]
        if right.type == '*':
            factors.extend(right.args)
        else:
            factors.append(right)
        return Tree('*', *factors)

    def factor(self) -> Optional[Tree]:
        """
        factor: '(' sum ')' | NUMBER
        """
        mark = self.mark()
        number = self.number()
        if number:
            return number
        self.reset(mark)
        if not self.expect('('):
            self.reset(mark)
            return None
        sum = self.sum()
        if not sum:
            self.reset(mark)
            return None
        if not self.expect(')'):
            self.reset(mark)
            return None
        return Tree('Group', sum)

    def number(self) -> Optional[Tree]:
        mark = self.mark()
        toktup = self._tokenizer.getnext()
        if toktup.type == token.NUMBER:
            return Tree('NUMBER', value=toktup.string)
        self.reset(mark)
        return None

    def expect(self, type: str) -> bool:
        mark = self.mark()
        toktup = self._tokenizer.getnext()
        if type in exact_token_types:
            if toktup.type == exact_token_types[type]:
                return True
        if type in token.__dict__:
            if toktup.type == token.__dict__[type]:
                return True
        if toktup.type == token.OP and toktup.string == type:
            return True
        self.reset(mark)
        return False


argparser = argparse.ArgumentParser(prog='pegen')
argparser.add_argument('filename')


def main() -> None:
    args = argparser.parse_args()
    with open(args.filename) as file:
        tokenizer = Tokenizer(file)
        parser = Parser(tokenizer)
        tree = parser.start()
        if not tree:
            print("Syntax error")
            sys.exit(1)
        print(tree)


if __name__ == '__main__':
    main()
