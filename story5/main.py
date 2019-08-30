#!/usr/bin/env python3.8

import sys
from tokenize import generate_tokens

from story5.grammar import GrammarParser
from story5.tokenizer import Tokenizer
from story5.generator3 import generate
from story5.visualizer import Visualizer

def main():
    file = "story5/toy.gram"
    print("Reading", file)
    with open(file) as f:
        tokengen = generate_tokens(f.readline)
        vis = None
        if "-v" in sys.argv:
            vis = Visualizer()
        tok = Tokenizer(tokengen, vis)
        p = GrammarParser(tok)
        try:
            rules = p.grammar()
            if vis:
                vis.done()
        finally:
            if vis:
                vis.close()
    if not rules:
        sys.exit("Fail")
    print("[")
    for rule in rules:
        print(f"  {rule},")
    print("]")
    for rule in rules:
        print(rule.name, end=": ", file=sys.stderr)
        print(*(" ".join(alt.items) for alt in rule.alts), sep=" | ", file=sys.stderr)
    outfile = "story5/toy.py"
    print("Updating", outfile, file=sys.stderr)
    with open(outfile, "w") as stream:
        generate(rules, stream)

if __name__ == '__main__':
    main()
