TOP = /usr/local
PYTHON ?= $(TOP)/bin/python3.8

GRAMMAR = data/cprog.gram
TESTFILE = data/cprog.txt
TIMEFILE = data/xxl.txt
TESTDIR = .

pegen/parse.c: $(GRAMMAR) pegen/*.py pegen/pegen.c pegen/*.h
	$(PYTHON) -m pegen -q -c $(GRAMMAR) -o pegen/parse.c --compile-extension

clean:
	-rm -f pegen/*.o pegen/*.so pegen/parse.c

dump: pegen/parse.c
	cat -n $(TESTFILE)
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse_file('$(TESTFILE)'); print(ast.dump(t))"

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
	$(PYTHON) test_parse_directory.py -g data/simpy.gram -d $(TESTDIR)

tags: TAGS

TAGS: pegen/*.py test/test_pegen.py
	etags pegen/*.py test/test_pegen.py
