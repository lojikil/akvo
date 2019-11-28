import uuid
import copy

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
        apply(self.fn, userdata)


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


class PathExecution(object):
    def __init__(self, asts, constraint=None):
        self.asts = asts
        self.constraint = constraint

    def __str__(self):
        tmpl = "PathExecution({0}, {1})"

        res = tmpl.format(self.asts.to_sexpr(),
                          str(self.constraint))
        return res

    def __repr__(self):
        return str(self)


class ForkPathExecution(object):
    # constraints so should be a list of path constraints
    # asts should be a list of ASTs to match constraints
    # so for example:
    # [Constraint(x == 10), Constraint(x != 10)]
    # [Begin(Call(print, "what?")), Begin(Call(print "ok..."))]
    def __init__(self, constraints, asts):
        self.constraints = constraints
        self.asts = asts


class DelayedExecution(object):
    # this object holds a form that
    # has been delayed, and an index
    # into that delayed form. We may
    # then resume rebuilding the new
    # AST, from this delayed transaction
    # this is meant to support apply-eval
    # in micorexecution in a simple way

    def __init__(self, form, startindex=0):
        self.form = form
        self.startindex = startindex
        self.new_form = copy.deepcopy(form)
        self.ftype = type(form)

    def force(self, result):
        # it would be nice to have a
        # index method for each AST,
        # but really for here we just
        # overwrite original value in
        # the resulting AST
        if (self.ftype is IfAST or
           self.ftype is WhileAST or
           self.ftype is ForAST):
            self.new_form.condition = result
        elif self.ftype is FunctionCallAST:
            self.params[self.startindex] = result
        elif (self.ftype is BeginAST or
              self.ftype is ExplicitBeginAST):
            self.body[self.startindex] = result
        elif (self.ftype is SetValueAST or
              self.ftype is ReturnAST):
            self.new_form.value = result

        self.startindex += 1

    def done_delaying_p(self):
        if self.ftype in [IfAST, WhileAST, ForAST, SetValueAST, ReturnAST]:
            return self.startindex > 0
        elif self.ftype in [BeginAST, ExplicitBeginAST]:
            return self.startindex >= len(self.cur_ast.body)
        elif self.ftype is FunctionCallAST:
            return self.startindex >= len(self.cur_ast.params)
        return True

    def yield_execution(self):
        if self.ftype in [IfAST, WhileAST, ForAST, SetValueAST, ReturnAST]:
            if self.startindex > 0:
                return None
            elif self.ftype in [SetValueAST, ReturnAST]:
                return self.value
            else:
                return self.cur_ast.condition
        elif self.ftype in [BeginAST, ExplicitBeginAST]:
            if self.startindex < len(self.cur_ast.body):
                return self.cur_ast.body[self.startindex]
        elif self.ftype is FunctionCallAST:
            if self.startindex < len(self.cur_ast.params):
                return self.cur_ast.params[self.startindex]
        return None

    def result_form(self):
        return self.new_ast

    def original_form(self):
        return self.cur_ast


class EvalEnv(object):
    # this is a simple spaghetti stack object
    # `members` is a dict of the current scope,
    # and any refs not found in `members` should
    # be passed to parent...

    def __init__(self, members, parent=None):
        self.members = members
        self.parent = parent

    def get(self, key):
        if key in self.members:
            return self.members[key]
        elif self.parent is not None:
            return self.parent.get(key)
        else:
            raise KeyError

    def get_or_none(self, key):
        res = None

        try:
            res = self.get(key)
            return (res,)
        except KeyError:
            return None

    def set(self, key, value):
        self.members[key] = value

    def walk(self, cnt=0):
        print("environment frame {0}".format(cnt))
        print self.members

        if self.parent is not None:
            self.parent.walk(cnt + 1)


