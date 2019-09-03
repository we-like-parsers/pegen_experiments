import curses
import sys
import time
import token
import tokenize

from story6.node import alt_repr


class Visualizer:

    def __init__(self):
        self.offsets = [0]
        self.cursor_x = 0
        self.symbols = []
        self.stack = []
        self.cache = []
        self.past = []
        self.future = []
        self.w = curses.initscr()
        curses.noecho()
        self.w.keypad(True)
        self.vis_tokens([], 0)
        self.going = True
        self.display_and_wait()

    def close(self):
        curses.echo()
        curses.endwin()

    def get_state(self):
        return (self.cursor_x, self.symbols[:], self.stack[:], self.cache[:])

    def set_state(self, state):
        self.cursor_x, self.symbols, self.stack, self.cache = state

    def wait(self):
        while True:
            key = self.w.getch()
            if key == ord('q'):
                self.close()
                sys.exit(0)
            if key == ord('b') or key == curses.KEY_BACKSPACE or key == 127 or key == curses.KEY_DC or key == curses.KEY_LEFT:
                if self.past:
                    self.future.append(self.get_state())
                    self.set_state(self.past.pop())
                    self.display()
                    continue
                else:
                    curses.flash()
                    continue
            if key == ord('f') or key == ord(' ') or key == curses.KEY_RIGHT:
                if self.future:
                    self.past.append(self.get_state())
                    self.set_state(self.future.pop())
                    self.display()
                    continue
                else:
                    if self.going:
                        self.past.append(self.get_state())
                    ## else:
                    ##     curses.flash()
                    return
            w = self.w
            w.move(curses.LINES - 1, max(0, curses.COLS - 10))
            w.addstr(f"[{key}]")
            curses.beep()  # Unrecognized input.

    def done(self):
        self.going = False
        while True:
            curses.flash()
            self.wait()

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
        self.cursor_x = offsets[pos]

    def display(self):
        w = self.w
        w.move(0, 0)
        w.clrtobot()
        y = (curses.LINES // 2 - 1) - len(self.stack)
        clip = 0
        if y < 0:
            clip = -y
            y = 0
        for (pos, s, res), rule in self.stack[clip:]:
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
                        if alt_i == alt_index and item_index < item_i < item_index + num_items:
                            attr = curses.A_UNDERLINE
                        else:
                            attr = 0
                        w.addnstr(" ", curses.COLS - x, attr)
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

        w.addstr(y, 0, "-"*curses.COLS)
        y += 1

        cursor_y = y
        w.addnstr(y, 0, " ".join(self.symbols), curses.COLS)
        y += 1

        w.addstr(y, 0, "-"*curses.COLS)
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

        w.move(cursor_y, min(curses.COLS - 1, self.cursor_x))

    def display_and_wait(self):
        self.display()
        self.wait()

    def call_repr(self, name, args):
        if name == 'expect' and len(args) == 1:
            if isinstance(args[0], int):
                s = f"{name}({token.tok_name.get(args[0], str(args[0]))})"
            else:
                s = f"{name}({args[0]!r})"
        else:
            s = name + str(args)
        return s

    def show_call(self, pos, name, args):
        while self.stack and self.stack[-1][0][-1]:
            val, rule = self.stack.pop()
            v2 = val[:2]
            self.cache[:] = [v for v in self.cache if v[:2] != v2]
            self.cache.append(val)
        w = self.w
        s = self.call_repr(name, args)
        val = (pos, s, None)
        self.stack.append((val, None))
        if val in self.cache:
            self.cache.remove(val)
        self.display_and_wait()

    def stuff_cache(self, pos, name, args, res):
        res = alt_repr(res)
        s = self.call_repr(name, args)
        v2 = (pos, s)
        self.cache[:] = [v for v in self.cache if v[:2] != v2]
        self.cache.append((pos, s, res))
        self.display_and_wait()

    def show_rule(self, name, alts):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][0][-1]:
            i -= 1
        top, rule = self.stack[i]
        rule = (name, alts, None)
        self.stack[i] = (top, rule)
        self.display_and_wait()

    def show_index(self, alt_index, item_index, num_items):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][0][-1]:
            i -= 1
        top, rule = self.stack[i]
        name, alts, indices = rule
        new_rule = (name, alts, (alt_index, item_index, num_items))
        if new_rule != rule:
            self.stack[i] = top, new_rule
            self.display_and_wait()

    def show_return(self, pos, res, endpos):
        i = len(self.stack) - 1
        while i >= 0 and self.stack[i][0][-1]:
            i -= 1
        top, rule = self.stack[i]
        top_pos, top_s, top_res = top
        top_res = alt_repr(res)
        top = top_pos, top_s, top_res
        self.stack[i] = top, rule
        self.display_and_wait()
