
@decor
def f():
    pass

@decor()
def f():
    pass

@decor( a, b, c = "warp" )
def f():
    pass

@decor( a,
        b = 12,
        c = 32 )
def f():
    pass

@decor1
@decor2
@decor3
def f():
    pass

@decor1
@decor2( a, b.c, d )
def f():
    pass

def f():
    def g():
        @decor1( a, b )
        @decor2( c, d=1 )
        class C:
            def f():
                pass
            @decor11( e )
            def g():
                pass
    pass