class Eval(object):
    def __init__(self, asts, env):
        self.asts = asts

        # thinking about it, you can even just
        # change these functions out, instead of
        # refactoring anything...
        self.builtins = {
            "<": lambda x, y: x < y,
            "<=": lambda x, y: x <= y,
            ">": lambda x, y: x > y,
            ">=": lambda x, y: x >= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            "+": lambda x, y: x + y,
            "*": lambda x, y: x * y,
            "/": lambda x, y: x / y,
            "//": lambda x, y: x // y,
            "&": lambda x, y: x & y,
            "|": lambda x, y: x | y,
            "^": lambda x, y: x ^ y,
            ">>": lambda x, y: x >> y,
            "<<": lambda x, y: x << y,
            "%": lambda x, y: x % y,
            "divmod": lambda x, y: divmod(x, y)
        }

        # allow users to pass raw dicts,
        # but convert them behind the scenes
        if env is None:
            self.env = EvalEnv({})
        elif type(env) is not EvalEnv:
            self.env = EvalEnv(env)
        else:
            self.env = env

    def enclose_env(self, env, srcparams, dstparams):
        new_env = {}

        if len(srcparams) != len(dstparams):
            return None
        for idx in range(0, len(srcparams)):
            new_env[dstparams[idx].variable] = srcparams[idx]
        return EvalEnv(new_env, env)

    def execute(self):
        # walk over each AST, and execute it via
        # the microexecutor below, collecting the
        # state updates for each
        for ast in self.asts:
            pass
        pass

    def microexecute(self, cur_ast, mustack=None, muenv=None):
        # execute ONE and ONLY ONE AST
        # assuming we have already split
        # things with ANF; an apply/eval
        # system could be worked into here
        # as well if ANF were not the case
        # also, we need a generic "set!"
        # form as well...

        if mustack is None:
            mustack = []

        if muenv is None:
            muenv = self.env

        res = None

        # let's change this; we need to have
        # an apply-eval cycle here, so that
        # all instructions below can simply
        # execute the AST at such time as
        # it is determined that they can
        # execute one and ONLY ONE AST.
        #
        # so, we need to extract th
        # condition or the like for
        # certain forms (`if`, &c) and
        # funtion calls, iterate over
        # that condition, and extract
        # parameters. If it is a ValueAST,
        # just add it to the parameter list.
        # if it is another form, a function,
        # or some item, extract it and set
        # *THAT* as the execution, with only
        # the result of that item being returned
        # and the original form being pushed to
        # the stack

        if type(cur_ast) is ValueAST:
            res = cur_ast
        elif type(cur_ast) is FunctionAST:
            self.env.set(cur_ast.name, cur_ast)
            res = VoidAST()
        elif type(cur_ast) is FunctionCallAST:
            new_ast = FunctionCallAST(cur_ast.name,
                                      [],
                                      cur_ast.returntype,
                                      cur_ast.symbolic)

            for param in cur_ast.params:
                if type(param) is VarRefAST:
                    try:
                        new_ast.params.append(muenv.get(param.variable))
                    except KeyError:
                        new_ast.params.append(ValueAST(None))
                else:
                    new_ast.params.append(param)
            if cur_ast.name in self.builtins:
                res = self.callfn(new_ast)
            elif muenv.get_or_none(new_ast.name) is not None:
                # man walrus would be nice ^^^
                fn = muenv.get(new_ast.name)
                res = fn.body
                muenv = self.enclose_env(muenv, new_ast.params, fn.params)
            else:
                # we have a purely symbolic function call here, we have no
                # inkling about types or other information, so we can just
                # symbolicate the result & type...
                pass
        elif type(cur_ast) is VariableDecAST:
            self.env.set(cur_ast.name, cur_ast.value)
            res = cur_ast
        elif type(cur_ast) is SetValueAST:
            if self.env.get_or_none(cur_ast.variable) is not None:
                self.env.set(cur_ast.variable, cur_ast.value)
            else:
                # NOTE
                # I'm not sure we want this. We probably actually want
                # to signal that we are executing a set! on a variable
                # that is heretofore undefined, and still set it. This
                # way we can execute code snippets that may have been
                # extracted from elsewhere...
                raise KeyError
        elif type(cur_ast) is ReturnAST:
            pass
        elif type(cur_ast) is BreakContinueAST:
            # this one is p simple: we want the
            # top-level interpreter to deal with
            # the frame of what needs to be popped
            # off or not...
            res = cur_ast
        elif type(cur_ast) is IfAST:
            condition = cur_ast.condition
            thenbranch = cur_ast.thenbranch
            elsebranch = cur_ast.elsebranch

            # look up or execute certain
            # conditions and set the `condition`
            # variable to be the result, with the
            # trace being that we looked up the
            # variable or called the function
            if type(condition) is VarRefAST:
                try:
                    condition = self.env.get(condition.variable)
                except Exception:
                    condition = ValueAST.new_symbolic_bool()
            elif type(condition) is FunctionCallAST:
                # this really should be handled by an eval pass
                # in an apply-eval loop I guess...
                new_ast = FunctionCallAST(condition.name,
                                          [],
                                          condition.returntype,
                                          condition.symbolic)

                for param in condition.params:
                    if type(param) is VarRefAST:
                        try:
                            new_ast.params.append(muenv.get(param.variable))
                        except KeyError:
                            new_ast.params.append(ValueAST(None))
                    else:
                        new_ast.params.append(param)

                if condition.name in self.builtins:
                    condition = self.callfn(new_ast)
                else:
                    # here we need to push the stack, and return
                    # that really.
                    pass

            if condition.symbolic:
                res = ForkPathExecution([cur_ast.condition == True,
                                         cur_ast.condition != True],
                                        [thenbranch, elsebranch])
            elif condition.value is True:
                res = PathExecution(thenbranch, cur_ast.condition)
            else:
                res = PathExecution(elsebranch, cur_ast.condition)

        elif type(cur_ast) is WhileAST:
            # we could do something very similar here
            # basically just res = a state with the
            # loop within it, so long as it's true.

            condition = cur_ast.condition
            body = cur_ast.body

            # look up or execute certain
            # conditions and set the `condition`
            # variable to be the result, with the
            # trace being that we looked up the
            # variable or called the function
            if type(condition) is VarRefAST:
                try:
                    condition = self.env.get(condition.variable)
                except Exception:
                    condition = ValueAST.new_symbolic_bool()
            elif type(condition) is FunctionCallAST:
                # this really should be handled by an eval pass
                # in an apply-eval loop I guess...
                new_ast = FunctionCallAST(condition.name,
                                          [],
                                          condition.returntype,
                                          condition.symbolic)

                for param in condition.params:
                    if type(param) is VarRefAST:
                        try:
                            new_ast.params.append(muenv.get(param.variable))
                        except KeyError:
                            new_ast.params.append(ValueAST(None))
                    else:
                        new_ast.params.append(param)

                if condition.name in self.builtins:
                    condition = self.callfn(new_ast)
                else:
                    # here we need to push the stack, and return
                    # that really.
                    pass

            if condition.symbolic:
                res = ForkPathExecution([cur_ast.condition == True,
                                         cur_ast.condition != True],
                                        [body, None])
            elif condition.value is True:
                res = PathExecution(body, cur_ast.condition)
                mustack.append(cur_ast)
            else:
                res = None
        elif type(cur_ast) is ForAST:
            pass
        elif type(cur_ast) is CondAST:
            pass
        elif type(cur_ast) is BeginAST or type(cur_ast) is ExplicitBeginAST:
            # for *most* cases these two are exactly the same
            # the only use case of the latter is when we're doing
            # source to source translation and the user has added
            # an explicit block, such as using an extra {} in C
            pass
        elif type(cur_ast) is VarRefAST:
            try:
                res = self.env.get(cur_ast.variable)
            except Exception:
                res = ValueAST(None)

        return (res, mustack, muenv)

    def callfn(self, cur_ast):
        # this is a first rough cut of calling
        # built-ins. Part of why this is another
        # method on Eval objects is so that if you
        # want to override how they work, you can
        # leave the microexecute & execute functions
        # alone and then only override this function
        #
        # probably should turn builtins to a dict that
        # hold lambdas to be applied for now. Also,
        # definitely need an apply/eval pass, even for
        # ANF (need to look up values prior to being
        # passed in here...)
        name = cur_ast.name
        params = cur_ast.params

        if name in self.builtins:
            return apply(self.builtins[name], params)


