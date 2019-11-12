import ast
import os
from pathlib import PurePath
from typing import Any

import pytest

from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.testutil import parse_string, generate_parser_c_extension

TEST_DIR = os.path.join("test", "test_data")
PYTHON_SOURCE_FILENAMES = sorted(
    filename for filename in os.listdir(TEST_DIR) if filename.endswith(".py")
)


def create_tmp_extension(tmp_path: PurePath) -> Any:
    with open(os.path.join("data", "simpy.gram"), "r") as grammar_file:
        grammar_source = grammar_file.read()
    grammar = parse_string(grammar_source, GrammarParser)
    extension = generate_parser_c_extension(grammar, tmp_path)
    return extension


def read_python_source(path: str) -> str:
    with open(path, "r") as file:
        source = file.read()
    return source


@pytest.mark.parametrize("filename", PYTHON_SOURCE_FILENAMES)
def test_ast_generation_on_source_files(tmp_path: PurePath, filename: PurePath) -> None:
    extension = create_tmp_extension(tmp_path)
    print()
    print(filename)
    source = read_python_source(os.path.join(TEST_DIR, filename))

    actual_ast = extension.parse_string(source)
    expected_ast = ast.parse(source)
    assert ast.dump(actual_ast, include_attributes=True) == ast.dump(
        expected_ast, include_attributes=True
    ), f"Wrong AST generation for file: {filename}"
