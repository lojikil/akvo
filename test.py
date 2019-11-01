import uspno9

print "Variable declaration tests\n====="

f = uspno9.VariableDecAST("f", uspno9.ValueAST(int, 10), int)
print f.to_sexpr()
g = uspno9.VariableDecAST("g", uspno9.ValueAST(int), int)
h = uspno9.VariableDecAST("h", vtype=int)
print g.to_sexpr()
print h.to_sexpr()
j = uspno9.VariableDecAST("j")
print j.to_sexpr()

print "\nif-form test\n====="

cond0 = uspno9.FunctionCallAST("<", [uspno9.VarRefAST("f", int),
                                     uspno9.VarRefAST("g", int,
                                                      symbolic=True)],
                                     bool)
then0 = uspno9.FunctionCallAST("print", [uspno9.ValueAST(str, "then")], str)
else0 = uspno9.FunctionCallAST("print", [uspno9.ValueAST(str, "else")], str)
if0 = uspno9.IfAST(cond0, then0, else0)

print if0.to_sexpr()

print "\ninteger logic tests\n======"

a = uspno9.ValueAST.new_integer(9)
s = uspno9.ValueAST.new_integer(10)

z = a < s
x = a > s
c = a <= s
v = a >= s
b = a != s
n = a == s

res = [z,x,c,v,b,n]

for r in res:
    print r.value, r.trace, r.symbolic


print "\narithmatic tests\n====="

jj = uspno9.ValueAST.new_symbolic_integer()

cg = a + s
ch = a + cg
cj = jj + a
ck = cj + ch

print cg.value, cg.trace
print ch.value, ch.trace
print cj.value, cj.trace
print ck.value, ck.trace

from uspno9 import *

print "\nexecution tests\n====="

if0 = IfAST(ValueAST.new_bool(True), ValueAST.new_integer(10), ValueAST.new_integer(11))
if1 = IfAST(VarRefAST("foo"), ValueAST.new_integer(12), ValueAST.new_integer(13))

print "execute the following test cases:"
print if0.to_sexpr()
print if1.to_sexpr()

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

print "results: ", results

cond1 = uspno9.FunctionCallAST("<", [uspno9.ValueAST.new_integer(10),
                                     uspno9.ValueAST.new_integer(11)],
                                     bool)
print type(cond1)
res, stack, env = vm0.microexecute(cond1)
print res.value
print res.trace

cond2 = uspno9.FunctionCallAST("<=", [uspno9.ValueAST.new_integer(10),
                                     uspno9.ValueAST.new_integer(11)],
                                     bool)
print type(cond2)
print cond2.to_sexpr()
res, stack, env = vm0.microexecute(cond2)
print res.value
print res.trace

print "Concrete:"

cond3 = uspno9.FunctionCallAST("<=", [uspno9.VarRefAST("bar"),
                                     uspno9.ValueAST.new_integer(11)],
                                     bool)
print type(cond3)
print cond3.to_sexpr()
res = vm0.microexecute(cond3)
print res[0].value
print res[0].trace

print "Symbolic:"
cond4 = uspno9.FunctionCallAST("<=", [uspno9.VarRefAST("baz"),
                                     uspno9.ValueAST.new_integer(11)],
                                     bool)
print type(cond4)
print cond4.to_sexpr()
res, stack, env = vm0.microexecute(cond4)
print res.lhs.to_sexpr()
print res.rhs.to_sexpr()

print "\nwhile test\n====="

body = [
    FunctionCallAST("print", [VarRefAST("bar")]),
    SetValueAST("bar", FunctionCallAST("+",
                                       [VarRefAST("bar"),
                                       ValueAST.new_integer(1)]))]

while0 = WhileAST(cond3, BeginAST(body))
print while0.to_sexpr()

res, stack, env = vm0.microexecute(while0)
print res

print "\nfunction test\n====="
# Let's build a new function...

cond5 = FunctionCallAST("<=", [VarRefAST("bar"), VarRefAST("len")], bool)
while1 = WhileAST(cond5, BeginAST(body))

fnb0 = BeginAST([VariableDecAST("bar", ValueAST.new_integer(0)),
                 while1])

# need a way to represent ::void as a type...
fn0 = FunctionAST("boo", [VarRefAST("len", int)], fnb0, VoidAST)

print "Boo should not be in the environment before hand:"
print env.get_or_none("boo")

res, stack, env = vm0.microexecute(fn0)

print "Boo should be in the environment after execution:"
print env.get_or_none("boo")

print "\nBefore execution, these should be simple:"
print res
print stack
print env

(res,) = env.get_or_none("boo")

print "\nFunction name: {0}, single parameter: {1}".format(res.name, res.params)
print "function body:", res.body.to_sexpr()

print "\nLet's execute that function:"
fncall0 = FunctionCallAST("boo", [ValueAST.new_integer(1)], VoidAST)

res, stack, env = vm0.microexecute(fncall0)

print res
print stack
print env
env.walk()

print "\nANF testing...\n====="
fc0 = FunctionCallAST("*", [ValueAST.new_integer(10), ValueAST.new_integer(20)])
fc1 = FunctionCallAST("/", [ValueAST.new_integer(12), ValueAST.new_integer(4)])
fc2 = FunctionCallAST("+", [fc0, fc1])
fc3 = FunctionCallAST("-", [fc2, ValueAST.new_integer(1)])

print "original form:"

print fc2.to_sexpr()

print "\nANF variant:"
var, result = fc2.to_anf()

for v in var:
    print v.to_sexpr()

print result.to_sexpr()

print "\noriginal form:"

print fc3.to_sexpr()

print "\nANF variant:"
var, result = fc3.to_anf()

for v in var:
    print v.to_sexpr()

print result.to_sexpr()
