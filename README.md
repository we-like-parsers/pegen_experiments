PEG parser generator experiments
================================

**NOTE:** The official PEG generator for Python 3.9 and later is now
included in the CPython repo under
[Tools/peg_generator/](https://github.com/python/cpython/tree/master/Tools/peg_generator).

See also [PEP 617](https://www.python.org/dev/peps/pep-0617/).

The code here is a modified copy of that generator where I am
experimenting with error recovery.

The code examples for my blog series on PEG parsing also exist here
(in story1/, story2, etc.).

Blog series
-----------

I've written a series of blog posts on Medium about PEG parsing:

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

I gave a talk about this at North Bay Python:
[Writing a PEG parser for fun and profit](https://www.youtube.com/watch?v=QppWTvh7_sI)
