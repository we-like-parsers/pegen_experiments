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
    int lineno, col_offset, end_lineno, end_col_offset;
    Memo *memo;
} Token;

typedef struct {
    struct tok_state *tok;
    Token *tokens;
    int mark;
    int fill, size;
    PyArena *arena;
} Parser;

typedef struct {
    alias_ty alias;
    int lineno, col_offset, end_lineno, end_col_offset;
} PegenAlias;

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

#define EXTRA_EXPR(head, tail) EXTRA(head, expr_type, tail, expr_type)
#define EXTRA(head, head_type_func, tail, tail_type_func) head_type_func##_headline(head), \
                                                          head_type_func##_headcol(head), \
                                                          tail_type_func##_tailline(tail), \
                                                          tail_type_func##_tailcol(tail), \
                                                          p->arena

PyObject *run_parser_from_file(const char *filename, void *(start_rule_func)(Parser *), int mode);
PyObject *run_parser_from_string(const char *str, void *(start_rule_func)(Parser *), int mode);
asdl_seq *singleton_seq(Parser *, void *);
asdl_seq *seq_insert_in_front(Parser *, void *, asdl_seq *);
asdl_seq *seq_flatten(Parser *, asdl_seq *);
expr_ty join_names_with_dot(Parser *, expr_ty, expr_ty);
int seq_count_dots(asdl_seq *);
alias_ty alias_for_star(Parser *);
void *seq_get_tail(void *, asdl_seq *);
PegenAlias *pegen_alias(alias_ty, int, int, int, int, PyArena *);
asdl_seq *seq_map_to_alias(Parser *, asdl_seq *);

inline int expr_type_headline(expr_ty a) { return a->lineno; }
inline int expr_type_headcol(expr_ty a) { return a->col_offset; }
inline int expr_type_tailline(expr_ty a) { return a->end_lineno; }
inline int expr_type_tailcol(expr_ty a) { return a->end_col_offset; }
inline int stmt_type_headline(stmt_ty a) { return a->lineno; }
inline int stmt_type_headcol(stmt_ty a) { return a->col_offset; }
inline int stmt_type_tailline(stmt_ty a) { return a->end_lineno; }
inline int stmt_type_tailcol(stmt_ty a) { return a->end_col_offset; }
inline int token_type_headline(Token *a) { return a->lineno; }
inline int token_type_headcol(Token *a) { return a->col_offset; }
inline int token_type_tailline(Token *a) { return a->end_lineno; }
inline int token_type_tailcol(Token *a) { return a->end_col_offset; }
inline int alias_type_headline(PegenAlias *a) { return a->lineno; }
inline int alias_type_headcol(PegenAlias *a) { return a->col_offset; }
inline int alias_type_tailline(PegenAlias *a) { return a->end_lineno; }
inline int alias_type_tailcol(PegenAlias *a) { return a->end_col_offset; }
