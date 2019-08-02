from __future__ import annotations  # Requires Python 3.7 or later

import ast
import re
import sys
import time
import token
import tokenize
import traceback
from typing import AbstractSet, Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, TYPE_CHECKING, TypeVar, Union

from pegen.parser import memoize, Parser
from pegen.tokenizer import exact_token_types

if TYPE_CHECKING:
    from pegen.parser_generator import ParserGenerator


def dedupe(name: str, names: List[str]) -> str:
    origname = name
    counter = 0
    while name in names:
        counter += 1
        name = f"{origname}_{counter}"
    names.append(name)
    return name


class Rule:
    def __init__(self, name: str, type: Optional[str], rhs: Rhs):
        self.name = name
        self.type = type
        self.rhs = rhs
        self.visited = False
        self.nullable = False
        self.left_recursive = False
        self.leader = False

    def is_loop(self):
        return self.name.startswith('_loop')

    def __str__(self):
        if self.type is None:
            return f"{self.name}: {self.rhs}"
        else:
            return f"{self.name}[{self.type}]: {self.rhs}"

    def __repr__(self):
        return f"Rule({self.name!r}, {self.type!r}, {self.rhs!r})"

    def visit(self, rules: Dict[str, Rule]) -> bool:
        if self.visited:
            # A left-recursive rule is considered non-nullable.
            return False
        self.visited = True
        self.nullable = self.rhs.visit(rules)
        return self.nullable

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()

    def flatten(self) -> Rhs:
        # If it's a single parenthesized group, flatten it.
        rhs = self.rhs
        if (not self.is_loop()
            and len(rhs.alts) == 1
            and len(rhs.alts[0].items) == 1
            and isinstance(rhs.alts[0].items[0].item, Group)):
            rhs = rhs.alts[0].items[0].item.rhs
        return rhs

    def collect_todo(self, gen: ParserGenerator) -> None:
        rhs = self.flatten()
        rhs.collect_todo(gen)

    def pgen_func(self, gen: ParserGenerator):
        is_loop = self.is_loop()
        rhs = self.flatten()
        if self.left_recursive:
            if self.leader:
                gen.print("@memoize_left_rec")
            # Non-leader rules in a cycle are not memoized
        else:
            gen.print("@memoize")
        gen.print(f"def {self.name}(self):")
        with gen.indent():
            gen.print(f"# {self.name}: {rhs}")
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

    def cgen_func(self, gen: ParserGenerator) -> None:
        is_loop = self.is_loop()
        is_repeat1 = self.name.startswith('_loop1')
        memoize = not self.leader
        rhs = self.flatten()
        if is_loop:
            type = 'asdl_seq *'
        elif self.type:
            type = self.type
        else:
            type = 'void *'

        gen.print(f"// {self}")
        if self.left_recursive:
            gen.print(f"static {type} {self.name}_raw(Parser *);")

        gen.print(f"static {type}")
        gen.print(f"{self.name}_rule(Parser *p)")

        if self.left_recursive:
            gen.print("{")
            with gen.indent():
                gen.print(f"{type} res = NULL;")
                gen.print(f"if (is_memoized(p, {self.name}_type, &res))")
                with gen.indent():
                    gen.print("return res;")
                gen.print("int mark = p->mark;")
                gen.print("int resmark = p->mark;")
                gen.print("while (1) {")
                with gen.indent():
                    gen.print(f"update_memo(p, mark, {self.name}_type, res);")
                    gen.print("p->mark = mark;")
                    gen.print(f"void *raw = {self.name}_raw(p);")
                    gen.print("if (raw == NULL || p->mark <= resmark)")
                    with gen.indent():
                        gen.print("break;")
                    gen.print("resmark = p->mark;")
                    gen.print("res = raw;")
                gen.print("}")
                gen.print("p->mark = resmark;")
                gen.print("return res;")
            gen.print("}")
            gen.print(f"static {type}")
            gen.print(f"{self.name}_raw(Parser *p)")

        gen.print("{")
        with gen.indent():
            if is_loop:
                gen.print(f"void *res = NULL;")
            else:
                gen.print(f"{type} res = NULL;")
            if memoize:
                gen.print(f"if (is_memoized(p, {self.name}_type, &res))")
                with gen.indent():
                    gen.print("return res;")
            gen.print("int mark = p->mark;")
            if is_loop:
                gen.print("void **children = PyMem_Malloc(0);")
                gen.print(f'if (!children) panic("malloc {self.name}");')
                gen.print("ssize_t n = 0;")
            rhs.cgen_body(gen, is_loop, self.name if memoize else None)
            if is_loop:
                if is_repeat1:
                    gen.print("if (n == 0) {")
                    with gen.indent():
                        gen.print("PyMem_Free(children);")
                        gen.print("return NULL;")
                    gen.print("}")
                gen.print("asdl_seq *seq = _Py_asdl_seq_new(n, p->arena);")
                gen.print(f'if (!seq) panic("asdl_seq_new {self.name}");')
                gen.print("for (int i = 0; i < n; i++) asdl_seq_SET(seq, i, children[i]);")
                gen.print("PyMem_Free(children);")
                if self.name:
                    gen.print(f"insert_memo(p, mark, {self.name}_type, seq);")
                gen.print("return seq;")
            else:
                ## gen.print(f'fprintf(stderr, "Fail at %d: {self.name}\\n", p->mark);')
                gen.print("res = NULL;")
        if not is_loop:
            gen.print("  done:")
            with gen.indent():
                    if memoize:
                        gen.print(f"insert_memo(p, mark, {self.name}_type, res);")
                    gen.print("return res;")
        gen.print("}")


