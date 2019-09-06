Plan of attack for the rest
===========================

Introduce various PEG/EBNF features gradually:

- [x] Make the grammar parser "self-hosted".
- [x] Named items
- [x] Groups containing alternatives (with actions)
- [x] Optional
- [x] Repetition (0+, 1+)
- [x] Lookahead (positive, negative)
- [x] Cut
- [ ] Fix left-recursion detection (including nullable)

Of these:

1. Named items: this just replaces the default name.  Syntax:
   `NAME '=' item`.  Representation: NamedItem(name, item).  [Done]

2. Groups: these are given a unique generated name and implemented as
   if they were a separate rule.  Exceptions: a group at the very top
   level of a rule melds away; a group with only one alternative gets
   inlined.  [Done]

3. Optional: either `[alts]` or `atom?`.  Must be named to use.  To
   represent in the parser generator use `Maybe(atom)`).  To implement
   them in the generated parser, ignore the result.  To represent them
   in the parse tree, use the value or `None`.  In the parser ths
   basically cannot fail, and we can write `and ((foo := self.foo())
   or True)`.  This means that in the parse tree it'll be represented
   as `None`.  Examples:
   ```
   expr: ['+'] term { term }
   ```
   This translates to
   ```
   if (True
       and (self.expect('+') or True)
       and (term := self.term())
   ):
       return term
   ```
   Also
   ```
   expr: t1=term t2=['+' term { term }] { t1 + t2 if t2 is not None else t1 }
   ```
   translates to
   ```
   if (True
       and (t1 := self.term()) is not None
       and ((t2 := self._gen_rule_1()) is not None or True)
   ):
       return t1 + t2 if t2 is not None else t1
   ```

4. Repetition: either `atom*` or `atom+`.  Representation in the
   parser generator: `Repeat0(atom)` or `Repeat1(atom)`.  In the
   parser we can use a helper, like `self.repeat0(self.expr)` or
   `self.repeat1(self.term)`; these return a list on success (which
   may be empty for `repeat0`) or `None` for failure.  Must be named
   to usefully refer to the list.

5. Lookahead: either `&atom` or `!atom`; these cannot be named.
   In the generator: `PosLookahead(atom)` or `NegLookahead(atom)`.
   In the parser: `self.pos_lookahead(self.expr)` or
   `self.neg_lookahead(self.expr)`.  Not in the parse tree.

6. Cut: `~`; cannot be named.  This disrupts the flow of the current
   choice, if the current alternative does not succeed, the whole
   choice fails (either a rule or a group).  Implementation as I did
   for the original pegen.  In the generator, `Cut()`; in the parser,
   `and (cut := True)`, and then the idiom changes from
   ```
   self.reset(pos)
   ```
   to
   ```
   self.reset(pos)
   if cut:
       return None
   ```


Revised visualizer design
=========================

Turns out the box around the current token is distracting, because it
looks like the box "contracts and expands" as the cursor moves right
and the token lookahead buffer is filled.  So instead I went with a
simple arrow pointing at the next token -- if there is no next token
yet, it points to the space where the next token will be.

I'm still looking for a better way to show the state of the parser.
Apart from the call stack, I also want to indicate the progress
through each rule as we parse.  Currently when we parse through e.g.
```
statement: if_statement | assignment | expr
if_statement: 'if' expr ':' statement
expr: term '+' expr | term
term: atom '*' term | atom
atom: NAME | NUMBER | '(' expr ')'
```
we show the call stack, e.g.
```
statement()
if_statement()
     expr()
     term()
     atom()
     expect(NAME)
```
but we don't show what happened to the `'if'` keyword and we don't
know if that term() call corresponds to the first alternative in
expr (i.e. `term '+' expr`) or the second (i.e. just `term`).

Maybe instead of just `expr()` we can show the entire rule for expr
with a highlight showing where we currently are, e.g.
```
expr: term '+' expr | term
      ^^^^
```

