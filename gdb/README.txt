This package forms the interface to GDB.

Currently the grammar that's used to parse the GDB/MI language is written in ANTLR3

The version of ANTLR3 that's used to compile the lexer/parser is 3.1.2

The grammar cited in the GDB/MI documentation is NOT comprehensive.  Though the grammar is adherent mostly to the spec, 
it appears that GDB can actually be a bit funny about certain asynchronous messages, so the grammar is not fully utilized.
The output from GDB is parsed a single line at a time, rather than being delimited by '(gdb)' end of message indicators. 
Any lines composed solely of '(gdb)' are stripped from the input stream, and any other nonblank lines are processed a single
line at a time, unmodified.