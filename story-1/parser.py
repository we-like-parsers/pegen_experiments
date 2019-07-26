class Parser:

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def mark(self):
        return self.tokenizer.mark()

    def reset(self, pos):
        self.tokenizer.reset(pos)

    def expect(self, type):
        if self.tokenizer.peek_token().type == type:
            return self.tokenizer.get_token()
        return None

    def expect_string(self, type, string):
        pos = self.mark()
        token = self.expect(type)
        if token and token.string == string:
            return token
        self.reset(pos)
        return None

