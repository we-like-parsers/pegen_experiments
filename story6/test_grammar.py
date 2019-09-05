from io import StringIO
from token import NAME, NUMBER, NEWLINE, ENDMARKER
from tokenize import generate_tokens

from story6.tokenizer import Tokenizer
from story6.parser import Parser
from story6.grammar import Alt, NamedItem, Rule, Maybe
from story6.grammarparser import GrammarParser

def test_grammar():
    program = ("stmt: asmt | expr\n"
               "asmt: NAME '=' expr\n"
               "expr: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
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
    grammar = p.start()
    assert grammar is None

def test_action():
    program = "start: NAME { foo + bar } | NUMBER { -baz }\n"
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
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

def test_indents():
    program = ("stmt: foo | bar\n"
               "    | baz\n"
               "    | booh | bah\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('stmt',
                          [Alt(['foo']), Alt(['bar']),
                           Alt(['baz']),
                           Alt(['booh']), Alt(['bah'])])]

def test_indents2():
    program = ("stmt:\n"
               "    | foo | bar\n"
               "    | baz\n"
               "    | booh | bah\n"
               "foo: bar\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('stmt',
                          [Alt(['foo']), Alt(['bar']),
                           Alt(['baz']),
                           Alt(['booh']), Alt(['bah'])]),
                     Rule('foo', [Alt(['bar'])])]

def test_meta():
    program = ("@start 'start'\n"
               "@foo bar\n"
               "@bar\n"
               "stmt: foo\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    grammar = p.start()
    assert grammar
    assert grammar.rules == [Rule('stmt', [Alt(["foo"])])]
    assert grammar.metas == [('start', 'start'),
                             ('foo', 'bar'),
                             ('bar', None)]

def test_named_item():
    program = ("start: f=foo\n"
               "foo: n=NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('start', [Alt([NamedItem('f', 'foo')])]),
                     Rule('foo', [Alt([NamedItem('n', 'NAME')])])]

def test_group():
    program = ("start: (foo foo | foo)\n"
               "foo: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('start', [Alt(['_gen_rule_0'])]),
                     Rule('foo', [Alt(['NAME'])]),
                     Rule('_gen_rule_0', [Alt(['foo', 'foo']), Alt(['foo'])])]

def test_maybe_1():
    program = ("start: foo?\n"
               "foo: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('start', [Alt([Maybe('foo')])]),
                     Rule('foo', [Alt(['NAME'])])]

def test_maybe_2():
    program = ("start: [foo]\n"
               "foo: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('start', [Alt([Maybe('foo')])]),
                     Rule('foo', [Alt(['NAME'])])]

def test_maybe_3():
    program = ("start: [foo foo | foo]\n"
               "foo: NAME\n")
    file = StringIO(program)
    tokengen = generate_tokens(file.readline)
    tok = Tokenizer(tokengen)
    p = GrammarParser(tok)
    rules = p.start().rules
    assert rules == [Rule('start', [Alt([Maybe('_gen_rule_0')])]),
                     Rule('foo', [Alt(['NAME'])]),
                     Rule('_gen_rule_0', [Alt(['foo', 'foo']), Alt(['foo'])])]
