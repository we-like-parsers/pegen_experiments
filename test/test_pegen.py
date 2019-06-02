import ast
import io
import textwrap
import tokenize

from pegen import GrammarParser, ParserGenerator, Tokenizer, Tree, grammar_tokenizer


def generate_parser(tree):
    # Generate a parser.
    genr = ParserGenerator(tree)
    out = io.StringIO()
    genr.file = out
    genr.generate_parser()

    # Load the generated parser class.
    ns = {}
    exec(out.getvalue(), ns)
    return ns['GeneratedParser']


def run_parser(file, parser_class, *, verbose=False):
    # Run the parser on a file (stream).
    tokenizer = Tokenizer(grammar_tokenizer(tokenize.generate_tokens(file.readline)))
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
    tree = parse_string(source, GrammarParser)
    return generate_parser(tree)


def test_expr_grammar():
    grammar = """
    start <- sums NEWLINE ENDMARKER
    sums <- sum (NEWLINE sum)*
    sum <- term '+' sum / term
    term <- factor '*' term / factor
    factor <- pair / group / NAME / STRING / NUMBER
    pair <- '(' sum ',' sum ')'
    group <- '(' sum ')'
    """
    parser_class = make_parser(grammar)
    tree = parse_string("42\n", parser_class)
    assert tree == Tree('start',
                        Tree('sums',
                             Tree('sum',
                                  Tree('term',
                                       Tree('factor',
                                            Tree('NUMBER', value='42')))),
                             Tree('Repeat')))


def test_optional_operator():
    grammar = """
    start <- sum NEWLINE
    sum <- term ('+' term)?
    term <- NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1+2\n", parser_class)
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


def test_optional_literal():
    grammar = """
    start <- sum NEWLINE
    sum <- term '+'?
    term <- NUMBER
    """
    parser_class = make_parser(grammar)
    tree = parse_string("1+\n", parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='1')),
                             Tree('_opt__tmp_1')))  # XXX Dodgy.
    tree = parse_string("1\n", parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='1')),
                             Tree('Empty')))


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

def test_python_expr():
    grammar = """
    start: expr NEWLINE? ENDMARKER { ast.Expression(expr, lineno=1, col_offset=0) }
    expr: expr '+' term { ast.BinOp(expr, ast.Add(), term) } | expr '-' term { ast.BinOp(expr, ast.Sub(), term) } | term { term }
    term: term '*' factor { ast.BinOp(term, ast.Mult(), factor) } | term '/' factor { ast.BinOp(term, ast.Div(), factor) } | factor { factor }
    factor: '(' expr ')' { expr } | atom { atom }
    atom: NAME { ast.Name(id=name.value, ctx=ast.Load()) } | NUMBER { ast.Constant(value=ast.literal_eval(number.value)) }
    """
    parser_class = make_parser(grammar)
    tree = parse_string("(1 + 2*3 + 5)/(6 - 2)\n", parser_class)
    ast.fix_missing_locations(tree)
    code = compile(tree, "", "eval")
    val = eval(code)
    assert val == 3.0
