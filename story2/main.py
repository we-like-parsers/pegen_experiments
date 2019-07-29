#!/usr/bin/env python3.8

import sys
from tokenize import generate_tokens

from story2.grammar import GrammarParser
from story2.tokenizer import Tokenizer

def main():
    file = "story2/toy.gram"
    with open(file) as f:
        tokengen = generate_tokens(f.readline)
        tok = Tokenizer(tokengen)
        p = GrammarParser(tok)
        grammar = p.start()
    if not grammar:
        sys.exit("Fail")
    for rule in grammar:
        print(rule.name, end=": ")
        print(*(" ".join(alt) for alt in rule.alts), sep=" | ")

if __name__ == '__main__':
    main()
