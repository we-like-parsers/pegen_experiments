TOP = /usr/local
INCLUDES = -I$(TOP)/include/python3.8

parse: parse.o pegen.o
	$(CC) parse.o pegen.o -o parse

parse.o: pegen.h parse.c
	$(CC) -c $(INCLUDES) parse.c

pegen.o: pegen.h pegen.c
	$(CC) -c $(INCLUDES) pegen.c

parse.c: data/cexpr.gram pegen.py
	$(TOP)/bin/python3.8 pegen.py -c data/cexpr.gram -o parse.c
