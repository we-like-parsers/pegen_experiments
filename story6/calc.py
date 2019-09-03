# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story6.memo import memoize, memoize_left_rec
from story6.node import Node
from story6.parser import Parser

class CalcParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['expr', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (expr := self.expr())
            and self.show_index(0, 1)
            and (newline := self.expect(NEWLINE))
        ):
            self.show_index(0, 0, 2)
            retval = expr
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
            and (expr := self.expr())
            and self.show_index(0, 1)
            and self.expect('+')
            and self.show_index(0, 2)
            and (term := self.term())
        ):
            self.show_index(0, 0, 3)
            retval = expr + term
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (expr := self.expr())
            and self.show_index(1, 1)
            and self.expect('-')
            and self.show_index(1, 2)
            and (term := self.term())
        ):
            self.show_index(1, 0, 3)
            retval = expr - term
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (term := self.term())
        ):
            self.show_index(2, 0, 1)
            retval = term
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def term(self):
        self.show_rule('term', [['NUMBER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (number := self.expect(NUMBER))
        ):
            self.show_index(0, 0, 1)
            retval = float ( number . string )
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None
