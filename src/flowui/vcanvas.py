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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QPen, QColor
from items import ( kindToString,
                    CellElement, VacantCell, CodeBlockCell, ScopeCellElement,
                    FileScopeCell, FunctionScopeCell, ClassScopeCell,
                    ForScopeCell, WhileScopeCell, TryScopeCell,
                    WithScopeCell, DecoratorScopeCell, ElseScopeCell,
                    ExceptScopeCell, FinallyScopeCell,
                    BreakCell, ContinueCell, ReturnCell, RaiseCell,
                    AssertCell, SysexitCell, ImportCell, IndependentCommentCell,
                    LeadingCommentCell, SideCommentCell, ConnectorCell, IfCell,
                    VSpacerCell, HSpacerCell )
from cdmcf import ( CODEBLOCK_FRAGMENT, FUNCTION_FRAGMENT, CLASS_FRAGMENT,
                    BREAK_FRAGMENT, CONTINUE_FRAGMENT, RETURN_FRAGMENT,
                    RAISE_FRAGMENT, ASSERT_FRAGMENT, SYSEXIT_FRAGMENT,
                    IMPORT_FRAGMENT, COMMENT_FRAGMENT,
                    WHILE_FRAGMENT, FOR_FRAGMENT, IF_FRAGMENT,
                    WITH_FRAGMENT, TRY_FRAGMENT )


