#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import contextlib
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
        if verbose:
            tok = self._tokenizer.peek()
            fill = ' '*mark + ' '
        if key not in self._symbol_cache:
            if verbose:
                print(f" {fill} {shorttok(tok)}: {' '*self._level}({method_name}")
            self._level += 1
            tree = method(self)
            self._level -= 1
            if tree:
                endmark = self.mark()
                if verbose:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level} {tree!r})  # fresh")
            else:
                endmark = mark
                self.reset(endmark)
                if verbose:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level} No {method_name})  # fresh")
            self._symbol_cache[key] = tree, endmark
        else:
            tree, endmark = self._symbol_cache[key]
            if tree:
                self.reset(endmark)
                if verbose:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level} {tree!r})  # cached")
            else:
                if verbose:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level} No {method_name})  # cached")
        return tree

    return symbol_wrapper


def memoize_expect(method: Callable[[Parser], bool]) -> bool:
    """Memoize the expect() method."""

    def expect_wrapper(self: Parser, type: str) -> bool:
        mark = self.mark()
        key = mark, type
        # Fast path: cache hit, and not verbose.
        if key in self._token_cache and not self._verbose:
            res, endmark = self._token_cache[key]
            if res:
                self.reset(endmark)
                # Uncomment these when parsing Python, to save
                # up to 80% of memory (though little time!).
                # self._token_cache.clear()
                # self._symbol_cache.clear()
            return res
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        if verbose:
            tok = self._tokenizer.peek()
            fill = ' '*mark + ' '
        if key not in self._token_cache:
            res = method(self, type)
            if res:
                if verbose:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level}({type!r})  # fresh")
                endmark = self.mark()
            else:
                if verbose:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level}(Not {type!r})  # fresh")
                endmark = mark
            self._token_cache[key] = res, endmark
        else:
            res, endmark = self._token_cache[key]
            if verbose:
                if res:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level}({type!r})  # cached")
                else:
                    print(f" {fill} {shorttok(tok)}: {' '*self._level}(Not {type!r})  # cached")
        self.reset(endmark)
        return res

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

    @memoize_expect
    def expect(self, type: str) -> bool:
        tok = self._tokenizer.peek()
        if tok.string == type:
            self._tokenizer.getnext()
            return True
        if type in exact_token_types:
            if tok.type == exact_token_types[type]:
                self._tokenizer.getnext()
                return True
        if type in token.__dict__:
            if tok.type == token.__dict__[type]:
                self._tokenizer.getnext()
                return True
        if tok.type == token.OP and tok.string == type:
            self._tokenizer.getnext()
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
        rule: NAME (':' | '<-') alternatives
        """
        if ((name := self.name()) and
            (self.expect(':') or self.expect('<-') or (self.expect('<') and self.expect('-'))) and
            (alts := self.alternatives())):
            return Tree('Rule', name, alts)
        return None

    @memoize
    def alternatives(self) -> Optional[Tree]:
        """
        alternatives: alternative ('|' | '/') alternatives | alternative
        """
        mark = self.mark()
        if ((left := self.alternative()) and
            (self.expect('|')  or self.expect('/')) and
            (right := self.alternatives())):
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
        item: optional | atom '*' | atom '+' | atom '?' | atom

        Note that optional cannot be followed by * or + or ?.

        Also note that '?' is an error to the Python tokenizer.
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
        if (atom := self.atom()) and self.expect('?'):
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

import sys
import tokenize

from pegen import memoize, Parser, Tokenizer, Tree

"""