class ControlFlowGraph(object):
    def __init__(self, asts, env):
        self.asts = asts
        self.env = env
        # not sure how to encode graphs just yet per se
        # certainly should be a cyclical graph, but it
        # could just be a reference...
        # additionally, we need to make sure that specific
        # cases do not branch out; for example, two mutually
        # recursive methods that call one another shouldn't
        # result in the CFG exploding...

    def simple_cfg(self, start):
        # a simple CFG recovery mechanism, without
        # constrain discovery; basically, give me a
        # list of calls from each function we pass
        # through

        fstnode = None
        prevseen = set()
        graph = {}
        callstack = []
        # worklist = set()
        curnode = None

        if type(start) is str:
            fstnode = self.env.get_or_none(start)
            curnode = start
        elif isinstance(start, AST):
            fstnode = start
            curnode = start
        else:
            return None

        if type(fstnode) is FunctionCallAST:
            # here, we need to look up the function
            # we're calling, and review the body of
            # *that* function. Also need to handle
            # calling this on built-ins... we probably
            # don't care if folks want to call builtins,
            # as that will be extremely noisy...
            pass
        elif isinstance(fstnode, AST) and hasattr(fstnode, 'body'):
            callstack.append(fstnode.body)
        print fstnode, type(fstnode)

        while len(callstack) > 0:
            curitem = callstack.pop()

            print "reviewing:", curitem

            if type(curitem) is FunctionCallAST:
                # note this function call, unless
                # it's something that's builtin...
                if curnode not in graph:
                    graph[curnode] = set()
                graph[curnode].add(curitem.name)
                # now, we have to iterate over each
                # item within the function call, to
                # make sure we have those items here...
                for pitem in curitem.params:
                    if type(pitem) is not ValueAST:
                        callstack.append(pitem)
            elif type(curitem) is IfAST:
                callstack.append(curitem.condition)
                callstack.append(curitem.thenbranch)
                callstack.append(curitem.elsebranch)
            elif type(curitem) in [BeginAST, ExplicitBeginAST]:
                callstack.extend(curitem.body)
            elif type(curitem) in [ForAST, WhileAST]:
                # we need to check both the body and
                # the conditional expression for loops
                callstack.append(curitem.condition)
                callstack.append(curitem.body)
            elif type(curitem) in [SetValueAST, ReturnAST]:
                callstack.append(curitem.value)

            prevseen.add(curnode)

        return (start, graph, prevseen)


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

		# May not be the best for large
		# buffers, but it does allow us
		# a simple mechanism for reading
		if type(src) is str:
			self.buffer = src
		else:
			self.buffer = src.read()

		self.curpos = 0


class SExpressionReader(ExpressionReader):
    def read(self):
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
			raise "whoops"

	def read_expression(self):
		pass

    def next(self):
        pass


class DExpressionReader(ExpressionReader):
    def read(self):
        pass

    def next(self):
        pass
