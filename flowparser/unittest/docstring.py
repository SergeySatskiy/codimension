
""" Module multiline docstring
    Second aligned string

"""

def f():
    " Single line single double-quote "
    pass

def f():
    ' Single line single single-quote '
    pass

def f():
    """ Single line three single-quote """
    pass

def f():
    ''' Single line three single-quote '''
    pass

def f():
    """
    Multiline 1
    Multiline 2
    """
    pass

def f():
    '''
    Multiline 1-2
              ^^^ digits
    '''
    pass

def f():
    class C:
        ''' Nested class docstring
            Second line '''
        def __init__( self ):
            """No space in first line
second line

third line"""
            pass

