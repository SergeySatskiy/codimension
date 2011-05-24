""" This is script doc string. """
g = 1               # block 1 at level 0
    # this is a comment that starts a line after indent
# this comment starts in column 1
h=2     # another inline comment
    # see if this comment is preceded by whitespace

def f(a,b,c):       # function with multiple returns
    """ This is multi-line
    function doc string.
    """
    if a > b:       # block 2 at level 1
        if b > c:   # block 3 at level 2
            a = c   # block 4 at level 3
        else:       # block 3 at level 2
            return  # block 4 at level 3 - explicit return
    print a         # block 2 at level 1
                    # implicit return
                    
                    
f(1,2,3)            # block 1 at level 0

[f(i,3,5) for i in range(5)]

def g(a,b):
    a += 1
    if a > 'c': print "a is larger"
    def h(b):
        return b*b
    return h(b)

g(3,2)
v = 123
# this function definition shows that parameter names are not
# defined until after the parameter list is completed. That is,
# it is invalid to define: def h(a,b=a): ...
def h(a, b=v,c=(v,),d={'a':(2,4,6)},e=[3,5,7]):
    print "b: a=%s b=%s" % (a,b)

def     k(  a   ,   b   )   :
    c = a
    d = b
    if c > d: return d
    def kk( c ):
        return c*c
    return kk(c+d)
    
class C:
    """ This is class doc string."""
    def __init__( self ):
        """ This is a member function doc string"""
        if 1:
            return
        elif 0: return
        
    class D (object):
        def dd( self, *args, **kwds ):
            return args, kwds

def main():
    "This is single line doc string"
    h(3)
    c = C()
    g(3,2)
    f(7,5,3)
    # next, test if whitespace affects token sequences
    h   (  'a' ,   'z' )   [   1   :   ]
    # next, test tokenization for statement that crosses lines
    h   (
    'b'
    ,
    'y'
    )   [
    1
    :
    ]
    
if __name__ == "__main__":
    main()
