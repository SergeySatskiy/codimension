""" Utility functions used throughout the PyMetrics system.

    $Id$
"""

import sys
import token
import re

def sqlQ( s ):
    """ Place single quotes around strings and escaping existing single quotes."""
    a = s.replace( "\\","\\\\" )
    a = a.replace( "'", "\\'" )
    a = a.replace( '"', '\\"' )
    return '"'+a+'"'
    
def csvQ( s ):
    """ Quote a string using rules for CSV data."""
    a = s.replace("\\","\\\\")
    b = a.replace( "'", "\\'" )
    c = b.replace( "\n", "\\n" )
    d = c.replace( '"', '""' )
    return '"'+d+'"'
    
def toTypeName( context, lst ):
    """ Convert token type numbers to names."""
    lstOut = []
    for name,blockDepth,semtype in lst:
        try:
            semName = token.tok_name[semtype]
            lstOut.append( (name,blockDepth,semName) )
        except KeyError, e:
            raise KeyError( "Unknown value '"+str( e )+"' for token/semantic type in context %s\n" % context )
    
    return lstOut
    
if 0:
    def mainTest():
        """ Built-in tests """
        def check( qs, s ):
            print "<%s>==<%s>" % (s.__repr__(),qs.__repr__())
            print "[%s]==[%s]" % (s,qs)
            try:
              assert( s.__repr__() == qs.__repr__() )
              assert( s, qs )
            except AssertionError:
              print "Failed"
        
        s0 = ''; qs0 = sqlQ(s0)
        check( qs0,  '""' )
        s1 = 'aName'; qs1 = sqlQ(s1)
        check( qs1, '"aName"' )
        s2 = 'A literal with a double quote (\") in it'; qs2 = sqlQ( s2 )
        check( qs2, '"A literal with a double quote (\\\") in it"' )
        s3 = '\'A literal with a single quote (\') in it\''; qs3 = sqlQ( s3 )
        check( qs3, '"\\\'A literal with a single quote (\\\') in it\\\'"' )
        s4 = """A multi-
    line literal."""; qs4 = sqlQ( s4 )
        check( qs4, '"A multi-\nline literal."' )
        
    if __name__ == "__main__":
        mainTest()
