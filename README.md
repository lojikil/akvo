# Overview

A simple test case for an intermediate representation that can be used for symbolic execution & abstract interpretation. I'm focusing on a greybox-style of 
symbex that concretizes via fuzzing.

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
from uspno9 import ValueAST
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
