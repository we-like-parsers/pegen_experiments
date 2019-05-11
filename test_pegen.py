import io
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
    # Run the parser.
    tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
    parser = parser_class(tokenizer)
    return parser.start()


def test_expr_grammar():
    # Read the expression grammar.
    with open('expr.txt') as file:
        tree = run_parser(file, GrammarParser)

    # Generate the parser and load the class.
    parser_class = generate_parser(tree)

    # Parse sample input.
    file = io.StringIO("42\n")
    tree = run_parser(file, parser_class)

    # Check the tree.
    assert tree == Tree('start',
                        Tree('sums',
                             Tree('sum',
                                  Tree('term',
                                       Tree('factor',
                                            Tree('NUMBER', value='42')))),
                             Tree('Empty')))


SAMPLE_GRAMMAR = """
start <- sum NEWLINE ENDMARKER
sum <- term '+' term | term
term <- NUMBER
"""


def test_sample_grammar():
    tree = run_parser(io.StringIO(SAMPLE_GRAMMAR), GrammarParser)
    parser_class = generate_parser(tree)
    tree = run_parser(io.StringIO("42\n"), parser_class)
    assert tree == Tree('start',
                        Tree('sum',
                             Tree('term',
                                  Tree('NUMBER', value='42'))))