class Leaf:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value

    def visit(self, rules: Dict[str, Rule]) -> bool:
        raise NotImplementedError

    def initial_names(self) -> AbstractSet[str]:
        raise NotImplementedError

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
        raise NotImplementedError


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

    def visit(self, rules: Dict[str, Rule]) -> bool:
        if self.value in rules:
            return rules[self.value].visit(rules)
        # Token or unknown; never empty.
        return False

    def initial_names(self) -> AbstractSet[str]:
        return {self.value}

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
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

    def visit(self, rules: Dict[str, Rule]) -> bool:
        # The string token '' is considered empty.
        return not self.value

    def initial_names(self) -> AbstractSet[str]:
        return set()

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
        if cpython:
            val = ast.literal_eval(self.value)
            if re.match(r'[a-zA-Z_]\w*\Z', val):
                type = token.NAME
                return 'keyword', f'keyword_token(p, "{val}")'
            else:
                assert val in exact_token_types, f"{self.value} is not a known literal"
                type = exact_token_types[val]
                return 'literal', f'expect_token(p, {type})'
        else:
            return 'literal', f"self.expect({self.value})"


class Rhs:
    def __init__(self, alts: List[Alt]):
        self.alts = alts
        self.memo: Optional[Tuple[Optional[str], str]] = None

    def __str__(self):
        return " | ".join(str(alt) for alt in self.alts)

    def __repr__(self):
        return f"Rhs({self.alts!r})"

    def visit(self, rules: Dict[str, Rule]) -> bool:
        for alt in self.alts:
            if alt.visit(rules):
                return True
        return False

    def initial_names(self) -> AbstractSet[str]:
        names: Set[str] = set()
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
        vars = {}
        for alt in self.alts:
            vars.update(alt.collect_vars(gen))
        for v, type in sorted(vars.items()):
            if not type:
                type = 'void *'
            else:
                type += ' '
            gen.print(f"{type}{v};")
        for alt in self.alts:
            alt.cgen_block(gen, is_loop, rulename)

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
        if self.memo is not None:
            return self.memo
        if len(self.alts) == 1 and len(self.alts[0].items) == 1:
            self.memo = self.alts[0].items[0].make_call(gen, cpython)
        else:
            name = gen.name_node(self)
            if cpython:
                self.memo = f"{name}_var", f"{name}_rule(p)"
            else:
                self.memo = name, f"self.{name}()"
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

    def visit(self, rules: Dict[str, Rule]) -> bool:
        for item in self.items:
            if not item.visit(rules):
                return False
        return True

    def initial_names(self) -> AbstractSet[str]:
        names: Set[str] = set()
        for item in self.items:
            names |= item.initial_names()
            if not item.nullable:
                break
        return names

    def collect_todo(self, gen: ParserGenerator) -> None:
        for item in self.items:
            item.collect_todo(gen)

    def pgen_block(self, gen: ParserGenerator, is_loop: bool = False):
        names: List[str] = []
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

    def collect_vars(self, gen: ParserGenerator) -> Dict[str, Optional[str]]:
        names: List[str] = []
        types = {}
        for item in self.items:
            name, type = item.add_var(gen, names)
            types[name] = type
        return types

    def cgen_block(self, gen: ParserGenerator, is_loop: bool, rulename: Optional[str]):
        # TODO: Refactor this -- there are too many is_loop checks.
        gen.print(f"// {self}")
        names: List[str] = []
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
                    gen.print(f"res = CONSTRUCTOR(p, {', '.join(names)});")
                else:
                    gen.print(f"res = {names[0]};")
            else:
                assert action[0] == '{' and action[-1] == '}', repr(action)
                action = action[1:-1].strip()
                gen.print(f"res = {action};")
                ## gen.print(f'fprintf(stderr, "Hit with action at %d: {self}, {names}, {action}\\n", p->mark);')
            if is_loop:
                gen.print("children = PyMem_Realloc(children, (n+1)*sizeof(void *));")
                gen.print(f'if (!children) panic("realloc {rulename}");')
                gen.print(f"children[n++] = res;")
                gen.print("mark = p->mark;")
            else:
                if rulename:
                    gen.print(f"insert_memo(p, mark, {rulename}_type, res);")
                gen.print(f"goto done;")
        gen.print("}")
        gen.print("p->mark = mark;")


