import simple
import time
import sys
import os

def report( title ):
    print( title )
    os.system( 'ps uww -p %d' % (os.getpid(),) )

report( 'Start:' )

if sys.argv[1] == 'encode':
    for x in range( 1000000 ):
        y = '%6d-Hello-%6d' % (x, x)
else:
    for x in range( 1000000 ):
        y = ('%6d-Hello-%6d' % (x, x)).encode( 'utf-8' )

report( 'InitDone:' )

if sys.argv[1] == 'encode':
    for x in range( 1000000 ):
        y = simple.encode_test( '%6d-Hello-%6d' % (x, x) )
else:
    for x in range( 1000000 ):
        y = simple.decode_test( ('%6d-Hello-%6d' % (x, x)).encode( 'utf-8' ) )

report( 'Done:' )
