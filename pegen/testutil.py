import importlib.util
import io
import sys
import textwrap
import tokenize

from pegen.build import compile_c_extension
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.c_generator import CParserGenerator
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Tokenizer, grammar_tokenizer


def generate_parser(rules):
    # Generate a parser.
    out = io.StringIO()
    genr = PythonParserGenerator(rules, out)
    genr.generate("<string>")

    # Load the generated parser class.
    ns = {}
    exec(out.getvalue(), ns)
    return ns["GeneratedParser"]


def run_parser(file, parser_class, *, verbose=False):
    # Run a parser on a file (stream).
    # Note that this always recognizes {...} as CURLY_STUFF.
    tokenizer = Tokenizer(grammar_tokenizer(tokenize.generate_tokens(file.readline)))
    parser = parser_class(tokenizer, verbose=verbose)
    result = parser.start()
    if result is None:
        raise parser.make_syntax_error()
    return result


def parse_string(source, parser_class, *, dedent=True, verbose=False):
    # Run the parser on a string.
    if dedent:
        source = textwrap.dedent(source)
    file = io.StringIO(source)
    return run_parser(file, parser_class, verbose=verbose)


def make_parser(source):
    # Combine parse_string() and generate_parser().
    rules = parse_string(source, GrammarParser).rules
    return generate_parser(rules)


def import_file(full_name, path):
    """Import a python module from a path"""

    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(mod)
    return mod


def generate_parser_c_extension(rules, path):
    """Generate a parser c extension for the given rules in the given path"""
    source = path / "parse.c"
    with open(source, "w") as file:
        genr = CParserGenerator(rules, file)
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
