import curses
import sys
import time
import token
import tokenize

from story3.node import alt_repr


class Visualizer:

    def __init__(self):
        self.offsets = [0]
        self.cursor = 0, 0
        self.stack = []
        self.cache = []
        self.w = curses.initscr()
        curses.noecho()
        self.vis_tokens([], 0)

    def close(self):
        curses.echo()
        curses.endwin()

    def wait(self):
        if chr(self.w.getch()) in 'qQ':
            sys.exit(0)

    def vis_tokens(self, tokens, pos):
        w = self.w
        symbols = []
        for t in tokens:
            s = alt_repr(t)
            symbols.append(s)
        self.symbols = symbols
        offset = 0
        offsets = [offset]
        for s in symbols:
            offset += len(s) + 1
            offsets.append(offset)
        self.offsets = offsets
        self.display_stack()
        w.move(0, 0)
        w.clrtobot()
        w.addstr(" ".join(symbols))
        self.cursor = 0, offsets[pos]
        self.display_stack()

    def display_stack(self):
        w = self.w
        w.move(4, 0)
        w.clrtobot()
        i = 4
        for pos, s, res in self.stack:
            if self.offsets[pos] >= curses.COLS:
                continue
            if res:
                s += " -> " + res
            if self.offsets[pos] + len(s) > curses.COLS:
                s = s[:curses.COLS - self.offsets[pos]]
            w.addstr(i, self.offsets[pos], s)
            i += 1
        i += 3
        for pos, s, res in reversed(self.cache):
            if i >= curses.LINES:
                break
            if self.offsets[pos] >= curses.COLS:
                continue
            if res:
                s += " -> " + res
            if self.offsets[pos] + len(s) > curses.COLS:
                s = s[:curses.COLS - self.offsets[pos]]
            w.addstr(i, self.offsets[pos], s)
            i += 1
        w.move(*self.cursor)

    def show_call(self, pos, name, args):
        while self.stack and self.stack[-1][-1]:
            val = self.stack.pop()
            if val in self.cache:
                self.cache.remove(val)
            self.cache.append(val)
        w = self.w
        if name == 'expect' and len(args) == 1:
            if isinstance(args[0], int):
                s = f"{name}({token.tok_name.get(args[0], str(args[0]))})"
            else:
                s = f"{name}({args[0]!r})"
        else:
            s = name + str(args)
        self.stack.append((pos, s, None))
        self.display_stack()
        self.wait()

    def show_return(self, pos, res, endpos):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][-1]:
            i -= 1
        self.stack[i] = self.stack[i][:2] + (alt_repr(res),)
        self.display_stack()
        self.wait()
