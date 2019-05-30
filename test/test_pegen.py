import io
import textwrap
import tokenize

from pegen import GrammarParser, ParserGenerator, Tokenizer, Tree


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


def run_parser(file, parser_class):
    # Run the parser on a file (stream).
    tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
    parser = parser_class(tokenizer)
    return parser.start()


def parse_string(source, parser_class, dedent=True):
    # Run the parser on a string.
    if dedent:
        source = textwrap.dedent(source)
    file = io.StringIO(source)
    return run_parser(file, parser_class)


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
