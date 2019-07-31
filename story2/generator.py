"""Quick and dirty code generator."""

from story2.grammar import Rule

HEADER = """\
# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story2.memo import memoize
from story2.node import Node
from story2.parser import Parser
"""

def generate(rules):
    print(HEADER)
    print(f"class ToyParser(Parser):")
    for rule in rules:
        print()
        print(f"    @memoize")
        print(f"    def {rule.name}(self):")
        print(f"        pos = self.mark()")
        for alt in rule.alts:
            items = []
            print(f"        if (True")
            for item in alt:
                if item[0] in ('"', "'"):
                    print(f"            and self.expect({item})")
                else:
                    var = item.lower()
                    if var in items:
                        var += str(len(items))
                    items.append(var)
                    if item.isupper():
                        print(f"            and ({var} := self.expect({item}))")
                    else:
                        print(f"            and ({var} := self.{item}())")
            print(f"        ):")
            print(f"            return Node({rule.name!r}, [{', '.join(items)}])")
            print(f"        self.reset(pos)")
        print(f"        return None")
