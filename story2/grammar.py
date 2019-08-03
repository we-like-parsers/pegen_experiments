"""Parser for the grammar file."""

from token import NAME, NEWLINE, STRING, ENDMARKER

from story2.parser import Parser

class Rule:

    def __init__(self, name, alts):
        self.name = name
        self.alts = alts

    def __repr__(self):
        return f"Rule({self.name!r}, {self.alts})"

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return NotImplemented
        return self.name == other.name and self.alts == other.alts


class GrammarParser(Parser):

    def grammar(self):
        pos = self.mark()
        if rule := self.rule():
            rules = [rule]
            while rule := self.rule():
                rules.append(rule)
            if self.expect(ENDMARKER):
                return rules
        self.reset(pos)
        return None

    def rule(self):
        pos = self.mark()
        if name := self.expect(NAME):
            if self.expect(":"):
                if alt := self.alternative():
                    alts = [alt]
                    apos = self.mark()
                    while (self.expect("|")
                           and (alt := self.alternative())):
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
