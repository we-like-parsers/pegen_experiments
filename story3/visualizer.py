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
        y = self.cursor_y
        y += 2
        w.move(y, 0)
        w.clrtobot()
        w.addstr(y, 0, "Parsing stack:", curses.A_REVERSE)
        y += 1
        for (pos, s, res), rule in self.stack:
            if rule and not res:
                name, alts, indices = rule
                x = self.offsets[pos]
                w.move(y, x)
                w.addnstr(name + ":", curses.COLS - x)
                y, x = w.getyx()
                if not indices:
                    indices = 0, 0, 0
                alt_index, item_index, num_items = indices
                for alt_i, alt in enumerate(alts):
                    if alt_i > 0:
                        w.addnstr(" |", curses.COLS - x)
                        y, x = w.getyx()
                    for item_i, item in enumerate(alt):
                        w.addnstr(" ", curses.COLS - x)
                        y, x = w.getyx()
                        if alt_i == alt_index and item_index <= item_i < item_index + num_items:
                            attr = curses.A_UNDERLINE
                        else:
                            attr = 0
                        w.addnstr(item, curses.COLS - x, attr)
                        y, x = w.getyx()
                    
            else:
                if self.offsets[pos] >= curses.COLS:
                    continue
                if res:
                    s += " -> " + res
                w.addnstr(y, self.offsets[pos], s, curses.COLS - self.offsets[pos])
            y += 1
        y += 1
        w.addstr(y, 0, "Memoization cache:", curses.A_REVERSE)
        y += 1
        for pos, s, res in reversed(self.cache):
            if y >= curses.LINES:
                break
            if self.offsets[pos] >= curses.COLS:
                continue
            if res:
                s += " -> " + res
            w.addnstr(y, self.offsets[pos], s, curses.COLS - self.offsets[pos])
            y += 1
        w.move(self.cursor_y, self.cursor_x)

    def show_call(self, pos, name, args):
        while self.stack and self.stack[-1][0][-1]:
            val, rule = self.stack.pop()
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
        self.stack.append(((pos, s, None), None))
        self.display_stack()
        self.wait()

    def show_rule(self, name, alts):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][0][-1]:
            i -= 1
        top, rule = self.stack[i]
        rule = (name, alts, None)
        self.stack[i] = (top, rule)
        self.display_stack()
        self.wait()

    def show_index(self, alt_index, item_index, num_items):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][0][-1]:
            i -= 1
        top, rule = self.stack[i]
        name, alts, indices = rule
        rule = (name, alts, (alt_index, item_index, num_items))
        self.stack[i] = top, rule


    def show_return(self, pos, res, endpos):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][0][-1]:
            i -= 1
        top, rule = self.stack[i]
        top_pos, top_s, top_res = top
        top_res = alt_repr(res)
        top = top_pos, top_s, top_res
        self.stack[i] = top, rule
        self.display_stack()
        self.wait()
