import uspno9
f = uspno9.VariableDecAST("f", uspno9.ValueAST(int, 10), int)
print f.to_sexpr()
g = uspno9.VariableDecAST("g", uspno9.ValueAST(int), int)
h = uspno9.VariableDecAST("h", vtype=int)
print g.to_sexpr()
print h.to_sexpr()
j = uspno9.VariableDecAST("j")
print j.to_sexpr()

cond0 = uspno9.FunctionCallAST("<", [uspno9.VarRefAST("f", int),
                                     uspno9.VarRefAST("g", int,
                                                      symbolic=True)],
                                     bool)
then0 = uspno9.FunctionCallAST("print", [uspno9.ValueAST(str, "then")], str)
else0 = uspno9.FunctionCallAST("print", [uspno9.ValueAST(str, "else")], str)
if0 = uspno9.IfAST(cond0, then0, else0)

print if0.to_sexpr()
