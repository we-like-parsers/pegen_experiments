import sys
import time
from lib2to3 import pytree, pygram
from lib2to3.pgen2 import driver, token, tokenize


import pegen


def main():
    filename = sys.argv[1]
    t0 = time.time()
    drv = driver.Driver(pygram.python_grammar, convert=pytree.convert)
    tree = drv.parse_file(filename)
    t1 = time.time()
    dt = t1 - t0
    with open(filename) as file:
        nlines = len(file.readlines())
    print("%.3f seconds for %d lines; %.0f lines/sec" % (dt, nlines, nlines/(dt or 1e-9)))
    pegen.print_memstats()


if __name__ == '__main__':
    main()
