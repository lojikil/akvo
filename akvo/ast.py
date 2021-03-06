import uuid


# ugly hack; I guess the AST object
# could capture that for me, I need
# to stew on that a bit more...
current_count = 0


class AST(object):
    pass


class VoidAST(AST):
    # a disjoint type meant to represent
    # when something returns no value
    def to_sexpr(self):
        return "#void"

    def to_dexpr(self):
        return "#void"

    def __str__(self):
        return "#void"


class FunctionAST(AST):
    def __init__(self, name, params=None, body=None,
                 returntype=None, symbolic=False,
                 inline=False):
        self.name = name
        self.params = params
        self.returntype = returntype
        self.userdefined = True
        self.inline = inline
        if body is None:
            self.body = None
            self.symbolic = True
        else:
            self.body = body
            self.symbolic = symbolic

    def to_sexpr(self):
        ret = []

        if self.symbolic:
            ret.append("define-symbolic-function")
        else:
            ret.append("define-function")

        ret.append(self.name)

        if self.vtype is not None:
            ret.append("::{0}".format(self.vtype.__name__))
        elif self.symbolic:
            # here, we know that vtype is None and
            # we have a symbolic function, so we can
            # safely assume that the type can be refined
            # and is symbolic currently
            self.append("::pure-symbolic")
        else:
            self.append("::void")

        if self.params is None:
            ret.append("()")
        else:
            ret.append("(")
            ret.extend([x.to_sexpr() for x in self.params])
            ret.append(")")

        ret.extend([x.to_sexpr() for x in self.body])
        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class FunctionCallAST(AST):
    def __init__(self, name, params, returntype=None, symbolic=False):
        self.name = name
        self.params = params
        self.returntype = returntype
        self.symbolic = symbolic

    def to_sexpr(self):
        ret = []

        if self.symbolic:
            ret.append("symbolic-call")
        else:
            ret.append("call")

        ret.append(self.name)

        if self.returntype is None:
            ret.append("::pure-symbolic")
        else:
            ret.append("::{0}".format(self.returntype.__name__))

        ret.extend([x.to_sexpr() for x in self.params])
        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass

    def _gen_var(self, form):
        # returns a new `define` form
        # with a freshsym name and the
        # `form` parameter as the value.
        # maybe should take an optional
        # source name so that we can bind
        # to known parameters (like named
        # params in user functions)
        #
        # so, I could just randomly generate
        # these, but I want to make runs
        # reproducible (save for UUIDs, of
        # course). So, it may make since to
        # just make this linearly and monotonically
        # increase over the course of things.
        # need to keep a counter running,
        # of course...

        global current_count  # hate this, lol
        name = "res_{0}".format(current_count)
        current_count += 1

        # we probably could reach into form
        # a bit more, but for now let's just
        # do the simplest thing possible

        res = VariableDecAST(name, value=form)
        return res

    def _gen_var_ref(self, form):
        # accept a VarAST (a variable
        # declaration) and return a
        # VarRefAST, with the type and
        # whatnot properly set from the
        # VarAST.
        return VarRefAST(form.name, vtype=form.vtype, symbolic=form.symbolic)

    def to_anf(self):
        # recursively inflate a function call from
        # a single call with multiple parameters
        # that may or may not be function calls
        # into a list of variable binds and function
        # calls
        #
        # e.g. turn `(call + (call * (variable z) 10) 11)`
        # into:
        #
        # ```scheme
        # (define a (call * (variable z) 10))
        # (call + a 11)
        # ```
        #
        # this allows us to analyze the environment
        # and see the return results for calls, as
        # well as simplifies execution models
        #
        # I've thought about just adding a `let` form
        # here, but I'd just end up doing alpha-conversion
        # to a freshsym + `def` anyway I think, since that
        # is relatively more practical than attempting to
        # add env-frames all the time (which will just be
        # flattened for any relatively normal analysis
        # anyway)

        nuvars = []
        finalcall = FunctionCallAST(name=self.name, params=[],
                                    returntype=self.returntype,
                                    symbolic=self.symbolic)

        for param in self.params:
            if type(param) is FunctionCallAST:
                tmpvars, tmpres = param.to_anf()
                nuvars.extend(tmpvars)
                nextvar = self._gen_var(tmpres)
                nuvars.append(nextvar)
                finalcall.params.append(self._gen_var_ref(nextvar))
            elif type(param) in [IfAST, WhileAST, ForAST, CondAST]:
                nextvar = self._gen_var(param)
                nuvars.append(nextvar)
                finalcall.params.append(self._gen_var_ref(nextvar))
            elif type(param) is FunctionAST:
                # an anonymous funciton, we need to lambda lift it
                continue
            else:
                finalcall.params.append(param)

        return nuvars, finalcall

    def from_anf(self):
        pass


