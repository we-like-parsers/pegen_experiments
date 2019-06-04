#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import contextlib
import os
import sys
import time
import token
import tokenize
import traceback
from typing import *

exact_token_types = token.EXACT_TOKEN_TYPES  # type: ignore

Mark = int  # NewType('Mark', int)


class Tree:
    """Parse tree node.

    There are two kinds of nodes:
    - Leaf nodes have a value field that's not None.
    - Interior nodes have an args field that's not empty.

    This should be considered an immutable data type,
    as it's used for the return type of memoized functions.
    """

    __slots__ = ('type', 'args', 'value')

    def __init__(self, type: str, *args: Optional['Tree'], value: Optional[str] = None):
        if value is not None:
            assert not args, args
        self.type = type
        self.args = args
        self.value = value

    def __repr__(self) -> str:
        if self.value is not None:
            return "%s(value=%r)" % (self.type, self.value)
        return "%s(%s)" % (self.type, ", ".join(repr(arg) for arg in self.args))

    def __str__(self) -> str:
        if self.value is not None:
            return str(self.value)
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tree):
            return NotImplemented
        return (self.type == other.type and
                self.args == other.args and
                self.value == other.value)

    def __hash__(self) -> int:
        return hash((self.type, self.args, self.value))


def shorttok(tok: tokenizer.TokenInfo) -> str:
    return "%-25.25s" % f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"


class Tokenizer:
    """Caching wrapper for the tokenize module.

    This is pretty tied to Python's syntax.
    """

    _tokens: List[tokenize.TokenInfo]

    def __init__(self, tokengen: Iterable[TokenInfo], *, verbose=False):
        self._tokengen = tokengen
        self._tokens = []
        self._index = 0
        self._verbose = verbose
        if verbose:
            self.report(False, False)

    def getnext(self) -> tokenize.TokenInfo:
        """Return the next token and updates the index."""
        cached = True
        while self._index == len(self._tokens):
            tok = next(self._tokengen)
            if tok.type in (token.NL, token.COMMENT):
                continue
            self._tokens.append(tok)
            cached = False
        tok = self._tokens[self._index]
        self._index += 1
        if self._verbose:
            self.report(cached, False)
        return tok

    def peek(self) -> tokenize.TokenInfo:
        """Return the next token *without* updating the index."""
        while self._index == len(self._tokens):
            tok = next(self._tokengen)
            if tok.type in (token.NL, token.COMMENT):
                continue
            self._tokens.append(tok)
        return self._tokens[self._index]

    def diagnose(self) -> tokenize.TokenInfo:
        if not self._tokens:
            self.getnext()
        return self._tokens[-1]

    def mark(self) -> Mark:
        return self._index

    def reset(self, index: Mark) -> None:
        if index == self._index:
            return
        assert 0 <= index <= len(self._tokens), (index, len(self._tokens))
        old_index = self._index
        self._index = index
        if self._verbose:
            self.report(True, index < old_index)

    def report(self, cached, back):
        if back:
            fill = '-'*self._index + '-'
        elif cached:
            fill = '-'*self._index + '>'
        else:
            fill = '-'*self._index + '*'
        if self._index == 0:
            print(f"{fill} (Bof)")
        else:
            tok = self._tokens[self._index - 1]
            print(f"{fill} {shorttok(tok)}")


def memoize(method: Callable[[Parser], Optional[Tree]]):
    """Memoize a symbol method."""
    method_name = method.__name__

    def symbol_wrapper(self: Parser) -> Optional[Tree]:
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


def memoize_left_rec(method: Callable[[Parser], Optional[Tree]]):
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    def symbol_wrapper(self: Parser) -> Optional[Tree]:
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


