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

    def __call__(self, *args):
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
        

def generate(rules, stream=None):
    gen = Generator(stream)
    gen(HEADER)
    gen(f"class ToyParser(Parser):")
    for rule in rules:
        gen()
        with gen.indent():
            gen(f"@memoize")
            gen(f"def {rule.name}(self):")
            with gen.indent():
                gen(f"pos = self.mark()")
                for alt in rule.alts:
                    items = []
                    gen(f"if (True")
                    with gen.indent():
                        for item in alt:
                            if item[0] in ('"', "'"):
                                gen(f"and self.expect({item})")
                            else:
                                var = item.lower()
                                if var in items:
                                    var += str(len(items))
                                items.append(var)
                                if item.isupper():
                                    gen(f"and ({var} := self.expect({item}))")
                                else:
                                    gen(f"and ({var} := self.{item}())")
                    gen(f"):")
                    with gen.indent():
                        gen(f"return Node({rule.name!r}, [{', '.join(items)}])")
                    gen(f"self.reset(pos)")
                gen(f"return None")
