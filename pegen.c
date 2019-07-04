#include <Python.h>
#include "pegen.h"
#include "v38tokenizer.h"

// Here, mark is the start of the node, while p->mark is the end.
// If node==NULL, they should be the same.
void
insert_memo(Parser *p, int mark, int type, ASTptr node)
{
    // Insert in front
    Memo *m = PyArena_Malloc(p->arena, sizeof(Memo));
    if (m == NULL)
        panic("Out of arena space");  // TODO: How to handle malloc failures
    m->type = type;
    m->node = node;
    m->mark = p->mark;
    m->next = p->tokens[mark].memo;
    p->tokens[mark].memo = m;
}

int  // bool
is_memoized(Parser *p, int type, ASTptr *pres)
{
    Token *t = &p->tokens[p->mark];
    Memo *m;
    for (m = t->memo; m != NULL; m = m->next) {
        if (m->type == type) {
            if (m->node == NULL)
                return 0;
            p->mark = m->mark;
            *pres = m->node;
            return 1;
        }
    }
    return 0;
}

void
panic(char *message)
{
    fprintf(stderr, "panic: pgen-generated parser: %s\n", message);
    exit(2);
}

ASTptr
CONSTRUCTOR(Parser *p, ...)
{
    return (void *)1;
}

static void
fill_token(Parser *p)
{
    char *start, *end;
    int type = PyTokenizer_Get(p->tok, &start, &end);
    if (type == ERRORTOKEN)
        panic("Error token");

    if (p->fill == p->size) {
        int newsize = p->size * 2;
        p->tokens = realloc(p->tokens, newsize * sizeof(Token));
        if (p->tokens == NULL)
            panic("Realloc tokens failed");
        memset(p->tokens + p->size, '\0', (newsize - p->size) * sizeof(Token));
        p->size = newsize;
    }

    Token *t = p->tokens + p->fill;
    t->type = type;
    t->bytes = PyBytes_FromStringAndSize(start, end - start);
    if (t->bytes == NULL)
        panic("PyBytes_FromStringAndSize failed");

    // TODO: lineno etc.

    fprintf(stderr, "Filled: %d \"%s\"\n", type, PyBytes_AsString(t->bytes));
    p->fill += 1;
}

ASTptr
expect_token(Parser *p, int type)
{
    if (p->mark == p->fill)
        fill_token(p);
    Token *t = p->tokens + p->mark;
    if (t->type != type)
        return NULL;
    p->mark += 1;
    return t->bytes;
}

ASTptr
endmarker_token(Parser *p)
{
    return expect_token(p, ENDMARKER);
}

ASTptr
name_token(Parser *p)
{
    return expect_token(p, NAME);
}

ASTptr
newline_token(Parser *p)
{
    return expect_token(p, NEWLINE);
}

ASTptr
number_token(Parser *p)
{
    return expect_token(p, NUMBER);
}

int
run_parser(const char *filename, ASTptr(*start_rule_func)(Parser *))
{
    FILE *fp = fopen(filename, "rb");
    if (fp == NULL)
        panic("Can't open file");

    Parser *p = malloc(sizeof(Parser));
    if (p == NULL)
        panic("Out of memory for Parser");

    p->tok = PyTokenizer_FromFile(fp, NULL, NULL, NULL);
    if (p->tok == NULL)
        return 0;

    p->tokens = malloc(sizeof(Token));
    memset(p->tokens, '\0', sizeof(Token));
    p->mark = 0;
    p->fill = 0;
    p->size = 1;

    p->arena = PyArena_New();
    if (!p->arena)
        return 0;

    fill_token(p);

    void *res = (*start_rule_func)(p);
    if (res == NULL) {
        PyErr_Format(PyExc_SyntaxError, "error at mark %d, fill %d, size %d", p->mark, p->fill, p->size);
        return 0;
    }

    // TODO: Free stuff

    return 1;
}
