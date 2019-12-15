from .ast import *

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
        print(fstnode, type(fstnode))

        while len(callstack) > 0:
            curitem = callstack.pop()

            print("reviewing:", curitem)

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


