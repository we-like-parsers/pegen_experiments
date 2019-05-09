PEG parser generator
====================

This is a work in progress.  Right now it can read a grammar (using
the same notation as CPython's Grammar) and generate a Python module
that contains a packrat parser.  Various desirable features are still
missing.

Note that this deviates from the formal PEG mechanism in various ways:

- Various grammar features not yet implemented correctly
- The notation is different from the standard PEG formalism
- It requires a separate tokenizer
- No support yet for &X and !X
- No way to specify what kind of tree to build
- No way to produce C code for a parser

___
PS. It's pronounced "pagan".
