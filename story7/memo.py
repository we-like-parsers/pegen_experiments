def memoize(func):
    """Memoize a parsing method.

    The functon must be a method on a class deriving from Parser.

    The method must have either no arguments or a single argument that
    is an int or str (the latter being the case for expect()).

    It must return either None or an object that is not modified (at
    least not while we're parsing).

    We memoize positive and negative outcomes per input position.

    The function is expected to move the input position iff it returns
    a not-None value.

    The memo is structured as a dict of dict, the outer dict indexed
    by input position, the inner by function and arguments.
    """

    def memoize_wrapper(self, *args):
        vis = self.tokenizer.vis
        pos = self.mark()
        if vis is not None:
            vis.show_call(pos, func.__name__, args)
        memo = self.memos.get(pos)
        if memo is None:
            memo = self.memos[pos] = {}
        key = (func, args)
        if key in memo:
            res, endpos = memo[key]
            self.reset(endpos)
        else:
            res = func(self, *args)
            endpos = self.mark()
            if res is None:
                assert endpos == pos
            else:
                assert endpos > pos
            memo[key] = res, endpos
        if vis is not None:
            vis.show_return(pos, res, endpos)
        return res

    return memoize_wrapper


def no_memoize(func):
    """Like @memoize but doesn't use cache."""

    def memoize_wrapper(self, *args):
        vis = self.tokenizer.vis
        pos = self.mark()
        if vis is not None:
            vis.show_call(pos, func.__name__, args)
        res = func(self, *args)
        endpos = self.mark()
        if res is None:
            assert endpos == pos
        else:
            assert endpos > pos
        if vis is not None:
            vis.show_return(pos, res, endpos)
        return res

    return memoize_wrapper


def memoize_left_rec(func):
    """Memoize a left-recursive parsing method.

    This is similar to @memoize but loops until no longer parse is obtained.

    Inspired by https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion
    """

    def memoize_left_rec_wrapper(self, *args):
        vis = self.tokenizer.vis
        pos = self.mark()
        if vis is not None:
            vis.show_call(pos, "*" + func.__name__, args)
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
            if vis is not None:
                vis.stuff_cache(pos, "*" + func.__name__, args, None)

            # Loop until no longer parse is obtained.
            while True:
                self.reset(pos)
                res = func(self, *args)
                endpos = self.mark()
                if endpos <= lastpos:
                    break
                memo[key] = lastres, lastpos = res, endpos
                if vis is not None:
                    vis.stuff_cache(pos, "*" + func.__name__, args, res)

            res = lastres
            self.reset(lastpos)

        if vis is not None:
            vis.show_return(pos, res, endpos)
        return res

    return memoize_left_rec_wrapper
