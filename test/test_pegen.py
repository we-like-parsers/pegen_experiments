import ast
import importlib.util
import io
import textwrap
import tokenize

from tokenize import TokenInfo, NAME, NEWLINE, NUMBER, OP

import pytest

from pegen.grammar import GrammarParser, GrammarVisitor
from pegen.grammar_visualizer import ASTGrammarPrinter
from pegen.python_generator import PythonParserGenerator
from pegen.c_generator import CParserGenerator
from pegen.build import compile_c_extension
from pegen.tokenizer import grammar_tokenizer, Tokenizer


def generate_parser(rules):
    # Generate a parser.
    out = io.StringIO()
    genr = PythonParserGenerator(rules, out)
    genr.generate("<string>")

    # Load the generated parser class.
    ns = {}
    exec(out.getvalue(), ns)
    return ns['GeneratedParser']


def run_parser(file, parser_class, *, verbose=False):
    # Run a parser on a file (stream).
    # Note that this always recognizes {...} as CURLY_STUFF.
    tokenizer = Tokenizer(grammar_tokenizer(tokenize.generate_tokens(file.readline)))
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
    rules = parse_string(source, GrammarParser).rules
    return generate_parser(rules)


def import_file(full_name, path):
    """Import a python module from a path"""

    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(mod)
    return mod


def generate_parser_c_extension(rules, path):
    """Generate a parser c extension for the given rules in the given path"""
    source = path / "parse.c"
    with open(source, "w") as file:
        genr = CParserGenerator(rules, file)
        genr.generate("parse.c")
    extension_path = compile_c_extension(str(source),
                                         build_dir=str(path / "build"))
    extension = import_file("parse", extension_path)
    return extension