class NativeCallAST(AST):
    # a simple class to wrap and
    # call native function
    #
    # probably need some type information
    # here...
    def __init__(self, name, params, fn):
        self.name = name
        self.params = params
        self.fn = fn

    def apply(self, userdata):
        self.fn(*userdata)


class VariableDecAST(AST):
    def __init__(self, name, value=None, vtype=None, symbolic=False):
        self.name = name
        if value is None:
            self.value = ValueAST(vtype)
            self.symbolic = True
            self.vtype = vtype
        else:
            if type(value) is ValueAST:
                self.value = value
            elif isinstance(value, AST):
                # separating this case here
                # because we may want to do
                # something with it soon...
                self.value = value
            else:
                self.value = ValueAST(vtype, value=value)
            self.vtype = vtype
            self.symbolic = symbolic

    def to_sexpr(self):
        ret = []
        if self.symbolic:
            ret.append("define-symbolic")
        else:
            ret.append("define")

        ret.append(self.name)

        # use Bigloo-style type annotations
        if self.vtype is None:
            ret.append("::pure-symbolic")
        else:
            ret.append("::{0}".format(self.vtype.__name__))

        # we technically can have Variables with symbolic values
        # basically we don't worry about that so much here...
        if self.symbolic:
            ret.append(str(self.value.tag))
        else:
            ret.append(self.value.to_sexpr())

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class ForkValueAST(object):
    __slots__ = ["lhs", "rhs"]

    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self):
        return "ForkValue({0}, {1})".format(str(self.lhs), str(self.rhs))

    def __repr__(self):
        return "ForkValue({0}, {1})".format(repr(self.lhs), repr(self.rhs))