Using curses we could do this using highlights.  We could show this
for each line, and move the tokens below. We could also add guides
to connect the rule to the token, e.g.
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
|    expr: term '+' expr | term
           ^^^^
|    term: atom '*' term | atom
                ^^^
|    |     expect('*')
|    |     |
'if' 'foo' '*' 'bar' ':' 'baz'
           ^
```
(I hope it will be less messy with highlights than ^^^^.)

Basically I am now trying to show the parse tree under development.
Let's start with the *final* parse tree (I am flipping again to having
the tokens at the top):
```
'if' 'foo' '+' 'bar' ':' 'baz' '=' 'one' '*' 'two' NEWLINE ENDMARKER

     atom      atom      target    atom      atom
     term      term                term      term
               expr                          expr
     expr__________                expr__________
                         assignment______________
if_statement_____________________________________
statement________________________________________
statements________________________________________________
start_______________________________________________________________
```

This builds up from the bottom to the top, from left to right.
Q: Should items be pushed as far up as they can, or as far down?
The above pushes up; here's pushing down, also with tokens added:
```
'if' 'foo' '+' 'bar' ':' 'baz' '=' 'one' '*' 'two' NEWLINE ENDMARKER

                                             NAME
               NAME                NAME      atom
     NAME      atom                atom      term
     atom      term      NAME      term  '*' expr
     term  '+' expr      targe '=' expr__________
     expr__________      assignment______________
if_statement_____________________________________
statement________________________________________  NEWLINE
statements________________________________________________ ENDMARKER
start_______________________________________________________________
```

This static image doesn't show the "false parses" (the attempts to
parse that fail) but as it builds up those do get included -- until
they are discarded.

Let's build up a small part.
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
              ^^^^
```

This means we're in statement(), and it's called into the first (and
only) item of the first alternative, `if_statement()`.  So we're also
in `if_statement()`, which has one alternative of four items, and
we're at the first item, `'if'`.  Now we call into `expect('if')`,
which is rendered like this:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
              ^^^^
expect('if')
```

If we weren't looking at `'if'`, it would return `None`, showing as
```
expect('if') -> None
```
(just like currently).  But as it's a success, it will show as
```
expect('if') -> 'if'
```
and then this will sink down to the cache, and the cursor in
`if_statement` will move:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
```

Then we'll add another call to the stack (`expr`), which is also
indented so as to align it with the token at which we're starting to
look for it (i.e., at `'foo'`):
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
```

Then this causes another call to `term`, and that another to `atom`:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
           ^^^^
     atom: NAME | NUMBER | '(' expr ')'
           ^^^^
```

Now we call `expect(NAME)`:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
           ^^^^
     atom: NAME | NUMBER | '(' expr ')'
           ^^^^
     expect(NAME)
```
and that succeeds:
```
     expect(NAME) -> NAME('foo')
```

Then the `expect()` call gets dropped from the stack into the cache,
and then `atom()` also returns.  It gets displayed as a successful
return first:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
           ^^^^
     atom() -> NAME('foo')
```

Then the `term` rule moves to the next item:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
                ^^^
```

Then we call `expect('*')`:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
                ^^^
           expect('*')
```
but this fails:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
                ^^^
           expect('*') -> None
```

So then the `term` rule moves to the second alternative:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
                           ^^^^
```

At this point `atom()` is immediately satisfied from the cache, so we
get
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
                           ^^^^
     atom() -> NAME('foo')
```

Then the whole thing repeats, `term` moves on to `'/'`, which fails,
and then `term` moves on to the third alternative:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term: atom '*' term | atom '/' atom | atom
                                           ^^^^
     atom() -> NAME('foo')
```

This time this is accepted so we get
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
           ^^^^
     term() -> atom() -> NAME('foo')
```

Now we finally move on to the second item in `expr`:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
                ^^^
```
(the `term` drops to the cache).

