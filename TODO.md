TODO items
----------

Grammar features:

- [ ] Stop using CURLY_STUFF hack and instead design a mini-grammar for what goes between { and }
- [ ] Handle reserved words like in Python (maybe later we'll do it differently)
- [ ] Report static bugs in the grammar,
      see https://github.com/PhilippeSigaud/Pegged/blob/master/pegged/introspection.d
- [ ] Make grammar parser bootstrappable

Refactoring:

- [ ] Change code generators to use visitor pattern
- [ ] Split up into multiple modules
- [ ] Less dependence on Python tokenizer
- [ ] Code cleanup
- [ ] Respond to Nam's code review

Python code generator:

- [ ] Rename all Parser methods to have a leading underscore
- [ ] Change memoize so as to minimize mark()/reset() calls (assume all functions are atomic)
- [ ] Move special cases in expect() (e.g. NEWLINE) to generation-time
- [ ] Reserved words the Python way

C Code generator:

- [x] actually return a result from parse() (an ast.AST)
- [ ] tests
- [ ] verbose debug output (selected when generating)
- [x] optional
- [x] groups
- [x] repetitions
- [ ] lookaheads
- [ ] cut operator
- [x] left recursion
- [ ] reserved words
- [ ] option to return a code object instead of an AST
- [ ] Avoid name conflicts between variable names and internal vars (e.g. mark, p)
- [ ] Python grammar development
- [ ] Test against a large amount of real Python code
- [ ] Better SyntaxError report
- [ ] String kinds, quotes and backslash escapes
- [ ] Store context for NAME tokens
- [ ] Use some syntax like '@prefix <string>' to put prefix in the .gram file instead of hardcoding

Infrastructure:

- [ ] CI setup (with coverage)
- [ ] documentation
- [ ] blog series
