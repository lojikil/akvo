import uspno9
f = uspno9.VariableDecAST("f", uspno9.ValueAST(int, 10), int)
print f.to_sexpr()
g = uspno9.VariableDecAST("g", uspno9.ValueAST(int), int)
h = uspno9.VariableDecAST("h", vtype=int)
print g.to_sexpr()
print h.to_sexpr()
