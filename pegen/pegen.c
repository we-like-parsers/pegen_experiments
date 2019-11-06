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
int
insert_memo(Parser *p, int mark, int type, void *node)
{
    // Insert in front
    Memo *m = PyArena_Malloc(p->arena, sizeof(Memo));
    if (m == NULL) {
        return -1;
    }
    m->type = type;
    m->node = node;
    m->mark = p->mark;
    m->next = p->tokens[mark].memo;
    p->tokens[mark].memo = m;
    return 0;
}

// Like insert_memo(), but updates an existing node if found.
int
update_memo(Parser *p, int mark, int type, void *node)
{
    for (Memo *m = p->tokens[mark].memo; m != NULL; m = m->next) {
        if (m->type == type) {
            // Update existing node.
            m->node = node;
            m->mark = p->mark;
            return 0;
        }
    }
    // Insert new node.
    return insert_memo(p, mark, type, node);
}

// Return dummy NAME.
void *
CONSTRUCTOR(Parser *p, ...)
{
    PyObject *id = PyUnicode_FromStringAndSize("", 0);
    if (id == NULL)
        return NULL;
    if (PyArena_AddPyObject(p->arena, id) < 0) {
        Py_DECREF(id);
        return NULL;
    }
    return Name(id, Load, 1, 0, 1, 0,p->arena);
}

static int
fill_token(Parser *p)
{
    char *start, *end;
    int type = PyTokenizer_Get(p->tok, &start, &end);
    if (type == ERRORTOKEN) {
        if (!PyErr_Occurred()) {
            PyErr_Format(PyExc_ValueError, "Error token");
            PyErr_Format(PyExc_SyntaxError, "Tokenizer returned error token");
            // There is no reliable column information for this error
            PyErr_SyntaxLocationObject(p->tok->filename, p->tok->lineno, 0);
        }
        return -1;
    }

    if (p->fill == p->size) {
        int newsize = p->size * 2;
        p->tokens = PyMem_Realloc(p->tokens, newsize * sizeof(Token));
        if (p->tokens == NULL) {
            PyErr_Format(PyExc_MemoryError, "Realloc tokens failed");
            return -1;
        }
        memset(p->tokens + p->size, '\0', (newsize - p->size) * sizeof(Token));
        p->size = newsize;
    }

    Token *t = p->tokens + p->fill;
    t->type = type;
    t->bytes = PyBytes_FromStringAndSize(start, end - start);
    if (t->bytes == NULL) {
        return -1;
    }
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
    return 0;
}

int  // bool
is_memoized(Parser *p, int type, void *pres)
{
    if (p->mark == p->fill) {
        if (fill_token(p) < 0) {
            return -1;
        }
    }

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
    return 0;
}

int
lookahead_with_string(int positive, void *(func)(Parser *, const char *), Parser *p, const char *arg)
{
    int mark = p->mark;
    void *res = func(p, arg);
    p->mark = mark;
    return (res != NULL) == positive;
}

int
lookahead_with_int(int positive, Token *(func)(Parser *, int), Parser *p, int arg)
{
    int mark = p->mark;
    void *res = func(p, arg);
    p->mark = mark;
    return (res != NULL) == positive;
}

int
lookahead(int positive, void *(func)(Parser *), Parser *p)
{
    int mark = p->mark;
    void *res = func(p);
    p->mark = mark;
    return (res != NULL) == positive;
}

