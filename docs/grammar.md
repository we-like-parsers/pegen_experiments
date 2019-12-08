Syntax
------

The grammar consists of a sequence of rules of the form:
```
rule_name: expression
```

Optionally, a type can be included right after the rule name,
which specifies the return type of the C or Python function
corresponding to the rule:
```
rule_name[return_type]: expression
```
If the return type is omitted, then a `void *` is
returned in C and an `Any` in Python.

### Grammar Expressions

##### `# comment`
Python-style comments.

##### `e1 e2`
Match e1, then match e2.
```
rule_name: first_rule second_rule
```

##### `e1 | e2`
Match e1 or e2.

The first alternative can also appear on the line after the rule
name for formatting purposes.  In that case, a | can also be used
before the first alternative, like so:
```
rule_name[return_type]:
    | first_alt
    | second_alt
```

##### `( e )`
Match e.
```
rule_name: (e)
```

A slightly more complex and useful example includes using the grouping
operator together with the repeat operators:
```
rule_name: (e1 e2)*
```

##### `[ e ] or e?`
Optinally match e.
```
rule_name: [e]
```

A more useful example includes defining that a trailing comma is optional:
```
rule_name: e (',' e)* [',']
```

##### `e*`
Match zero or more occurences of e.
```
rule_name: (e1 e2)*
```

##### `e+`
Match one or more occurences of e.
```
rule_name: (e1 e2)+
```
##### `s.e+`
Match one or more occurences of e, separated by s. The generated parse tree
does not include the separator. This is identical to `(e (s e)*)`.
```
rule_name: ','.e+
```

##### `&e`
Succeed if e can be parsed, without consuming any input.

##### `!e`
Fail if e can be parsed, without consuming any input.

An example taken from `data/simpy.gram` specifies that a primary
consists of an atom, which is not followed by a `.` or a `(` or
a `[`:
```
primary: atom !'.' !'(' !'['
```

##### `~e`
Commit to the current alternative, even if it fails to parse.
```
rule_name: '(' ~ some_rule ')' | some_alt
```
In this example, if a left parenthesis is parsed, then the other
alternative won't be considered, even if some_rule or ')' fail
to be parsed.


### Return Value

Optionally, an alternative can be followed by a so-called action
in curly-braces, which specifies the return value of the alternative:
```
rule_name[return_type]:
    | first_alt1 first_alt2 { first_alt1 }
    | second_alt1 second_alt2 { second_alt1 }
```
If the action is omitted and C code is being generated, then there
are two different possibilities:
1.  If there's a single name in the alternative, this gets returned.
2.  If not, a dummy name object gets returned.

If Python code is being generated, then a list with all the parsed
expressions gets returned.


### Variables in the Grammar

A subexpression can be named by preceding it with an identifier and an `=` sign.
The name can then be used in the action, like this:
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
