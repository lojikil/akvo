# Overview

A simple test case for an intermediate representation that can be used for symbolic execution & abstract interpretation. I'm focusing on a greybox-style of 
symbex that concretizes via fuzzing.

_NOTE BENE_ This is a fork of my previous project, [Unamed Symbolic Executor Number 9](https://github.com/lojikil/uspno.9). Some refactoring has been applied
and it has been made to work with 3.x (I use 3.7 locally, but will update to 3.8 eventually)

# Exploration

This is meant to be a test bed for exploring ideas, rather than an industrial-quality grey-box path explorer. A few things I'd like to look into:

- abstract interpretation & symbolic execution in one tool
- how [Directed Automated Random Testing (DART)](https://patricegodefroid.github.io/public_psfiles/pldi2005.pdf) and [Scalable Automated Guided Execution (SAGE)](https://patricegodefroid.github.io/public_psfiles/ndss2008.pdf) can be applied outside of Microsoft
- [Eclipser](https://github.com/SoftSec-KAIST/Eclipser) is similarly an inspiration [paper link](https://softsec.kaist.ac.kr/~jschoi/data/icse2019.pdf)
- lowering the barrier to entry for program analysis for other folks, such as first-tier malware analysts
- alternative methods of concretization, such as fuzzing
- the role that regular expressions play in forming string constraints (as in, build up the possible characters for a string from what RegExs we pass)
- Negation of regular expressions to find the acceptable set of characters
- including string-focused fuzzing & generation strategies in our bag of tricks, so as to find things like XSS & SQLi
- a wider array of source & sink tracing, so as to find interesting bugs in web, blockchain, and other projects
- automatic deobfuscation of malware, akin to automatic exploit generation
- a framework like [Facebook's pfff](https://github.com/facebookarchive/pfff) for control-flow graphs, source to source translation, &c.
- the basis of something like ["Static analysis at scale at Instagram"](https://instagram-engineering.com/static-analysis-at-scale-an-instagram-story-8f498ab71a0c)
- the ability to provide ["fixes" to code, like this tweet](https://twitter.com/moyix/status/1177384798727204864?s=20) automatically [paper link](https://srg.doc.ic.ac.uk/files/papers/loops-pldi-19.pdf)
- Semantic patching like [Comby](https://comby.dev) and [Coccinelle](http://coccinelle.lip6.fr/)
- Visualization similar to [this paper on visualizing Abstract Abstract Machines](http://kyleheadley.github.io/PHDWebsite/2019-headley-aamviz-scheme-submit.pdf), with [an implementation here](https://analysisviz.gilray.net)
- Something like [MonkeyType](https://github.com/Instagram/MonkeyType) to discover types at specific execution points within programs (even if they are `union` types)
- Eventually, I'd like to include a parser so that we can easily describe new languages and map them to program semantics in the IR. This should be something simple, like Parsing Expression Grammars (PEGs).

This was the basis of [my talk](https://github.com/lojikil/fuzzy-tyrant) at [GrrCon](http://grrcon.com/presentations/#lojikil).

# Targets

I am initially focusing on loading JavaScript into the IR, due to the fact that I'm interested in malware droppers and have many client projects in JavaScript.
Additionally, I'd love to target:

- VBScript, for Office Macros
- PowerShell, for droppers and other malicious code
- PHP, for webshells and the like
- Go, because I see so much of it at work and there's no real good tools for working with it

# Programming Interface

Currently, there are two main programming interfaces to contend with:

1. the Python API (which I eventually need to make into another language such as F# or Scala)
1. the Bigloo-like Scheme language that represents the semantics of the actual program

The Python system is a set of APIs implemented as classes; these classes represent ASTs for forms such as `if` or `while`, which may be executed by a Virtual
Machine (basically, an AST walker; eventually I may add a SECD-style symbolic VM, similar to what I did for a client). The largest of these 
classes so far is the `ValueAST` class, which represents basic literals within a program:

```python
from akvo import ValueAST
g = ValueAST.new_integer(10)
h = ValueAST.new_integer(11)
j = ValueAST.new_symbolic_integer()
k = g + h
l = h + g
m = j + g
print k.trace, k.value, "\n", l.trace, l.value, "\n", m.trace, m.value
```

Values in this Bigloo-like Scheme have several annotations:

- is the value symbolic or concrete?
- is there a trace?
- a tag (UUID) for each and every value within a program

The last item is to ensure that if we see the literal `10` within a program 3 time, each location is uniquely tagged, such that we may always trace back
to the specific location that this "magic value" was introduced. Both the Scheme system and the Python API accept tags as part of values, such that if 
you reify Python Classes to Scheme, they may be reinflated with the same tags and the like.

## Execution

The _more_ interesting part of having a language, even if it is just an AST walker, is execution. To this end, akvo also supports
a style of "microexecution" of Scheme/IR forms:

```python
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
```

These will result in a series of `PathExecution` instances that detail the conditions underwhich the `if`
forms executed:

```
execute the following test cases:
(if (value True ::bool trace: True tag: 84aa56ef-5982-419a-b3d5-35a385c3c3cd) (value 10 ::int trace: 10 tag: a6cc2f6a-8c40-4fa6-a181-b490d2670802) (value 11 ::int trace: 11 tag: 2799c5f8-ed85-4946-bd21-3332f1333f2b))
(if (variable foo ::pure-symbolic) (value 12 ::int trace: 12 tag: 299ed052-c239-4ffd-87cc-9b4de5dffe1b) (value 13 ::int trace: 13 tag: 6e563b33-7d1f-4df5-b080-67a17c83b71c))

Result: (PathExecution((value 10 ::int trace: 10 tag: a6cc2f6a-8c40-4fa6-a181-b490d2670802), <akvo.ast.ValueAST object at 0x10153c630>), [], <akvo.eval.EvalEnv object at 0x101627128>)
Result: (PathExecution((value 10 ::int trace: 10 tag: a6cc2f6a-8c40-4fa6-a181-b490d2670802), <akvo.ast.ValueAST object at 0x10153c630>), [], <akvo.eval.EvalEnv object at 0x1016271d0>)
Result: (PathExecution((value 12 ::int trace: 12 tag: 299ed052-c239-4ffd-87cc-9b4de5dffe1b), <akvo.ast.VarRefAST object at 0x10160bbe0>), [], <akvo.eval.EvalEnv object at 0x101627128>)
Result: (<akvo.eval.ForkPathExecution object at 0x101627358>, [], <akvo.eval.EvalEnv object at 0x1016271d0>)
```

Note that each execution results in a `PathExecution` instance, save for the last case; here, we do not have a known value for `foo`,
and akvo informs us that there are two paths, denoted by a `ForkPathExecution` instance:

```python
result = results[-1]
print([x.to_sexpr() for x in result[0].asts])
# Displays something like: ['(value 12 ::int trace: 12 tag: c2cb1f9d-9b03-4d56-947b-660cf63880ad)', '(value 13 ::int trace: 13 tag: 84d405ec-58f8-4241-9816-f53ca1c9e62a)']
print(result[0].constraints)
# Displays: [False, True]
```

## Scheme

There is also a reader for Scheme-based forms of Code Property Graphs (CPGs) in `akvo.reader.SExpressionReader`; this can be used to
read short or canonical Scheme programs that have been saved by other passes, or expressions written by users in order to configure
an analysis or even simply general programming. This is based off the `akvo.reader.Lexeme` class.

```python
import akvo.reader
src = """(if (call < 10 11) "yes" "no")"""

lexes = Lexeme.all(src)
for lex in lexes:
    print(f"type: {lex.lexeme_type}, value: {lex.lexeme_value}")

# just an example, I'm still working on the parsing
# of expressions
reader = akvo.reader.SExpressionReader(src)
ifast = reader.read()
print(ifast.to_sexpr())
```

### Cannonical vs Short forms

You'll note that I often give examples in short form, but akvo itself always prints long, or cannonical, form. This is so that humans
can write code to the level of precision they require, and akvo always operates on the same level. Some examples follow.

```scheme
; short form
10

; cannonical form
(value 10 tag: ... trace: 10)

; short form
(call * 10 20)

; cannonical form
(call * ::pure-symbolic
    (value 10 ::int trace: 10 tag: e953a22c-8439-4eb4-a686-faff4a48b417)
    (value 20 ::int trace: 20 tag: 24f2d9f8-b851-479e-b112-c1ed9ed1a867))
```
