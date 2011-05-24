class A:
    pass

class A1():
    pass

class A2( a ):
    pass

class A3( a, b, c ):
    pass

class A4( a,
          b.c,
          d ):
    pass


class B( a.b.c.d.e ):
    def __init__( self ):
        pass

class B1( a.b, c.d ):
    def a( cls, e = f[ 18 + 35 ], g = "bla" ):
        pass
    def b( self, h ):
        pass
    def c( other, k, l = [] ):
        pass

# Class A again
class A:
    def overriden( self ):
        pass

