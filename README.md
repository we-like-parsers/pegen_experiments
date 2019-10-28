PEG parser generator
====================
[![Build Status](https://travis-ci.com/gvanrossum/pegen.svg?branch=master)](https://travis-ci.com/gvanrossum/pegen)
[![Coverage Status](https://coveralls.io/repos/github/gvanrossum/pegen/badge.svg?branch=master)](https://coveralls.io/github/gvanrossum/pegen?branch=master)

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

Blog series
-----------

I've started blogging on Medium about this.  I'll probably end up
rewriting everything based on the approach from the blogs.  Episodes:

- [Series overview](https://medium.com/@gvanrossum_83706/peg-parsing-series-de5d41b2ed60)
- [PEG Parsers](https://medium.com/@gvanrossum_83706/peg-parsers-7ed72462f97c)
- [Building a PEG Parser](https://medium.com/@gvanrossum_83706/building-a-peg-parser-d4869b5958fb)
- [Generating a PEG Parser](https://medium.com/@gvanrossum_83706/generating-a-peg-parser-520057d642a9)
- [Visualizing PEG Parsing](https://medium.com/@gvanrossum_83706/visualizing-peg-parsing-93a36f259423)
- [Left-recursive PEG grammars](https://medium.com/@gvanrossum_83706/left-recursive-peg-grammars-65dab3c580e1)
- [Adding actions to a PEG grammar](https://medium.com/@gvanrossum_83706/adding-actions-to-a-peg-grammar-d5e00fa1092f)
- [A Meta-Grammar for PEG Parsers](https://medium.com/@gvanrossum_83706/a-meta-grammar-for-peg-parsers-3d3d502ea332)
- [Implementing PEG Features](https://medium.com/@gvanrossum_83706/implementing-peg-features-76caa4b2151f)
- [PEG at the Core Developer Sprint](https://medium.com/@gvanrossum_83706/peg-at-the-core-developer-sprint-8b23677b91e6)

C code generator
----------------

I am working on generating C code for a Python extension based on the
same grammar notation.  This will produce an AST that can be compiled
to running code.

It is not yet complete, but a preliminary test shows that it can parse
a file of 100,000 lines containing simple expressions (`data/xxl.txt`)
in ~0.8 seconds, using ~420 MiB of memory.  For comparison, compiling
the same file to bytecode currently takes ~2.5 seconds, using ~870
MiB.  (A newer version can produce working AST nodes, and it produces
the AST for that same file in ~5.9 seconds, using ~1100 miB; the
stdlib ast module does the same in ~6 seconds, using ~880 MiB.
However these times are on a faster machine.  Likely the majority of
this time is spent converting the internal AST to the public AST.)

__________
PS. It's pronounced "peggen".
