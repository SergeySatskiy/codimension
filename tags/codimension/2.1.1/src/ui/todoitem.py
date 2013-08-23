#
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
# $Id: todoitem.py 17 2011-01-16 21:23:13Z sergey.satskiy@gmail.com $
#


""" todo item implementation """

from PyQt4.QtCore import Qt, QStringList
from PyQt4.QtGui import QTreeWidgetItem, QColor

from utils.pixmapcache  import PixmapCache

__separator = " -++- "

class TodoItem( QTreeWidgetItem ):
    """ Single todo item data structure """

    def __init__( self, description, fileName = "", lineNumber = 0,
                  completed = False, isFixme = False ):

        self.__completed = completed
        self.__description = description
        self.__filename = fileName
        self.__lineno = lineNumber
        self.__isfixme = isFixme

        QTreeWidgetItem.__init__( self,
            QStringList() << "" \
                          << self.__filename \
                          << (self.__lineno and "%6d" % self.__lineno or "") \
                          << self.__description )

        self.setCompleted( completed )
        self.colorizeTask()

        # Alignment for the line number column
        self.setTextAlignment( 2, Qt.AlignRight )
        return

    def colorizeTask( self ):
        """ Set the color of the task item """

        index = 0
        while index <= 3:
            if self.__isfixme:
                self.setTextColor( index, QColor( Qt.red ) )
            else:
                self.setTextColor( index, QColor( Qt.black ) )
            index += 1
        return

    def setDescription( self, description ):
        """ Updates the description """

        self.__description = description
        self.setText( 3, self.__description )
        return

    def setCompleted( self, completed ):
        """ Updates the completed flag """

        self.__completed = completed
        if self.__completed:
            self.setIcon( 0, PixmapCache().getIcon( "taskcompleted.png" ) )
        else:
            self.setIcon( 0, PixmapCache().getIcon( "empty.png" ) )
        return

    def isCompleted( self ):
        """ Provides the completion status """

        return self.__completed

    def getFilename( self ):
        """ Provides the filename """

        return self.__filename

    def getLineNumber( self ):
        """ Provides the line number """

        return self.__lineno

    def __str__( self ):

        return str( self.__completed ) + __separator + \
               str( self.__isfixme ) + __separator + \
               self.__filename + __separator + \
               self.__lineno + __separator + \
               self.__description


def parseTodoItem( string ):
    """ Parses a string and creates a todo item """

    parts = string.split( __separator )
    if len( parts ) < 5:
        raise Exception( "Cannot parse string representation of a todo item. " \
                         "Expected 5 parts or more. Found " + \
                         str( len(parts) ) + ". Line: " + string )

    completed = parts[0] == "True"
    isFixme = parts[1] == "True"
    fileName = parts[2]
    lineNumber = int( parts[3] )

    # The description may contain the separator too...
    description = ""
    if len( parts ) == 5:
        # the description does not contain separator
        description = parts[4]
    else:
        description = string.replace( __separator.join( parts[ 4: ] ), '' )

    return TodoItem( description, fileName, lineNumber, completed, isFixme )

