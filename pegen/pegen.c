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
    m->next = p->tokens[mark]->memo;
    p->tokens[mark]->memo = m;
    return 0;
}

// Like insert_memo(), but updates an existing node if found.
int
update_memo(Parser *p, int mark, int type, void *node)
{
    for (Memo *m = p->tokens[mark]->memo; m != NULL; m = m->next) {
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
        p->tokens = PyMem_Realloc(p->tokens, newsize * sizeof(Token *));
        if (p->tokens == NULL) {
            PyErr_Format(PyExc_MemoryError, "Realloc tokens failed");
            return -1;
        }
        for (int i = p->size; i < newsize; i++) {
            p->tokens[i] = PyMem_Malloc(sizeof(Token));
            memset(p->tokens[i], '\0', sizeof(Token));
        }
        p->size = newsize;
    }

    Token *t = p->tokens[p->fill];
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

    t->lineno = lineno;
    t->col_offset = col_offset;
    t->end_lineno = end_lineno;
    t->end_col_offset = end_col_offset;

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

    Token *t = p->tokens[p->mark];

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
    Token *t = p->tokens[p->mark];
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
    return Name(id, Load, t->lineno, t->col_offset, t->end_lineno, t->end_col_offset, p->arena);
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
    return Constant(c, NULL, t->lineno, t->col_offset, t->end_lineno, t->end_col_offset, p->arena);
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
    return Constant(c, NULL, t->lineno, t->col_offset, t->end_lineno, t->end_col_offset, p->arena);
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
    p->tokens = PyMem_Malloc(sizeof(Token *));
    if (!p->tokens) {
        PyErr_Format(PyExc_MemoryError, "Out of memory for tokens");
        goto exit;
    }
    p->tokens[0] = PyMem_Malloc(sizeof(Token));
    memset(p->tokens[0], '\0', sizeof(Token));
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
            Token *t = p->tokens[p->fill - 1];
	    // TODO: comvert from bytes offset to character offset
	    // TODO: set correct attributes on SyntaxError object
            PyErr_Format(PyExc_SyntaxError, "error at line %d, col %d, token %s",
                         t->lineno, t->col_offset + 1, token_name(t->type));
            PyErr_SyntaxLocationObject(p->tok->filename, t->lineno, t->col_offset + 1);
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

    for (int i = 0; i < p->size; i++) {
        PyMem_Free(p->tokens[i]);
    }
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

/* Creates a single-element asdl_seq* that contains a */
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

/* Creates a copy of seq and prepends a to it */
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
_get_flattened_seq_size(asdl_seq *seqs)
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

/* Flattens an asdl_seq* of asdl_seq*s */
asdl_seq *
seq_flatten(Parser *p, asdl_seq *seqs)
{
    int flattened_seq_size = _get_flattened_seq_size(seqs);
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

/* Creates a new name of the form <first_name>.<second_name> */
expr_ty
join_names_with_dot(Parser *p, expr_ty first_name, expr_ty second_name)
{
    PyObject *first_identifier = first_name->v.Name.id;
    PyObject *second_identifier = second_name->v.Name.id;

    if (PyUnicode_READY(first_identifier) == -1) {
        return NULL;
    }
    if (PyUnicode_READY(second_identifier) == -1) {
        return NULL;
    }
    const char *first_str = PyUnicode_AsUTF8(first_identifier);
    if (!first_str) {
        return NULL;
    }
    const char *second_str = PyUnicode_AsUTF8(second_identifier);
    if (!second_str) {
        return NULL;
    }
    ssize_t len = strlen(first_str) + strlen(second_str) + 1; // +1 for the dot

    PyObject *str = PyBytes_FromStringAndSize(NULL, len);
    if (!str) {
        return NULL;
    }

    char *s = PyBytes_AS_STRING(str);
    if (!s) {
        return NULL;
    }

    strcpy(s, first_str);
    s += strlen(first_str);
    *s++ = '.';
    strcpy(s, second_str);
    s += strlen(second_str);
    *s = '\0';

    PyObject *uni = PyUnicode_DecodeUTF8(PyBytes_AS_STRING(str),
                                         PyBytes_GET_SIZE(str),
                                         NULL);
    Py_DECREF(str);
    if (!uni) {
        return NULL;
    }
    PyUnicode_InternInPlace(&uni);
    if (PyArena_AddPyObject(p->arena, uni) < 0) {
        Py_DECREF(uni);
        return NULL;
    }

    return Name(uni,
                Load,
                first_name->lineno,
                first_name->col_offset,
                second_name->end_lineno,
                second_name->end_col_offset,
                p->arena);
}

/* Counts the total number of dots in seq's tokens */
int
seq_count_dots(asdl_seq *seq)
{
    int number_of_dots = 0;
    for (int i = 0, l = asdl_seq_LEN(seq); i < l; i++) {
        Token *current_expr = asdl_seq_GET(seq, i);
        if (current_expr->type == ELLIPSIS) {
            number_of_dots += 3;
        } else if (current_expr->type == DOT) {
            number_of_dots += 1;
        } else {
            return -1;
        }
    }

    return number_of_dots;
}

/* Creates an alias with '*' as the identifier name */
alias_ty
alias_for_star(Parser *p)
{
    PyObject *str = PyUnicode_InternFromString("*");
    if (!str)
        return NULL;
    if (PyArena_AddPyObject(p->arena, str) < 0) {
        Py_DECREF(str);
        return NULL;
    }
    return alias(str, NULL, p->arena);
}

/* Returns the last element of seq or previous if seq is empty */
void *
seq_get_tail(void *previous, asdl_seq *seq)
{
    if (asdl_seq_LEN(seq) == 0) {
        return previous;
    }
    return asdl_seq_GET(seq, asdl_seq_LEN(seq) - 1);
}

/* Constructs a PegenAlias */
PegenAlias *
pegen_alias(alias_ty alias,
            int lineno,
            int col_offset,
            int end_lineno,
            int end_col_offset,
            PyArena *arena)
{
    PegenAlias *a = PyArena_Malloc(arena, sizeof(PegenAlias));
    if (!a) {
        return NULL;
    }
    a->alias = alias;
    a->lineno = lineno;
    a->col_offset = col_offset;
    a->end_lineno = end_lineno;
    a->end_col_offset = end_col_offset;
    return a;
}

/* Extracts alias_ty's from an asdl_seq* of PegenAlias*s */
asdl_seq *
extract_orig_aliases(Parser *p, asdl_seq *seq)
{
    int len = asdl_seq_LEN(seq);
    asdl_seq *new_seq = _Py_asdl_seq_new(len, p->arena);
    for (int i = 0; i < len; i++) {
        PegenAlias *a = asdl_seq_GET(seq, i);
        asdl_seq_SET(new_seq, i, a->alias);
    }
    return new_seq;
}

/* Creates a new asdl_seq* with the identifiers of all the names in seq */
asdl_seq *
map_names_to_ids(Parser *p, asdl_seq *seq)
{
    int len = asdl_seq_LEN(seq);
    asdl_seq *new_seq = _Py_asdl_seq_new(len, p->arena);
    for (int i = 0; i < len; i++) {
        expr_ty e = asdl_seq_GET(seq, i);
        asdl_seq_SET(new_seq, i, e->v.Name.id);
    }
    return new_seq;
}

/* Constructs a CmpopExprPair */
CmpopExprPair *
cmpop_expr_pair(Parser *p, cmpop_ty cmpop, expr_ty expr)
{
    CmpopExprPair *a = PyArena_Malloc(p->arena, sizeof(CmpopExprPair));
    if (!a) {
        return NULL;
    }
    a->cmpop = cmpop;
    a->expr = expr;
    return a;
}

asdl_int_seq *
_get_cmpops(Parser *p, asdl_seq *seq)
{
    int len = asdl_seq_LEN(seq);
    asdl_int_seq *new_seq = _Py_asdl_int_seq_new(len, p->arena);
    for (int i = 0; i < len; i++) {
        CmpopExprPair *pair = asdl_seq_GET(seq, i);
        asdl_seq_SET(new_seq, i, pair->cmpop);
    }
    return new_seq;
}

asdl_seq *
_get_exprs(Parser *p, asdl_seq *seq)
{
    int len = asdl_seq_LEN(seq);
    asdl_seq *new_seq = _Py_asdl_seq_new(len, p->arena);
    for (int i = 0; i < len; i++) {
        CmpopExprPair *pair = asdl_seq_GET(seq, i);
        asdl_seq_SET(new_seq, i, pair->expr);
    }
    return new_seq;
}

/* Wrapper for _Py_Compare, so that the call in the grammar stays concise */
expr_ty
Pegen_Compare(Parser *p, expr_ty expr, asdl_seq *pairs)
{
    return _Py_Compare(expr,
                       _get_cmpops(p, pairs),
                       _get_exprs(p, pairs),
                       EXTRA_EXPR(expr, ((CmpopExprPair *) seq_get_tail(NULL, pairs))->expr));
}

/* Accepts a load name and creates an identical store name */
expr_ty
store_name(Parser *p, expr_ty load_name)
{
    if (!load_name) {
        return NULL;
    }
    return _Py_Name(load_name->v.Name.id,
                    Store,
                    EXTRA_EXPR(load_name, load_name));
}

expr_ty
_del_name(Parser *p, expr_ty load_name)
{
    return _Py_Name(load_name->v.Name.id,
                    Del,
                    EXTRA_EXPR(load_name, load_name));
}

/* Creates an asdl_seq* where all the elements have been changed to have del as context */
asdl_seq *
map_targets_to_del_names(Parser *p, asdl_seq *seq)
{
    int len = asdl_seq_LEN(seq);
    asdl_seq *new_seq = _Py_asdl_seq_new(len, p->arena);
    for (int i = 0; i < len; i++) {
        expr_ty e = asdl_seq_GET(seq, i);
        assert(e->kind == Name_kind || e->kind == Tuple_kind || e->kind == List_kind); // For now!
        if (e->kind == Name_kind) {
            asdl_seq_SET(new_seq, i, _del_name(p, e));
        } else if (e->kind == Tuple_kind) {
            asdl_seq_SET(new_seq, i, _Py_Tuple(map_targets_to_del_names(p, e->v.Tuple.elts),
                                               Del,
                                               EXTRA_EXPR(e, e)));
        } else if (e->kind == List_kind) {
            asdl_seq_SET(new_seq, i, _Py_List(map_targets_to_del_names(p, e->v.List.elts),
                                              Del,
                                              EXTRA_EXPR(e, e)));
        }
    }
    return new_seq;
}

/* Constructs a NameDefaultPair */
NameDefaultPair *
name_default_pair(Parser *p, arg_ty arg, expr_ty value)
{
    NameDefaultPair *a = PyArena_Malloc(p->arena, sizeof(NameDefaultPair));
    if (!a) {
        return NULL;
    }
    a->arg = arg;
    a->value = value;
    return a;
}

/* Constructs a SlashWithDefault */
SlashWithDefault *
slash_with_default(Parser *p, asdl_seq *plain_names, asdl_seq *names_with_defaults)
{
    SlashWithDefault *a = PyArena_Malloc(p->arena, sizeof(SlashWithDefault));
    if (!a) {
        return NULL;
    }
    a->plain_names = plain_names;
    a->names_with_defaults = names_with_defaults;
    return a;
}

/* Constructs a StarEtc */
StarEtc *
star_etc(Parser *p, arg_ty vararg, asdl_seq *kwonlyargs, arg_ty kwarg)
{
    StarEtc *a = PyArena_Malloc(p->arena, sizeof(StarEtc));
    if (!a) {
        return NULL;
    }
    a->vararg = vararg;
    a->kwonlyargs = kwonlyargs;
    a->kwarg = kwarg;
    return a;
}

asdl_seq *
_join_seqs(Parser *p, asdl_seq *a, asdl_seq *b)
{
    int first_len = asdl_seq_LEN(a);
    int second_len = asdl_seq_LEN(b);
    asdl_seq *new_seq = _Py_asdl_seq_new(first_len + second_len, p->arena);
    if (!new_seq) {
        return NULL;
    }

    int k = 0;
    for (int i = 0; i < first_len; i++) {
        asdl_seq_SET(new_seq, k++, asdl_seq_GET(a, i));
    }
    for (int i = 0; i < second_len; i++) {
        asdl_seq_SET(new_seq, k++, asdl_seq_GET(b, i));
    }

    return new_seq;
}

asdl_seq *
_get_names(Parser *p, asdl_seq *names_with_defaults)
{
    int len = asdl_seq_LEN(names_with_defaults);
    asdl_seq *seq = _Py_asdl_seq_new(len, p->arena);
    if (!seq) {
        return NULL;
    }
    for (int i = 0; i < len; i++) {
        NameDefaultPair *pair = asdl_seq_GET(names_with_defaults, i);
        asdl_seq_SET(seq, i, pair->arg);
    }
    return seq;
}

asdl_seq *
_get_defaults(Parser *p, asdl_seq *names_with_defaults)
{
    int len = asdl_seq_LEN(names_with_defaults);
    asdl_seq *seq = _Py_asdl_seq_new(len, p->arena);
    if (!seq) {
        return NULL;
    }
    for (int i = 0; i < len; i++) {
        NameDefaultPair *pair = asdl_seq_GET(names_with_defaults, i);
        asdl_seq_SET(seq, i, pair->value);
    }
    return seq;
}

/* Constructs an arguments_ty object out of all the parsed constructs in the parameters rule */
arguments_ty
make_arguments(Parser *p, asdl_seq *slash_without_default, SlashWithDefault *slash_with_default,
               asdl_seq *plain_names, asdl_seq *names_with_default, StarEtc *star_etc)
{
    asdl_seq *posonlyargs;
    if (slash_without_default != NULL) {
        posonlyargs = slash_without_default;
    } else if (slash_with_default != NULL) {
        asdl_seq *slash_with_default_names = _get_names(p, slash_with_default->names_with_defaults);
        if (!slash_with_default_names) {
            return NULL;
        }
        posonlyargs = _join_seqs(p,
                                 slash_with_default->plain_names,
                                 slash_with_default_names);
        if (!posonlyargs) {
            return NULL;
        }
    } else {
        posonlyargs = _Py_asdl_seq_new(0, p->arena);
        if (!posonlyargs) {
            return NULL;
        }
    }

    asdl_seq *posargs;
    if (plain_names != NULL && names_with_default != NULL) {
        asdl_seq *names_with_default_names = _get_names(p, names_with_default);
        if (!names_with_default_names) {
            return NULL;
        }
        posargs = _join_seqs(p,
                             plain_names,
                             names_with_default_names);
        if (!posargs) {
            return NULL;
        }
    } else if (plain_names == NULL && names_with_default != NULL) {
        posargs = _get_names(p, names_with_default);
        if (!posargs) {
            return NULL;
        }
    } else if (plain_names != NULL && names_with_default == NULL) {
        posargs = plain_names;
    } else {
        posargs = _Py_asdl_seq_new(0, p->arena);
        if (!posargs) {
            return NULL;
        }
    }

    asdl_seq *posdefaults;
    if (slash_with_default != NULL && names_with_default != NULL) {
        asdl_seq *slash_with_default_values = _get_defaults(
            p,
            slash_with_default->names_with_defaults
        );
        if (!slash_with_default_values) {
            return NULL;
        }
        asdl_seq *names_with_default_values = _get_defaults(
            p,
            names_with_default
        );
        if (!names_with_default_values) {
            return NULL;
        }
        posdefaults = _join_seqs(p,
                                 slash_with_default_values,
                                 names_with_default_values);
        if (!posdefaults) {
            return NULL;
        }
    } else if (slash_with_default == NULL && names_with_default != NULL) {
        posdefaults = _get_defaults(p, names_with_default);
        if (!posdefaults) {
            return NULL;
        }
    } else if (slash_with_default != NULL && names_with_default == NULL) {
        posdefaults = _get_defaults(p, slash_with_default->names_with_defaults);
        if (!posdefaults) {
            return NULL;
        }
    } else {
        posdefaults = _Py_asdl_seq_new(0, p->arena);
        if (!posdefaults) {
            return NULL;
        }
    }

    arg_ty vararg = NULL;
    if (star_etc != NULL && star_etc->vararg != NULL) {
        vararg = star_etc->vararg;
    }

    asdl_seq *kwonlyargs;
    if (star_etc != NULL && star_etc->kwonlyargs != NULL) {
        kwonlyargs = _get_names(p, star_etc->kwonlyargs);
        if (!kwonlyargs) {
            return NULL;
        }
    } else {
        kwonlyargs = _Py_asdl_seq_new(0, p->arena);
        if (!kwonlyargs) {
            return NULL;
        }
    }

    asdl_seq *kwdefaults;
    if (star_etc != NULL && star_etc->kwonlyargs != NULL) {
        kwdefaults = _get_defaults(p, star_etc->kwonlyargs);
        if (!kwdefaults) {
            return NULL;
        }
    } else {
        kwdefaults = _Py_asdl_seq_new(0, p->arena);
        if (!kwdefaults) {
            return NULL;
        }
    }

    arg_ty kwarg = NULL;
    if (star_etc != NULL && star_etc->kwarg != NULL) {
        kwarg = star_etc->kwarg;
    }

    return _Py_arguments(posonlyargs, posargs, vararg, kwonlyargs, kwdefaults,
                         kwarg, posdefaults, p->arena);
}

/* Constructs an empty arguments_ty object, that gets used when a function accepts no arguments. */
arguments_ty
empty_arguments(Parser *p)
{
    asdl_seq *posonlyargs = _Py_asdl_seq_new(0, p->arena);
    if (!posonlyargs) {
        return NULL;
    }
    asdl_seq *posargs = _Py_asdl_seq_new(0, p->arena);
    if (!posargs) {
        return NULL;
    }
    asdl_seq *posdefaults = _Py_asdl_seq_new(0, p->arena);
    if (!posdefaults) {
        return NULL;
    }
    asdl_seq *kwonlyargs = _Py_asdl_seq_new(0, p->arena);
    if (!kwonlyargs) {
        return NULL;
    }
    asdl_seq *kwdefaults = _Py_asdl_seq_new(0, p->arena);
    if (!kwdefaults) {
        return NULL;
    }

    return _Py_arguments(posonlyargs, posargs, NULL, kwonlyargs,
                         kwdefaults, NULL, kwdefaults, p->arena);
}
