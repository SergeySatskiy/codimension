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

from ui.qt import QColor, QPen, QBrush
from cdmcfparser import (CODEBLOCK_FRAGMENT, FUNCTION_FRAGMENT, CLASS_FRAGMENT,
                         BREAK_FRAGMENT, CONTINUE_FRAGMENT, RETURN_FRAGMENT,
                         RAISE_FRAGMENT, ASSERT_FRAGMENT, SYSEXIT_FRAGMENT,
                         IMPORT_FRAGMENT, COMMENT_FRAGMENT,
                         WHILE_FRAGMENT, FOR_FRAGMENT, IF_FRAGMENT,
                         WITH_FRAGMENT, TRY_FRAGMENT, CML_COMMENT_FRAGMENT)
from .cml import CMLVersion, CMLsw, CMLgb, CMLge, CMLdoc
from .cellelement import CellElement
from .items import (CodeBlockCell, ReturnCell, RaiseCell, AssertCell,
                    SysexitCell, ImportCell,  IfCell, DecoratorCell)
from .minimizeditems import (MinimizedIndependentCommentCell,
                             MinimizedIndependentDocCell)
from .auxitems import ConnectorCell, VacantCell, VSpacerCell, Rectangle
from .loopjumpitems import BreakCell, ContinueCell
from .scopeitems import (ScopeCellElement, FileScopeCell, FunctionScopeCell,
                         ClassScopeCell, ForScopeCell, WhileScopeCell,
                         TryScopeCell, WithScopeCell,
                         ExceptScopeCell, FinallyScopeCell,
                         ForElseScopeCell, WhileElseScopeCell,
                         TryElseScopeCell, ElseScopeCell,
                         ScopeHSideEdge, ScopeVSideEdge, ScopeSpacer)
from .commentitems import (AboveCommentCell, LeadingCommentCell,
                           SideCommentCell, IndependentCommentCell)
from .groupitems import (EmptyGroup, OpenedGroupBegin, OpenedGroupEnd,
                         CollapsedGroup, HGroupSpacerCell)
