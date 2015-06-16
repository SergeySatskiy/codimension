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
                    LeadingCommentCell, SideCommentCell, ConnectorCell, IfCell )
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

        # Rendering support
        self.width = None
        self.height = None
        self.minWidth = None
        self.minHeight = None
        return

    def clear( self ):
        " Resets the layout "
        self.cells = []
        self.parent = None
        self.__currentCF = None
        self.__currentScopeClass = None
        self.width = None
        self.height = None
        self.minWidth = None
        self.minHeight = None
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

    def __allocateAndSet( self, row, column, what ):
        " Allocates a cell and sets it to the given value "
        self.__allocateCell( row, column )
        self.cells[ row ][ column ] = what
        return

    def __allocateScope( self, suite, scopeType, row, column ):
        " Allocates a scope for a suite "
        canvas = VirtualCanvas( self )
        canvas.layout( suite, scopeType )
        self.__allocateAndSet( row, column, canvas )
        return

    def __allocateLeadingComment( self, item, row, column ):
        " Allocates a leading comment if so "
        if item.leadingComment:
            self.__allocateCell( row, column + 1 )
            self.cells[ row ][ column ] = ConnectorCell( [ (ConnectorCell.NORTH,
                                                            ConnectorCell.SOUTH) ] )
            self.cells[ row ][ column + 1 ] = LeadingCommentCell( item )
            return row + 1
        return row

    def layoutSuite( self, vacantRow, suite,
                     scopeKind = None, cf = None, column = 1 ):
        " Does a single suite layout "
        if scopeKind:
            self.__currentCF = cf
            self.__currentScopeClass = _scopeToClass[ scopeKind ]

        for item in suite:
            if item.kind in [ FUNCTION_FRAGMENT, CLASS_FRAGMENT ]:
                scopeCanvas = VirtualCanvas( self )
                if item.kind == FUNCTION_FRAGMENT:
                    scopeCanvas.layout( item, CellElement.FUNC_SCOPE )
                else:
                    scopeCanvas.layout( item, CellElement.CLASS_SCOPE )

                if item.decorators:
                    for dec in reversed( item.decorators ):
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

                self.__allocateAndSet( vacantRow, column, scopeCanvas )
                vacantRow += 1
                continue

            if item.kind == WITH_FRAGMENT:
                self.__allocateScope( item, CellElement.WITH_SCOPE,
                                      vacantRow, column )
                vacantRow += 1
                continue

            if item.kind == WHILE_FRAGMENT:
                self.__allocateScope( item, CellElement.WHILE_SCOPE,
                                      vacantRow, column )
                if item.elsePart:
                    self.__allocateScope( item.elsePart, CellElement.ELSE_SCOPE,
                                          vacantRow, column + 1 )
                vacantRow += 1
                continue

            if item.kind == FOR_FRAGMENT:
                self.__allocateScope( item, CellElement.FOR_SCOPE,
                                      vacantRow, column )
                if item.elsePart:
                    self.__allocateScope( item.elsePart, CellElement.ELSE_SCOPE,
                                          vacantRow, column + 1 )
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
                self.__allocateScope( item, CellElement.TRY_SCOPE,
                                      vacantRow, column )
                nextColumn = column + 1
                for exceptPart in item.exceptParts:
                    self.__allocateScope( exceptPart, CellElement.EXCEPT_SCOPE,
                                          vacantRow, nextColumn )
                    nextColumn += 1
                if item.elsePart:
                    self.__allocateScope( item.elsePart, CellElement.ELSE_SCOPE,
                                          vacantRow, nextColumn )
                    nextColumn += 1
                if item.finallyPart:
                    self.__allocateScope( item.finallyPart, CellElement.FINALLY_SCOPE,
                                          vacantRow, nextColumn )
                vacantRow += 1
                continue

            if item.kind == IF_FRAGMENT:
                vacantRow = self.__allocateLeadingComment( item, vacantRow, column )
                self.__allocateAndSet( vacantRow, column, IfCell( item ) )

                # Memorize the No-branch endpoint
                openEnd = [vacantRow, column + 1]
                vacantRow += 1

                # Allocate Yes-branch
                branchLayout = VirtualCanvas( self )
                branchLayout.layoutSuite( 0, item.suite, CellElement.NO_SCOPE, None, 0 )

                # Copy the layout cells into the current layout calculating the
                # max width of the layout
                branchWidth, branchHeight = self.__copyLayout( branchLayout, vacantRow, column )

                # Calculate the number of horizontal connectors left->right
                count = branchWidth - 1
                while count > 0:
                    self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ],
                                           ConnectorCell( [ (ConnectorCell.WEST,
                                                             ConnectorCell.EAST) ] ) )
                    openEnd[ 1 ] += 1
                    count -= 1

                self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ],
                                       ConnectorCell( [ (ConnectorCell.WEST,
                                                         ConnectorCell.SOUTH) ] ) )
                openEnd[ 0 ] += 1

                branchEndStack = []
                branchEndStack.append( (vacantRow + branchHeight, column) )

                # Handle the elif and else branches
                for elifBranch in item.elifParts:
                    if elifBranch.condition:
                        # This is the elif ...
                        openEnd[ 0 ] = self.__allocateLeadingComment( elifBranch, openEnd[ 0 ], openEnd[ 1 ] )
                        self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ], IfCell( elifBranch ) )

                        # Memorize the new open end
                        newOpenEnd = [openEnd[ 0 ], openEnd[ 1 ] + 1]
                        openEnd[ 0 ] += 1

                        # Allocate Yes-branch
                        branchLayout = VirtualCanvas( self )
                        branchLayout.layoutSuite( 0, elifBranch.suite, CellElement.NO_SCOPE, None, 0 )

                        # Copy the layout cells into the current layout
                        # calculating the max width of the layout
                        branchWidth, branchHeight = self.__copyLayout( branchLayout, openEnd[ 0 ], openEnd[ 1 ] )

                        # Calculate the number of horizontal connectors left->right
                        count = branchWidth - 1
                        while count > 0:
                            self.__allocateAndSet( newOpenEnd[ 0 ], newOpenEnd[ 1 ],
                                                   ConnectorCell( [ (ConnectorCell.WEST,
                                                                     ConnectorCell.EAST) ] ) )
                            newOpenEnd[ 1 ] += 1
                            count -= 1

                        self.__allocateAndSet( newOpenEnd[ 0 ], newOpenEnd[ 1 ],
                                               ConnectorCell( [ (ConnectorCell.WEST,
                                                                 ConnectorCell.SOUTH) ] ) )
                        newOpenEnd[ 0 ] += 1

                        branchEndStack.append( (openEnd[ 0 ] + branchHeight, openEnd[ 1 ]) )
                        openEnd = newOpenEnd
                    else:
                        # This is the else which is always the last
                        branchLayout = VirtualCanvas( self )
                        branchLayout.layoutSuite( 0, elifBranch.suite, CellElement.NO_SCOPE, None, 0 )
                        branchWidth, branchHeight = self.__copyLayout( branchLayout, openEnd[ 0 ], openEnd[ 1 ] )

                        # replace the open end
                        openEnd[ 0 ] += branchHeight


                # Make the connections between the open ends and the branch ends
                while branchEndStack:
                    targetRow, targetColumn = branchEndStack.pop( -1 )

                    # make the branches adjusted
                    while targetRow > openEnd[ 0 ]:
                        self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ],
                                               ConnectorCell( [ (ConnectorCell.NORTH,
                                                                 ConnectorCell.SOUTH) ] ) )
                        openEnd[ 0 ] += 1
                    while openEnd[ 0 ] > targetRow:
                        self.__allocateAndSet( targetRow, targetColumn,
                                               ConnectorCell( [ (ConnectorCell.NORTH,
                                                                 ConnectorCell.SOUTH) ] ) )
                        targetRow += 1

                    # make the horizontal connection
                    self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ],
                                           ConnectorCell( [ (ConnectorCell.NORTH,
                                                             ConnectorCell.WEST) ] ) )
                    openEnd[ 1 ] -= 1
                    while openEnd[ 1 ] > targetColumn:
                        self.cells[ openEnd[ 0 ] ][ openEnd[ 1 ] ] = ConnectorCell( [ (ConnectorCell.EAST,
                                                                                       ConnectorCell.WEST) ] )
                        openEnd[ 1 ] -= 1
                    self.cells[ targetRow ][ targetColumn ] = ConnectorCell( [ (ConnectorCell.NORTH,
                                                                                ConnectorCell.SOUTH),
                                                                               (ConnectorCell.EAST,
                                                                                ConnectorCell.CENTER) ] )

                    # adjust the new open end
                    openEnd = [ targetRow + 1, targetColumn ]

                vacantRow = openEnd[ 0 ]
                continue


            # Below are the single cell fragments possibly with comments
            cellClass = _fragmentKindToCellClass[ item.kind ]
            vacantRow = self.__allocateLeadingComment( item, vacantRow, column )
            self.__allocateAndSet( vacantRow, column, cellClass( item ) )

            if item.sideComment:
                self.__allocateAndSet( vacantRow, column + 1, SideCommentCell( item ) )
            vacantRow += 1

            # end of for loop

        return vacantRow

    def __copyLayout( self, fromCanvas, row, column ):
        " Copies all the cells from another layout starting from the row, column "
        width = 0
        height = 0
        for line in fromCanvas.cells:
            lineWidth = len( line )
            if lineWidth > width:
                width = lineWidth
            self.__allocateCell( row + height, column + lineWidth - 1 )
            for index, item in enumerate( line ):
                self.cells[ row + height ][ column + index ] = fromCanvas.cells[ height ][ index ]
            height += 1

        return width, height


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

    def render( self, settings ):
        " Preforms rendering for all the cells "
        self.width = 0
        self.height = 0

        maxColumns = 0
        for row in self.cells:
            maxHeight = 0
            for cell in row:
                _, height = cell.render( settings )
                if height > maxHeight:
                    maxHeight = height
            columns = 0
            for cell in row:
                cell.height = maxHeight
                columns += 1
            if columns > maxColumns:
                maxColumns = columns
            self.height += maxHeight

        for column in xrange( maxColumns ):
            maxWidth = 0
            for row in self.cells:
                if column < len( row ):
                    if row[ column ].width > maxWidth:
                        maxWidth = row[ column ].width
            for row in self.cells:
                if column < len( row ):
                    row[ column ].width = maxWidth
            self.width += maxWidth

        self.minWidth = self.minWidth
        self.minHeight = self.height
        return (self.width, self.height)

    def draw( self, scene, settings, baseX = 0, baseY = 0 ):
        " Draws the diagram on the real canvas "
        currentY = baseY
        for row in self.cells:
            height = row[ 0 ].height
            currentX = baseX
            for cell in row:
                if settings.debug:
                    scene.addLine( currentX, currentY, currentX + cell.width, currentY )
                    scene.addLine( currentX, currentY, currentX, currentY + cell.height )
                    scene.addLine( currentX, currentY + cell.height, currentX + cell.width, currentY + cell.height )
                    scene.addLine( currentX + cell.width, currentY, currentX + cell.width, currentY + cell.height )
                cell.draw( scene, settings, currentX, currentY )
                currentX += cell.width
            currentY += height
        return

