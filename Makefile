TOP = /usr/local
INCLUDES = -I$(TOP)/include/python3.8
LDFLAGS = -L/usr/local/lib/python3.8/config-3.8-darwin -ldl
LDSHARED = $(CC) -bundle -undefined dynamic_lookup $(LDFLAGS)

parse.so: parse.o pegen.o
	$(LDSHARED) parse.o pegen.o -o parse.so

parse.o: pegen.h parse.c
	$(CC) -c $(INCLUDES) parse.c

pegen.o: pegen.h pegen.c
	$(CC) -c $(INCLUDES) pegen.c

parse.c: data/cexpr.gram pegen.py
	$(TOP)/bin/python3.8 pegen.py -c data/cexpr.gram -o parse.c

clean:
	rm *.o *.so parse.c
