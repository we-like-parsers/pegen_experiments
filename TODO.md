TODO items
----------

Grammar features:

- [x] Stop using CURLY_STUFF hack and instead design a mini-grammar for what goes between { and }
- [ ] Report static bugs in the grammar,
      see https://github.com/PhilippeSigaud/Pegged/blob/master/pegged/introspection.d
- [x] Make grammar parser bootstrappable

Refactoring:

- [x] Change code generators to use visitor pattern
- [x] Split up into multiple modules
- [ ] Less dependence on Python tokenizer (not a priority, actually)
- [ ] Code cleanup (always under construction)
- [ ] Respond to Nam's code review

Python code generator:

- [ ] Rename all Parser methods to have a leading underscore
- [ ] Change memoize so as to minimize mark()/reset() calls (assume all functions are atomic)
- [ ] Move special cases in expect() (e.g. NEWLINE) to generation-time
- [ ] Reserved words the Python way

C Code generator:

- [x] actually return a result from parse() (an ast.AST)
- [ ] more tests
- [ ] verbose debug output (selected when generating)
- [x] optional
- [x] groups
- [x] repetitions
- [x] lookaheads
- [x] cut operator
- [x] left recursion
- [ ] reserved words
- [ ] option to return a code object instead of an AST
- [ ] Avoid name conflicts between variable names and internal vars (e.g. mark, p)
- [x] Python grammar development
- [x] Test against a large amount of real Python code
- [ ] Improve SyntaxError report (stop putting line/col in message)
- [ ] String kinds, quotes and backslash escapes
- [ ] Store context for NAME tokens
- [ ] Use some syntax like '@prefix <string>' to put prefix in the .gram file instead of hardcoding

Infrastructure:

- [x] CI setup (with coverage)
- [ ] documentation
- [x] blog series (started)
