# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story7.memo import memoize, memoize_left_rec
from story7.node import Node
from story7.parser import Parser

from ast import literal_eval

class CalcParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['expr_stmt*', 'ENDMARKER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (expr_stmt := self.loop(False, self.expr_stmt)) is not None
            and self.show_index(0, 1)
            and (endmarker := self.expect(ENDMARKER)) is not None
        ):
            self.show_index(0, 0, 2)
            return Node('start', [expr_stmt, endmarker])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def expr_stmt(self):
        self.show_rule('expr_stmt', [['expr', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (expr := self.expr()) is not None
            and self.show_index(0, 1)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(0, 0, 2)
            retval = print ( expr ) or True
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize_left_rec
    def expr(self):
        self.show_rule('*' + 'expr', [['expr', "'+'", '~', 'term'], ['expr', "'-'", '~', 'term'], ['term']])
        pos = self.mark()
        cut = False
        if (True
            and self.show_index(0, 0)
            and (expr := self.expr()) is not None
            and self.show_index(0, 1)
            and self.expect('+') is not None
            and self.show_index(0, 2)
            and True
            and self.show_index(0, 3)
            and (term := self.term()) is not None
        ):
            self.show_index(0, 0, 4)
            retval = expr + term
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(1, 0)
            and (expr := self.expr()) is not None
            and self.show_index(1, 1)
            and self.expect('-') is not None
            and self.show_index(1, 2)
            and True
            and self.show_index(1, 3)
            and (term := self.term()) is not None
        ):
            self.show_index(1, 0, 4)
            retval = expr - term
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(2, 0)
            and (term := self.term()) is not None
        ):
            self.show_index(2, 0, 1)
            retval = term
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize_left_rec
    def term(self):
        self.show_rule('*' + 'term', [["'-'", '~', 'term'], ["'+'", '~', 'term'], ['term', "'*'", '~', 'factor'], ['term', "'/'", '~', 'factor'], ['term', "'//'", '~', 'factor'], ['factor']])
        pos = self.mark()
        cut = False
        if (True
            and self.show_index(0, 0)
            and self.expect('-') is not None
            and self.show_index(0, 1)
            and True
            and self.show_index(0, 2)
            and (term := self.term()) is not None
        ):
            self.show_index(0, 0, 3)
            retval = - term
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(1, 0)
            and self.expect('+') is not None
            and self.show_index(1, 1)
            and True
            and self.show_index(1, 2)
            and (term := self.term()) is not None
        ):
            self.show_index(1, 0, 3)
            retval = + term
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(2, 0)
            and (term := self.term()) is not None
            and self.show_index(2, 1)
            and self.expect('*') is not None
            and self.show_index(2, 2)
            and True
            and self.show_index(2, 3)
            and (factor := self.factor()) is not None
        ):
            self.show_index(2, 0, 4)
            retval = term * factor
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(3, 0)
            and (term := self.term()) is not None
            and self.show_index(3, 1)
            and self.expect('/') is not None
            and self.show_index(3, 2)
            and True
            and self.show_index(3, 3)
            and (factor := self.factor()) is not None
        ):
            self.show_index(3, 0, 4)
            retval = term / factor
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(4, 0)
            and (term := self.term()) is not None
            and self.show_index(4, 1)
            and self.expect('//') is not None
            and self.show_index(4, 2)
            and True
            and self.show_index(4, 3)
            and (factor := self.factor()) is not None
        ):
            self.show_index(4, 0, 4)
            retval = term // factor
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(5, 0)
            and (factor := self.factor()) is not None
        ):
            self.show_index(5, 0, 1)
            retval = factor
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def factor(self):
        self.show_rule('factor', [['atom', "'**'", '~', 'factor'], ['atom']])
        pos = self.mark()
        cut = False
        if (True
            and self.show_index(0, 0)
            and (atom := self.atom()) is not None
            and self.show_index(0, 1)
            and self.expect('**') is not None
            and self.show_index(0, 2)
            and True
            and self.show_index(0, 3)
            and (factor := self.factor()) is not None
        ):
            self.show_index(0, 0, 4)
            retval = atom ** factor
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        if (True
            and self.show_index(1, 0)
            and (atom := self.atom()) is not None
        ):
            self.show_index(1, 0, 1)
            retval = atom
            if retval is not None:
                return retval
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def atom(self):
        self.show_rule('atom', [['STRING'], ['NUMBER'], ["'('", '~', 'expr', "')'"]])
        pos = self.mark()
        cut = False
        if (True
            and self.show_index(0, 0)
            and (string := self.expect(STRING)) is not None
        ):
            self.show_index(0, 0, 1)
            retval = literal_eval ( string . string )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (number := self.expect(NUMBER)) is not None
        ):
            self.show_index(1, 0, 1)
            retval = literal_eval ( number . string )
            if retval is not None:
                return retval
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and self.expect('(') is not None
            and self.show_index(2, 1)
            and True
            and self.show_index(2, 2)
            and (expr := self.expr()) is not None
            and self.show_index(2, 3)
            and self.expect(')') is not None
        ):
            self.show_index(2, 0, 4)
            retval = expr
            if retval is not None:
                return retval
        self.reset(pos)
        if cut:
            self.show_index(0, 0, 0)
            return None
        self.show_index(0, 0, 0)
        return None
