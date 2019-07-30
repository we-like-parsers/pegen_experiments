from story2.memo import memoize

class Parser:

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.memos = {}

    def mark(self):
        return self.tokenizer.mark()

    def reset(self, pos):
        self.tokenizer.reset(pos)

    @memoize
    def expect(self, arg):
        token = self.tokenizer.peek_token()
        if token.type == arg or token.string == arg:
            return self.tokenizer.get_token()
        return None
