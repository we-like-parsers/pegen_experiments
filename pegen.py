#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

from __future__ import annotations  # Requires Python 3.7 or later

import argparse
import ast
import contextlib
import os
import sys
import time
import token
import tokenize
import traceback
from typing import *

import sccutils

T = TypeVar('T')

exact_token_types = token.EXACT_TOKEN_TYPES  # type: ignore

Mark = int  # NewType('Mark', int)


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
            if tok.type == token.ERRORTOKEN and tok.string.isspace():
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
            if tok.type == token.ERRORTOKEN and tok.string.isspace():
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
            #
            # TODO: Fix this for indirectly left-recursive rules!
            # E.g.
            #   start: foo '+' bar | bar
            #   foo: start
            #   bar: NUMBER
            # (We don't clear the cache for foo.)

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


class Rule:
    def __init__(self, name: str, type: str, rhs: Rhs):
        self.name = name
        self.type = type
        self.rhs = rhs
        self.visited = False
        self.nullable = None
        self.left_recursive = False
        self.leader = False

    def __str__(self):
        if self.type is None:
            return f"{self.name}: {self.rhs}"
        else:
            return f"{self.name}[{self.type}]: {self.rhs}"

    def __repr__(self):
        return f"Rule({self.name!r}, {self.type!r}, {self.rhs!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        if self.visited:
            # A left-recursive rule is considered non-nullable.
            return False
        self.visited = True
        self.nullable = self.rhs.visit(rules)
        assert self.nullable is not None
        return self.nullable

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()

    def flatten(self) -> Rhs:
        # If it's a single parenthesized group, flatten it.
        is_loop = self.name.startswith('_loop_')
        rhs = self.rhs
        if (not is_loop
            and len(rhs.alts) == 1
            and len(rhs.alts[0].items) == 1
            and isinstance(rhs.alts[0].items[0].item, Group)):
            rhs = rhs.alts[0].items[0].item.rhs
        return rhs

    def collect_todo(self, gen: ParserGenerator) -> None:
        rhs = self.flatten()
        rhs.collect_todo(gen)

    def pgen_func(self, gen: ParserGenerator, rulename: str):
        is_loop = rulename.startswith('_loop_')
        rhs = self.flatten()
        if self.left_recursive:
            if self.leader:
                gen.print("@memoize_left_rec")
            # Non-leader rules in a cycle are not memoized
        else:
            gen.print("@memoize")
        gen.print(f"def {rulename}(self):")
        with gen.indent():
            gen.print(f"# {rulename}: {rhs}")
            if self.nullable:
                gen.print(f"# nullable={self.nullable}")
            gen.print("mark = self.mark()")
            if is_loop:
                gen.print("children = []")
            rhs.pgen_body(gen, is_loop)
            if is_loop:
                gen.print("return children")
            else:
                gen.print("return None")

    def cgen_func(self, gen: ParserGenerator, rulename: str) -> None:
        is_loop = rulename.startswith('_loop')
        is_repeat1 = rulename.startswith('_loop1')
        memoize = not self.leader
        if self.left_recursive:
            print(f"Warning: {rulename} is left-recursive; generating bogus code",
                  file=sys.stderr)

        rhs = self.flatten()
        gen.print(f"// {self}")
        type = self.type or 'void*'
        gen.print(f"static {type}")
        gen.print(f"{rulename}_rule(Parser *p)")
        gen.print("{")
        with gen.indent():
            gen.print(f"{type} res = NULL;")
            gen.print("int mark = p->mark;")
            if memoize:
                gen.print(f"if (is_memoized(p, {rulename}_type, &res))")
            with gen.indent():
                gen.print("return res;")
            if is_loop:
                gen.print("void **children = PyMem_Malloc(0);")
                gen.print(f'if (!children) panic("malloc {rulename}");')
                gen.print("ssize_t n = 0;")
            rhs.cgen_body(gen, is_loop, rulename if memoize else None)
            if is_loop:
                if is_repeat1:
                    gen.print("if (n == 0) {")
                    with gen.indent():
                        gen.print("PyMem_Free(children);")
                        gen.print("return NULL;")
                    gen.print("}")
                gen.print("asdl_seq *seq = _Py_asdl_seq_new(n, p->arena);")
                gen.print(f'if (!seq) panic("asdl_seq_new {rulename}");')
                gen.print("for (int i = 0; i < n; i++) asdl_seq_SET(seq, i, children[i]);")
                gen.print("PyMem_Free(children);")
                if rulename:
                    gen.print(f"insert_memo(p, mark, {rulename}_type, seq);")
                gen.print("return seq;")
            else:
                gen.print("// Fail")
                if memoize:
                    gen.print(f"insert_memo(p, mark, {rulename}_type, NULL);",
                              "// Memoize negative result")
                gen.print("return NULL;")
        gen.print("}")


