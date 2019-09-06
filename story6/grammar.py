"""Parser for the grammar file."""

from ast import literal_eval

from token import COMMENT, DEDENT, ENDMARKER, INDENT, NAME, NEWLINE, NL, NUMBER, STRING

from story6.parser import Parser


class Grammar:

    def __init__(self, rules, metas):
        self.rules = rules
        self.rules_dict = {rule.name: rule for rule in rules}
        self.metas = metas
        self.metas_dict = dict(metas)

    def __repr__(self):
        lines = ["Grammar(["]
        for rule in self.rules:
            lines.append(f"    {rule!r},")
        if self.metas:
            lines.append("], [")
            for meta in self.metas:
                lines.append(f"    {meta!r}",)
            lines.append("])")
        else:
            lines.append("], [])")
        return "\n".join(lines)

    def __str__(self):
        lines = []
        for key, value in self.metas:
            if value is None:
                lines.append(f"@{key}")
            elif value.isalnum():
                lines.append(f"@{key} {value}")
            else:
                lines.append(f"@{key} {value!r}")
        for rule in self.rules:
            lines.append(f"{rule}")
        return "\n".join(lines)


class Rule:

    def __init__(self, name, alts):
        self.name = name
        self.alts = alts

    def __repr__(self):
        return f"Rule({self.name!r}, {self.alts})"

    def __str__(self):
        lines = [f"{self.name}:"]
        for alt in self.alts:
            lines.append(f"    | {alt}")
        return "\n".join(lines)

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return NotImplemented
        return self.name == other.name and self.alts == other.alts


class Alt:

    def __init__(self, items, action=None):
        self.items = items
        self.action = action

    def __repr__(self):
        if self.action:
            return f"Alt({self.items!r}, {self.action!r})"
        else:
            return f"Alt({self.items!r})"

    def __str__(self):
        items = " ".join(str(item) for item in self.items)
        if self.action:
            return f"{items} {{ {self.action} }}"
        else:
            return items

    def __eq__(self, other):
        if not isinstance(other, Alt):
            return NotImplemented
        return self.items == other.items and self.action == other.action


class NamedItem:

    def __init__(self, name, item):
        self.name = name
        self.item = item

    def __repr__(self):
        return f"NamedItem({self.name!r}, {self.item!r})"

    def __str__(self):
        return f"{self.name}={self.item}"

    def __eq__(self, other):
        if not isinstance(other, NamedItem):
            return NotImplemented
        return self.name == other.name and self.item == other.item


class Maybe:
    def __init__(self, item):
        self.item = item

    def __repr__(self):
        return f"Maybe({self.item!r}"

    def __str__(self):
        return f"[{self.item}]"

    def __eq__(self, other):
        if not isinstance(other, Maybe):
            return NotImplemented
        return self.item == other.item


# This class is no longer used (except as a backup).
# The new grammar parser is in grammarparser.py.
class GrammarParser(Parser):

    def start(self):
        pos = self.mark()
        if (grammar := self.grammar()) and self.expect(ENDMARKER):
            return grammar
        self.reset(pos)
        return None

    def grammar(self):
        rules = []
        metas = []
        pos = self.mark()
        while True:
            if rule := self.rule():
                rules.append(rule)
            elif meta := self.meta():
                metas.append(meta)
            elif self.expect(NL) or self.expect(COMMENT):
                continue
            else:
                return Grammar(rules, metas)
        self.reset(pos)
        return None

    def meta(self):
        pos = self.mark()
        if self.expect("@") and (name := self.expect(NAME)):
            apos = self.mark()
            if self.expect(NEWLINE):
                return (name.string, None)
            self.reset(apos)
            if (string := self.expect(STRING)) and self.expect(NEWLINE):
                return (name.string, literal_eval(string.string))
            self.reset(apos)
            if (string := self.expect(NAME)) and self.expect(NEWLINE):
                return (name.string, string.string)
            self.reset(apos)
            if (string := self.expect(NUMBER)) and self.expect(NEWLINE):
                return (name.string, literal_eval(string.string))
        self.reset(pos)
        return None

    def rule(self):
        pos = self.mark()
        if (name := self.expect(NAME)) and self.expect(":"):
            if alts := self.alts_newline():
                pass
            elif self.expect(NEWLINE):
                alts = []
            else:
                self.reset(pos)
                return None
            if alts1 := self.indented_alts():
                alts.extend(alts1)
            if alts:
                return Rule(name.string, alts)
        self.reset(pos)
        return None

    def indented_alts(self):
        pos = self.mark()
        if self.expect(INDENT):
            alts = []
            while True:
                if alts1 := self.bar_alts_newline():
                    alts.extend(alts1)
                elif self.expect(NL) or self.expect(COMMENT):
                    pass
                else:
                    break
            if self.expect(DEDENT):
                return alts
        self.reset(pos)
        return None

    def bar_alts_newline(self):
        pos = self.mark()
        if self.expect("|") and (alts := self.alts_newline()):
            return alts
        self.reset(pos)
        return None

    def alts_newline(self):
        pos = self.mark()
        if (alts := self.alts()) and self.expect(NEWLINE):
            return alts
        self.reset(pos)
        return None

    def alts(self):
        pos = self.mark()
        if alt := self.alternative():
            alts = [alt]
            while alt := self.bar_alt():
                alts.append(alt)
            return alts
        self.reset(pos)
        return None

    def bar_alt(self):
        pos = self.mark()
        if self.expect("|") and (alt := self.alternative()):
            return alt
        self.reset(pos)
        return None

    def alternative(self):
        items = []
        while item := self.item():
            items.append(item)
        if not items:
            return None
        # Look for {...}
        action = None
        pos = self.mark()
        if self.expect("{"):
            # Collect arbitrary tokens until "}" found, skipping matching {...} pairs.
            action_tokens = []
            level = 0
            while True:
                token = self.tokenizer.get_token().string
                if token == "{":
                    level += 1
                elif token == "}":
                    level -= 1
                    if level < 0:
                        break
                action_tokens.append(token)
            action = " ".join(action_tokens)
        return Alt(items, action)

    def item(self):
        if name := self.expect(NAME):
            return name.string
        if string := self.expect(STRING):
            return string.string
        return None
