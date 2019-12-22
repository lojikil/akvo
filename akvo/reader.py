class Lexeme(object):
    # holds a Lexeme and has a bunch of
    # helper methods. I'm attempting to
    # avoid a huge hierarchy of Lexeme
    # classes here...

    breakchars = [';', '{', '}', '[', ']', '(', ')', '"']
    whitespace = [" ", "\t", "\n", "\r"]

    def __init__(self, lexeme_value, lexeme_type):
        self.lexeme_value = lexeme_value
        self.lexeme_type = lexeme_type
        self.offset = 0

        if lexeme_value is not None:
            self.offset = len(lexeme_value)

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

    @staticmethod
    def new_opar(lv):
        return Lexeme(lv, 10)

    def is_opar(self):
        return self.lexeme_type == 10

    @staticmethod
    def new_cpar(lv):
        return Lexeme(lv, 11)

    def is_cpar(self):
        return self.lexeme_type == 11

    @staticmethod
    def new_obracket(lv):
        return Lexeme(lv, 12)

    def is_obracket(self):
        return self.lexeme_type == 12

    @staticmethod
    def new_cbracket(lv):
        return Lexeme(lv, 13)

    def is_cbracket(self):
        return self.lexeme_type == 13

    @staticmethod
    def new_osquig(lv):
        return Lexeme(lv, 14)

    def is_osquig(self):
        return self.lexeme_type == 14

    @staticmethod
    def new_csquig(lv):
        return Lexeme(lv, 15)

    def is_csquig(self):
        return self.lexeme_type == 15

    @staticmethod
    def new_error(msg):
        return Lexeme(msg, 16)

    def is_error(self):
        return self.lexeme_type == 16

    # END OF LINE #
    @staticmethod
    def new_end_of_line():
        return Lexeme(None, 17)

    def is_end_of_line(self):
        return self.lexeme_type == 17

    @staticmethod
    def next(buf, curpos, skipcomments=True):
        # so, obviously we want this to be able
        # to process comments and such, *but*,
        # we also want it to record newlines and
        # such, so that we know where in the code
        # a specific read error or expression comes
        # from. This could also be useful within
        # the AST system, as it can then record
        # where a specific value comes from in the
        # source. Even further, we may want to
        # record the *original* line number as well
        # as the *transcoded* line number, so that
        # we can do source mapping back to the
        # original code base.
        #
        # actually, thinking about this further,
        # we need to return the offset as well
        #
        # skipcomments: if True, we do not return
        # a lexeme for comments, but instead just
        # consume it until the next token; useful
        # for CST construction
        #
        # probably actually need the same thing
        # for white space, if we really want to
        # be able to construct a CST from these
        # lexes...

        # because we eat white space by default,
        # we actually need to track the offset
        # for the user, so they know where the
        # current end position in the buffer is
        while (curpos < len(buf) and
               buf[curpos] in Lexeme.whitespace):
            curpos += 1

        if curpos >= len(buf):
            return Lexeme.new_end_of_line()

        if buf[curpos] == '(':
            return Lexeme.new_opar('(')
        elif buf[curpos] == ')':
            return Lexeme.new_cpar(')')
        elif buf[curpos] == '[':
            return Lexeme.new_obracket('[')
        elif buf[curpos] == ']':
            return Lexeme.new_cbracket(']')
        elif buf[curpos] == '{':
            return Lexeme.new_osquig('{')
        elif buf[curpos] == '}':
            return Lexeme.new_csquig('}')
        elif buf[curpos].isdigit():
            pass
        elif buf[curpos] == '"':
            curpos += 1
            start = curpos
            while buf[curpos] != '"':
                if buf[curpos] == '\\':
                    curpos += 1
                curpos += 1
            res = buf[start:curpos]
            return Lexeme.new_string(res)
        elif buf[curpos] == "'":
            pass
        elif buf[curpos].isalpha():
            start = curpos
            while (buf[curpos] not in Lexeme.whitespace and
                   buf[curpos] not in Lexeme.breakchars):
                curpos += 1
            res = buf[start:curpos]
            return Lexeme.new_sym(res)
        elif buf[curpos] == ';':
            pass

    @staticmethod
    def new_error(message):
        return Lexeme(lv, 16)

    def is_error(self):
        return self.lexeme_type == 16

    @staticmethod
    def expect(buf, curpos, expected):
        res = Lexeme.next(buf, curpos)

        if res.lexeme_type != expected:
            return Lexeme.new_error("unexpected lexeme type found!")
        return res


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
