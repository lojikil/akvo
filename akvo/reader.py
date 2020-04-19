from .ast import ValueAST


class Lexeme(object):
    # holds a Lexeme and has a bunch of
    # helper methods. I'm attempting to
    # avoid a huge hierarchy of Lexeme
    # classes here...

    breakchars = [';', '{', '}', '[', ']', '(', ')', '"']
    whitespace = [" ", "\t", "\n", "\r"]

    def __init__(self, lexeme_value, lexeme_type, offset):
        self.lexeme_value = lexeme_value
        self.lexeme_type = lexeme_type
        self.offset = offset
        self.length = 0

        if lexeme_value is not None:
            self.length = len(lexeme_value)

    @staticmethod
    def new_key(lv, offset):
        return Lexeme(lv, 0, offset)

    def is_key(self):
        return self.lexeme_type == 0

    @staticmethod
    def new_keyword(lv, offset):
        return Lexeme(lv, 1, offset)

    def is_keyword(self):
        return self.lexeme_type == 1

    @staticmethod
    def new_string(lv, offset):
        return Lexeme(lv, 2, offset)

    def is_string(self):
        return self.lexeme_type == 2

    @staticmethod
    def new_int(lv, offset):
        return Lexeme(lv, 3, offset)

    def is_int(self):
        return self.lexeme_type == 3

    @staticmethod
    def new_hex(lv, offset):
        return Lexeme(lv, 4, offset)

    def is_hex(self):
        return self.lexeme_type == 4

    @staticmethod
    def new_oct(lv, offset):
        return Lexeme(lv, 5, offset)

    def is_oct(self):
        return self.lexeme_type == 5

    @staticmethod
    def new_bin(lv, offset):
        return Lexeme(lv, 6, offset)

    def is_bin(self):
        return self.lexeme_type == 6

    @staticmethod
    def new_float(lv, offset):
        return Lexeme(lv, 7, offset)

    def is_float(self):
        return self.lexeme_type == 7

    @staticmethod
    def new_char(lv, offset):
        return Lexeme(lv, 8, offset)

    def is_char(self):
        return self.lexeme_type == 8

    @staticmethod
    def new_sym(lv, offset):
        return Lexeme(lv, 9, offset)

    def is_sym(self):
        return self.lexeme_type == 9

    @staticmethod
    def new_opar(lv, offset):
        return Lexeme(lv, 10, offset)

    def is_opar(self):
        return self.lexeme_type == 10

    @staticmethod
    def new_cpar(lv, offset):
        return Lexeme(lv, 11, offset)

    def is_cpar(self):
        return self.lexeme_type == 11

    @staticmethod
    def new_obracket(lv, offset):
        return Lexeme(lv, 12, offset)

    def is_obracket(self):
        return self.lexeme_type == 12

    @staticmethod
    def new_cbracket(lv, offset):
        return Lexeme(lv, 13, offset)

    def is_cbracket(self):
        return self.lexeme_type == 13

    @staticmethod
    def new_osquig(lv, offset):
        return Lexeme(lv, 14, offset)

    def is_osquig(self):
        return self.lexeme_type == 14

    @staticmethod
    def new_csquig(lv, offset):
        return Lexeme(lv, 15, offset)

    def is_csquig(self):
        return self.lexeme_type == 15

    @staticmethod
    def new_error(msg, offset):
        return Lexeme(msg, 16, offset)

    def is_error(self):
        return self.lexeme_type == 16

    # END OF LINE #
    @staticmethod
    def new_end_of_line(offset):
        return Lexeme(None, 17, offset)

    def is_end_of_line(self):
        return self.lexeme_type == 17

    def __str__(self):
        return "Lexeme('{0}', {1})".format(self.lexeme_value,
                                           self.lexeme_type)

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

        start = curpos

        if curpos >= len(buf):
            return Lexeme.new_end_of_line(start)

        if buf[curpos] == '(':
            return Lexeme.new_opar('(', start)
        elif buf[curpos] == ')':
            return Lexeme.new_cpar(')', start)
        elif buf[curpos] == '[':
            return Lexeme.new_obracket('[', start)
        elif buf[curpos] == ']':
            return Lexeme.new_cbracket(']', start)
        elif buf[curpos] == '{':
            return Lexeme.new_osquig('{', start)
        elif buf[curpos] == '}':
            return Lexeme.new_csquig('}', start)
        elif buf[curpos].isdigit():
            dtype = 0
            while (curpos < len(buf) and
                   buf[curpos] not in Lexeme.whitespace and
                   buf[curpos] not in Lexeme.breakchars):
                if dtype == 0:
                    # I do really need to check
                    # positionally where these
                    # are, like 0b01001 is ok,
                    # but 0001b1010 is wrong...
                    if buf[curpos] == '.':
                        # float
                        dtype = 1
                    elif buf[curpos] == 'b':
                        # binary
                        dtype = 2
                    elif buf[curpos] == 'x':
                        # hex
                        dtype = 3
                    elif buf[curpos] == 'o':
                        # oct
                        dtype = 4
                    elif buf[curpos].isdigit():
                        pass
                    else:
                        # we need to handle symbols here,
                        # because I didn't make this whole
                        # thing a giant state machine.
                        dtype = 5
                    curpos += 1
                elif dtype == 1:
                    if buf[curpos].isdigit():
                        curpos += 1
                    elif buf[curpos].isalpha():
                        # need to check for a wider range
                        # of things here, like ! and $ and
                        # so on.
                        curpos += 1
                        dtype = 5
                elif dtype == 2:
                    if buf[curpos] in ["0", "1"]:
                        curpos += 1
                    elif buf[curpos].isalpha():
                        curpos += 1
                        dtype = 5
                elif dtype == 3:
                    if buf[curpos] in "0123456789ABCDEFabcdef":
                        curpos += 1
                    else:
                        curpos += 1
                        dtype = 5
                elif dtype == 4:
                    if buf[curpos] in "01234567":
                        curpos += 1
                    else:
                        curpos += 1
                        dtype = 5
                elif dtype == 5:
                    curpos += 1

            res = buf[start:curpos]

            if dtype == 0:
                return Lexeme.new_int(res, start)
            elif dtype == 1:
                return Lexeme.new_float(res, start)
            elif dtype == 2:
                return Lexeme.new_bin(res, start)
            elif dtype == 3:
                return Lexeme.new_hex(res, start)
            elif dtype == 4:
                return Lexeme.new_oct(res, start)
            elif dtype == 5:
                return Lexeme.new_sym(res, start)

        elif buf[curpos] == '"':
            curpos += 1
            start = curpos
            while buf[curpos] != '"':
                if buf[curpos] == '\\':
                    curpos += 1
                curpos += 1
            res = buf[start:curpos]
            return Lexeme.new_string(res, start + 1)
        elif buf[curpos] == "'":
            curpos += 1
            start = curpos
            if buf[curpos] == '\\':
                curpos += 1
                # probably should just make this a
                # lookup table...
                if buf[curpos] == 'n':
                    res = "\n"
                elif buf[curpos] == 'v':
                    res = '\v'
                elif buf[curpos] == 'r':
                    res = '\r'
                elif buf[curpos] == 'b':
                    res = '\b'
                elif buf[curpos] == 'l':
                    res = '\l'
                elif buf[curpos] == 't':
                    res = '\t'
                else:
                    res = buf[curpos]
            else:
                res = buf[curpos]
            curpos += 1

            if buf[curpos] != "'":
                return Lexeme.new_error("malformed character")
            else:
                return Lexeme.new_char(res, start)
        elif buf[curpos].isalpha() or buf[curpos].isprintable():
            start = curpos
            while (curpos < len(buf) and
                   buf[curpos] not in Lexeme.whitespace and
                   buf[curpos] not in Lexeme.breakchars):
                curpos += 1
            res = buf[start:curpos]
            return Lexeme.new_sym(res, start)
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

    @staticmethod
    def iter_next(buf):
        offset = 0
        while True:
            if offset > len(buf):
                raise StopIteration()

            res = Lexeme.next(buf, offset)

            if res.is_end_of_line():
                raise StopIteration()

            offset = res.offset + res.length
            yield res

    @staticmethod
    def all(buf):
        ret = []
        try:
            for lex in Lexeme.iter_next(buf):
                ret.append(lex)
        finally:
            return ret


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
    def read(self, pos=0):
        res = Lexeme.next(self.src, pos)

        if res.is_string():
            return ValueAST.new_string(res.lexeme_value)
        elif res.is_int():
            # I think the helper methods here need to actually
            # deal with values, not the reader per se. The thought
            # here is what do we do when we have integers that are
            # too large for a python int (or w/e)? We don't want
            # the _reader_ to know how to do that work, that is an
            # abstraction leak. Instead, the helper method should
            # handle such situations
            return ValueAST.new_integer(int(res.lexeme_value))
        elif res.is_hex():
            pass
        elif res.is_oct():
            pass
        elif res.is_float():
            pass
        elif res.is_char():
            pass
        elif res.is_sym():
            pass


class DExpressionReader(ExpressionReader):
    def read(self):
        pass

    def next(self):
        pass
