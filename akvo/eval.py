from .ast import (AST, VoidAST, FunctionAST, FunctionCallAST, NativeCallAST,
                  VariableDecAST, ForkValueAST, ValueAST, IfAST, WhileAST,
                  CondAST, BeginAST, ExplicitBeginAST, VarRefAST, ReturnAST,
                  SetValueAST, BreakContinueAST, ForAST)
import copy


class PathExecution(object):
    def __init__(self, asts, constraint=None):
        self.asts = asts
        self.constraint = constraint

    def __str__(self):
        tmpl = "PathExecution({0}, {1})"

        res = tmpl.format(self.asts.to_sexpr(),
                          self.constraint.to_sexpr())
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
        print(("environment frame {0}".format(cnt)))
        print(self.members)

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
        elif type(cur_ast) is NativeCallAST:
            pass
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
            return self.builtins[name](*params)
