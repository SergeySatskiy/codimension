" Classes "

# Leading
class C( ClassA,        # Side
         ClassB ):
    """ Docstring """
    def __init__( self ):
        ClassA.__init__( self )
        self.__x = 0
