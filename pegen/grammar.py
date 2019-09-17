from __future__ import annotations  # Requires Python 3.7 or later

from abc import abstractmethod
from typing import AbstractSet, Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, TYPE_CHECKING, TypeVar, Union

from pegen.parser import memoize, Parser

if TYPE_CHECKING:
    from pegen.parser_generator import ParserGenerator


class GrammarError(Exception):
    pass


class GrammarVisitor:

    def visit(self, node, *args, **kwargs):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def visit_TokenInfo(self):
        pass

    def generic_visit(self, node, *args, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        for value in node:
            if isinstance(value, list):
                for item in value:
                    self.visit(item, *args, **kwargs)
            else:
                self.visit(value, *args, **kwargs)


class Grammar:

    def __init__(self, rules):
        self.rules = {rule.name: rule for rule in rules}

    def __str__(self):
        return "\n".join(f"{name}: {rule}" for name, rule in self.rules.items())

    def __repr__(self):
        return f"Grammar({self.rules!r})"

    def __iter__(self):
        yield from self.rules.values()


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

    def __iter__(self):
        yield self.rhs

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        if self.visited:
            # A left-recursive rule is considered non-nullable.
            return False
        self.visited = True
        self.nullable = self.rhs.nullable_visit(rules)
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


class Leaf:

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value

    def __iter__(self):
        return
        yield

    @abstractmethod
    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def initial_names(self) -> AbstractSet[str]:
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

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        if self.value in rules:
            return rules[self.value].nullable_visit(rules)
        # Token or unknown; never empty.
        return False

    def initial_names(self) -> AbstractSet[str]:
        return {self.value}


class StringLeaf(Leaf):
    """The value is a string literal, including quotes."""

    def __repr__(self):
        return f"StringLeaf({self.value!r})"

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        # The string token '' is considered empty.
        return not self.value

    def initial_names(self) -> AbstractSet[str]:
        return set()


class Rhs:

    def __init__(self, alts: List[Alt]):
        self.alts = alts
        self.memo: Optional[Tuple[Optional[str], str]] = None

    def __str__(self):
        return " | ".join(str(alt) for alt in self.alts)

    def __repr__(self):
        return f"Rhs({self.alts!r})"

    def __iter__(self):
        yield self.alts

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        for alt in self.alts:
            if alt.nullable_visit(rules):
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


class Alt:

    def __init__(self, items: List[NamedItem], *, icut: int = -1, action: Optional[str] = None):
        self.items = items
        self.icut = icut
        self.action = action

    def __str__(self):
        core = " ".join(str(item) for item in self.items)
        if self.action:
            return f"{core} {{ {self.action} }}"
        else:
            return core

    def __repr__(self):
        args = [repr(self.items)]
        if self.icut >= 0:
            args.append(f"icut={self.icut}")
        if self.action:
            args.append(f"action={self.action!r}")
        return f"Alt({', '.join(args)})"

    def __iter__(self):
        yield self.items

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        for item in self.items:
            if not item.nullable_visit(rules):
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

    def __iter__(self):
        yield self.item

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        self.nullable = self.item.nullable_visit(rules)
        return self.nullable

    def initial_names(self) -> AbstractSet[str]:
        return self.item.initial_names()

    def collect_todo(self, gen: ParserGenerator) -> None:
        gen.callmakervisitor.visit(self.item)


class Lookahead:

    def __init__(self, node: Plain, sign: str):
        self.node = node
        self.sign = sign

    def __str__(self):
        return f"{self.sign}{self.node}"

    def __iter__(self):
        yield self.node

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        return True

    def initial_names(self) -> AbstractSet[str]:
        return set()


class PositiveLookahead(Lookahead):

    def __init__(self, node: Plain):
        super().__init__(node, '&')

    def __repr__(self):
        return f"PositiveLookahead({self.node!r})"


class NegativeLookahead(Lookahead):

    def __init__(self, node: Plain):
        super().__init__(node, '!')

    def __repr__(self):
        return f"NegativeLookahead({self.node!r})"


class Opt:

    def __init__(self, node: Item):
        self.node = node

    def __str__(self):
        return f"{self.node}?"

    def __repr__(self):
        return f"Opt({self.node!r})"

    def __iter__(self):
        yield self.node

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        return True

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat:
    """Shared base class for x* and x+."""

    def __init__(self, node: Plain):
        self.node = node
        self.memo: Optional[Tuple[Optional[str], str]] = None

    @abstractmethod
    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        raise NotImplementedError

    def __iter__(self):
        yield self.node

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat0(Repeat):

    def __str__(self):
        return f"({self.node})*"

    def __repr__(self):
        return f"Repeat0({self.node!r})"

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        return True


class Repeat1(Repeat):

    def __str__(self):
        return f"({self.node})+"

    def __repr__(self):
        return f"Repeat1({self.node!r})"

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        return False


class Group:

    def __init__(self, rhs: Rhs):
        self.rhs = rhs

    def __str__(self):
        return f"({self.rhs})"

    def __repr__(self):
        return f"Group({self.rhs!r})"

    def __iter__(self):
        yield self.rhs

    def nullable_visit(self, rules: Dict[str, Rule]) -> bool:
        return self.rhs.nullable_visit(rules)

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()


class Cut:

    def __init__(self):
        pass

    def __repr__(self):
        return f"Cut()"

    def __str__(self):
        return f"~"

    def __eq__(self, other):
        if not isinstance(other, Cut):
            return NotImplemented
        return True


Plain = Union[Leaf, Group]
Item = Union[Plain, Opt, Repeat, Lookahead, Rhs]