class Leaf:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


class NameLeaf(Leaf):
    """The value is the name."""

    def __str__(self):
        if self.value == 'ENDMARKER':
            return '$'
        if self.value == 'CUT':
            return '~'
        return super().__str__()

    def __repr__(self):
        return f"NameLeaf({self.value!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        if self.value in rules:
            return rules[self.value].visit(rules)
        # Token or unknown; never empty.
        return False

    def initial_names(self) -> AbstractSet[str]:
        return {self.value}

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        name = self.value
        if name in ('NAME', 'NUMBER', 'STRING', 'CUT', 'CURLY_STUFF'):
            name = name.lower()
            if cpython:
                return f"{name}_var", f"{name}_token(p)"
            else:
                return name, f"self.{name}()"
        if name in ('NEWLINE', 'DEDENT', 'INDENT', 'ENDMARKER'):
            if cpython:
                name = name.lower()
                return f"{name}_var", f"{name}_token(p)"
            else:
                return name.lower(), f"self.expect({name!r})"
        if cpython:
            return f"{name}_var", f"{name}_rule(p)"
        else:
            return name, f"self.{name}()"


class StringLeaf(Leaf):
    """The value is a string literal, including quotes."""

    def __repr__(self):
        return f"StringLeaf({self.value!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        # The string token '' is considered empty.
        return not self.value

    def initial_names(self) -> AbstractSet[str]:
        return set()

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        if cpython:
            val = ast.literal_eval(self.value)
            type = exact_token_types[val]
            return 'string_var', f'expect_token(p, {type})'
        else:
            return 'string', f"self.expect({self.value})"


class Rhs:
    def __init__(self, alts: List[Alt]):
        self.alts = alts
        self.memo = None

    def __str__(self):
        return " | ".join(str(alt) for alt in self.alts)

    def __repr__(self):
        return f"Rhs({self.alts!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        for alt in self.alts:
            if alt.visit(rules):
                return True
        return False

    def initial_names(self) -> AbstractSet[str]:
        names = set()
        for alt in self.alts:
            names |= alt.initial_names()
        return names

    def collect_todo(self, gen: ParserGenerator) -> None:
        for alt in self.alts:
            alt.collect_todo(gen)

    def pgen_body(self, gen: ParserGenerator, is_loop: bool = False) -> None:
        if is_loop:
            assert len(self.alts) == 1
        for alt in self.alts:
            alt.pgen_block(gen, is_loop)

    def cgen_body(self, gen: ParserGenerator, is_loop: bool, rulename: Optional[str]) -> None:
        if is_loop:
            assert len(self.alts) == 1
        vars = set()
        for alt in self.alts:
            vars |= alt.collect_vars(gen)
        for v in sorted(vars):
            gen.print(f"void *{v};")
        for alt in self.alts:
            alt.cgen_block(gen, is_loop, rulename)

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        if self.memo is not None:
            return self.memo
        if len(self.alts) == 1 and len(self.alts[0].items) == 1:
            self.memo = self.alts[0].items[0].make_call(gen, cpython)
        else:
            name = gen.name_node(self)
            if cpython:
                self.memo = f"{name}_var", f"{name}_rule(p)"
            else:
                self.memo =name, f"self.{name}()"
        return self.memo


