import ast
import os
from pathlib import PurePath
from typing import Any

import pytest  # type: ignore

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension

TEST_CASES = [
    ('annotated_assignment', 'x: int = 42\n'),
    ('annotated_assignment_with_parens', '(paren): int = 3+2\n'),
    ('annotated_assignment_with_yield', 'x: int = yield 42\n'),
    ('annotated_no_assignment', 'x: int\n'),
    ('annotation_with_parens', '(parens): int\n'),
    ('assert', 'assert a\n'),
    ('assert_message', 'assert a, b\n'),
    ('asyncfor', 'async for i in a:\n    pass\n'),
    ('augmented_assignment', 'x += 42\n'),
    ('binop_add', '1 + 1\n'),
    ('binop_add_multiple', '1 + 1 + 1 + 1\n'),
    ('binop_all', '1 + 2 * 5 + 3 ** 2 - -3\n'),
    ('binop_boolop_comp', '1 + 1 == 2 or 1 + 1 == 3 and not b\n'),
    ('boolop_or', 'a or b\n'),
    ('boolop_or_multiple', 'a or b or c\n'),
    ('comp', 'a == b\n'),
    ('comp_multiple', 'a == b == c\n'),
    ('decorator', '@a\ndef f():\n    pass\n'),
    ('del_list', 'del a, [b, c]\n'),
    ('del_multiple', 'del a, b\n'),
    ('del_tuple', 'del a, (b, c)\n'),
    ('delete', 'del a\n'),
    ('dict', '{\n    a: 1,\n    b: 2,\n    c: 3\n}\n'),
    ('dict_comp', '{x:1 for x in a}\n'),
    ('dict_comp_if', '{x:1+2 for x in a if b}\n'),
    ('for', 'for i in a:\n    pass\n'),
    ('for_else', 'for i in a:\n    pass\nelse:\n    pass\n'),
    ('for_underscore', 'for _ in a:\n    pass\n'),
    ('function_return_type', 'def f() -> Any:\n    pass\n'),
    ('global', 'global a, b\n'),
    ('group', '(yield a)\n'),
    ('if_elif', 'if a:\n    pass\nelif b:\n    pass\n'),
    ('if_elif_elif', 'if a:\n    pass\nelif b:\n    pass\nelif c:\n    pass\n'),
    ('if_elif_else', 'if a:\n    pass\nelif b:\n    pass\nelse:\n    pass\n'),
    ('if_else', 'if a:\n    pass\nelse:\n    pass\n'),
    ('if_simple', 'if a: pass\n'),
    ('import', 'import a\n'),
    ('import_alias', 'import a as b\n'),
    ('import_dotted', 'import a.b\n'),
    ('import_dotted_alias', 'import a.b as c\n'),
    ('import_dotted_multichar', 'import ab.cd\n'),
    ('import_from', 'from a import b\n'),
    ('import_from_alias', 'from a import b as c\n'),
    ('import_from_dotted', 'from a.b import c\n'),
    ('import_from_dotted_alias', 'from a.b import c as d\n'),
    ('import_from_multiple_aliases', 'from a import b as c, d as e\n'),
    ('import_from_one_dot', 'from .a import b\n'),
    ('import_from_one_dot_alias', 'from .a import b as c\n'),
    ('import_from_star', 'from a import *\n'),
    ('import_from_three_dots', 'from ...a import b\n'),
    ('kwarg', 'def f(**a):\n    pass\n'),
    ('kwonly_args', 'def f(*, a, b):\n    pass\n'),
    ('kwonly_args_with_default', 'def f(*, a=2, b):\n    pass\n'),
    ('lambda_kwarg', 'lambda **a: 42\n'),
    ('lambda_kwonly_args', 'lambda *, a, b: 42\n'),
    ('lambda_kwonly_args_with_default', 'lambda *, a=2, b: 42\n'),
    ('lambda_mixed_args', 'lambda a, /, b, *, c: 42\n'),
    ('lambda_mixed_args_with_default', 'lambda a, b=2, /, c=3, *e, f, **g: 42\n'),
    ('lambda_no_args', 'lambda: 42\n'),
    ('lambda_pos_args', 'lambda a,b: 42\n'),
    ('lambda_pos_args_with_default', 'lambda a, b=2: 42\n'),
    ('lambda_pos_only_args', 'lambda a, /: 42\n'),
    ('lambda_pos_only_args_with_default', 'lambda a=0, /: 42\n'),
    ('lambda_pos_posonly_args', 'lambda a, b, /, c, d: 42\n'),
    ('lambda_pos_posonly_args_with_default', 'lambda a, b=0, /, c=2: 42\n'),
    ('lambda_vararg', 'lambda *a: 42\n'),
    ('lambda_vararg_kwonly_args', 'lambda *a, b: 42\n'),
    ('list', '[1, 2, a]\n'),
    ('list_comp', '[i for i in a]\n'),
    ('list_comp_if', '[i for i in a if b]\n'),
    ('list_trailing_comma', '[1+2, a, 3+4,]\n'),
    ('mixed_args', 'def f(a, /, b, *, c):\n    pass\n'),
    ('mixed_args_with_default', 'def f(a, b=2, /, c=3, *e, f, **g):\n    pass'),
    ('multiple_assignments', 'x = y = z = 42\n'),
    ('multiple_assignments_with_yield', 'x = y = z = yield 42\n'),
    ('multiple_pass', 'pass; pass\npass\n'),
    ('nonlocal', 'nonlocal a, b\n'),
    ('pass', 'pass\n'),
    ('pos_args', 'def f(a, b):\n    pass\n'),
    ('pos_args_with_default', 'def f(a, b=2):\n    pass\n'),
    ('pos_only_args', 'def f(a, /):\n    pass\n'),
    ('pos_only_args_with_default', 'def f(a=0, /):\n    pass\n'),
    ('pos_posonly_args', 'def f(a, b, /, c, d):\n    pass\n'),
    ('pos_posonly_args_with_default', 'def f(a, b=0, /, c=2):\n    pass\n'),
    ('raise', 'raise\n'),
    ('raise_ellipsis', 'raise ...\n'),
    ('raise_expr', 'raise a\n'),
    ('raise_from', 'raise a from b\n'),
    ('return', 'return\n'),
    ('return_expr', 'return a\n'),
    ('set', '{1, 2+4, 3+5}\n'),
    ('set_comp', '{i for i in a}\n'),
    ('set_trailing_comma', '{1, 2, 3,}\n'),
    ('simple_assignment', 'x = 42\n'),
    ('simple_assignment_with_yield', 'x = yield 42\n'),
    ('try_except', 'try:\n    pass\nexcept:\n    pass\n'),
    ('try_except_else', 'try:\n    pass\nexcept:\n    pass\nelse:\n    pass\n'),
    ('try_except_else_finally', 'try:\n    pass\nexcept:\n    pass\nelse:\n    pass\nfinally:\n    pass\n'),
    ('try_except_expr', 'try:\n    pass\nexcept a:\n    pass\n'),
    ('try_except_expr_target', 'try:\n    pass\nexcept a as b:\n    pass\n'),
    ('try_except_finally', 'try:\n    pass\nexcept:\n    pass\nfinally:\n    pass\n'),
    ('try_finally', 'try:\n    pass\nfinally:\n    pass\n'),
    ('tuple', '(1, 2, 3)\n'),
    ('vararg', 'def f(*a):\n    pass\n'),
    ('vararg_kwonly_args', 'def f(*a, b):\n    pass\n'),
    ('while', 'while a:\n    pass\n'),
    ('while_else', 'while a:\n    pass\nelse:\n    pass\n'),
    ('with', 'with a:\n    pass\n'),
    ('with_as', 'with a as b:\n    pass\n'),
    ('yield', 'yield\n'),
    ('yield_expr', 'yield a\n'),
    ('yield_from', 'yield from a\n'),
]

TEST_IDS, TEST_SOURCES = zip(*TEST_CASES)

def create_tmp_extension(tmp_path: PurePath) -> Any:
    with open(os.path.join("data", "simpy.gram"), "r") as grammar_file:
        grammar_source = grammar_file.read()
    grammar = parse_string(grammar_source, GrammarParser)
    extension = generate_parser_c_extension(grammar, tmp_path)
    return extension


@pytest.fixture(scope="module")
def parser_extension(tmp_path_factory: Any) -> Any:
    tmp_path = tmp_path_factory.mktemp("extension")
    extension = create_tmp_extension(tmp_path)
    return extension


@pytest.mark.parametrize("source", TEST_SOURCES, ids=TEST_IDS)
def test_ast_generation_on_source_files(parser_extension: Any, source: str) -> None:
    print(source)
    actual_ast = parser_extension.parse_string(source)
    expected_ast = ast.parse(source)
    assert ast.dump(actual_ast, include_attributes=True) == ast.dump(
        expected_ast, include_attributes=True
    ), f"Wrong AST generation for source: {source}"