CONN_N_S = [ (ConnectorCell.NORTH, ConnectorCell.SOUTH) ]
CONN_W_E = [ (ConnectorCell.WEST, ConnectorCell.EAST) ]
CONN_E_W = [ (ConnectorCell.EAST, ConnectorCell.WEST) ]
CONN_N_W = [ (ConnectorCell.NORTH, ConnectorCell.WEST) ]
CONN_W_S = [ (ConnectorCell.WEST, ConnectorCell.SOUTH) ]
CONN_E_S = [ (ConnectorCell.EAST, ConnectorCell.SOUTH) ]

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

    def __init__( self, settings, x, y, parent ):
        self.kind = CellElement.VCANVAS
        self.cells = []         # Stores the item instances
                                # from items.py or other virtual canvases
        self.canvas = parent    # Reference to the upper level canvas or
                                # None for the most upper canvas
        self.settings = settings
        self.addr = [ x, y ]

        # Layout support
        self.__currentCF = None
        self.__currentScopeClass = None

        # Rendering support
        self.width = 0
        self.height = 0
        self.minWidth = 0
        self.minHeight = 0
        self.linesInHeader = 0

        # Painting support
        self.baseX = 0
        self.baseY = 0
        self.scopeRectangle = None
        return

    def getScopeName( self ):
        " Provides the name of the scope drawn on the canvas "
        for rowNumber, row in enumerate( self.cells ):
            for columnNumber, cell in enumerate( row ):
                if cell.kind == CellElement.FILE_SCOPE:
                    return ""
                if cell.kind == CellElement.FOR_SCOPE:
                    return "<b>for</b>"
                if cell.kind == CellElement.WHILE_SCOPE:
                    return "<b>while</b>"
                if cell.kind == CellElement.TRY_SCOPE:
                    return "<b>try</b>"
                if cell.kind == CellElement.WITH_SCOPE:
                    return "<b>with</b>"
                if cell.kind == CellElement.EXCEPT_SCOPE:
                    return "<b>except</b>"
                if cell.kind == CellElement.FINALLY_SCOPE:
                    return "<b>finally</b>"
                if cell.kind == CellElement.FUNC_SCOPE:
                    return "<b>def</b>&nbsp;<i>" + cell.ref.name.getContent() + "</i>()"
                if cell.kind == CellElement.CLASS_SCOPE:
                    return "<b>class</b>&nbsp;" + cell.ref.name.getContent()
                if cell.kind == CellElement.DECOR_SCOPE:
                    return "@" + cell.ref.name.getContent()
                if cell.kind == CellElement.ELSE_SCOPE:
                    parentCanvas = cell.canvas.canvas
                    canvasToTheLeft = parentCanvas.cells[ cell.canvas.addr[ 1 ] ][ cell.canvas.addr[ 0 ] - 1 ]
                    scopeToTheLeftName = canvasToTheLeft.getScopeName()
                    if scopeToTheLeftName in [ "for", "while" ]:
                        return "<b>" + scopeToTheLeftName + "</b>-<b>else</b>"
                    if scopeToTheLeftName in [ "try", "except" ]:
                        return "<b>try</b>-<b>else</b>"
                    return "<b>else</b>"
        return None

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

    def __isTerminalCell( self, row, column ):
        """ Tells if a cell is terminal,
            i.e. no need to continue the control flow line """
        try:
            return self.cells[ row ][ column ].kind in [
                                                CellElement.BREAK,
                                                CellElement.CONTINUE,
                                                CellElement.RETURN,
                                                CellElement.RAISE,
                                                CellElement.SYSEXIT ]
        except:
            return False

    def __isVacantCell( self, row, column ):
        " Tells if a cell is a vacant one "
        try:
            return self.cells[ row ][ column ].kind == CellElement.VACANT
        except:
            return True

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
                        self.__currentScopeClass( self.__currentCF, self,
                                                  0, lastIndex,
                                                  ScopeCellElement.LEFT ) )
        lastIndex = len( self.cells[ row ] ) - 1
        while lastIndex < column:
            self.cells[ row ].append( VacantCell( None, self, lastIndex, row ) )
            lastIndex += 1
        return

    def __allocateAndSet( self, row, column, what ):
        " Allocates a cell and sets it to the given value "
        self.__allocateCell( row, column )
        self.cells[ row ][ column ] = what
        return

    def __allocateScope( self, item, scopeType, row, column ):
        " Allocates a scope for a suite "
        canvas = VirtualCanvas( self.settings, column, row, self )
        canvas.layout( item, scopeType )
        self.__allocateAndSet( row, column, canvas )
        return

    def __allocateLeadingComment( self, item, row, column ):
        " Allocates a leading comment if so "
        if item.leadingComment:
            self.__allocateCell( row, column + 1 )
            self.cells[ row ][ column ] = ConnectorCell( CONN_N_S,
                                                         self, column, row )
            self.cells[ row ][ column + 1 ] = LeadingCommentCell( item, self, column + 1, row )
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
                scopeCanvas = VirtualCanvas( self.settings, None, None, self )
                scopeItem = item
                if item.kind == FUNCTION_FRAGMENT:
                    scopeCanvas.layout( item, CellElement.FUNC_SCOPE )
                else:
                    scopeCanvas.layout( item, CellElement.CLASS_SCOPE )

                if item.decorators:
                    for dec in reversed( item.decorators ):
                        # Create a decorator scope virtual canvas
                        decScope = VirtualCanvas( self.settings, None, None, self )
                        decScopeRows = len( decScope.cells )
                        if scopeItem.leadingComment:
                            # Need two rows; one for the comment + one for the scope
                            decScope.layout( dec, CellElement.DECOR_SCOPE, 2 )
                            decScope.__allocateCell( decScopeRows - 3, 2 )
                            decScope.cells[ decScopeRows - 3 ][ 2 ] = LeadingCommentCell( scopeItem, decScope, 2, decScopeRows - 3 )
                        else:
                            # Need one row for the scope
                            decScope.layout( dec, CellElement.DECOR_SCOPE, 1 )
                        decScope.__allocateCell( decScopeRows - 2, 1 )

                        # Fix the parent
                        scopeCanvas.parent = decScope
                        scopeCanvas.canvas = decScope
                        # Set the decorator content
                        decScope.cells[ decScopeRows - 2 ][ 1 ] = scopeCanvas
                        scopeCanvas.addr = [ 1, decScopeRows - 2 ]
                        # Set the current content scope
                        scopeCanvas = decScope
                        scopeItem = dec

                if scopeItem.leadingComment:
                    self.__allocateCell( vacantRow, column + 1 )
                    self.cells[ vacantRow ][ column + 1 ] = LeadingCommentCell( scopeItem, self, column + 1, vacantRow )
                    vacantRow += 1

                # Insert a spacer to avoid badge overlapping with a previous
                # scope or a comment
                self.__allocateAndSet( vacantRow, column, VSpacerCell( None, self, column, vacantRow ) )
                vacantRow += 1

                # Update the scope canvas parent and address
                scopeCanvas.parent = self
                scopeCanvas.addr = [ column, vacantRow ]
                self.__allocateAndSet( vacantRow, column, scopeCanvas )
                vacantRow += 1
                continue

            if item.kind == WITH_FRAGMENT:
                if item.leadingComment:
                    vacantRow = self.__allocateLeadingComment( item,
                                                               vacantRow,
                                                               column )
                self.__allocateScope( item, CellElement.WITH_SCOPE,
                                      vacantRow, column )
                vacantRow += 1
                continue

            if item.kind == WHILE_FRAGMENT:
                if item.leadingComment:
                    vacantRow = self.__allocateLeadingComment( item,
                                                               vacantRow,
                                                               column )
                else:
                    if item.elsePart:
                        if item.elsePart.leadingComment:
                            self.__allocateAndSet( vacantRow, column, ConnectorCell( CONN_N_S,
                                                                                     self, column, vacantRow ) )
                            vacantRow += 1
                self.__allocateScope( item, CellElement.WHILE_SCOPE,
                                      vacantRow, column )
                if item.elsePart:
                    if item.elsePart.leadingComment:
                        self.__allocateAndSet( vacantRow - 1, column + 2, LeadingCommentCell( item.elsePart, self, column + 2, vacantRow - 1 ) )
                    self.__allocateScope( item.elsePart, CellElement.ELSE_SCOPE,
                                          vacantRow, column + 1 )
                vacantRow += 1
                continue

            if item.kind == FOR_FRAGMENT:
                if item.leadingComment:
                    vacantRow = self.__allocateLeadingComment( item,
                                                               vacantRow,
                                                               column )
                else:
                    if item.elsePart:
                        if item.elsePart.leadingComment:
                            self.__allocateAndSet( vacantRow, column, ConnectorCell( CONN_N_S,
                                                                                     self, column, vacantRow ) )
                            vacantRow += 1
                self.__allocateScope( item, CellElement.FOR_SCOPE,
                                      vacantRow, column )
                if item.elsePart:
                    if item.elsePart.leadingComment:
                        self.__allocateAndSet( vacantRow - 1, column + 2, LeadingCommentCell( item.elsePart, self, column + 2, vacantRow - 1 ) )
                    self.__allocateScope( item.elsePart, CellElement.ELSE_SCOPE,
                                          vacantRow, column + 1 )
                vacantRow += 1
                continue

            if item.kind == COMMENT_FRAGMENT:
                self.__allocateCell( vacantRow, column + 1 )
                self.cells[ vacantRow ][ column ] = ConnectorCell( CONN_N_S,
                                                                   self, column, vacantRow )
                self.cells[ vacantRow ][ column + 1 ] = IndependentCommentCell( item,
                                                                                self, column + 1, vacantRow )
                vacantRow += 1
                continue

            if item.kind == TRY_FRAGMENT:
                def needCommentRow( item ):
                    " Tells if a row for comments need to be reserved "
                    if item.leadingComment:
                        return True
                    for exceptPart in item.exceptParts:
                        if exceptPart.leadingComment:
                            return True
                    if item.elsePart:
                        if item.elsePart.leadingComment:
                            return True
                    return False

                if needCommentRow( item ):
                    commentRow = vacantRow
                    vacantRow += 1
                    if item.leadingComment:
                        self.__allocateAndSet( commentRow, column + 1,
                                               LeadingCommentCell( item, self, column + 1, commentRow ) )
                self.__allocateScope( item, CellElement.TRY_SCOPE,
                                      vacantRow, column )
                nextColumn = column + 1
                for exceptPart in item.exceptParts:
                    if exceptPart.leadingComment:
                        self.__allocateAndSet( commentRow, nextColumn + 1,
                                               LeadingCommentCell( exceptPart, self, nextColumn + 1, commentRow ) )
                    self.__allocateScope( exceptPart, CellElement.EXCEPT_SCOPE,
                                          vacantRow, nextColumn )
                    nextColumn += 1
                if item.elsePart:
                    if item.elsePart.leadingComment:
                        self.__allocateAndSet( commentRow, nextColumn + 1,
                                               LeadingCommentCell( item.elsePart, self, nextColumn + 1, commentRow ) )
                    self.__allocateScope( item.elsePart, CellElement.ELSE_SCOPE,
                                          vacantRow, nextColumn )
                    nextColumn += 1
                # The finally part is located below
                if item.finallyPart:
                    vacantRow += 1
                    vacantRow = self.__allocateLeadingComment( item.finallyPart, vacantRow, column )
                    self.__allocateScope( item.finallyPart, CellElement.FINALLY_SCOPE,
                                          vacantRow, column )
                vacantRow += 1
                continue

            if item.kind == IF_FRAGMENT:
                vacantRow = self.__allocateLeadingComment( item, vacantRow, column )
                self.__allocateAndSet( vacantRow, column, IfCell( item, self, column, vacantRow ) )

                # Memorize the No-branch endpoint
                openEnd = [vacantRow, column + 1]
                vacantRow += 1

                # Allocate Yes-branch
                branchLayout = VirtualCanvas( self.settings, None, None, None )
                branchLayout.layoutSuite( 0, item.suite, CellElement.NO_SCOPE, None, 0 )

                # Copy the layout cells into the current layout calculating the
                # max width of the layout
                branchWidth, branchHeight = self.__copyLayout( branchLayout, vacantRow, column )

                # Calculate the number of horizontal connectors left->right
                count = branchWidth - 1
                while count > 0:
                    self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ],
                                           ConnectorCell( [ (ConnectorCell.WEST,
                                                             ConnectorCell.EAST) ],
                                                          self, openEnd[ 1 ], openEnd[ 0 ] ) )
                    openEnd[ 1 ] += 1
                    count -= 1

                self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ],
                                       ConnectorCell( [ (ConnectorCell.WEST,
                                                         ConnectorCell.SOUTH) ],
                                                      self, openEnd[ 1 ], openEnd[ 0 ] ) )
                if item.sideComment:
                    self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ] + 1,
                                           SideCommentCell( item, self, openEnd[ 1 ] + 1, openEnd[ 0 ] ) )
                openEnd[ 0 ] += 1

                branchEndStack = []
                branchEndStack.append( (vacantRow + branchHeight, column) )

                # Handle the elif and else branches
                for elifBranch in item.elifParts:
                    if elifBranch.condition:
                        # This is the elif ...
                        openEnd[ 0 ] = self.__allocateLeadingComment( elifBranch, openEnd[ 0 ], openEnd[ 1 ] )
                        self.__allocateAndSet( openEnd[ 0 ], openEnd[ 1 ], IfCell( elifBranch, self, openEnd[ 1 ], openEnd[ 0 ] ) )

                        # Memorize the new open end
                        newOpenEnd = [openEnd[ 0 ], openEnd[ 1 ] + 1]
                        openEnd[ 0 ] += 1

                        # Allocate Yes-branch
                        branchLayout = VirtualCanvas( self.settings, None, None, None )
                        branchLayout.layoutSuite( 0, elifBranch.suite, CellElement.NO_SCOPE, None, 0 )

                        # Copy the layout cells into the current layout
                        # calculating the max width of the layout
                        branchWidth, branchHeight = self.__copyLayout( branchLayout, openEnd[ 0 ], openEnd[ 1 ] )

                        # Calculate the number of horizontal connectors left->right
                        count = branchWidth - 1
                        while count > 0:
                            self.__allocateAndSet( newOpenEnd[ 0 ], newOpenEnd[ 1 ],
                                                   ConnectorCell( CONN_W_E,
                                                                  self, newOpenEnd[ 1 ], newOpenEnd[ 0 ] ) )
                            newOpenEnd[ 1 ] += 1
                            count -= 1

                        self.__allocateAndSet( newOpenEnd[ 0 ], newOpenEnd[ 1 ],
                                               ConnectorCell( CONN_W_S,
                                                              self, newOpenEnd[ 1 ], newOpenEnd[ 0 ] ) )
                        if elifBranch.sideComment:
                            self.__allocateAndSet( newOpenEnd[ 0 ], newOpenEnd[ 1 ] + 1,
                                                   SideCommentCell( elifBranch, self, newOpenEnd[ 1 ] + 1, newOpenEnd[ 0 ] ) )
                        newOpenEnd[ 0 ] += 1

                        branchEndStack.append( (openEnd[ 0 ] + branchHeight, openEnd[ 1 ]) )
                        openEnd = newOpenEnd
                    else:
                        # This is the else which is always the last
                        if elifBranch.leadingComment:
                            # Draw it as an independent comment
                            self.__allocateCell( openEnd[ 0 ], openEnd[ 1 ] + 1 )
                            self.cells[ openEnd[ 0 ] ][ openEnd[ 1 ] ] = ConnectorCell( CONN_N_S,
                                                                                        self, openEnd[ 1 ],
                                                                                        openEnd[ 0 ] )
                            cItem = IndependentCommentCell( elifBranch.leadingComment,
                                                            self, openEnd[ 1 ] + 1, openEnd[ 0 ] )
                            cItem.leadingForElse = True
                            self.cells[ openEnd[ 0 ] ][ openEnd[ 1 ] + 1 ] = cItem
                            openEnd[ 0 ] += 1
                        if elifBranch.sideComment:
                            # Draw it as an independent comment
                            self.__allocateCell( openEnd[ 0 ], openEnd[ 1 ] + 1 )
                            self.cells[ openEnd[ 0 ] ][ openEnd[ 1 ] ] = ConnectorCell( CONN_N_S,
                                                                                        self, openEnd[ 1 ],
                                                                                        openEnd[ 0 ] )
                            cItem = IndependentCommentCell( elifBranch.sideComment,
                                                            self, openEnd[ 1 ] + 1, openEnd[ 0 ] )
                            cItem.sideForElse = True
                            self.cells[ openEnd[ 0 ] ][ openEnd[ 1 ] + 1 ] = cItem
                            openEnd[ 0 ] += 1

                        branchLayout = VirtualCanvas( self.settings, None, None, None )
                        branchLayout.layoutSuite( 0, elifBranch.suite, CellElement.NO_SCOPE, None, 0 )
                        branchWidth, branchHeight = self.__copyLayout( branchLayout, openEnd[ 0 ], openEnd[ 1 ] )

                        # replace the open end
                        openEnd[ 0 ] += branchHeight

                branchEndStack.append( openEnd )
                mainBranch = branchEndStack.pop( 0 )
                mainRow = mainBranch[ 0 ]
                mainCol = mainBranch[ 1 ]

                while branchEndStack:
                    srcRow, srcCol = branchEndStack.pop( 0 )

                    # Adjust the main branch
                    if self.__isTerminalCell( mainRow - 1, mainCol ) or \
                       self.__isVacantCell( mainRow - 1, mainCol ):
                        if mainRow < srcRow:
                            mainRow = srcRow
                    else:
                        while mainRow < srcRow:
                            self.__allocateAndSet( mainRow, mainCol,
                                                   ConnectorCell( CONN_N_S, self, mainCol, mainRow ) )
                            mainRow += 1

                    if self.__isTerminalCell( srcRow - 1, srcCol ):
                        # No need to make any connections from a terminated branch
                        continue

                    # Do the source branch adjustment
                    while srcRow < mainRow:
                        self.__allocateAndSet( srcRow, srcCol,
                                               ConnectorCell( CONN_N_S, self, srcCol, srcRow ) )
                        srcRow += 1

                    # Do the horizontal connection
                    self.__allocateAndSet( srcRow, srcCol,
                                           ConnectorCell( CONN_N_W,
                                                          self, srcCol, srcRow ) )
                    srcCol -= 1
                    while mainCol < srcCol:
                        self.__allocateAndSet( srcRow, srcCol,
                                               ConnectorCell( CONN_E_W, self, srcCol, srcRow ) )
                        srcCol -= 1

                    # Do the proper main branch connection
                    if self.__isTerminalCell( mainRow - 1, mainCol ) or \
                       self.__isVacantCell( mainRow - 1, mainCol ):
                        self.__allocateAndSet( mainRow, mainCol,
                                               ConnectorCell( CONN_E_S, self, mainCol, mainRow ) )
                    else:
                        self.__allocateAndSet( mainRow, mainCol,
                                               ConnectorCell( [ (ConnectorCell.NORTH,
                                                                 ConnectorCell.SOUTH),
                                                                (ConnectorCell.EAST,
                                                                 ConnectorCell.CENTER) ], self, mainCol, mainRow ) )
                    mainRow += 1

                vacantRow = mainRow + 1
                continue

            # Below are the single cell fragments possibly with comments
            cellClass = _fragmentKindToCellClass[ item.kind ]
            vacantRow = self.__allocateLeadingComment( item, vacantRow, column )
            self.__allocateAndSet( vacantRow, column,
                                   cellClass( item, self, column, vacantRow ) )

            if item.sideComment:
                self.__allocateAndSet( vacantRow, column + 1,
                                       SideCommentCell( item, self, column + 1, vacantRow ) )
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
                newRow = row + height
                newColumn = column + index
                self.cells[ newRow ][ newColumn ] = fromCanvas.cells[ height ][ index ]
                self.cells[ newRow ][ newColumn ].canvas = self
                self.cells[ newRow ][ newColumn ].addr = [ newColumn, newRow ]
            height += 1

        return width, height


    def layout( self, cf, scopeKind = CellElement.FILE_SCOPE,
                          rowsToAllocate = 1 ):
        " Does the layout "

        self.__currentCF = cf
        self.__currentScopeClass = _scopeToClass[ scopeKind ]

        # Allocate the scope header
        headerRow = 0
        self.__allocateCell( headerRow, 1, False )
        self.cells[ headerRow ][ 0 ] = self.__currentScopeClass( cf, self, 0, headerRow, ScopeCellElement.TOP_LEFT )
        self.cells[ headerRow ][ 1 ] = self.__currentScopeClass( cf, self, 1, headerRow, ScopeCellElement.TOP )
        self.linesInHeader += 1
        headerRow += 1
        self.__allocateCell( headerRow, 1 )
        self.cells[ headerRow ][ 1 ] = self.__currentScopeClass( cf, self, 1, headerRow, ScopeCellElement.DECLARATION )
        self.linesInHeader += 1

        if hasattr( cf, "sideComment" ):
            if cf.sideComment:
                self.__allocateCell( headerRow - 1, 2 )
                self.cells[ headerRow - 1 ][ 2 ] = self.__currentScopeClass( cf, self, 2, headerRow - 1, ScopeCellElement.TOP )
                self.__allocateCell( headerRow, 2 )
                self.cells[ headerRow ][ 2 ] = self.__currentScopeClass( cf, self, 2, headerRow, ScopeCellElement.SIDE_COMMENT )

        vacantRow = headerRow + 1
        if hasattr( cf, "docstring" ):
            if cf.docstring:
                if cf.docstring.getDisplayValue():
                    self.__allocateCell( vacantRow, 1 )
                    self.cells[ vacantRow ][ 1 ] = self.__currentScopeClass( cf, self, 1, vacantRow, ScopeCellElement.DOCSTRING )
                    vacantRow += 1
                    self.linesInHeader += 1

        # Spaces after the header to avoid glueing the flow chart to the header
        self.__allocateAndSet( vacantRow, 1, VSpacerCell( None, self, 1, vacantRow ) )
        vacantRow += 1

        if scopeKind in [ CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE ]:
            # insert one more spacer because there is the 'continue' badge
            self.__allocateAndSet( vacantRow, 1, VSpacerCell( None, self, 1, vacantRow ) )
            vacantRow += 1

        # Handle the content of the scope
        if scopeKind == CellElement.DECOR_SCOPE:
            # no suite, just reserve the required rows
            while rowsToAllocate > 0:
                self.__allocateCell( vacantRow, 0 )
                vacantRow += 1
                rowsToAllocate -= 1
        else:
            # walk the suite
            # no changes in the scope kind or control flow object
            vacantRow = self.layoutSuite( vacantRow, cf.suite )


        if scopeKind in [ CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE ]:
            # insert a spacer because there is the 'break' badge
            self.__allocateAndSet( vacantRow, 1, VSpacerCell( None, self, 1, vacantRow ) )
            vacantRow += 1

        # Allocate the scope footer
        self.__allocateCell( vacantRow, 1, False )
        self.cells[ vacantRow ][ 0 ] = self.__currentScopeClass( cf, self, 0, vacantRow, ScopeCellElement.BOTTOM_LEFT )
        self.cells[ vacantRow ][ 1 ] = self.__currentScopeClass( cf, self, 1, vacantRow, ScopeCellElement.BOTTOM )
        return

    def render( self ):
        " Preforms rendering for all the cells "
        self.width = 0
        self.height = 0

        # Loop through all the rows:
        # - calculate the max number of columns
        # - set the hight in the row as the max hight of all cells in the row
        # - detect tail comments cells
        maxColumns = 0
        for row in self.cells:
            maxHeight = 0
            for cell in row:
                _, height = cell.render()
                if height > maxHeight:
                    maxHeight = height
            columns = 0
            for cell in row:
                cell.height = maxHeight
                columns += 1
            if columns > maxColumns:
                maxColumns = columns
            self.height += maxHeight

            if row:
                if row[ -1 ].kind in [ CellElement.LEADING_COMMENT,
                                       CellElement.INDEPENDENT_COMMENT,
                                       CellElement.SIDE_COMMENT ]:
                    row[ -1 ].tailComment = True

        # Loop over all columns
        tailCommentColumns = []
        for column in xrange( maxColumns ):
            maxWidth = 0
            for index, row in enumerate( self.cells ):
                if column < len( row ):
                    if column != 0 and index < self.linesInHeader:
                        continue    # Skip the header
                    if row[ column ].kind != CellElement.VCANVAS:
                        if row[ column ].tailComment:
                            tailCommentColumns.append( index )  # Skip columns which have trailing comments
                            continue
                    if row[ column ].width > maxWidth:
                        maxWidth = row[ column ].width
            for index, row in enumerate( self.cells ):
                if column < len( row ):
                    if column != 0 and index < self.linesInHeader:
                        continue    # Skip the header
                    if row[ column ].kind != CellElement.VCANVAS:
                        if row[ column ].tailComment:
                            continue            # Skip the line trailing comments
                    row[ column ].width = maxWidth
            self.width += maxWidth

        # In fact self.width here is the width of the body, not the header
        # (without the trailing (right) border of the scope)
        for rowIndex in xrange( 1, self.linesInHeader ):
            headerWidth = 0
            for item in self.cells[ rowIndex ]:
                headerWidth += item.width
            if headerWidth > self.width:
                self.width = headerWidth

        # Scope width might need to be adjusted by the size of the lines with
        # the trailing comments
        for rowIndex in tailCommentColumns:
            lineWidth = 0
            for item in self.cells[ rowIndex ]:
                lineWidth += item.width
            if lineWidth > self.width:
                self.width = lineWidth

        self.width = self.width + self.settings.rectRadius + self.settings.hScopeSpacing
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        " Draws the diagram on the real canvas "
        self.baseX = baseX
        self.baseY = baseY
        currentY = baseY
        for row in self.cells:
            if not row:
                continue
            height = row[ 0 ].height
            currentX = baseX
            for cell in row:
                if self.settings.debug:
                    pen = QPen( Qt.DotLine )
                    pen.setColor( QColor( 0, 255, 0, 255 ) )
                    pen.setWidth( 1 )
                    scene.addLine( currentX, currentY, currentX + cell.width, currentY, pen )
                    scene.addLine( currentX, currentY, currentX, currentY + cell.height, pen )
                    scene.addLine( currentX, currentY + cell.height, currentX + cell.width, currentY + cell.height, pen )
                    scene.addLine( currentX + cell.width, currentY, currentX + cell.width, currentY + cell.height, pen )
                cell.draw( scene, currentX, currentY )
                currentX += cell.width
            currentY += height
        return

