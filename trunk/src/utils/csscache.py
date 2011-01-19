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


" codimension CSS cache singleton "

import os.path, sys
from optparse  import OptionParser


class CSSCache( object ):
    """
    Implementation idea is taken from here:
    http://wiki.forum.nokia.com/index.php/How_to_make_a_singleton_in_Python
    """

    _iInstance = None
    class Singleton:
        " Provides css cache singleton facility "

        def __init__( self ):
            self.__cache = {}
            abspath = os.path.abspath( sys.argv[ 0 ] )
            self.__searchPath = os.path.dirname( abspath ) + \
                                os.path.sep + 'css' + os.path.sep
            return

        def getCSS( self, name ):
            " Provides the required CSS content or an empty string "

            if name.endswith( '.css' ):
                name = name[ : -4 ]     # strip .css
            name = name.replace( os.path.sep, '.' )

            try:
                return self.__cache[ name ]
            except KeyError:
                path = self.__searchPath + name.replace( '.', os.path.sep ) + \
                       ".css"
                if not os.path.exists( path ):
                    self.__cache[ name ] = ""
                    return ""

                content = self.__getCSSContent( path )
                self.__cache[ name ] = content
                return content

        def __getCSSContent( self, path ):
            " Provides the resolved CSS content "

            content = []
            self.__parseSingleCSS( path, content )
            return "".join( content )

        def __parseSingleCSS( self, path, content ):
            """ Recursive function to get a single CSS content
                with removed comment lines and resolved INCLUDEs """

            f = open( path )
            for line in f:
                if line.strip().startswith( '//' ):
                    continue
                if line.strip().upper().startswith( 'INCLUDE' ):
                    parts = line.strip().split()
                    if len( parts ) != 2:
                        raise Exception( "Unexpected line format: '" + line + \
                                         "' in file '" + path + "'" )

                    fileName = parts[1].strip()
                    if fileName.startswith( '/' ):
                        # absolute path
                        if not os.path.exists( fileName ):
                            raise Exception( "INCLUDE file '" + fileName + \
                                             "' in '" + path + \
                                             "' has not been found" )
                        self.__parseSingleCSS( fileName, content )
                        continue

                    # relative path
                    includedFileName = os.path.dirname( path ) + '/' + fileName
                    includedFileName = os.path.normpath( includedFileName )
                    if not os.path.exists( includedFileName ):
                        raise Exception( "INCLUDE file '" + fileName + "' (" + \
                                         includedFileName + ") in '" + path + \
                                         "' has not been found" )
                    self.__parseSingleCSS( includedFileName, content )
                    continue
                # Some line
                if len( line.strip() ) > 0:
                    content.append( line )

            f.close()
            return

    def __init__( self ):
        if CSSCache._iInstance is None:
            CSSCache._iInstance = CSSCache.Singleton()

        self.__dict__[ '_CSSCache__iInstance' ] = CSSCache._iInstance
        return

    def __getattr__( self, aAttr ):
        return getattr( self._iInstance, aAttr )


# The script execution entry point
if __name__ == "__main__":

    parser = OptionParser(
    """
    %prog  <css name>
    Prints the resolved css
    Css name could be with or without .css extension
    The css file is serached in the ./css/ directory
    The nested css path must be given with . separator, e.g.: my.path.file
    """ )

    options, args = parser.parse_args()

    if len( args ) != 1:
        print >> sys.stderr, "One arguments expected"
        sys.exit( 1 )

    cache = CSSCache()
    resolvedContent = cache.getCSS( args[ 0 ] )
    print "Resolved css for " + args[ 0 ] + ":"
    if resolvedContent == "":
        print "CSS not found"
    else:
        print resolvedContent

    sys.exit( 0 )
