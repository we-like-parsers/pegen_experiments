"""Simple code generator."""

from contextlib import contextmanager

from story6.grammar import Rule

HEADER = """\
# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story6.memo import memoize, memoize_left_rec
from story6.node import Node
from story6.parser import Parser
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

    def is_left_rec(self, rule):
        # TODO: Indirect left recursion (hidden behind possibly-empty
        # items) and mutual left recursion (recursion involving
        # multiple rules).  Indirect recursion only becomes important
        # once we support PEG features like optional or repeated
        # items.  Mutual left recursion is currently an undetected
        # grammar bug -- don't do this!  (A full implementation is in
        # the ../pegen/parser_generator.py module.)
        for alt in rule.alts:
            if alt.items[0] == rule.name:
                return True
        return False

    def gen_rule(self, rule):
        if self.is_left_rec(rule):
            self.put(f"@memoize_left_rec")
            leftrec = "'*' + "
        else:
            self.put(f"@memoize")
            leftrec = ""
        self.put(f"def {rule.name}(self):")
        with self.indent():
            alts = [alt.items for alt in rule.alts]
            self.put(f"self.show_rule({leftrec}{rule.name!r}, {alts!r})")
            self.put(f"pos = self.mark()")
            for i, alt in enumerate(rule.alts):
                self.gen_alt(alt, rule, i)
            self.put(f"self.show_index(0, 0, 0)")
            self.put(f"return None")

    def gen_alt(self, alt, rule, alt_index):
        items = []
        self.put(f"if (True")
        with self.indent():
            for i, item in enumerate(alt.items):
                self.gen_item(item, items, alt_index, i)
        self.put(f"):")
        with self.indent():
            self.put(f"self.show_index({alt_index}, 0, {len(alt.items)})")
            if alt.action:
                self.put(f"return {alt.action}")
            else:
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


def generate(rules, classname, stream=None):
    gen = Generator(stream)
    gen.put(HEADER)
    gen.put(f"class {classname}(Parser):")
    for rule in rules:
        gen.put()
        with gen.indent():
            gen.gen_rule(rule)
