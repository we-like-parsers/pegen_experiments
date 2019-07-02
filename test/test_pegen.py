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
    # Run a parser on a file (stream).
    # Note that this always recognizes {...} as CURLY_STUFF.
    tokenizer = pegen.Tokenizer(pegen.grammar_tokenizer(tokenize.generate_tokens(file.readline)))
    parser = parser_class(tokenizer, verbose=verbose)
    result = parser.start()
    if result is None:
        raise parser.make_syntax_error()
    return result


def parse_string(source, parser_class, *, dedent=True, verbose=False):
    # Run the parser on a string.
    if dedent:
        source = textwrap.dedent(source)
    file = io.StringIO(source)
    return run_parser(file, parser_class, verbose=verbose)


def make_parser(source):
    # Combine parse_string() and generate_parser().
    rules = parse_string(source, pegen.GrammarParser)
    return generate_parser(rules)


def test_parse_grammar():
    grammar = """
    start: sum NEWLINE
    sum: t1=term '+' t2=term { action } | term
    term: NUMBER
    """
    rules = parse_string(grammar, pegen.GrammarParser)
    # Check the str() and repr() of a few rules; AST nodes don't support ==.
    assert str(rules['start']) == "start: sum NEWLINE"
    assert str(rules['sum']) == "sum: t1=term '+' t2=term { action } | term"
    assert repr(rules['term']) == "Rule('term', Rhs([Alt([NamedItem(None, NameLeaf('NUMBER'))])]))"


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
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1\n')], None],
                    TokenInfo(NEWLINE, string='\n', start=(1, 1), end=(1, 2), line='1\n')]