class Alt:
    def __init__(self, items: List[NamedItem], *, icut: int = -1, action: Optional[str] = None):
        self.items = items
        self.icut = icut
        self.action = action

    def __str__(self):
        core = " ".join(str(item) for item in self.items)
        if self.action:
            return f"{core} {self.action}"
        else:
            return core

    def __repr__(self):
        args = [repr(self.items)]
        if self.icut >= 0:
            args.append(f"icut={self.icut}")
        if self.action:
            args.append(f"action={self.action!r}")
        return f"Alt({', '.join(args)})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        for item in self.items:
            if not item.visit(rules):
                return False
        return True

    def initial_names(self) -> AbstractSet[str]:
        names = set()
        for item in self.items:
            names |= item.initial_names()
            if not item.nullable:
                break
        return names

    def collect_todo(self, gen: ParserGenerator) -> None:
        for item in self.items:
            item.collect_todo(gen)

    def pgen_block(self, gen: ParserGenerator, is_loop: bool = False):
        names = []
        gen.print("cut = False")  # TODO: Only if needed.
        if is_loop:
            gen.print("while (")
        else:
            gen.print("if (")
        with gen.indent():
            first = True
            for item in self.items:
                if first:
                    first = False
                else:
                    gen.print("and")
                item.pgen_item(gen, names)
        gen.print("):")
        with gen.indent():
            action = self.action
            if not action:
                action = f"[{', '.join(names)}]"
            else:
                assert action[0] == '{' and action[-1] == '}', repr(action)
                action = action[1:-1].strip()
            if is_loop:
                gen.print(f"children.append({action})")
                gen.print(f"mark = self.mark()")
            else:
                gen.print(f"return {action}")
        gen.print("self.reset(mark)")
        # Skip remaining alternatives if a cut was reached.
        gen.print("if cut: return None")  # TODO: Only if needed.

    def collect_vars(self, gen: ParserGenerator) -> AbstractSet[str]:
        names = []
        for item in self.items:
            item.add_vars(gen, names)
        return set(names)

    def cgen_block(self, gen: ParserGenerator, is_loop: bool, rulename: Optional[str]):
        # TODO: Refactor this -- there are too many is_loop checks.
        gen.print(f"// {self}")
        names = []
        if is_loop:
            gen.print("while (")
        else:
            gen.print("if (")
        with gen.indent():
            first = True
            for item in self.items:
                if first:
                    first = False
                else:
                    gen.print("&&")
                item.cgen_item(gen, names)
        gen.print(") {")
        with gen.indent():
            action = self.action
            if not action:
                ## gen.print(f'fprintf(stderr, "Hit at %d: {self}, {names}\\n", p->mark);')
                if len(names) > 1:
                    gen.print(f"void *res = CONSTRUCTOR(p, {', '.join(names)});")
                else:
                    gen.print(f"void *res = {names[0]};")
            else:
                assert action[0] == '{' and action[-1] == '}', repr(action)
                action = action[1:-1].strip()
                gen.print(f"void *res = {action};")
                ## gen.print(f'fprintf(stderr, "Hit with action at %d: {self}, {names}, {action}\\n", p->mark);')
            if is_loop:
                gen.print("children = PyMem_Realloc(children, (n+1)*sizeof(void*));")
                gen.print(f'if (!children) panic("realloc {rulename}");')
                gen.print(f"children[n++] = res;")
                gen.print("mark = p->mark;")
            else:
                if rulename:
                    gen.print(f"insert_memo(p, mark, {rulename}_type, res);")
                gen.print(f"return res;")
        gen.print("}")
        gen.print("p->mark = mark;")


class NamedItem:
    def __init__(self, name: Optional[str], item: Item):
        self.name = name
        self.item = item
        self.nullable = None

    def __str__(self):
        if self.name:
            return f"{self.name}={self.item}"
        else:
            return str(self.item)

    def __repr__(self):
        return f"NamedItem({self.name!r}, {self.item!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        self.nullable = self.item.visit(rules)
        assert self.nullable is not None
        return self.nullable

    def initial_names(self) -> AbstractSet[str]:
        return self.item.initial_names()

    def collect_todo(self, gen: ParserGenerator) -> None:
        self.item.make_call(gen, True)

    def pgen_item(self, gen: ParserGenerator, names: List[str]):
        name, call = self.item.make_call(gen, cpython=False)
        if self.name:
            name = self.name
        if not name:
            gen.print(call)
        else:
            if name != 'cut':
                name = dedupe(name, names)
            gen.print(f"({name} := {call})")

    def add_vars(self, gen: ParserGenerator, names: List[str]) -> None:
        name, call = self.make_call(gen, cpython=True)
        if name != 'cut':
            name = dedupe(name, names)

    def cgen_item(self, gen: ParserGenerator, names: List[str]):
        name, call = self.make_call(gen, cpython=True)
        if not name:
            gen.print(call)
        else:
            if name != 'cut':
                name = dedupe(name, names)
            gen.print(f"({name} = {call})")

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        name, call = self.item.make_call(gen, cpython)
        if self.name:
            name = self.name
        return name, call


