PYTHON ?= `/usr/bin/which python3.8`
CPYTHON ?= "./cpython"

GRAMMAR = data/cprog.gram
TESTFILE = data/cprog.txt
TIMEFILE = data/xxl.txt
TESTDIR = .

build: pegen/parse.c

pegen/parse.c: $(GRAMMAR) pegen/*.py pegen/pegen.c pegen/*.h pegen/grammar_parser.py
	$(PYTHON) -m pegen -q -c $(GRAMMAR) -o pegen/parse.c --compile-extension

clean:
	-rm -f pegen/*.o pegen/*.so pegen/parse.c

dump: pegen/parse.c
	cat -n $(TESTFILE)
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse_file('$(TESTFILE)'); print(ast.dump(t))"

regen-metaparser: pegen/metagrammar.gram pegen/*.py
	$(PYTHON) -m pegen -q -c pegen/metagrammar.gram -o pegen/grammar_parser.py

# Note: These targets really depend on the generated shared object in pegen/parse.*.so but
# this has different names in different systems so we are abusing the implicit dependency on
# parse.c by the use of --compile-extension.

test: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; t = parse.parse_file('$(TESTFILE)'); exec(compile(t, '', 'exec'))"

compile: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; t = parse.parse_file('$(TESTFILE)')"

time: pegen/parse.c
	/usr/bin/time -l $(PYTHON) -c "from pegen import parse; parse.parse_file('$(TIMEFILE)')"

time_stdlib:
	/usr/bin/time -l $(PYTHON) -c "import ast; ast.parse(open('$(TIMEFILE)').read())"

simpy:
	$(PYTHON) scripts/test_parse_directory.py -g data/simpy.gram -d $(TESTDIR) --short

simpy_cpython:
	$(PYTHON) scripts/test_parse_directory.py \
		-g data/simpy.gram \
		-d $(CPYTHON) \
		--short \
		--exclude "*/test2to3/*" \
		--exclude "*/test2to3/**/*" \
		--exclude "*/bad*" \
		--exclude "*/lib2to3/tests/data/*"

mypy: regen-metaparser
	mypy  # For list of files, see mypy.ini

black:
	black pegen tatsu test test*.py scripts

tags: TAGS

TAGS: pegen/*.py test/test_pegen.py
	etags pegen/*.py test/test_pegen.py
