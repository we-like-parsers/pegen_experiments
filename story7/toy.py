# This is @generated code; do not edit!

from token import ENDMARKER, NAME, NEWLINE, NUMBER, STRING

from story7.memo import memoize, memoize_left_rec
from story7.node import Node
from story7.parser import Parser

# This is the toy grammar used in the blog series.

class ToyParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['statements', 'ENDMARKER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (statements := self.statements()) is not None
            and self.show_index(0, 1)
            and (endmarker := self.expect(ENDMARKER)) is not None
        ):
            self.show_index(0, 0, 2)
            return Node('start', [statements, endmarker])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def statements(self):
        self.show_rule('statements', [['statement', 'NEWLINE', 'statements'], ['statement', 'NEWLINE']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (statement := self.statement()) is not None
            and self.show_index(0, 1)
            and (newline := self.expect(NEWLINE)) is not None
            and self.show_index(0, 2)
            and (statements := self.statements()) is not None
        ):
            self.show_index(0, 0, 3)
            return Node('statements', [statement, newline, statements])
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (statement := self.statement()) is not None
            and self.show_index(1, 1)
            and (newline := self.expect(NEWLINE)) is not None
        ):
            self.show_index(1, 0, 2)
            return Node('statements', [statement, newline])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def statement(self):
        self.show_rule('statement', [['if_statement'], ['assignment'], ['expr']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (if_statement := self.if_statement()) is not None
        ):
            self.show_index(0, 0, 1)
            return Node('statement', [if_statement])
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (assignment := self.assignment()) is not None
        ):
            self.show_index(1, 0, 1)
            return Node('statement', [assignment])
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (expr := self.expr()) is not None
        ):
            self.show_index(2, 0, 1)
            return Node('statement', [expr])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize_left_rec
    def expr(self):
        self.show_rule('*' + 'expr', [['expr', "'+'", 'term'], ['expr', "'-'", 'term'], ['term']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (expr := self.expr()) is not None
            and self.show_index(0, 1)
            and self.expect('+') is not None
            and self.show_index(0, 2)
            and (term := self.term()) is not None
        ):
            self.show_index(0, 0, 3)
            return Node('expr', [expr, term])
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (expr := self.expr()) is not None
            and self.show_index(1, 1)
            and self.expect('-') is not None
            and self.show_index(1, 2)
            and (term := self.term()) is not None
        ):
            self.show_index(1, 0, 3)
            return Node('expr', [expr, term])
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (term := self.term()) is not None
        ):
            self.show_index(2, 0, 1)
            return Node('expr', [term])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize_left_rec
    def term(self):
        self.show_rule('*' + 'term', [['term', "'*'", 'atom'], ['term', "'/'", 'atom'], ['atom']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (term := self.term()) is not None
            and self.show_index(0, 1)
            and self.expect('*') is not None
            and self.show_index(0, 2)
            and (atom := self.atom()) is not None
        ):
            self.show_index(0, 0, 3)
            return Node('term', [term, atom])
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (term := self.term()) is not None
            and self.show_index(1, 1)
            and self.expect('/') is not None
            and self.show_index(1, 2)
            and (atom := self.atom()) is not None
        ):
            self.show_index(1, 0, 3)
            return Node('term', [term, atom])
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and (atom := self.atom()) is not None
        ):
            self.show_index(2, 0, 1)
            return Node('term', [atom])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def atom(self):
        self.show_rule('atom', [['NAME'], ['NUMBER'], ["'('", 'expr', "')'"]])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (name := self.expect(NAME)) is not None
        ):
            self.show_index(0, 0, 1)
            return Node('atom', [name])
        self.reset(pos)
        if (True
            and self.show_index(1, 0)
            and (number := self.expect(NUMBER)) is not None
        ):
            self.show_index(1, 0, 1)
            return Node('atom', [number])
        self.reset(pos)
        if (True
            and self.show_index(2, 0)
            and self.expect('(') is not None
            and self.show_index(2, 1)
            and (expr := self.expr()) is not None
            and self.show_index(2, 2)
            and self.expect(')') is not None
        ):
            self.show_index(2, 0, 3)
            return Node('atom', [expr])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def assignment(self):
        self.show_rule('assignment', [['target', "'='", 'expr']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (target := self.target()) is not None
            and self.show_index(0, 1)
            and self.expect('=') is not None
            and self.show_index(0, 2)
            and (expr := self.expr()) is not None
        ):
            self.show_index(0, 0, 3)
            return Node('assignment', [target, expr])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def target(self):
        self.show_rule('target', [['NAME']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (name := self.expect(NAME)) is not None
        ):
            self.show_index(0, 0, 1)
            return Node('target', [name])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def if_statement(self):
        self.show_rule('if_statement', [["'if'", 'expr', "':'", 'statement']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and self.expect('if') is not None
            and self.show_index(0, 1)
            and (expr := self.expr()) is not None
            and self.show_index(0, 2)
            and self.expect(':') is not None
            and self.show_index(0, 3)
            and (statement := self.statement()) is not None
        ):
            self.show_index(0, 0, 4)
            return Node('if_statement', [expr, statement])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

# The end.
