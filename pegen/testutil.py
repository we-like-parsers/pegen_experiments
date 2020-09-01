import importlib.util
import io
import os
import pathlib
import sys
import textwrap
import tokenize
import token

from typing import Any, cast, Dict, Final, IO, List, Tuple, Type

from pegen.build import compile_c_extension
from pegen.c_generator import CParserGenerator
from pegen.grammar import Grammar
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.parser import Parser
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Mark, Tokenizer

ALL_TOKENS = token.tok_name
EXACT_TOKENS = token.EXACT_TOKEN_TYPES  # type: ignore
NON_EXACT_TOKENS = {
    name for index, name in token.tok_name.items() if index not in EXACT_TOKENS.values()
}


def generate_parser(grammar: Grammar) -> Type[Parser]:
    # Generate a parser.
    out = io.StringIO()
    genr = PythonParserGenerator(grammar, out)
    genr.generate("<string>")

    # Load the generated parser class.
    ns: Dict[str, Any] = {}
    exec(out.getvalue(), ns)
    return ns["GeneratedParser"]


def run_parser(file: IO[bytes], parser_class: Type[Parser], *, verbose: bool = False) -> Any:
    # Run a parser on a file (stream).
    tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))  # type: ignore # typeshed issue #3515
    parser = parser_class(tokenizer, verbose=verbose)
    result = parser.start()
    if result is None:
        raise parser.make_syntax_error()
    return result


def parse_string(
    source: str, parser_class: Type[Parser], *, dedent: bool = True, verbose: bool = False
) -> Any:
    # Run the parser on a string.
    if dedent:
        source = textwrap.dedent(source)
    file = io.StringIO(source)
    return run_parser(file, parser_class, verbose=verbose)  # type: ignore # typeshed issue #3515


def make_parser(source: str) -> Type[Parser]:
    # Combine parse_string() and generate_parser().
    grammar = parse_string(source, GrammarParser)
    return generate_parser(grammar)


def import_file(full_name: str, path: str) -> Any:
    """Import a python module from a path"""

    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)

    # We assume this is not None and has an exec_module() method.
    # See https://docs.python.org/3/reference/import.html?highlight=exec_module#loading
    loader = cast(Any, spec.loader)
    loader.exec_module(mod)
    return mod


def generate_c_parser_source(grammar: Grammar) -> str:
    out = io.StringIO()
    genr = CParserGenerator(grammar, ALL_TOKENS, EXACT_TOKENS, NON_EXACT_TOKENS, out)
    genr.generate("<string>")
    return out.getvalue()


def generate_parser_c_extension(
    grammar: Grammar, path: pathlib.PurePath, debug: bool = False
) -> Any:
    """Generate a parser c extension for the given grammar in the given path

    Returns a module object with a parse_string() method.
    TODO: express that using a Protocol.
    """
    # Make sure that the working directory is empty: reusing non-empty temporary
    # directories when generating extensions can lead to segmentation faults.
    # Check issue #95 (https://github.com/gvanrossum/pegen/issues/95) for more
    # context.
    assert not os.listdir(path)
    source = path / "parse.c"
    with open(source, "w", encoding="utf-8") as file:
        genr = CParserGenerator(
            grammar, ALL_TOKENS, EXACT_TOKENS, NON_EXACT_TOKENS, file, debug=debug
        )
        genr.generate("parse.c")
    extension_path = compile_c_extension(str(source), build_dir=str(path / "build"))
    extension = import_file("parse", extension_path)
    return extension


def print_memstats() -> bool:
    MiB: Final = 2 ** 20
    try:
        import psutil  # type: ignore
    except ImportError:
        return False
    print("Memory stats:")
    process = psutil.Process()
    meminfo = process.memory_info()
    res = {}
    res["rss"] = meminfo.rss / MiB
    res["vms"] = meminfo.vms / MiB
    if sys.platform == "win32":
        res["maxrss"] = meminfo.peak_wset / MiB
    else:
        # See https://stackoverflow.com/questions/938733/total-memory-used-by-python-process
        import resource  # Since it doesn't exist on Windows.

        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            factor = 1
        else:
            factor = 1024  # Linux
        res["maxrss"] = rusage.ru_maxrss * factor / MiB
    for key, value in res.items():
        print(f"  {key:12.12s}: {value:10.0f} MiB")
    return True


