Syntax
------

The grammar consists of a sequence of rules of the form:
```
rule_name: <expression>
```

Optionally, a type can be included right after the rule name,
which specifies the return type of the C function corresponging
to the rule:
```
rule_name[return_type]: <expression>
```
If the return type is omitted, then a `void *` is
returned.

### Grammar Expressions

##### `# comment`
Python-style comments

##### `e1 e2`
Match e1, then match e2

##### `e1 | e2`
Match e1 or e2.

A | can be used before the first alternative as well for formatting
purposes.

##### `( e )`
Match e

##### `[ e ] or e?`
Optinally match e

##### `e*`
Match zero or more occurences of e

##### `e+`
Match one or more occurences of e

##### `s.e+`
Match one or more occurences of e, separated by s. The generated parse tree
does not include the separator. This is identical to `(e (s e)*)`.

##### `&e`
Succeed if e can be parsed, without consuming any input.

##### `!e`
Fail if e can be parsed, without consuming any input.

##### `~e`
Commit to the current alternative, even if it fails to parse.


### Return Value

Optionally, an alternative can be followed by a so-called action
in curly-braces, which specifies the return value of the alternative:
```
rule_name[return_type]:
    | first_alt1 first_alt2 { first_alt1 }
    | second_alt1 second_alt2 { second_alt1 }
```
If the action is omitted, then there are two different possibilities:
1.  If there's a single name in the alternative, this gets returned.
2.  If not, a dummy name object gets returned.


### Variables in the Grammar

An expression can be named.  The name can the be used in the action,
like this:
```
rule_name[return_type]: '(' a=some_other_rule ')' { a }
```

Style
-----

This is not a hard limit, but lines longer than 110 characters should almost
always be wrapped.  Most lines should be wrapped after the opening action
curly brace, like:

```
really_long_rule[expr_ty]: some_arbitrary_rule {
    _This_is_the_action }
```
