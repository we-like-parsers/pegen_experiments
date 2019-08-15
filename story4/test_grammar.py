from io import StringIO
from token import NAME, NUMBER, NEWLINE, ENDMARKER
from tokenize import generate_tokens

from story4.tokenizer import Tokenizer
from story4.parser import Parser
from story4.grammar import GrammarParser, Rule

def test_grammar():
    program = ("stmt: asmt | expr\n"
               "asmt: NAME '=' expr\n"
               "expr: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.grammar()
    assert rules == [Rule('stmt', [['asmt'], ['expr']]), Rule('asmt', [['NAME', "'='", 'expr']]), Rule('expr', [['NAME']])]

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
