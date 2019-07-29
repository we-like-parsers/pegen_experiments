from token import NAME, NUMBER

from story2.parser import Parser
from story2.node import Node

class ToyParser(Parser):

    def statement(self):
        if a := self.assignment():
            return a
        if e := self.expr():
            return e
        if i := self.if_statement():
            return i
        return None

    def expr(self):
        if t := self.term():
            pos = self.mark()
            if op := self.expect("+"):
                if e := self.expr():
                    return Node("add", [t, e])
            self.reset(pos)
            if op := self.expect("-"):
                if e := self.expr():
                    return Node("sub", [t, e])
            self.reset(pos)
            return t
        return None

    def term(self):
        if t := self.atom():
            pos = self.mark()
            if op := self.expect("*"):
                if e := self.term():
                    return Node("mul", [t, e])
            self.reset(pos)
            if op := self.expect("/"):
                if e := self.term():
                    return Node("div", [t, e])
            self.reset(pos)
            return t
        return None

    def atom(self):
        if token := self.expect(NAME):
            return token
        if token := self.expect(NUMBER):
            return token
        pos = self.mark()
        if self.expect("("):
            if e := self.expr():
                if self.expect(")"):
                    return e
        self.reset(pos)
        return None

    def assignment(self):
        pos = self.mark()
        if ((t := self.target()) and
            self.expect("=") and
            (e := self.expr())):
            return Node("assign", [t, e])
        self.reset(pos)
        return None

    def target(self):
        return self.expect(NAME)

    def if_statement(self):
        pos = self.mark()
        if (self.expect("if") and
            (e := self.expr()) and
            self.expect(":") and
            (s := self.statement())):
            return Node("if", [e, s])
        self.reset(pos)
        return None
