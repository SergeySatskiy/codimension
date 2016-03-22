
" sys.exit() "

if True:
    import sys
    sys.exit( 1 )

    from sys import exit
    exit( 2 )
else:
    from sys import exit as f
    f( 3 )

    from sys import *
    # Leading
    exit( 4 )   # Side
