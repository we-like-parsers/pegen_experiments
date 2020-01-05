import ast
import os
from pathlib import PurePath
from typing import Any, Union, Iterable, Tuple
from textwrap import dedent

import pytest  # type: ignore

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension

# fmt: off

TEST_CASES = [
    ('annotated_assignment', 'x: int = 42'),
    ('annotated_assignment_with_parens', '(paren): int = 3+2'),
    ('annotated_assignment_with_yield', 'x: int = yield 42'),
    ('annotated_no_assignment', 'x: int'),
    ('annotation_with_parens', '(parens): int'),
    ('assert', 'assert a'),
    ('assert_message', 'assert a, b'),
    ('asyncfor',
     '''
        async for i in a:
            pass
     '''),
    ('augmented_assignment', 'x += 42'),
    ('binop_add', '1 + 1'),
    ('binop_add_multiple', '1 + 1 + 1 + 1'),
    ('binop_all', '1 + 2 * 5 + 3 ** 2 - -3'),
    ('binop_boolop_comp', '1 + 1 == 2 or 1 + 1 == 3 and not b'),
    ('boolop_or', 'a or b'),
    ('boolop_or_multiple', 'a or b or c'),
    ('class_def_bases',
     '''
        class C(A, B):
            pass
     '''),
    ('class_def_decorators',
     '''
        @a
        class C:
            pass
     '''),
    ('class_def_keywords',
     '''
        class C(keyword=a+b, **c):
            pass
     '''),
    ('class_def_mixed',
     '''
        class C(A, B, keyword=0, **a):
            pass
     '''),
    ('class_def_simple',
     '''
        class C:
            pass
     '''),
    ('class_def_starred_and_kwarg',
     '''
        class C(A, B, *x, **y):
            pass
     '''),
    ('class_def_starred_in_kwargs',
     '''
        class C(A, x=2, *[B, C], y=3):
            pass
     '''),
    ('comp', 'a == b'),
    ('comp_multiple', 'a == b == c'),
    ('decorator',
     '''
        @a
        def f():
            pass
     '''),
    ('del_list', 'del a, [b, c]'),
    ('del_multiple', 'del a, b'),
    ('del_tuple', 'del a, (b, c)'),
    ('delete', 'del a'),
    ('dict',
     '''
        {
            a: 1,
            b: 2,
            c: 3
        }
     '''),
    ('dict_comp', '{x:1 for x in a}'),
    ('dict_comp_if', '{x:1+2 for x in a if b}'),
    ('for',
     '''
        for i in a:
            pass
     '''),
    ('for_else',
     '''
        for i in a:
            pass
        else:
            pass
     '''),
    ('for_underscore',
     '''
        for _ in a:
            pass
     '''),
    ('function_return_type',
     '''
        def f() -> Any:
            pass
     '''),
    ('global', 'global a, b'),
    ('group', '(yield a)'),
    ('if_elif',
     '''
        if a:
            pass
        elif b:
            pass
     '''),
    ('if_elif_elif',
     '''
        if a:
            pass
        elif b:
            pass
        elif c:
            pass
     '''),
    ('if_elif_else',
     '''
        if a:
            pass
        elif b:
            pass
        else:
           pass
     '''),
    ('if_else',
     '''
        if a:
            pass
        else:
            pass
     '''),
    ('if_simple', 'if a: pass'),
    ('import', 'import a'),
    ('import_alias', 'import a as b'),
    ('import_dotted', 'import a.b'),
    ('import_dotted_alias', 'import a.b as c'),
    ('import_dotted_multichar', 'import ab.cd'),
    ('import_from', 'from a import b'),
    ('import_from_alias', 'from a import b as c'),
    ('import_from_dotted', 'from a.b import c'),
    ('import_from_dotted_alias', 'from a.b import c as d'),
    ('import_from_multiple_aliases', 'from a import b as c, d as e'),
    ('import_from_one_dot', 'from .a import b'),
    ('import_from_one_dot_alias', 'from .a import b as c'),
    ('import_from_star', 'from a import *'),
    ('import_from_three_dots', 'from ...a import b'),
    ('kwarg',
     '''
        def f(**a):
            pass
     '''),
    ('kwonly_args',
     '''
        def f(*, a, b):
            pass
     '''),
    ('kwonly_args_with_default',
     '''
        def f(*, a=2, b):
            pass
     '''),
    ('lambda_kwarg', 'lambda **a: 42'),
    ('lambda_kwonly_args', 'lambda *, a, b: 42'),
    ('lambda_kwonly_args_with_default', 'lambda *, a=2, b: 42'),
    ('lambda_mixed_args', 'lambda a, /, b, *, c: 42'),
    ('lambda_mixed_args_with_default', 'lambda a, b=2, /, c=3, *e, f, **g: 42'),
    ('lambda_no_args', 'lambda: 42'),
    ('lambda_pos_args', 'lambda a,b: 42'),
    ('lambda_pos_args_with_default', 'lambda a, b=2: 42'),
    ('lambda_pos_only_args', 'lambda a, /: 42'),
    ('lambda_pos_only_args_with_default', 'lambda a=0, /: 42'),
    ('lambda_pos_posonly_args', 'lambda a, b, /, c, d: 42'),
    ('lambda_pos_posonly_args_with_default', 'lambda a, b=0, /, c=2: 42'),
    ('lambda_vararg', 'lambda *a: 42'),
    ('lambda_vararg_kwonly_args', 'lambda *a, b: 42'),
    ('list', '[1, 2, a]'),
    ('list_comp', '[i for i in a]'),
    ('list_comp_if', '[i for i in a if b]'),
    ('list_trailing_comma', '[1+2, a, 3+4,]'),
    ('mixed_args',
     '''
        def f(a, /, b, *, c):
            pass
     '''),
    ('mixed_args_with_default',
     '''
        def f(a, b=2, /, c=3, *e, f, **g):
            pass
     '''),
    ('multiple_assignments', 'x = y = z = 42'),
    ('multiple_assignments_with_yield', 'x = y = z = yield 42'),
    ('multiple_pass',
     '''
        pass; pass
        pass
     '''),
    ('nonlocal', 'nonlocal a, b'),
    ('pass', 'pass'),
    ('pos_args',
     '''
        def f(a, b):
            pass
     '''),
    ('pos_args_with_default',
     '''
        def f(a, b=2):
            pass
     '''),
    ('pos_only_args',
     '''
        def f(a, /):
            pass
     '''),
    ('pos_only_args_with_default',
     '''
        def f(a=0, /):
            pass
     '''),
    ('pos_posonly_args',
     '''
        def f(a, b, /, c, d):
            pass
     '''),
    ('pos_posonly_args_with_default',
     '''
        def f(a, b=0, /, c=2):
            pass
     '''),
    ('raise', 'raise'),
    ('raise_ellipsis', 'raise ...'),
    ('raise_expr', 'raise a'),
    ('raise_from', 'raise a from b'),
    ('return', 'return'),
    ('return_expr', 'return a'),
    ('set', '{1, 2+4, 3+5}'),
    ('set_comp', '{i for i in a}'),
    ('set_trailing_comma', '{1, 2, 3,}'),
    ('simple_assignment', 'x = 42'),
    ('simple_assignment_with_yield', 'x = yield 42'),
    ('try_except',
     '''
        try:
            pass
        except:
            pass
     '''),
    ('try_except_else',
     '''
        try:
            pass
        except:
            pass
        else:
            pass
     '''),
    ('try_except_else_finally',
     '''
        try:
            pass
        except:
            pass
        else:
            pass
        finally:
            pass
     '''),
    ('try_except_expr',
     '''
        try:
            pass
        except a:
            pass
     '''),
    ('try_except_expr_target',
     '''
        try:
            pass
        except a as b:
            pass
     '''),
    ('try_except_finally',
     '''
        try:
            pass
        except:
            pass
        finally:
            pass
     '''),
    ('try_finally',
     '''
        try:
            pass
        finally:
            pass
     '''),
    ('tuple', '(1, 2, 3)'),
    ('vararg',
     '''
        def f(*a):
            pass
     '''),
    ('vararg_kwonly_args',
     '''
        def f(*a, b):
            pass
     '''),
    ('while',
     '''
        while a:
            pass
     '''),
    ('while_else',
     '''
        while a:
            pass
        else:
             pass
    '''),
    ('with',
     '''
        with a:
            pass
     '''),
    ('with_as',
     '''
        with a as b:
            pass
     '''),
    ('with_list_recursive',
     '''
        with a as [x, [y, z]]:
            pass
     '''),
    ('with_tuple_recursive',
     '''
        with a as ((x, y), z):
            pass
     '''),
    ('with_tuple_target',
     '''
        with a as (x, y):
            pass
     '''),
    ('yield', 'yield'),
    ('yield_expr', 'yield a'),
    ('yield_from', 'yield from a'),
]

# fmt: on


def prepare_test_cases(
    test_cases: Iterable[Tuple[str, Union[str, Iterable[str]]]]
) -> Tuple[Iterable[str], Iterable[str]]:

    test_ids, _test_sources = zip(*TEST_CASES)
    test_sources = list(_test_sources)
    for index, source in enumerate(test_sources):
        if isinstance(source, str):
            result = dedent(source)
        elif not isinstance(source, (list, tuple)):
            result = "\n".join(source)
        else:
            raise TypeError(f"Invalid type for test source: {source}")
        test_sources[index] = result
    return test_ids, test_sources


TEST_IDS, TEST_SOURCES = prepare_test_cases(TEST_CASES)


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