class ValueAST(AST):
    # I can see two mechanisms for supporting radically
    # different value styles:
    # - a plugin arch, wherein you can register a function
    #   to handle an operation (for example, JSAdd)
    # - just creating a subclass of ValueAST for that language
    #   (for example, JSValueAST)
    # - Actually, there is a THIRD idea: instead of overriding
    #   how *value* works, we add functions within the *evaluator*
    #   and use *that* to call specific functions. For example, we
    #   may have a `(call + ::int ...)` on some code. The `call`
    #   system then looks up `+`, and calls it off itself. We can
    #   then override *that* and call our own `+` in the evaluator
    def __init__(self, vtype, value=None, symbolic=False,
                 constraint=None, trace=None):
        self.vtype = vtype
        self.tag = uuid.uuid4()

        if value is None:
            self.value = self.tag
            self.symbolic = True
        else:
            # probably need to unpack value
            # if it's a list, dict, set, or tuple
            self.value = value
            self.symbolic = False

        self.constraint = constraint

        if trace is None:
            # Traces are in effect a meta-constraint language
            # that interfaces with the term *AND* type languages
            # that we've been implementing here...
            if symbolic:
                self.trace = [str(self.tag)]
            else:
                self.trace = [str(value) + " tag: " + str(self.tag)]
        else:
            self.trace = trace

    def to_sexpr(self):
        ret = []

        if self.symbolic:
            ret.append("symbolic-value")
            ret.append(str(self.tag))
        else:
            ret.append("value")
            ret.append(str(self.value))

        if self.vtype is not None:
            ret.append("::{0}".format(self.vtype.__name__))
        else:
            ret.append("::pure-symbolic")

        if self.constraint is not None:
            ret.append("constraint:")
            ret.append(self.constraint)

        if self.trace is not None:
            ret.append("trace:")
            ret.append(" ".join(self.trace))

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass

    # need helper methods & mechanisms for modeling
    # lists, sets, dicts, tuples as both concrete
    # and symbolic values

    @staticmethod
    def new_symbolic_bool():
        res = ValueAST(vtype=bool, symbolic=True)
        return res

    @staticmethod
    def new_symbolic_integer():
        res = ValueAST(vtype=int, symbolic=True)
        return res

    @staticmethod
    def new_symbolic_string():
        res = ValueAST(vtype=str, symbolic=True)
        return res

    @staticmethod
    def new_symbolic_float():
        res = ValueAST(vtype=float, symbolic=True)
        return res

    @staticmethod
    def new_integer(value):
        res = ValueAST(vtype=int, value=value)
        return res

    @staticmethod
    def new_bool(value):
        res = ValueAST(vtype=bool, value=value)
        return res

    @staticmethod
    def new_string(value):
        return ValueAST(vtype=str, value=value)

    @staticmethod
    def new_float(value):
        return ValueAST(vtype=float, value=value)

    def __lt__(self, other):
        # NOTE so reading the SAGE paper, we see that we want at least
        # one run to gather constraints of the program, and then we
        # make another pass to negate those constraints. So we may want
        # to change how we return ForkValues here, because we may want
        # to note what the path constraint is, and then we can just
        # return that the constraint here is that they are equal...

        rv = ValueAST(bool, False)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        # one thing to note: there may be a case to be made that
        # on symbolic comparison, we should check if the symbolic
        # values have constraints that would make them true. For
        # example:
        # g = ValueAST.new_symbolic_int(constraint: "(< $it 10)")
        # h = ValueAST.new_symbolic_int(constraint: "(>= $it 10)")
        # j = g < h
        # print j.value
        # we may wish to have j be *true* in this case, because we
        # know given those constraints that g < h for all values that
        # g may contain. This may also just be something that goes
        # to the scenario generator, and we don't *really* care what
        # else goes in there
        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value < other
            rv.trace = [self_trace, " < ", other_trace]
            return rv
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value < other.value
            rv.trace = [self_trace, " < ", other_trace]
            return rv

        # ok, so we're here; that means either self or other
        # was symbolic, meaning we need to return a symbolic
        # Boolean set, aka a ForkValue

        lhs = rv
        rhs = ValueAST.new_symbolic_bool()
        lhs.symbolic = True
        lhs.value = lhs.tag

        lhs.trace = [self_trace, " < ", other_trace]
        rhs.trace = [self_trace, " >= ", other_trace]

        return ForkValueAST(lhs, rhs)

    def __gt__(self, other):
        rv = ValueAST(bool, False)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value > other
            rv.trace = [self_trace, " > ", other_trace]
            return rv
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value > other.value
            rv.trace = [self_trace, " > ", other_trace]
            return rv

        # ok, so we're here; that means either self or other
        # was symbolic, meaning we need to return a symbolic
        # Boolean set, aka a ForkValue

        lhs = rv
        rhs = ValueAST.new_symbolic_bool()
        lhs.symbolic = True
        lhs.value = lhs.tag

        lhs.trace = [self_trace, " > ", other_trace]
        rhs.trace = [self_trace, " <= ", other_trace]

        return ForkValueAST(lhs, rhs)

    def __le__(self, other):
        rv = ValueAST(bool, False)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value <= other
            rv.trace = [self_trace, " <= ", other_trace]
            return rv
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value <= other.value
            rv.trace = [self_trace, " <= ", other_trace]
            return rv

        # ok, so we're here; that means either self or other
        # was symbolic, meaning we need to return a symbolic
        # Boolean set, aka a ForkValue

        lhs = rv
        rhs = ValueAST.new_symbolic_bool()
        lhs.symbolic = True
        lhs.value = lhs.tag

        lhs.trace = [self_trace, " <= ", other_trace]
        rhs.trace = [self_trace, " > ", other_trace]

        return ForkValueAST(lhs, rhs)

    def __ge__(self, other):
        rv = ValueAST(bool, False)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value >= other
            rv.trace = [self_trace, " >= ", other_trace]
            return rv
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value >= other.value
            rv.trace = [self_trace, " >= ", other_trace]
            return rv

        # ok, so we're here; that means either self or other
        # was symbolic, meaning we need to return a symbolic
        # Boolean set, aka a ForkValue

        lhs = rv
        rhs = ValueAST.new_symbolic_bool()
        lhs.symbolic = True
        lhs.value = lhs.tag

        lhs.trace = [self_trace, " >= ", other_trace]
        rhs.trace = [self_trace, " < ", other_trace]

        return ForkValueAST(lhs, rhs)

    def __ne__(self, other):
        rv = ValueAST(bool, False)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value != other
            rv.trace = [self_trace, " != ", other_trace]
            return rv
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value != other.value
            rv.trace = [self_trace, " != ", other_trace]
            return rv

        # ok, so we're here; that means either self or other
        # was symbolic, meaning we need to return a symbolic
        # Boolean set, aka a ForkValue

        lhs = rv
        rhs = ValueAST.new_symbolic_bool()
        lhs.symbolic = True
        lhs.value = lhs.tag

        lhs.trace = [self_trace, " != ", other_trace]
        rhs.trace = [self_trace, " == ", other_trace]

        return ForkValueAST(lhs, rhs)

    def __eq__(self, other):
        # NOTE so reading the SAGE paper, we see that we want at least
        # one run to gather constraints of the program, and then we
        # make another pass to negate those constraints. So we may want
        # to change how we return ForkValues here, because we may want
        # to note what the path constraint is, and then we can just
        # return that the constraint here is that they are equal...

        rv = ValueAST(bool, False)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value == other
            rv.trace = ["(", self.trace, ") == ", other]
            return rv
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value == other.value
            rv.trace = ["(", self.trace, ") == (", other.trace, ")"]
            return rv

        # ok, so we're here; that means either self or other
        # was symbolic, meaning we need to return a symbolic
        # Boolean set, aka a ForkValue

        lhs = rv
        rhs = ValueAST.new_symbolic_bool()
        lhs.symbolic = True
        lhs.value = lhs.tag

        if not self.symbolic:
            lhs.trace = ["(", self.trace, ") == (", other.trace, ")"]
            rhs.trace = ["(", self.trace, ") != (", other.trace, ")"]
        else:
            # self itself (lol) is symbolic, so we have to take a little
            # more care to see what other is.
            if type(other) is not ValueAST:
                lhs.trace = ["(", self.trace, ") == (", other, ")"]
                rhs.trace = ["(", self.trace, ") != (", other, ")"]
            else:
                lhs.trace = ["(", self.trace, ") == (", other.trace, ")"]
                rhs.trace = ["(", self.trace, ") != (", other.trace, ")"]

        return ForkValueAST(lhs, rhs)

    def __add__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value + other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "+", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value + other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "+", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "+", other_trace]

        return rv

    def __radd__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other + self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "+", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value + self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "+", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "+", self_trace]

        return rv

    def __sub__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value - other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "-", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value - other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "-", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "-", other_trace]

        return rv

    def __rsub__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other - self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "-", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value - self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "-", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "-", self_trace]

        return rv

    def __mul__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value * other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "*", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value * other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "*", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "*", other_trace]

        return rv

    def __rmul__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other * self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "*", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value * self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "*", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "*", self_trace]

        return rv

    def __div__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value / other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "/", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value / other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "/", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "/", other_trace]

        return rv

    def __rdiv__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other / self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "/", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value / self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "/", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "/", self_trace]

        return rv

    def __rshift__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value >> other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, ">>", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value >> other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, ">>", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, ">>", other_trace]

        return rv

    def __rrshift__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other >> self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, ">>", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value >> self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, ">>", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, ">>", self_trace]

        return rv

    def __lshift__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value << other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "<<", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value << other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "<<", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "<<", other_trace]

        return rv

    def __rlshift__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other << self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "<<", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value << self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "<<", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "<<", self_trace]

        return rv

    def __xor__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value ^ other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "^", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value ^ other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "^", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "^", other_trace]

        return rv

    def __rxor__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other ^ self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "^", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value ^ self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "^", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "^", self_trace]

        return rv

    def __or__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value | other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "|", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value | other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "|", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "|", other_trace]

        return rv

    def __ror__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other | self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "|", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value | self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "|", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "|", self_trace]

        return rv

    def __and__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value & other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "&", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value & other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "&", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "&", other_trace]

        return rv

    def __rand__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other & self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "&", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value & self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "&", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "&", self_trace]

        return rv

    def __mod__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value % other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "%", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value % other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "%", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "%", other_trace]

        return rv

    def __rmod__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other % self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "%", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value % self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "%", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "%", self_trace]

        return rv

    def __truediv__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value // other
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "//", other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = self.value // other.value
            rv.vtype = type(rv.value)
            rv.trace = [self_trace, "//", other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "//", other_trace]

        return rv

    def __rtruediv__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other // self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "//", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value // self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "//", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "//", self_trace]

        return rv

    def __divmod__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = divmod(self.value, other)
            rv.vtype = type(rv.value)
            rv.trace = ["divmod", self_trace, other_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = divmod(self.value, other.value)
            rv.vtype = type(rv.value)
            rv.trace = ["divmod", self_trace, other_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = ["divmod", self_trace, other_trace]

        return rv

    def __rdivmod__(self, other):
        rv = ValueAST(None)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = other / self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "/", self_trace]
            rv.symbolic = False
        elif (not self.symbolic and
              type(other) is ValueAST and
              not other.symbolic):
            rv.value = other.value / self.value
            rv.vtype = type(rv.value)
            rv.trace = [other_trace, "/", self_trace]
            rv.symbolic = False
        elif self.symbolic or other.symbolic:
            # here we know that self is symbolic
            rv.vtype = self.vtype  # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [other_trace, "/", self_trace]

        return rv


class IfAST(AST):
    def __init__(self, condition, thenbranch, elsebranch=None):
        self.condition = condition
        self.thenbranch = thenbranch
        self.elsebranch = elsebranch

    def to_sexpr(self):
        ret = ["if"]

        ret.append(self.condition.to_sexpr())
        ret.append(self.thenbranch.to_sexpr())

        if self.elsebranch is not None:
            ret.append(self.elsebranch.to_sexpr())

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class WhileAST(AST):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def to_sexpr(self):
        ret = ["while"]

        ret.append(self.condition.to_sexpr())
        ret.append(self.body.to_sexpr())

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class ForAST(AST):
    def __init__(self, init, condition, increment, body):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.body = body

    def to_sexpr(self):
        ret = ["for"]

        ret.append(self.init.to_sexpr())
        ret.append(self.condition.to_sexpr())
        ret.append(self.increment.to_sexpr())
        ret.append(self.body.to_sexpr())

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class CondAST(AST):
    def __init__(self, condition, cases, thens, base=None, basethen=None):
        self.condition = condition
        self.cases = cases
        self.thens = thens
        self.base = base
        self.basethen = basethen

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class BeginAST(AST):
    def __init__(self, body):
        self.body = body

    def to_sexpr(self):
        ret = ["begin"]

        ret.extend([x.to_sexpr() for x in self.body])

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class ExplicitBeginAST(AST):
    # this is meant to be subtly different
    # from the above, insofar as there are
    # times when we absolutely want to encode
    # a `begin` and never remove them, whereas
    # the above AST may be removed on output
    # at times
    def __init__(self, body):
        self.body = body

    def to_sexpr(self):
        ret = ["begin"]

        ret.extend([x.to_sexpr() for x in self.body])

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class VarRefAST(AST):
    def __init__(self, variable, vtype=None, scope=None, symbolic=False):
        # technically, we're losing the trace here with a
        # variable ref...
        self.variable = variable
        self.vtype = vtype
        self.scope = scope
        self.symbolic = symbolic

    def to_sexpr(self):
        ret = []

        if self.symbolic:
            ret.append("symbolic-variable")
        else:
            ret.append("variable")

        ret.append(self.variable)

        if self.vtype is not None:
            ret.append("::{0}".format(self.vtype.__name__))
        else:
            ret.append("::pure-symbolic")

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
        pass


class ReturnAST(AST):
    def __init__(self, value):
        self.value = value

    def to_sexpr(self):
        ret = ["return"]
        ret.append(self.value.to_sexpr())
        return "(" + " ".join(ret) + ")"


class BreakContinueAST(AST):
    def __init__(self, isbreakp=False):
        self.isbreakp = isbreakp

    def to_sexpr(self):
        if self.isbreakp:
            return "(break)"
        else:
            return "(continue)"


class SetValueAST(AST):
    def __init__(self, variable, value):
        self.variable = variable
        self.value = value

    def to_sexpr(self):
        ret = ["set!", self.variable]
        ret.append(self.value.to_sexpr())
        return "(" + " ".join(ret) + ")"


