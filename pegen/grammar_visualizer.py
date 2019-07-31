import argparse
import tokenize

from pegen.tokenizer import Tokenizer
from pegen.tokenizer import grammar_tokenizer
from pegen.grammar import GrammarParser

argparser = argparse.ArgumentParser(prog='pegen', description="Pretty print the AST for a given PEG grammar")
argparser.add_argument('filename', help="Grammar description")


class ASTGrammarPrinter:

    def children(self, node):
        for value in node:
            if isinstance(value, list):
                yield from value
            else:
                yield value

    def name(self, node):
        if not list(self.children(node)):
            return repr(node)
        return node.__class__.__name__

    def print_grammar_ast(self, rules):
        for rule in rules.values():
            print(self.print_nodes_recursively(rule))

    def print_nodes_recursively(self, node, prefix="", istail=True):

        children = list(self.children(node))
        value = self.name(node)

        line = prefix + ("└──" if istail else "├──") + value + "\n"
        sufix = "   " if istail else "│  "

        if not children:
            return line

        *children, last = children
        for child in children:
            line += self.print_nodes_recursively(child, prefix + sufix, False)
        line += self.print_nodes_recursively(last, prefix + sufix, True)

        return line


def main() -> None:
    args = argparser.parse_args()
    with open(args.filename) as file:
        tokenizer = Tokenizer(grammar_tokenizer(tokenize.generate_tokens(file.readline)))
        parser = GrammarParser(tokenizer)
        rules = parser.start()

    visitor = ASTGrammarPrinter()
    visitor.print_grammar_ast(rules)


if __name__ == "__main__":
    main()
