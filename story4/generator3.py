"""Simple code generator."""

from contextlib import contextmanager

from story4.grammar import Rule

HEADER = """\
# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story4.memo import memoize
from story4.node import Node
from story4.parser import Parser
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
            self.put(f"self.show_rule({rule.name!r}, {rule.alts!r})")
            self.put(f"pos = self.mark()")
            for i, alt in enumerate(rule.alts):
                self.gen_alt(alt, rule, i)
            self.put(f"self.show_index(0, 0, 0)")
            self.put(f"return None")

    def gen_alt(self, alt, rule, alt_index):
        items = []
        self.put(f"if (True")
        with self.indent():
            for i, item in enumerate(alt):
                self.gen_item(item, items, alt_index, i)
        self.put(f"):")
        with self.indent():
            self.put(f"self.show_index({alt_index}, 0, {len(alt)})")
            self.put(f"return Node({rule.name!r}, [{', '.join(items)}])")
        self.put(f"self.reset(pos)")

    def gen_item(self, item, items, alt_index, item_index):
        self.put(f"and self.show_index({alt_index}, {item_index})")
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
