# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story3.memo import memoize
from story3.node import Node
from story3.parser import Parser

class ToyParser(Parser):

    @memoize
    def start(self):
        self.show_rule('start', [['statements', 'ENDMARKER']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (statements := self.statements())
            and self.show_index(0, 1)
            and (endmarker := self.expect(ENDMARKER))
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
            and (statement := self.statement())
            and self.show_index(0, 1)
            and (newline := self.expect(NEWLINE))
            and self.show_index(0, 2)
            and (statements := self.statements())
        ):
            self.show_index(0, 0, 3)
            return Node('statements', [statement, newline, statements])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(1, 0)
            and (statement := self.statement())
            and self.show_index(1, 1)
            and (newline := self.expect(NEWLINE))
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
            and (if_statement := self.if_statement())
        ):
            self.show_index(0, 0, 1)
            return Node('statement', [if_statement])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(1, 0)
            and (assignment := self.assignment())
        ):
            self.show_index(1, 0, 1)
            return Node('statement', [assignment])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(2, 0)
            and (expr := self.expr())
        ):
            self.show_index(2, 0, 1)
            return Node('statement', [expr])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def expr(self):
        self.show_rule('expr', [['term', "'+'", 'expr'], ['term', "'-'", 'term'], ['term']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (term := self.term())
            and self.show_index(0, 1)
            and self.expect('+')
            and self.show_index(0, 2)
            and (expr := self.expr())
        ):
            self.show_index(0, 0, 3)
            return Node('expr', [term, expr])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(1, 0)
            and (term := self.term())
            and self.show_index(1, 1)
            and self.expect('-')
            and self.show_index(1, 2)
            and (term1 := self.term())
        ):
            self.show_index(1, 0, 3)
            return Node('expr', [term, term1])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(2, 0)
            and (term := self.term())
        ):
            self.show_index(2, 0, 1)
            return Node('expr', [term])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None

    @memoize
    def term(self):
        self.show_rule('term', [['atom', "'*'", 'term'], ['atom', "'/'", 'atom'], ['atom']])
        pos = self.mark()
        if (True
            and self.show_index(0, 0)
            and (atom := self.atom())
            and self.show_index(0, 1)
            and self.expect('*')
            and self.show_index(0, 2)
            and (term := self.term())
        ):
            self.show_index(0, 0, 3)
            return Node('term', [atom, term])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(1, 0)
            and (atom := self.atom())
            and self.show_index(1, 1)
            and self.expect('/')
            and self.show_index(1, 2)
            and (atom1 := self.atom())
        ):
            self.show_index(1, 0, 3)
            return Node('term', [atom, atom1])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(2, 0)
            and (atom := self.atom())
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
            and (name := self.expect(NAME))
        ):
            self.show_index(0, 0, 1)
            return Node('atom', [name])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(1, 0)
            and (number := self.expect(NUMBER))
        ):
            self.show_index(1, 0, 1)
            return Node('atom', [number])
        self.reset(pos)
        self.show_index(0, 0, 0)
        if (True
            and self.show_index(2, 0)
            and self.expect('(')
            and self.show_index(2, 1)
            and (expr := self.expr())
            and self.show_index(2, 2)
            and self.expect(')')
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
            and (target := self.target())
            and self.show_index(0, 1)
            and self.expect('=')
            and self.show_index(0, 2)
            and (expr := self.expr())
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
            and (name := self.expect(NAME))
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
            and self.expect('if')
            and self.show_index(0, 1)
            and (expr := self.expr())
            and self.show_index(0, 2)
            and self.expect(':')
            and self.show_index(0, 3)
            and (statement := self.statement())
        ):
            self.show_index(0, 0, 4)
            return Node('if_statement', [expr, statement])
        self.reset(pos)
        self.show_index(0, 0, 0)
        return None
