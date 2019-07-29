class Tokenizer:

    def __init__(self, tokengen):
        """Call with tokenize.generate_tokens(...)."""
        self.tokengen = tokengen
        self.tokens = []
        self.pos = 0

    def mark(self):
        return self.pos

    def reset(self, pos):
        self.pos = pos

    def get_token(self):
        token = self.peek_token()
        self.pos += 1
        return token

    def peek_token(self):
        if self.pos == len(self.tokens):
            self.tokens.append(next(self.tokengen))
        return self.tokens[self.pos]