class NamedItem:
    def __init__(self, name: Optional[str], item: Item):
        self.name = name
        self.item = item
        self.nullable = False

    def __str__(self):
        if self.name:
            return f"{self.name}={self.item}"
        else:
            return str(self.item)

    def __repr__(self):
        return f"NamedItem({self.name!r}, {self.item!r})"

    def visit(self, rules: Dict[str, Rule]) -> bool:
        self.nullable = self.item.visit(rules)
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

    def add_var(self, gen: ParserGenerator, names: List[str]) -> Tuple[Optional[str], Optional[str]]:
        name, call = self.item.make_call(gen, cpython=True)
        type = None
        if name and name != 'cut':
            if name.endswith('_var'):
                rulename = name[:-4]
                rule = gen.rules.get(rulename)
                if rule is not None:
                    if rule.is_loop():
                        type = 'asdl_seq *'
                    else:
                        type = rule.type
                elif name.startswith('_loop'):
                    type = 'asdl_seq *'
            if self.name:
                name = self.name
            name = dedupe(name, names)
        return name, type

    def cgen_item(self, gen: ParserGenerator, names: List[str]):
        name, call = self.make_call(gen, cpython=True)
        if not name:
            gen.print(call)
        else:
            if name != 'cut':
                name = dedupe(name, names)
            gen.print(f"({name} = {call})")

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
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

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
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

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
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

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
        name, call = self.node.make_call(gen, cpython)
        if cpython:
            return "opt_var", f"{call}, 1"  # Using comma operator!
        else:
            return "opt", f"{call},"  # Note trailing comma!

    def visit(self, rules: Dict[str, Rule]) -> bool:
        return True

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat:
    """Shared base class for x* and x+."""

    def __init__(self, node: Plain):
        self.node = node
        self.memo: Optional[str] = None

    def visit(self, rules: Dict[str, Rule]) -> bool:
        raise NotImplementedError

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
        raise NotImplementedError

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat0(Repeat):
    def __str__(self):
        return f"({self.node})*"

    def __repr__(self):
        return f"Repeat0({self.node!r})"

    def visit(self, rules: Dict[str, Rule]) -> bool:
        return True

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
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

    def visit(self, rules: Dict[str, Rule]) -> bool:
        return False

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
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

    def visit(self, rules: Dict[str, Rule]) -> bool:
        return self.rhs.visit(rules)

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()

    def make_call(self, gen: ParserGenerator, cpython: bool) -> Tuple[Optional[str], str]:
        return self.rhs.make_call(gen, cpython)


Plain = Union[Leaf, Group]
Item = Union[Plain, Opt, Repeat, Lookahead]


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
            assert rule
            rules[rule.name] = rule
            mark = self.mark()
        if self.expect('ENDMARKER'):
            return rules
        return None

    @memoize
    def rule(self) -> Optional[Rule]:
        """
        rule: NAME [ '[' NAME ['*'] ']' ] ':' alternatives NEWLINE
        """
        mark = self.mark()
        if ((name := self.name()) and
                self.expect(':') and
                (alts := self.alternatives()) and
                self.expect('NEWLINE')):
            assert name
            return Rule(name.string, None, alts)
        self.reset(mark)
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
                self.expect('[') and
                (type := self.name()) and
                self.expect('*') and
                self.expect(']') and
                self.expect(':') and
                (alts := self.alternatives()) and
                self.expect('NEWLINE')):
            assert name
            return Rule(name.string, type.string + '*', alts)
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
            assert name
            assert item
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
    def lookahead(self) -> Optional[Lookahead]:
        """
        lookahead: ('&' | '!') atom
        """
        mark = self.mark()
        if (lookahead := (self.expect('&') or self.expect('!'))) and (atom := self.atom()):
            assert lookahead
            assert atom
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
            assert atom
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
            assert alts
            return Group(alts)
        self.reset(mark)
        if name := self.name():
            assert name
            return NameLeaf(name.string)
        if string := self.string():
            assert string
            return StringLeaf(string.string)
        return None

