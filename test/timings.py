import sys
import time
import token
import tokenize

import pegen


def main():
    t0 = time.time()
    ntoks = 0
    nlines = 0
    line_ends = (token.NL, token.NEWLINE)
    for filename in sys.argv[1:]:
        print(f"{nlines:10} lines", end="\r", file=sys.stderr)
        try:
            with open(filename) as file:
                toks = tokenize.generate_tokens(file.readline)
                for tok in toks:
                    ntoks += 1
                    if tok.type in line_ends:
                        nlines += 1
        except Exception as err:
            print("Error:", err, file=sys.stderr)
    tok = None
    t1 = time.time()
    dt = t1 - t0
    print(f"{ntoks} tokens, {nlines} lines in {dt:.3f} secs", file=sys.stderr)
    if dt:
        print(f"{ntoks/dt:.0f} tokens/sec, {nlines/dt:.0f} lines/sec", file=sys.stderr)
    pegen.print_memstats()


if __name__ == "__main__":
    main()