class Lookahead:
    def __init__(self, node: Plain, sign: str):
        self.node = node
        self.sign = sign

    def __str__(self):
        return f"{self.sign}{self.node}"

    def visit(self, rules: Dict[str, Rule]) -> bool:
        return True

    def initial_names(self) -> AbstractSet[str]:
        return set()

    def make_call_helper(self, gen: ParserGenerator, cpython: bool) -> str:
        name, call = self.node.make_call(gen, cpython)
        head, tail = call.split('(', 1)
        assert tail[-1] == ')'
        tail = tail[:-1]
        return head, tail


class PositiveLookahead(Lookahead):
    def __init__(self, node: Plain):
        super().__init__(node, '&')

    def __repr__(self):
        return f"PositiveLookahead({self.node!r})"

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        head, tail = self.make_call_helper(gen, cpython)
        if cpython:
            return None, f"positive_lookahead({head}, {tail})"
        else:
            return None, f"self.positive_lookahead({head}, {tail})"

class NegativeLookahead(Lookahead):
    def __init__(self, node: Plain):
        super().__init__(node, '!')

    def __repr__(self):
        return f"NegativeLookahead({self.node!r})"

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        head, tail = self.make_call_helper(gen, cpython)
        if cpython:
            return None, f"negative_lookahead({head}, {tail})"
        else:
            return None, f"self.negative_lookahead({head}, {tail})"


class Opt:
    def __init__(self, node: Plain):
        self.node = node

    def __str__(self):
        return f"{self.node}?"

    def __repr__(self):
        return f"Opt({self.node!r})"

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        name, call = self.node.make_call(gen, cpython)
        if cpython:
            return "opt_var", f"{call}, 1"  # Using comma operator!
        else:
            return "opt", f"{call},"  # Note trailing comma!

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        return True

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat:
    """Shared base class for x* and x+."""

    def __init__(self, node: Plain):
        self.node = node
        self.memo = None

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat0(Repeat):
    def __str__(self):
        return f"({self.node})*"

    def __repr__(self):
        return f"Repeat0({self.node!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        return True

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        if self.memo is not None:
            return self.memo
        name = gen.name_loop(self.node, False)
        if cpython:
            self.memo = f"{name}_var", f"{name}_rule(p)"
        else:
            self.memo = name, f"self.{name}(),"  # Also a trailing comma!
        return self.memo


class Repeat1(Repeat):
    def __str__(self):
        return f"({self.node})+"

    def __repr__(self):
        return f"Repeat1({self.node!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        # TODO: What if self.node is itself nullable?
        return False

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        if self.memo is not None:
            return self.memo
        name = gen.name_loop(self.node, True)
        if cpython:
            self.memo = f"{name}_var", f"{name}_rule(p)"  # But not here!
        else:
            self.memo = name, f"self.{name}()"  # But no trailing comma here!
        return self.memo


class Group:
    def __init__(self, rhs: Rhs):
        self.rhs = rhs

    def __str__(self):
        return f"({self.rhs})"

    def __repr__(self):
        return f"Group({self.rhs!r})"

    def visit(self, rules: Dict[str, Rule]) -> Optional[bool]:
        return self.rhs.visit(rules)

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[str, str]:
        return self.rhs.make_call(gen, cpython)


Plain = Union[Leaf, Group]
Item = Union[Plain, Opt, Repeat]


