#!/usr/bin/env python3.8

import sys
from tokenize import generate_tokens

from story3.grammar import GrammarParser
from story3.tokenizer import Tokenizer
from story3.generator import generate
from story3.visualizer import Visualizer

def main():
    file = "story3/toy.gram"
    print("Reading", file)
    with open(file) as f:
        tokengen = generate_tokens(f.readline)
        vis = Visualizer()
        tok = Tokenizer(tokengen, vis)
        p = GrammarParser(tok)
        rules = p.grammar()
    if not rules:
        sys.exit("Fail")
    print("[")
    for rule in rules:
        print(f"  {rule},")
    print("]")
    for rule in rules:
        print(rule.name, end=": ", file=sys.stderr)
        print(*(" ".join(alt) for alt in rule.alts), sep=" | ", file=sys.stderr)
    outfile = "story3/toy.py"
    print("Updating", outfile, file=sys.stderr)
    with open(outfile, "w") as stream:
        generate(rules, stream)

if __name__ == '__main__':
    main()
