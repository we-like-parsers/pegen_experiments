Helper Structs
--------------

The following are all types defined in `pegen/pegen.h`.

##### Memo

Linked list, optimized for quickly finding a given type.

- type: int, either a token or a rule (rules start at 256)
- node: NULL or pointer to AST node OR pointer to token object
- mark: if node != NULL, index into Parser's array of tokens
- next: NULL or pointer to next Memo structure

##### Token

These are in an array linked from Parser.

- type: int, token type (needs only 8 bits)
- bytes: bytes object
- lineno, col_offset, end_lineno, end_col_offset: int
- memo: Pointer to linked list Memo

##### Parser

The Parser needs to point to a PyArena, used for allocating AST nodes and
other things.

- tok: Pointer to tokenizer, CPython's struct tok_state
- tokens: Pointer to array of Token pointers
- mark: index into array of Tokens
- fill: number of valid entries in array of Tokens
- size: total number of entries in array of Tokens
- arena: memory allocation arena (owns all AST, Token, Memo structures allocated)

##### PegenAlias

Needed because alias_ty does not hold line and column offset info.
When a rule needs to return an alias_ty, it returns a PegenAlias*
instead so that line and column info get propagated to the caller,
which extracts this info together with the alias_ty.

- alias: alias_ty
- lineno, col_offset, end_lineno, end_col_offset: int

##### CmpopExprPair

This gets used by the rules that implement comparison, due to the
structure of the Compare AST Object.

- cmpop: cmpop_ty, The comparison operator
- expr: expr_ty, The expression that gets compared

#### AugOperator

Used to encapsulate the value of an operator_ty enum value.

- kind: operator_ty, The augmented assignment operator


Helper Functions
----------------

###### `asdl_seq *singleton_seq(Parser *p, void *a)`
Creates a single-element `asdl_seq *` that contains `a`.

###### `asdl_seq *seq_insert_in_front(Parser *p, void *a, asdl_seq *seq)`
Creates a copy of `seq` and prepends `a` to it.

###### `asdl_seq *seq_flatten(Parser *p, asdl_seq *seq)`
Flattens an `asdl_seq *` of `asdl_seq *`s.

###### `expr_ty join_names_with_dot(Parser *p, expr_ty first_name, expr_ty second_name)`
Creates a new name of the form <first_name>.<second_name>.

###### `int seq_count_dots(asdl_seq *seq)`
Counts the total number of dots in `seq`s tokens.

###### `alias_ty alias_for_star(Parser *p)`
Creates an alias with `*` as the identifier name.

###### `void *seq_get_head(void *previous, asdl_seq *seq)`
Returns the first element of `seq` or `previous` if `seq` is empty.

###### `void *seq_get_tail(void *previous, asdl_seq *seq)`
Returns the last element of `seq` or `previous` if `seq` is empty.

###### `PegenAlias *pegen_alias(alias_ty alias, int lineno, int col_offset, int end_lineno, int end_col_offset, PyArena *arena)`
Constructs a `PegenAlias`.

###### `asdl_seq *extract_orig_aliases(Parser *p, asdl_seq *seq)`
Extracts `alias_ty`s from an `asdl_seq *` of `PegenAlias *`s.

###### `asdl_seq *map_names_to_ids(Parser *p, asdl_seq *seq)`
Creates a new `asdl_seq *` with the identifiers of all the names in `seq`.

###### `CmpopExprPair *cmpop_expr_pair(Parser *p, cmpop_ty cmpop, expr_ty expr)`
Constructs a `CmpopExprPair`.

###### `expr_ty Pegen_Compare(Parser *p, expr_ty expr, asdl_seq *pairs)`
Wrapper for `_Py_Compare`, so that the call in the grammar stays concise.

###### `expr_ty store_name(Parser *p, expr_ty load_name)`
Accepts a load name and creates an identical store name.

###### `asdl_seq *map_targets_to_del_names(Parser *p, asdl_seq *seq)`
Creates an `asdl_seq *` where all the elements have been changed to have del as context.

###### `asdl_seq *augoperator(Parser *p, operator_ty kind)`
Creates an `AugOperator` encapsulating the operator type provided in *kind*.
