# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story6.memo import memoize, memoize_left_rec
from story6.node import Node
from story6.parser import Parser

from ast import literal_eval

class CalcParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['_gen_rule_0']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (ee := self._gen_rule_0()) is not None
        ):
            self.show_index(0, 0, 1)
            retval = ee
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize_left_rec
    def expr(self):
        self.show_rule('*' + 'expr', [['expr', "'+'", 'term'], ['expr', "'-'", 'term'], ['term']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (e1 := self.expr()) is not None
            and self.show_index(0, 1)
            and self.expect('+') is not None
            and self.show_index(0, 2)
            and (e2 := self.term()) is not None
        ):
            self.show_index(0, 0, 3)
            retval = e1 + e2
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (e1 := self.expr()) is not None
            and self.show_index(1, 1)
            and self.expect('-') is not None
            and self.show_index(1, 2)
            and (e2 := self.term()) is not None
        ):
            self.show_index(1, 0, 3)
            retval = e1 - e2
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (e := self.term()) is not None
        ):
            self.show_index(2, 0, 1)
            retval = e
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def term(self):
        self.show_rule('term', [['[_gen_rule_1]', 'NUMBER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and ((a := self._gen_rule_1()) or True)
            and self.show_index(0, 1)
            and (number := self.expect(NUMBER)) is not None
        ):
            self.show_index(0, 0, 2)
            retval = literal_eval ( ( a or "" ) + number . string )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def _gen_rule_0(self):
        self.show_rule('_gen_rule_0', [['expr', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (e := self.expr()) is not None
            and self.show_index(0, 1)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(0, 0, 2)
            retval = e
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def _gen_rule_1(self):
        self.show_rule('_gen_rule_1', [["'+'"], ["'-'"]])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and self.expect('+') is not None
        ):
            self.show_index(0, 0, 1)
            retval = ""
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and self.expect('-') is not None
        ):
            self.show_index(1, 0, 1)
            retval = "-"
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None
