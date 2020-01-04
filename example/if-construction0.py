from akvo.ast import IfAST, ValueAST, VarRefAST
from akvo.eval import EvalEnv, Eval

# The Scheme Code for these:
#
# (if true 10 11)
# (if foo 12 13)
#

if0 = IfAST(ValueAST.new_bool(True),
            ValueAST.new_integer(10),
            ValueAST.new_integer(11))
if1 = IfAST(VarRefAST("foo"),
            ValueAST.new_integer(12),
            ValueAST.new_integer(13))

print("execute the following test cases:")
print(if0.to_sexpr())
print(if1.to_sexpr())

rootenv0 = EvalEnv({"foo": ValueAST.new_bool(True),
                    "bar": ValueAST.new_integer(10)})
rootenv1 = EvalEnv({"foo": ValueAST.new_symbolic_bool()})

# we don't affix the asts for now, because we're just
# going to microexecute them
vm0 = Eval(None, rootenv0)
vm1 = Eval(None, rootenv1)

results = [
    vm0.microexecute(if0),
    vm1.microexecute(if0),
    vm0.microexecute(if1),
    vm1.microexecute(if1)]

print("results: ", results)

for result in results:
    print("Result: {0}".format(result))
