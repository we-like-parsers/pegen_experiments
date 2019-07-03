#include <Python.h>
#include <Python-ast.h>
#include <pyarena.h>

#define ASTptr void*

typedef struct memo {
    int type;
    ASTptr node;
    int mark;
    struct memo *next;
} Memo;

typedef struct token {
    int type;
    char *start, *end;
    int line, col, endline, endcol;
    Memo *memo;
} Token;

typedef struct parse {
    struct tok_state *tok;
    char *input;
    Token *tokens;
    int mark;
    int fill, size;
    PyArena *arena;
} Parser;

void insert_memo(Parser *p, int mark, int type, ASTptr node);
int is_memoized(Parser *p, int type, ASTptr *pres);
void panic(char *message);

void *expect_token(Parser *p, char *c);

void *endmarker_token(Parser *p);
void *name_token(Parser *p);
void *newline_token(Parser *p);
void *number_token(Parser *p);

void *CONSTRUCTOR(Parser *p, ...);

#define LINE(arg) ((expr_ty)(arg))->lineno
#define COL(arg) ((expr_ty)(arg))->col_offset
#define ENDLINE(arg) ((expr_ty)(arg))->end_lineno
#define ENDCOL(arg) ((expr_ty)(arg))->end_col_offset