def test_alt_optional_operator():
    grammar = """
    start: sum NEWLINE
    sum: term ['+' term]
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1 + 2\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1 + 2\n')],
                     [TokenInfo(OP, string='+', start=(1, 2), end=(1, 3), line='1 + 2\n'),
                      [TokenInfo(NUMBER, string='2', start=(1, 4), end=(1, 5), line='1 + 2\n')]]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 5), end=(1, 6), line='1 + 2\n')]
    node = parse_string("1\n", parser_class)
    assert node == [[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1\n')], None],
                    TokenInfo(NEWLINE, string='\n', start=(1, 1), end=(1, 2), line='1\n')]


def test_repeat_0_simple():
    grammar = """
    start: thing thing* NEWLINE
    thing: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1 2 3\n", parser_class)
    assert node == [[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1 2 3\n')],
                    [[[TokenInfo(NUMBER, string='2', start=(1, 2), end=(1, 3), line='1 2 3\n')]],
                     [[TokenInfo(NUMBER, string='3', start=(1, 4), end=(1, 5), line='1 2 3\n')]]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 5), end=(1, 6), line='1 2 3\n')]
    node = parse_string("1\n", parser_class)
    assert node == [[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1\n')],
                    [],
                    TokenInfo(NEWLINE, string='\n', start=(1, 1), end=(1, 2), line='1\n')]


def test_repeat_0_complex():
    grammar = """
    start: term ('+' term)* NEWLINE
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1 + 2 + 3\n", parser_class)
    assert node == [[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1 + 2 + 3\n')],
                    [[[TokenInfo(OP, string='+', start=(1, 2), end=(1, 3), line='1 + 2 + 3\n'),
                       [TokenInfo(NUMBER, string='2', start=(1, 4), end=(1, 5), line='1 + 2 + 3\n')]]],
                     [[TokenInfo(OP, string='+', start=(1, 6), end=(1, 7), line='1 + 2 + 3\n'),
                       [TokenInfo(NUMBER, string='3', start=(1, 8), end=(1, 9), line='1 + 2 + 3\n')]]]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 9), end=(1, 10), line='1 + 2 + 3\n')]


def test_repeat_1_simple():
    grammar = """
    start: thing thing+ NEWLINE
    thing: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1 2 3\n", parser_class)
    assert node == [[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1 2 3\n')],
                    [[[TokenInfo(NUMBER, string='2', start=(1, 2), end=(1, 3), line='1 2 3\n')]],
                     [[TokenInfo(NUMBER, string='3', start=(1, 4), end=(1, 5), line='1 2 3\n')]]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 5), end=(1, 6), line='1 2 3\n')]
    with pytest.raises(SyntaxError):
        parse_string("1\n", parser_class)


def test_repeat_1_complex():
    grammar = """
    start: term ('+' term)+ NEWLINE
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("1 + 2 + 3\n", parser_class)
    assert node == [[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1 + 2 + 3\n')],
                    [[[TokenInfo(OP, string='+', start=(1, 2), end=(1, 3), line='1 + 2 + 3\n'),
                       [TokenInfo(NUMBER, string='2', start=(1, 4), end=(1, 5), line='1 + 2 + 3\n')]]],
                     [[TokenInfo(OP, string='+', start=(1, 6), end=(1, 7), line='1 + 2 + 3\n'),
                       [TokenInfo(NUMBER, string='3', start=(1, 8), end=(1, 9), line='1 + 2 + 3\n')]]]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 9), end=(1, 10), line='1 + 2 + 3\n')]
    with pytest.raises(SyntaxError):
        parse_string("1\n", parser_class)


def test_left_recursive():
    grammar = """
    start: expr NEWLINE
    expr: ('-' term | expr '+' term | term)
    term: NUMBER
    foo: NAME+
    bar: NAME*
    baz: NAME?
    """
    rules = parse_string(grammar, pegen.GrammarParser)
    parser_class = generate_parser(rules)
    assert not rules['start'].left_recursive
    assert rules['expr'].left_recursive
    assert not rules['term'].left_recursive
    assert not rules['foo'].left_recursive
    assert not rules['bar'].left_recursive
    assert not rules['baz'].left_recursive
    node = parse_string("1 + 2 + 3\n", parser_class)
    assert node == [[[[[TokenInfo(NUMBER, string='1', start=(1, 0), end=(1, 1), line='1 + 2 + 3\n')]],
                      TokenInfo(OP, string='+', start=(1, 2), end=(1, 3), line='1 + 2 + 3\n'),
                      [TokenInfo(NUMBER, string='2', start=(1, 4), end=(1, 5), line='1 + 2 + 3\n')]],
                     TokenInfo(OP, string='+', start=(1, 6), end=(1, 7), line='1 + 2 + 3\n'),
                     [TokenInfo(NUMBER, string='3', start=(1, 8), end=(1, 9), line='1 + 2 + 3\n')]],
                    TokenInfo(NEWLINE, string='\n', start=(1, 9), end=(1, 10), line='1 + 2 + 3\n')]


def test_python_expr():
    grammar = """
    start: expr NEWLINE? $ { ast.Expression(expr, lineno=1, col_offset=0) }
    expr: ( expr '+' term { ast.BinOp(expr, ast.Add(), term, lineno=expr.lineno, col_offset=expr.col_offset, end_lineno=term.end_lineno, end_col_offset=term.end_col_offset) }
          | expr '-' term { ast.BinOp(expr, ast.Sub(), term, lineno=expr.lineno, col_offset=expr.col_offset, end_lineno=term.end_lineno, end_col_offset=term.end_col_offset) }
          | term { term }
          )
    term: ( l=term '*' r=factor { ast.BinOp(l, ast.Mult(), r, lineno=l.lineno, col_offset=l.col_offset, end_lineno=r.end_lineno, end_col_offset=r.end_col_offset) }
          | l=term '/' r=factor { ast.BinOp(l, ast.Div(), r, lineno=l.lineno, col_offset=l.col_offset, end_lineno=r.end_lineno, end_col_offset=r.end_col_offset) }
          | factor { factor }
          )
    factor: ( '(' expr ')' { expr }
            | atom { atom }
            )
    atom: ( n=NAME { ast.Name(id=n.string, ctx=ast.Load(), lineno=n.start[0], col_offset=n.start[1], end_lineno=n.end[0], end_col_offset=n.end[1]) }
          | n=NUMBER { ast.Constant(value=ast.literal_eval(n.string), lineno=n.start[0], col_offset=n.start[1], end_lineno=n.end[0], end_col_offset=n.end[1]) }
          )
    """
    parser_class = make_parser(grammar)
    node = parse_string("(1 + 2*3 + 5)/(6 - 2)\n", parser_class)
    code = compile(node, "", "eval")
    val = eval(code)
    assert val == 3.0


def test_nullable():
    grammar = """
    start: sign NUMBER
    sign: ['-' | '+']
    """
    rules = parse_string(grammar, pegen.GrammarParser)
    out = io.StringIO()
    genr = pegen.ParserGenerator(rules, out)
    assert rules['start'].nullable is False  # Not None!
    assert rules['sign'].nullable


def test_advanced_left_recursive():
    grammar = """
    start: NUMBER | sign start
    sign: ['-']
    """
    rules = parse_string(grammar, pegen.GrammarParser)
    out = io.StringIO()
    genr = pegen.ParserGenerator(rules, out)
    assert rules['start'].nullable is False  # Not None!
    assert rules['sign'].nullable
    assert rules['start'].left_recursive
    assert not rules['sign'].left_recursive


def test_mutually_left_recursive():
    grammar = """
    start: foo 'E'
    foo: bar 'A' | 'B'
    bar: foo 'C' | 'D'
    """
    rules = parse_string(grammar, pegen.GrammarParser)
    out = io.StringIO()
    genr = pegen.ParserGenerator(rules, out)
    assert not rules['start'].left_recursive
    assert rules['foo'].left_recursive
    assert rules['bar'].left_recursive
    genr.generate_parser("<string>")
    ns = {}
    exec(out.getvalue(), ns)
    parser_class = ns['GeneratedParser']
    node = parse_string("D A C A E", parser_class)
    assert node == [[[[[TokenInfo(type=NAME, string='D', start=(1, 0), end=(1, 1), line='D A C A E')],
                       TokenInfo(type=NAME, string='A', start=(1, 2), end=(1, 3), line='D A C A E')],
                      TokenInfo(type=NAME, string='C', start=(1, 4), end=(1, 5), line='D A C A E')],
                     TokenInfo(type=NAME, string='A', start=(1, 6), end=(1, 7), line='D A C A E')],
                    TokenInfo(type=NAME, string='E', start=(1, 8), end=(1, 9), line='D A C A E')]
    node = parse_string("B C A E", parser_class)
    assert node != None
    assert node == [[[[TokenInfo(type=NAME, string='B', start=(1, 0), end=(1, 1), line='B C A E')],
                      TokenInfo(type=NAME, string='C', start=(1, 2), end=(1, 3), line='B C A E')],
                     TokenInfo(type=NAME, string='A', start=(1, 4), end=(1, 5), line='B C A E')],
                    TokenInfo(type=NAME, string='E', start=(1, 6), end=(1, 7), line='B C A E')]


def test_lookahead():
    grammar = """
    start: (expr_stmt | assign_stmt) &'.'
    expr_stmt: !(target '=') expr
    assign_stmt: target '=' expr
    expr: term ('+' term)*
    target: NAME
    term: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("foo = 12 + 12 .", parser_class)
    assert node == [[[[TokenInfo(NAME, string='foo', start=(1, 0), end=(1, 3), line='foo = 12 + 12 .')],
                      TokenInfo(OP, string='=', start=(1, 4), end=(1, 5), line='foo = 12 + 12 .'),
                      [[TokenInfo(NUMBER, string='12', start=(1, 6), end=(1, 8), line='foo = 12 + 12 .')],
                       [[[TokenInfo(OP, string='+', start=(1, 9), end=(1, 10), line='foo = 12 + 12 .'),
                          [TokenInfo(NUMBER, string='12', start=(1, 11), end=(1, 13), line='foo = 12 + 12 .')]]]]]]]]


def test_named_lookahead_error():
    grammar = """
    start: foo=!'x' NAME
    """
    with pytest.raises(SyntaxError):
        make_parser(grammar)


def test_start_leader():
    grammar = """
    start: attr | NAME
    attr: start '.' NAME
    """
    # Would assert False without a special case in compute_left_recursives().
    make_parser(grammar)


def test_left_recursion_too_complex():
    grammar = """
    start: foo | bar
    foo: bar '+' | '+'
    bar: foo '-' | '-'
    """
    with pytest.raises(ValueError) as errinfo:
        make_parser(grammar)
    assert "has multiple leaders" in str(errinfo.value)


def test_cut():
    grammar = """
    start: '(' ~ expr ')'
    expr: NUMBER
    """
    parser_class = make_parser(grammar)
    node = parse_string("(1)", parser_class, verbose=True)
    assert node == [TokenInfo(OP, string='(', start=(1, 0), end=(1, 1), line='(1)'),
                    [TokenInfo(NUMBER, string='1', start=(1, 1), end=(1, 2), line='(1)')],
                    TokenInfo(OP, string=')', start=(1, 2), end=(1, 3), line='(1)')]