The `expect('+')` call succeeds and we move on to the third item:
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
                    ^^^^
```

This goes through similar girations until we get
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr: term '+' expr | term '-' term | term
                    ^^^^
               expr() -> term() -> atom() -> NAME('bar')
```

Then the outer `expr` succeeds and we get
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr() -> (term() -> atom() -> NAME('foo')) '+' (expr() -> term() -> atom() -> NAME('bar'))
```

Or perhaps compressed?
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr() -> term() '+' expr()
```

Or perhaps rendered vertically?
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr() ->
         term() -> atom() -> NAME('foo')
         '+'
         expr() -> term() -> atom() -> NAME('bar')
```

Or perhaps aligned with the tokens?
```
statement: if_statement | assignment | expr
           ^^^^^^^^^^^^
if_statement: 'if' expr ':' statement
                   ^^^^
     expr() ->
     |+- term() -> atom() -> NAME('foo')
     ||    +- '+'
     ||    |   +- expr() -> term() -> atom() -> NAME('bar')
     ||    |   |
'if' 'foo' '+' 'bar' ':' 'baz' '=' 'one' '*' 'two' NEWLINE ENDMARKER
```

Or perhaps at this point show a partial parse tree?
```
        statement
            |
      if_statement
            |
 +----------+------+--------+
 |          |      |        |
'if'       expr   ':'   statement
 :          |      ?        ?
 :     +----+----+
 :     |    |    |
 :    term '+'  expr
 :     |    :    |
 :    atom  :   term
 :     |    :    |
 :    NAME  :   atom
 :     :    :    |
 :     :    :   NAME
 :     :    :    :
'if' 'foo' '+' 'bar' ':' 'baz' '=' 'one' '*' 'two' NEWLINE ENDMARKER
```

Idea: let's add a toggle to the UI.  The "normal" mode displays call
stacks, with minimal info about parse trees; the "alternative" mode
displays parse trees, disregarding call stacks.


(For reference the fully tokenized input:)
```
'if' 'foo' '+' 'bar' ':' 'baz' '=' 'one' '*' 'two' NEWLINE ENDMARKER
```


Visualizer design
=================

Basic idea: the parser generates a log of JSON records that we can
visualize separately (or in real time?).  This design allows for
different visualizers.  Also, the generation of logging events can be
enabled/disabled in the meta-compiler, so you can have an optimized
parser that doesn't need to check for verbose flags (and is more
readable on top).

Top row: tokenizer state.  A line of tokens (just quoted strings) with
a box around the one currently at the mark.  If we haven't peeked yet,
just a bar.  Examples:


```
# Next token is '=':
                         +---+
 'if' 'x' '+' 'y' ':' 'x'|'='|
                         +---+

# Next token hasn't been read yet:
                             +
 'if' 'x' '+' 'y' ':' 'x' '='|
                             +

# Next token is '=', beyond that in the tokens buffer are three more:
                         +---+
 'if' 'x' '+' 'y' ':' 'x'|'='| '1' '+' 'y'
                         +---+

```

Below that: parsing stack. Each parsing method that's been called and
hasn't returned yet is listed (oldest frame on top).  The first
character of the method name is aligned with the beginning of the
corresponding token in the top row.  Parsing methods that did return
and are still in play are listed below that in square brackets
(truncated as needed to fit).  Example:

```
                             +
 'if' 'x' '+' 'y' ':' 'x' '='|
                             +

 statement...
 if_statement...
      [expr-----]      statement...
                       assignment...
                       [t]     expr...
                               term...
                               atom...
```

(`[t]` stands for `[term]`, it's been truncated to correctly indicate
the extent.)

At this point various `expect()` calls are made and the array of
tokens will expand to show the box with `'1'` in it.

Finally, below that, is the memo cache.  This is indented the same as
the parsing stack, with some kind of indicator of success or failure,
and a range (for success).  We should try not to repeat what's already
shown above (`[expr-----]` and `[t]`), and maybe suppress all tokens.
I'm not actually sure what to do here yet.  Example:

```
      [expr-----]
      [t]     [t]
      [a]     [a]
