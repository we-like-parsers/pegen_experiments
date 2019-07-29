from io import StringIO
from token import NAME, NUMBER, OP, NEWLINE, ENDMARKER
from tokenize import generate_tokens

from story2.tokenizer import Tokenizer

def test_basic():
    program = "f(42)"
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    def get():
        return tok.get_token()[:2]
    assert get() == (NAME, "f")
    assert get() == (OP, "(")
    assert get() == (NUMBER, "42")
    assert get() == (OP, ")")
    assert get() == (NEWLINE, "")
    assert get() == (ENDMARKER, "")

def test_mark_reset():
    program = "f(42) + abc"
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    def get():
        return tok.get_token()[:2]
    assert get() == (NAME, "f")
    pos = tok.mark()
    assert get() == (OP, "(")
    assert get() == (NUMBER, "42")
    assert get() == (OP, ")")
    pos2 = tok.mark()
    tok.reset(pos)
    assert get() == (OP, "(")
    assert get() == (NUMBER, "42")
    assert get() == (OP, ")")
    tok.reset(pos)
    assert get() == (OP, "(")
    tok.reset(pos2)  # Forward
    assert get() == (OP, "+")
    assert get() == (NAME, "abc")
    tok.reset(pos)
    assert get() == (OP, "(")
    assert get() == (NUMBER, "42")
    assert get() == (OP, ")")
    assert get() == (OP, "+")
    assert get() == (NAME, "abc")
