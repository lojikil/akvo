
class Lexeme(object):
    # holds a Lexeme and has a bunch of
    # helper methods. I'm attempting to
    # avoid a huge hierarchy of Lexeme
    # classes here...

    def __init__(self, lexeme_value, lexeme_type):
        self.lexeme_value = lexeme_value
        self.lexeme_type = lexeme_type

    @staticmethod
    def new_key(lv):
        return Lexeme(lv, 0)

    def is_key(self):
        return self.lexeme_type == 0

    @staticmethod
    def new_keyword(lv):
        return Lexeme(lv, 1)

    def is_keyword(self):
        return self.lexeme_type == 1

    @staticmethod
    def new_string(lv):
        return Lexeme(lv, 2)

    def is_string(self):
        return self.lexeme_type == 2

    @staticmethod
    def new_int(lv):
        return Lexeme(lv, 3)

    def is_int(self):
        return self.lexeme_type == 3

    @staticmethod
    def new_hex(lv):
        return Lexeme(lv, 4)

    def is_hex(self):
        return self.lexeme_type == 4

    @staticmethod
    def new_oct(lv):
        return Lexeme(lv, 5)

    def is_oct(self):
        return self.lexeme_type == 5

    @staticmethod
    def new_bin(lv):
        return Lexeme(lv, 6)

    def is_bin(self):
        return self.lexeme_type == 6

    @staticmethod
    def new_float(lv):
        return Lexeme(lv, 7)

    def is_float(self):
        return self.lexeme_type == 7

    @staticmethod
    def new_char(lv):
        return Lexeme(lv, 8)

    def is_char(self):
        return self.lexeme_type == 8

    @staticmethod
    def new_sym(lv):
        return Lexeme(lv, 9)

    def is_sym(self):
        return self.lexeme_type == 9


class ExpressionReader(object):
    def __init__(self, src):
        self.src = src
        self.whitespace = [" ", "\t", "\n", "\r"]

        # May not be the best for large
        # buffers, but it does allow us
        # a simple mechanism for reading
        if type(src) is str:
            self.buffer = src
        else:
            self.buffer = src.read()

        self.curpos = 0

    def iswhite(self, c):
        return c in self.whitespace


class SExpressionReader(ExpressionReader):
    def read(self):

        # eat whitespace; we could just trim(),
        # but that would miss interstitial
        # whitespace, and would be a bit ineffiecient
        while self.iswhite(self.buffer[self.curpos]):
            self.curpos += 1

        if self.buffer[self.curpos] is "(":
            return self.read_expression()
        elif self.buffer[self.curpos] is "[":
            return self.read_array()
        # need end detection like #\] and such
        # should return a Lexeme there...
        elif self.buffer[self.curpos] is "\"":
            return self.read_string()
        elif self.buffer[self.curpos] is "#":
            return self.read_sharp()
        elif self.buffer[self.curpos] is "'":
            # this isn't needed, since we don't
            # really need quoted things in this
            # Scheme, but may as well have it,
            # since I'm sure eventually I'll add
            # some sort of macro...
            return self.read_quote()
        elif self.buffer[self.curpos].isdigit():
            # this should dispatch for all numeric
            # types in this unnamed Scheme...
            # - int: 99
            # - float: 9.9
            # - complex: +9i-9
            # - hex: 0x63
            # - oct: 0o143
            # - bin: 0b1100011
            return self.read_numeric()
        else:
            return self.read_symbol()

    def read_expression(self):
        prep = []
        self.curpos += 1
        head = self.read_symbol()

    def read_numeric(self):
        pass

    def read_array(self):
        pass

    def read_string(self):

        start = self.curpos
        self.curpos += 1

        while self.buffer[self.curpos] != '"':
            if self.buffer[self.curpos] == '\\':
                self.curpos += 1
            self.curpos += 1

            if self.curpos > len(self.buffer):
                return LexError("missing end of string before end of buffer")

        return self.buffer[start:self.curpos]

    def read_symbol(self):
        pass

    def next(self):
        pass


class DExpressionReader(ExpressionReader):
    def read(self):
        pass

    def next(self):
        pass
