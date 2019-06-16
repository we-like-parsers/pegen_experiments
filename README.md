PEG parser generator
====================

This is a work in progress.  Right now it can read a grammar (using
the same notation as CPython's Grammar) and generate a Python module
that contains a packrat parser.  Various desirable features are still
missing.

Note that this deviates from the standard [PEG
notation](https://github.com/PhilippeSigaud/Pegged/wiki/PEG-Basics) in
various ways:

- It requires a separate tokenizer (currently tied to tokenize.py)
- The notation is different from the standard PEG formalism:
  - Use `:` instead of `<-`
  - Use `|` instead of `/`
  - Notation for tokens is the same as in CPython's Grammar too
- No support yet for "cut", `~`
- Handling of operators and reserved words is a bit janky

Both the generator and the generated parsers require Python 3.8 -- it
turns out writing a recursive-descent packrat parser is a really great
use case for the walrus operator (`:=`).

See [TODO.md](TODO.md) for a list of open tasks.

__________
PS. It's pronounced "pagan".