Token *
expect_token(Parser *p, int type)
{
    if (p->mark == p->fill) {
        if (fill_token(p) < 0) {
            return NULL;
        }
    }
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
async_token(Parser *p)
{
    return expect_token(p, ASYNC);
}

void *
await_token(Parser *p)
{
    return expect_token(p, AWAIT);
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
        return NULL;
    PyObject *id = PyUnicode_DecodeUTF8(s, n, NULL);
    if (id == NULL)
        return NULL;
    if (PyArena_AddPyObject(p->arena, id) < 0) {
        Py_DECREF(id);
        return NULL;
    }
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
    // TODO: Just copy CPython's machinery for parsing numbers.
    PyObject *c = PyLong_FromString(PyBytes_AsString(t->bytes), (char **)0, 0);
    if (c == NULL) {
	PyErr_Clear();
        PyObject *tbytes = t->bytes;
        Py_ssize_t size = PyBytes_Size(tbytes);
        char *bytes = PyBytes_AsString(tbytes);
        char lastc = size == 0 ? 0 : bytes[size - 1];
        int iscomplex = 0;
        PyObject *obytes = NULL;
        if (size > 0 && (lastc == 'j' || lastc == 'J')) {
            iscomplex = 1;
            obytes = PyBytes_FromStringAndSize(bytes, size - 1);
            if (obytes == NULL)
                return NULL;
            tbytes = obytes;
        }
	c = PyFloat_FromString(tbytes);
        Py_XDECREF(obytes);
	if (c == NULL)
	    return NULL;
        if (iscomplex) {
            double real = PyFloat_AsDouble(c);
            double imag = 0;
            Py_DECREF(c);
            c = PyComplex_FromDoubles(real, imag);
            if (c == NULL)
                return NULL;
        }
    }
    if (PyArena_AddPyObject(p->arena, c) < 0) {
        Py_DECREF(c);
        return NULL;
    }
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
        return NULL;
    // Strip quotes.
    // TODO: Properly handle all forms of string quotes and backslashes.
    PyObject *c = PyUnicode_FromStringAndSize(s+1, len-2);
    if (!c)
        return NULL;
    if (PyArena_AddPyObject(p->arena, c) < 0) {
        Py_DECREF(c);
        return NULL;
    }
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
    if (p == NULL) {
        PyErr_Format(PyExc_MemoryError, "Out of memory for Parser");
        goto exit;
    }
    assert(tok != NULL);
    p->tok = tok;
    p->tokens = PyMem_Malloc(sizeof(Token));
    if (!p->tokens) {
        PyErr_Format(PyExc_MemoryError, "Out of memory for tokens");
        goto exit;
    }
    memset(p->tokens, '\0', sizeof(Token));
    p->mark = 0;
    p->fill = 0;
    p->size = 1;

    p->arena = PyArena_New();
    if (!p->arena) {
        goto exit;
    }

    if (fill_token(p) < 0) {
        goto exit;
    }

    PyErr_Clear();

    void *res = (*start_rule_func)(p);
    if (res == NULL) {
        if (PyErr_Occurred()) {
            goto exit;
        }
        if (p->fill == 0) {
            PyErr_Format(PyExc_SyntaxError, "error at start before reading any input");
            PyErr_SyntaxLocationObject(p->tok->filename, 1, 1);
        }
        else {
            Token *t = p->tokens + p->fill - 1;
	    // TODO: comvert from bytes offset to character offset
	    // TODO: set correct attributes on SyntaxError object
            PyErr_Format(PyExc_SyntaxError, "error at line %d, col %d, token %s",
                         t->line, t->col + 1, token_name(t->type));
            PyErr_SyntaxLocationObject(p->tok->filename, t->line, t->col + 1);
        }
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
    if (fp == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, filename);
        return NULL;
    }

    PyObject *filename_ob = NULL;
    if ((filename_ob = PyUnicode_FromString(filename)) == NULL)
        return NULL;

    // From here on we need to clean up even if there's an error
    PyObject *result = NULL;

    struct tok_state* tok = PyTokenizer_FromFile(fp, NULL, NULL, NULL);
    if (tok == NULL)
        goto error;

    // Transfers ownership
    tok->filename = filename_ob;
    filename_ob = NULL;

    result = run_parser(tok, start_rule_func, mode);

    PyTokenizer_Free(tok);

 error:
    fclose(fp);
    Py_XDECREF(filename_ob);
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
    if (!seq) {
        return NULL;
    }
    asdl_seq_SET(seq, 0, a);
    return seq;
}

asdl_seq *
seq_insert_in_front(Parser *p, void *a, asdl_seq *seq)
{
    if (!seq) {
        return singleton_seq(p, a);
    }

    asdl_seq *new_seq = _Py_asdl_seq_new(asdl_seq_LEN(seq) + 1, p->arena);
    if (!new_seq) {
        return NULL;
    }

    asdl_seq_SET(new_seq, 0, a);
    for (int i = 1, l = asdl_seq_LEN(new_seq); i < l; i++) {
        asdl_seq_SET(new_seq, i, asdl_seq_GET(seq, i-1));
    }
    return new_seq;
}

int
get_flattened_seq_size(asdl_seq *seqs)
{
    int size = 0;
    for (int i = 0, l = asdl_seq_LEN(seqs); i < l; i++) {
        asdl_seq *inner_seq = asdl_seq_GET(seqs, i);

        // This following exclusion is needed, in order to correctly
        // handle the void pointers generated by the CONSTRUCTOR
        // function above.
        if (asdl_seq_GET(inner_seq, 0) == (void *) 1) continue;

        size += asdl_seq_LEN(inner_seq);
    }
    return size;
}

asdl_seq *
seq_flatten(Parser *p, asdl_seq *seqs)
{
    int flattened_seq_size = get_flattened_seq_size(seqs);
    asdl_seq *flattened_seq = _Py_asdl_seq_new(flattened_seq_size, p->arena);
    if (!flattened_seq) {
        return NULL;
    }

    int flattened_seq_idx = 0;
    for (int i = 0, l = asdl_seq_LEN(seqs); i < l; i++) {
        asdl_seq *inner_seq = asdl_seq_GET(seqs, i);

        // This following exclusion is needed, in order to correctly
        // handle the void pointers generated by the CONSTRUCTOR
        // function above.
        if (asdl_seq_GET(inner_seq, 0) == (void *) 1) continue;

        for (int j = 0, li = asdl_seq_LEN(inner_seq); j < li; j++) {
            asdl_seq_SET(flattened_seq, flattened_seq_idx++, asdl_seq_GET(inner_seq, j));
        }
    }
    assert(flattened_seq_idx == flattened_seq_size);

    return flattened_seq;
}

expr_ty
seq_to_dotted_name(Parser *p, asdl_seq *seq)
{
    if (!seq) {
        return NULL;
    }

    expr_ty final_name = asdl_seq_GET(seq, 0);
    for (int i = 1, l = asdl_seq_LEN(seq); i < l; i++) {
        expr_ty name = asdl_seq_GET(seq, i);
        final_name = _Py_Attribute(final_name, get_identifier_from_expr_ty(name), Load, EXTRA(final_name, name));
    }

    return final_name;
}

identifier
get_identifier_from_expr_ty(expr_ty expr)
{
    if (expr->kind == Attribute_kind) {
        return expr->v.Attribute.attr;
    }
    if (expr->kind == Name_kind) {
        return expr->v.Name.id;
    }

    return NULL;
}
