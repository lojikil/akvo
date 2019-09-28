# Overview

A simple test case for an intermediate representation that can be used for symbolic execution & abstract interpretation. I'm focusing on a greybox-style of 
symbex that concretizes via fuzzing.

# Exploration

This is meant to be a test bed for exploring ideas, rather than an industrial-quality grey-box path explorer. A few things I'd like to look into:

- abstract interpretation & symbolic execution in one tool
- how [Directed Automated Random Testing (DART)](https://patricegodefroid.github.io/public_psfiles/pldi2005.pdf) and [Scalable Automated Guided Execution (SAGE)](https://patricegodefroid.github.io/public_psfiles/ndss2008.pdf) can be applied outside of Microsoft
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

This will also be the basis of my talk at [GrrCon](http://grrcon.com/presentations/#lojikil).

# Targets

I am initially focusing on loading JavaScript into the IR, due to the fact that I'm interested in malware droppers and have many client projects in JavaScript.
Additionally, I'd love to target:

- VBScript, for Office Macros
- PowerShell, for droppers and other malicious code
- PHP, for webshells and the like
- Go, because I see so much of it at work and there's no real good tools for working with it
