from io import StringIO
from token import NAME, NUMBER, NEWLINE, ENDMARKER
from tokenize import generate_tokens

from story5.tokenizer import Tokenizer
from story5.parser import Parser
from story5.grammar import Alt, GrammarParser, Rule

def test_grammar():
    program = ("stmt: asmt | expr\n"
               "asmt: NAME '=' expr\n"
               "expr: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.grammar()
    assert rules == [Rule('stmt', [Alt(['asmt']), Alt(['expr'])]),
                     Rule('asmt', [Alt(['NAME', "'='", 'expr'])]),
                     Rule('expr', [Alt(['NAME'])])]

def test_failure():
    program = ("stmt: asmt | expr\n"
               "asmt: NAME '=' expr 42\n"
               "expr: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.grammar()
    assert rules is None

def test_action():
    program = "start: NAME { foo + bar } | NUMBER { -baz }\n"
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.grammar()
    assert rules == [Rule("start", [Alt(["NAME"], "foo + bar"),
                                    Alt(["NUMBER"], "- baz")])]
    assert rules != [Rule("start", [Alt(["NAME"], "foo + bar"),
                                    Alt(["NUMBER"], "baz")])]

def test_action_repr_str():
    alt = Alt(["one", "two"])
    assert repr(alt) == "Alt(['one', 'two'])"
    assert str(alt) == "one two"

    alt = Alt(["one", "two"], "foo + bar")
    assert repr(alt) == "Alt(['one', 'two'], 'foo + bar')"
    assert str(alt) == "one two { foo + bar }"
