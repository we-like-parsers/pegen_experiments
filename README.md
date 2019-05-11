PEG parser generator
====================

This is a work in progress.  Right now it can read a grammar (using
the same notation as CPython's Grammar) and generate a Python module
that contains a packrat parser.  Various desirable features are still
missing.

Note that this deviates from the standard [PEG
notation](https://github.com/PhilippeSigaud/Pegged/wiki/PEG-Basics) in
various ways:

- It requires a separate tokenizer
- The notation is different from the standard PEG formalism
- No support yet for &X and !X
- Various grammar features not yet implemented correctly

Other TO DO items:

- Tests
- Syntax what kind of tree to build, e.g. { ... } (combine with 'NAME = ...')
- Generate C code

Both the generator and the generated parsers require Python 3.8 -- it
turns out writing a recursive-descent packrat parser is a really great
use case for the walrus operator (:=).

___
PS. It's pronounced "pagan".
