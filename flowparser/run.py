#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id: run.py 2397 2015-03-18 19:03:10Z sergey.satskiy@gmail.com $
#

" Convinience parser launcher "

import sys


def formatFlow( s ):
    " Reformats the control flow output "
    result = ""
    shifts = []
    pos = 0

    maxIndex = len( s ) - 1
    for index in xrange( len( s ) ):
        sym = s[ index ]
        if sym == "\n":
            result += sym
            lastShift = shifts[ -1 ]
            result += lastShift * " "
            pos = lastShift
            continue
        if sym == "<":
            pos += 1
            if (index > 0 and s[ index - 1 ] == '>') or \
               (index > 1 and s[ index - 2 ] == '>'):
                result = result[ : -1 ]
            else:
                shifts.append( pos )
            result += sym
            continue
        if sym == ">":
            shift = shifts[ -1 ] - 1
            result += '\n'
            result += shift * " "
            pos = shift
            result += sym
            pos += 1
            if index < maxIndex:
                if s[ index + 1 ] == '>':
                    del shifts[ -1 ]
            continue
        result += sym
        pos += 1
    return result


from cdmcf import getControlFlowFromFile, VERSION

if len( sys.argv ) != 2:
    print >> sys.stderr, "Single file name is expected"
    sys.exit( 1 )

print "Running control flow parser version: " + VERSION

controlFlow = getControlFlowFromFile( sys.argv[ 1 ] )
print formatFlow( str( controlFlow ) )
sys.exit( 0 )

