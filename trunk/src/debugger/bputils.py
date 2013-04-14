#!/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011  Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id$
#
# The idea for the calculating the valid lines is taken from rpdb2.
#


validBreakPointLinesCache = {}


def clearValidBreakpointLinesCache():
    " Resets the cache "
    global validBreakPointLinesCache
    validBreakPointLinesCache = {}
    return


def getBreakpointLines( fileName, srcCode ):
    " Provides a set of breakable lines "
    global validBreakPointLinesCache

    if validBreakPointLinesCache.has_key( fileName ):
        return validBreakPointLinesCache[ fileName ]

    try:
        if srcCode is None:
            f = open( fileName )
            srcCode = f.read()
            f.close()
        lines = calcBreakpointLines( srcCode )
        validBreakPointLinesCache[ fileName ] = lines
        return lines
    except:
        return None



def calcBreakpointLines( sourceCode ):
    " Calculates valid breakpoint lines "

    def __safeOrd( char ):
        " Exception safe ord "
        try:
            return ord( char )
        except:
            return char

    def __calcValidLines( code, validLines ):
        " Calculates valid breakpoint lines "
        l = code.co_firstlineno
        validLines.add( l )
        bl = [ __safeOrd( c ) for c in code.co_lnotab[ 2::2 ] ]
        sl = [ __safeOrd( c ) for c in code.co_lnotab[ 1::2 ] ]
        for ( bi, si ) in zip( bl, sl ):
            l += si
            if bi == 0:
                continue
            validLines.add( l )
        if sl:
            l += sl[-1]
            validLines.add( l )
        return

    def __calcSubCodesList( code ):
        " Adds nested fragments "
        tc = type( code )
        t = [(c.co_firstlineno, c) for c in code.co_consts if type(c) == tc]
        t.sort()
        scl = [c[1] for c in t]
        return scl


    code = compile( sourceCode, '', "exec" )

    t = [ code ]
    validLines = set()

    while t:
        c = t.pop(0)
        __calcValidLines( c, validLines )
        subcodeslist = __calcSubCodesList( c )
        t = subcodeslist + t

    return validLines


if __name__ == "__main__":
    import sys
    if len( sys.argv ) != 2:
        print >> sys.stderr, "Expected python file name"
        sys.exit( 1 )

    print "Valid break point lines:"
    print calcBreakpointLines( open( sys.argv[ 1 ] ).read() )
    sys.exit( 0 )

