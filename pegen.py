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

Mark = int  # NewType('Mark', int)


class Tree:
    """Parse tree node.

    There are two kinds of nodes:
    - Leaf nodes have a value field that's not None.
    - Interior nodes have an args field that's not empty.
    """

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
    """Caching wrapper for the tokenize module.

    This is hopelessly tied to Python's syntax.
    """

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
            # TODO: Skip NL and COMMENT here.
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


def memoize(method: Callable[[Parser], Optional[Tree]]):
    """Memoize a symbol method."""

    def symbol_wrapper(self: Parser) -> Optional[Tree]:
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


def memoize_expect(method: Callable[[Parser], bool]) -> bool:
    """Memoize the expect() method."""

    def expect_wrapper(self: Parser, type: str) -> bool:
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
    """Parsing base class."""

    def __init__(self, tokenizer: Tokenizer):
        self._tokenizer = tokenizer
        self._symbol_cache: Dict[Tuple[Mark,
                                       Callable[[Parser], Optional[Tree]]],
                                 Tuple[Optional[Tree], Mark]] = {}
        self._token_cache: Dict[Tuple[Mark, str], bool] = {}
        # Pass through common tokeniser methods.
        # TODO: Rename to _mark and _reset.
        self.mark = self._tokenizer.mark
        self.reset = self._tokenizer.reset

    @memoize
    def name(self) -> Optional[Tree]:
        toktup = self._tokenizer.getnext()
        if toktup.type == token.NAME:
            return Tree('NAME', value=toktup.string)
        return None

    @memoize
    def number(self) -> Optional[Tree]:
        toktup = self._tokenizer.getnext()
        if toktup.type == token.NUMBER:
            return Tree('NUMBER', value=toktup.string)
        return None

    @memoize
    def string(self) -> Optional[Tree]:
        toktup = self._tokenizer.getnext()
        if toktup.type == token.STRING:
            return Tree('STRING', value=toktup.string)
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


class GrammarParser(Parser):
    """Parser for Grammar files."""

    @memoize
    def start(self) -> Optional[Tree]:
        """
        start: '\n'* (rule '\n'+)+ EOF
        """
        trees = []
        while True:
            mark = self.mark()
            if self.expect('NL'):
                continue
            if self.expect('COMMENT'):
                continue
            if (tree := self.rule()) and self.expect('NEWLINE'):
                trees.append(tree)
            else:
                self.reset(mark)
                if not self.expect('ENDMARKER'):
                    return None
                break

        if trees:
            return Tree('Grammar', *trees)
        return None

    @memoize
    def rule(self) -> Optional[Tree]:
        """
        rule: NAME ':' alternatives
        """
        if (name := self.name()) and self.expect(':') and (alts := self.alternatives()):
            return Tree('Rule', name, alts)
        return None

    @memoize
    def alternatives(self) -> Optional[Tree]:
        """
        alternatives: alternative '|' alternatives | alternative
        """
        mark = self.mark()
        if (left := self.alternative()) and self.expect('|') and (right := self.alternatives()):
            alts = [left]
            if right.type == 'Alts':
                alts.extend(right.args)
            else:
                alts.append(right)
            return Tree('Alts', *alts)
        self.reset(mark)
        return self.alternative()

    @memoize
    def alternative(self) -> Optional[Tree]:
        """
        alternative: item alternative | item
        """
        mark = self.mark()
        if (item := self.item()) and (alt := self.alternative()):
            items = [item]
            if alt.type == 'Alt':
                items.extend(alt.args)
            else:
                items.append(alt)
            return Tree('Alt', *items)
        self.reset(mark)
        return self.item()

    @memoize
    def item(self) -> Optional[Tree]:
        """
        item: optional | atom '*' | atom '+' | atom

        Note that optional cannot be followed by * or +.
        """
        mark = self.mark()
        if (opt := self.optional()):
            return opt
        if (atom := self.atom()) and self.expect('*'):
            return Tree('ZeroOrMore', atom)
        self.reset(mark)
        if (atom := self.atom()) and self.expect('+'):
            return Tree('OneOrMore', atom)
        self.reset(mark)
        return self.atom()

    @memoize
    def optional(self) -> Optional[Tree]:
        """
        optional: '[' alternatives ']'
        """
        if self.expect('[') and (alts := self.alternatives()) and self.expect(']'):
            return Tree('Opt', alts)
        return None

    @memoize
    def atom(self) -> Optional[Tree]:
        """
        atom: group | NAME | STRING
        """
        mark = self.mark()
        if (par := self.group()):
            return par
        if (name := self.name()):
            return name
        if (string := self.string()):
            return string
        return None

    @memoize
    def group(self) -> Optional[Tree]:
        """
        group: '(' alternatives ')'
        """
        if self.expect('(') and (alts := self.alternatives()) and self.expect(')'):
            return Tree('Group', alts)
        return None


class ExpressionParser(Parser):
    """Parser for simple expressions.

    Currently just + and * on numbers, with parentheses.
    """

    @memoize
    def start(self) -> Optional[Tree]:
        """
        start: '\n'* (sum '\n'+)+ EOF
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
        return self.term()

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
        return self.factor()

    @memoize
    def factor(self) -> Optional[Tree]:
        """
        factor: '(' sum ')' | NUMBER
        """
        mark = self.mark()
        if self.expect('(') and (sum := self.sum()) and self.expect(')'):
            return Tree('Group', sum)
        self.reset(mark)
        return self.number()


argparser = argparse.ArgumentParser(prog='pegen')
argparser.add_argument('-q', '--quiet', action='store_true')
argparser.add_argument('-v', '--verbose', action='store_true')
argparser.add_argument('-g', '--grammar', action='store_true')
argparser.add_argument('filename')


def main() -> None:
    args = argparser.parse_args()
    t0 = time.time()
    with open(args.filename) as file:
        tokenizer = Tokenizer(file)
        if args.grammar:
            parser = GrammarParser(tokenizer)
        else:
            parser = ExpressionParser(tokenizer)
        tree = parser.start()
        if not tree:
            print("Syntax error at:", tokenizer.diagnose(), file=sys.stderr)
            sys.exit(1)
        if not args.quiet:
            if tree.type in ('Sums', 'Grammar'):
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
