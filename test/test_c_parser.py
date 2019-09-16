import ast
import pytest

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension


def check_input_strings_for_grammar(grammar, tmp_path, valid_cases=None, invalid_cases=None):
    rules = parse_string(grammar, GrammarParser).rules
    extension = generate_parser_c_extension(rules, tmp_path)

    if valid_cases:
        for case in valid_cases:
            extension.parse_string(case)

    if invalid_cases:
        for case in invalid_cases:
            with pytest.raises(SyntaxError):
                extension.parse_string(case)


def test_c_parser(tmp_path):
    grammar = """
    start[mod_ty]: a=stmt* $ { Module(a, NULL, p->arena) }
    stmt[stmt_ty]: a=expr_stmt { a }
    expr_stmt[stmt_ty]: a=expr NEWLINE { _Py_Expr(a, EXTRA(a, a)) }
    expr[expr_ty]: ( l=expr '+' r=term { _Py_BinOp(l, Add, r, EXTRA(l, r)) }
                   | l=expr '-' r=term { _Py_BinOp(l, Sub, r, EXTRA(l, r)) }
                   | t=term { t }
                   )
    term[expr_ty]: ( l=term '*' r=factor { _Py_BinOp(l, Mult, r, EXTRA(l, r)) }
                   | l=term '/' r=factor { _Py_BinOp(l, Div, r, EXTRA(l, r)) }
                   | f=factor { f }
                   )
    factor[expr_ty]: ('(' e=expr ')' { e }
                     | a=atom { a }
                     )
    atom[expr_ty]: ( n=NAME { n }
                   | n=NUMBER { n }
                   | s=STRING { s }
                   )
    """
    rules = parse_string(grammar, GrammarParser).rules
    extension = generate_parser_c_extension(rules, tmp_path)

    expressions = [
        "4+5",
        "4-5",
        "4*5",
        "1+4*5",
        "1+4/5",
        "(1+1) + (1+1)",
        "(1+1) - (1+1)",
        "(1+1) * (1+1)",
        "(1+1) / (1+1)",
    ]

    for expr in expressions:
        the_ast = extension.parse_string(expr)
        expected_ast = ast.parse(expr)
        assert ast.dump(the_ast) == ast.dump(expected_ast)


def test_lookahead(tmp_path):
    grammar = """
    start: NAME &NAME expr NEWLINE? ENDMARKER
    expr: NAME | NUMBER
    """
    valid_cases = ["foo bar"]
    invalid_cases = ["foo 34"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases, invalid_cases)


def test_negative_lookahead(tmp_path):
    grammar = """
    start: NAME !NAME expr NEWLINE? ENDMARKER
    expr: NAME | NUMBER
    """
    valid_cases = ["foo 34"]
    invalid_cases = ["foo bar"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases, invalid_cases)


def test_cut(tmp_path):
    grammar = """
    start: X ~ Y Z | X Q S
    X: 'x'
    Y: 'y'
    Z: 'z'
    Q: 'q'
    S: 's'
    """
    valid_cases = ["x y z"]
    invalid_cases = ["x q s"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases, invalid_cases)


def test_left_recursion(tmp_path):
    grammar = """
    start: expr NEWLINE
    expr: ('-' term | expr '+' term | term)
    term: NUMBER
    """
    valid_cases = ["-34", "34", "34 + 12", "1 + 1 + 2 + 3"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases)


def test_advanced_left_recursive(tmp_path):
    grammar = """
    start: NUMBER | sign start
    sign: ['-']
    """
    valid_cases = ["23", "-34"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases)


def test_mutually_left_recursive(tmp_path):
    grammar = """
    start: foo 'E'
    foo: bar 'A' | 'B'
    bar: foo 'C' | 'D'
    """
    valid_cases = ["B E", "D A C A E"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases)
