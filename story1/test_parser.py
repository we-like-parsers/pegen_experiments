from io import StringIO
from token import NAME, NUMBER, OP, NEWLINE, ENDMARKER
from tokenize import generate_tokens

from story1.tokenizer import Tokenizer
from story1.parser import Parser
from story1.toy import ToyParser

def test_basic():
    program = "f(42)"
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = Parser(tok)
    t = p.expect(NAME)
    assert t and t.string == "f"
    pos = p.mark()
    assert p.expect("(")
    t = p.expect(NUMBER)
    assert t and t.string == "42"
    assert p.expect(")")
    pos2 = p.mark()
    p.reset(pos)
    assert p.expect("(")
    assert p.expect(NUMBER)
    assert p.expect(")")
    p.reset(pos)

    assert p.expect("(")
    p.reset(pos2)
    assert p.expect(NEWLINE)
    assert p.expect(ENDMARKER)

def test_toy():
    program = "x - (y + z)"
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = ToyParser(tok)
    tree = p.statement()
    assert tree and tree.type == "sub"
    assert tree.children[0].type == NAME
    assert tree.children[1].type == "add"
