import argparse
import curses
import importlib
import sys
from tokenize import generate_tokens

from story6.parser import Parser
from story6.tokenizer import Tokenizer
from story6.visualizer import Visualizer


argparser = argparse.ArgumentParser()
argparser.add_argument("program", nargs="?", default="story6/in.txt", help="Sample program (in.txt)")
argparser.add_argument("-g", "--grammar", default="story6.toy.ToyParser", help="Grammar class (ToyParser)")
argparser.add_argument("-s", "--start", default="start", help="Start symbol (start)")
argparser.add_argument("-q", "--quiet", action="store_true", help="Don't use visualizer")


def main():
    args = argparser.parse_args()
    filename = args.program
    startname = args.start
    modname, classname = args.grammar.rsplit(".", 1)
    try:
        mod = importlib.import_module(modname)
    except ImportError:
        sys.exit(f"Cannot import {modname}")
    try:
        cls = getattr(mod, classname)
    except AttributeError:
        sys.exit(f"Module {modname} has no attribute {classname}")
    if not isinstance(cls, type):
        sys.exit(f"Object {modname}.{classname} is not a class ({cls!r})")
    if not issubclass(cls, Parser):
        sys.exit(f"Object {modname}.{classname} is not a subclass of Parser")

    tree = None
    with open(filename) as f:
        tokengen = generate_tokens(f.readline)
        if args.quiet:
            vis = None
        else:
            vis = Visualizer()
        try:
            tok = Tokenizer(tokengen, vis)
            p = cls(tok)
            start = getattr(p, startname)
            tree = start()
            if vis:
                vis.done()
        finally:
            if vis:
                vis.close()

    if tree:
        print(tree)
    else:
        if tok.tokens:
            last = tok.tokens[-1]
            print(f"Line {last.start[0]}:")
            print(last.line)
            print(" "*last.start[1] + "^")
        sys.exit("SyntaxError")


main()
