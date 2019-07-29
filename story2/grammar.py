"""Parser for the grammar file."""

from token import NAME, NEWLINE, STRING

from story2.parser import Parser

class Rule:
    def __init__(self, name, alts):
        self.name = name
        self.alts = alts


class GrammarParser(Parser):

    def start(self):
        if rule := self.rule():
            rules = [rule]
            while rule := self.rule():
                rules.append(rule)
            return rules
        return None

    def rule(self):
        pos = self.mark()
        if name := self.expect(NAME):
            if self.expect(":"):
                if alt := self.alternative():
                    alts = [alt]
                    apos = self.mark()
                    while self.expect("|") and (alt := self.alternative()):
                        alts.append(alt)
                        apos = self.mark()
                    self.reset(apos)
                    if self.expect(NEWLINE):
                        return Rule(name.string, alts)
        self.reset(pos)
        return None

    def alternative(self):
        items = []
        while item := self.item():
            items.append(item)
        return items

    def item(self):
        if name := self.expect(NAME):
            return name.string
        if string := self.expect(STRING):
            return string.string
        return None
