import curses
import sys
from tokenize import generate_tokens

from story4.toy import ToyParser
from story4.tokenizer import Tokenizer
from story4.visualizer import Visualizer


def main():
    filename = "story4/in.txt"
    startname = "start"
    if sys.argv[1:]:
        filename = sys.argv[1]
        if sys.argv[2:]:
            startname = sys.argv[2]
    with open(filename) as f:
        tokengen = generate_tokens(f.readline)
        vis = Visualizer()
        tok = Tokenizer(tokengen, vis)
        p = ToyParser(tok)
        start = getattr(p, startname)
        try:
            tree = start()
            vis.done()
        finally:
            vis.close()


main()
