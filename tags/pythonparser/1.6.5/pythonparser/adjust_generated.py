# The generated code requires minor adjustments which are done here

import sys

f = open( "pythonbriefParser.c", "r" )
content = f.read()
f.close()

content = content.replace( "INPUT->_LT(INPUT, n)", "tokLT(INPUT, n)" )
content = content.replace( "FOLLOWSTACK->push(FOLLOWSTACK, ((void *)(&(x))), NULL)", "stackPush(FOLLOWSTACK, ((void *)(&(x))), NULL)" )
content = content.replace( "FOLLOWSTACK->pop(FOLLOWSTACK)", "stackPop(FOLLOWSTACK)" )

f = open( "pythonbriefParser.c", "w" )
f.write( content )
f.close()

sys.exit( 0 )

