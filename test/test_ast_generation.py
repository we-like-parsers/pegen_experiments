import ast
import os

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension

PYTHON_SOURCE_FILENAMES = ["pass.py", "multiple_pass.py"]


def create_tmp_extension(tmp_path):
    with open(os.path.join("data", "simpy.gram"), "r") as grammar_file:
        grammar = grammar_file.read()
    grammar = parse_string(grammar, GrammarParser)
    extension = generate_parser_c_extension(grammar, tmp_path)
    return extension


def read_python_source(path):
    with open(path, "r") as file:
        source = file.read()
    return source


def test_ast_generation_on_source_files(tmp_path):
    extension = create_tmp_extension(tmp_path)
    for filename in PYTHON_SOURCE_FILENAMES:
        source = read_python_source(os.path.join("test", "test_data", filename))

        actual_ast = extension.parse_string(source)
        expected_ast = ast.parse(source)
        assert ast.dump(actual_ast) == ast.dump(
            expected_ast
        ), f"Wrong AST generation for file: {filename}"
