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

    with open(filename) as f:
        tokengen = generate_tokens(f.readline)
        vis = Visualizer()
        tok = Tokenizer(tokengen, vis)
        p = cls(tok)
        start = getattr(p, startname)
        try:
            tree = start()
            vis.done()
        finally:
            vis.close()


main()
