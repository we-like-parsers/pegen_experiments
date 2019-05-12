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
    ## print("GENERATED:")
    ## print(out.getvalue())

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


def test_expr_grammar():
    # Read the expression grammar.
    with open('expr.txt') as file:
        tree = run_parser(file, GrammarParser)

    # Generate the parser and load the class.
    parser_class = generate_parser(tree)

    # Parse sample input.
    tree = parse_string("42\n", parser_class)

    # Check the tree.
    assert tree == Tree('start',
                        Tree('sums',
                             Tree('sum',
                                  Tree('term',
                                       Tree('factor',
                                            Tree('NUMBER', value='42')))),
                             Tree('Empty')))


def test_simple_grammar():
    grammar = """
    start <- sum NEWLINE ENDMARKER
    sum <- term ('+' term)?
    term <- NUMBER
    """
    tree = parse_string(grammar, GrammarParser)
    parser_class = generate_parser(tree)
    tree = parse_string("1+2\n", parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='1')),
                             Tree('term',
                                  Tree('NUMBER', value='2'))))
    tree = run_parser(io.StringIO("1\n"), parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='1')),
                             Tree('Empty')))
