#include <Python.h>
#include "pegen.h"
#include "v38tokenizer.h"

static const char *
token_name(int type)
{
    if (0 <= type && type <= N_TOKENS)
        return _PyParser_TokenNames[type];
    return "<Huh?>";
}

// Here, mark is the start of the node, while p->mark is the end.
// If node==NULL, they should be the same.
void
insert_memo(Parser *p, int mark, int type, void *node)
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

// Like insert_memo(), but updates an existing node if found.
void
update_memo(Parser *p, int mark, int type, void *node)
{
    for (Memo *m = p->tokens[mark].memo; m != NULL; m = m->next) {
        if (m->type == type) {
            // Update existing node.
            m->node = node;
            m->mark = p->mark;
            return;
        }
    }
    // Insert new node.
    insert_memo(p, mark, type, node);
}

void
panic(char *message)
{
    fprintf(stderr, "panic: pgen-generated parser: %s\n", message);
    exit(2);
}

void *
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
        p->tokens = PyMem_Realloc(p->tokens, newsize * sizeof(Token));
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
    PyArena_AddPyObject(p->arena, t->bytes);

    int lineno = type == STRING ? p->tok->first_lineno : p->tok->lineno;
    const char *line_start = type == STRING ? p->tok->multi_line_start : p->tok->line_start;
    int end_lineno = p->tok->lineno;
    int col_offset = -1, end_col_offset = -1;
    if (start != NULL && start >= line_start)
        col_offset = start - line_start;
    if (end != NULL && end >= p->tok->line_start)
        end_col_offset = end - p->tok->line_start;

    t->line = lineno;
    t->col = col_offset;
    t->endline = end_lineno;
    t->endcol = end_col_offset;

    // if (p->fill % 100 == 0) fprintf(stderr, "Filled at %d: %s \"%s\"\n", p->fill, token_name(type), PyBytes_AsString(t->bytes));
    p->fill += 1;
}

int  // bool
is_memoized(Parser *p, int type, void *pres)
{
    if (p->mark == p->fill)
        fill_token(p);

    Token *t = &p->tokens[p->mark];

    for (Memo *m = t->memo; m != NULL; m = m->next) {
        if (m->type == type) {
            p->mark = m->mark;
            *(void **)(pres) = m->node;
            // fprintf(stderr, "%d < %d: memoized!\n", p->mark, p->fill);
            return 1;
        }
    }
    // fprintf(stderr, "%d < %d: not memoized\n", p->mark, p->fill);
    return 0; }

Token *
expect_token(Parser *p, int type)
{
    if (p->mark == p->fill)
        fill_token(p);
    Token *t = p->tokens + p->mark;
    if (t->type != type) {
        // fprintf(stderr, "No %s at %d\n", token_name(type), p->mark);
        return NULL;
    }
    p->mark += 1;
    // fprintf(stderr, "Got %s at %d: %s\n", token_name(type), p->mark, PyBytes_AsString(t->bytes));
    return t;
}

void *
endmarker_token(Parser *p)
{
    return expect_token(p, ENDMARKER);
}

expr_ty
name_token(Parser *p)
{
    Token *t = expect_token(p, NAME);
    if (t == NULL)
        return NULL;
    char *s;
    Py_ssize_t n;
    if (PyBytes_AsStringAndSize(t->bytes, &s, &n) < 0)
        panic("bytes");
    PyObject *id = PyUnicode_DecodeUTF8(s, n, NULL);
    if (id == NULL)
        panic("unicode");
    PyArena_AddPyObject(p->arena, id);
    // TODO: What new_identifier() does.
    return Name(id, Load, t->line, t->col, t->endline, t->endcol, p->arena);
}

void *
newline_token(Parser *p)
{
    return expect_token(p, NEWLINE);
}

void *
indent_token(Parser *p)
{
    return expect_token(p, INDENT);
}

void *
dedent_token(Parser *p)
{
    return expect_token(p, DEDENT);
}

