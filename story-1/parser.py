class Parser:

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def mark(self):
        return self.tokenizer.mark()

    def reset(self, pos):
        self.tokenizer.reset(pos)

    def expect(self, arg):
        if isinstance(arg, int):
            return self.expect_type(arg)
        elif isinstance(arg, str):
            return self.expect_string(arg)
        else:
            assert False

    def expect_type(self, type):
        if self.tokenizer.peek_token().type == type:
            return self.tokenizer.get_token()
        return None

    def expect_string(self, string):
        token = self.tokenizer.peek_token()
        if token.string == string:
            return self.tokenizer.get_token()
        return None

