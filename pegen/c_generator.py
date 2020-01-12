import ast
import re
from typing import Any, cast, Dict, IO, Optional, List, Text, Tuple

from pegen.grammar import (
    Cut,
    GrammarVisitor,
    Rhs,
    Alt,
    NamedItem,
    NameLeaf,
    StringLeaf,
    Lookahead,
    PositiveLookahead,
    NegativeLookahead,
    Opt,
    Repeat0,
    Repeat1,
    Gather,
    Group,
    Rule,
)
from pegen import grammar
from pegen.parser_generator import dedupe, ParserGenerator
from pegen.tokenizer import exact_token_types

EXTENSION_PREFIX = """\
#include "pegen.h"
"""
EXTENSION_SUFFIX = """
static PyObject *
parse_file(PyObject *self, PyObject *args)
{
    const char *filename;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return NULL;
    return run_parser_from_file(filename, (void *)start_rule, %(mode)s);
}

static PyObject *
parse_string(PyObject *self, PyObject *args)
{
    const char *the_string;

    if (!PyArg_ParseTuple(args, "s", &the_string))
        return NULL;
    return run_parser_from_string(the_string, (void *)start_rule, %(mode)s);
}

static PyMethodDef ParseMethods[] = {
    {"parse_file",  parse_file, METH_VARARGS, "Parse a file."},
    {"parse_string",  parse_string, METH_VARARGS, "Parse a string."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef parsemodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "%(modulename)s",
    .m_doc = "A parser.",
    .m_methods = ParseMethods,
};

PyMODINIT_FUNC
PyInit_%(modulename)s(void)
{
    PyObject *m = PyModule_Create(&parsemodule);
    if (m == NULL)
        return NULL;

    return m;
}

// The end
"""


class CCallMakerVisitor(GrammarVisitor):
    def __init__(self, parser_generator: ParserGenerator):
        self.gen = parser_generator
        self.cache: Dict[Any, Any] = {}

    def visit_NameLeaf(self, node: NameLeaf) -> Tuple[str, str]:
        name = node.value
        if name in ("NAME", "NUMBER", "STRING"):
            name = name.lower()
            return f"{name}_var", f"{name}_token(p)"
        if name in ("NEWLINE", "DEDENT", "INDENT", "ENDMARKER", "ASYNC", "AWAIT"):
            name = name.lower()
            return f"{name}_var", f"{name}_token(p)"
        return f"{name}_var", f"{name}_rule(p)"

    def visit_StringLeaf(self, node: StringLeaf) -> Tuple[str, str]:
        val = ast.literal_eval(node.value)
        if re.match(r"[a-zA-Z_]\w*\Z", val):
            return "keyword", f'keyword_token(p, "{val}")'
        else:
            assert val in exact_token_types, f"{node.value} is not a known literal"
            type = exact_token_types[val]
            return "literal", f"expect_token(p, {type})"

    def visit_Rhs(self, node: Rhs) -> Tuple[Optional[str], str]:
        if node in self.cache:
            return self.cache[node]
        if len(node.alts) == 1 and len(node.alts[0].items) == 1:
            self.cache[node] = self.visit(node.alts[0].items[0])
        else:
            name = self.gen.name_node(node)
            self.cache[node] = f"{name}_var", f"{name}_rule(p)"
        return self.cache[node]

    def visit_NamedItem(self, node: NamedItem) -> Tuple[Optional[str], str]:
        name, call = self.visit(node.item)
        if node.name:
            name = node.name
        return name, call

    def lookahead_call_helper(self, node: Lookahead, positive: int) -> Tuple[None, str]:
        name, call = self.visit(node.node)
        func, args = call.split("(", 1)
        assert args[-1] == ")"
        args = args[:-1]
        if not args.startswith("p,"):
            return None, f"lookahead({positive}, {func}, {args})"
        elif args[2:].strip().isalnum():
            return None, f"lookahead_with_int({positive}, {func}, {args})"
        else:
            return None, f"lookahead_with_string({positive}, {func}, {args})"

    def visit_PositiveLookahead(self, node: PositiveLookahead) -> Tuple[None, str]:
        return self.lookahead_call_helper(node, 1)

    def visit_NegativeLookahead(self, node: NegativeLookahead) -> Tuple[None, str]:
        return self.lookahead_call_helper(node, 0)

    def visit_Opt(self, node: Opt) -> Tuple[str, str]:
        name, call = self.visit(node.node)
        return "opt_var", f"{call}, 1"  # Using comma operator!

    def visit_Repeat0(self, node: Repeat0) -> Tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        name = self.gen.name_loop(node.node, False)
        self.cache[node] = f"{name}_var", f"{name}_rule(p)"
        return self.cache[node]

    def visit_Repeat1(self, node: Repeat1) -> Tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        name = self.gen.name_loop(node.node, True)
        self.cache[node] = f"{name}_var", f"{name}_rule(p)"
        return self.cache[node]

    def visit_Gather(self, node: Gather) -> Tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        name = self.gen.name_gather(node)
        self.cache[node] = f"{name}_var", f"{name}_rule(p)"
        return self.cache[node]

    def visit_Group(self, node: Group) -> Tuple[Optional[str], str]:
        return self.visit(node.rhs)

    def visit_Cut(self, node: Cut) -> Tuple[str, str]:
        return "cut_var", "1"


