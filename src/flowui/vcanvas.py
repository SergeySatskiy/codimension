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
                    ExceptScopeCell, FinallyScopeCell,
                    BreakCell, ContinueCell, ReturnCell, RaiseCell,
                    AssertCell, SysexitCell, ImportCell, IndependentCommentCell,
                    LeadingCommentCell, SideCommentCell, ConnectorCell )
from cdmcf import ( CODEBLOCK_FRAGMENT, FUNCTION_FRAGMENT, CLASS_FRAGMENT,
                    BREAK_FRAGMENT, CONTINUE_FRAGMENT, RETURN_FRAGMENT,
                    RAISE_FRAGMENT, ASSERT_FRAGMENT, SYSEXIT_FRAGMENT,
                    IMPORT_FRAGMENT, COMMENT_FRAGMENT,
                    WHILE_FRAGMENT, FOR_FRAGMENT, IF_FRAGMENT,
                    WITH_FRAGMENT, TRY_FRAGMENT )

_scopeToClass = {
    CellElement.NO_SCOPE:       None,
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

_fragmentKindToCellClass = {
    CODEBLOCK_FRAGMENT:     CodeBlockCell,
    BREAK_FRAGMENT:         BreakCell,
    CONTINUE_FRAGMENT:      ContinueCell,
    RETURN_FRAGMENT:        ReturnCell,
    RAISE_FRAGMENT:         RaiseCell,
    ASSERT_FRAGMENT:        AssertCell,
    SYSEXIT_FRAGMENT:       SysexitCell,
    IMPORT_FRAGMENT:        ImportCell
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
                s += str( item ) + ", "
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
                if self.__currentScopeClass:
                    self.cells[ lastIndex ].append(
                        self.__currentScopeClass( self.__currentCF,
                                                  ScopeCellElement.LEFT ) )
        lastIndex = len( self.cells[ row ] ) - 1
        while lastIndex < column:
            self.cells[ row ].append( VacantCell() )
            lastIndex += 1
        return

    def layoutSuite( self, vacantRow, suite,
                     scopeKind = None, cf = None, column = 1 ):
        " Does a single sute layout "
        if scopeKind:
            self.__currentCF = cf
            self.__currentScopeClass = _scopeToClass[ scopeKind ]

        for item in suite:
            if item.kind in [ FUNCTION_FRAGMENT, CLASS_FRAGMENT ]:
                scopeCanvas = VirtualCanvas( self )
                if item.kind == FUNCTION_FRAGMENT:
                    scopeCanvas.layout( item, CellElement.FUNCTION_SCOPE )
                else:
                    scopeCanvas.layout( item, CellElement.CLASS_SCOPE )

                if item.decors:
                    for dec in reversed( item.decors ):
                        # Create a decorator scope virtual canvas
                        decScope = VirtualCanvas()
                        decScope.layout( dec, CellElement.DECOR_SCOPE )
                        # Fix the parent
                        scopeCanvas.parent = decScope
                        # Set the decorator content
                        decScope.cells[ -2 ][ 1 ] = scopeCanvas
                        # Set the current content scope
                        scopeCanvas = decScope

                # Update the scope canvas parent
                scopeCanvas.parent = self

                self.__allocateCell( vacantRow, column )
                self.cells[ vacantRow ][ column ] = scopeCanvas
                vacantRow += 1
                continue

            if item.kind == WITH_FRAGMENT:
                scopeCanvas = VirtualCanvas( self )
                scopeCanvas.layout( item, CellElement.WITH_SCOPE )
                self.__allocateCell( vacantRow, column )
                self.cells[ vacantRow ][ column ] = scopeCanvas
                vacantRow += 1
                continue

            if item.kind == WHILE_FRAGMENT:
                scopeCanvas = VirtualCanvas( self )
                scopeCanvas.layout( item, CellElement.WHILE_SCOPE )
                self.__allocateCell( vacantRow, column )
                self.cells[ vacantRow ][ column ] = scopeCanvas
                if item.elsePart:
                    elseScopeCanvas = VirtualCanvas( self )
                    elseScopeCanvas.layout( item.elsePart, CellElement.ELSE_SCOPE )
                    self.__allocateCell( vacantRow, column + 1 )
                    self.cells[ vacantRow ][ column + 1 ] = elseScopeCanvas
                vacantRow += 1
                continue

            if item.kind == FOR_FRAGMENT:
                scopeCanvas = VirtualCanvas( self )
                scopeCanvas.layout( item, CellElement.FOR_SCOPE )
                self.__allocateCell( vacantRow, column )
                self.cells[ vacantRow ][ column ] = scopeCanvas
                if item.elsePart:
                    elseScopeCanvas = VirtualCanvas( self )
                    elseScopeCanvas.layout( item.elsePart, CellElement.ELSE_SCOPE )
                    self.__allocateCell( vacantRow, column + 1 )
                    self.cells[ vacantRow ][ column + 1 ] = elseScopeCanvas
                vacantRow += 1
                continue

            if item.kind == COMMENT_FRAGMENT:
                self.__allocateCell( vacantRow, column + 1 )
                self.cells[ vacantRow ][ column ] = ConnectorCell( [ (ConnectorCell.NORTH,
                                                                      ConnectorCell.SOUTH) ] )
                self.cells[ vacantRow ][ column + 1 ] = IndependentCommentCell( item )
                vacantRow += 1
                continue

            if item.kind == TRY_FRAGMENT:
                tryScopeCanvas = VirtualCanvas( self )
                tryScopeCanvas.layout( item, CellElement.TRY_SCOPE )
                self.__allocateCell( vacantRow, column )
                self.cells[ vacantRow ][ column ] = tryScopeCanvas
                nextColumn = column + 1
                for exceptPart in item.exceptParts:
                    exceptScopeCanvas = VirtualCanvas( self )
                    exceptScopeCanvas.layout( exceptPart, CellElement.EXCEPT_SCOPE )
                    self.__allocateCell( vacantRow, nextColumn )
                    self.cells[ vacantRow ][ nextColumn ] = exceptScopeCanvas
                    nextColumn += 1
                if item.elsePart:
                    elseScopeCanvas = VirtualCanvas( self )
                    elseScopeCanvas.layout( item.elsePart, CellElement.ELSE_SCOPE )
                    self.__allocateCell( vacantRow, nextColumn )
                    self.cells[ vacantRow ][ nextColumn ] = elseScopeCanvas
                    nextColumn += 1
                if item.finallyPart:
                    finallyScopeCanvas = VirtualCanvas( self )
                    finallyScopeCanvas.layout( item.finallyPart, CellElement.FINALLY_SCOPE )
                    self.__allocateCell( vacantRow, nextColumn )
                    self.cells[ vacantRow ][ nextColumn ] = finallyScopeCanvas
                vacantRow += 1
                continue

            if item.kind == IF_FRAGMENT:
                pass


            # Below the single cell fragments possibly with comments
            cellClass = _fragmentKindToCellClass[ item.kind ]
            if item.leadingComment:
                self.__allocateCell( vacantRow, column + 1 )
                self.cells[ vacantRow ][ column ] = ConnectorCell( [ (ConnectorCell.NORTH,
                                                                      ConnectorCell.SOUTH) ] )
                self.cells[ vacantRow ][ column + 1 ] = LeadingCommentCell( item )
                vacantRow += 1

            self.__allocateCell( vacantRow, column )
            self.cells[ vacantRow ][ column ] = cellClass( item )

            if item.sideComment:
                self.__allocateCell( vacantRow, column + 1 )
                self.cells[ vacantRow ][ column + 1 ] = SideCommentCell( item )
            vacantRow += 1

            # end of for loop


        return vacantRow

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

        # Handle the content of the scope
        if scopeKind == CellElement.DECOR_SCOPE:
            # no suite, only one cell needs to be reserved
            self.__allocateCell( vacantRow, 1 )
            vacantRow += 1
        else:
            # walk the suite
            # no changes in the scope kind or control flow object
            vacantRow = self.layoutSuite( vacantRow, cf.suite )


        # Allocate the scope footer
        self.__allocateCell( vacantRow, 1, False )
        self.cells[ vacantRow ][ 0 ] = self.__currentScopeClass( cf, ScopeCellElement.BOTTOM_LEFT )
        self.cells[ vacantRow ][ 1 ] = self.__currentScopeClass( cf, ScopeCellElement.BOTTOM )
        return