class GrammarParser(Parser):
    """Hand-written parser for Grammar files."""

    @memoize
    def start(self) -> Optional[Dict[str, Rule]]:
        """
        start: rule+ ENDMARKER
        """
        mark = self.mark()
        rules = {}
        while rule := self.rule():
            rules[rule.name] = rule
            mark = self.mark()
        if self.expect('ENDMARKER'):
            return rules
        return None

    @memoize
    def rule(self) -> Optional[Rule]:
        """
        rule: NAME [ '[' NAME ']' ] ':' alternatives NEWLINE
        """
        mark = self.mark()
        if ((name := self.name()) and
                self.expect('[') and
                (type := self.name()) and
                self.expect(']') and
                self.expect(':') and
                (alts := self.alternatives()) and
                self.expect('NEWLINE')):
            return Rule(name.string, type.string, alts)
        self.reset(mark)
        if ((name := self.name()) and
                self.expect(':') and
                (alts := self.alternatives()) and
                self.expect('NEWLINE')):
            return Rule(name.string, None, alts)
        self.reset(mark)
        return None

    @memoize
    def alternatives(self) -> Optional[Rhs]:
        """
        alternatives: alternative ('|' alternative)*
        """
        mark = self.mark()
        alts = []
        if alt := self.alternative():
            alts.append(alt)
        else:
            return None
        mark = self.mark()
        while self.expect('|') and (alt := self.alternative()):
            alts.append(alt)
            mark = self.mark()
        self.reset(mark)
        if not alts:
            return None
        return Rhs(alts)

    @memoize
    def alternative(self) -> Optional[Alt]:
        """
        alternative: named_item+ ('~' (named_item+ ['$'] | '$') | ['$']) [CURLY_STUFF]
        """
        mark = ubermark = self.mark()
        items = []
        while item := self.named_item():
            items.append(item)
            mark = self.mark()
        if not items:
            return None
        icut = -1
        if self.expect('~'):
            items.append(NamedItem(None, NameLeaf('CUT')))
            icut = len(items)
            mark = self.mark()
            while item := self.named_item():
                items.append(item)
                mark = self.mark()
        if self.expect('$'):
            items.append(NamedItem(None, NameLeaf('ENDMARKER')))
        if icut == len(items):
            # Can't have "cut" as the last item
            self.reset(ubermark)
            return None
        action = self.curly_stuff()
        return Alt(items, icut=icut, action=action.string if action else None)

    @memoize
    def named_item(self) -> Optional[NamedItem]:
        """
        named_item: NAME '=' item | item | lookahead
        """
        mark = self.mark()
        if (name := self.name()) and self.expect('=') and (item := self.item()):
            return NamedItem(name.string, item)
        self.reset(mark)
        item = self.item()
        if not item:
            self.reset(mark)  # Redundant?
            item = self.lookahead()
            if not item:
                return None
        return NamedItem(None, item)

    @memoize
    def lookahead(self) -> Optional[NamedItem]:
        """
        lookahead: ('&' | '!') atom
        """
        mark = self.mark()
        if (lookahead := (self.expect('&') or self.expect('!'))) and (atom := self.atom()):
            if lookahead.string == '&':
                return PositiveLookahead(atom)
            else:
                return NegativeLookahead(atom)
        self.reset(mark)
        return None

    @memoize
    def item(self) -> Optional[Item]:
        """
        item: '[' alternatives ']' | atom ('?' | '*' | '+')?
        """
        mark = self.mark()
        if self.expect('[') and (alts := self.alternatives()) and self.expect(']'):
            return Opt(alts)
        self.reset(mark)
        if atom := self.atom():
            mark = self.mark()
            if self.expect('?'):
                return Opt(atom)
            if self.expect('*'):
                return Repeat0(atom)
            if self.expect('+'):
                return Repeat1(atom)
            return atom
        return None

    @memoize
    def atom(self) -> Optional[Plain]:
        """
        atom: '(' alternatives ')' | NAME | STRING
        """
        mark = self.mark()
        if self.expect('(') and (alts := self.alternatives()) and self.expect(')'):
            return Group(alts)
        self.reset(mark)
        if name := self.name():
            return NameLeaf(name.string)
        if string := self.string():
            return StringLeaf(string.string)
        return None


MODULE_PREFIX = """\
#!/usr/bin/env python3.8
# @generated by pegen.py from {filename}
from __future__ import annotations

import ast
import sys
import tokenize

from pegen import memoize, memoize_left_rec, Parser

"""

MODULE_SUFFIX = """

if __name__ == '__main__':
    from pegen import simple_parser_main
    simple_parser_main(GeneratedParser)
"""

EXTENSION_PREFIX = """\
// @generated by pegen.py from {filename}

#include "pegen.h"
"""

EXTENSION_SUFFIX = """
// TODO: Allow specifying a module name

static PyObject *
parse_file(PyObject *self, PyObject *args)
{
    const char *filename;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return NULL;
    if (!run_parser(filename, (void *)start_rule))
        return NULL;
    Py_RETURN_NONE;
}

static PyMethodDef ParseMethods[] = {
    {"parse",  parse_file, METH_VARARGS, "Parse a file."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef parsemodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "parse",
    .m_doc = "A parser.",
    .m_methods = ParseMethods,
};

PyMODINIT_FUNC
PyInit_parse(void)
{
    PyObject *m = PyModule_Create(&parsemodule);
    if (m == NULL)
        return NULL;

    return m;
}

// The end
"""


