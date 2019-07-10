TOP = /usr/local
PYTHON = $(TOP)/bin/python3.8
INCLUDES = -I$(TOP)/include/python3.8
LDFLAGS = -L$(TOP)/lib/python3.8/config-3.8-darwin -ldl
LDSHARED = $(CC) -bundle -undefined dynamic_lookup $(LDFLAGS)
CFLAGS = -Werror

GRAMMAR = data/cexpr.gram

parse.so: parse.o pegen.o
	$(LDSHARED) parse.o pegen.o -o parse.so

parse.o: parse.c pegen.h v38tokenizer.h
	$(CC) $(CFLAGS) -c $(INCLUDES) parse.c

pegen.o: pegen.c pegen.h
	$(CC) $(CFLAGS) -c $(INCLUDES) pegen.c

parse.c: $(GRAMMAR) pegen.py
	$(PYTHON) pegen.py -c $(GRAMMAR) -o parse.c

clean:
	rm *.o *.so parse.c