class Parser:
    """Parsing base class."""

    def __init__(self, tokenizer: Tokenizer, *, verbose=False):
        self._tokenizer = tokenizer
        self._verbose = verbose
        self._level = 0
        self._symbol_cache: Dict[Tuple[Mark,
                                       Callable[[Parser], Optional[Tree]]],
                                 Tuple[Optional[Tree], Mark]] = {}
        self._token_cache: Dict[Tuple[Mark, str], bool] = {}
        # Pass through common tokeniser methods.
        # TODO: Rename to _mark and _reset.
        self.mark = self._tokenizer.mark
        self.reset = self._tokenizer.reset

    def showpeek(self):
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"

    @memoize
    def name(self) -> Optional[Tree]:
        tok = self._tokenizer.peek()
        if tok.type == token.NAME:
            self._tokenizer.getnext()
            return Tree('NAME', value=tok.string)
        return None

    @memoize
    def number(self) -> Optional[Tree]:
        tok = self._tokenizer.peek()
        if tok.type == token.NUMBER:
            self._tokenizer.getnext()
            return Tree('NUMBER', value=tok.string)
        return None

    @memoize
    def string(self) -> Optional[Tree]:
        tok = self._tokenizer.peek()
        if tok.type == token.STRING:
            self._tokenizer.getnext()
            return Tree('STRING', value=tok.string)
        return None

    @memoize
    def curly_stuff(self) -> Optional[Tree]:
        tok = self._tokenizer.peek()
        if tok.type == CURLY_STUFF:
            self._tokenizer.getnext()
            return Tree('CURLY_STUFF', value=tok.string)
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

    def make_syntax_error(self, filename="<unknown>") -> NoReturn:
        tok = self._tokenizer.diagnose()
        return SyntaxError("pegen parse failure", (filename, tok.start[0], 1 + tok.start[1], tok.line))


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
        if ((name := self.name()) and
            self.expect(':') and
            (alts := self.alternatives())):
            return Tree('Rule', name, alts)
        return None

    @memoize_left_rec
    def alternatives(self) -> Optional[Tree]:
        """
        This is the actual (naive) code; it is not memoized.

        alternatives: alternatives '|' alternative | alternative
        """
        mark = self.mark()
        if ((left := self.alternatives()) and
            self.expect('|') and
            (right := self.alternative())):
            if left.type == 'Alts':
                alts = list(left.args)
                alts.append(right)
            else:
                alts = [left, right]
            return Tree('Alts', *alts)
        self.reset(mark)
        return self.alternative()

    @memoize
    def alternative(self) -> Optional[Tree]:
        """
        alternative: (named_item alternative | named_item) [CURLY_STUFF]
        """
        mark = self.mark()
        if (item := self.named_item()) and (alt := self.alternative()):
            items = [item]
            if alt.type == 'Alt':
                items.extend(alt.args)
            else:
                items.append(alt)
            if c := self.curly_stuff():
                items.append(c)
            return Tree('Alt', *items)
        self.reset(mark)
        if not (item := self.named_item()):
            return None
        if c := self.curly_stuff():
            return Tree('Alt', item, c)
        return item

    @memoize
    def named_item(self) -> Optional[Tree]:
        """
        named_item: NAME '=' item | item
        """
        mark = self.mark()
        if (name := self.name()) and self.expect('=') and (item := self.item()):
            return Tree('Named', name, item)
        self.reset(mark)
        return self.item()

    @memoize
    def item(self) -> Optional[Tree]:
        """
        item: optional | atom '*' | atom '+' | atom ' '* '?' | atom

        Note that optional cannot be followed by * or + or ?.

        Also note that '?' is an error to the Python tokenizer; every
        space before it is also returned as an error in this case, so
        we must ignore that.  (Somehow it seems important to support
        this syntax though.)
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
        if atom := self.atom():
            while self.expect(' '):
                pass
            if self.expect('?'):
                return Tree('Opt', atom)
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
            return alts
        return None


PARSER_PREFIX = """#!/usr/bin/env python3.8
# @generated by pegen.py from {filename}
from __future__ import annotations

import ast
import sys
import tokenize

from pegen import memoize, memoize_left_rec, Parser, Tokenizer, Tree

"""

PARSER_SUFFIX = """

if __name__ == '__main__':
    from pegen import simple_parser_main
    simple_parser_main(GeneratedParser)
