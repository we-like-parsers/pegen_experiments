import ast
import os
from pathlib import PurePath
from typing import Any, Iterable, List, Tuple, Union
from textwrap import dedent

import pytest  # type: ignore

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension
from pegen.ast_dump import ast_dump

# fmt: off

TEST_CASES = [
    ('annotated_assignment', 'x: int = 42'),
    ('annotated_assignment_tuple', 'x: tuple = 1, 2'),
    ('annotated_assignment_with_parens', '(paren): int = 3+2'),
    ('annotated_assignment_with_yield', 'x: int = yield 42'),
    ('annotated_no_assignment', 'x: int'),
    ('annotation_with_multiple_parens', '((parens)): int'),
    ('annotation_with_parens', '(parens): int'),
    ('annotated_assignment_with_attr', 'a.b: int'),
    ('annotated_assignment_with_subscript', 'a[b]: int'),
    ('annotated_assignment_with_attr_and_parens', '(a.b): int'),
    ('annotated_assignment_with_subscript_and_parens', '(a[b]): int'),
    ('assert', 'assert a'),
    ('assert_message', 'assert a, b'),
    ('assignment_false', 'a = False'),
    ('assignment_none', 'a = None'),
    ('assignment_true', 'a = True'),
    ('assignment_paren', '(a) = 42'),
    ('assignment_paren_multiple', '(a, b) = (0, 1)'),
    ('asyncfor',
     '''
        async for i in a:
            pass
     '''),
    ('attribute_call', 'a.b()'),
    ('attribute_multiple_names', 'abcd.efg.hij'),
    ('attribute_simple', 'a.b'),
    ('attributes_subscript', 'a.b[0]'),
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
    ('call_attribute', 'f().b'),
    ('call_genexp', 'f(i for i in a)'),
    ('call_mixed_args', 'f(a, b, *c, **d)'),
    ('call_mixed_args_named', 'f(a, b, *c, d=4, **v)'),
    ('call_one_arg', 'f(a)'),
    ('call_posarg_genexp', 'f(a, (i for i in a))'),
    ('call_simple', 'f()'),
    ('call_subscript', 'f()[0]'),
    ('comp', 'a == b'),
    ('comp_multiple', 'a == b == c'),
    ('comp_paren_end', 'a == (b-1)'),
    ('comp_paren_start', '(a-1) == b'),
    ('decorator',
     '''
        @a
        def f():
            pass
     '''),
    ('decorator_async',
     '''
        @a
        async def d():
            pass
     '''),
    ('del_attribute', 'del a.b'),
    ('del_call_attribute', 'del a().c'),
    ('del_call_genexp_attribute', 'del a(i for i in b).c'),
    ('del_empty', 'del()'),
    ('del_list', 'del a, [b, c]'),
    ('del_mixed', 'del a[0].b().c'),
    ('del_multiple', 'del a, b'),
    ('del_multiple_calls_attribute', 'del a()().b'),
    ('del_paren', 'del(a,b)'),
    ('del_paren_single_target', 'del(a)'),
    ('del_subscript_attribute', 'del a[0].b'),
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
    ('dict_empty', '{}'),
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
    ('for_star_target_in_paren', 'for (a) in b: pass'),
    ('for_star_targets_attribute', 'for a.b in c: pass'),
    ('for_star_targets_call_attribute', 'for a().c in b: pass'),
    ('for_star_targets_empty', 'for () in a: pass'),
    ('for_star_targets_mixed', 'for a[0].b().c in d: pass'),
    ('for_star_targets_mixed_starred',
     '''
        for a, *b, (c, d) in e:
            pass
     '''),
    ('for_star_targets_multiple', 'for a, b in c: pass'),
    ('for_star_targets_nested_starred', 'for *[*a] in b: pass'),
    ('for_star_targets_starred', 'for *a in b: pass'),
    ('for_star_targets_subscript_attribute', 'for a[0].b in c: pass'),
    ('for_star_targets_trailing_comma',
     '''
        for a, (b, c), in d:
            pass
     '''),
    ('for_star_targets_tuple', 'for a, (b, c) in d: pass'),
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
    ('f-string_slice', "f'{x[2]}'"),
    ('f-string_slice_upper', "f'{x[2:3]}'"),
    ('f-string_slice_step', "f'{x[2:3:-2]}'"),
    ('f-string_constant', "f'{42}'"),
    ('f-string_boolop', "f'{x and y}'"),
    ('f-string_named_expr', "f'{(x:=42)}'"),
    ('f-string_binop', "f'{x+y}'"),
    ('f-string_unaryop', "f'{not x}'"),
    ('f-string_lambda', "f'{(lambda x, /, y, y2=42 , *z, k1, k2=34, **k3: 42)}'"),
    ('f-string_lambda_call', "f'{(lambda: 2)(2)}'"),
    ('f-string_ifexpr', "f'{x if y else z}'"),
    ('f-string_dict', "f'{ {2:34, 3:34} }'"),
    ('f-string_set', "f'{ {2,-45} }'"),
    ('f-string_list', "f'{ [2,-45] }'"),
    ('f-string_tuple', "f'{ (2,-45) }'"),
    ('f-string_listcomp', "f'{[x for x in y if z]}'"),
    ('f-string_setcomp', "f'{ {x for x in y if z} }'"),
    ('f-string_dictcomp', "f'{ {x:x for x in y if z} }'"),
    ('f-string_genexpr', "f'{ (x for x in y if z) }'"),
    ('f-string_yield', "f'{ (yield x) }'"),
    ('f-string_yieldfrom', "f'{ (yield from x) }'"),
    ('f-string_await', "f'{ await x }'"),
    ('f-string_compare', "f'{ x == y }'"),
    ('f-string_call', "f'{ f(x,y,z) }'"),
    ('f-string_attribute', "f'{ f.x.y.z }'"),
    ('f-string_starred', "f'{ *x, }'"),
    ('f-string_doublestarred', "f'{ {**x} }'"),
    ('f-string_escape_brace', "f'{{Escape'"),
    ('f-string_escape_closing_brace', "f'Escape}}'"),
    ('f-string_repr', "f'{a!r}'"),
    ('f-string_str', "f'{a!s}'"),
    ('f-string_ascii', "f'{a!a}'"),
    ('f-string_debug', "f'{a=}'"),
    ('f-string_padding', "f'{a:03d}'"),
    ('f-string_multiline',
     """
        f'''
        {hello}
        '''
     """),
    ('f-string_multiline_in_expr',
     """
        f'''
        {
        hello
        }
        '''
     """),
    ('f-string_multiline_in_call',
     """
        f'''
        {f(
            a, b, c
        )}
        '''
     """),
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
    ('multipart_string_bytes', 'b"Hola" b"Hello" b"Bye"'),
    ('multipart_string_triple', '"""Something here""" "and now"'),
    ('multipart_string_different_prefixes', 'u"Something" "Other thing" r"last thing"'),
    ('multiple_assignments', 'x = y = z = 42'),
    ('multiple_assignments_with_yield', 'x = y = z = yield 42'),
    ('multiple_pass',
     '''
        pass; pass
        pass
     '''),
    ('namedexpr', '(x := [1, 2, 3])'),
    ('namedexpr_false', '(x := False)'),
    ('namedexpr_none', '(x := None)'),
    ('namedexpr_true', '(x := True)'),
    ('nonlocal', 'nonlocal a, b'),
    ('number_complex', '-2.234+1j'),
    ('number_float', '-34.2333'),
    ('number_imaginary_literal', '1.1234j'),
    ('number_integer', '-234'),
    ('number_underscores', '1_234_567'),
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
    ('primary_mixed', 'a.b.c().d[0]'),
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
    ('string_bytes', 'b"hello"'),
    ('string_concatenation_bytes', 'b"hello" b"world"'),
    ('string_concatenation_simple', '"abcd" "efgh"'),
    ('string_format_simple', 'f"hello"'),
    ('string_format_with_formatted_value', 'f"hello {world}"'),
    ('string_simple', '"hello"'),
    ('string_unicode', 'u"hello"'),
    ('subscript_attribute', 'a[0].b'),
    ('subscript_call', 'a[b]()'),
    ('subscript_multiple_slices', 'a[0:a:2, 1]'),
    ('subscript_simple', 'a[0]'),
    ('subscript_single_element_tuple', 'a[0,]'),
    ('subscript_trailing_comma', 'a[0, 1, 2,]'),
    ('subscript_tuple', 'a[0, 1, 2]'),
    ('subscript_whole_slice', 'a[0+1:b:c]'),
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
    ('unpacking_binop', '[*([1, 2, 3] + [3, 4, 5])]'),
    ('unpacking_call', '[*b()]'),
    ('unpacking_compare', '[*(x < y)]'),
    ('unpacking_constant', '[*3]'),
    ('unpacking_dict', '[*{1: 2, 3: 4}]'),
    ('unpacking_dict_comprehension', '[*{x:y for x,y in z}]'),
    ('unpacking_ifexpr', '[*([1, 2, 3] if x else y)]'),
    ('unpacking_list', '[*[1,2,3]]'),
    ('unpacking_list_comprehension', '[*[x for x in y]]'),
    ('unpacking_namedexpr', '[*(x:=[1, 2, 3])]'),
    ('unpacking_set', '[*{1,2,3}]'),
    ('unpacking_set_comprehension', '[*{x for x in y}]'),
    ('unpacking_string', '[*"myvalue"]'),
    ('unpacking_tuple', '[*(1,2,3)]'),
    ('unpacking_unaryop', '[*(not [1, 2, 3])]'),
    ('unpacking_yield', '[*(yield 42)]'),
    ('unpacking_yieldfrom', '[*(yield from x)]'),
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
    ('with_as_paren',
     '''
        with a as (b):
            pass
     '''),
    ('with_as_empty', 'with a as (): pass'),
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

FAIL_TEST_CASES = [
    ("annotation_multiple_targets", "(a, b): int = 42"),
    ("annotation_nested_tuple", "((a, b)): int"),
    ("annotation_list", "[a]: int"),
    ("annotation_lambda", "lambda: int = 42"),
    ("annotation_tuple", "(a,): int"),
    ("annotation_tuple_without_paren", "a,: int"),
    ("assignment_keyword", "a = if"),
    ("comprehension_lambda", "(a for a in lambda: b)"),
    ("comprehension_else", "(a for a in b if c else d"),
    ("del_call", "del a()"),
    ("del_call_genexp", "del a(i for i in b)"),
    ("del_subscript_call", "del a[b]()"),
    ("del_attribute_call", "del a.b()"),
    ("del_mixed_call", "del a[0].b().c.d()"),
    ("for_star_targets_call", "for a() in b: pass"),
    ("for_star_targets_subscript_call", "for a[b]() in c: pass"),
    ("for_star_targets_attribute_call", "for a.b() in c: pass"),
    ("for_star_targets_mixed_call", "for a[0].b().c.d() in e: pass"),
    ("for_star_targets_in", "for a, in in b: pass"),
    ("f-string_assignment", "f'{x = 42}'"),
    ("f-string_empty", "f'{}'"),
    ("f-string_function_def", "f'{def f(): pass}'"),
    ("f-string_lambda", "f'{lambda x: 42}'"),
    ("f-string_singe_brace", "f'{'"),
    ("f-string_single_closing_brace", "f'}'"),
    ("from_import_invalid", "from import import a"),
    # This test case checks error paths involving tokens with uninitialized
    # values of col_offset and end_col_offset.
    ("invalid indentation",
     """
     def f():
         a
             a
     """),
]

GOOD_BUT_FAIL_TEST_CASES = [
    ('string_concatenation_format', 'f"{hello} world" f"again {and_again}"'),
    ('string_concatenation_multiple',
     '''
        f"hello" f"{world} again" f"and_again"
     '''),
    ('f-string_multiline_comp',
     """
        f'''
        {(i for i in a
            if b)}
        '''
     """),
]

# fmt: on


def cleanup_source(source: Any) -> str:
    if isinstance(source, str):
        result = dedent(source)
    elif not isinstance(source, (list, tuple)):
        result = "\n".join(source)
    else:
        raise TypeError(f"Invalid type for test source: {source}")
    return result


def prepare_test_cases(
    test_cases: Iterable[Tuple[str, Union[str, Iterable[str]]]]
) -> Tuple[Tuple[str, ...], List[str]]:

    test_ids: Tuple[str, ...]
    test_ids, _test_sources = zip(*test_cases)
    test_sources = [cleanup_source(source) for source in _test_sources]
    return test_ids, test_sources


TEST_IDS, TEST_SOURCES = prepare_test_cases(TEST_CASES)

GOOD_BUT_FAIL_TEST_IDS, GOOD_BUT_FAIL_SOURCES = prepare_test_cases(GOOD_BUT_FAIL_TEST_CASES)

FAIL_TEST_IDS, FAIL_SOURCES = prepare_test_cases(FAIL_TEST_CASES)


def create_tmp_extension(tmp_path: PurePath) -> Any:
    with open(os.path.join("data", "python.gram"), "r") as grammar_file:
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
def test_correct_ast_generation_on_source_files(parser_extension: Any, source: str) -> None:
    actual_ast = parser_extension.parse_string(source, mode=1)
    expected_ast = ast.parse(source)
    assert ast_dump(actual_ast, include_attributes=True) == ast_dump(
        expected_ast, include_attributes=True
    ), f"Wrong AST generation for source: {source}"


@pytest.mark.parametrize("source", FAIL_SOURCES, ids=FAIL_TEST_IDS)
def test_incorrect_ast_generation_on_source_files(parser_extension: Any, source: str) -> None:
    with pytest.raises(SyntaxError):
        parser_extension.parse_string(source, mode=0)


@pytest.mark.xfail
@pytest.mark.parametrize("source", GOOD_BUT_FAIL_SOURCES, ids=GOOD_BUT_FAIL_TEST_IDS)
def test_correct_but_known_to_fail_ast_generation_on_source_files(
    parser_extension: Any, source: str
) -> None:
    actual_ast = parser_extension.parse_string(source, mode=1)
    expected_ast = ast.parse(source)
    assert ast_dump(actual_ast, include_attributes=True) == ast_dump(
        expected_ast, include_attributes=True
    ), f"Wrong AST generation for source: {source}"


@pytest.mark.parametrize("source", GOOD_BUT_FAIL_SOURCES, ids=GOOD_BUT_FAIL_TEST_IDS)
def test_correct_ast_generation_without_pos_info(parser_extension: Any, source: str) -> None:
    actual_ast = parser_extension.parse_string(source, mode=1)
    expected_ast = ast.parse(source)
    assert ast_dump(actual_ast) == ast_dump(
        expected_ast
    ), f"Wrong AST generation for source: {source}"
