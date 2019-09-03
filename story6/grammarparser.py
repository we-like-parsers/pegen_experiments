# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story6.memo import memoize, memoize_left_rec
from story6.node import Node
from story6.parser import Parser


from ast import literal_eval
from token import COMMENT, DEDENT, INDENT, NL, OP

from story6.grammar import Grammar, Rule, Alt

class GrammarParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['grammar', 'ENDMARKER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (grammar := self.grammar())
            and self.show_index(0, 1)
            and (endmarker := self.expect(ENDMARKER))
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
            and (metas := self.metas())
            and self.show_index(0, 1)
            and (rules := self.rules())
        ):
            self.show_index(0, 0, 2)
            retval = Grammar ( rules , metas )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (rules := self.rules())
        ):
            self.show_index(1, 0, 1)
            retval = Grammar ( rules , [ ] )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def metas(self):
        self.show_rule('metas', [['meta', 'metas'], ['meta'], ['blank', 'metas'], ['blank']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (meta := self.meta())
            and self.show_index(0, 1)
            and (metas := self.metas())
        ):
            self.show_index(0, 0, 2)
            retval = [ meta ] + metas
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (meta := self.meta())
        ):
            self.show_index(1, 0, 1)
            retval = [ meta ]
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (blank := self.blank())
            and self.show_index(2, 1)
            and (metas := self.metas())
        ):
            self.show_index(2, 0, 2)
            retval = metas
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(3, 0)
            and (blank := self.blank())
        ):
            self.show_index(3, 0, 1)
            retval = [ ]
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
            and self.expect("@")
            and self.show_index(0, 1)
            and (name := self.expect(NAME))
            and self.show_index(0, 2)
            and (newline := self.expect(NEWLINE))
        ):
            self.show_index(0, 0, 3)
            retval = ( name . string , None )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and self.expect("@")
            and self.show_index(1, 1)
            and (name := self.expect(NAME))
            and self.show_index(1, 2)
            and (name1 := self.expect(NAME))
            and self.show_index(1, 3)
            and (newline := self.expect(NEWLINE))
        ):
            self.show_index(1, 0, 4)
            retval = ( name . string , name1 . string )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and self.expect("@")
            and self.show_index(2, 1)
            and (name := self.expect(NAME))
            and self.show_index(2, 2)
            and (string := self.expect(STRING))
            and self.show_index(2, 3)
            and (newline := self.expect(NEWLINE))
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
        self.show_rule('rules', [['rule', 'rules'], ['rule'], ['blank', 'rules'], ['blank']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (rule := self.rule())
            and self.show_index(0, 1)
            and (rules := self.rules())
        ):
            self.show_index(0, 0, 2)
            retval = [ rule ] + rules
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (rule := self.rule())
        ):
            self.show_index(1, 0, 1)
            retval = [ rule ]
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (blank := self.blank())
            and self.show_index(2, 1)
            and (rules := self.rules())
        ):
            self.show_index(2, 0, 2)
            retval = rules
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(3, 0)
            and (blank := self.blank())
        ):
            self.show_index(3, 0, 1)
            retval = [ ]
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
            and (name := self.expect(NAME))
            and self.show_index(0, 1)
            and self.expect(":")
            and self.show_index(0, 2)
            and (alts := self.alts())
            and self.show_index(0, 3)
            and (newline := self.expect(NEWLINE))
            and self.show_index(0, 4)
            and (indent := self.expect(INDENT))
            and self.show_index(0, 5)
            and (more_alts := self.more_alts())
            and self.show_index(0, 6)
            and (dedent := self.expect(DEDENT))
        ):
            self.show_index(0, 0, 7)
            retval = Rule ( name . string , alts + more_alts )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (name := self.expect(NAME))
            and self.show_index(1, 1)
            and self.expect(":")
            and self.show_index(1, 2)
            and (newline := self.expect(NEWLINE))
            and self.show_index(1, 3)
            and (indent := self.expect(INDENT))
            and self.show_index(1, 4)
            and (more_alts := self.more_alts())
            and self.show_index(1, 5)
            and (dedent := self.expect(DEDENT))
        ):
            self.show_index(1, 0, 6)
            retval = Rule ( name . string , more_alts )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (name := self.expect(NAME))
            and self.show_index(2, 1)
            and self.expect(":")
            and self.show_index(2, 2)
            and (alts := self.alts())
            and self.show_index(2, 3)
            and (newline := self.expect(NEWLINE))
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
            and self.expect("|")
            and self.show_index(0, 1)
            and (alts := self.alts())
            and self.show_index(0, 2)
            and (newline := self.expect(NEWLINE))
            and self.show_index(0, 3)
            and (more_alts := self.more_alts())
        ):
            self.show_index(0, 0, 4)
            retval = alts + more_alts
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and self.expect("|")
            and self.show_index(1, 1)
            and (alts := self.alts())
            and self.show_index(1, 2)
            and (newline := self.expect(NEWLINE))
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
            and (alt := self.alt())
            and self.show_index(0, 1)
            and self.expect("|")
            and self.show_index(0, 2)
            and (alts := self.alts())
        ):
            self.show_index(0, 0, 3)
            retval = [ alt ] + alts
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (alt := self.alt())
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
            and (items := self.items())
            and self.show_index(0, 1)
            and (action := self.action())
        ):
            self.show_index(0, 0, 2)
            retval = Alt ( items , action )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (items := self.items())
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
            and (item := self.item())
            and self.show_index(0, 1)
            and (items := self.items())
        ):
            self.show_index(0, 0, 2)
            retval = [ item ] + items
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (item := self.item())
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
        self.show_rule('item', [['NAME'], ['STRING']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (name := self.expect(NAME))
        ):
            self.show_index(0, 0, 1)
            retval = name . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (string := self.expect(STRING))
        ):
            self.show_index(1, 0, 1)
            retval = string . string
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
            and self.expect("{")
            and self.show_index(0, 1)
            and (stuffs := self.stuffs())
            and self.show_index(0, 2)
            and self.expect("}")
        ):
            self.show_index(0, 0, 3)
            retval = "{" + stuffs + "}"
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
            and (stuff := self.stuff())
            and self.show_index(0, 1)
            and (stuffs := self.stuffs())
        ):
            self.show_index(0, 0, 2)
            retval = stuff + " " + stuffs
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (stuff := self.stuff())
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
        self.show_rule('stuff', [['action'], ['NAME'], ['NUMBER'], ['STRING'], ['OP']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (action := self.action())
        ):
            self.show_index(0, 0, 1)
            retval = action
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (name := self.expect(NAME))
        ):
            self.show_index(1, 0, 1)
            retval = name . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (number := self.expect(NUMBER))
        ):
            self.show_index(2, 0, 1)
            retval = number . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(3, 0)
            and (string := self.expect(STRING))
        ):
            self.show_index(3, 0, 1)
            retval = string . string
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(4, 0)
            and (op := self.expect(OP))
        ):
            self.show_index(4, 0, 1)
            retval = op . string if op . string not in ( "{" , "}" ) else None
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def blank(self):
        self.show_rule('blank', [['NL'], ['COMMENT']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (nl := self.expect(NL))
        ):
            self.show_index(0, 0, 1)
            return Node('blank', [nl])
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (comment := self.expect(COMMENT))
        ):
            self.show_index(1, 0, 1)
            return Node('blank', [comment])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None
