# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story6.memo import memoize, memoize_left_rec
from story6.node import Node
from story6.parser import Parser


from ast import literal_eval
from token import DEDENT, INDENT, OP

from story6.grammar import Grammar, Rule, Alt, NamedItem, Lookahead, Maybe, Loop, Cut

BaseParser = Parser

class Parser(BaseParser):

    def __init__(self, tokenizer):
        super().__init__(tokenizer)
        self.extra_rules = []

    def synthetic_rule(self, alts):
        name = f"_synthetic_rule_{len(self.extra_rules)}"
        rule = Rule(name, alts)
        self.extra_rules.append(rule)
        return rule

class GrammarParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['grammar', 'ENDMARKER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (grammar := self.grammar()) is not None
            and self.show_index(0, 1)
            and (endmarker := self.expect(ENDMARKER)) is not None
        ):
            self.show_index(0, 0, 2)
            retval = grammar
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def grammar(self):
        self.show_rule('grammar', [['metas', 'rules'], ['rules']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (metas := self.metas()) is not None
            and self.show_index(0, 1)
            and (rules := self.rules()) is not None
        ):
            self.show_index(0, 0, 2)
            retval = Grammar ( rules + self . extra_rules , metas )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (rules := self.rules()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = Grammar ( rules + self . extra_rules , [ ] )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def metas(self):
        self.show_rule('metas', [['meta', 'metas'], ['meta']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (meta := self.meta()) is not None
            and self.show_index(0, 1)
            and (metas := self.metas()) is not None
        ):
            self.show_index(0, 0, 2)
            retval = [ meta ] + metas
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (meta := self.meta()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = [ meta ]
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def meta(self):
        self.show_rule('meta', [['"@"', 'NAME', 'NEWLINE'], ['"@"', 'NAME', 'NAME', 'NEWLINE'], ['"@"', 'NAME', 'STRING', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and self.expect("@") is not None
            and self.show_index(0, 1)
            and (name := self.expect(NAME)) is not None
            and self.show_index(0, 2)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(0, 0, 3)
            retval = ( name . string , None )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and self.expect("@") is not None
            and self.show_index(1, 1)
            and (name := self.expect(NAME)) is not None
            and self.show_index(1, 2)
            and (name1 := self.expect(NAME)) is not None
            and self.show_index(1, 3)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(1, 0, 4)
            retval = ( name . string , name1 . string )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and self.expect("@") is not None
            and self.show_index(2, 1)
            and (name := self.expect(NAME)) is not None
            and self.show_index(2, 2)
            and (string := self.expect(STRING)) is not None
            and self.show_index(2, 3)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(2, 0, 4)
            retval = ( name . string , literal_eval ( string . string ) )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def rules(self):
        self.show_rule('rules', [['rule', 'rules'], ['rule']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (rule := self.rule()) is not None
            and self.show_index(0, 1)
            and (rules := self.rules()) is not None
        ):
            self.show_index(0, 0, 2)
            retval = [ rule ] + rules
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (rule := self.rule()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = [ rule ]
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def rule(self):
        self.show_rule('rule', [['NAME', '":"', 'alts', 'NEWLINE', 'INDENT', 'more_alts', 'DEDENT'], ['NAME', '":"', 'NEWLINE', 'INDENT', 'more_alts', 'DEDENT'], ['NAME', '":"', 'alts', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (name := self.expect(NAME)) is not None
            and self.show_index(0, 1)
            and self.expect(":") is not None
            and self.show_index(0, 2)
            and (alts := self.alts()) is not None
            and self.show_index(0, 3)
            and (newline := self.expect(NEWLINE)) is not None
            and self.show_index(0, 4)
            and (indent := self.expect(INDENT)) is not None
            and self.show_index(0, 5)
            and (more_alts := self.more_alts()) is not None
            and self.show_index(0, 6)
            and (dedent := self.expect(DEDENT)) is not None
        ):
            self.show_index(0, 0, 7)
            retval = Rule ( name . string , alts + more_alts )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (name := self.expect(NAME)) is not None
            and self.show_index(1, 1)
            and self.expect(":") is not None
            and self.show_index(1, 2)
            and (newline := self.expect(NEWLINE)) is not None
            and self.show_index(1, 3)
            and (indent := self.expect(INDENT)) is not None
            and self.show_index(1, 4)
            and (more_alts := self.more_alts()) is not None
            and self.show_index(1, 5)
            and (dedent := self.expect(DEDENT)) is not None
        ):
            self.show_index(1, 0, 6)
            retval = Rule ( name . string , more_alts )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (name := self.expect(NAME)) is not None
            and self.show_index(2, 1)
            and self.expect(":") is not None
            and self.show_index(2, 2)
            and (alts := self.alts()) is not None
            and self.show_index(2, 3)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(2, 0, 4)
            retval = Rule ( name . string , alts )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def more_alts(self):
        self.show_rule('more_alts', [['"|"', 'alts', 'NEWLINE', 'more_alts'], ['"|"', 'alts', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and self.expect("|") is not None
            and self.show_index(0, 1)
            and (alts := self.alts()) is not None
            and self.show_index(0, 2)
            and (newline := self.expect(NEWLINE)) is not None
            and self.show_index(0, 3)
            and (more_alts := self.more_alts()) is not None
        ):
            self.show_index(0, 0, 4)
            retval = alts + more_alts
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and self.expect("|") is not None
            and self.show_index(1, 1)
            and (alts := self.alts()) is not None
            and self.show_index(1, 2)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(1, 0, 3)
            retval = alts
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def alts(self):
        self.show_rule('alts', [['alt', '"|"', 'alts'], ['alt']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (alt := self.alt()) is not None
            and self.show_index(0, 1)
            and self.expect("|") is not None
            and self.show_index(0, 2)
            and (alts := self.alts()) is not None
        ):
            self.show_index(0, 0, 3)
            retval = [ alt ] + alts
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (alt := self.alt()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = [ alt ]
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def alt(self):
        self.show_rule('alt', [['items', 'action'], ['items']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (items := self.items()) is not None
            and self.show_index(0, 1)
            and (action := self.action()) is not None
        ):
            self.show_index(0, 0, 2)
            retval = Alt ( items , action )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (items := self.items()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = Alt ( items , None )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def items(self):
        self.show_rule('items', [['item', 'items'], ['item']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (item := self.item()) is not None
            and self.show_index(0, 1)
            and (items := self.items()) is not None
        ):
            self.show_index(0, 0, 2)
            retval = [ item ] + items
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (item := self.item()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = [ item ]
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def item(self):
        self.show_rule('item', [['NAME', "'='", 'molecule'], ['"&"', 'atom'], ['"!"', 'atom'], ['"~"'], ['molecule']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (name := self.expect(NAME)) is not None
            and self.show_index(0, 1)
            and self.expect('=') is not None
            and self.show_index(0, 2)
            and (molecule := self.molecule()) is not None
        ):
            self.show_index(0, 0, 3)
            retval = NamedItem ( name . string , molecule )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and self.expect("&") is not None
            and self.show_index(1, 1)
            and (atom := self.atom()) is not None
        ):
            self.show_index(1, 0, 2)
            retval = Lookahead ( atom )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and self.expect("!") is not None
            and self.show_index(2, 1)
            and (atom := self.atom()) is not None
        ):
            self.show_index(2, 0, 2)
            retval = Lookahead ( atom , False )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(3, 0)
            and self.expect("~") is not None
        ):
            self.show_index(3, 0, 1)
            retval = Cut ( )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(4, 0)
            and (molecule := self.molecule()) is not None
        ):
            self.show_index(4, 0, 1)
            retval = molecule
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def molecule(self):
        self.show_rule('molecule', [['atom', '"?"'], ['atom', '"*"'], ['atom', '"+"'], ['atom'], ['"["', 'atom', '"]"'], ['"["', 'alts', '"]"']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (atom := self.atom()) is not None
            and self.show_index(0, 1)
            and self.expect("?") is not None
        ):
            self.show_index(0, 0, 2)
            retval = Maybe ( atom )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (atom := self.atom()) is not None
            and self.show_index(1, 1)
            and self.expect("*") is not None
        ):
            self.show_index(1, 0, 2)
            retval = Loop ( atom )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (atom := self.atom()) is not None
            and self.show_index(2, 1)
            and self.expect("+") is not None
        ):
            self.show_index(2, 0, 2)
            retval = Loop ( atom , True )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(3, 0)
            and (atom := self.atom()) is not None
        ):
            self.show_index(3, 0, 1)
            retval = atom
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(4, 0)
            and self.expect("[") is not None
            and self.show_index(4, 1)
            and (atom := self.atom()) is not None
            and self.show_index(4, 2)
            and self.expect("]") is not None
        ):
            self.show_index(4, 0, 3)
            retval = Maybe ( atom )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(5, 0)
            and self.expect("[") is not None
            and self.show_index(5, 1)
            and (alts := self.alts()) is not None
            and self.show_index(5, 2)
            and self.expect("]") is not None
        ):
            self.show_index(5, 0, 3)
            retval = Maybe ( self . synthetic_rule ( alts ) . name )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def atom(self):
        self.show_rule('atom', [['NAME'], ['STRING'], ['"("', 'alts', '")"']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (name := self.expect(NAME)) is not None
        ):
            self.show_index(0, 0, 1)
            retval = name . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (string := self.expect(STRING)) is not None
        ):
            self.show_index(1, 0, 1)
            retval = string . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and self.expect("(") is not None
            and self.show_index(2, 1)
            and (alts := self.alts()) is not None
            and self.show_index(2, 2)
            and self.expect(")") is not None
        ):
            self.show_index(2, 0, 3)
            retval = self . synthetic_rule ( alts ) . name
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def action(self):
        self.show_rule('action', [['"{"', 'stuffs', '"}"']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and self.expect("{") is not None
            and self.show_index(0, 1)
            and (stuffs := self.stuffs()) is not None
            and self.show_index(0, 2)
            and self.expect("}") is not None
        ):
            self.show_index(0, 0, 3)
            retval = stuffs
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def stuffs(self):
        self.show_rule('stuffs', [['stuff', 'stuffs'], ['stuff']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (stuff := self.stuff()) is not None
            and self.show_index(0, 1)
            and (stuffs := self.stuffs()) is not None
        ):
            self.show_index(0, 0, 2)
            retval = stuff + " " + stuffs
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (stuff := self.stuff()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = stuff
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def stuff(self):
        self.show_rule('stuff', [['"{"', 'stuffs', '"}"'], ['NAME'], ['NUMBER'], ['STRING'], ['OP']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and self.expect("{") is not None
            and self.show_index(0, 1)
            and (stuffs := self.stuffs()) is not None
            and self.show_index(0, 2)
            and self.expect("}") is not None
        ):
            self.show_index(0, 0, 3)
            retval = "{" + stuffs + "}"
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (name := self.expect(NAME)) is not None
        ):
            self.show_index(1, 0, 1)
            retval = name . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (number := self.expect(NUMBER)) is not None
        ):
            self.show_index(2, 0, 1)
            retval = number . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(3, 0)
            and (string := self.expect(STRING)) is not None
        ):
            self.show_index(3, 0, 1)
            retval = string . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(4, 0)
            and (op := self.expect(OP)) is not None
        ):
            self.show_index(4, 0, 1)
            retval = None if op . string in ( "{" , "}" ) else op . string
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None
