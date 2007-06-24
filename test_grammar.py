import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import GDBMIParser
import GDBMILexer

reload(GDBMIParser)
reload(GDBMILexer)

import sys
import antlr3
import antlr3.tree

def parse(file):
    fp = open(file)
    char_stream = antlr3.ANTLRInputStream(fp)
    lexer = GDBMILexer.GDBMILexer(char_stream)
    tokens = antlr3.CommonTokenStream(lexer)
    parser = GDBMIParser.GDBMIParser(tokens)
    fp.close()
    
    return lexer, tokens, parser 


if __name__ == "__main__":

    lexer, tokens, parser = parse("tests/test2.txt")
    response = parser.output().response
    print response.result.cls
    print response.result
