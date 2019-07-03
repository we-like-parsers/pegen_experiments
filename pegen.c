#include <Python.h>
#include "pegen.h"

// Here, mark is the start of the node, while p->mark is the end.
// If node==NULL, they should be the same.
void
insert_memo(Parser *p, int mark, int type, ASTptr node)
{
    // Insert in front
    Memo *m = PyArena_Malloc(p->arena, sizeof(Memo));
    if (m == NULL)
        panic("pegen-generated parser out of arena space");  // TODO: How to handle malloc failures
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
    fprintf(stderr, "panic: %s\n", message);
}