from .docitems import IndependentDocCell, LeadingDocCell, AboveDocCell
from .routines import getDocComment


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
    CellElement.FOR_ELSE_SCOPE: ForElseScopeCell,
    CellElement.WHILE_ELSE_SCOPE: WhileElseScopeCell,
    CellElement.TRY_ELSE_SCOPE: TryElseScopeCell,
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

    def __init__(self, settings, xAddr, yAddr,
                 validGroups, collapsedGroups, parent):
        self.kind = CellElement.VCANVAS

        # the item instances from items.py or other virtual canvases
        self.cells = []

        # Reference to the upper level canvas or None for the most upper canvas
        self.canvas = parent
        self.editor = None

        self.settings = settings
        self.addr = [xAddr, yAddr]

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

    def cleanup(self):
        """Cleans up the references etc"""
        self.canvas = None
        self.editor = None
        self.settings = None
        self.addr = None
        self.__currentCF = None
        self.__currentScopeClass = None
        self.scopeRectangle = None
        self.__validGroups = None
        self.__validGroupBeginLines = None
        self.__validGroupEndLines = None
        self.__validGroupLines = None
        self.__collapsedGroups = None
        self.__groupStack = None

        for row in self.cells:
            if row:
                for cell in row:
                    if isinstance(cell, VirtualCanvas):
                        cell.cleanup()

    @staticmethod
    def scopedItem():
        """The vcanvas is not a scoped item"""
        return False

    @staticmethod
    def isComment():
        """The vcanvas is not a comment"""
        return False

    @staticmethod
    def isCMLDoc():
        """The vcanvas is not a CML doc"""
        return False

    def getScopeName(self):
        """Provides the name of the scope drawn on the canvas"""
        for row in self.cells:
            for cell in row:
                if cell.kind in _scopeToName:
                    return _scopeToName[cell.kind]
                if cell.kind == CellElement.FUNC_SCOPE:
                    return 'def ' + cell.ref.name.getContent() + '()'
                if cell.kind == CellElement.CLASS_SCOPE:
                    return 'class ' + cell.ref.name.getContent()
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
                        ScopeHSideEdge(self.__currentCF, self, 0, lastIndex))
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
        if not self.settings.noComment and not self.settings.hidecomments:
            leadingDoc = getDocComment(item.leadingCMLComments)
            if leadingDoc:
                self.__allocateCell(row, column + 1)
                self.cells[row][column] = ConnectorCell(CONN_N_S, self,
                                                        column, row)
                self.cells[row][column + 1] = LeadingDocCell(item, leadingDoc,
                                                             self,
                                                             column + 1, row)
                row += 1

            if item.leadingComment:
                self.__allocateCell(row, column + 1)
                self.cells[row][column] = ConnectorCell(CONN_N_S, self,
                                                        column, row)

                self.cells[row][column + 1] = self.__createLeadingComment(
                    item, self, column + 1, row)
                row += 1
        return row

    def __needLoopCommentRow(self, item):
        """Tells # of rows to be reserved for comments/docs for the loops"""
        if self.settings.noComment or self.settings.hidecomments:
            return 0, 0, []

        comments = []

        doc = getDocComment(item.leadingCMLComments)
        comments.append([doc, item.leadingComment])
        rows = 0
        if item.leadingComment:
            rows += 1
        if doc:
            rows += 1

        elseRows = 0
        if item.elsePart:
            elseDoc = getDocComment(item.elsePart.leadingCMLComments)
            comments.append([elseDoc, item.elsePart.leadingComment])

            if item.elsePart.leadingComment:
                elseRows += 1
            if elseDoc:
                elseRows += 1
        else:
            comments.append([None, None])
        return rows, elseRows, comments

    def __needTryCommentRow(self, item):
        """Tells if a row for comments need to be reserved"""
        if self.settings.noComment or self.settings.hidecomments:
            return 0, []

        comments = []

        doc = getDocComment(item.leadingCMLComments)
        rows = 0
        if item.leadingComment:
            rows += 1
        if doc:
            rows += 1
        comments.append([rows, doc, item.leadingComment])

        if not self.settings.hideexcepts:
            for exceptPart in item.exceptParts:
                excDoc = getDocComment(exceptPart.leadingCMLComments)

                excRows = 0
                if exceptPart.leadingComment:
                    excRows += 1
                if excDoc:
                    excRows += 1
                comments.append([excRows, excDoc, exceptPart.leadingComment])

                rows = max(rows, excRows)
        return rows, comments

    def __checkLeadingCMLComments(self, leadingCMLComments):
        """Provides a list of group begins/ends as they are in the comments"""
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

        if item.kind in [FUNCTION_FRAGMENT, CLASS_FRAGMENT]:
            if item.decorators:
                return self.__checkLeadingCMLComments(
                    item.decorators[0].leadingCMLComments)

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
            newGroup = CollapsedGroup(item, groupComment, self,
                                      column, vacantRow)
        else:
            newGroup = OpenedGroupBegin(item, groupComment, self,
                                        column, vacantRow)
            newGroup.isTerminal = self.__isTerminalCell(vacantRow - 1, column)

        # allocate new cell, memo the group begin ref,
        # add the group to the stack and return a new vacant row
        self.__allocateAndSet(vacantRow, column, newGroup)
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
            emptyGroup = EmptyGroup(groupBegin.ref,
                                    groupBegin.groupBeginCMLRef, self,
                                    groupColumn, groupRow)
            self.cells[groupRow][groupColumn] = emptyGroup
        elif currentGroup.kind == CellElement.COLLAPSED_GROUP:
            # Collapsed group: the end of the group is memorized in the common
            # block after ifs
            pass
        else:
            # Opened group: insert a group end
            groupEnd = OpenedGroupEnd(item, groupBegin.groupBeginCMLRef,
                                      self, column, vacantRow)
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

    def __createIndependentComment(self, ref, canvas, xPos, yPos):
        """Creates an independent comment"""
        if self.settings.hidecomments:
            return MinimizedIndependentCommentCell(ref, canvas, xPos, yPos)
        return IndependentCommentCell(ref, canvas, xPos, yPos)

    def __createLeadingComment(self, ref, canvas, xPos, yPos):
        """Creates a leading comment"""
        return LeadingCommentCell(ref, canvas, xPos, yPos)

    def __createAboveComment(self, ref, canvas, xPos, yPos):
        """Creates an above comment"""
        return AboveCommentCell(ref, canvas, xPos, yPos)

    def __createSideComment(self, ref, canvas, xPos, yPos):
        """Creates a side comment"""
        return SideCommentCell(ref, canvas, xPos, yPos)

    def __needSideComment(self, item):
        """True if a side comment is needed"""
        if self.settings.noComment:
            return False
        if self.settings.hidecomments:
            return False
        return item.sideComment is not None

    def __layoutCMLComment(self, item, vacantRow, column):
        """Lays out a CML comment"""
        if hasattr(item, 'ref'):
            # High level CML comment, low level are out of interest
            if item.CODE == CMLdoc.CODE:
                conn = ConnectorCell(CONN_N_S, self, column, vacantRow)
                if self.settings.hidecomments:
                    doc = MinimizedIndependentDocCell(item, self, column + 1,
                                                      vacantRow)
                else:
                    doc = IndependentDocCell(item, self, column + 1, vacantRow)

                self.__allocateCell(vacantRow, column + 1)
                self.cells[vacantRow][column] = conn
                self.cells[vacantRow][column + 1] = doc
                vacantRow += 1
        return vacantRow

    def __layoutWith(self, item, vacantRow, column):
        """Lays out a with statement"""
        vacantRow = self.__allocateLeadingComment(item, vacantRow, column)
        self.__allocateScope(item, CellElement.WITH_SCOPE, vacantRow, column)
        if self.__needSideComment(item):
            comment = self.__createSideComment(item, self,
                                               column + 1, vacantRow)
            self.__allocateAndSet(vacantRow, column + 1, comment)
        return vacantRow + 1

    def __layoutComment(self, item, vacantRow, column):
        """Lays out a comment"""
        conn = ConnectorCell(CONN_N_S, self, column, vacantRow)
        comment = self.__createIndependentComment(item, self, column + 1,
                                                  vacantRow)

        self.__allocateCell(vacantRow, column + 1)
        self.cells[vacantRow][column] = conn
        self.cells[vacantRow][column + 1] = comment
        return vacantRow + 1

    def __firstDecorNeedFullComments(self, item):
        """Provides the number of the required rows"""
        if not item.decorators:
            return 0
        if self.settings.noDecor or self.settings.hidedecors:
            return 0
        if self.settings.noComment or self.settings.hidecomments:
            return 0
        count = 0
        decor = item.decorators[0]
        if decor.leadingComment:
            count += 1
        leadingDoc = getDocComment(decor.leadingCMLComments)
        if leadingDoc:
            count += 1
        return count

    def __itemNeedFullComments(self, item):
        """Provides the number of required rows"""
        if self.settings.noComment or self.settings.hidecomments:
            return 0
        count = 0
        if item.leadingComment:
            count += 1
        leadingDoc = getDocComment(item.leadingCMLComments)
        if leadingDoc:
            count += 1
        return count

    def __layoutDefClass(self, item, vacantRow, column):
        """Lays out a function or a class"""
        # Now the class or function scope
        scopeCanvas = VirtualCanvas(self.settings, None, None,
                                    self.__validGroups, self.__collapsedGroups,
                                    self)
        if item.kind == FUNCTION_FRAGMENT:
            scopeCanvas.layout(item, CellElement.FUNC_SCOPE)
        else:
            scopeCanvas.layout(item, CellElement.CLASS_SCOPE)

        decorComments = self.__firstDecorNeedFullComments(item)
        mainComments = self.__itemNeedFullComments(item)

        if decorComments > 0:
            defClassRegionBegin = vacantRow

        if decorComments > mainComments:
            # Allocate connectors
            connectorCount = decorComments - mainComments
            while connectorCount > 0:
                conn = ConnectorCell(CONN_N_S, self, column, vacantRow)
                self.__allocateCell(vacantRow, column)
                self.cells[vacantRow][column] = conn
                vacantRow += 1
                connectorCount -= 1

        # Leading comment and doc
        vacantRow = self.__allocateLeadingComment(item, vacantRow, column)

        if decorComments > 0:
            decorColumn = column + 1
            if item.sideComment:
                decorColumn += 1

            tempVacantRow = defClassRegionBegin
            if mainComments > decorComments:
                spare = mainComments - decorComments
                tempVacantRow += spare
            decor = item.decorators[0]
            leadingDoc = getDocComment(decor.leadingCMLComments)
            if leadingDoc:
                doc = AboveDocCell(decor, leadingDoc, self,
                                   decorColumn, tempVacantRow)
                doc.needConnector = False
                doc.smallBadge = True
                doc.hanging = True
                self.__allocateAndSet(tempVacantRow, decorColumn, doc)
                tempVacantRow += 1
            if decor.leadingComment:
                comment = self.__createAboveComment(decor, self, decorColumn,
                                                    tempVacantRow)
                comment.needConnector = leadingDoc is not None
                comment.smallBadge = True
                comment.hanging = True
                self.__allocateAndSet(tempVacantRow, decorColumn, comment)

            self.dependentRegions.append((defClassRegionBegin,
                                          defClassRegionBegin +
                                          max(mainComments, decorComments)))

        # Update the scope canvas parent and address
        scopeCanvas.parent = self
        scopeCanvas.addr = [column, vacantRow]
        self.__allocateAndSet(vacantRow, column, scopeCanvas)

        vacantColumn = column + 1
        if self.__needSideComment(item):
            comment = self.__createSideComment(item, self,
                                               vacantColumn, vacantRow)
            self.__allocateAndSet(vacantRow, vacantColumn, comment)
            vacantColumn += 1

        if item.decorators and not self.settings.noDecor and not self.settings.hidedecors:
            if item.decorators:
                decoratorCanvas = VirtualCanvas(self.settings, vacantColumn,
                                                vacantRow, self.__validGroups,
                                                self.__collapsedGroups,
                                                self)
                decoratorCanvas.layoutDecorators(item, scopeCanvas.cells[0][0])
                self.__allocateAndSet(vacantRow, vacantColumn, decoratorCanvas)

        return vacantRow + 1

    def __layoutLoop(self, item, vacantRow, column):
        """Lays out a loop"""
        targetScope = CellElement.WHILE_SCOPE
        if item.kind == FOR_FRAGMENT:
            targetScope = CellElement.FOR_SCOPE

        loopRegionBegin = vacantRow
        mainRows, elseRows, aboveItems = self.__needLoopCommentRow(item)
        maxRows = max(mainRows, elseRows)
        if maxRows > 0:
            # Main part
            cRow = vacantRow + (maxRows - mainRows)

            tempVacant = vacantRow
            while mainRows < maxRows:
                conn = ConnectorCell(CONN_N_S, self, column, tempVacant)
                self.__allocateCell(tempVacant, column)
                self.cells[tempVacant][column] = conn
                tempVacant += 1
                mainRows += 1

            if aboveItems[0][0]:
                doc = AboveDocCell(item, aboveItems[0][0], self, column, cRow)
                doc.needConnector = True
                self.__allocateAndSet(cRow, column, doc)
                cRow += 1
            if item.leadingComment:
                comment = self.__createAboveComment(item, self, column, cRow)
                comment.needConnector = True
                self.__allocateAndSet(cRow, column, comment)

            if elseRows > 0:
                cRow = vacantRow + (maxRows - elseRows)
                vacantColumn = column + 1
                if item.sideComment and not self.settings.noComment:
                    vacantColumn += 1

                if aboveItems[1][0]:
                    doc = AboveDocCell(item.elsePart, aboveItems[1][0], self,
                                       vacantColumn, cRow)
                    self.__allocateAndSet(cRow, vacantColumn, doc)
                    cRow += 1
                if aboveItems[1][1]:
                    comment = self.__createAboveComment(item.elsePart, self,
                                                        vacantColumn, cRow)
                    comment.needConnector = aboveItems[1][0] is not None
                    self.__allocateAndSet(cRow, vacantColumn, comment)

                self.dependentRegions.append((loopRegionBegin,
                                              vacantRow + maxRows))

            vacantRow += maxRows

        self.__allocateScope(item, targetScope, vacantRow, column)

        vacantColumn = column + 1
        if self.__needSideComment(item):
            comment = self.__createSideComment(item, self,
                                               vacantColumn, vacantRow)
            self.__allocateAndSet(vacantRow, vacantColumn, comment)
            vacantColumn += 1

        if item.elsePart:
            if item.kind == FOR_FRAGMENT:
                self.__allocateScope(item.elsePart, CellElement.FOR_ELSE_SCOPE,
                                     vacantRow, vacantColumn)
            else:
                self.__allocateScope(item.elsePart,
                                     CellElement.WHILE_ELSE_SCOPE,
                                     vacantRow, vacantColumn)
            if self.__needSideComment(item.elsePart):
                comment = self.__createSideComment(item.elsePart, self,
                                                   vacantColumn + 1, vacantRow)
                self.__allocateAndSet(vacantRow, vacantColumn + 1, comment)

            self.cells[vacantRow][vacantColumn].setLeaderRef(item)
        return vacantRow + 1

    def __layoutTry(self, item, vacantRow, column):
        """Lays out a try statement"""
        tryRegionBegin = vacantRow

        maxRows, aboveItems = self.__needTryCommentRow(item)
        if maxRows > 0:
            # Main part
            mainRows = aboveItems[0][0]
            cRow = vacantRow + (maxRows - mainRows)

            tempVacant = vacantRow
            while mainRows < maxRows:
                conn = ConnectorCell(CONN_N_S, self, column, tempVacant)

                self.__allocateCell(tempVacant, column)
                self.cells[tempVacant][column] = conn
                tempVacant += 1
                mainRows += 1

            if aboveItems[0][1]:
                doc = AboveDocCell(item, aboveItems[0][1], self, column, cRow)
                doc.needConnector = True
                self.__allocateAndSet(cRow, column, doc)
                cRow += 1
            if item.leadingComment:
                comment = self.__createAboveComment(item, self, column, cRow)
                comment.needConnector = True
                self.__allocateAndSet(cRow, column, comment)

            if item.exceptParts and not self.settings.hideexcepts:
                self.dependentRegions.append((tryRegionBegin,
                                              vacantRow + maxRows))


        self.__allocateScope(item, CellElement.TRY_SCOPE,
                             vacantRow + maxRows, column)

        vacantColumn = column + 1
        if self.__needSideComment(item):
            comment = self.__createSideComment(item, self,
                                               vacantColumn,
                                               vacantRow + maxRows)
            self.__allocateAndSet(vacantRow + maxRows, vacantColumn, comment)
            vacantColumn += 1

        if not self.settings.hideexcepts:
            exceptIndex = 1
            for exceptPart in item.exceptParts:
                if maxRows > 0:
                    excRows = aboveItems[exceptIndex][0]
                    cRow = vacantRow + (maxRows - excRows)

                    if aboveItems[exceptIndex][1]:
                        doc = AboveDocCell(exceptPart,
                                           aboveItems[exceptIndex][1],
                                           self, vacantColumn, cRow)
                        doc.hanging = True
                        self.__allocateAndSet(cRow, vacantColumn, doc)
                        cRow += 1
                    if aboveItems[exceptIndex][2]:
                        comment = self.__createAboveComment(exceptPart, self,
                                                            vacantColumn, cRow)
                        comment.needConnector = \
                            aboveItems[exceptIndex][1] is not None
                        comment.hanging = True
                        self.__allocateAndSet(cRow, vacantColumn, comment)

                self.__allocateScope(exceptPart,
                                     CellElement.EXCEPT_SCOPE,
                                     vacantRow + maxRows, vacantColumn)
                self.cells[vacantRow + maxRows][vacantColumn].setLeaderRef(item)

                if self.__needSideComment(exceptPart):
                    comment = self.__createSideComment(exceptPart, self,
                                                       vacantColumn + 1,
                                                       vacantRow + maxRows)
                    self.__allocateAndSet(vacantRow + maxRows, vacantColumn + 1,
                                          comment)
                    vacantColumn += 1

                exceptIndex += 1
                vacantColumn += 1

        vacantRow += maxRows

        # The else part goes below
        if item.elsePart:
            vacantRow += 1
            vacantRow = self.__allocateLeadingComment(item.elsePart,
                                                      vacantRow, column)
            self.__allocateScope(item.elsePart, CellElement.TRY_ELSE_SCOPE,
                                 vacantRow, column)
            self.cells[vacantRow][column].setLeaderRef(item)
            if self.__needSideComment(item.elsePart):
                comment = self.__createSideComment(item.elsePart, self,
                                                   column + 1, vacantRow)
                self.__allocateAndSet(vacantRow, column + 1, comment)
        # The finally part is located below
        if item.finallyPart:
            vacantRow += 1
            vacantRow = self.__allocateLeadingComment(item.finallyPart,
                                                      vacantRow, column)
            self.__allocateScope(item.finallyPart, CellElement.FINALLY_SCOPE,
                                 vacantRow, column)
            self.cells[vacantRow][column].setLeaderRef(item)
            if self.__needSideComment(item.finallyPart):
                comment = self.__createSideComment(item.finallyPart, self,
                                                   column + 1, vacantRow)
                self.__allocateAndSet(vacantRow, column + 1, comment)
        return vacantRow + 1

    def __layoutIf(self, item, vacantRow, column):
        """Lays out an if statement"""
        lastNonElseIndex = len(item.parts) - 1
        for index in range(len(item.parts)):
            if item.parts[index].condition is None:
                lastNonElseIndex = index - 1
                break

        canvas = VirtualCanvas(self.settings, 0, 0, self.__validGroups,
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
            tempCanvas = VirtualCanvas(self.settings, 0, 0, self.__validGroups,
                                       self.__collapsedGroups, self)
            tempCanvas.isNoScope = True
            tempCanvas.layoutIfBranch(item.parts[index], canvas)
            canvas = tempCanvas
            index -= 1

        self.__allocateAndSet(vacantRow, 1, canvas)
        return vacantRow + 1

    def layoutDecorators(self, item, scopeItem):
        """Lays out decorators"""
        isClass = item.kind == CLASS_FRAGMENT

        vacantRow = 0
        column = 0
        lastIndex = len(item.decorators) - 1
        for index, dec in enumerate(item.decorators):
            if index > 0:
                # The very first decorator comments are allocated together with
                # the class/function so it is skipped here
                if not self.settings.noComment and not self.settings.hidecomments:
                    leadingDoc = getDocComment(dec.leadingCMLComments)
                    if leadingDoc:
                        doc = AboveDocCell(dec, leadingDoc, self, column, vacantRow)
                        doc.needConnector = False
                        doc.smallBadge = True
                        doc.hanging = True
                        self.__allocateAndSet(vacantRow, column, doc)
                        vacantRow += 1

                    if dec.leadingComment:
                        comment = self.__createAboveComment(dec, self, column, vacantRow)
                        comment.needConnector = leadingDoc is not None
                        comment.smallBadge = True
                        hanging = True
                        self.__allocateAndSet(vacantRow, column, comment)
                        vacantRow += 1

            cell = DecoratorCell(dec, self, column, vacantRow, scopeItem)
            cell.isFirst = index == 0

            self.__allocateAndSet(vacantRow, column, cell)
            if self.__needSideComment(dec):
                comment = self.__createSideComment(dec, self,
                                                   column + 1, vacantRow)
                self.__allocateAndSet(vacantRow, column + 1, comment)
            vacantRow += 1

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
                if not self.settings.noComment:
                    vacantRow = self.__layoutCMLComment(item, vacantRow, column)
                continue

            if item.kind == COMMENT_FRAGMENT:
                if not self.settings.noComment:
                    vacantRow = self.__layoutComment(item, vacantRow, column)
                continue

            if item.kind == WITH_FRAGMENT:
                if not self.settings.noWith:
                    vacantRow = self.__layoutWith(item, vacantRow, column)
                continue

            if item.kind in [FUNCTION_FRAGMENT, CLASS_FRAGMENT]:
                vacantRow = self.__layoutDefClass(item, vacantRow, column)
                continue

            if item.kind in [WHILE_FRAGMENT, FOR_FRAGMENT]:
                if item.kind == FOR_FRAGMENT and self.settings.noFor:
                    continue
                if item.kind == WHILE_FRAGMENT and self.settings.noWhile:
                    continue
                vacantRow = self.__layoutLoop(item, vacantRow, column)
                continue

            if item.kind == TRY_FRAGMENT:
                if not self.settings.noTry:
                    vacantRow = self.__layoutTry(item, vacantRow, column)
                continue

            if item.kind == IF_FRAGMENT:
                if not self.settings.noIf:
                    vacantRow = self.__layoutIf(item, vacantRow, column)
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

            if self.__needSideComment(item):
                comment = self.__createSideComment(item, self,
                                                   column + 1, vacantRow)
                self.__allocateAndSet(vacantRow, column + 1, comment)
            vacantRow += 1

            # end of for loop

        if scopeKind:
            self.__currentCF = None

        return vacantRow

    def layoutIfBranch(self, yBranch, nBranch):
        """Used in 'if' statements processing"""
        # It is always called when a layout is empty
        vacantRow = self.__allocateLeadingComment(yBranch, 0, 0)
        self.__allocateAndSet(vacantRow, 0,
                              IfCell(yBranch, self, 0, vacantRow))

        # Exclude the leading comments and docs from the dependent region
        dependentRegionBegin = vacantRow

        topConnector = ConnectorCell(CONN_W_S, self, 1, vacantRow)
        topConnector.subKind = ConnectorCell.TOP_IF
        self.__allocateAndSet(vacantRow, 1, topConnector)

        if self.__needSideComment(yBranch):
            comment = self.__createSideComment(yBranch, self, 2, vacantRow)
            self.__allocateAndSet(vacantRow, 2, comment)
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
                    cItem = self.__createIndependentComment(
                        nBranch.leadingComment, branchLayout, 1, 0)
                    branchLayout.cells.append([])
                    branchLayout.cells[0].append(conn)
                    branchLayout.cells[0].append(cItem)

                if nBranch.sideComment and not self.settings.noComment:
                    # Draw as an independent comment: insert into the layout
                    rowIndex = scopeCommentRows - 1
                    conn = ConnectorCell(CONN_N_S, branchLayout, 0, rowIndex)
                    cItem = self.__createIndependentComment(
                        nBranch.sideComment, branchLayout, 1, rowIndex)
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

        self.dependentRegions.append((dependentRegionBegin, vacantRow))

    def setLeaderRef(self, ref):
        """Sets the leader ref for ELSE, EXCEPT and FINALLY scopes"""
        if self.cells[0][0].kind in [CellElement.ELSE_SCOPE,
                                     CellElement.EXCEPT_SCOPE,
                                     CellElement.FINALLY_SCOPE]:
            if self.cells[0][0].subKind == ScopeCellElement.TOP_LEFT:
                self.cells[0][0].leaderRef = ref
                return
        raise Exception("Logic error: cannot set the leader reference")

    def layoutModule(self, cflow):
        """Lays out a module"""
        self.isNoScope = True
        vacantRow = 0

        # Avoid glueing to the top view edge
        self.__allocateAndSet(vacantRow, 1,
                              VSpacerCell(None, self, 1, vacantRow))
        vacantRow += 1

        if not self.settings.noComment and not self.settings.hidecomments:
            leadingDoc = getDocComment(cflow.leadingCMLComments)
            if leadingDoc:
                doc = AboveDocCell(cflow, leadingDoc, self, 1, vacantRow)
                doc.needConnector = False
                doc.hanging = True
                self.__allocateAndSet(vacantRow, 1, doc)
                vacantRow += 1
            if cflow.leadingComment:
                comment = self.__createAboveComment(cflow, self, 1, vacantRow)
                comment.needConnector = leadingDoc is not None
                comment.hanging = True
                self.__allocateAndSet(vacantRow, 1, comment)
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
                                    ScopeCellElement.DOCSTRING] or \
                        cell.kind == CellElement.SCOPE_CORNER_EDGE:
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

        # else, try, finally and except with no clause need no declaration
        if self.cells[vacantRow - 1][0].needDeclaration():
            self.__allocateCell(vacantRow, 1)
            self.cells[vacantRow][1] = self.__currentScopeClass(
                cflow, self, 1, vacantRow, ScopeCellElement.DECLARATION)
            self.linesInHeader += 1
            vacantRow += 1

        if hasattr(cflow, "docstring"):
            if cflow.docstring and (not self.settings.noDocstring and
                                    not self.settings.hidedocstrings):
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
        leadingCMLComments = None
        if scopeKind == CellElement.FILE_SCOPE:
            leadingCMLComments = cflow.leadingCMLComments
        vacantRow = self.layoutSuite(vacantRow, cflow.suite, None, None, 1,
                                     leadingCMLComments)

        # Allocate the scope footer
        self.__allocateCell(vacantRow, 0, False)
        self.cells[vacantRow][0] = ScopeSpacer(cflow, self, 0, vacantRow)

        self.__currentCF = None

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
                                    CellElement.SIDE_COMMENT,
                                    CellElement.ABOVE_COMMENT,
                                    CellElement.INDEPENDENT_MINIMIZED_COMMENT]:
                    row[-1].tailComment = True
            index += 1

        for column in range(maxColumns):
            maxColumnWidth = 0
            index = start
            while index <= end:
                row = self.cells[index]
                if column < len(row):
                    row[column].render()
                    if not row[column].scopedItem():
                        if row[column].isComment() or row[column].isCMLDoc():
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
                    if not cell.scopedItem():
                        if cell.isComment() or cell.isCMLDoc():
                            cell.adjustWidth()
                for cell in row:
                    cell.height = maxHeight
                    if cell.kind == CellElement.VCANVAS:
                        if not cell.hasScope():
                            cell.adjustLastCellHeight(maxHeight)
                self.height += maxHeight
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

        # There is no need to add spacing at the right hand side for groups.
        # The appropriate number of spacers were added for canvases and regular
        # rows so no adjustments here.

        # Third pass for if branch adjustments
        for rowIndex, row in enumerate(self.cells):
            for cellIndex, cell in enumerate(row):
                if cell.kind == CellElement.IF:
                    cellBelow = self.cells[rowIndex + 1][cellIndex]
                    spare = cellBelow.width - cellBelow.minWidth
                    minShift = 2 * self.settings.hCellPadding + self.settings.mainLine + self.settings.ifWidth
                    if spare > minShift:
                        cellBelowRight = self.cells[rowIndex + 1][cellIndex + 1]
                        if cellBelowRight.kind == CellElement.VCANVAS:
                            # The rhs branch will be shifted to the left
                            if spare < cellBelowRight.width:
                                # The RHS branch is wider than the available shift
                                # width so use it all
                                shift = spare
                            else:
                                # The RHS branch is narrower than the available
                                # shift width so use only the cell width
                                shift = cellBelowRight.width
                            # Signal the IF cell that there will be no RHS
                            # connector but a bottom instead
                            cell.needHConnector = False
                            cell.rhsShift = shift

                            cellBelow.width -= shift
                            # Delete the RHS if connector cell
                            del self.cells[rowIndex][cellIndex + 1]

                            try:
                                # The if side comment heeds to be re-rendered
                                # because it is not region dependent anymore
                                sideCommentCell = self.cells[rowIndex][cellIndex + 1]
                                if sideCommentCell.kind in [CellElement.SIDE_COMMENT]:
                                    oldMinHeight = sideCommentCell.minHeight
                                    oldHeight = sideCommentCell.height
                                    sideCommentCell.render()
                                    sideCommentCell.minHeight = oldMinHeight
                                    sideCommentCell.height = oldHeight
                                    # The rhs connector has been deleted, so the
                                    # x address is changed
                                    sideCommentCell.addr = [cellIndex + 1, rowIndex]
                            except:
                                pass

                            # Finishing connector if so, should be adjusted too
                            try:
                                closingCell = self.cells[rowIndex + 2][cellIndex]
                                if closingCell.kind == CellElement.CONNECTOR:
                                    if closingCell.hasVertical() and closingCell.hasHorizontal():
                                        closingCell.width -= shift
                            except:
                                pass
                            break

        # The if cells adjustments may have deleted connectors and adjusted
        # cell width, so recalculate the canves width
        self.width = 0
        for row in self.cells:
            totalWidth = 0
            for cell in row:
                totalWidth += cell.width
            self.width = max(self.width, totalWidth)

        if self.hasScope():
            # Right hand side vertical part
            self.width += self.settings.scopeRectRadius + self.settings.hCellPadding

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
        self.editor = editor

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
                    if cell.kind == CellElement.VCANVAS:
                        rect = Rectangle(self, currentX + 1, currentY + 1,
                                         cell.width - 2, cell.height -2)
                        rect.pen = QPen(QColor(255, 0, 0, 255))
                        rect.brush = QBrush(QColor(255, 0, 0, 127))
                        rect.setToolTip('Canvas ' + str(cell.width) + 'x' +
                                        str(cell.height))
                        scene.addItem(rect)
                    else:
                        rect = Rectangle(self, currentX, currentY,
                                         cell.width, cell.height)
                        rect.pen = QPen(QColor(0, 255, 0, 255))
                        rect.brush = QBrush(QColor(0, 255, 0, 127))
                        rect.setToolTip('Item ' + str(cell) +
                                        ' ' + str(cell.kind))
                        scene.addItem(rect)
                cell.draw(scene, currentX, currentY)
                currentX += cell.width
            currentY += height


def formatFlow(s):
    """Reformats the control flow output"""
    result = ""
    shifts = []     # positions of opening '<'
    pos = 0         # symbol position in a line
    nextIsList = False

    def IsNextList(index, maxIndex, buf):
        if index == maxIndex:
            return False
        if buf[index + 1] == '<':
            return True
        if index < maxIndex - 1:
            if buf[index + 1] == '\n' and buf[index + 2] == '<':
                return True
        return False

    maxIndex = len(s) - 1
    for index in range(len(s)):
        sym = s[index]
        if sym == "\n":
            lastShift = shifts[-1]
            result += sym + lastShift * " "
            pos = lastShift
            if index < maxIndex:
                if s[index + 1] not in "<>":
                    result += " "
                    pos += 1
            continue
        if sym == "<":
            if nextIsList == False:
                shifts.append(pos)
            else:
                nextIsList = False
            pos += 1
            result += sym
            continue
        if sym == ">":
            shift = shifts[-1]
            result += '\n'
            result += shift * " "
            pos = shift
            result += sym
            pos += 1
            if IsNextList(index, maxIndex, s):
                nextIsList = True
            else:
                del shifts[-1]
                nextIsList = False
            continue
        result += sym
        pos += 1
    return result
