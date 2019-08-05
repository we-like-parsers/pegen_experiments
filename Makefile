TOP = /usr/local
PYTHON ?= $(TOP)/bin/python3.8

GRAMMAR = data/cprog.gram
TESTFILE = data/cprog.txt
TIMEFILE = data/xxl.txt

pegen/parse.c: $(GRAMMAR) pegen/*.py pegen/pegen.c pegen/*.h
	$(PYTHON) -m pegen -q -c $(GRAMMAR) -o pegen/parse.c --compile-extension

clean:
	-rm -f pegen/*.o pegen/*.so pegen/parse.c

dump: pegen/parse.c
	cat -n $(TESTFILE)
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse('$(TESTFILE)'); print(ast.dump(t))"

test: pegen/parse.c
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse('$(TESTFILE)'); exec(compile(t, '', 'exec'))"

time: pegen/parse.c
	/usr/bin/time -l $(PYTHON) -c "from pegen import parse; parse.parse('$(TIMEFILE)')"

time_stdlib:
	/usr/bin/time -l $(PYTHON) -c "import ast; ast.parse(open('$(TIMEFILE)').read())"

tags: TAGS

TAGS: pegen/*.py test/test_pegen.py
	etags pegen/*.py test/test_pegen.py
