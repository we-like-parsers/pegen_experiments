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

    The memo is keyed by input position and function arguments.
    """

    memo = {}

    def memoize_wrapper(self, *args):
        pos = self.mark()
        key = (pos, args)
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
        return res

    return memoize_wrapper
