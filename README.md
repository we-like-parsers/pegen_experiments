PEG parser generator
====================

This is a work in progress.  Right now it can read a grammar (using an
extension of the notation used by pgen2 for CPython's Grammar) and
generate a pure Python module that contains a packrat parser.

Note that this deviates from the standard [PEG
notation](https://github.com/PhilippeSigaud/Pegged/wiki/PEG-Basics) in
various ways:

- It requires a separate tokenizer (currently tied to tokenize.py)
- The notation is different from the standard PEG formalism:
  - Use `:` instead of `<-`
  - Use `|` instead of `/`
  - Notation for tokens is the same as in CPython's Grammar too
- Handling of operators and reserved words is a bit janky

Both the generator and the generated parsers require Python 3.8 -- it
turns out writing a recursive-descent packrat parser is a really great
use case for the walrus operator (`:=`).

See [TODO.md](TODO.md) for a list of open tasks.

C code generator
----------------

I am working on generating C code for a Python extension based on the
same grammar notation.  This will produce an AST that can be compiled
to running code.

It is not yet complete, but a preliminary test shows that it can parse
a file of 100,000 lines containing simple expressions (`data/xxl.txt`)
in ~0.8 seconds, using ~420 MiB of memory.  For comparison, compiling
the same file to bytecode currently takes ~2.5 seconds, using ~870
MiB.

__________
PS. It's pronounced "pagan".
