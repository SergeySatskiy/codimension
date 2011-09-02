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
# $Id$
#


" brief python parser test "


import os, sys
from optparse import OptionParser
from cdmbriefparser import getBriefModuleInfoFromFile, \
                           getBriefModuleInfoFromMemory



def parserError( parser, message ):
    " Prints the message and help on stderr "

    sys.stdout = sys.stderr
    print message
    parser.print_help()
    return 1



def main():
    " main function for the netschedule multi test "

    parser = OptionParser(
    """
    %prog <file name>
    Note #1: netschedule server will be running on the same host
    """ )
    parser.add_option( "-m", "--use-memory-buffer",
                       action="store_true", dest="memory", default=False,
                       help="Read the whole file first and " \
                            "then parse it (default: False)" )

    # parse the command line options
    options, args = parser.parse_args()

    if len( args ) != 1:
        return parserError( parser, "One argument is expected" )

    fileName = os.path.abspath( args[ 0 ] )
    if not os.path.exists( fileName ):
        raise Exception( "Cannot find file to parse. Expected here: " + \
                         fileName )

    info = None
    if options.memory:
        content = file( fileName ).read()
        info = getBriefModuleInfoFromMemory( content )
    else:
        info = getBriefModuleInfoFromFile( fileName )

    print info.niceStringify()
    if info.isOK:
        print "No errors found"
    else:
        print "Errors found"

    if len( info.lexerErrors ) > 0:
        print "Lexer errors:"
        print "\n".join( info.lexerErrors )
    else:
        print "No lexer errors"

    if len( info.errors ) > 0:
        print "Parser errors:"
        print "\n".join( info.errors )
    else:
        print "No parser errors"

    return 0



# The script execution entry point
if __name__ == "__main__":
    try:
        returnValue = main()
    except Exception, excpt:
        print >> sys.stderr, str( excpt )
        returnValue = 1

    sys.exit( returnValue )

