"""Simple code generator."""

from contextlib import contextmanager
import token
import sys

from story7.grammar import Grammar, Rule, Alt, NamedItem, Lookahead, Cut, Maybe, Loop

HEADER = """\
# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story7.memo import memoize, memoize_left_rec, no_memoize
from story7.node import Node
from story7.parser import Parser
"""


def flatten(items):
    return [str(it.item) if isinstance(it, NamedItem) else str(it) for it in items]


def has_cut(alt):
    return any(isinstance(item, Cut) for item in alt.items)


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
        # TODO: Implement this correctly.  (Full implementation is in
        # the ../pegen/parser_generator.py module.)
        for alt in rule.alts:
            for item in alt.items:
                if isinstance(item, NamedItem):
                    item = item.item
                orig = item
                if isinstance(item, (Maybe, Loop, Lookahead)):
                    item = item.item
                if item == rule.name:
                    return True
                if isinstance(orig, (Maybe, Lookahead)):
                    continue
                if isinstance(orig, Loop) and not orig.nonempty:
                    continue
                break
        return False

    def gen_rule(self, rule, memoize):
        if self.is_left_rec(rule):
            self.put(f"@memoize_left_rec")
            leftrec = "'*' + "
        else:
            if memoize:
                self.put(f"@memoize")
            else:
                self.put(f"@no_memoize")
            leftrec = ""
        self.put(f"def {rule.name}(self):")
        with self.indent():
            alts = [flatten(alt.items) for alt in rule.alts]
            self.put(f"self.show_rule({leftrec}{rule.name!r}, {alts!r})")
            self.put(f"pos = self.mark()")
            if any(has_cut(alt) for alt in rule.alts):
                self.put(f"cut = False")
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
                self.put(f"retval = {alt.action}")
                self.put(f"if retval is not None:")
                with self.indent():
                    self.put(f"return retval")
            else:
                self.put(f"return Node({rule.name!r}, [{', '.join(items)}])")
        self.put(f"self.reset(pos)")
        if has_cut(alt):
            self.put(f"if cut:")
            with self.indent():
                self.put(f"self.show_index(0, 0, 0)")
                self.put(f"return None")

    def gen_item(self, item, items, alt_index, item_index):
        self.put(f"and self.show_index({alt_index}, {item_index})")

        if isinstance(item, Cut):
            var = "cut"
            phrase = "True"
        else:
            # This is messy, because it depends on properties of the grammar,
            # e.g. a lookahead or cut cannot be named.
            var = None
            if isinstance(item, NamedItem):
                var, item = item.name, item.item

            orig = item
            if isinstance(item, (Lookahead, Loop, Maybe)):
                item = item.item
            assert isinstance(item, str), repr(item)

            if item[0] in ('"', "'") or item.isupper():
                func = "self.expect"
                arg = item
            else:
                func = f"self.{item}"
                arg = ""

            if arg:
                comma_arg = f", {arg}"
            else:
                comma_arg = ""

            if isinstance(orig, Lookahead):
                var = None
                phrase = f"self.lookahead({orig.positive}, {func}{comma_arg})"
            else:
                if var is None and item[0] not in ('"', "'"):
                    if item.isupper():
                        var = item.lower()
                    else:
                        var = item
                    if var in items:
                        var += str(len(items))

                if isinstance(orig, Loop):
                    phrase = f"self.loop({orig.nonempty}, {func}{comma_arg})"
                else:
                    phrase = f"{func}({arg})"

                if var is not None:
                    phrase = f"({var} := {phrase})"
                    items.append(var)

                phrase = f"{phrase} is not None"

                if isinstance(orig, Maybe):
                    phrase = f"({phrase} or True)"

        self.put(f"and {phrase}")


def check(grammar):
    errors = 0
    for rule in grammar.rules:
        for alt in rule.alts:
            for item in alt.items:
                if isinstance(item, NamedItem):
                    item = item.item
                elif isinstance(item, Lookahead):
                    item = item.item
                elif isinstance(item, Cut):
                    continue
                if isinstance(item, Maybe):
                    item = item.item
                elif isinstance(item, Loop):
                    item = item.item
                if item.isupper():
                    ival = getattr(token, item, None)
                    if not isinstance(ival, int) or not 0 <= ival < token.N_TOKENS:
                        print(f"Error: Uppercase item {item} occurring in rule {rule.name} is not a valid token",
                              file=sys.stderr)
                        errors += 1
                elif item[0] in ('"', "'"):
                    pass
                elif item not in grammar.rules_dict:
                    print(f"Error: Item {item} occurring in rule {rule.name} does not refer to a valid rule",
                          file=sys.stderr)
                    errors += 1
    return errors


def generate(grammar, classname, stream=None):
    metas = grammar.metas_dict
    memoize = "no_memoize" not in metas
    gen = Generator(stream)
    header = metas.get("header", HEADER)
    subheader = metas.get("subheader", "")
    gen.put(header)
    if subheader:
        gen.put(subheader)
    gen.put(f"class {classname}(Parser):")
    for rule in grammar.rules:
        gen.put()
        with gen.indent():
            gen.gen_rule(rule, memoize)
    trailer = metas.get("trailer")
    if trailer:
        gen.put(trailer)
