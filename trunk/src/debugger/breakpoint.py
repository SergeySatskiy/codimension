#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Debugger breakpoint "

import os, os.path
from utils.globals import GlobalData


class Breakpoint:
    " Represents a single breakpoint "

    def __init__( self, fileName = None, lineNumber = None, condition = None,
                        temporary = False, enabled = True, ignoreCount = 0 ):

        if fileName is None:
            self.__fileName = fileName
        elif os.path.isabs( fileName ):
            project = GlobalData().project
            if project.isLoaded():
                if project.isProjectFile( fileName ):
                    # This is a project file; strip the project dir
                    self.__fileName = fileName.replace( project.getProjectDir(),
                                                        "" )
                else:
                    # Not a project file, save as is
                    self.__fileName = fileName
            else:
                # Pretty much impossible
                self.__fileName = fileName
        else:
            # Relative path, i.e. a project file
            self.__fileName = fileName

        self.__lineNumber = lineNumber
        self.__condition = condition
        self.__temporary = temporary
        self.__enabled = enabled
        self.__ignoreCount = 0

        return

    def isValid( self ):
        " True if the breakpoint is valid "
        if self.__fileName is None:
            return False

        if os.path.isabs( self.__fileName ):
            if not os.path.exists( self.__fileName ):
                return False
        else:
            project = GlobalData().project
            if project.isLoaded():
                path = project.getProjectDir() + self.__fileName
                if not os.path.exists( path ):
                    return False
            else:
                if not os.path.exists( self.__fileName ):
                    return False

        return self.__lineNumber is not None and \
               self.__lineNumber > 0

    def getFileName( self ):
        " Provides the file name "
        return self.__fileName

    def getAbsoluteFileName( self ):
        " Provides the absolute file name "
        if self.__fileName is None:
            return None
        if os.path.isabs( self.__fileName ):
            return self.__fileName

        project = GlobalData().project
        if project.isLoaded():
            return project.getProjectDir() + self.__fileName
        return os.path.abspath( self.__fileName )

    def getLineNumber( self ):
        " Provides the line number "
        return self.__lineNumber

    def getCondition( self ):
        " Provides the condition "
        return self.__condition

    def isTemporary( self ):
        " True if temporary "
        return self.__temporary

    def isEnabled( self ):
        " True if enabled "
        return self.__enabled

    def getIgnoreCount( self ):
        " Provides the ignore count "
        return self.__ignoreCount

    def getLocation( self, fullForm = False ):
        " Provides the breakpoint location "
        if self.__fileName is None:
            return str( self.__fileName ) + ":" + str( self.__lineNumber )

        if fullForm:
            return self.getAbsoluteFileName() + ":" + str( self.__lineNumber )

        return os.path.basename( self.__fileName ) + ":" + \
               str( self.__lineNumber )

    def serialize( self ):
        " Serializes the breakpoint to a string "
        return ":::".join( [ str( self.__fileName ), str( self.lineNumber ),
                             str( self.__condition ), str( self.__temporary ),
                             str( self.__enabled ), str( self.__ignoreCount ) ] )

    def deserialize( self, source ):
        " Deserializes the breakpoint "
        parts = source.split( ":::" )
        if len( parts ) != 6:
            raise Exception( "Unexpected number of fields" )

        if parts[ 0 ] == "None":
            self.__fileName = None
        else:
            self.__fileName = parts[ 0 ]

        if parts[ 1 ] == "None":
            self.__lineNumber = None
        else:
            self.__lineNumber = int( parts[ 1 ] )

        if parts[ 2 ] == "None":
            self.__condition = None
        else:
            self.__condition = parts[ 2 ]

        if parts[ 3 ] == "True":
            self.__temporary = True
        else:
            self.__temporary = False

        if parts[ 4 ] == "True":
            self.__enabled = True
        else:
            self.__enabled = False

        self.__ignoreCount = int( parts[ 5 ] )

        return self.isValid()

