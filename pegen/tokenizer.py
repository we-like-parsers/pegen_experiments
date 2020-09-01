import token
import tokenize
from typing import Any, List, Iterator

Mark = int  # NewType('Mark', int)

exact_token_types = token.EXACT_TOKEN_TYPES  # type: ignore


def shorttok(tok: tokenize.TokenInfo) -> str:
    return "%-25.25s" % f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"


def token_repr(self: Any) -> str:
    return f"{tokenize.tok_name[self.type]}({self.string!r:.25})"


tokenize.TokenInfo.__repr__ = token_repr  # type: ignore


class Tokenizer:
    """Caching wrapper for the tokenize module.

    This is pretty tied to Python's syntax.
    """

    _tokens: List[tokenize.TokenInfo]

    def __init__(self, tokengen: Iterator[tokenize.TokenInfo], *, verbose: bool = False):
        self._tokengen = tokengen
        self._tokens = []
        self._index = 0
        self._farthest = 0
        self._verbose = verbose
        if verbose:
            self.report(False, False)

    def getnext(self) -> tokenize.TokenInfo:
        """Return the next token and updates the index."""
        cached = True
        while self._index == len(self._tokens):
            try:
                tok = next(self._tokengen)
            except (IndentationError, tokenize.TokenError) as err:
                tok = self.fix_token_error(err)
            if tok.type in (tokenize.NL, tokenize.COMMENT):
                continue
            if tok.type == token.ERRORTOKEN and tok.string.isspace():
                continue
            self._tokens.append(tok)
            cached = False
        tok = self._tokens[self._index]
        self._index += 1
        self._farthest = max(self._farthest, self._index)
        if self._verbose:
            self.report(cached, False)
        return tok

    def peek(self) -> tokenize.TokenInfo:
        """Return the next token *without* updating the index."""
        while self._index == len(self._tokens):
            try:
                tok = next(self._tokengen)
            except (IndentationError, tokenize.TokenError) as err:
                tok = self.fix_token_error(err)
            if tok.type in (tokenize.NL, tokenize.COMMENT):
                continue
            if tok.type == token.ERRORTOKEN and tok.string.isspace():
                continue
            self._tokens.append(tok)
        self._farthest = max(self._farthest, self._index + 1)
        return self._tokens[self._index]

    def fix_token_error(self, err: tokenize.TokenError) -> tokenize.TokenInfo:
        msg = err.args[0]
        if msg == "EOF in multi-line statement":
            return tokenize.TokenInfo(token.ENDMARKER, "", (0, 0), (0, 0), "")
        elif msg == "EOF in multi-line string":
            return tokenize.TokenInfo(token.ERRORTOKEN, "", (0, 0), (0, 0), "")
        elif msg == "unindent does not match any outer indentation level":
            return tokenize.TokenInfo(token.ERRORTOKEN, "", (0, 0), (0, 0), "")
        else:
            raise err

    def diagnose(self) -> tokenize.TokenInfo:
        if 1 <= self._farthest <= len(self._tokens):
            return self._tokens[self._farthest - 1]
        # Fall back on last token seen.  TODO: When does this get called?
        assert False, "Shouldn't get here"
        if not self._tokens:
            self.getnext()
        return self._tokens[-1]

    def mark(self) -> Mark:
        return self._index

    def reset(self, index: Mark) -> None:
        if index == self._index:
            return
        assert 0 <= index <= len(self._tokens), (index, len(self._tokens))
        old_index = self._index
        self._index = index
        if self._verbose:
            self.report(True, index < old_index)

    def get_farthest(self) -> Mark:
        return self._farthest

    def update_farthest(self, farthest: Mark) -> None:
        self._farthest = max(self._farthest, farthest)

    def reset_farthest(self, farthest: Mark) -> Mark:
        prior_farthest = self._farthest
        self._farthest = farthest
        return prior_farthest

    def report(self, cached: bool, back: bool) -> None:
        if back:
            fill = "-" * self._index + "-"
        elif cached:
            fill = "-" * self._index + ">"
        else:
            fill = "-" * self._index + "*"
        if self._index == 0:
            print(f"{fill} (Bof)")
        else:
            tok = self._tokens[self._index - 1]
            print(f"{fill} {shorttok(tok)}")
