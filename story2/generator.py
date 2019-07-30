"""Quick and dirty code generator."""

from story2.grammar import Rule

def is_string(s):
    return s[0] in ('"', "'") and s[-1] == s[0]

def is_lower(s):
    return s.islower()

def is_upper(s):
    return s.isupper()

def generate(rules):
    print(f"# This is @generated code; do not edit!")
    print()
    print(f"from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER")
    print()
    print(f"from story2.parser import Parser")
    print(f"from story2.node import Node")
    print()
    print(f"class ToyParser(Parser):")
    for rule in rules:
        print()
        print(f"  def {rule.name}(self):")
        print(f"    pos = self.mark()")
        for alt in rule.alts:
            items = []
            print(f"    if (True")
            for item in alt:
                if is_string(item):
                    print(f"        and self.expect({item})")
                else:
                    var = item.lower()
                    if var in items:
                        var += str(len(items))
                    items.append(var)
                    if is_lower(item):
                        print(f"        and ({var} := self.{item}())")
                    elif is_upper(item):
                        print(f"        and ({var} := self.expect({item}))")
                    else:
                        assert False, f"What kind of item is {item}?"
            print(f"    ):")
            print(f"        return Node({rule.name!r}, [{', '.join(items)}])")
            print(f"    self.reset(pos)")
        print(f"    return None")
