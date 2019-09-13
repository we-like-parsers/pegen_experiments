import sys
import time

sys.path.append("..")
import pegen

from tatsu.util import generic_main
from parse import UnknownBuffer, UnknownParser


def main():
    t0 = time.time()
    for filename in sys.argv[1:]:
        try:
            with open(filename) as file:
                text = file.read()
            parser = UnknownParser()
            ast = parser.parse(text, rule_name="start", filename=filename, whitespace=" ")
        except Exception as err:
            print("Error:", err, file=sys.stderr)
    t1 = time.time()
    nlines = 0
    for filename in sys.argv[1:]:
        with open(filename) as file:
            nlines += len(file.readlines())
    dt = t1 - t0
    print(f"{nlines} lines in {dt:.3f} secs", file=sys.stderr)
    if dt:
        print(f"{nlines/dt:.0f} lines/sec", file=sys.stderr)
    pegen.print_memstats()


if __name__ == "__main__":
    main()
