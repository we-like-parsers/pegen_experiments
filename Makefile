TOP = /usr/local
PYTHON = $(TOP)/bin/python3.8
INCLUDES = -I$(TOP)/include/python3.8
LDFLAGS = -L$(TOP)/lib/python3.8/config-3.8-darwin -ldl
LDSHARED = $(CC) -bundle -undefined dynamic_lookup $(LDFLAGS)
CFLAGS = -Werror

GRAMMAR = data/cprog.gram
TESTFILE = data/cprog.txt
TIMEFILE = data/xxl.txt

pegen/parse.so: pegen/parse.o pegen/pegen.o
	$(LDSHARED) pegen/parse.o pegen/pegen.o -o pegen/parse.so

pegen/parse.o: pegen/parse.c pegen/pegen.h pegen/v38tokenizer.h
	$(CC) $(CFLAGS) -c $(INCLUDES) pegen/parse.c -o pegen/parse.o

pegen/pegen.o: pegen/pegen.c pegen/pegen.h
	$(CC) $(CFLAGS) -c $(INCLUDES) pegen/pegen.c -o pegen/pegen.o

pegen/parse.c: $(GRAMMAR) pegen/*.py
	$(PYTHON) -m pegen -q -c $(GRAMMAR) -o pegen/parse.c

clean:
	-rm -f pegen/*.o pegen/*.so pegen/parse.c

dump: pegen/parse.so
	cat -n $(TESTFILE)
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse('$(TESTFILE)'); print(ast.dump(t))"

test: pegen/parse.so
	$(PYTHON) -c "from pegen import parse; import ast; t = parse.parse('$(TESTFILE)'); exec(compile(t, '', 'exec'))"

time: pegen/parse.so
	/usr/bin/time -l $(PYTHON) -c "from pegen import parse; parse.parse('$(TIMEFILE)')"

time_stdlib:
	/usr/bin/time -l $(PYTHON) -c "import ast; ast.parse(open('$(TIMEFILE)').read())"

tags: TAGS

TAGS: pegen/*.py test/test_pegen.py
	etags pegen/*.py test/test_pegen.py