def describe_token(tok: tokenize.TokenInfo, parser: Parser) -> str:
    if tok.type == token.ERRORTOKEN:
        return repr(tok.string)
    if tok.type == token.OP:
        return repr(tok.string)
    if tok.type == token.AWAIT:
        return "'await'"
    if tok.type == token.ASYNC:
        return "'async'"
    if tok.string in parser._keywords:
        return repr(tok.string)
    return token.tok_name[tok.type]


def recovery_by_insertions(
    parser: Parser, limit: int = 100
) -> Tuple[
    tokenize.TokenInfo, Mark, List[tokenize.TokenInfo], Dict[Mark, List[tokenize.TokenInfo]]
]:
    tokenizer = parser._tokenizer
    howfar: Dict[int, List[tokenize.TokenInfo]] = {}
    initial_farthest = parser.get_farthest()
    pos = initial_farthest - 1
    got = tokenizer._tokens[pos]
    for i in range(limit):
        parser.reset(0)
        save_farthest = parser.reset_farthest(0)
        parser.clear_excess(pos)
        parser.insert_dummy(pos, i)
        tree = parser.start()
        tok = parser.remove_dummy()
        if tok is None:
            break
        farthest = parser.reset_farthest(save_farthest)
        if tree is not None or farthest > pos:
            howfar.setdefault(farthest, []).append(tok)
    else:
        # TODO: Don't print
        print(f"Stopped after trying {limit} times")
    if howfar:
        # Only report those tokens that got the farthest
        farthest = max(howfar)
        expected = sorted(howfar[farthest])
    else:
        farthest = pos
        expected = []
    return (got, farthest, expected, howfar)


def recovery_by_deletions(
    parser: Parser, limit: int = 2
) -> List[Tuple[tokenize.TokenInfo, int, Mark, Mark]]:
    tokenizer = parser._tokenizer
    # TODO: Don't use len() here, but somehow use get_farthest.
    orig_farthest = parser.get_farthest()
    orig_pos = orig_farthest - 1
    results = []
    for i in range(limit):
        pos = orig_pos - i
        if pos < 0:
            break
        parser.reset(0)
        parser.reset_farthest(0)
        parser.clear_excess(pos)
        tok = parser.delete_token(pos)
        tree = parser.start()
        parser.insert_token(pos, tok)
        farthest = parser.reset_farthest(orig_farthest)
        parser.reset(orig_pos)
        if farthest > orig_farthest:
            results.append((tok, i, pos, farthest))
    return results


def make_improved_syntax_error(parser: Parser, filename: str, limit: int = 100) -> SyntaxError:
    err = parser.make_syntax_error(filename)

    if not isinstance(err, SyntaxError):
        return err

    got, farthest, expected, howfar = recovery_by_insertions(parser, limit=limit)

    if got.type == token.INDENT and len(expected) > 10:  # 10 is pretty arbitrary
        return IndentationError("unexpected indent", *err.args[1:])
    if len(expected) == 1 and expected[0].type == token.INDENT:
        return IndentationError("expected an indented block", *err.args[1:])

    deletions = recovery_by_deletions(parser, limit=1)
    if deletions:
        d_tok, d_index, d_pos, d_farthest = deletions[0]
        if d_farthest >= farthest:
            return err.__class__(f"invalid syntax (unexpected token {describe_token(d_tok, parser)})")

    if isinstance(err, SyntaxError) and err.msg == "pegen parse failure":
        expected_strings = ", ".join([describe_token(tok, parser) for tok in expected])
        return err.__class__(f"invalid syntax (expected one of {expected_strings})", *err.args[1:])

    return err
