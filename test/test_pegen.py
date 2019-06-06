import ast
import io
import textwrap
import token
import tokenize

import pytest

import pegen

TokenInfo = tokenize.TokenInfo
NAME = token.NAME
NEWLINE = token.NEWLINE
NUMBER = token.NUMBER
OP = token.OP


def generate_parser(rules):
    # Generate a parser.
    out = io.StringIO()
    genr = pegen.ParserGenerator(rules, out)
    genr.generate_parser("<string>")

    # Load the generated parser class.
    ns = {}
    exec(out.getvalue(), ns)
    return ns['GeneratedParser']


def run_parser(file, parser_class, *, verbose=False):
    # Run the parser on a file (stream).
    tokenizer = pegen.Tokenizer(pegen.grammar_tokenizer(tokenize.generate_tokens(file.readline)))
    parser = parser_class(tokenizer, verbose=verbose)
    return parser.start()


def parse_string(source, parser_class, *, dedent=True, verbose=False):
    # Run the parser on a string.
    if dedent:
        source = textwrap.dedent(source)
    file = io.StringIO(source)
    return run_parser(file, parser_class, verbose=verbose)


def make_parser(source):
    # Combine parse_string() and generate_parser().
    node = parse_string(source, pegen.GrammarParser)
    return generate_parser(node)


def test_parse_grammar():
    grammar = """
    start: sum NEWLINE
    sum: t1=term '+' t2=term { action } | term
    term: NUMBER
    """
    rules = parse_string(grammar, pegen.GrammarParser)
    # Check the str() and repr() of a few rules; AST nodes don't support ==.
    assert str(rules[0]) == "start: sum NEWLINE"
    assert str(rules[1]) == "sum: t1=term '+' t2=term { action } | term"
    assert repr(rules[2]) == "Rule('term', Alts([Alt([NamedItem(None, NameLeaf('NUMBER'))])]))"


def test_expr_grammar():
    grammar = """
    start: sum NEWLINE
    sum: term '+' term | term
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("42\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='42', start=(1, 0), end=(1, 2), line='42\n')]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 2), end=(1, 3), line='42\n')]


def test_optional_operator():
    grammar = """
    start: sum NEWLINE
    sum: term ('+' term)?
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1+2\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1+2\n')],
                     [TokenInfo(OP, string='+', start=(1, 1), end=(1, 2), line='1+2\n'),
                      [TokenInfo(NUMBER, string='2', start=(1, 2), end=(1, 3), line='1+2\n')]]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 3), end=(1, 4), line='1+2\n')]
    node = parse_string("1\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1\n')], None],
                    TokenInfo(NEWLINE, string='\n', start=(1, 1), end=(1, 2), line='1\n')]


def test_optional_literal():
    grammar = """
    start: sum NEWLINE
    sum: term '+' ?
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1+\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1+\n')],
                     TokenInfo(OP, string='+', start=(1, 1), end=(1, 2), line='1+\n')],
                    TokenInfo(NEWLINE, string='\n', start=(1, 2), end=(1, 3), line='1+\n')]
    node = parse_string("1\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1\n')],
                     None],
                    TokenInfo(NEWLINE, string='\n', start=(1, 1), end=(1, 2), line='1\n')]


@pytest.mark.skip
def test_alt_optional_operator():
    grammar = """
    start: sum NEWLINE
    sum: term ['+' term]
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1 + 2\n", parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='1')),
                             Tree('term',
                                  Tree('NUMBER', value='2'))))
    tree = parse_string("1\n", parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='1')),
                             Tree('Empty')))


@pytest.mark.skip
def test_repeat_0_simple():
    grammar = """
    start: thing thing* NEWLINE
    thing: NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1 2 3\n", parser_class)
    assert tree == Tree('start',
                        Tree('thing',
                             Tree('NUMBER', value='1')),
                        Tree('Repeat',
                             Tree('thing',
                                  Tree('NUMBER', value='2')),
                             Tree('thing',
                                  Tree('NUMBER', value='3'))))
    tree = parse_string("1\n", parser_class)
    assert tree == Tree('start',
                        Tree('thing',
                             Tree('NUMBER', value='1')),
                        Tree('Repeat'))


@pytest.mark.skip
def test_repeat_0_complex():
    grammar = """
    start: term ('+' term)* NEWLINE
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1 + 2 + 3\n", parser_class)
    assert tree == Tree('start',
                        Tree('term',
                             Tree('NUMBER', value='1')),
                        Tree('Repeat',
                             Tree('term',
                                  Tree('NUMBER', value='2')),
                             Tree('term',
                                  Tree('NUMBER', value='3'))))


@pytest.mark.skip
def test_repeat_1_simple():
    grammar = """
    start: thing thing+ NEWLINE
    thing: NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1 2 3\n", parser_class)
    assert tree == Tree('start',
                        Tree('thing',
                             Tree('NUMBER', value='1')),
                        Tree('Repeat',
                             Tree('thing',
                                  Tree('NUMBER', value='2')),
                             Tree('thing',
                                  Tree('NUMBER', value='3'))))
    tree = parse_string("1\n", parser_class)
    assert tree is None


@pytest.mark.skip
def test_repeat_1_complex():
    grammar = """
    start: term ('+' term)+ NEWLINE
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1 + 2 + 3\n", parser_class)
    assert tree == Tree('start',
                        Tree('term',
                             Tree('NUMBER', value='1')),
                        Tree('Repeat',
                             Tree('term',
                                  Tree('NUMBER', value='2')),
                             Tree('term',
                                  Tree('NUMBER', value='3'))))
    tree = parse_string("1\n", parser_class)
    assert tree is None

@pytest.mark.skip
def test_left_recursive():
    grammar = """
    start: expr NEWLINE
    expr: expr '+' term | term
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1 + 2 + 3\n", parser_class)
    assert tree == Tree('start',
                        Tree('expr',
                             Tree('expr',
                                  Tree('expr',
                                       Tree('term', Tree('NUMBER', value='1'))),
                                  Tree('term', Tree('NUMBER', value='2'))),
                             Tree('term', Tree('NUMBER', value='3'))))

@pytest.mark.skip
def test_python_expr():
    grammar = """
    start: expr NEWLINE? ENDMARKER { ast.Expression(expr, lineno=1, col_offset=0) }
    expr: ( expr '+' term { ast.BinOp(expr, ast.Add(), term) }
          | expr '-' term { ast.BinOp(expr, ast.Sub(), term) }
          | term { term }
          )
    term: ( term '*' factor { ast.BinOp(term, ast.Mult(), factor) }
          | term '/' factor { ast.BinOp(term, ast.Div(), factor) }
          | factor { factor }
          )
    factor: ( '(' expr ')' { expr }
            | atom { atom }
            )
    atom: ( NAME { ast.Name(id=name.value, ctx=ast.Load()) }
          | NUMBER { ast.Constant(value=ast.literal_eval(number.value)) }
          )
    """
    parser_class = make_parser(grammar)
    tree = parse_string("(1 + 2*3 + 5)/(6 - 2)\n", parser_class)
    ast.fix_missing_locations(tree)
    code = compile(tree, "", "eval")
    val = eval(code)
    assert val == 3.0
