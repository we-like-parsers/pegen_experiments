#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <token.h>
#include <Python-ast.h>
#include <pyarena.h>

typedef struct _memo {
    int type;
    void *node;
    int mark;
    struct _memo *next;
} Memo;

typedef struct {
    int type;
    PyObject *bytes;
    int line, col, endline, endcol;
    Memo *memo;
} Token;

typedef struct {
    struct tok_state *tok;
    Token *tokens;
    int mark;
    int fill, size;
    PyArena *arena;
} Parser;

void insert_memo(Parser *p, int mark, int type, void *node);
void update_memo(Parser *p, int mark, int type, void *node);
int is_memoized(Parser *p, int type, void *pres);
void panic(char *message);

Token *expect_token(Parser *p, int token);

void *endmarker_token(Parser *p);
expr_ty name_token(Parser *p);
void *newline_token(Parser *p);
expr_ty number_token(Parser *p);
expr_ty string_token(Parser *p);

void *CONSTRUCTOR(Parser *p, ...);

#define LINE(arg) ((expr_ty)(arg))->lineno
#define COL(arg) ((expr_ty)(arg))->col_offset
#define ENDLINE(arg) ((expr_ty)(arg))->end_lineno
#define ENDCOL(arg) ((expr_ty)(arg))->end_col_offset
#define EXTRA(head, tail) LINE(head), COL(head), ENDLINE(tail), ENDCOL(tail), p->arena

PyObject *run_parser(const char *filename, void *(start_rule_func)(Parser *), int mode);
asdl_seq *singleton_seq(Parser *, void *);