class ParserGenerator:

    def __init__(self, rules: Dict[str, Rule], file: Optional[IO[Text]]):
        self.rules = rules
        self.file = file
        self.level = 0
        compute_nullables(rules)
        self.first_graph, self.first_sccs = compute_left_recursives(self.rules)
        self.todo = self.rules.copy()  # Rules to generate
        self.counter = 0  # For name_rule()/name_loop()

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

    def generate_python_module(self, filename: str) -> None:
        self.print(MODULE_PREFIX.format(filename=filename))
        self.print("class GeneratedParser(Parser):")
        while self.todo:
            for rulename, rule in list(self.todo.items()):
                del self.todo[rulename]
                self.print()
                with self.indent():
                    rule.pgen_func(self, rulename)
        self.print(MODULE_SUFFIX.rstrip('\n'))

    def generate_cpython_extension(self, filename: str) -> None:
        self.collect_todo()
        self.print(EXTENSION_PREFIX.format(filename=filename))
        for i, rulename in enumerate(self.todo, 1000):
            self.print(f"#define {rulename}_type {i}")
        self.print()
        for rulename, rule in self.todo.items():
            self.print(f"static {rule.type or 'void*'} {rulename}_rule(Parser *p);")
        self.print()
        while self.todo:
            for rulename, rule in list(self.todo.items()):
                del self.todo[rulename]
                self.print()
                rule.cgen_func(self, rulename)
        self.print(EXTENSION_SUFFIX.rstrip('\n'))

    def collect_todo(self) -> None:
        done = set()  # type: Set[str]
        while True:
            alltodo = set(self.todo)
            todo = alltodo - done
            if not todo:
                break
            for rulename in todo:
                self.todo[rulename].collect_todo(self)
            done = alltodo

    def name_node(self, rhs: Rhs) -> str:
        self.counter += 1
        name = f'_tmp_{self.counter}'  # TODO: Pick a nicer name.
        self.todo[name] = Rule(name, None, rhs)
        return name

    def name_loop(self, node: Plain, is_repeat1: bool) -> str:
        self.counter += 1
        if is_repeat1:
            prefix = '_loop1_'
        else:
            prefix = '_loop0_'
        name = f'{prefix}{self.counter}'  # TODO: It's ugly to signal via the name.
        self.todo[name] = Rule(name, None, Rhs([Alt([NamedItem(None, node)])]))
        return name


def compute_nullables(rules: Dict[str, Rule]) -> None:
    """Compute which rules in a grammar are nullable.

    Thanks to TatSu (tatsu/leftrec.py) for inspiration.
    """
    for rule in rules.values():
        rule.visit(rules)


def compute_left_recursives(rules: Dict[str, Rule]) -> Tuple[Dict[str, Set[str]], List[Set[str]]]:
    graph = make_first_graph(rules)
    sccs = list(sccutils.strongly_connected_components(graph.keys(), graph))
    for scc in sccs:
        if len(scc) > 1:
            for name in scc:
                rules[name].left_recursive = True
            # Try to find a leader such that all cycles go through it.
            leaders = set(scc)
            for start in scc:
                for cycle in sccutils.find_cycles_in_scc(graph, scc, start):
                    ## print("Cycle:", " -> ".join(cycle))
                    leaders -= (scc - set(cycle))
                    if not leaders:
                        raise ValueError(f"SCC {scc} has no leadership candidate (no element is included in all cycles)")
            ## print("Leaders:", leaders)
            leader = min(leaders)  # Pick an arbitrary leader from the candidates.
            rules[leader].leader = True
        else:
            name = min(scc)  # The only element.
            if name in graph[name]:
                rules[name].left_recursive = True
                rules[name].leader = True
    return graph, sccs


def make_first_graph(rules: Dict[str, Rule]) -> Dict[str, str]:
    """Compute the graph of left-invocations.

    There's an edge from A to B if A may invoke B at its initial
    position.

    Note that this requires the nullable flags to have been computed.
    """
    graph = {}
    vertices = set()
    for rulename, rhs in rules.items():
        graph[rulename] = names = rhs.initial_names()
        vertices |= names
    for vertex in vertices:
        graph.setdefault(vertex, set())
    return graph


def dedupe(name: str, names: List[str]) -> str:
    origname = name
    counter = 0
    while name in names:
        counter += 1
        name = f"{origname}_{counter}"
    names.append(name)
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
            print(f"; {nlines/dt:.0f} lines/sec")
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
            print(f"; {nlines/dt:.0f} lines/sec")
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
