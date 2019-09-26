class AST(object):
    pass

class FunctionAST(AST):
    def __init__(self, name, params=None, body=None, returntype=None, symbolic=False):
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
        pass

    def to_dexpr(self):
        pass


class FunctionCallAST(AST):
    def __init__(self, name, params, returntype=None, symbolic=False):
        self.name = name
        self.params = params
        self.returntype = returntype
        self.symbolic = symbolic

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class VariableDecAST(AST):
    def __init__(self, name, value=None, vtype=None, symbolic=False):
        self.name = name
        self.value = value
        self.vtype = returntype
        self.symbolic = symbolic

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class ValueAST(AST):
    def __init__(self, vtype, value=None, symbolic=False, constraint=None):
        self.vtype = vtype
        if value is None:
            self.value = None
            self.symbolic = True
        else:
            self.value = value
            self.symbolic = True
        self.constraint = constraint

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class IfAST(AST):
    def __init__(self, condition, thenbranch, elsebranch=None):
        self.condition = condition
        self.thenbranch = thenbranch
        self.elsebranch = elsebranch

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class WhileAST(AST):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class ForAST(AST):
    def __init__(self, init, condition, increment, body):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.body = body

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class CondAST(AST):
    def  __init__(self, condition, cases, thens, base=None, basethen=None):
        self.condition = condition
        self.cases = cases
        self.thens = thens
        self.base = base
        self.basethen = basethen

    def to_sexpr(self):
        pass

    def to_dexpr(self):
        pass


class EvalEnv(object):
    def __init__(self, members, parent=None):
        self.members = members
        self.parent = parent


def ast_eval(o, env):
    pass

def ast_read(src):
    pass
