def memoize_left_rec(func):

    def memoize_left_rec_wrapper(self, *args):
        pos = self.mark()
        memo = self.memos.get(pos)
        if memo is None:
            memo = self.memos[pos] = {}
        key = (func, args)
        if key in memo:
            res, endpos = memo[key]
            self.reset(endpos)
        else:
            # This is where we deviate from @memoize.

            # Prime the cache with a failure.
            memo[key] = lastres, lastpos = None, pos

            # Loop until no longer parse is obtained.
            while True:
                self.reset(pos)
                res = func(self, *args)
                endpos = self.mark()
                if endpos <= lastpos:
                    break
                memo[key] = lastres, lastpos = res, endpos

            res = lastres
            self.reset(lastpos)

        return res

    return memoize_left_rec_wrapper
