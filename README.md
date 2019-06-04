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
- No support yet for `&X` and `!X`

Other TO DO items:

- Measure performance (both time and memory)
- More tests
- CI setup, including coverage
- Generate C code (but this is waaaaay in the future)

Both the generator and the generated parsers require Python 3.8 -- it
turns out writing a recursive-descent packrat parser is a really great
use case for the walrus operator (:=).

__________
PS. It's pronounced "pagan".
