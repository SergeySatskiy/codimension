import sys
sys.path.insert( 0, 'pyds%d%d' % (sys.version_info[0], sys.version_info[1]) )

import pycxx_iter

it = pycxx_iter.IterT( 5, 7 )


for i in it:
    print( i, it )

print( "refcount of it:", sys.getrefcount( it ) )

for i in it.reversed():
    print( i )

print( "refcount of it:", sys.getrefcount( it ) )
