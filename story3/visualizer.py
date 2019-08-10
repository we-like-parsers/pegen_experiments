import curses
import sys
import time
import token
import tokenize

from story3.node import alt_repr


class Visualizer:

    def __init__(self):
        self.offsets = [0]
        self.cursor_y, self.cursor_x = 0, 0
        self.stack = []
        self.cache = []
        self.w = curses.initscr()
        curses.start_color()
        curses.noecho()
        self.w.keypad(True)
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
        w.addstr("Tokenization buffer:", curses.A_REVERSE)
        w.move(1, 0)
        w.addstr(" ".join(symbols))
        y, x = divmod(offsets[pos], curses.COLS)
        self.cursor_y, self.cursor_x = 1 + y, x
        self.display_stack()

    def display_stack(self):
        w = self.w
        i = self.cursor_y
        i += 2
        w.move(i, 0)
        w.clrtobot()
        w.addstr(i, 0, "Parsing stack:", curses.A_REVERSE)
        i += 1
        for pos, s, res in self.stack:
            if self.offsets[pos] >= curses.COLS:
                continue
            if res:
                s += " -> " + res
            w.addnstr(i, self.offsets[pos], s, curses.COLS - self.offsets[pos])
            i += 1
        i += 1
        w.addstr(i, 0, "Memoization cache:", curses.A_REVERSE)
        i += 1
        for pos, s, res in reversed(self.cache):
            if i >= curses.LINES:
                break
            if self.offsets[pos] >= curses.COLS:
                continue
            if res:
                s += " -> " + res
            w.addnstr(i, self.offsets[pos], s, curses.COLS - self.offsets[pos])
            i += 1
        w.move(self.cursor_y, self.cursor_x)

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
