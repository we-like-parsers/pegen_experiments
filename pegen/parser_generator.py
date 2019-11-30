import contextlib
import token
from abc import abstractmethod

from typing import AbstractSet, Dict, IO, Iterator, List, Optional, Set, Text, Tuple

from pegen import sccutils
from pegen.grammar import (
    Grammar,
    Rule,
    Rhs,
    Alt,
    NamedItem,
    Plain,
    NameLeaf,
    StringLeaf,
    Gather,
)
from pegen.grammar import GrammarError, GrammarVisitor


class RuleCheckingVisitor(GrammarVisitor):
    def __init__(self, rules: Dict[str, Rule]):
        self.rules = rules

    def visit_NameLeaf(self, node: NameLeaf) -> None:
        if node.value not in self.rules and node.value not in token.tok_name.values():
            # TODO: Add line/col info to (leaf) nodes
            raise GrammarError(f"Dangling reference to rule {node.value!r}")


class ParserGenerator:

    callmakervisitor: GrammarVisitor

    def __init__(self, grammar: Grammar, file: Optional[IO[Text]]):
        self.grammar = grammar
        self.rules = grammar.rules
        if "start" not in self.rules:
            raise GrammarError("Grammar must have a 'start' rule")
        checker = RuleCheckingVisitor(self.rules)
        for rule in self.rules.values():
            checker.visit(rule)
        self.file = file
        self.level = 0
        compute_nullables(self.rules)
        self.first_graph, self.first_sccs = compute_left_recursives(self.rules)
        self.todo = self.rules.copy()  # Rules to generate
        self.counter = 0  # For name_rule()/name_loop()

    @abstractmethod
    def generate(self, filename: str) -> None:
        raise NotImplementedError

    @contextlib.contextmanager
    def indent(self) -> Iterator[None]:
        self.level += 1
        try:
            yield
        finally:
            self.level -= 1

    def print(self, *args: object) -> None:
        if not args:
            print(file=self.file)
        else:
            print("    " * self.level, end="", file=self.file)
            print(*args, file=self.file)

    def printblock(self, lines: str) -> None:
        for line in lines.splitlines():
            self.print(line)

    def collect_todo(self) -> None:
        done: Set[str] = set()
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
        name = f"_tmp_{self.counter}"  # TODO: Pick a nicer name.
        self.todo[name] = Rule(name, None, rhs)
        return name

    def name_loop(self, node: Plain, is_repeat1: bool) -> str:
        self.counter += 1
        if is_repeat1:
            prefix = "_loop1_"
        else:
            prefix = "_loop0_"
        name = f"{prefix}{self.counter}"  # TODO: It's ugly to signal via the name.
        self.todo[name] = Rule(name, None, Rhs([Alt([NamedItem(None, node)])]))
        return name

    def name_gather(self, node: Gather) -> str:
        self.counter += 1
        name = f"_gather_{self.counter}"
        self.counter += 1
        extra_function_name = f"_loop0_{self.counter}"
        extra_function_alt = Alt(
            [NamedItem(None, node.separator), NamedItem("elem", node.node),], action="elem",
        )
        self.todo[extra_function_name] = Rule(
            extra_function_name, None, Rhs([extra_function_alt]),
        )
        alt = Alt(
            [NamedItem("elem", node.node), NamedItem("seq", NameLeaf(extra_function_name)),],
        )
        self.todo[name] = Rule(name, None, Rhs([alt]),)
        return name


def dedupe(name: str, names: List[str]) -> str:
    origname = name
    counter = 0
    while name in names:
        counter += 1
        name = f"{origname}_{counter}"
    names.append(name)
    return name


def compute_nullables(rules: Dict[str, Rule]) -> None:
    """Compute which rules in a grammar are nullable.

    Thanks to TatSu (tatsu/leftrec.py) for inspiration.
    """
    for rule in rules.values():
        rule.nullable_visit(rules)


def compute_left_recursives(
    rules: Dict[str, Rule]
) -> Tuple[Dict[str, AbstractSet[str]], List[AbstractSet[str]]]:
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
                    leaders -= scc - set(cycle)
                    if not leaders:
                        raise ValueError(
                            f"SCC {scc} has no leadership candidate (no element is included in all cycles)"
                        )
            ## print("Leaders:", leaders)
            leader = min(leaders)  # Pick an arbitrary leader from the candidates.
            rules[leader].leader = True
        else:
            name = min(scc)  # The only element.
            if name in graph[name]:
                rules[name].left_recursive = True
                rules[name].leader = True
    return graph, sccs


def make_first_graph(rules: Dict[str, Rule]) -> Dict[str, AbstractSet[str]]:
    """Compute the graph of left-invocations.

    There's an edge from A to B if A may invoke B at its initial
    position.

    Note that this requires the nullable flags to have been computed.
    """
    graph = {}
    vertices: Set[str] = set()
    for rulename, rhs in rules.items():
        graph[rulename] = names = rhs.initial_names()
        vertices |= names
    for vertex in vertices:
        graph.setdefault(vertex, set())
    return graph
