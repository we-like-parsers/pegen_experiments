import curses
import sys
from tokenize import generate_tokens

from story3.toy import ToyParser
from story3.tokenizer import Tokenizer
from story3.visualizer import Visualizer


def main():
    filename = "story3/in.txt"
    if sys.argv[1:]:
        filename = sys.argv[1]
    with open(filename) as f:
        tokengen = generate_tokens(f.readline)
        vis = Visualizer()
        tok = Tokenizer(tokengen, vis)
        p = ToyParser(tok)
        try:
            tree = p.statement()
            while True:
                curses.flash()
                vis.wait()
        finally:
            vis.close()


main()
