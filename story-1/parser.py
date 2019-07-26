class Parser:

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def mark(self):
        return self.tokenizer.mark()

    def reset(self, pos):
        self.tokenizer.reset(pos)

    def expect(self, arg):
        token = self.tokenizer.peek_token()
        if ((isinstance(arg, int) and token.type == arg) or
            (isinstance(arg, str) and token.string == arg)):
            return self.tokenizer.get_token()
        return None
