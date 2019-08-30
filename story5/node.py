from token import tok_name
from tokenize import TokenInfo


def short_token(tok: TokenInfo) -> str:
    s = tok.string
    if s == '' or s.isspace():
        return tok_name[tok.type]
    else:
        return repr(s)


def alt_repr(x) -> str:
    if isinstance(x, TokenInfo):
        return short_token(x)
    else:
        return repr(x)


class Node:

    def __init__(self, type, children):
        self.type = type
        self.children = children

    def __repr__(self):
        return f"Node({self.type}, [{', '.join(map(alt_repr, self.children))}])"

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return self.type == other.type and self.children == other.children
