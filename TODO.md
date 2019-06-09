TODO items
----------

- [ ] Implement !x, &x
- [ ] Implement cut (~)
- [ ] Compute indirect (mutual) left-recursion correctly,
      see https://github.com/neogeny/TatSu/blob/master/tatsu/leftrec.py
- [ ] Rename ENDMARKER to $ (apparently standard)
- [ ] Rename all Parser methods to have a leading underscore
- [ ] Change memoize so as to minumize mark()/reset() calls (assume all functions are atomic)
- [ ] Move special cases in expect() (e.g. NEWLINE) to generation-time
- [ ] Stop using CURLY_STUFF hack and instead design a mini-grammar for what goes between { and }
- [ ] Handle reserved words like in Python (maybe later we'll do it differently)
- [ ] Report static bugs in the grammar,
      see https://github.com/PhilippeSigaud/Pegged/blob/master/pegged/introspection.d
- [ ] Make grammar parser bootstrappable
- [ ] CI setup (with coverage)
- [ ] Generate C code
