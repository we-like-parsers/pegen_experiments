import curses
import sys
from tokenize import generate_tokens

from story4.toy import ToyParser
from story4.tokenizer import Tokenizer
from story4.visualizer import Visualizer


def main():
    filename = "story4/in.txt"
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
