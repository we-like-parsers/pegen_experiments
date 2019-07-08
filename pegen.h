#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <token.h>
#include <Python-ast.h>
#include <pyarena.h>

typedef void *ASTptr;

typedef struct _memo {
    int type;
    ASTptr node;
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

void insert_memo(Parser *p, int mark, int type, ASTptr node);
int is_memoized(Parser *p, int type, ASTptr *pres);
void panic(char *message);

ASTptr expect_token(Parser *p, int token);

ASTptr endmarker_token(Parser *p);
ASTptr name_token(Parser *p);
ASTptr newline_token(Parser *p);
ASTptr number_token(Parser *p);

ASTptr CONSTRUCTOR(Parser *p, ...);

#define LINE(arg) ((expr_ty)(arg))->lineno
#define COL(arg) ((expr_ty)(arg))->col_offset
#define ENDLINE(arg) ((expr_ty)(arg))->end_lineno
#define ENDCOL(arg) ((expr_ty)(arg))->end_col_offset

int run_parser(const char *filename, ASTptr(*start_rule_func)(Parser *));
