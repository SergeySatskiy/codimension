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
# The implementation vastly derived from eric4. Here is the original copyright:
# Copyright (c) 2002 - 2013 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""Debugger variable browser items"""

from ui.qt import Qt, QTreeWidgetItem
from utils.pixmapcache import getIcon


def getDisplayValue( displayValue ):
    " Takes potentially multilined value and converts it to a single line "

    lines = str( displayValue ).splitlines()
    lineCount = len( lines )
    if lineCount > 1:
        # There are many lines. Find first non-empty.
        nonEmptyIndex = None
        index = -1
        for line in lines:
            index += 1
            if len( line.strip() ) > 0:
                nonEmptyIndex = index
                break
        if nonEmptyIndex is None:
            displayValue = ""   # Multilined empty string
        else:
            if len( lines[ nonEmptyIndex ] ) > 128:
                displayValue = lines[ nonEmptyIndex ][ : 128 ] + "<...>"
            else:
                displayValue = lines[ nonEmptyIndex ]
                if nonEmptyIndex < lineCount - 1:
                    displayValue += "<...>"

            if nonEmptyIndex > 0:
                displayValue = "<...>" + displayValue
    elif lineCount == 1:
        # There is just one line
        if len( lines[ 0 ] ) > 128:
            displayValue = lines[ 0 ][ : 128 ] + "<...>"
        else:
            value = lines[ 0 ]

    return displayValue


def getTooltipValue( value ):
    """ Takes a potentially multilined string and converts it to
        the form suitable for tooltips """

    value = str( value )
    if Qt.mightBeRichText( value ):
        tooltipValue = str( Qt.escape( value ) )
    else:
        tooltipValue = value

    lines = tooltipValue.splitlines()
    lineCount = len( lines )
    if lineCount > 1:
        value = ""
        index = 0
        for line in lines:
            if index >= 5:  # First 5 lines only
                break
            if index > 0:
                value += "\n"
            if len( line ) > 128:
                value += line[ : 128 ] + "<...>"
            else:
                value += line
            index += 1
        if lineCount > 5:
            value += "\n<...>"
    elif lineCount == 1:
        if len( lines[ 0 ] ) > 128:
            value = lines[ 0 ][ : 128 ] + "<...>"
        else:
            value = lines[ 0 ]

    return value



class VariableItem( QTreeWidgetItem ):
    " Base structure for variable items "

    def __init__( self, parent, isGlobal,
                        displayName, displayValue, displayType ):
        self.__isGlobal = isGlobal
        self.__value = displayValue
        self.__name = displayName
        self.__type = displayType

        # Decide about the display value
        displayValue = getDisplayValue( displayValue )

        # Decide about the tooltip
        self.__tooltip = "Name: " + displayName + "\n" + \
                         "Type: " + displayType + "\n" + \
                         "Value: "

        tooltipDisplayValue = getTooltipValue( self.__value )
        if '\r' in tooltipDisplayValue or '\n' in tooltipDisplayValue:
            self.__tooltip += "\n" + tooltipDisplayValue
        else:
            self.__tooltip += tooltipDisplayValue

        QTreeWidgetItem.__init__( self, parent, [ displayName, displayValue,
                                                  displayType ] )

        self.populated = True
        return

    def getValue( self ):
        " Provides the variable value "
        return self.__value

    def getName( self ):
        " Provides the variable name "
        return self.__name

    def getType( self ):
        " Provides the variable type "
        return self.__type

    def isGlobal( self ):
        " Tells if the variable is global "
        return self.__isGlobal

    def data( self, column, role ):
        " Provides the data for the requested role "
        if role == Qt.ToolTipRole:
            return self.__tooltip
        if role == Qt.DecorationRole:
            if column == 0:
                if not self.parent():
                    if self.__isGlobal:
                        fileName = 'globvar.png'
                    else:
                        fileName = 'locvar.png'
                    return getIcon( fileName )
        return QTreeWidgetItem.data( self, column, role )

    def attachDummy( self ):
        " Attach a dummy sub item to allow for lazy population "
        QTreeWidgetItem( self, [ "DUMMY" ] )
        return

    def deleteChildren( self ):
        " Deletes all children (cleaning the subtree) "
        for item in self.takeChildren():
            del item

    def key( self, column ):
        """ Generates the key for this item.
            @param column the column to sort on (integer)
        """
        return self.text( column )

    def __lt__( self, other ):
        column = self.treeWidget().sortColumn()
        return self.key( column ) < other.key( column )

    def expand( self ):
        " Does nothing for the basic item. Should be overwritten "
        return

    def collapse( self ):
        " Does nothing for the basic item. Should be overwritten "
        return


class SpecialVariableItem( VariableItem ):
    """
    These special variable nodes are generated for classes, lists,
    tuples and dictionaries.
    """

    def __init__( self, parent, debugger, isGlobal,
                        displayName, displayValue, displayType, frameNumber ):
        VariableItem.__init__( self, parent, isGlobal,
                                     displayName, displayValue, displayType )
        self.attachDummy()
        self.populated = False

        self.frameNumber = frameNumber
        self.__debugger = debugger
        return

    def expand( self ):
        " Expands the item "
        self.deleteChildren()
        self.populated = True

        pathlist = [ str( self.text( 0 ) ) ]
        par = self.parent()

        # Step 1: get a pathlist up to the requested variable
        while par is not None:
            pathlist.insert( 0, str( par.text( 0 ) ) )
            par = par.parent()

        # Step 2: request the variable from the debugger
        self.__debugger.remoteClientVariable( self.isGlobal(),
                                              pathlist, self.frameNumber )
        return



class ArrayElementVariableItem( VariableItem ):
    " Represents an array element "

    def __init__( self, parent, isGlobal, displayName, displayValue, displayType ):

        VariableItem.__init__( self, parent, isGlobal,
                                     displayName, displayValue, displayType )

        """
        Array elements have numbers as names, but the key must be
        right justified and zero filled to 6 decimal places. Then
        element 2 will have a key of '000002' and appear before
        element 10 with a key of '000010'
        """
        keyStr = str( self.text( 0 ) )
        self.arrayElementKey = "%.6d" % int( keyStr )
        return

    def key( self, column ):
        " Generates the key for this item "
        if column == 0:
            return self.arrayElementKey
        return VariableItem.key( self, column )



class SpecialArrayElementVariableItem( SpecialVariableItem ):
    " Represents a special array variable node "

    def __init__( self, parent, debugger, isGlobal,
                        displayName, displayValue, displayType, frameNumber ):

        SpecialVariableItem.__init__( self, parent, debugger, isGlobal,
                                      displayName, displayValue, displayType, frameNumber )

        """
        Array elements have numbers as names, but the key must be
        right justified and zero filled to 6 decimal places. Then
        element 2 will have a key of '000002' and appear before
        element 10 with a key of '000010'
        """
        keyStr = str( self.text( 0 ) )[ : -2 ]     # strip off [], () or {}
        self.arrayElementKey = "%.6d" % int( keyStr )
        return

    def key( self, column ):
        " Generates the key for this item "

        if column == 0:
            return self.arrayElementKey
        return SpecialVariableItem.key( self, column )

