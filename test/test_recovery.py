import io
import tokenize

from data.python_parser import GeneratedParser  # type: ignore
from pegen.testutil import (
    describe_token,
    make_improved_syntax_error,
    recovery_by_deletions,
    recovery_by_insertions,
)
from pegen.tokenizer import Tokenizer
from pegen.parser import Parser


def make_parser(source: str) -> Parser:
    file = io.StringIO(source)
    tokengen = tokenize.generate_tokens(file.readline)
    tokenizer = Tokenizer(tokengen)
    return GeneratedParser(tokenizer)


def test_good_source() -> None:
    parser = make_parser("0")
    tree = parser.start()
    assert (
        str(tree)
        == "[[[[[[[[[[[[[[[[[[[[[[[[[[NUMBER('0')]]]]]]]]]]]]]]]]]]], NEWLINE('')]]]]], ENDMARKER('')]]"
    )


def test_fail_source() -> None:
    parser = make_parser("(a+)")
    tree = parser.start()
    assert tree is None


def test_make_syntax_error() -> None:
    parser = make_parser("(a+)")
    parser.start()
    err = parser.make_syntax_error()
    assert err.args[0] == "pegen parse failure"  # Why not "invalid syntax"?


def test_recovery_by_insertions() -> None:
    parser = make_parser("(a+)")
    parser.start()
    got, reach, expected, howfar = recovery_by_insertions(parser)
    assert got.string == ")"
    assert reach == 7  # ( a + NEW ) \n $
    expected_strings = [t.string for t in expected]
    assert expected_strings == ["NAME", "NUMBER", "STRING", "...", "False", "None", "True"]


def test_fail_to_insert() -> None:
    parser = make_parser("(a;)")
    parser.start()
    got, reach, expected, howfar = recovery_by_insertions(parser)
    assert got.string == ";"
    assert reach == 5  # ( a ) ; )
    expected_strings = {t.string for t in expected}
    assert expected_strings == {")"}


def test_recovery_by_deletions() -> None:
    parser = make_parser("(a;)")
    parser.start()
    results = recovery_by_deletions(parser)
    assert len(results) == 1
    tok, i, pos, reach = results[0]
    assert tok.string == ";"
    assert i == 0
    assert pos == 2
    assert reach == 5  # ( a ) \n $


def test_recovery_by_deletions_backup() -> None:
    parser = make_parser("(a+)")
    parser.start()
    results = recovery_by_deletions(parser)
    assert len(results) == 1
    tok, i, pos, reach = results[0]
    assert tok.string == "+"
    assert i == 1
    assert pos == 2
    assert reach == 5  # ( a ) \n $


def test_make_improved_syntax_error() -> None:
    parser = make_parser("(a+)")
    parser.start()
    err = make_improved_syntax_error(parser)
    assert (
        err.args[0]
        == "invalid syntax (expected one of NAME, NUMBER, STRING, '...', 'False', 'None', 'True')"
    )


def test_bad_unindent_during_recovery() -> None:
    # Catch IndentationError("unindent does not match any outer indentation
    # level") raised in tokenize.py
    # fmt: off
    parser = make_parser(
        "if 1:\n"
        "    while 1\n"
        "  pass\n"
    )
    # fmt: on
    parser.start()
    err = make_improved_syntax_error(parser)
    assert err.args[0] == "invalid syntax (expected one of ':')"


def test_unexpected_eof_during_recovery() -> None:
    # Catch TokenError("EOF in multi-line statement") raised in tokenize.py
    # (this really means "not enough close parentheses")
    parser = make_parser("{")
    parser.start()
    err = make_improved_syntax_error(parser)


def test_eof_in_multiline_string_during_recovery() -> None:
    # Catch TokenError("EOF in multi-line string") raised in tokenize.py
    parser = make_parser("'''")
    parser.start()
    err = make_improved_syntax_error(parser)


def test_very_long_arg_list() -> None:
    # This raises RecursionError for n >= 222
    n = 221
    args = ", ".join(map(str, range(n)))
    source = f"A({args})"
    parser = make_parser(source)
    parser.start()
    err = make_improved_syntax_error(parser)
