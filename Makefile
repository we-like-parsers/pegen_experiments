PYTHON ?= python3.10
CPYTHON ?= cpython
MYPY ?= mypy

GRAMMAR = data/python.gram
TOKENS = data/Tokens
TESTFILE = data/cprog.txt
TIMEFILE = data/xxl.txt
TESTDIR = .
TESTFLAGS = --short

PARSE_C = peg_extension/parse.c

build: $(PARSE_C)

$(PARSE_C): $(GRAMMAR) pegen/*.py peg_extension/peg_extension.c pegen/grammar_parser.py
	$(PYTHON) -m pegen -q c $(GRAMMAR) $(TOKENS) -o $(PARSE_C) --compile-extension

clean:
	-rm -f peg_extension/*.o peg_extension/*.so $(PARSE_C)

dump: $(PARSE_C)
	cat -n $(TESTFILE)
	$(PYTHON) -c "from peg_extension import parse; import ast; t = parse.parse_file('$(TESTFILE)', mode=1); print(ast.dump(t))"

regen-metaparser: pegen/metagrammar.gram pegen/*.py
	$(PYTHON) -m pegen -q python pegen/metagrammar.gram -o pegen/grammar_parser.py

# Note: These targets really depend on the generated shared object in pegen/parse.*.so but
# this has different names in different systems so we are abusing the implicit dependency on
# parse.c by the use of --compile-extension.

.PHONY: test

test: run

run: $(PARSE_C)
	$(PYTHON) -c "from peg_extension import parse; t = parse.parse_file('$(TESTFILE)', mode=2); exec(t)"

compile: $(PARSE_C)
	$(PYTHON) -c "from peg_extension import parse; t = parse.parse_file('$(TESTFILE)', mode=2)"

parse: $(PARSE_C)
	$(PYTHON) -c "from peg_extension import parse; t = parse.parse_file('$(TESTFILE)', mode=1)"

check: $(PARSE_C)
	$(PYTHON) -c "from peg_extension import parse; t = parse.parse_file('$(TESTFILE)', mode=0)"

stats: $(PARSE_C)
	$(PYTHON) -c "from peg_extension import parse; t = parse.parse_file('$(TIMEFILE)', mode=0); parse.dump_memo_stats()" >@data
	$(PYTHON) scripts/joinstats.py @data

time: time_compile

time_compile: $(PARSE_C)
	/usr/bin/time -l $(PYTHON) -c "from peg_extension import parse; parse.parse_file('$(TIMEFILE)', mode=2)"

time_parse: $(PARSE_C)
	/usr/bin/time -l $(PYTHON) -c "from peg_extension import parse; parse.parse_file('$(TIMEFILE)', mode=1)"

time_check: $(PARSE_C)
	/usr/bin/time -l $(PYTHON) -c "from peg_extension import parse; parse.parse_file('$(TIMEFILE)', mode=0)"

time_stdlib: time_stdlib_compile

time_stdlib_compile:
	/usr/bin/time -l $(PYTHON) -c "import ast; compile(open('$(TIMEFILE)').read(), '$(TIMEFILE)', 'exec')"

time_stdlib_parse:
	/usr/bin/time -l $(PYTHON) -c "import ast; ast.parse(open('$(TIMEFILE)').read())"

test_local: clean-cpython
	$(PYTHON) scripts/test_parse_directory.py \
		-g data/python.gram \
		-d $(TESTDIR) \
		$(TESTFLAGS) \
		--exclude "*/failset/*" \
		--exclude "*/failset/**" \
		--exclude "*/failset/**/*"

test_global: $(CPYTHON)
	$(PYTHON) scripts/test_parse_directory.py \
		-g data/python.gram \
		-d $(CPYTHON) \
		$(TESTFLAGS) \
		--exclude "*/test2to3/*" \
		--exclude "*/test2to3/**/*" \
		--exclude "*/bad*" \
		--exclude "*/lib2to3/tests/data/*"

# To create the tarball, go to the parent of a clean cpython checkout,
# and run `tar cf cpython-lib.tgz cpython/Lib`.  (This will include
# non .py files that aren't needed, but they're harmless.)
cpython:
	tar xf data/cpython-lib.tgz

clean-cpython:
	-rm -rf cpython

mypy: regen-metaparser
	$(MYPY)  # For list of files, see mypy.ini

black: format-python

format-python:
	black pegen tatsu tests scripts

bench: cpython
	$(MAKE) -s test_global 2>/dev/null
	$(MAKE) -s test_global 2>/dev/null
	$(MAKE) -s test_global 2>/dev/null

# To install clang-format:
#    on mac: "brew install clang-format"
#    on ubuntu: "apt-get install clang-format"
#    on arch: "pacman -S clang"
format-c:
	clang-format peg_extension/peg_extension.c -i

# To install clang-tidy:
#    on mac:
#       "brew install llvm"
#       Then, create symlinks to the binaries. For example:
#       ln -s "$(brew --prefix llvm)/bin/clang-format" "/usr/local/bin/clang-format"
#       ln -s "$(brew --prefix llvm)/bin/clang-tidy" "/usr/local/bin/clang-tidy"
#    on ubuntu: "apt-get install clang-tidy"
#    on arch: "pacman -S clang"
clang-tidy:
	$(eval COMPILE_OPTIONS = $(shell python-config --cflags))
	clang-tidy peg_extension/peg_extension.c -fix-errors -fix -checks="readability-braces-around-statements" -- $(COMPILE_OPTIONS) 1>/dev/null

format: format-python format-c

find_max_nesting:
	$(PYTHON) scripts/find_max_nesting.py

tags: TAGS

TAGS: pegen/*.py tests/test_pegen.py
	etags pegen/*.py tests/test_pegen.py
