# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""
Virtual canvas to represent a control flow
The basic idea is to split the canvas into cells and each cell could
be whether a vacant or filled with a certain graphics element.

At the very beginning the canvas is empty and can grow left, right or down
when a new element needs to be inserted.

The whole canvas is split into independent sections. The growing in one section
does not affect all the other sections.
"""

from items import ( kindToString,
                    CellElement, VacantCell, CodeBlockCell, ScopeCellElement,
                    FileScopeCell, FunctionScopeCell, ClassScopeCell,
                    ForScopeCell, WhileScopeCell, TryScopeCell,
                    WithScopeCell, DecoratorScopeCell, ElseScopeCell,
                    ExceptScopeCell, FinallyScopeCell )
from cdmcf import CODEBLOCK_FRAGMENT


_scopeToClass = {
    CellElement.FILE_SCOPE:     FileScopeCell,
    CellElement.FUNC_SCOPE:     FunctionScopeCell,
    CellElement.CLASS_SCOPE:    ClassScopeCell,
    CellElement.FOR_SCOPE:      ForScopeCell,
    CellElement.WHILE_SCOPE:    WhileScopeCell,
    CellElement.TRY_SCOPE:      TryScopeCell,
    CellElement.WITH_SCOPE:     WithScopeCell,
    CellElement.DECOR_SCOPE:    DecoratorScopeCell,
    CellElement.ELSE_SCOPE:     ElseScopeCell,
    CellElement.EXCEPT_SCOPE:   ExceptScopeCell,
    CellElement.FINALLY_SCOPE:  FinallyScopeCell
}



class VirtualCanvas:
    " Holds the control flow representation "

    def __init__( self, parent = None ):
        self.cells = []                 # Stores the item instances
                                        # from items.py or other virtual
                                        # canvases
        self.parent = parent            # Reference to the upper level canvas

        # Layout support
        self.__currentCF = None
        self.__currentScopeClass = None
        return

    def clear( self ):
        " Resets the layout "
        self.cells = []
        self.parent = None
        self.__currentScopeClass = None
        return

    def __str__( self ):
        s = "Rows: " + str( len( self.cells ) )
        c = 0
        for row in self.cells:
            s += "\nRow " + str( c ) + ": [ "
            for item in row:
                if hasattr( item, "kind" ):
                    s += kindToString( item.kind ) + ", "
                else:
                    s += "VirtualCanvas, "
            s += "]"
            c += 1
        return s

    def render( self, settings ):
        " Preforms rendering for all the cells "
        return (0, 0)

    def draw( self, scene ):
        " Draws the diagram on the real canvas "
        return

    def __allocateCell( self, row, column, needScopeEdge = True ):
        """ Allocates a cell as Vacant if it is not available yet
            Can only allocate bottom and right growing cells
        """
        lastIndex = len( self.cells ) - 1
        while lastIndex < row:
            self.cells.append( [] )
            lastIndex += 1
            if needScopeEdge:
                self.cells[ lastIndex ].append(
                    self.__currentScopeClass( self.__currentCF,
                                              ScopeCellElement.LEFT ) )
        lastIndex = len( self.cells[ row ] ) - 1
        while lastIndex < column:
            self.cells[ row ].append( VacantCell() )
            lastIndex += 1
        return

    def layout( self, cf, scopeKind = CellElement.FILE_SCOPE ):
        " Does the layout "

        self.__currentCF = cf
        self.__currentScopeClass = _scopeToClass[ scopeKind ]

        # Allocate the scope header
        headerRow = 0
        if hasattr( cf, "leadingComment" ):
            if cf.leadingComment:
                self.__allocateCell( 0, 2, False )  # No left scope edge required
                self.cells[ 0 ][ 2 ] = self.__currentScopeClass( self.__currentCF,
                                                ScopeCellElement.LEADING_COMMENT )
                headerRow = 1

        self.__allocateCell( headerRow, 1, False )
        self.cells[ headerRow ][ 0 ] = self.__currentScopeClass( cf, ScopeCellElement.TOP_LEFT )
        self.cells[ headerRow ][ 1 ] = self.__currentScopeClass( cf, ScopeCellElement.TOP )
        headerRow += 1
        self.__allocateCell( headerRow, 1 )
        self.cells[ headerRow ][ 1 ] = self.__currentScopeClass( cf, ScopeCellElement.DECLARATION )

        if hasattr( cf, "sideComment" ):
            if cf.sideComment:
                self.__allocateCell( headerRow - 1, 2 )
                self.cells[ headerRow - 1 ][ 2 ] = self.__currentScopeClass( cf, ScopeCellElement.TOP )
                self.__allocateCell( headerRow, 2 )
                self.cells[ headerRow ][ 2 ] = self.__currentScopeClass( cf, ScopeCellElement.SIDE_COMMENT )

        vacantRow = headerRow + 1
        if hasattr( cf, "docstring" ):
            if cf.docstring:
                self.__allocateCell( vacantRow, 1 )
                self.cells[ vacantRow ][ 1 ] = self.__currentScopeClass( cf, ScopeCellElement.DOCSTRING )
                vacantRow += 1

        # walk the suite
        for item in cf.suite:
            if item.kind == CODEBLOCK_FRAGMENT:
                self.__allocateCell( vacantRow, 1 )
                self.cells[ vacantRow ][ 1 ] = CodeBlockCell( item )
                vacantRow += 1
                continue


        # Allocate the scope footer
        self.__allocateCell( vacantRow, 1, False )
        self.cells[ vacantRow ][ 0 ] = self.__currentScopeClass( cf, ScopeCellElement.BOTTOM_LEFT )
        self.cells[ vacantRow ][ 1 ] = self.__currentScopeClass( cf, ScopeCellElement.BOTTOM )
        return

