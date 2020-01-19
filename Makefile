PYTHON ?= `/usr/bin/which python3.8`
CPYTHON ?= "./cpython"
MYPY ?= `/usr/bin/which mypy`

GRAMMAR = data/simpy.gram
TESTFILE = data/cprog.txt
TIMEFILE = data/xxl.txt
TESTDIR = .
TESTFLAGS = --short

build: pegen/parse.c

pegen/parse.c: $(GRAMMAR) pegen/*.py pegen/pegen.c pegen/*.h pegen/grammar_parser.py
	$(PYTHON) -m pegen -q -c $(GRAMMAR) -o pegen/parse.c --compile-extension

clean:
	-rm -f pegen/*.o pegen/*.so pegen/parse.c

dump: pegen/parse.c
	cat -n $(TESTFILE)
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse_file('$(TESTFILE)', mode=1); print(ast.dump(t))"

regen-metaparser: pegen/metagrammar.gram pegen/*.py
	$(PYTHON) -m pegen -q -c pegen/metagrammar.gram -o pegen/grammar_parser.py

# Note: These targets really depend on the generated shared object in pegen/parse.*.so but
# this has different names in different systems so we are abusing the implicit dependency on
# parse.c by the use of --compile-extension.

.PHONY: test

test: run

run: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; t = parse.parse_file('$(TESTFILE)'); exec(t)"

compile: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; t = parse.parse_file('$(TESTFILE)', mode=2)"

parse: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; t = parse.parse_file('$(TESTFILE)', mode=1)"

check: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; t = parse.parse_file('$(TESTFILE)', mode=0)"

time: time_compile

time_compile: pegen/parse.c
	/usr/bin/time -l $(PYTHON) -c "from pegen import parse; parse.parse_file('$(TIMEFILE)', mode=2)"

time_parse: pegen/parse.c
	/usr/bin/time -l $(PYTHON) -c "from pegen import parse; parse.parse_file('$(TIMEFILE)', mode=1)"

time_check: pegen/parse.c
	/usr/bin/time -l $(PYTHON) -c "from pegen import parse; parse.parse_file('$(TIMEFILE)', mode=0)"

time_stdlib: time_stdlib_compile

time_stdlib_compile:
	/usr/bin/time -l $(PYTHON) -c "import ast; compile(open('$(TIMEFILE)').read(), '$(TIMEFILE)', 'exec')"

time_stdlib_parse:
	/usr/bin/time -l $(PYTHON) -c "import ast; ast.parse(open('$(TIMEFILE)').read())"

simpy:
	$(PYTHON) scripts/test_parse_directory.py \
		-g data/simpy.gram \
		-d $(TESTDIR) \
		$(TESTFLAGS) \
		--exclude "*/failset/*" \
		--exclude "*/failset/**" \
		--exclude "*/failset/**/*"

simpy_cpython:
	$(PYTHON) scripts/test_parse_directory.py \
		-g data/simpy.gram \
		-d $(CPYTHON) \
		$(TESTFLAGS) \
		--exclude "*/test2to3/*" \
		--exclude "*/test2to3/**/*" \
		--exclude "*/bad*" \
		--exclude "*/lib2to3/tests/data/*"

mypy: regen-metaparser
	$(MYPY)  # For list of files, see mypy.ini

black:
	black pegen tatsu test scripts

find_max_nesting:
	$(PYTHON) scripts/find_max_nesting.py

tags: TAGS

TAGS: pegen/*.py test/test_pegen.py
	etags pegen/*.py test/test_pegen.py