class CParserGenerator(ParserGenerator, GrammarVisitor):
    def __init__(self, grammar: grammar.Grammar, file: Optional[IO[Text]], debug: bool = False):
        super().__init__(grammar, file)
        self.callmakervisitor = CCallMakerVisitor(self)
        self._varname_counter = 0
        self.debug = debug

    def unique_varname(self, name: str = "tmpvar") -> str:
        new_var = name + "_" + str(self._varname_counter)
        self._varname_counter += 1
        return new_var

    def call_with_errorcheck_return(self, call_text: str, returnval: str) -> None:
        error_var = self.unique_varname()
        self.print(f"int {error_var} = {call_text};")
        self.print(f"if ({error_var}) {{")
        with self.indent():
            self.print(f"return {returnval};")
        self.print(f"}}")

    def call_with_errorcheck_goto(self, call_text: str, goto_target: str) -> None:
        error_var = self.unique_varname()
        self.print(f"int {error_var} = {call_text};")
        self.print(f"if ({error_var}) {{")
        with self.indent():
            self.print(f"goto {goto_target};")
        self.print(f"}}")

    def out_of_memory_return(
        self, expr: str, returnval: str, message: str = "Parser out of memory"
    ) -> None:
        self.print(f"if ({expr}) {{")
        with self.indent():
            self.print(f'PyErr_Format(PyExc_MemoryError, "{message}");')
            self.print(f"return {returnval};")
        self.print(f"}}")

    def out_of_memory_goto(
        self, expr: str, goto_target: str, message: str = "Parser out of memory"
    ) -> None:
        self.print(f"if ({expr}) {{")
        with self.indent():
            self.print(f'PyErr_Format(PyExc_MemoryError, "{message}");')
            self.print(f"goto {goto_target};")
        self.print(f"}}")

    def generate(self, filename: str) -> None:
        self.collect_todo()
        self.print(f"// @generated by pegen.py from {filename}")
        header = self.grammar.metas.get("header", EXTENSION_PREFIX)
        if header:
            self.print(header.rstrip("\n"))
        subheader = self.grammar.metas.get("subheader", "")
        if subheader:
            self.print(subheader)
        for i, rulename in enumerate(self.todo, 1000):
            self.print(f"#define {rulename}_type {i}")
        self.print()
        for rulename, rule in self.todo.items():
            if rule.is_loop() or rule.is_gather():
                type = "asdl_seq *"
            elif rule.type:
                type = rule.type + " "
            else:
                type = "void *"
            self.print(f"static {type}{rulename}_rule(Parser *p);")
        self.print()
        while self.todo:
            for rulename, rule in list(self.todo.items()):
                del self.todo[rulename]
                self.print()
                self.visit(rule)
        mode = int(self.rules["start"].type == "mod_ty")
        modulename = self.grammar.metas.get("modulename", "parse")
        trailer = self.grammar.metas.get("trailer", EXTENSION_SUFFIX)
        if trailer:
            self.print(trailer.rstrip("\n") % dict(mode=mode, modulename=modulename))

    def _set_up_token_start_metadata_extraction(self) -> None:
        self.print("if (p->mark == p->fill && fill_token(p) < 0) {")
        with self.indent():
            self.print("return NULL;")
        self.print("}")
        self.print("int start_lineno = p->tokens[mark]->lineno;")
        self.print("UNUSED(start_lineno); // Only used by EXTRA macro")
        self.print("int start_col_offset = p->tokens[mark]->col_offset;")
        self.print("UNUSED(start_col_offset); // Only used by EXTRA macro")

    def _set_up_token_end_metadata_extraction(self) -> None:
        self.print("Token *token = get_last_nonnwhitespace_token(p);")
        self.print("if (token == NULL) {")
        with self.indent():
            self.print("return NULL;")
        self.print("}")
        self.print(f"int end_lineno = token->end_lineno;")
        self.print("UNUSED(end_lineno); // Only used by EXTRA macro")
        self.print(f"int end_col_offset = token->end_col_offset;")
        self.print("UNUSED(end_col_offset); // Only used by EXTRA macro")

    def _set_up_rule_memoization(self, node: Rule, result_type: str) -> None:
        self.print("{")
        with self.indent():
            self.print(f"{result_type} res = NULL;")
            self.print(f"if (is_memoized(p, {node.name}_type, &res))")
            with self.indent():
                self.print("return res;")
            self.print("int mark = p->mark;")
            self.print("int resmark = p->mark;")
            self.print("while (1) {")
            with self.indent():
                self.call_with_errorcheck_return(
                    f"update_memo(p, mark, {node.name}_type, res)", "res"
                )
                self.print("p->mark = mark;")
                self.print(f"void *raw = {node.name}_raw(p);")
                self.print("if (raw == NULL || p->mark <= resmark)")
                with self.indent():
                    self.print("break;")
                self.print("resmark = p->mark;")
                self.print("res = raw;")
            self.print("}")
            self.print("p->mark = resmark;")
            self.print("return res;")
        self.print("}")
        self.print(f"static {result_type}")
        self.print(f"{node.name}_raw(Parser *p)")

    def _handle_default_rule_body(self, node: Rule, rhs: Rhs, result_type: str) -> None:
        memoize = not node.left_recursive

        with self.indent():
            self.print(f"{result_type} res = NULL;")
            if memoize:
                self.print(f"if (is_memoized(p, {node.name}_type, &res))")
                with self.indent():
                    self.print("return res;")
            self.print("int mark = p->mark;")
            self._set_up_token_start_metadata_extraction()
            self.visit(
                rhs,
                is_loop=False,
                is_gather=node.is_gather(),
                rulename=node.name if memoize else None,
            )
            if self.debug:
                self.print(f'fprintf(stderr, "Fail at %d: {node.name}\\n", p->mark);')
            self.print("res = NULL;")
        self.print("  done:")
        with self.indent():
            if memoize:
                self.print(f"insert_memo(p, mark, {node.name}_type, res);")
            self.print("return res;")

    def _handle_loop_rule_body(self, node: Rule, rhs: Rhs) -> None:
        memoize = not node.left_recursive
        is_repeat1 = node.name.startswith("_loop1")

        with self.indent():
            self.print(f"void *res = NULL;")
            if memoize:
                self.print(f"if (is_memoized(p, {node.name}_type, &res))")
                with self.indent():
                    self.print("return res;")
            self.print("int mark = p->mark;")
            self.print("void **children = PyMem_Malloc(0);")
            self.out_of_memory_return(f"!children", "NULL")
            self.print("ssize_t n = 0;")
            self._set_up_token_start_metadata_extraction()
            self.visit(
                rhs,
                is_loop=True,
                is_gather=node.is_gather(),
                rulename=node.name if memoize else None,
            )
            if is_repeat1:
                self.print("if (n == 0) {")
                with self.indent():
                    self.print("PyMem_Free(children);")
                    self.print("return NULL;")
                self.print("}")
            self.print("asdl_seq *seq = _Py_asdl_seq_new(n, p->arena);")
            self.out_of_memory_return(f"!seq", "NULL", message=f"asdl_seq_new {node.name}")
            self.print("for (int i = 0; i < n; i++) asdl_seq_SET(seq, i, children[i]);")
            self.print("PyMem_Free(children);")
            if node.name:
                self.print(f"insert_memo(p, mark, {node.name}_type, seq);")
            self.print("return seq;")

    def visit_Rule(self, node: Rule) -> None:
        is_loop = node.is_loop()
        is_gather = node.is_gather()
        rhs = node.flatten()
        if is_loop or is_gather:
            result_type = "asdl_seq *"
        elif node.type:
            result_type = node.type
        else:
            result_type = "void *"

        for line in str(node).splitlines():
            self.print(f"// {line}")
        if node.left_recursive and node.leader:
            self.print(f"static {result_type} {node.name}_raw(Parser *);")

        self.print(f"static {result_type}")
        self.print(f"{node.name}_rule(Parser *p)")

        if node.left_recursive and node.leader:
            self._set_up_rule_memoization(node, result_type)

        self.print("{")
        if is_loop:
            self._handle_loop_rule_body(node, rhs)
        else:
            self._handle_default_rule_body(node, rhs, result_type)
        self.print("}")

    def visit_NamedItem(self, node: NamedItem, names: List[str]) -> None:
        name, call = self.callmakervisitor.visit(node)
        if not name:
            self.print(call)
        else:
            name = dedupe(name, names)
            self.print(f"({name} = {call})")

    def visit_Rhs(
        self, node: Rhs, is_loop: bool, is_gather: bool, rulename: Optional[str]
    ) -> None:
        if is_loop:
            assert len(node.alts) == 1
        for alt in node.alts:
            self.visit(alt, is_loop=is_loop, is_gather=is_gather, rulename=rulename)

    def visit_Alt(
        self, node: Alt, is_loop: bool, is_gather: bool, rulename: Optional[str]
    ) -> None:
        self.print(f"{{ // {node}")
        with self.indent():
            vars = self.collect_vars(node)
            for v, type in sorted(item for item in vars.items() if item[0] is not None):
                if not type:
                    type = "void *"
                else:
                    type += " "
                if v == "cut_var":
                    v += " = 0"  # cut_var must be initialized
                self.print(f"{type}{v};")
            names: List[str] = []
            if is_loop:
                self.print("while (")
            else:
                self.print("if (")
            with self.indent():
                first = True
                for item in node.items:
                    if first:
                        first = False
                    else:
                        self.print("&&")
                    self.visit(item, names=names)
            self.print(") {")
            with self.indent():
                self._set_up_token_end_metadata_extraction()
                action = node.action
                if not action:
                    if len(names) > 1:
                        if is_gather:
                            assert len(names) == 2
                            self.print(f"res = seq_insert_in_front(p, {names[0]}, {names[1]});")
                        else:
                            if self.debug:
                                self.print(
                                    f'fprintf(stderr, "Hit without action [%d:%d]: %s\\n", mark, p->mark, "{node}");'
                                )
                            self.print(f"res = CONSTRUCTOR(p, {', '.join(names)});")
                    else:
                        if self.debug:
                            self.print(
                                f'fprintf(stderr, "Hit with default action [%d:%d]: %s\\n", mark, p->mark, "{node}");'
                            )
                        self.print(f"res = {names[0]};")
                else:
                    self.print(f"res = {action};")
                    if self.debug:
                        self.print(
                            f'fprintf(stderr, "Hit with action [%d-%d]: %s\\n", mark, p->mark, "{node}");'
                        )
                if is_loop:
                    self.print("children = PyMem_Realloc(children, (n+1)*sizeof(void *));")
                    self.out_of_memory_return(f"!children", "NULL", message=f"realloc {rulename}")
                    self.print(f"children[n++] = res;")
                    self.print("mark = p->mark;")
                else:
                    self.print(f"goto done;")
            self.print("}")
            self.print("p->mark = mark;")
            if "cut_var" in names:
                self.print("if (cut_var) return NULL;")
        self.print("}")

    def collect_vars(self, node: Alt) -> Dict[str, Optional[str]]:
        names: List[str] = []
        types = {}
        for item in node.items:
            name, type = self.add_var(item, names)
            types[name] = type
        return types

    def add_var(self, node: NamedItem, names: List[str]) -> Tuple[str, Optional[str]]:
        name: str
        call: str
        name, call = self.callmakervisitor.visit(node.item)
        type = None
        if not name:
            return name, type
        if name.startswith("cut"):
            return name, "int"
        if name.endswith("_var"):
            rulename = name[:-4]
            rule = self.rules.get(rulename)
            if rule is not None:
                if rule.is_loop() or rule.is_gather():
                    type = "asdl_seq *"
                else:
                    type = rule.type
            elif name.startswith("_loop") or name.startswith("_gather"):
                type = "asdl_seq *"
            elif name == "name_var" or name == "string_var" or name == "number_var":
                type = "expr_ty"
        if node.name:
            name = node.name
        name = dedupe(name, names)
        return name, type
