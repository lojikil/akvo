import uuid


class AST(object):
    pass


class FunctionAST(AST):
    def __init__(self, name, params=None, body=None,
                 returntype=None, symbolic=False):
        self.name = name
        self.params = params
        self.returntype = returntype
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

        rv = ValueAST(bool)

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
        rv = ValueAST(bool)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value > other
            rv.trace = [ self_trace, " > ", other_trace]
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
        rv = ValueAST(bool)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value <= other
            rv.trace = [ self_trace, " <= ", other_trace]
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
        rv = ValueAST(bool)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value >= other
            rv.trace = [ self_trace, " >= ", other_trace]
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
        rv = ValueAST(bool)

        self_trace = "(" + " ".join(self.trace) + ")"

        if type(other) is ValueAST:
            other_trace = " ".join(other.trace)
        else:
            other_trace = str(other)

        other_trace = "({0})".format(other_trace)

        if self.symbolic is False and type(other) is not ValueAST:
            rv.value = self.value != other
            rv.trace = [ self_trace, " != ", other_trace]
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

        rv = ValueAST(bool)

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
            rv.trace = [ self_trace, "+", other_trace]
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
            rv.vtype = self.vtype # is this correct?
            rv.symbolic = True
            rv.value = rv.tag
            rv.trace = [self_trace, "+", other_trace]

        return rv

    def __radd__(self, other):
        pass

    def __sub__(self, other):
        pass

    def __rsub__(self, other):
        pass


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

    def set(self, key, value):
        self.members[key] = value


class Eval(object):
    def __init__(self, asts, env):
        self.asts = asts
        self.env = env

    def execute(self):
        # walk over each AST, and execute it via
        # the microexecutor below, collecting the
        # state updates for each
        for ast in self.asts:
            pass
        pass

    def microexecute(self, cur_ast):
        # execute ONE and ONLY ONE AST
        # assuming we have already split
        # things with ANF; an apply/eval
        # system could be worked into here
        # as well if ANF were not the case
        # also, we need a generic "set!"
        # form as well...

        if type(cur_ast) is ValueAST:
            return (cur_ast, state)
        elif type(cur_ast) is FunctionAST:
            pass
        elif type(cur_ast) is FunctionCallAST:
            pass
        elif type(cur_ast) is VariableDecAST:
            self.env.set(cur_ast.name, cur_ast.value)
            return cur_ast
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
                except:
                    condition = ValueAST.new_symbolic_bool()
            elif type(condition) is FunctionCallAST:
                pass

            if condition.symbolic:
                return ForkPathExecution([condition == True,
                                          condition != True],
                                         [thenbranch, elsebranch])
            elif condition.value is True:
                return PathExecution(thenbranch, condition)
            else:
                return PathExecution(elsebranch, condition)

        elif type(cur_ast) is WhileAST:
            # we could do something very similar here
            # basically just return a state with the
            # loop within it, so long as it's true.
            pass
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
            pass


class ControlFlowGraph(object):
    def __init__(self, asts, env):
        pass


class SExpressionReader(object):
    pass


class DExpressionReader(object):
    pass
