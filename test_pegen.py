import io
import tokenize

from pegen import GrammarParser, ParserGenerator, Tokenizer, Tree


def test_expr_grammar():
    # Read the expression grammar.
    with open('expr.txt') as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
        parser = GrammarParser(tokenizer)
        tree = parser.start()

    # Generate a parser.
    genr = ParserGenerator(tree)
    out = io.StringIO()
    genr.file = out
    genr.generate_parser()

    # Load the generated parser class.
    ns = {}
    exec(out.getvalue(), ns)
    GeneratedParser = ns['GeneratedParser']

    # Run the parser.
    file = io.StringIO("42\n")
    tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
    parser = GeneratedParser(tokenizer)
    tree = parser.start()

    # Check the tree.
    assert tree == Tree('start', Tree('sums',
                                      Tree('sum',
                                           Tree('term',
                                                Tree('factor',
                                                     Tree('NUMBER', value='42')))),
                                      Tree('Empty')))

    # TODO: Verify other inputs.
