# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""
Virtual canvas to represent a control flow.

The basic idea is to split the canvas into cells and each cell could
be whether a vacant or filled with a certain graphics element.

At the very beginning the canvas is empty and can grow left, right or down
when a new element needs to be inserted.

The whole canvas is split into independent sections. The growing in one section
does not affect all the other sections.
"""

from ui.qt import Qt, QPen, QColor
from cdmcfparser import (CODEBLOCK_FRAGMENT, FUNCTION_FRAGMENT, CLASS_FRAGMENT,
                         BREAK_FRAGMENT, CONTINUE_FRAGMENT, RETURN_FRAGMENT,
                         RAISE_FRAGMENT, ASSERT_FRAGMENT, SYSEXIT_FRAGMENT,
                         IMPORT_FRAGMENT, COMMENT_FRAGMENT,
                         WHILE_FRAGMENT, FOR_FRAGMENT, IF_FRAGMENT,
                         WITH_FRAGMENT, TRY_FRAGMENT, CML_COMMENT_FRAGMENT)
from .cml import CMLVersion, CMLsw
from .items import (CellElement, VacantCell, CodeBlockCell,
                    BreakCell, ContinueCell, ReturnCell, RaiseCell,
                    AssertCell, SysexitCell, ImportCell, AboveCommentCell,
                    LeadingCommentCell, SideCommentCell, ConnectorCell, IfCell,
                    VSpacerCell, IndependentCommentCell)
from .scopeitems import (ScopeCellElement, FileScopeCell, FunctionScopeCell,
                         ClassScopeCell, ForScopeCell, WhileScopeCell,
                         TryScopeCell, WithScopeCell, DecoratorScopeCell,
                         ElseScopeCell, ExceptScopeCell, FinallyScopeCell)


CONN_N_S = [(ConnectorCell.NORTH, ConnectorCell.SOUTH)]
CONN_W_E = [(ConnectorCell.WEST, ConnectorCell.EAST)]
CONN_E_W = [(ConnectorCell.EAST, ConnectorCell.WEST)]
CONN_N_W = [(ConnectorCell.NORTH, ConnectorCell.WEST)]
CONN_W_S = [(ConnectorCell.WEST, ConnectorCell.SOUTH)]
CONN_E_S = [(ConnectorCell.EAST, ConnectorCell.SOUTH)]

_scopeToClass = {
    CellElement.NO_SCOPE: None,
    CellElement.FILE_SCOPE: FileScopeCell,
    CellElement.FUNC_SCOPE: FunctionScopeCell,
    CellElement.CLASS_SCOPE: ClassScopeCell,
    CellElement.FOR_SCOPE: ForScopeCell,
    CellElement.WHILE_SCOPE: WhileScopeCell,
    CellElement.TRY_SCOPE: TryScopeCell,
    CellElement.WITH_SCOPE: WithScopeCell,
    CellElement.DECOR_SCOPE: DecoratorScopeCell,
    CellElement.ELSE_SCOPE: ElseScopeCell,
    CellElement.EXCEPT_SCOPE: ExceptScopeCell,
    CellElement.FINALLY_SCOPE: FinallyScopeCell}

_fragmentKindToCellClass = {
    CODEBLOCK_FRAGMENT: CodeBlockCell,
    BREAK_FRAGMENT: BreakCell,
    CONTINUE_FRAGMENT: ContinueCell,
    RETURN_FRAGMENT: ReturnCell,
    RAISE_FRAGMENT: RaiseCell,
    ASSERT_FRAGMENT: AssertCell,
    SYSEXIT_FRAGMENT: SysexitCell,
    IMPORT_FRAGMENT: ImportCell}

_scopeToName = {
    CellElement.FILE_SCOPE: "",
    CellElement.FOR_SCOPE: "for",
    CellElement.WHILE_SCOPE: "while",
    CellElement.TRY_SCOPE: "try",
    CellElement.WITH_SCOPE: "with",
    CellElement.EXCEPT_SCOPE: "except",
    CellElement.FINALLY_SCOPE: "finally"}


_terminalCellTypes = (
    CellElement.BREAK,
    CellElement.CONTINUE,
    CellElement.RETURN,
    CellElement.RAISE,
    CellElement.SYSEXIT)


class VirtualCanvas:

    """Holds the control flow representation"""

    def __init__(self, settings, x, y, parent):
        self.kind = CellElement.VCANVAS

        # the item instances from items.py or other virtual canvases
        self.cells = []

        # Reference to the upper level canvas or None for the most upper canvas
        self.canvas = parent

        self.settings = settings
        self.addr = [x, y]

        # Layout support
        self.__currentCF = None
        self.__currentScopeClass = None
        self.isNoScope = False

        # Rendering support
        self.width = 0
        self.height = 0
        self.minWidth = 0
        self.minHeight = 0
        self.linesInHeader = 0

        # inclusive regions of rows with columns which affect each other width
        self.dependentRegions = []

        self.tailComment = False

        # Painting support
        self.baseX = 0
        self.baseY = 0
        self.scopeRectangle = None

    def getScopeName(self):
        """Provides the name of the scope drawn on the canvas"""
        for _, row in enumerate(self.cells):
            for _, cell in enumerate(row):
                if cell.kind in _scopeToName:
                    return _scopeToName[cell.kind]
                if cell.kind == CellElement.FUNC_SCOPE:
                    return 'def ' + cell.ref.name.getContent() + '()'
                if cell.kind == CellElement.CLASS_SCOPE:
                    return 'class ' + cell.ref.name.getContent()
                if cell.kind == CellElement.DECOR_SCOPE:
                    return '@' + cell.ref.name.getContent()
                if cell.kind == CellElement.ELSE_SCOPE:
                    parentCanvas = cell.canvas.canvas
                    row = cell.canvas.addr[1]
                    column = cell.canvas.addr[0] - 1
                    cellToTheLeft = parentCanvas.cells[row][column]
                    if cellToTheLeft.kind == CellElement.VCANVAS:
                        scopeToTheLeftName = cellToTheLeft.getScopeName()
                        if scopeToTheLeftName in ['for', 'while']:
                            return scopeToTheLeftName + '-else'
                    return 'try-else'
        return None

    def __str__(self):
        """Rather debug support"""
        val = 'Rows: ' + str(len(self.cells))
        count = 0
        for row in self.cells:
            val += '\nRow ' + str(count) + ': [ '
            for item in row:
                val += str(item) + ', '
            val += ']'
            count += 1
        return val

    def __isTerminalCell(self, row, column):
        """Tells if a cell is terminal.

        i.e. no need to continue the control flow line.
        """
        try:
            cell = self.cells[row][column]
            if cell.kind == CellElement.VCANVAS:
                return cell.cells[-1][0].kind in _terminalCellTypes
            return cell.kind in _terminalCellTypes
        except:
            return False

    def __isVacantCell(self, row, column):
        """Tells if a cell is a vacant one"""
        try:
            return self.cells[row][column].kind == CellElement.VACANT
        except:
            return True

    def __allocateCell(self, row, column, needScopeEdge=True):
        """Allocates a cell as Vacant if it is not available yet.

        Can only allocate bottom and right growing cells.
        """
        lastIndex = len(self.cells) - 1
        while lastIndex < row:
            self.cells.append([])
            lastIndex += 1
            if needScopeEdge:
                if self.__currentScopeClass:
                    self.cells[lastIndex].append(
                        self.__currentScopeClass(self.__currentCF, self,
                                                 0, lastIndex,
                                                 ScopeCellElement.LEFT))
        lastIndex = len(self.cells[row]) - 1
        while lastIndex < column:
            self.cells[row].append(VacantCell(None, self, lastIndex, row))
            lastIndex += 1

    def __allocateAndSet(self, row, column, what):
        """Allocates a cell and sets it to the given value"""
        self.__allocateCell(row, column)
        self.cells[row][column] = what

    def __allocateScope(self, item, scopeType, row, column):
        """Allocates a scope for a suite"""
        canvas = VirtualCanvas(self.settings, column, row, self)
        canvas.layout(item, scopeType)
        self.__allocateAndSet(row, column, canvas)

    def __allocateLeadingComment(self, item, row, column):
        """Allocates a leading comment if so"""
        if item.leadingComment:
            self.__allocateCell(row, column + 1)
            self.cells[row][column] = ConnectorCell(CONN_N_S, self,
                                                    column, row)
            self.cells[row][column + 1] = LeadingCommentCell(item, self,
                                                             column + 1, row)
            return row + 1
        return row

    @staticmethod
    def __needLoopCommentRow(item):
        """Tells if a row for comments need to be reserved"""
        if item.leadingComment:
            return True
        if item.elsePart:
            if item.elsePart.leadingComment:
                return True
        return False

    @staticmethod
    def __needTryCommentRow(item):
        """Tells if a row for comments need to be reserved"""
        if item.leadingComment:
            return True
        for exceptPart in item.exceptParts:
            if exceptPart.leadingComment:
                return True
        return False

    def layoutSuite(self, vacantRow, suite,
                    scopeKind=None, cflow=None, column=1):
        """Does a single suite layout"""
        if scopeKind:
            self.__currentCF = cflow
            self.__currentScopeClass = _scopeToClass[scopeKind]

        for item in suite:
            if item.kind == CML_COMMENT_FRAGMENT:
                # CML comments are not shown on the diagram
                continue

            if item.kind in [FUNCTION_FRAGMENT, CLASS_FRAGMENT]:
                scopeCanvas = VirtualCanvas(self.settings, None, None, self)
                scopeItem = item
                if item.kind == FUNCTION_FRAGMENT:
                    scopeCanvas.layout(item, CellElement.FUNC_SCOPE)
                else:
                    scopeCanvas.layout(item, CellElement.CLASS_SCOPE)

                if item.decorators:
                    for dec in reversed(item.decorators):
                        # Create a decorator scope virtual canvas
                        decScope = VirtualCanvas(self.settings,
                                                 None, None, self)
                        decScopeRows = len(decScope.cells)
                        if scopeItem.leadingComment:
                            # Need two rows; one for the comment
                            #                + one for the scope
                            decScope.layout(dec, CellElement.DECOR_SCOPE, 2)
                            decScope.__allocateCell(decScopeRows - 3, 2)
                            decScope.cells[decScopeRows - 3][1] = \
                                ConnectorCell(CONN_N_S,
                                              decScope, 1, decScopeRows - 3)
                            decScope.cells[decScopeRows - 3][2] = \
                                LeadingCommentCell(scopeItem, decScope, 2,
                                                   decScopeRows - 3)
                        else:
                            # Need one row for the scope
                            decScope.layout(dec, CellElement.DECOR_SCOPE, 1)

                        decScope.__allocateCell(decScopeRows - 2, 1)

                        # Fix the parent
                        scopeCanvas.parent = decScope
                        scopeCanvas.canvas = decScope
                        # Set the decorator content
                        decScope.cells[decScopeRows - 2][1] = scopeCanvas
                        scopeCanvas.addr = [1, decScopeRows - 2]
                        # Set the current content scope
                        scopeCanvas = decScope
                        scopeItem = dec

                if scopeItem.leadingComment:
                    self.__allocateCell(vacantRow, column + 1)
                    self.cells[vacantRow][column] = \
                        ConnectorCell(CONN_N_S, self, column, vacantRow)
                    self.cells[vacantRow][column + 1] = \
                        LeadingCommentCell(scopeItem, self, column + 1,
                                           vacantRow)
                    vacantRow += 1

                # Update the scope canvas parent and address
                scopeCanvas.parent = self
                scopeCanvas.addr = [column, vacantRow]
                self.__allocateAndSet(vacantRow, column, scopeCanvas)
                vacantRow += 1
                continue

            if item.kind == WITH_FRAGMENT:
                if item.leadingComment:
                    self.__allocateCell(vacantRow, column + 1)
                    self.cells[vacantRow][column] = \
                        ConnectorCell(CONN_N_S, self, column, vacantRow)
                    self.cells[vacantRow][column + 1] = \
                        LeadingCommentCell(item, self, column + 1, vacantRow)
                    vacantRow += 1

                self.__allocateScope(item, CellElement.WITH_SCOPE,
                                     vacantRow, column)
                vacantRow += 1
                continue

            if item.kind in [WHILE_FRAGMENT, FOR_FRAGMENT]:
                targetScope = CellElement.WHILE_SCOPE
                if item.kind == FOR_FRAGMENT:
                    targetScope = CellElement.FOR_SCOPE

                loopRegionBegin = vacantRow
                if self.__needLoopCommentRow(item):
                    if item.leadingComment:
                        comment = AboveCommentCell(item, self, column,
                                                   vacantRow)
                        comment.needConnector = True
                        self.__allocateAndSet(vacantRow, column, comment)
                    else:
                        self.__allocateCell(vacantRow, column)
                        self.cells[vacantRow][column] = \
                            ConnectorCell(CONN_N_S, self, column, vacantRow)
                    if item.elsePart:
                        if item.elsePart.leadingComment:
                            self.__allocateAndSet(
                                vacantRow, column + 1,
                                AboveCommentCell(item.elsePart, self,
                                                 column + 1, vacantRow))
                        self.dependentRegions.append((loopRegionBegin,
                                                      vacantRow + 1))
                    vacantRow += 1

                self.__allocateScope(item, targetScope, vacantRow, column)
                if item.elsePart:
                    self.__allocateScope(item.elsePart, CellElement.ELSE_SCOPE,
                                         vacantRow, column + 1)
                vacantRow += 1
                continue

            if item.kind == COMMENT_FRAGMENT:
                self.__allocateCell(vacantRow, column + 1)
                self.cells[vacantRow][column] = \
                    ConnectorCell(CONN_N_S, self, column, vacantRow)
                self.cells[vacantRow][column + 1] = \
                    IndependentCommentCell(item, self, column + 1, vacantRow)
                vacantRow += 1
                continue

            if item.kind == TRY_FRAGMENT:
                tryRegionBegin = vacantRow
                if self.__needTryCommentRow(item):
                    commentRow = vacantRow
                    vacantRow += 1
                    if item.leadingComment:
                        comment = AboveCommentCell(item, self, column,
                                                   commentRow)
                        comment.needConnector = True
                        self.__allocateAndSet(commentRow, column, comment)
                    else:
                        self.__allocateAndSet(commentRow, column,
                                              ConnectorCell(CONN_N_S, self,
                                                            column,
                                                            commentRow))
                    if item.exceptParts:
                        self.dependentRegions.append((tryRegionBegin,
                                                      vacantRow))

                self.__allocateScope(item, CellElement.TRY_SCOPE,
                                     vacantRow, column)
                nextColumn = column + 1
                for exceptPart in item.exceptParts:
                    if exceptPart.leadingComment:
                        self.__allocateAndSet(
                            commentRow, nextColumn,
                            AboveCommentCell(exceptPart, self,
                                             nextColumn, commentRow))
                    self.__allocateScope(exceptPart, CellElement.EXCEPT_SCOPE,
                                         vacantRow, nextColumn)
                    nextColumn += 1
                # The else part goes below
                if item.elsePart:
                    vacantRow += 1
                    vacantRow = self.__allocateLeadingComment(item.elsePart,
                                                              vacantRow,
                                                              column)
                    self.__allocateScope(item.elsePart, CellElement.ELSE_SCOPE,
                                         vacantRow, column)
                # The finally part is located below
                if item.finallyPart:
                    vacantRow += 1
                    vacantRow = self.__allocateLeadingComment(
                        item.finallyPart, vacantRow, column)
                    self.__allocateScope(
                        item.finallyPart, CellElement.FINALLY_SCOPE,
                        vacantRow, column)
                vacantRow += 1
                continue

            if item.kind == IF_FRAGMENT:
                lastNonElseIndex = len(item.parts) - 1
                for index in range(len(item.parts)):
                    if item.parts[index].condition is None:
                        lastNonElseIndex = index - 1
                        break

                canvas = VirtualCanvas(self.settings, 0, 0, self)
                canvas.isNoScope = True

                if lastNonElseIndex == len(item.parts) - 1:
                    # There is no else
                    canvas.layoutIfBranch(item.parts[lastNonElseIndex], None)
                else:
                    canvas.layoutIfBranch(item.parts[lastNonElseIndex],
                                          item.parts[lastNonElseIndex + 1])

                index = lastNonElseIndex - 1
                while index >= 0:
                    tempCanvas = VirtualCanvas(self.settings, 0, 0, self)
                    tempCanvas.isNoScope = True
                    tempCanvas.layoutIfBranch(item.parts[index], canvas)
                    canvas = tempCanvas
                    index -= 1

                self.__allocateAndSet(vacantRow, 1, canvas)
                vacantRow += 1
                continue

            # Below are the single cell fragments possibly with comments
            cellClass = _fragmentKindToCellClass[item.kind]
            vacantRow = self.__allocateLeadingComment(item, vacantRow, column)
            self.__allocateAndSet(vacantRow, column,
                                  cellClass(item, self, column, vacantRow))

            if item.sideComment:
                self.__allocateAndSet(vacantRow, column + 1,
                                      SideCommentCell(item, self, column + 1,
                                                      vacantRow))
            vacantRow += 1

            # end of for loop

        return vacantRow

    def layoutIfBranch(self, yBranch, nBranch):
        """Used in 'if' statements processing"""
        # It is always called when a layout is empty
        vacantRow = self.__allocateLeadingComment(yBranch, 0, 0)
        self.__allocateAndSet(vacantRow, 0,
                              IfCell(yBranch, self, 0, vacantRow))

        self.__allocateAndSet(vacantRow, 1,
                              ConnectorCell(CONN_W_S, self, 1, vacantRow))

        if yBranch.sideComment:
            self.__allocateAndSet(vacantRow, 2,
                                  SideCommentCell(yBranch, self, 2, vacantRow))
        vacantRow += 1

        # Test if there is a switch of the branches
        yBelow = CMLVersion.find(yBranch.leadingCMLComments, CMLsw) is not None

        # Allocate the YES branch
        if yBelow:
            branchLayout = VirtualCanvas(self.settings, 0, vacantRow, self)
        else:
            branchLayout = VirtualCanvas(self.settings, 1, vacantRow, self)
        branchLayout.isNoScope = True
        branchLayout.layoutSuite(0, yBranch.suite,
                                 CellElement.NO_SCOPE, None, 0)

        if yBelow:
            self.__allocateAndSet(vacantRow, 0, branchLayout)
        else:
            self.__allocateAndSet(vacantRow, 1, branchLayout)

        # nBranch could be: None: for absent of else
        #                   ifPart: present else
        #                   vcanvas: other elif
        if nBranch is None:
            if yBelow:
                self.__allocateAndSet(vacantRow, 1,
                                      ConnectorCell(CONN_N_S,
                                                    self, 1, vacantRow))
                vacantRow += 1
                self.__allocateAndSet(vacantRow, 1,
                                      ConnectorCell(CONN_N_W,
                                                    self, 1, vacantRow))
                if self.__isTerminalCell(vacantRow - 1, 0) or \
                   self.__isVacantCell(vacantRow - 1, 0):
                    self.__allocateAndSet(vacantRow, 0,
                                          ConnectorCell(CONN_E_S,
                                                        self, 0, vacantRow))
                else:
                    self.__allocateAndSet(
                        vacantRow, 0,
                        ConnectorCell([(ConnectorCell.NORTH,
                                        ConnectorCell.SOUTH),
                                       (ConnectorCell.EAST,
                                        ConnectorCell.CENTER)],
                                      self, 0, vacantRow))
            else:
                self.__allocateAndSet(vacantRow, 0,
                                      ConnectorCell(CONN_N_S,
                                                    self, 0, vacantRow))
                if not self.__isTerminalCell(vacantRow, 1) and \
                   not self.__isVacantCell(vacantRow, 1):
                    vacantRow += 1
                    self.__allocateAndSet(vacantRow, 1,
                                          ConnectorCell(CONN_N_W,
                                                        self, 1, vacantRow))
                    self.__allocateAndSet(
                        vacantRow, 0,
                        ConnectorCell([(ConnectorCell.NORTH,
                                        ConnectorCell.SOUTH),
                                       (ConnectorCell.EAST,
                                        ConnectorCell.CENTER)],
                                      self, 0, vacantRow))
        else:
            if nBranch.kind == CellElement.VCANVAS:
                if yBelow:
                    self.__allocateAndSet(vacantRow, 1, nBranch)
                else:
                    self.__allocateAndSet(vacantRow, 0, nBranch)
            else:
                # This is 'else' suite
                scopeCommentRows = 0
                if nBranch.leadingComment:
                    scopeCommentRows += 1
                if nBranch.sideComment:
                    scopeCommentRows += 1

                if yBelow:
                    branchLayout = VirtualCanvas(self.settings,
                                                 1, vacantRow, self)
                else:
                    branchLayout = VirtualCanvas(self.settings,
                                                 0, vacantRow, self)

                if nBranch.leadingComment:
                    # Draw as an independent comment: insert into the layout
                    conn = ConnectorCell(CONN_N_S, branchLayout, 0, 0)
                    cItem = IndependentCommentCell(nBranch.leadingComment,
                                                   branchLayout, 1, 0)
                    branchLayout.cells.append([])
                    branchLayout.cells[0].append(conn)
                    branchLayout.cells[0].append(cItem)

                if nBranch.sideComment:
                    # Draw as an independent comment: insert into the layout
                    rowIndex = scopeCommentRows - 1
                    conn = ConnectorCell(CONN_N_S, branchLayout, 0, rowIndex)
                    cItem = IndependentCommentCell(nBranch.sideComment,
                                                   branchLayout, 1, rowIndex)
                    cItem.sideForElse = True
                    branchLayout.cells.append([])
                    branchLayout.cells[rowIndex].append(conn)
                    branchLayout.cells[rowIndex].append(cItem)

                branchLayout.isNoScope = True
                branchLayout.layoutSuite(scopeCommentRows, nBranch.suite,
                                         CellElement.NO_SCOPE, None, 0)

                if yBelow:
                    self.__allocateAndSet(vacantRow, 1, branchLayout)
                else:
                    self.__allocateAndSet(vacantRow, 0, branchLayout)

            # Finilizing connectors
            leftTerminal = self.__isTerminalCell(vacantRow, 0) or \
                           self.__isVacantCell(vacantRow, 0)
            rightTerminal = self.__isTerminalCell(vacantRow, 1) or \
                            self.__isVacantCell(vacantRow, 1)

            if leftTerminal and rightTerminal:
                pass    # No need to do anything
            elif leftTerminal:
                vacantRow += 1
                self.__allocateAndSet(vacantRow, 1,
                                      ConnectorCell(CONN_N_W,
                                                    self, 1, vacantRow))
                self.__allocateAndSet(vacantRow, 0,
                                      ConnectorCell(CONN_E_S,
                                                    self, 0, vacantRow))
            elif rightTerminal:
                pass    # No need to do anything
            else:
                # Both are non terminal
                vacantRow += 1
                self.__allocateAndSet(vacantRow, 1,
                                      ConnectorCell(CONN_N_W,
                                                    self, 1, vacantRow))
                self.__allocateAndSet(
                    vacantRow, 0,
                    ConnectorCell([(ConnectorCell.NORTH,
                                    ConnectorCell.SOUTH),
                                   (ConnectorCell.EAST,
                                    ConnectorCell.CENTER)],
                                  self, 0, vacantRow))

        self.dependentRegions.append((0, vacantRow))

    def layoutModule(self, cflow):
        """Lays out a module"""
        if cflow.leadingComment:
            self.isNoScope = True

            vacantRow = 0
            self.__allocateAndSet(vacantRow, 1,
                                  VSpacerCell(None, self, 1, vacantRow))
            vacantRow += 1
            self.__allocateCell(vacantRow, 2, False)
            self.cells[vacantRow][1] = ConnectorCell(CONN_N_S,
                                                     self, 1, vacantRow)
            self.cells[vacantRow][2] = LeadingCommentCell(cflow,
                                                          self, 2, vacantRow)
            vacantRow += 1
            self.__allocateScope(cflow, CellElement.FILE_SCOPE, vacantRow, 0)
        else:
            self.layout(cflow, CellElement.FILE_SCOPE)

    def layout(self, cflow, scopeKind, rowsToAllocate=1):
        """Does the layout"""
        self.__currentCF = cflow
        self.__currentScopeClass = _scopeToClass[scopeKind]

        vacantRow = 0

        # Allocate the scope header
        self.__allocateCell(vacantRow, 0, False)
        self.cells[vacantRow][0] = self.__currentScopeClass(
            cflow, self, 0, vacantRow, ScopeCellElement.TOP_LEFT)
        self.linesInHeader += 1
        vacantRow += 1
        self.__allocateCell(vacantRow, 1)
        self.cells[vacantRow][1] = self.__currentScopeClass(
            cflow, self, 1, vacantRow, ScopeCellElement.DECLARATION)
        self.linesInHeader += 1

        if hasattr(cflow, "sideComment"):
            if cflow.sideComment:
                self.__allocateCell(vacantRow - 1, 2)
                self.cells[vacantRow - 1][2] = self.__currentScopeClass(
                    cflow, self, 2, vacantRow - 1, ScopeCellElement.TOP)
                self.__allocateCell(vacantRow, 2)
                self.cells[vacantRow][2] = self.__currentScopeClass(
                    cflow, self, 2, vacantRow, ScopeCellElement.SIDE_COMMENT)

        vacantRow += 1
        if hasattr(cflow, "docstring"):
            if cflow.docstring:
                if cflow.docstring.getDisplayValue():
                    self.__allocateCell(vacantRow, 1)
                    self.cells[vacantRow][1] = self.__currentScopeClass(
                        cflow, self, 1, vacantRow, ScopeCellElement.DOCSTRING)
                    vacantRow += 1
                    self.linesInHeader += 1

        # Spaces after the header to avoid glueing the flow chart to the header
        self.__allocateAndSet(vacantRow, 1,
                              VSpacerCell(None, self, 1, vacantRow))
        vacantRow += 1

        # Handle the content of the scope
        if scopeKind == CellElement.DECOR_SCOPE:
            # no suite, just reserve the required rows
            while rowsToAllocate > 0:
                self.__allocateCell(vacantRow, 0)
                vacantRow += 1
                rowsToAllocate -= 1
        else:
            # walk the suite
            # no changes in the scope kind or control flow object
            vacantRow = self.layoutSuite(vacantRow, cflow.suite)

        # Allocate the scope footer
        self.__allocateCell(vacantRow, 0, False)
        self.cells[vacantRow][0] = self.__currentScopeClass(
            cflow, self, 0, vacantRow, ScopeCellElement.BOTTOM_LEFT)

    def __dependentRegion(self, rowIndex):
        """True if it is a dependent region"""
        if self.dependentRegions:
            return self.dependentRegions[0][0] == rowIndex
        return False

    def __getRangeMaxColumns(self, start, end):
        """Provides the max columns"""
        maxColumns = 0
        while start <= end:
            maxColumns = max(maxColumns, len(self.cells[start]))
            start += 1
        return maxColumns

    def __renderRegion(self):
        """Renders a region where the rows affect each other"""
        start, end = self.dependentRegions.pop(0)
        maxColumns = self.__getRangeMaxColumns(start, end)

        # Detect the region tail comment cells
        index = start
        while index <= end:
            row = self.cells[index]
            if row:
                if row[-1].kind in [CellElement.LEADING_COMMENT,
                                    CellElement.INDEPENDENT_COMMENT,
                                    CellElement.SIDE_COMMENT]:
                    row[-1].tailComment = True
            index += 1

        for column in range(maxColumns):
            maxColumnWidth = 0
            index = start
            while index <= end:
                row = self.cells[index]
                if column < len(row):
                    row[column].render()
                    if row[column].kind in [CellElement.INDEPENDENT_COMMENT,
                                            CellElement.SIDE_COMMENT,
                                            CellElement.LEADING_COMMENT]:
                        row[column].adjustWidth()
                    if not row[column].tailComment:
                        maxColumnWidth = max(row[column].width, maxColumnWidth)
                index += 1

            index = start
            while index <= end:
                row = self.cells[index]
                if column < len(row):
                    if not row[column].tailComment:
                        row[column].width = maxColumnWidth
                index += 1

        # Update the row height and calculate the row width
        index = start
        while index <= end:
            maxHeight = 0
            row = self.cells[index]
            rowWidth = 0
            for cell in row:
                maxHeight = max(cell.height, maxHeight)
                rowWidth += cell.width
            self.width = max(self.width, rowWidth)
            for cell in row:
                cell.height = maxHeight
                if cell.kind == CellElement.VCANVAS:
                    if not cell.hasScope():
                        cell.adjustLastCellHeight(maxHeight)
            self.height += maxHeight
            index += 1

        return end

    def hasScope(self):
        """True if it has a scope"""
        try:
            return self.cells[0][0].scopedItem()
        except:
            return False

    def render(self):
        """Preforms rendering for all the cells"""
        self.width = 0
        self.height = 0

        maxRowIndex = len(self.cells) - 1
        index = 0
        while index <= maxRowIndex:
            if self.__dependentRegion(index):
                index = self.__renderRegion()
            else:
                row = self.cells[index]
                maxHeight = 0
                for cell in row:
                    _, height = cell.render()
                    maxHeight = max(maxHeight, height)
                    if cell.kind in [CellElement.INDEPENDENT_COMMENT,
                                     CellElement.SIDE_COMMENT,
                                     CellElement.LEADING_COMMENT]:
                        cell.adjustWidth()
                totalWidth = 0
                for cell in row:
                    cell.height = maxHeight
                    totalWidth += cell.width
                    if cell.kind == CellElement.VCANVAS:
                        if not cell.hasScope():
                            cell.adjustLastCellHeight(maxHeight)
                self.height += maxHeight
                self.width = max(self.width, totalWidth)
            index += 1

        if self.hasScope():
            # Right hand side vertical part
            self.width += self.settings.rectRadius + self.settings.hCellPadding
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def adjustLastCellHeight(self, maxHeight):
        """Adjusts the cell height if needed.

        The last cell in the first column of the non-scope virtual canvas
        may need to be adjusted to occupy the whole row hight in the upper
        level canvas. This happens mostly in 'if' statements.
        """
        allButLastHeight = 0
        for index in range(len(self.cells) - 1):
            allButLastHeight += self.cells[index][0].height

        # Update the height for all the cells in the last row
        for cell in self.cells[-1]:
            if allButLastHeight + cell.height < maxHeight:
                cell.height = maxHeight - allButLastHeight
                if cell.kind == CellElement.VCANVAS:
                    if not cell.hasScope():
                        cell.adjustLastCellHeight(cell.height)

    def setEditor(self, editor):
        """Provides the editor counterpart"""
        for row in self.cells:
            if row:
                for cell in row:
                    cell.setEditor(editor)

    def draw(self, scene, baseX, baseY):
        """Draws the diagram on the real canvas"""
        self.baseX = baseX
        self.baseY = baseY
        currentY = baseY
        for row in self.cells:
            if not row:
                continue
            height = row[0].height
            currentX = baseX
            for cell in row:
                if self.settings.debug:
                    pen = QPen(Qt.DotLine)
                    pen.setWidth(1)
                    if cell.kind == CellElement.VCANVAS:
                        pen.setColor(QColor(255, 0, 0, 255))
                        scene.addLine(currentX + 1, currentY + 1,
                                      currentX + cell.width - 2, currentY + 1,
                                      pen)
                        scene.addLine(currentX + 1, currentY + 1,
                                      currentX + 1, currentY + cell.height - 2,
                                      pen)
                        scene.addLine(currentX + 1, currentY + cell.height - 2,
                                      currentX + cell.width - 2,
                                      currentY + cell.height - 2, pen)
                        scene.addLine(currentX + cell.width - 2, currentY + 1,
                                      currentX + cell.width - 2,
                                      currentY + cell.height - 2, pen)
                    else:
                        pen.setColor(QColor(0, 255, 0, 255))
                        scene.addLine(currentX, currentY,
                                      currentX + cell.width, currentY, pen)
                        scene.addLine(currentX, currentY,
                                      currentX, currentY + cell.height, pen)
                        scene.addLine(currentX, currentY + cell.height,
                                      currentX + cell.width,
                                      currentY + cell.height, pen)
                        scene.addLine(currentX + cell.width, currentY,
                                      currentX + cell.width,
                                      currentY + cell.height, pen)
                cell.draw(scene, currentX, currentY)
                currentX += cell.width
            currentY += height
