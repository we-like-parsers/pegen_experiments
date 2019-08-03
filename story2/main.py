#!/usr/bin/env python3.8

import sys
from tokenize import generate_tokens

from story2.grammar import GrammarParser
from story2.tokenizer import Tokenizer
from story2.generator import generate

def main():
    file = "story2/toy.gram"
    print("Reading", file)
    with open(file) as f:
        tokengen = generate_tokens(f.readline)
        tok = Tokenizer(tokengen)
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
    outfile = "story2/toy.py"
    print("Updating", outfile, file=sys.stderr)
    with open(outfile, "w") as stream:
        generate(rules, stream)

if __name__ == '__main__':
    main()