PARSER_SUFFIX = """

def main():
    import argparse, time, token
    from pegen import print_memstats
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-v', '--verbose', action='count', default=0,
                           help="Print timing stats; repeat for more debug output")
    argparser.add_argument('-q', '--quiet', action='store_true',
                           help="Don't print the parsed program")
    argparser.add_argument('filename')
    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose == 2 or verbose >= 4
    verbose_parser = verbose >= 3
    t0 = time.time()
    with open(args.filename) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline), verbose=verbose_tokenizer)
        parser = GeneratedParser(tokenizer, verbose=verbose_parser)
        tree = parser.start()
        endpos = file.tell()
    t1 = time.time()
    if not tree:
        print("Syntax error at:", tokenizer.diagnose(), file=sys.stderr)
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
              end="", file=sys.stderr)
        if dt:
            print("; %.3f lines/sec" % (nlines / dt), file=sys.stderr)
        else:
            print(file=sys.stderr)
        print("Caches sizes:", file=sys.stderr)
        print(f"  token array : {len(tokenizer._tokens):10}", file=sys.stderr)
        print(f"  symbol cache: {len(parser._symbol_cache):10}", file=sys.stderr)
        print(f"  token cache : {len(parser._token_cache):10}", file=sys.stderr)
        print_memstats()


if __name__ == '__main__':
    main()
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

    def print(self, *args, **kwds):
        print("    "*self.level, end="", file=self.file)
        print(*args, **kwds, file=self.file)

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

    def gen_rule(self, rulename: str, rhs: Tree) -> None:
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
            items = alt.args
        elif alt.type == 'Opt':
            items = [alt.args[0]]
        else:
            items = [alt]
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
                child, text = self.gen_item(item, children)
                if child:
                    self.print(f"({child} := {text})")
                    children.append(child)
                else:
                    self.print(text)
        self.print("):")
        with self.indent():
            if rulename.startswith('_') and len(children) == 1:
                child = f"{children[0]}"
            else:
                child = f"Tree({rulename!r}, {', '.join(children)})"
            if special in ('ZeroOrMore', 'OneOrMore'):
                self.print("mark = self.mark()")
                self.print(f"children.append({child})")
            else:
                self.print(f"return {child}")
        self.print("self.reset(mark)")

    def gen_item(self, item: Tree, children: List[str]) -> Tuple[str, str]:
        if item.type == 'STRING':
            return None, f"self.expect({item.value})"
        if item.type == 'NAME':
            name = item.value
            if name in exact_token_types or name in ('NEWLINE', 'DEDENT', 'INDENT', 'ENDMARKER'):
                return None, f"self.expect({item.value!r})"
            if name in ('NAME', 'STRING', 'NUMBER'):
                name = name.lower()
                return dedupe(name, children), f"self.{name}()"
            if name in self.todo or name in self.done:
                return dedupe(name, children), f"self.{name}()"
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
            return dedupe(name, children), f"self.{name}()"
        if item.type in ('Alts', 'Alt'):
            name = self.name_tree(item)
            return dedupe(name, children), f"self.{name}()"
            
        raise RuntimeError(f"Unrecognized item {item!r}")
        name = self.name_tree(item)
        return name, f"self.{name}()"


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
    print("Memory stats:", file=sys.stderr)
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
        print(f"  {key:12.12s}: {value:10.0f} MiB", file=sys.stderr)
    return True


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
    verbose_tokenizer = verbose == 2 or verbose >= 4
    verbose_parser = verbose >= 3
    t0 = time.time()

    with open(args.filename) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline), verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        tree = parser.start()
        if not tree:
            print("Syntax error at:", tokenizer.diagnose(), file=sys.stderr)
            sys.exit(1)
        endpos = file.tell()

    if not args.quiet:
        if tree.type == 'Grammar':
            for arg in tree.args:
                print(arg)
        else:
            print(tree)

    genr = ParserGenerator(tree, args.filename)
    if args.output:
        genr.set_output(args.output)
    genr.generate_parser()

    t1 = time.time()

    if verbose:
        dt = t1 - t0
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
        print("Caches sizes:", file=sys.stderr)
        print(f"  token array : {len(tokenizer._tokens):10}", file=sys.stderr)
        print(f"  symbol cache: {len(parser._symbol_cache):10}", file=sys.stderr)
        print(f"  token cache : {len(parser._token_cache):10}", file=sys.stderr)
        if not print_memstats():
            print("(Can't find psutil; install it for memory stats.)", file=sys.stderr)


if __name__ == '__main__':
    main()
