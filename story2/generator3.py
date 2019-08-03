"""Simple code generator."""

from contextlib import contextmanager

from story2.grammar import Rule

HEADER = """\
# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story2.memo import memoize
from story2.node import Node
from story2.parser import Parser
"""


class Generator:

    def __init__(self, stream=None):
        self.stream = stream  # If None, write to sys.stdout.
        self.indentation = ""

    def put(self, *args):
        # Note: print(..., file=None) prints to sys.stdout.
        print(end=self.indentation, file=self.stream)
        print(*args, file=self.stream)

    @contextmanager
    def indent(self):
        save = self.indentation
        try:
            self.indentation += "    "
            yield
        finally:
            self.indentation = save

    def gen_rule(self, rule):
        self.put(f"@memoize")
        self.put(f"def {rule.name}(self):")
        with self.indent():
            self.put(f"pos = self.mark()")
            for alt in rule.alts:
                self.gen_alt(alt, rule)
            self.put(f"return None")

    def gen_alt(self, alt, rule):
        items = []
        self.put(f"if (True")
        with self.indent():
            for item in alt:
                self.gen_item(item, items)
        self.put(f"):")
        with self.indent():
            self.put(f"return Node({rule.name!r}, [{', '.join(items)}])")
        self.put(f"self.reset(pos)")

    def gen_item(self, item, items):
        if item[0] in ('"', "'"):
            self.put(f"and self.expect({item})")
        else:
            var = item.lower()
            if var in items:
                var += str(len(items))
            items.append(var)
            if item.isupper():
                self.put(f"and ({var} := self.expect({item}))")
            else:
                self.put(f"and ({var} := self.{item}())")


def generate(rules, stream=None):
    gen = Generator(stream)
    gen.put(HEADER)
    gen.put(f"class ToyParser(Parser):")
    for rule in rules:
        gen.put()
        with gen.indent():
            gen.gen_rule(rule)
