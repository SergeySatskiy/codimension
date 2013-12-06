# The generated code requires minor adjustments which are done here

import sys

f = open( "pythonbriefParser.c", "r" )
content = f.read()
f.close()

content = content.replace( "INPUT->_LT(INPUT, n)", "tokLT(INPUT, n)" )

f = open( "pythonbriefParser.c", "w" )
f.write( content )
f.close()

sys.exit( 0 )

