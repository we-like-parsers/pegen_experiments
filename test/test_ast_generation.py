import ast
import os
from pathlib import PurePath
from typing import Any

import pytest  # type: ignore

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


@pytest.fixture(scope="module")
def parser_extension(tmp_path_factory: Any) -> Any:
    tmp_path = tmp_path_factory.mktemp("extension")
    extension = create_tmp_extension(tmp_path)
    return extension


@pytest.mark.parametrize("filename", PYTHON_SOURCE_FILENAMES)
def test_ast_generation_on_source_files(parser_extension: Any, filename: PurePath) -> None:
    if filename == "group.py":
        pytest.skip("AST Generation for groups can fail. See #107 on Github.")
    source = read_python_source(os.path.join(TEST_DIR, filename))

    actual_ast = parser_extension.parse_string(source)
    expected_ast = ast.parse(source)
    assert ast.dump(actual_ast, include_attributes=True) == ast.dump(
        expected_ast, include_attributes=True
    ), f"Wrong AST generation for file: {filename}"


@pytest.mark.xfail(strict=True)
def test_ast_generation_group(parser_extension: Any) -> None:
    source = read_python_source(os.path.join(TEST_DIR, "group.py"))

    actual_ast = parser_extension.parse_string(source)
    expected_ast = ast.parse(source)
    assert ast.dump(actual_ast, include_attributes=True) == ast.dump(
        expected_ast, include_attributes=True
    ), f"Wrong AST generation for file: group.py"
