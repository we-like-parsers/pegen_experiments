"""Quick and dirty code generator."""

from story2.grammar import Rule

HEADER = """\
# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story2.memo import memoize
from story2.node import Node
from story2.parser import Parser
"""

import sys

p = print  # Shorthand


def generate(rules, stream=None):
    if stream:
        sys.stdout = stream
    p(HEADER)
    generate_parser_class(rules)


def generate_parser_class(rules):
    p(f"class ToyParser(Parser):")
    for rule in rules:
        p()
        p(f"    @memoize")
        p(f"    def {rule.name}(self):")
        p(f"        pos = self.mark()")
        for alt in rule.alts:
            items = []
            p(f"        if (True")
            for item in alt:
                if item[0] in ('"', "'"):
                    p(f"            and self.expect({item})")
                else:
                    var = item.lower()
                    if var in items:
                        var += str(len(items))
                    items.append(var)
                    if item.isupper():
                        p("            " +
                          f"and ({var} := self.expect({item}))")
                    else:
                        p(f"            " +
                          f"and ({var} := self.{item}())")
            p(f"        ):")
            p(f"            " +
              f"return Node({rule.name!r}, [{', '.join(items)}])")
            p(f"        self.reset(pos)")
        p(f"        return None")
