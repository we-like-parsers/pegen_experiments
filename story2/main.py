#!/usr/bin/env python3.8

import sys
from tokenize import generate_tokens

from story2.grammar import GrammarParser
from story2.tokenizer import Tokenizer
from story2.generator import generate

def main():
    file = "story2/toy.gram"
    with open(file) as f:
        tokengen = generate_tokens(f.readline)
        tok = Tokenizer(tokengen)
        p = GrammarParser(tok)
        rules = p.start()
    if not rules:
        sys.exit("Fail")
    for rule in rules:
        print(rule.name, end=": ", file=sys.stderr)
        print(*(" ".join(alt) for alt in rule.alts), sep=" | ", file=sys.stderr)
    generate(rules)

if __name__ == '__main__':
    main()
