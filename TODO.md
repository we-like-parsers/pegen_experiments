TODO items
----------

- [ ] Support for x?, x* and x+ in actions
- [x] Support naming items in alternatives
- [ ] Unify main() and simple_parser_main()
- [ ] Make grammar parser bootstrappable
- [x] Stop supporting PEG native grammar (<-, /)
- [ ] Implement !x, &x
- [x] Implement naming of items
- [ ] Return the token or None from expect() rather than True/False
- [ ] Move special cases in expect() (e.g. NEWLINE) to generation-time
- [ ] Stop using CURLY_STUFF hack and instead design a mini-grammar for what goes between { and }
- [x] Make PARSER_SUFFIX smaller, move most of the logic into a helper function
- [ ] CI setup (with coverage)
