import ast
from pathlib import PurePath
from typing import Optional, Sequence

import pytest  # type: ignore

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension


def check_input_strings_for_grammar(
    source: str,
    tmp_path: PurePath,
    valid_cases: Sequence[str] = (),
    invalid_cases: Sequence[str] = (),
) -> None:
    grammar = parse_string(source, GrammarParser)
    extension = generate_parser_c_extension(grammar, tmp_path)

    if valid_cases:
        for case in valid_cases:
            extension.parse_string(case)

    if invalid_cases:
        for case in invalid_cases:
            with pytest.raises(SyntaxError):
                extension.parse_string(case)


def verify_ast_generation(source: str, stmt: str, tmp_path: PurePath) -> None:
    grammar = parse_string(source, GrammarParser)
    extension = generate_parser_c_extension(grammar, tmp_path)

    expected_ast = ast.parse(stmt)
    actual_ast = extension.parse_string(stmt)
    assert ast.dump(expected_ast) == ast.dump(actual_ast)


def test_c_parser(tmp_path: PurePath) -> None:
    grammar_source = """
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
    grammar = parse_string(grammar_source, GrammarParser)
    extension = generate_parser_c_extension(grammar, tmp_path)

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


def test_lookahead(tmp_path: PurePath) -> None:
    grammar = """
    start: NAME &NAME expr NEWLINE? ENDMARKER
    expr: NAME | NUMBER
    """
    valid_cases = ["foo bar"]
    invalid_cases = ["foo 34"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases, invalid_cases)


def test_negative_lookahead(tmp_path: PurePath) -> None:
    grammar = """
    start: NAME !NAME expr NEWLINE? ENDMARKER
    expr: NAME | NUMBER
    """
    valid_cases = ["foo 34"]
    invalid_cases = ["foo bar"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases, invalid_cases)


def test_cut(tmp_path: PurePath) -> None:
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


def test_left_recursion(tmp_path: PurePath) -> None:
    grammar = """
    start: expr NEWLINE
    expr: ('-' term | expr '+' term | term)
    term: NUMBER
    """
    valid_cases = ["-34", "34", "34 + 12", "1 + 1 + 2 + 3"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases)


def test_advanced_left_recursive(tmp_path: PurePath) -> None:
    grammar = """
    start: NUMBER | sign start
    sign: ['-']
    """
    valid_cases = ["23", "-34"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases)


def test_mutually_left_recursive(tmp_path: PurePath) -> None:
    grammar = """
    start: foo 'E'
    foo: bar 'A' | 'B'
    bar: foo 'C' | 'D'
    """
    valid_cases = ["B E", "D A C A E"]
    check_input_strings_for_grammar(grammar, tmp_path, valid_cases)


def test_return_stmt_noexpr_action(tmp_path: PurePath) -> None:
    grammar = """
    start[mod_ty]: a=[statements] ENDMARKER { Module(a, NULL, p->arena) }
    statements[asdl_seq*]: a=statement+ { a }
    statement[stmt_ty]: simple_stmt
    simple_stmt[stmt_ty]: small_stmt
    small_stmt[stmt_ty]: return_stmt
    return_stmt[stmt_ty]: a='return' NEWLINE { _Py_Return(NULL, EXTRA(a, a)) }
    """
    stmt = "return"
    verify_ast_generation(grammar, stmt, tmp_path)


def test_pass_stmt_action(tmp_path: PurePath) -> None:
    grammar = """
    start[mod_ty]: a=[statements] ENDMARKER { Module(a, NULL, p->arena) }
    statements[asdl_seq*]: a=statement+ { a }
    statement[stmt_ty]: simple_stmt
    simple_stmt[stmt_ty]: small_stmt
    small_stmt[stmt_ty]: pass_stmt
    pass_stmt[stmt_ty]: a='pass' NEWLINE { _Py_Pass(EXTRA(a, a)) }
    """
    stmt = "pass"
    verify_ast_generation(grammar, stmt, tmp_path)


def test_if_stmt_action(tmp_path: PurePath) -> None:
    grammar = """
start[mod_ty]: a=[statements] ENDMARKER { Module(a, NULL, p->arena) }
statements[asdl_seq*]: a=statement+ { seq_flatten(p, a) }
statement[asdl_seq*]:  a=compound_stmt { singleton_seq(p, a) } | simple_stmt

simple_stmt[asdl_seq*]: a=small_stmt b=further_small_stmt* [';'] NEWLINE { seq_insert_in_front(p, a, b) }
further_small_stmt[stmt_ty]: ';' a=small_stmt { a }

block: simple_stmt | NEWLINE INDENT a=statements DEDENT { a }

compound_stmt: if_stmt

if_stmt: 'if' a=full_expression ':' b=block { _Py_If(a, b, NULL, EXTRA(a, b)) }

small_stmt[stmt_ty]: pass_stmt

pass_stmt[stmt_ty]: a='pass' { _Py_Pass(EXTRA(a, a)) }

full_expression: NAME
"""
    stmt = "pass"
    verify_ast_generation(grammar, stmt, tmp_path)