```


Design for the C code
=====================

Let's do recursive descent first.  It's simple and we can try to limit
the stack manually (currently CPython only allows about 100 nested
parentheses so that's okay).

Parser structure
----------------

Also needs to point to a PyArena, used for allocating AST nodes and
other things.  And maybe some flag indicating there's an allocation
error and a convention to bail if there is one.

Possibly return Py_None for "no match" rather than NULL?  That will
allow NULL to mean "error" (other than syntax error or EOF).  But it
will be very clumsy, make all generated code more complex (may have to
introduce goto).

- tok: Pointer to tokenizer, CPython's struct tok_state
- input: Pointer to input bytes (char *), same as tok->input (owned by tok).
         (Not used though.  And tokenizing from file won't have it.)
- tokens: Pointer to array of Token structs
- mark: index into array of Tokens
- fill: number of valid entries in array of Tokens
- size: total number of entries in array of Tokens
- arena: memory allocation arena (owns all AST, Token, Memo structures allocated)

Token structure
---------------

These are in an array linked from Parser.  (Or linked list???)

- type: int, token type (needs only 8 bits)
- value: bytes object [or maybe just two indices into parser->input?)
- line, col, endline, endcol: int
- memo: Pointer to linked list Memo

Memo structure
--------------

Linked list, optimized for quickly finding a given type.  (Or array???)

- type: int, either a token or a rule (rules start at 256)
- node: NULL or pointer to AST node OR pointer to token object (TODO)
- mark: if node != NULL, index into Parser's array of tokens
- next: NULL or pointer to next Memo structure

C function for a rule
---------------------

Similar to the Python functions, but memoziation is done here.

// Constants for rules: expr_type, term_type, etc.
// Constants for tokens: NAME, NUMBER, NEWLINE, LPAR, RPAR, etc.
// Functions for rules: expr_rule, term_rule, etc.

#define expr_type  321

static ASTptr
expr_rule(Parser *p)
{
    ASTptr res = NULL;
    int mark = p->mark;
    if (is_memoized(p, expr_type, &res))
        return res;
    // Alternatives start here
    if ((a = rule_a(p)) && (b = rule_b(p)) && (c = rule_c(p))) {
        // On success
        res = <make new AST node from (a, b, c)>
        insert_memo(p, mark, expr_type, res);
        return res;
    }
    p->mark = mark;
    // More alternatives...
    ...
    // At the end
    // Memoize negative result too!
    insert_memo(p, mark, expr_type, NULL);
    return NULL;
}

// Here, mark is the start of the node, while p->mark is the end.
// If node==NULL, they should be the same.
static void
insert_memo(Parser *p, int mark, int type, ASTptr node)
{
    // Insert in front
    Memo *m = PyArena_Malloc(p->arena, sizeof(Memo));
    if (m == NULL)
        panic();  // TODO: How to handle malloc failures
    m->type = type;
    m->node = node;
    m->mark = p->mark;
    m->next = p->tokens[mark].memo;
    p->tokens[mark].memo = m;
}

static int  // bool
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

Structure for each rule
-----------------------

    ASTptr a, *b, *c;
    if ((a = a_rule(p) && (b = b_rule(p)) && (c = c_rule(p))) {
        ASTptr res = SomeAstRule(a, b, c, p->arena);  // Often also add line, col, endline, endcol
        if (res == NULL)
            panic();
        insert_memo(p, mark, expr_type, res);
        return res;
    }
    p->mark = mark;  // Prep for the next alternative, or for fail return

Expecting tokens
----------------

(This is where the token position actually gets moved.)

NUMBER: return Constant(parsenumber(c, string), NULL, line, col, endline, endcol, p->arena)
STRING: return <something similar but more complicated>
ELLIPSIS: return Constant(Py_Ellipsis, NULL, line, col, endline, endcol, p->arena)
NAME: return Name(id, Load/Store, line, col endline, endcol, p->arena)
      But if it's a keyword, something else?
OP: Translate into something else?  Does it always mean an error?
    Only seems to be generated for things like ? or $.
LPAR, 'if', etc.: return something appropriate
      (a Python object added with PyArena_AddPyObject(p->arena, obj),
      or a special marker object

Conclusion, we may need a way to fit tokens (both with extra value
like NUMBER and without, like LPAR) in the return types of grammar
rule functions, unless we want to use a different type for expect()
kinds of things.

Let's say we have (memoized) expect(NAME) in the Python version; in
the C version we'd have

static ASTptr
expect_name(Parser *p)
{
    ASTptr res;
    if (is_memoized(p, NAME, &res))
        return res;
    int mark = p->mark;
    Token *t = next_token(p);  // effectively &p->tokens[p->mark++]
    if (t->type == NAME) {
        // TODO: Load/Store distinction
        res = Name(t->string, Load, <line/col info>, p->arena);
        insert_memo(p, mark, NAME, res);
        return res;
    }
    insert_memo(p, mark, NAME, NULL);
    return NULL;
}

And ditto for STRING

OTOH for all tokens without extra info we could have one function:

static ASTptr
expect_token(Parser *p, int type)
{
    ASTptr res;
    if (is_memoized(p, NAME, &res))
        return res;
    int mark = p->mark;
    Token *t = next_token(p);  // effectively &p->tokens[p->mark++]
    if (t->type == type) {
        res = <some constant>  // TODO
        insert_memo(p, mark, type, res);
        return res;
    }
    insert_memo(p, mark, type, NULL);
    return NULL;
}

What should the result type be here?  Something that's a subclass of
AST.  For things like LPAR, there's no precedent.  Also, maybe this
shouldn't bother with memoization, since the info is all there.  Just
inline the fast path of next_token(p).

Return types for rules
----------------------

It turns out the AST nodes are not uniquely identifiably given just a
void*.  You must know whether it points to e.g. a mod_ty, a stmt_ty,
or an expr_ty -- each of these is their own typedef in Python-ast.h,
with its own enum for union discrimination, and the object is
structured like this:

typedef struct _stmt *stmt_ty;

enum _stmt_kind {FunctionDef_kind=1, AsyncFunctionDef_kind=2, ClassDef_kind=3,
                 ...........};
struct _stmt {
    enum _stmt_kind kind;
    union {
        struct {
            identifier name;
            .............
        } FunctionDef;
        ...........
    } v;
    int lineno;
    int col_offset;
    int end_lineno;
    int end_col_offset;
};

We will have to have a way for the rule to indicate the return type of
the function generated for the rule.  How can we do this?  One option
would be to add the type in brackets after the rule name, like so:

start[mod_ty]: stmt* $ { ........ }
stmt[stmt_ty]: small_stmt | large_stmt
small_stmt[stmt_ty]: .........

However, this does not give the parser enough information if it wants
to split out an optional or repeated sub-expression, nor does it give
the return type of nested alternatives like `('+' | '-')` here:

sum[expr_ty]: term ('+' | '-') sum

Maybe we can put the type in the action, like this:

start: stmt* $ { mod_ty | .......... }

We also need a data type to represent lists of things.  Maybe asdl_seq
is enough?  But wha about asdl_int_seq?  (Both are in asdl.h.)

And what do we use as the type to represent tokens, e.g. '+'?
I guess it would come down to

add_op[operator_ty]: '+' { Add } | '-' { Sub }

and then we'd have this:

sum[expr_ty]: l=term op=add_op r=term { BinOp(l, op, r, l->lineno, l->col_offset, r->end_lineno, r->end_col_offset, p->arena) }

(Of course we'd need to deal with left-recursion still.)

Return types for tokens
-----------------------

We need something to represent tokens, so we can at least get line
numbers out of them.  Example:

term[expr_ty]: ....... | op='-' t=term { UnaryOp(USub, t, op->lineno, op->col_offset, t->end_lineno, t->end_col_offset, p->arena) }

So whatever the tokenizer uses to represent the token, it had better
have lineno etc. attributes.  I guess we could use our own Token
struct, just rename line, col, endline, endcol to the longer names.

Shorter actions
---------------

I also desperately want the actions to be shorter.  E.g. for the latter rule I want to write

term[expr_ty]: ....... | op='-' t=term { UnaryOp(USub, t, STUFF(op, t)) }

where

#define STUFF(l, r) l->lineno, l->col_offset, r->end_lineno, r->end_col_offset, p->arena

This however runs into a C preprocessor issue; maybe we'll have to write

...... { _Py_UnaryOp(USub, t, STUFF(op, t)) }

Alternatively we could define our own macros MyBinOp, MyUnaryOp etc., so you could write

...... { _Py_UnaryOp(USub, t, STUFF(op, t)) }


Avoiding name conflicts
-----------------------

It would be tragic if we couldn't name a rule 'if' or int'.  So we do
everything with suffixes, e.g. expr_rule, expr_type, expr_var.
Currently there's a loophole where named subexpressions don't have a
_var suffix, but I think that won't work -- then you couldn't name a
*subexpression* for' or 'struct', and naming it 'p' or 'mark' would
also cause problems.  So probably it'll have to be l_var and r_var in
the action, if the grammar uses 'l' and 'r'.


Implementing repeated values
----------------------------

Consider

start: foo* { <what to put here?> }
foo: NUMBER

The generated C code has to have a way to collect 0 or more foo items
for consumption by the { curly stuff }.  In the generated Python code
we just use

def _loop_1(self):
    mark = self.mark()
    children = []
    while (foo := self.foo()):
        children.append(foo)
        mark = self.mark()
    self.reset(mark)
    return children

but in C we don't have such luxuries.  I guess the most basic way out
is to use malloc/realloc, like this:

// Insert casts until compiler is happy
static asdl_seq *
_loop_1_rule(Parser *p)
{
    void **children = PyMem_Malloc(0);
    ssize_t n = 0;
    while (foo = foo_rool(p)) {
        children = PyMem_Realloc(children, (n+1)*sizeof(void*));
        if (!children) panic("...");
        children[n++] = foo;
    }
    asdl_seq *res = _Py_asdl_seq_new(n, p->arena);
    if (res == NULL) panic("...");
    for (int i = 0; i < n; i++) asdl_seq_SET(res, i, children[i]);
    PyMem_Free(children);
    return res;
}

The cost here is a potentially quadratic realloc() loop (especially
bothersome if a large list or module is being compiled), but hopefully
we're running on a system where the system realloc() (or
PyMem_Realloc()) is smart.  If the O(N**2) behavior becomes a problem
we can write our own wrapper or macro that rounds the size up
logarithmically (e.g. using the algorithm from list_resize()).

For the * operator we may return a sequence of 0 elements, for the +
operator we should return NULL if there are no elements:

    if (n == 0) {
        PyMem_Free(children);
        return NULL;
    }


Implementing left-recursion
---------------------------

We rely on the analysis that marks left-recursuve rules and determines
leaders for each SCC.

We generate two functions:

- expr_rule(p) has the signature of a typical rule function
- expr_rule_raw(p) is used internally

These correspond to the decorated and undecorated functions in Python.

We need to add a new function to *replace* a memoized item if it's
already there (and insert it if it isn't).

The outer function does:

- if it's memoized, return that
- prime the memo with failure
- repeatedly:
  - reset mark
  - call the raw function
  - if it fails or doesn't move mark ahead, break
  - else, overwrite the memo with the result and continue
- return the last successfully memoed value/position
