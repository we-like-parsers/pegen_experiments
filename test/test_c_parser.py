import ast
import pytest

from pegen.grammar import GrammarParser

from test.util import parse_string, import_file, generate_parser_c_extension


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

    rules = parse_string(grammar, GrammarParser).rules
    extension = generate_parser_c_extension(rules, tmp_path)

    extension.parse_string("foo bar")

    with pytest.raises(SyntaxError):
        extension.parse_string("foo 34")


def test_negative_lookahead(tmp_path):
    grammar = """
    start: NAME !NAME expr NEWLINE? ENDMARKER
    expr: NAME | NUMBER
    """

    rules = parse_string(grammar, GrammarParser).rules
    extension = generate_parser_c_extension(rules, tmp_path)

    extension.parse_string("foo 34")

    with pytest.raises(SyntaxError):
        extension.parse_string("foo bar")
