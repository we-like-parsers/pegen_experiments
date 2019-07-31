# This is @generated code; do not edit!

from token import NAME, NUMBER, STRING, NEWLINE, ENDMARKER

from story2.memo import memoize
from story2.node import Node
from story2.parser import Parser

class ToyParser(Parser):

  @memoize
  def start(self):
    pos = self.mark()
    if (True
        and (statements := self.statements())
        and (endmarker := self.expect(ENDMARKER))
    ):
        return Node('start', [statements, endmarker])
    self.reset(pos)
    return None

  @memoize
  def statements(self):
    pos = self.mark()
    if (True
        and (statement := self.statement())
        and (newline := self.expect(NEWLINE))
    ):
        return Node('statements', [statement, newline])
    self.reset(pos)
    if (True
        and (statement := self.statement())
        and (newline := self.expect(NEWLINE))
        and (statements := self.statements())
    ):
        return Node('statements', [statement, newline, statements])
    self.reset(pos)
    return None

  @memoize
  def statement(self):
    pos = self.mark()
    if (True
        and (assignment := self.assignment())
    ):
        return Node('statement', [assignment])
    self.reset(pos)
    if (True
        and (expr := self.expr())
    ):
        return Node('statement', [expr])
    self.reset(pos)
    if (True
        and (if_statement := self.if_statement())
    ):
        return Node('statement', [if_statement])
    self.reset(pos)
    return None

  @memoize
  def expr(self):
    pos = self.mark()
    if (True
        and (term := self.term())
        and self.expect('+')
        and (expr := self.expr())
    ):
        return Node('expr', [term, expr])
    self.reset(pos)
    if (True
        and (term := self.term())
        and self.expect('-')
        and (term1 := self.term())
    ):
        return Node('expr', [term, term1])
    self.reset(pos)
    if (True
        and (term := self.term())
    ):
        return Node('expr', [term])
    self.reset(pos)
    return None

  @memoize
  def term(self):
    pos = self.mark()
    if (True
        and (atom := self.atom())
        and self.expect('*')
        and (term := self.term())
    ):
        return Node('term', [atom, term])
    self.reset(pos)
    if (True
        and (atom := self.atom())
        and self.expect('/')
        and (atom1 := self.atom())
    ):
        return Node('term', [atom, atom1])
    self.reset(pos)
    if (True
        and (atom := self.atom())
    ):
        return Node('term', [atom])
    self.reset(pos)
    return None

  @memoize
  def atom(self):
    pos = self.mark()
    if (True
        and (name := self.expect(NAME))
    ):
        return Node('atom', [name])
    self.reset(pos)
    if (True
        and (number := self.expect(NUMBER))
    ):
        return Node('atom', [number])
    self.reset(pos)
    if (True
        and self.expect('(')
        and (expr := self.expr())
        and self.expect(')')
    ):
        return Node('atom', [expr])
    self.reset(pos)
    return None

  @memoize
  def assignment(self):
    pos = self.mark()
    if (True
        and (target := self.target())
        and self.expect('=')
        and (expr := self.expr())
    ):
        return Node('assignment', [target, expr])
    self.reset(pos)
    return None

  @memoize
  def target(self):
    pos = self.mark()
    if (True
        and (name := self.expect(NAME))
    ):
        return Node('target', [name])
    self.reset(pos)
    return None

  @memoize
  def if_statement(self):
    pos = self.mark()
    if (True
        and self.expect('if')
        and (expr := self.expr())
        and self.expect(':')
        and (statement := self.statement())
    ):
        return Node('if_statement', [expr, statement])
    self.reset(pos)
    return None
