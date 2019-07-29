class Node:

    def __init__(self, type, children):
        self.type = type
        self.children = children

    def __repr__(self):
        return f"Node({self.type}, {self.children})"

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return self.type == other.type and self.children == other.children
