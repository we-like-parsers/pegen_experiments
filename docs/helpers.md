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

##### CmpopExprPair

This gets used by the rules that implement comparison, due to the
structure of the Compare AST Object.

- cmpop: cmpop_ty, The comparison operator
- expr: expr_ty, The expression that gets compared

##### KeyValuePair

Used to hold a key value pair, that is needed when parsing the key
value pairs of a dict.

- key: expr_ty, The pair's key
- value: expr_ty, The pair's value

##### NameDefaultPair

Needed so that rules that implement function parameters, can store
names and their default values.

- arg: arg_ty, The argument name
- value: expr_ty, arg's default value

##### SlashWithoutDefault

This is used by the `slash_without_default` rule, which parses two
different kinds of positional only arguments and stores those in this
struct.

- plain_names: `asdl_seq *` of `arg_ty`s or NULL, Positional only
  arguments with no default values
- names_with_defaults: `asdl_seq *` of `NameDefaultsPair`s, Positional
  only arguments with default values

##### StarEtc

This is used by the `star_etc` rules, whose role is to parse the vararg,
the keyword only arguments and the kwarg.

- vararg: `arg_ty` or NULL, The vararg
- kwonlyargs: `asdl_seq *` of `NameDefaultPair`s or NULL, Keyword only arguments
- kwarg: `arg_ty` or NULL, The kwarg

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

###### `KeyValuePair *key_value_pair(Parser *p, expr_ty key, expr_ty value)`
Constructs a `KeyValuePair` that is used when parsing a dict's key value pairs.

###### `asdl_seq *get_keys(Parser *p, asdl_seq *seq)`
Extracts all keys from an `asdl_seq*` of `KeyValuePair*`s.

###### `asdl_seq *get_values(Parser *p, asdl_seq *seq)`
Extracts all values from an `asdl_seq*` of `KeyValuePair*`s.

###### `NameDefaultPair *name_default_pair(Parser *p, arg_ty arg, expr_ty value)`
Constructs a `NameDefaultPair`.

###### `SlashWithDefault *slash_with_default(Parser *p, asdl_seq *plain_names, asdl_seq *names_with_defaults)`
Constructs a `SlashWithDefault`.

###### `StarEtc *star_etc(Parser *p, arg_ty vararg, asdl_seq *kwonlyargs, arg_ty kwarg)`
Constructs a `StarEtc`.

###### `arguments_ty make_arguments(Parser *p, asdl_seq *slash_without_default, SlashWithDefault *slash_with_default, asdl_seq *plain_names, asdl_seq *names_with_default, StarEtc *star_etc)`
Constructs an `arguments_ty` object out of all the parsed constructs in the `parameters` rule.

###### `arguments_ty empty_arguments(Parser *p)`
Constructs an empty `arguments_ty` object, that gets used when a function accepts no arguments.

###### `asdl_seq *augoperator(Parser *p, operator_ty kind)`
Creates an `AugOperator` encapsulating the operator type provided in *kind*.