"""

class ParserGenerator:

    def __init__(self, grammar: Tree, filename: str = ""):
        assert grammar.type == 'Grammar', (grammar.type, grammar.args, grammar.value)
        self.grammar = grammar
        self.filename = filename
        self.input: Optional[str] = None
        self.file: Optional[TextIO] = None
        self.level = 0

    @contextlib.contextmanager
    def indent(self) -> None:
        self.level += 1
        try:
            yield
        finally:
            self.level -= 1

    def print(self, *args):
        if not args:
            print(file=self.file)
        else:
            print("    "*self.level, end="", file=self.file)
            print(*args, file=self.file)

    def printblock(self, lines):
        for line in lines.splitlines():
            self.print(line)

    def set_output(self, filename: str) -> None:
        self.file = open(filename, 'w')

    def close(self) -> None:
        file = self.file
        if file:
            self.file = None
            file.close()

    def generate_parser(self) -> None:
        self.print(PARSER_PREFIX.format(filename=self.filename))
        self.print("class GeneratedParser(Parser):")
        self.todo: Dict[str, Tree] = {}  # Rules to generate
        self.done: Dict[str, Tree] = {}  # Rules generated
        self.counter = 0
        for rule in self.grammar.args:
            self.todo[str(rule.args[0])] = rule.args[1]
        while self.todo:
            for rulename, rhs in list(self.todo.items()):
                self.done[rulename] = rhs
                del self.todo[rulename]
                self.print()
                with self.indent():
                    self.gen_rule(rulename, rhs)
        self.print(PARSER_SUFFIX.rstrip('\n'))

    def name_tree(self, tree: Tree) -> str:
        ## for k, v in self.todo.items() | self.done.items():
        ##     if tree == v:
        ##         return k
        self.counter += 1
        name = f'_tmp_{self.counter}'  # TODO: Pick a nicer name.
        if name not in self.todo and name not in self.done:
            self.todo[name] = tree
        return name

    def is_recursive(self, rulename: str, rhs: Tree) -> bool:
        # This is just a PoC -- we only find recursion if one of the
        # alternatives directly starts with this rule.  I'm sure
        # there's a real graph algorithm that can determine whether a
        # node is recursive, I'm just too lazy to look it up.
        if rhs.type == 'Alts':
            alts = list(rhs.args)
        else:
            alts = [rhs]
        for alt in alts:
            if alt.type == 'Alt':
                items = list(alt.args)
            else:
                items = [alt]
            item = items[0]
            if item.type == 'NAME' and item.value == rulename:
                return True
        return False

    def gen_rule(self, rulename: str, rhs: Tree) -> None:
        if self.is_recursive(rulename, rhs):
            self.print("@memoize_left_rec")
        else:
            self.print("@memoize")
        self.print(f"def {rulename}(self):")
        with self.indent():
            self.print("mark = self.mark()")
            if rhs.type == 'Alts':
                for alt in rhs.args:
                    self.gen_alt(rulename, alt)
            elif rhs.type in ('ZeroOrMore', 'OneOrMore'):
                self.print("children = []")
                self.gen_alt(rulename, rhs.args[0], special=rhs.type)
            else:
                self.gen_alt(rulename, rhs)
            if rhs.type == 'Opt':
                self.print("return Tree('Empty')")
            elif rhs.type == 'ZeroOrMore':
                self.print("return Tree('Repeat', *children)")
            elif rhs.type == 'OneOrMore':
                self.print("if children:")
                with self.indent():
                    self.print("return Tree('Repeat', *children)")
                self.print("return None")
            else:
                self.print("return None")

    def gen_alt(self, rulename: str, alt: Tree, *, special=None) -> None:
        if alt.type == 'Alt':
            items = list(alt.args)
        elif alt.type == 'Opt':
            items = [alt.args[0]]
        else:
            items = [alt]
        if items[-1].type == "CURLY_STUFF":
            curly_stuff = items.pop(-1)
        else:
            curly_stuff = None
        self.print("#", str(alt))
        if special in ('ZeroOrMore', 'OneOrMore'):
            # TODO: Collect children.
            self.print("while (")
        else:
            self.print("if (")
        children = []
        first = True
        with self.indent():
            for item in items:
                if first:
                    first = False
                else:
                    self.print("and")
                child, text = self.gen_named_item(item, children)
                if child:
                    self.print(f"({child} := {text})")
                    children.append(child)
                else:
                    self.print(text)
        self.print("):")
        with self.indent():
            if curly_stuff:
                code = curly_stuff.value
                assert code[0] == '{' and code[-1] == '}', repr(code)
                child = code[1:-1].strip()
            elif rulename.startswith('_') and len(children) == 1:
                child = f"{children[0]}"
            else:
                child = f"Tree({rulename!r}, {', '.join(children)})"
            if special in ('ZeroOrMore', 'OneOrMore'):
                self.print("mark = self.mark()")
                self.print(f"children.append({child})")
            else:
                self.print(f"return {child}")
        self.print("self.reset(mark)")

    def gen_named_item(self, item: Tree, children: List[str]) -> Tuple[str, str]:
        if item.type == 'Named':
            item_name = item.args[0].value
            item_proper = item.args[1]
            return self.gen_item(item_name, item_proper, children)
        else:
            return self.gen_item(None, item, children)

    def gen_item(self, item_name: str, item: Tree, children: List[str]) -> Tuple[str, str]:
        if item.type == 'STRING':
            return item_name, f"self.expect({item.value})"
        if item.type == 'NAME':
            name = item.value
            if name in exact_token_types or name in ('NEWLINE', 'DEDENT', 'INDENT', 'ENDMARKER'):
                return item_name, f"self.expect({item.value!r})"
            if name in ('NAME', 'STRING', 'NUMBER', 'CURLY_STUFF'):
                name = name.lower()
                return item_name or dedupe(name, children), f"self.{name}()"
            if name in self.todo or name in self.done:
                return item_name or dedupe(name, children), f"self.{name}()"
            # TODO: Report as an error in the grammar, with line
            # number and column of the reference.
            raise RuntimeError(f"Don't know what {name!r} is")
        if item.type in ('Opt', 'ZeroOrMore', 'OneOrMore'):
            prefix = '_' + item.type.lower() + '_'
            subitem = item.args[0]
            if subitem.type == 'NAME':
                subname = subitem.value
            else:
                subname = self.name_tree(subitem)
            name = prefix + subname
            if name not in self.todo and name not in self.done:
                self.todo[name] = item
            return item_name or dedupe(name, children), f"self.{name}()"
        if item.type in ('Alts', 'Alt'):
            name = self.name_tree(item)
            return item_name or dedupe(name, children), f"self.{name}()"

        raise RuntimeError(f"Unrecognized item {item!r}")


def dedupe(name: str, names: Container[str]) -> str:
    origname = name
    counter = 0
    while name in names:
        counter += 1
        name = f"{origname}_{counter}"
    return name


def print_memstats() -> bool:
    MiB: Final = 2**20
    try:
        import psutil
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


# Hack: extra token to represent '{ ... }'
CURLY_STUFF = token.N_TOKENS + 1
token.tok_name[CURLY_STUFF] = 'CURLY_STUFF'


def grammar_tokenizer(token_generator):
    for tok in token_generator:
        if tok.string == '{':
            start = tok.start
            nest = 1
            accumulated = ['{']
            for tok in token_generator:
                accumulated.append(tok.string)
                if tok.string == '{':
                    nest += 1
                elif tok.string == '}':
                    nest -= 1
                    if nest == 0:
                        end = tok.end
                        break
            print(f"CURLY_STUFF: {' '.join(accumulated)}")
            yield tokenize.TokenInfo(CURLY_STUFF, " ".join(accumulated), start, end, "")
        else:
            yield tok


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
    verbose_tokenizer = verbose >= 2
    verbose_parser = verbose == 1 or verbose >= 3

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
        endpos = file.tell()
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
        print("Total time: %.3f sec; %d lines (%d bytes)" % (dt, nlines, endpos),
              end="")
        if dt:
            print("; %.3f lines/sec" % (nlines / dt))
        else:
            print()
        print("Caches sizes:")
        print(f"  token array : {len(tokenizer._tokens):10}")
        print(f"  symbol cache: {len(parser._symbol_cache):10}")
        print(f"  token cache : {len(parser._token_cache):10}")
        print_memstats()


argparser = argparse.ArgumentParser(prog='pegen', description="Experimental PEG-like parser generator")
argparser.add_argument('-q', '--quiet', action='store_true', help="Don't print the parsed grammar")
argparser.add_argument('-v', '--verbose', action='count', default=0,
                       help="Print timing stats; repeat for more debug output")
argparser.add_argument('-o', '--output', default='parse.py', metavar='OUT',
                       help="Where to write the generated parser (default parse.py)")
argparser.add_argument('filename', help="Grammar description")


def main() -> None:
    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose >= 2
    verbose_parser = verbose == 1 or verbose >= 3
    t0 = time.time()

    with open(args.filename) as file:
        tokenizer = Tokenizer(grammar_tokenizer(tokenize.generate_tokens(file.readline)),
                              verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        tree = parser.start()
        if not tree:
            err = parser.make_syntax_error(args.filename)
            traceback.print_exception(err.__class__, err, None)
            sys.exit(1)
        endpos = file.tell()

    if not args.quiet:
        if tree.type == 'Grammar':
            for arg in tree.args:
                print(arg)
        else:
            print(tree)

    genr = ParserGenerator(tree, args.filename)
    genr.set_output(args.output)
    genr.generate_parser()
    os.chmod(args.output, 0o755)  # TODO: Honor umask.

    t1 = time.time()

    if not args.quiet:
        dt = t1 - t0
        diag = tokenizer.diagnose()
        nlines = diag.end[0]
        if diag.type == token.ENDMARKER:
            nlines -= 1
        print("Total time: %.3f sec; %d lines (%d bytes)" % (dt, nlines, endpos), end="")
        if dt:
            print("; %.3f lines/sec" % (nlines / dt))
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
