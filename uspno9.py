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
            self.value = ValueAST(None)
            self.symbolic = True
            self.vtype = vtype
        else:
            self.value = value
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


class ValueAST(AST):
    def __init__(self, vtype, value=None, symbolic=False,
                 constraint=None, trace=None):
        self.vtype = vtype
        self.tag = uuid.uuid4()
        if value is None:
            self.value = None
            self.symbolic = True
        else:
            self.value = value
            self.symbolic = False
        self.constraint = constraint
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
            ret.append(self.trace)

        return "(" + " ".join(ret) + ")"

    def to_dexpr(self):
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


class EvalEnv(object):
    def __init__(self, members, parent=None):
        self.members = members
        self.parent = parent


class Eval(object):
    def __init__(self, asts, env):
        pass


class ControlFlowGraph(object):
    def __init__(self, asts, env):
        pass


class SExpressionReader(object):
    pass


class DExpressionReader(object):
    pass
