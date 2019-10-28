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

int insert_memo(Parser *p, int mark, int type, void *node);
int update_memo(Parser *p, int mark, int type, void *node);
int is_memoized(Parser *p, int type, void *pres);

int lookahead_with_string(int, void *(func)(Parser *, const char *), Parser *, const char *);
int lookahead_with_int(int, Token *(func)(Parser *, int), Parser *, int);
int lookahead(int, void *(func)(Parser *), Parser *);

Token *expect_token(Parser *p, int type);

void *async_token(Parser *p);
void *await_token(Parser *p);
void *endmarker_token(Parser *p);
expr_ty name_token(Parser *p);
void *newline_token(Parser *p);
void *indent_token(Parser *p);
void *dedent_token(Parser *p);
expr_ty number_token(Parser *p);
expr_ty string_token(Parser *p);
void *keyword_token(Parser *p, const char *val);

void *CONSTRUCTOR(Parser *p, ...);

#define LINE(arg) ((expr_ty)(arg))->lineno
#define COL(arg) ((expr_ty)(arg))->col_offset
#define ENDLINE(arg) ((expr_ty)(arg))->end_lineno
#define ENDCOL(arg) ((expr_ty)(arg))->end_col_offset
#define EXTRA(head, tail) LINE(head), COL(head), ENDLINE(tail), ENDCOL(tail), p->arena

PyObject *run_parser_from_file(const char *filename, void *(start_rule_func)(Parser *), int mode);
PyObject *run_parser_from_string(const char *str, void *(start_rule_func)(Parser *), int mode);
asdl_seq *singleton_seq(Parser *, void *);
asdl_seq *seq_insert_in_front(Parser *, void *, asdl_seq *);
asdl_seq *seq_flatten(Parser *, asdl_seq *);