expr_ty
number_token(Parser *p)
{
    Token *t = expect_token(p, NUMBER);
    if (t == NULL)
        return NULL;
    // TODO: Check for float, complex.
    PyObject *c = PyLong_FromString(PyBytes_AsString(t->bytes), (char **)0, 0);
    if (c == NULL)
        panic("long");
    PyArena_AddPyObject(p->arena, c);
    return Constant(c, NULL, t->line, t->col, t->endline, t->endcol, p->arena);
}

expr_ty
string_token(Parser *p)
{
    Token *t = expect_token(p, STRING);
    if (t == NULL)
        return NULL;
    char *s = NULL;
    Py_ssize_t len = 0;
    if (PyBytes_AsStringAndSize(t->bytes, &s, &len) < 0)
        panic("bytes");
    // Strip quotes.
    // TODO: Properly handle all forms of string quotes and backslashes.
    PyObject *c = PyUnicode_FromStringAndSize(s+1, len-2);
    if (!c)
        panic("string");
    PyArena_AddPyObject(p->arena, c);
    return Constant(c, NULL, t->line, t->col, t->endline, t->endcol, p->arena);
}

void *
keyword_token(Parser *p, const char *val)
{
    int mark = p->mark;
    Token *t = expect_token(p, NAME);
    if (t == NULL)
        return NULL;
    if (strcmp(val, PyBytes_AsString(t->bytes)) == 0)
        return t;
    p->mark = mark;
    return NULL;
}

PyObject *
run_parser(struct tok_state* tok, void *(start_rule_func)(Parser *), int mode)
{
    PyObject* result = NULL;
    Parser *p = PyMem_Malloc(sizeof(Parser));
    if (p == NULL)
        panic("Out of memory for Parser");

    assert(tok != NULL);
    p->tok = tok;
    p->tokens = PyMem_Malloc(sizeof(Token));
    if (!p->tokens)
        panic("Out of memory for tokens");
    memset(p->tokens, '\0', sizeof(Token));
    p->mark = 0;
    p->fill = 0;
    p->size = 1;

    p->arena = PyArena_New();
    if (!p->arena) {
        goto exit;
    }

    fill_token(p);

    void *res = (*start_rule_func)(p);
    if (res == NULL) {
        PyErr_Format(PyExc_SyntaxError, "error at mark %d, fill %d, size %d", p->mark, p->fill, p->size);
        goto exit;
    }

    if (mode == 1) {
        result =  PyAST_mod2obj(res);
    } else {
        result = Py_None;
        Py_INCREF(result);
    }

exit:

    PyMem_Free(p->tokens);
    if (p->arena != NULL) {
        PyArena_Free(p->arena);
    }
    PyMem_Free(p);
    return result;
}

PyObject *
run_parser_from_file(const char *filename, void *(start_rule_func)(Parser *), int mode)
{
    FILE *fp = fopen(filename, "rb");
    if (fp == NULL)
        panic("Can't open file");

    struct tok_state* tok = PyTokenizer_FromFile(fp, NULL, NULL, NULL);

    if (tok == NULL)
        return NULL;

    PyObject* result = run_parser(tok, start_rule_func, mode);
    PyTokenizer_Free(tok);
    return result;
}

PyObject *
run_parser_from_string(const char* str, void *(start_rule_func)(Parser *), int mode)
{
    struct tok_state* tok = PyTokenizer_FromString(str, 1);

    if (tok == NULL)
        return NULL;

    PyObject* result = run_parser(tok, start_rule_func, mode);
    PyTokenizer_Free(tok);
    return result;
}

asdl_seq *
singleton_seq(Parser *p, void *a)
{
    asdl_seq *seq = _Py_asdl_seq_new(1, p->arena);
    if (!seq) panic("_Py_asdl_seq_new");
    asdl_seq_SET(seq, 0, a);
    return seq;
}
