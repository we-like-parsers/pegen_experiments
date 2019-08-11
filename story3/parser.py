from story3.memo import memoize

class Parser:

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.memos = {}

    def mark(self):
        return self.tokenizer.mark()

    def reset(self, pos):
        self.tokenizer.reset(pos)

    def show_rule(self, name, alts):
        # alts is a list of lists of strings
        vis = self.tokenizer.vis
        if vis:
            vis.show_rule(name, alts)

    def show_index(self, alt_index, item_index, num_items=1):
        vis = self.tokenizer.vis
        if vis:
            vis.show_index(alt_index, item_index, num_items)
        return True

    @memoize
    def expect(self, arg):
        token = self.tokenizer.peek_token()
        if token.type == arg or token.string == arg:
            return self.tokenizer.get_token()
        return None