@pytest.mark.parametrize(
    "expr",
    [
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

)
def test_c_parser(expr, tmp_path):
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

    parse_file = tmp_path / "cprog.txt"
    with open(parse_file, "w") as file:
        file.write(expr)

    the_ast = extension.parse(str(parse_file))
    expected_ast = ast.parse(expr)
    assert ast.dump(the_ast) == ast.dump(expected_ast)


def test_parse_grammar():
    grammar = """
    start: sum NEWLINE
    sum: t1=term '+' t2=term { action } | term
    term: NUMBER
    """
    rules = parse_string(grammar, GrammarParser).rules
    # Check the str() and repr() of a few rules; AST nodes don't support ==.
    assert str(rules['start']) == "start: sum NEWLINE"
    assert str(rules['sum']) == "sum: t1=term '+' t2=term { action } | term"
    assert repr(rules['term']) == "Rule('term', None, Rhs([Alt([NamedItem(None, NameLeaf('NUMBER'))])]))"

def test_typed_rules():
    grammar = """
    start[int]: sum NEWLINE
    sum[int]: t1=term '+' t2=term { action } | term
    term[int]: NUMBER
    """
    rules = parse_string(grammar, GrammarParser).rules
    # Check the str() and repr() of a few rules; AST nodes don't support ==.
    assert str(rules['start']) == "start[int]: sum NEWLINE"
    assert str(rules['sum']) == "sum[int]: t1=term '+' t2=term { action } | term"
    assert repr(rules['term']) == "Rule('term', 'int', Rhs([Alt([NamedItem(None, NameLeaf('NUMBER'))])]))"


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
    rules = parse_string(grammar, GrammarParser).rules
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
    rules = parse_string(grammar, GrammarParser).rules
    out = io.StringIO()
    genr = PythonParserGenerator(rules, out)
    assert rules['start'].nullable is False  # Not None!
    assert rules['sign'].nullable


def test_advanced_left_recursive():
    grammar = """
    start: NUMBER | sign start
    sign: ['-']
    """
    rules = parse_string(grammar, GrammarParser).rules
    out = io.StringIO()
    genr = PythonParserGenerator(rules, out)
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
    rules = parse_string(grammar, GrammarParser).rules
    out = io.StringIO()
    genr = PythonParserGenerator(rules, out)
    assert not rules['start'].left_recursive
    assert rules['foo'].left_recursive
    assert rules['bar'].left_recursive
    genr.generate("<string>")
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
    start: foo
    foo: bar '+' | baz '+' | '+'
    bar: baz '-' | foo '-' | '-'
    baz: foo '*' | bar '*' | '*'
    """
    with pytest.raises(ValueError) as errinfo:
        make_parser(grammar)
    assert "no leader" in str(errinfo.value)


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


class TestGrammarVisitor:

    class Visitor(GrammarVisitor):
        def __init__(self):
            self.n_nodes = 0

        def visit(self, node):
            self.n_nodes += 1
            super().visit(node)

    def test_parse_trivial_grammar(self):
        grammar = """
        start: 'a'
        """
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()

        visitor.visit(rules)

        assert visitor.n_nodes == 6

    def test_parse_or_grammar(self):
        grammar = """
        start: rule
        rule: 'a' | 'b'
        """
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()

        visitor.visit(rules)

        # Rules/Rule/Rhs/Alt/NamedItem/NameLeaf   -> 6
        #       Rule/Rhs/                         -> 2
        #                Alt/NamedItem/StringLeaf -> 3
        #                Alt/NamedItem/StringLeaf -> 3

        assert visitor.n_nodes == 14

    def test_parse_repeat1_grammar(self):
        grammar = """
        start: 'a'+
        """
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()

        visitor.visit(rules)

        # Rules/Rule/Rhs/Alt/NamedItem/Repeat1/StringLeaf -> 6

        assert visitor.n_nodes == 7

    def test_parse_repeat0_grammar(self):
        grammar = """
        start: 'a'*
        """
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()

        visitor.visit(rules)

        # Rules/Rule/Rhs/Alt/NamedItem/Repeat0/StringLeaf -> 6

        assert visitor.n_nodes == 7


    def test_parse_optional_grammar(self):
        grammar = """
        start: 'a' ['b']
        """
        rules = parse_string(grammar, GrammarParser)
        visitor = self.Visitor()

        visitor.visit(rules)

        # Rules/Rule/Rhs/Alt/NamedItem/StringLeaf                       -> 6
        #                    NamedItem/Opt/Rhs/Alt/NamedItem/Stringleaf -> 6

        assert visitor.n_nodes == 12


class TestGrammarVisualizer:
    def test_simple_rule(self):
        grammar = """
        start: 'a' 'b'
        """
        rules = parse_string(grammar, GrammarParser)

        printer = ASTGrammarPrinter()
        lines = []
        printer.print_grammar_ast(rules, printer=lines.append)

        output = "\n".join(lines)
        expected_output = textwrap.dedent("""\
        └──Rule
           └──Rhs
              └──Alt
                 ├──NamedItem
                 │  └──StringLeaf("'a'")
                 └──NamedItem
                    └──StringLeaf("'b'")
        """)

        assert output == expected_output

    def test_multiple_rules(self):
        grammar = """
        start: a b
        a: 'a'
        b: 'b'
        """
        rules = parse_string(grammar, GrammarParser)

        printer = ASTGrammarPrinter()
        lines = []
        printer.print_grammar_ast(rules, printer=lines.append)

        output = "\n".join(lines)
        expected_output = textwrap.dedent("""\
        └──Rule
           └──Rhs
              └──Alt
                 ├──NamedItem
                 │  └──NameLeaf('a')
                 └──NamedItem
                    └──NameLeaf('b')

        └──Rule
           └──Rhs
              └──Alt
                 └──NamedItem
                    └──StringLeaf("'a'")

        └──Rule
           └──Rhs
              └──Alt
                 └──NamedItem
                    └──StringLeaf("'b'")
                        """)

        assert output == expected_output

    def test_deep_nested_rule(self):
        grammar = """
        start: 'a' ['b'['c'['d']]]
        """
        rules = parse_string(grammar, GrammarParser)

        printer = ASTGrammarPrinter()
        lines = []
        printer.print_grammar_ast(rules, printer=lines.append)

        output = "\n".join(lines)
        print()
        print(output)
        expected_output = textwrap.dedent("""\
        └──Rule
           └──Rhs
              └──Alt
                 ├──NamedItem
                 │  └──StringLeaf("'a'")
                 └──NamedItem
                    └──Opt
                       └──Rhs
                          └──Alt
                             ├──NamedItem
                             │  └──StringLeaf("'b'")
                             └──NamedItem
                                └──Opt
                                   └──Rhs
                                      └──Alt
                                         ├──NamedItem
                                         │  └──StringLeaf("'c'")
                                         └──NamedItem
                                            └──Opt
                                               └──Rhs
                                                  └──Alt
                                                     └──NamedItem
                                                        └──StringLeaf("'d'")
                                """)

        assert output == expected_output

