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

Python code generator:

- [ ] Rename all Parser methods to have a leading underscore
- [ ] Change memoize so as to minimize mark()/reset() calls (assume all functions are atomic)
- [ ] Move special cases in expect() (e.g. NEWLINE) to generation-time

C Code generator:

- [ ] actually return a result from parse() (either a code object or an ast.AST)
- [ ] tests
- [x] optional
- [x] groups
- [ ] loops
- [ ] lookaheads
- [ ] cut operator
- [ ] left recursion
- [ ] Avoid name conflicts between variable names and internal vars (e.g. mark, p)

Infrastructure:

- [ ] CI setup (with coverage)
- [ ] code cleanup
- [ ] documentation
- [ ] blog series
