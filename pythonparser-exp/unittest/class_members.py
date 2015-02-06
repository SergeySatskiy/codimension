
class C:
    def __init__( self ):
        self.a = 1
        self.b = 2
        print "some"

    def f( cls ):
        cls.c = 3
        cls.d, cls.e = 4, 5

    def g():
        self.l = 0
        self.k = 6

class D:
    class E:
        def __init__( s ):
            s.m = 0
            (s.n, s.o) = 7, 8
            s.jjj[45] = 732     # Must not appear, that's usage
            (s.z.p) = 999       # Must not appear, that's usage

class F:

    @staticmethod
    def method( first ):
        first.one = 9
        first.two = 10

