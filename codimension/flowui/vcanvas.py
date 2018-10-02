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
from .cml import CMLVersion, CMLsw, CMLgb, CMLge
from .items import (CellElement, VacantCell, CodeBlockCell, BreakCell,
                    ContinueCell, ReturnCell, RaiseCell, AssertCell,
                    SysexitCell, ImportCell,  ConnectorCell, IfCell,
                    VSpacerCell, MinimizedExceptCell)
from .scopeitems import (ScopeCellElement, FileScopeCell, FunctionScopeCell,
                         ClassScopeCell, ForScopeCell, WhileScopeCell,
                         TryScopeCell, WithScopeCell, DecoratorScopeCell,
                         ElseScopeCell, ExceptScopeCell, FinallyScopeCell)
from .commentitems import (AboveCommentCell, LeadingCommentCell,
                           SideCommentCell, IndependentCommentCell)
from .groupitems import (EmptyGroup, OpenedGroupBegin, OpenedGroupEnd,
                         CollapsedGroup, HGroupSpacerCell)


CONN_N_S = [(ConnectorCell.NORTH, ConnectorCell.SOUTH)]
CONN_W_E = [(ConnectorCell.WEST, ConnectorCell.EAST)]
CONN_E_W = [(ConnectorCell.EAST, ConnectorCell.WEST)]
CONN_N_W = [(ConnectorCell.NORTH, ConnectorCell.WEST)]
CONN_W_S = [(ConnectorCell.WEST, ConnectorCell.SOUTH)]
CONN_E_S = [(ConnectorCell.EAST, ConnectorCell.SOUTH)]
CONN_N_C = [(ConnectorCell.NORTH, ConnectorCell.CENTER)]

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

    def __init__(self, settings, x, y, validGroups, collapsedGroups, parent):
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

        # Groups support
        self.__validGroups = validGroups
        self.__validGroupBeginLines = [item[1] for item in validGroups]
        self.__validGroupEndLines = [item[2] for item in validGroups]
        self.__validGroupLines = self.__validGroupBeginLines + \
                                 self.__validGroupEndLines
        self.__collapsedGroups = collapsedGroups
        self.__groupStack = []  # [item, row, column]
        self.maxLocalOpenGroupDepth = 0
        self.maxGlobalOpenGroupDepth = 0

        # Supports the second stage of open group layout. If True => this
        # nested layout needs to be considered on the upper levels with how
        # the spacing is inserted for the open groups
        self.isIfBelowLayout = False
        self.isOuterIfLayout = False

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
                    if cell.statement == ElseScopeCell.TRY_STATEMENT:
                        return 'try-else'
                    if cell.statement == ElseScopeCell.FOR_STATEMENT:
                        return 'for-else'
                    if cell.statement == ElseScopeCell.WHILE_STATEMENT:
                        return 'while-else'
                    # The 'statement' is set only for the TOP_LEFT item of the
                    # ELSE_SCOPE so it must be found here because we start from
                    # the top left corner
                    return '???'
        return None

    def __str__(self):
        """Rather debug support"""
        val = '\nRows: ' + str(len(self.cells))
        count = 0
        for row in self.cells:
            val += '\nRow ' + str(count) + ' (' + str(len(row)) + ' items): [ '
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
            # The previous row could be a group end...
            while self.cells[row][-1].kind in [CellElement.OPENED_GROUP_END,
                                               CellElement.OPENED_GROUP_BEGIN]:
                row -= 1

            cell = self.cells[row][column]
            if cell.kind == CellElement.COLLAPSED_GROUP:
                return self.__isCollapsedGroupTerminal(cell)

            if cell.kind == CellElement.VCANVAS:
                # If it is a scope then the last item in the scope should be
                # checked
                cells = cell.cells
                rowIndex = len(cells) - 1
                while cells[rowIndex][-1].kind in [CellElement.OPENED_GROUP_END,
                                                   CellElement.OPENED_GROUP_BEGIN]:
                    rowIndex -= 1
                cell = cell.cells[rowIndex][0]
            if cell.kind == CellElement.CONNECTOR:
                if cell.connections == CONN_N_C:
                    # On some smart zoom levels the primitives are replaced
                    # with connectors. The terminal cells are replaced with a
                    # half a connector from NORTH to CENTER
                    return True
            return cell.kind in _terminalCellTypes
        except:
            return False

    def __isCollapsedGroupTerminal(self, group):
        """Tells if the collapsed group has the last item terminal"""
        if group.nestedRefs[-1].CODE in [BREAK_FRAGMENT,
                                         CONTINUE_FRAGMENT,
                                         RETURN_FRAGMENT,
                                         RAISE_FRAGMENT,
                                         SYSEXIT_FRAGMENT]:
            return True

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
        canvas = VirtualCanvas(self.settings, column, row,
                               self.__validGroups, self.__collapsedGroups,
                               self)
        canvas.layout(item, scopeType)
        self.__allocateAndSet(row, column, canvas)

    def __allocateLeadingComment(self, item, row, column):
        """Allocates a leading comment if so"""
        if item.leadingComment and not self.settings.noComment:
            self.__allocateCell(row, column + 1)
            self.cells[row][column] = ConnectorCell(CONN_N_S, self,
                                                    column, row)
            self.cells[row][column + 1] = LeadingCommentCell(item, self,
                                                             column + 1, row)
            return row + 1
        return row

    def __needLoopCommentRow(self, item):
        """Tells if a row for comments need to be reserved"""
        if self.settings.noComment:
            return False
        if item.leadingComment:
            return True
        if item.elsePart:
            if item.elsePart.leadingComment:
                return True
        return False

    def __needTryCommentRow(self, item):
        """Tells if a row for comments need to be reserved"""
        if self.settings.noComment:
            return False
        if item.leadingComment:
            return True
        if not self.settings.hideexcepts:
            for exceptPart in item.exceptParts:
                if exceptPart.leadingComment:
                    return True
        return False

    def __checkLeadingCMLComments(self, leadingCMLComments):
        """Provides a list of group begins and ends as they are in the leading comments"""
        groups = []
        for comment in leadingCMLComments:
            if hasattr(comment, 'CODE'):
                if comment.CODE in [CMLgb.CODE, CMLge.CODE]:
                    itemFirstLine = comment.ref.parts[0].beginLine
                    if itemFirstLine in self.__validGroupLines:
                        groups.append(comment)
        return groups

    def __getGroups(self, item):
        """Provides a list of group begins and ends as they are in the item"""
        if type(item) == list:
            # this is a list of CML comments
            return self.__checkLeadingCMLComments(item)

        # Only valid groups are taken into account
        if item.kind == CML_COMMENT_FRAGMENT:
            if hasattr(item, 'ref'):
                # High level CML comment (low level are not interesting here)
                itemFirstLine = item.ref.parts[0].beginLine
                if itemFirstLine in self.__validGroupLines:
                    return [item]
            return []

        if item.kind == IF_FRAGMENT:
            return self.__checkLeadingCMLComments(
                item.parts[0].leadingCMLComments)

        # The item may have a leading CML comment which ends a valid group
        if not hasattr(item, 'leadingCMLComments'):
            return []
        return self.__checkLeadingCMLComments(item.leadingCMLComments)

    def __isGroupBegin(self, groupComment):
        """True if it is a valid group begin"""
        return groupComment.CODE == CMLgb.CODE

    def __onGroupBegin(self, item, groupComment, vacantRow, column):
        """Handles the group begin"""
        if self.__groupStack:
            if self.__groupStack[-1][0].kind == CellElement.COLLAPSED_GROUP:
                # We are still in a collapsed group
                return vacantRow

        groupId = groupComment.id
        if self.__isGroupCollapsed(groupId):
            newGroup = CollapsedGroup(item, self, column, vacantRow)
        else:
            newGroup = OpenedGroupBegin(item, self, column, vacantRow)
            newGroup.isTerminal = self.__isTerminalCell(vacantRow - 1, column)

        # allocate new cell, memo the group begin ref,
        # add the group to the stack and return a new vacant row
        self.__allocateAndSet(vacantRow, column, newGroup)
        newGroup.groupBeginCMLRef = groupComment
        self.__groupStack.append([newGroup, vacantRow, column])
        return vacantRow + 1

    def __onGroupEnd(self, item, groupComment, vacantRow, column):
        """Handles the group end"""
        # At least one group must be in the stack!
        currentGroup = self.__groupStack[-1][0]
        if currentGroup.getGroupId() != groupComment.id:
            # It is not a close of the current group
            return vacantRow

        groupBegin = self.__groupStack[-1][0]
        groupRow = self.__groupStack[-1][1]
        groupColumn = self.__groupStack[-1][2]

        # There are three cases here:
        # - end of a collapsed group
        # - end of an empty group
        # - end of an open group
        if not currentGroup.nestedRefs:
            # Empty group: replace the beginning of the group with an empty one
            emptyGroup = EmptyGroup(groupBegin.ref, self, groupColumn, groupRow)
            emptyGroup.groupBeginCMLRef = groupBegin.groupBeginCMLRef
            self.cells[groupRow][groupColumn] = emptyGroup
        elif currentGroup.kind == CellElement.COLLAPSED_GROUP:
            # Collapsed group: the end of the group is memorized in the common
            # block after ifs
            pass
        else:
            # Opened group: insert a group end
            groupEnd = OpenedGroupEnd(item, self, column, vacantRow)
            groupEnd.groupBeginCMLRef = groupBegin.groupBeginCMLRef
            groupEnd.groupEndCMLRef = groupComment
            groupEnd.groupBeginRow = groupRow
            groupEnd.groupBeginColumn = groupColumn

            groupEnd.isTerminal = self.__isTerminalCell(vacantRow - 1, column)
            self.__allocateAndSet(vacantRow, column, groupEnd)

            self.cells[groupRow][groupColumn].groupEndRow = vacantRow
            self.cells[groupRow][groupColumn].groupEndColumn = column

            vacantRow += 1

        self.cells[groupRow][groupColumn].groupEndCMLRef = groupComment

        self.__groupStack.pop()
        return vacantRow

    def __isGroupCollapsed(self, groupId):
        """True if the group is collapsed"""
        if self.__collapsedGroups:
            return groupId in self.__collapsedGroups
        return False

    def __handleGroups(self, item, vacantRow, column):
        """Picks all the valid group begins and ends

        Decides what to do and returns True if it is a collapsed group and
        the further items need to be skipped
        """
        for groupComment in self.__getGroups(item):
            # The group begin/end comments are going to the nested refs as
            # separate items regardless from where they came. This lets to
            # detect empty groups easier.
            if self.__groupStack:
                currentGroupId = self.__groupStack[-1][0].getGroupId()
                if currentGroupId != groupComment.id:
                    # The 'if' is to avoid the end of the group to be added
                    # to the nested refs
                    self.__groupStack[-1][0].nestedRefs.append(groupComment)

            if self.__isGroupBegin(groupComment):
                vacantRow = self.__onGroupBegin(item, groupComment,
                                                vacantRow, column)
            else:
                vacantRow = self.__onGroupEnd(item, groupComment,
                                              vacantRow, column)

        # type(item) != list protects from dealing with a list of CML comments
        if self.__groupStack and type(item) != list:
            # We are in some kind of a group
            needToAdd = True
            if item.kind == CML_COMMENT_FRAGMENT:
                if hasattr(item, 'ref'):
                    # That's a high level comment
                    if item.CODE in [CMLgb.CODE, CMLge.CODE]:
                        if item.id == self.__groupStack[-1][0].getGroupId():
                            needToAdd = False
            if needToAdd:
                self.__groupStack[-1][0].nestedRefs.append(item)
            if self.__groupStack[-1][0].kind == CellElement.COLLAPSED_GROUP:
                return True, vacantRow

        # We are not in a group now, so process the item
        return False, vacantRow

    def __checkOpenGroupBefore(self, vacantRow, column):
        """Checks if the previous row is an open group end"""
        if vacantRow > 0:
            for cell in self.cells[vacantRow - 1]:
                if cell.kind == CellElement.OPENED_GROUP_END:
                    # Need to insert a connector or a spacer
                    if cell.isTerminal:
                        spacerColumn = column
                    else:
                        spacerColumn = column + 1
                        conn = ConnectorCell(CONN_N_S, self, column, vacantRow)
                        self.__allocateAndSet(vacantRow, column, conn)
                    spacer = VSpacerCell(None, self, spacerColumn, vacantRow)
                    self.__allocateAndSet(vacantRow, spacerColumn, spacer)

                    vacantRow += 1
                    return vacantRow
        return vacantRow

    def layoutSuite(self, vacantRow, suite,
                    scopeKind=None, cflow=None, column=1,
                    leadingCMLComments=None):
        """Does a single suite layout"""
        if scopeKind:
            self.__currentCF = cflow
            self.__currentScopeClass = _scopeToClass[scopeKind]

        skipItem = False
        if not self.settings.noGroup:
            if leadingCMLComments:
                skipItem, vacantRow = self.__handleGroups(leadingCMLComments,
                                                          vacantRow, column)

        for item in suite:

            if not self.settings.noGroup:
                skipItem, vacantRow = self.__handleGroups(item,
                                                          vacantRow, column)
                if skipItem:
                    continue

            if item.kind == CML_COMMENT_FRAGMENT:
                # CML comments are not shown on the diagram
                continue

            if item.kind in [FUNCTION_FRAGMENT, CLASS_FRAGMENT]:
                scopeCanvas = VirtualCanvas(self.settings, None, None,
                                            self.__validGroups,
                                            self.__collapsedGroups, self)
                scopeItem = item
                if item.kind == FUNCTION_FRAGMENT:
                    scopeCanvas.layout(item, CellElement.FUNC_SCOPE)
                else:
                    scopeCanvas.layout(item, CellElement.CLASS_SCOPE)

                if item.decorators and not self.settings.noDecor:
                    for dec in reversed(item.decorators):
                        # Create a decorator scope virtual canvas
                        decScope = VirtualCanvas(self.settings,
                                                 None, None,
                                                 self.__validGroups,
                                                 self.__collapsedGroups, self)
                        decScopeRows = len(decScope.cells)
                        if scopeItem.leadingComment and not self.settings.noComment:
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

                if scopeItem.leadingComment and not self.settings.noComment:
                    self.__allocateCell(vacantRow, column + 1)
                    self.cells[vacantRow][column] = \
                        ConnectorCell(CONN_N_S, self, column, vacantRow)
                    self.cells[vacantRow][column + 1] = \
                        LeadingCommentCell(scopeItem, self, column + 1,
                                           vacantRow)
                    vacantRow += 1
                else:
                    vacantRow = self.__checkOpenGroupBefore(vacantRow, column)

                # Update the scope canvas parent and address
                scopeCanvas.parent = self
                scopeCanvas.addr = [column, vacantRow]
                self.__allocateAndSet(vacantRow, column, scopeCanvas)
                vacantRow += 1
                continue

            if item.kind == WITH_FRAGMENT:
                if self.settings.noWith:
                    continue

                if item.leadingComment and not self.settings.noComment:
                    self.__allocateCell(vacantRow, column + 1)
                    self.cells[vacantRow][column] = \
                        ConnectorCell(CONN_N_S, self, column, vacantRow)
                    self.cells[vacantRow][column + 1] = \
                        LeadingCommentCell(item, self, column + 1, vacantRow)
                    vacantRow += 1
                else:
                    vacantRow = self.__checkOpenGroupBefore(vacantRow, column)

                self.__allocateScope(item, CellElement.WITH_SCOPE,
                                     vacantRow, column)
                vacantRow += 1
                continue

            if item.kind in [WHILE_FRAGMENT, FOR_FRAGMENT]:
                targetScope = CellElement.WHILE_SCOPE
                if item.kind == FOR_FRAGMENT:
                    targetScope = CellElement.FOR_SCOPE

                if item.kind == FOR_FRAGMENT and self.settings.noFor:
                    continue
                if item.kind == WHILE_FRAGMENT and self.settings.noWhile:
                    continue

                loopRegionBegin = vacantRow
                if self.__needLoopCommentRow(item):
                    if item.leadingComment and not self.settings.noComment:
                        comment = AboveCommentCell(item, self, column,
                                                   vacantRow)
                        comment.needConnector = True
                        self.__allocateAndSet(vacantRow, column, comment)
                    else:
                        self.__allocateCell(vacantRow, column)
                        self.cells[vacantRow][column] = \
                            ConnectorCell(CONN_N_S, self, column, vacantRow)
                    if item.elsePart:
                        if item.elsePart.leadingComment and not self.settings.noComment:
                            self.__allocateAndSet(
                                vacantRow, column + 1,
                                AboveCommentCell(item.elsePart, self,
                                                 column + 1, vacantRow))
                        self.dependentRegions.append((loopRegionBegin,
                                                      vacantRow + 1))
                    vacantRow += 1
                else:
                    vacantRow = self.__checkOpenGroupBefore(vacantRow, column)


                self.__allocateScope(item, targetScope, vacantRow, column)
                if item.elsePart:
                    self.__allocateScope(item.elsePart, CellElement.ELSE_SCOPE,
                                         vacantRow, column + 1)
                    self.cells[vacantRow][column + 1].setLeaderRef(item)
                    if item.kind == FOR_FRAGMENT:
                        self.cells[vacantRow][column + 1].setElseStatement(ElseScopeCell.FOR_STATEMENT)
                    else:
                        self.cells[vacantRow][column + 1].setElseStatement(ElseScopeCell.WHILE_STATEMENT)
                vacantRow += 1
                continue

            if item.kind == COMMENT_FRAGMENT:
                if self.settings.noComment:
                    continue

                self.__allocateCell(vacantRow, column + 1)
                self.cells[vacantRow][column] = \
                    ConnectorCell(CONN_N_S, self, column, vacantRow)
                self.cells[vacantRow][column + 1] = \
                    IndependentCommentCell(item, self, column + 1,
                                           vacantRow)
                vacantRow += 1
                continue

            if item.kind == TRY_FRAGMENT:
                if self.settings.noTry:
                    continue

                tryRegionBegin = vacantRow
                if self.__needTryCommentRow(item):
                    commentRow = vacantRow
                    vacantRow += 1
                    if item.leadingComment and not self.settings.noComment:
                        comment = AboveCommentCell(item, self, column,
                                                   commentRow)
                        comment.needConnector = True
                        self.__allocateAndSet(commentRow, column, comment)
                    else:
                        self.__allocateAndSet(commentRow, column,
                                              ConnectorCell(CONN_N_S, self,
                                                            column,
                                                            commentRow))
                    if item.exceptParts and not self.settings.hideexcepts:
                        self.dependentRegions.append((tryRegionBegin,
                                                      vacantRow))

                self.__allocateScope(item, CellElement.TRY_SCOPE,
                                     vacantRow, column)
                if self.settings.hideexcepts:
                    if item.exceptParts:
                        miniExcept = MinimizedExceptCell(item, self,
                                                         column + 1, vacantRow)
                        self.__allocateAndSet(vacantRow, column + 1,
                                              miniExcept)
                else:
                    nextColumn = column + 1
                    for exceptPart in item.exceptParts:
                        if exceptPart.leadingComment and not self.settings.noComment:
                            self.__allocateAndSet(
                                commentRow, nextColumn,
                                AboveCommentCell(exceptPart, self,
                                                 nextColumn, commentRow))
                        self.__allocateScope(exceptPart,
                                             CellElement.EXCEPT_SCOPE,
                                             vacantRow, nextColumn)
                        self.cells[vacantRow][nextColumn].setLeaderRef(item)
                        nextColumn += 1
                # The else part goes below
                if item.elsePart:
                    vacantRow += 1
                    vacantRow = self.__allocateLeadingComment(item.elsePart,
                                                              vacantRow,
                                                              column)
                    self.__allocateScope(item.elsePart, CellElement.ELSE_SCOPE,
                                         vacantRow, column)
                    self.cells[vacantRow][column].setLeaderRef(item)
                    self.cells[vacantRow][column].setElseStatement(ElseScopeCell.TRY_STATEMENT)
                # The finally part is located below
                if item.finallyPart:
                    vacantRow += 1
                    vacantRow = self.__allocateLeadingComment(
                        item.finallyPart, vacantRow, column)
                    self.__allocateScope(
                        item.finallyPart, CellElement.FINALLY_SCOPE,
                        vacantRow, column)
                    self.cells[vacantRow][column].setLeaderRef(item)
                vacantRow += 1
                continue

            if item.kind == IF_FRAGMENT:
                if self.settings.noIf:
                    continue

                lastNonElseIndex = len(item.parts) - 1
                for index in range(len(item.parts)):
                    if item.parts[index].condition is None:
                        lastNonElseIndex = index - 1
                        break

                canvas = VirtualCanvas(self.settings, 0, 0,
                                       self.__validGroups,
                                       self.__collapsedGroups, self)
                canvas.isNoScope = True
                canvas.isIfBelowLayout = True
                canvas.isOuterIfLayout = True

                if lastNonElseIndex == len(item.parts) - 1:
                    # There is no else
                    canvas.layoutIfBranch(item.parts[lastNonElseIndex], None)
                else:
                    canvas.layoutIfBranch(item.parts[lastNonElseIndex],
                                          item.parts[lastNonElseIndex + 1])

                index = lastNonElseIndex - 1
                while index >= 0:
                    tempCanvas = VirtualCanvas(self.settings, 0, 0,
                                               self.__validGroups,
                                               self.__collapsedGroups, self)
                    tempCanvas.isNoScope = True
                    tempCanvas.layoutIfBranch(item.parts[index], canvas)
                    canvas = tempCanvas
                    index -= 1

                self.__allocateAndSet(vacantRow, 1, canvas)
                vacantRow += 1
                continue

            # Below are the single cell fragments possibly with comments
            if item.kind == CODEBLOCK_FRAGMENT and self.settings.noBlock:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_S, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == IMPORT_FRAGMENT and self.settings.noImport:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_S, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == BREAK_FRAGMENT and self.settings.noBreak:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_C, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == CONTINUE_FRAGMENT and self.settings.noContinue:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_C, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == RETURN_FRAGMENT and self.settings.noReturn:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_C, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == RAISE_FRAGMENT and self.settings.noRaise:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_C, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == ASSERT_FRAGMENT and self.settings.noAssert:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_S, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue
            if item.kind == SYSEXIT_FRAGMENT and self.settings.noSysExit:
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = ConnectorCell(CONN_N_C, self,
                                                              column, vacantRow)
                vacantRow += 1
                continue

            cellClass = _fragmentKindToCellClass[item.kind]
            vacantRow = self.__allocateLeadingComment(item, vacantRow, column)
            self.__allocateAndSet(vacantRow, column,
                                  cellClass(item, self, column, vacantRow))

            if item.sideComment and not self.settings.noComment:
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

        topConnector = ConnectorCell(CONN_W_S, self, 1, vacantRow)
        topConnector.subKind = ConnectorCell.TOP_IF
        self.__allocateAndSet(vacantRow, 1, topConnector)

        if yBranch.sideComment and not self.settings.noComment:
            self.__allocateAndSet(vacantRow, 2,
                                  SideCommentCell(yBranch, self, 2, vacantRow))
        vacantRow += 1

        # Test if there is a switch of the branches
        yBelow = CMLVersion.find(yBranch.leadingCMLComments, CMLsw) is not None

        # Allocate the YES branch
        if yBelow:
            branchLayout = VirtualCanvas(self.settings, 0, vacantRow,
                                         self.__validGroups,
                                         self.__collapsedGroups, self)
            branchLayout.isIfBelowLayout = True
        else:
            branchLayout = VirtualCanvas(self.settings, 1, vacantRow,
                                         self.__validGroups,
                                         self.__collapsedGroups, self)
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
                bottomConnector = ConnectorCell(CONN_N_W, self, 1, vacantRow)
                bottomConnector.subKind = ConnectorCell.BOTTOM_IF
                self.__allocateAndSet(vacantRow, 1, bottomConnector)
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
                    bottomConnector = ConnectorCell(CONN_N_W, self,
                                                    1, vacantRow)
                    bottomConnector.subKind = ConnectorCell.BOTTOM_IF
                    self.__allocateAndSet(vacantRow, 1, bottomConnector)
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
                if nBranch.leadingComment and not self.settings.noComment:
                    scopeCommentRows += 1
                if nBranch.sideComment and not self.settings.noComment:
                    scopeCommentRows += 1

                if yBelow:
                    branchLayout = VirtualCanvas(self.settings,
                                                 1, vacantRow,
                                                 self.__validGroups,
                                                 self.__collapsedGroups, self)
                else:
                    branchLayout = VirtualCanvas(self.settings,
                                                 0, vacantRow,
                                                 self.__validGroups,
                                                 self.__collapsedGroups, self)
                    branchLayout.isIfBelowLayout = True

                if nBranch.leadingComment and not self.settings.noComment:
                    # Draw as an independent comment: insert into the layout
                    conn = ConnectorCell(CONN_N_S, branchLayout, 0, 0)
                    cItem = IndependentCommentCell(nBranch.leadingComment,
                                                   branchLayout, 1, 0)
                    branchLayout.cells.append([])
                    branchLayout.cells[0].append(conn)
                    branchLayout.cells[0].append(cItem)

                if nBranch.sideComment and not self.settings.noComment:
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
                bottomConnector = ConnectorCell(CONN_N_W, self, 1, vacantRow)
                bottomConnector.subKind = ConnectorCell.BOTTOM_IF
                self.__allocateAndSet(vacantRow, 1, bottomConnector)
                self.__allocateAndSet(vacantRow, 0,
                                      ConnectorCell(CONN_E_S,
                                                    self, 0, vacantRow))
            elif rightTerminal:
                pass    # No need to do anything
            else:
                # Both are non terminal
                vacantRow += 1
                bottomConnector = ConnectorCell(CONN_N_W, self, 1, vacantRow)
                bottomConnector.subKind = ConnectorCell.BOTTOM_IF
                self.__allocateAndSet(vacantRow, 1, bottomConnector)
                self.__allocateAndSet(
                    vacantRow, 0,
                    ConnectorCell([(ConnectorCell.NORTH,
                                    ConnectorCell.SOUTH),
                                   (ConnectorCell.EAST,
                                    ConnectorCell.CENTER)],
                                  self, 0, vacantRow))

        self.dependentRegions.append((0, vacantRow))

    def setLeaderRef(self, ref):
        """Sets the leader ref for ELSE, EXCEPT and FINALLY scopes"""
        if self.cells[0][0].kind in [CellElement.ELSE_SCOPE,
                                     CellElement.EXCEPT_SCOPE,
                                     CellElement.FINALLY_SCOPE]:
            if self.cells[0][0].subKind == ScopeCellElement.TOP_LEFT:
                self.cells[0][0].leaderRef = ref
                return
        raise Exception("Logic error: cannot set the leader reference")

    def setElseStatement(self, statement):
        if self.cells[0][0].kind == CellElement.ELSE_SCOPE:
            if self.cells[0][0].subKind == ScopeCellElement.TOP_LEFT:
                self.cells[0][0].statement = statement
                return
        raise Exception("Logic error: cannot set the else statement")

    def layoutModule(self, cflow):
        """Lays out a module"""
        self.isNoScope = True
        vacantRow = 0

        # Avoid glueing to the top view edge
        self.__allocateAndSet(vacantRow, 1,
                              VSpacerCell(None, self, 1, vacantRow))
        vacantRow += 1

        if cflow.leadingComment and not self.settings.noComment:
            self.__allocateCell(vacantRow, 2, False)
            self.cells[vacantRow][1] = ConnectorCell(CONN_N_S,
                                                     self, 1, vacantRow)
            self.cells[vacantRow][2] = LeadingCommentCell(cflow,
                                                          self, 2, vacantRow)
            vacantRow += 1

        self.__allocateScope(cflow, CellElement.FILE_SCOPE, vacantRow, 0)

        # Second stage: shifts to accomadate open groups
        self.openGroupsAdjustments()

    def getInsertIndex(self, row):
        """Provides an insert index for a spacing and a row kind.

        index: 0, 1 or -1
               -1 => no need to insert
        row kind: 0, 1, 2, -1
                  0 => regular line
                  1 => group begin line
                  -1 => group end line
                  2 => nested virtual canvas which needs to be considered
        """
        for cellIndex, cell in enumerate(row):
            if cell.kind == CellElement.VCANVAS:
                if cell.isIfBelowLayout:
                    return cellIndex, 2
                continue
            if cell.scopedItem():
                if cell.subKind in [ScopeCellElement.TOP_LEFT,
                                    ScopeCellElement.DECLARATION,
                                    ScopeCellElement.DOCSTRING,
                                    ScopeCellElement.BOTTOM_LEFT]:
                    return -1, None
            if cell.kind == CellElement.OPENED_GROUP_BEGIN:
                return cellIndex, 1
            if cell.kind == CellElement.OPENED_GROUP_END:
                return cellIndex, -1

        # Regular row
        if self.isNoScope:
            return 0, 0
        return 1, 0

    def openGroupsAdjustments(self):
        """Adjusts the layout if needed for the open groups"""
        localOpenGroupsStackLevel = 0
        maxLocalDepth = 0
        stackMaxDepth = 0
        for row in self.cells:
            for cell in row:
                if cell.kind == CellElement.VCANVAS:
                    if cell.isIfBelowLayout:
                        # Nested needs to be considered
                        nestedStackMaxDepth = cell.openGroupsAdjustments()
                        stackMaxDepth = max(stackMaxDepth,
                                            localOpenGroupsStackLevel +
                                            nestedStackMaxDepth)
                    else:
                        # Do the shifting independent
                        cell.openGroupsAdjustments()
                elif cell.kind == CellElement.OPENED_GROUP_BEGIN:
                    localOpenGroupsStackLevel += 1
                    stackMaxDepth = max(stackMaxDepth,
                                        localOpenGroupsStackLevel)
                    maxLocalDepth = max(maxLocalDepth,
                                        localOpenGroupsStackLevel)
                elif cell.kind == CellElement.OPENED_GROUP_END:
                    localOpenGroupsStackLevel -= 1

        # Memorize the max local (not considering the nested canvaces) depth
        self.maxLocalOpenGroupDepth = maxLocalDepth

        if self.isIfBelowLayout:
            return stackMaxDepth

        self.insertOpenGroupShift(stackMaxDepth, 0)

    def insertOpenGroupShift(self, depth, insertedByUpper):
        """Inserts the horizontal open group spacers"""
        if depth <= 0:
            return

        self.maxGlobalOpenGroupDepth = depth

        # Insert the shift as required
        localOpenGroupsStackLevel = 0
        insertCountStack = []

        for rowIndex, row in enumerate(self.cells):
            insertIndex, rowKind = self.getInsertIndex(row)
            if insertIndex < 0:
                continue

            if rowKind == 1:
                # group begin row
                groupBeginCell = self.cells[rowIndex][insertIndex]
                groupBeginCell.selfAndDeeperNestLevel, groupBeginCell.selfMaxNestLevel = self.updateGroupNestLevel(
                    rowIndex + 1, row[insertIndex].groupEndRow - 1)
                groupBeginCell.selfAndDeeperNestLevel += 1
                groupBeginCell.selfMaxNestLevel += 1

                localOpenGroupsStackLevel += 1

                insertCount = depth - groupBeginCell.selfAndDeeperNestLevel - insertedByUpper
                insertCountStack.append(insertCount)
                if insertCount > 0:
                    spacer = HGroupSpacerCell(None, self, insertIndex, rowIndex)
                    spacer.count = insertCount
                    row.insert(insertIndex, spacer)

                    insertIndex += 1
                    self.__adjustRowAddresses(row, insertIndex)
            elif rowKind == -1:
                # group end row
                groupEndCell = self.cells[rowIndex][insertIndex]
                insertCount = insertCountStack.pop()

                if insertCount > 0:
                    spacer = HGroupSpacerCell(None, self, insertIndex, rowIndex)
                    spacer.count = insertCount
                    # The group begin column has been shifted 1 cell so the
                    # reference address needs to be adjusted.
                    groupEndCell.groupBeginColumn += 1
                    row.insert(insertIndex, spacer)

                    insertIndex += 1
                    self.__adjustRowAddresses(row, insertIndex)
                localOpenGroupsStackLevel -= 1

                groupBeginCell = self.cells[groupEndCell.groupBeginRow][groupEndCell.groupBeginColumn]
                groupEndCell.selfAndDeeperNestLevel = groupBeginCell.selfAndDeeperNestLevel
            elif rowKind == 2:
                # there is a nested canvas to consider
                insertCount = 0
                if row[insertIndex].isOuterIfLayout:
                    insertCount = max(self.maxLocalOpenGroupDepth - 1,
                                      localOpenGroupsStackLevel, 0)

                    if insertCount > 0:
                        spacer = HGroupSpacerCell(None, self, insertIndex,
                                                  rowIndex)
                        spacer.count = insertCount
                        row.insert(insertIndex, spacer)

                        insertIndex += 1
                        self.__adjustRowAddresses(row, insertIndex)

                        # To have the canvas size calculated properly
                        spacerAfter = HGroupSpacerCell(None, self,
                                                       len(row), rowIndex)
                        spacerAfter.count = spacer.count
                        row.append(spacerAfter)

                row[insertIndex].insertOpenGroupShift(
                    depth, insertedByUpper + insertCount)
            else:
                # regular row
                if self.isOuterIfLayout:
                    # It could be a connector or an if block. A shift is used
                    # instead of inserting a spacer to avoid problems with
                    # dependent region rendering
                    for index in range(insertIndex, len(row)):
                        row[index].hShift = depth - insertedByUpper
                else:
                    spacer = HGroupSpacerCell(None, self,
                                              insertIndex, rowIndex)
                    spacer.count = depth - insertedByUpper
                    row.insert(insertIndex, spacer)

                    insertIndex += 1
                    self.__adjustRowAddresses(row, insertIndex)

                    # To have the canvas size calculated properly
                    spacerAfter = HGroupSpacerCell(None, self,
                                                   len(row), rowIndex)
                    spacerAfter.count = spacer.count
                    row.append(spacerAfter)

    def updateGroupNestLevel(self, startRow, endRow):
        """startRow and endRow are inclusive"""
        maxCurrentAndDeeper = 0
        maxCurrentLevel = 0
        currentLevel = 0
        for rowIndex in range(startRow, endRow + 1):
            for cell in self.cells[rowIndex]:
                if cell.kind == CellElement.OPENED_GROUP_BEGIN:
                    currentLevel += 1
                    maxCurrentAndDeeper = max(maxCurrentAndDeeper,
                                              currentLevel)
                    maxCurrentLevel = max(maxCurrentLevel, currentLevel)
                    cell.selfAndDeeperNestLevel, cell.selfMaxNestLevel = self.updateGroupNestLevel(
                        rowIndex + 1, cell.groupEndRow - 1)
                    cell.selfAndDeeperNestLevel += 1
                    cell.selfMaxNestLevel += 1
                elif cell.kind == CellElement.OPENED_GROUP_END:
                    currentLevel -= 1
                elif cell.kind == CellElement.VCANVAS:
                    if cell.isIfBelowLayout:
                        level, _ = cell.updateGroupNestLevel(
                            0, len(cell.cells) - 1)
                        maxCurrentAndDeeper = max(maxCurrentAndDeeper,
                                                  currentLevel + level)
        return maxCurrentAndDeeper, maxCurrentLevel

    @staticmethod
    def __adjustRowAddresses(row, index):
        lastIndex = len(row) - 1
        while index <= lastIndex:
            row[index].addr[0] += 1
            index += 1

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
            if cflow.sideComment and not self.settings.noComment:
                self.__allocateCell(vacantRow - 1, 2)
                self.cells[vacantRow - 1][2] = self.__currentScopeClass(
                    cflow, self, 2, vacantRow - 1, ScopeCellElement.TOP)
                self.__allocateCell(vacantRow, 2)
                self.cells[vacantRow][2] = self.__currentScopeClass(
                    cflow, self, 2, vacantRow, ScopeCellElement.SIDE_COMMENT)

        vacantRow += 1
        if hasattr(cflow, "docstring"):
            if cflow.docstring and not self.settings.noDocstring:
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
            leadingCMLComments = None
            if scopeKind == CellElement.FILE_SCOPE:
                leadingCMLComments = cflow.leadingCMLComments
            vacantRow = self.layoutSuite(vacantRow, cflow.suite, None, None, 1,
                                         leadingCMLComments)

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

    def __renderRegion(self, openGroups):
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

        # Update the row height and calculate the row width.
        # It also catches the open groups.
        index = start
        while index <= end:
            maxHeight = 0
            row = self.cells[index]
            rowWidth = 0
            for cell in row:
                if cell.kind == CellElement.OPENED_GROUP_END:
                    openGroups.append([cell.groupBeginRow,
                                       cell.groupBeginColumn,
                                       index])
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

        openGroups = []
        maxRowIndex = len(self.cells) - 1
        index = 0
        while index <= maxRowIndex:
            if self.__dependentRegion(index):
                index = self.__renderRegion(openGroups)
            else:
                row = self.cells[index]
                maxHeight = 0
                for cell in row:
                    if cell.kind == CellElement.OPENED_GROUP_END:
                        openGroups.append([cell.groupBeginRow,
                                           cell.groupBeginColumn,
                                           index])

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

        # Second pass for the groups
        for groupBeginRow, groupBeginColumn, groupEndRow in openGroups:
            group = self.cells[groupBeginRow][groupBeginColumn]
            group.groupHeight = 0
            group.groupWidth = 0
            for row in range(groupBeginRow + 1, groupEndRow):
                group.groupHeight += self.cells[row][0].height
                rowWidth = 0
                for column in range(groupBeginColumn, len(self.cells[row])):
                    cell = self.cells[row][column]
                    if cell.kind != CellElement.H_GROUP_SPACER:
                        rowWidth += cell.width
                group.groupWidth = max(group.groupWidth, rowWidth)
            group.groupWidth += (group.selfMaxNestLevel - 1) * 4 * self.settings.openGroupHSpacer

        if self.hasScope():
            # Right hand side vertical part
            self.width += self.settings.rectRadius + self.settings.hCellPadding

        # There is no need to add spacing at the right hand side for groups.
        # The appropriate number of spacers were added for canvases and regular
        # rows so no adjustments here.

        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def adjustLastCellHeight(self, maxHeight):
        """Adjusts the cell height if needed.

        The last cell in the first column of the non-scope virtual canvas
        may need to be adjusted to occupy the whole row hight in the upper
        level canvas. This happens mostly in 'if' statements.
        """
        if not self.cells:
            return

        # The last items could be group ends so we need to find the last
        # meaningful row.
        rowIndex = len(self.cells) - 1
        while self.cells[rowIndex][-1].kind == CellElement.OPENED_GROUP_END:
            rowIndex -= 1

        allExceptLastMeaningfulHeight = 0
        for index in range(len(self.cells)):
            if index != rowIndex:
                allExceptLastMeaningfulHeight += self.cells[index][0].height

        # Update the height for all the cells in the last row
        for cell in self.cells[rowIndex]:
            if allExceptLastMeaningfulHeight + cell.height < maxHeight:
                cell.height = maxHeight - allExceptLastMeaningfulHeight
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
