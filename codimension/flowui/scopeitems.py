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

"""Various items used to represent a control flow on a virtual canvas"""

# pylint: disable=C0305
# pylint: disable=C0302
# pylint: disable=W0702
# pylint: disable=R0913

from sys import maxsize
from html import escape
from ui.qt import Qt, QPen, QBrush, QGraphicsRectItem, QGraphicsItem, QPointF, QColor
from .auxitems import (BadgeItem, Connector, HSpacerCell, VSpacerCell,
                       SpacerCell, DocstringBadgeItem, CommentBadgeItem,
                       ExceptBadgeItem, ScopeDecorBadgeItem, DocLinkBadgeItem)
from .cellelement import CellElement
from .routines import distance, getNoCellCommentBoxPath, getDocComment
from .cml import CMLVersion
from .colormixin import ColorMixin
from .textmixin import TextMixin
from .abovebadges import AboveBadgesSpacer


class ScopeHSideEdge(HSpacerCell):

    """Reserves some space for the scope horizontal edge"""

    def __init__(self, ref, canvas, x, y):
        HSpacerCell.__init__(self, ref, canvas, x, y,
                             width=canvas.settings.scopeRectRadius +
                             canvas.settings.hCellPadding)
        self.kind = CellElement.SCOPE_H_SIDE_EDGE


class ScopeVSideEdge(VSpacerCell):

    """Reserves some space for the scope vertical edge"""

    def __init__(self, ref, canvas, x, y):
        VSpacerCell.__init__(self, ref, canvas, x, y,
                             height=canvas.settings.scopeRectRadius +
                             canvas.settings.vCellPadding)
        self.kind = CellElement.SCOPE_V_SIDE_EDGE


class ScopeSpacer(SpacerCell):

    """Reserves some space for the scope corner"""

    def __init__(self, ref, canvas, x, y):
        SpacerCell.__init__(self, ref, canvas, x, y,
                            width=canvas.settings.scopeRectRadius +
                            canvas.settings.hCellPadding,
                            height=canvas.settings.scopeRectRadius +
                            canvas.settings.vCellPadding)
        self.kind = CellElement.SCOPE_CORNER_EDGE


class ScopeCellElement(CellElement, TextMixin, ColorMixin, QGraphicsRectItem):

    """Base class for the scope items"""

    TOP_LEFT = 0
    DECLARATION = 1
    DOCSTRING = 3

    def __init__(self, ref, canvas, x, y, subKind,
                 bgColor, fgColor, borderColor):
        isDocstring = subKind == ScopeCellElement.DOCSTRING
        if isDocstring:
            bgColor = canvas.settings.docstringBGColor
            fgColor = canvas.settings.docstringFGColor
            # This is the case of the full text docstring i.e. the border color
            # is borowed from the scope

        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, bgColor, fgColor, borderColor,
                            isDocstring=isDocstring)
        if isDocstring:
            # The color mixin may overwrite the border color of the docstring
            # so it needs to be recovered for the full text docstrings
            self.borderColor = borderColor

        QGraphicsRectItem.__init__(self)

        self.subKind = subKind
        self.__navBarUpdate = None
        self._connector = None
        self.scene = None
        self.__sideCommentPath = None

        # Will be initialized only for the TOP_LEFT item of the
        # ELSE_SCOPE, EXCEPT_SCOPE and FINALLY_SCOPE
        # It points to TRY, FOR and WHILE approprietely
        self.leaderRef = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __renderTopLeft(self):
        """Renders the top left corner of the scope"""
        s = self.canvas.settings
        self.minHeight = s.scopeRectRadius + s.vCellPadding
        if self.aboveBadges.hasAny():
            self.minHeight += self.aboveBadges.height + s.badgeToScopeVPadding
        self.minWidth = s.scopeRectRadius + s.hCellPadding

        # Sometimes there are many badges and little content
        # So the widest value needs to be picked.
        # The wiered s.scopeRectRadius / 2 is because the badges start
        # from the very edge of the scope
        self.minWidth = max(self.aboveBadges.width + s.scopeRectRadius / 2,
                            self.minWidth)

    def __renderDeclaration(self):
        """Renders the scope declaration"""
        s = self.canvas.settings
        self.setupText(self)

        # Top and left edges are in the neiborgh cells
        self.minHeight = self.textRect.height() + \
                         2 * s.vHeaderPadding - s.scopeRectRadius
        self.minWidth = self.textRect.width() + \
                        2 * s.hHeaderPadding - s.scopeRectRadius

        if self.kind in [CellElement.WHILE_SCOPE,
                         CellElement.FOR_SCOPE]:
            self.minWidth += 2 * s.ifWidth + 2 * s.loopHeaderPadding

        self.minWidth = max(self.minWidth, s.minWidth)

    def __renderDocstring(self):
        """Renders the scope docstring"""
        s = self.canvas.settings
        self.setupText(self, customText=self.ref.docstring.getDisplayValue(),
                       customReplacement='')

        self.minHeight = self.textRect.height() + 2 * s.vHeaderPadding
        self.minWidth = self.textRect.width() + 2 * (s.hHeaderPadding -
                                                     s.scopeRectRadius)

    def renderCell(self):
        """Provides rendering for the scope elements"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.__renderTopLeft()
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.__renderDeclaration()
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.__renderDocstring()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __followLoop(self):
        """Used to detect if an 'else' scope is for a loop"""
        row = self.canvas.addr[1]
        column = self.canvas.addr[0] - 1
        cells = self.canvas.canvas.cells
        try:
            if cells[row][column].kind == CellElement.SIDE_COMMENT:
                return True
            if cells[row][column].kind == CellElement.VCANVAS:
                return cells[row][column].cells[0][0].kind \
                    in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]
            return False
        except:
            return False

    def __needConnector(self):
        """True if a connector is required"""
        if self.kind in [CellElement.FOR_SCOPE,
                         CellElement.WHILE_SCOPE, CellElement.FUNC_SCOPE,
                         CellElement.CLASS_SCOPE, CellElement.WITH_SCOPE,
                         CellElement.FINALLY_SCOPE, CellElement.TRY_SCOPE]:
            return True
        if self.kind == CellElement.ELSE_SCOPE:
            return self.statement == ElseScopeCell.TRY_STATEMENT
        return False

    def __drawTopLeft(self):
        """Draws the top left element of a scope"""
        s = self.canvas.settings

        # Draw connector if needed
        if self.__needConnector() and self._connector is None:
            # The connector needs to go only to the middle of the badge
            # so there will be two of them
            self._connector = Connector(
                self.canvas, self.baseX + s.mainLine,
                self.baseY, self.baseX + s.mainLine,
                self.baseY + s.vCellPadding)
            self.scene.addItem(self._connector)

            bottomConnector = Connector(
                self.canvas, self.baseX + s.mainLine,
                self.baseY + self.minHeight,
                self.baseX + s.mainLine,
                self.baseY + self.canvas.height)
            self.scene.addItem(bottomConnector)

        # Draw the scope rounded rectangle when we see the top left corner
        penWidth = s.selectPenWidth - 1

        yPos = self.baseY + s.vCellPadding - penWidth
        height = self.canvas.minHeight - 2 * s.vCellPadding + 2 * penWidth
        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + s.badgeToScopeVPadding
            yPos += badgeShift
            height -= badgeShift
        self.setRect(
            self.baseX + s.hCellPadding - penWidth, yPos,
            self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth, height)
        self.scene.addItem(self)
        self.canvas.scopeRectangle = self

        # Draw badges
        # The scope badges do not use the RHS edge, they all are drawn from the
        # left edge so there is no need in the last parameter which is a
        # min width
        self.aboveBadges.draw(self.scene, s,
                              self.baseX, self.baseY, None)

        # Draw a horizontal connector if needed
        if self._connector is None:
            afterLoop = self.kind == CellElement.ELSE_SCOPE and self.__followLoop()
            if self.kind == CellElement.EXCEPT_SCOPE or afterLoop:
                parentCanvas = self.canvas.canvas
                cellToTheLeft = parentCanvas.cells[
                    self.canvas.addr[1]][self.canvas.addr[0] - 1]
                if cellToTheLeft.kind == CellElement.SIDE_COMMENT:
                    cellToTheLeft = parentCanvas.cells[
                        self.canvas.addr[1]][self.canvas.addr[0] - 2]

                yPos = self.baseY + s.vCellPadding + self.aboveBadges.height / 2

                cellToTheLeft = cellToTheLeft.cells[0][0]
                startXPos = cellToTheLeft.baseX + s.hCellPadding + cellToTheLeft.aboveBadges[0].width

                if afterLoop:
                    startXPos -= s.loopHeaderPadding

                self._connector = Connector(
                    self.canvas,
                    startXPos,
                    yPos,
                    self.baseX + s.hCellPadding - s.boxLineWidth,
                    yPos)
                self._connector.penStyle = Qt.DotLine
                self.scene.addItem(self._connector)

                cellToTheLeft.aboveBadges.raizeAllButFirst()

        if hasattr(self.scene.parent(), "updateNavigationToolbar"):
            self.__navBarUpdate = self.scene.parent().updateNavigationToolbar
            self.setAcceptHoverEvents(True)

        if self.kind in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]:
            self.__calcPolygon()

    def __calcPolygon(self):
        """Calculates the polygon for loops"""
        s = self.canvas.settings
        yTopPos = self.baseY + s.vCellPadding
        if self.aboveBadges.hasAny():
            yTopPos += self.aboveBadges.height + s.badgeToScopeVPadding

        cellBelow = self.canvas.cells[self.addr[1] + 1][self.addr[0]]
        halfDeclHeight = (cellBelow.height + s.scopeRectRadius) / 2

        self.x1 = self.baseX + s.hCellPadding + s.loopHeaderPadding
        self.y1 = yTopPos + halfDeclHeight
        self.x2 = self.x1 + s.ifWidth
        self.y2 = self.y1 - halfDeclHeight
        self.x4 = self.baseX + self.canvas.minWidth - s.hCellPadding - s.loopHeaderPadding
        self.y4 = self.y1
        self.x3 = self.x4 - s.ifWidth
        self.y3 = self.y2
        self.x5 = self.x3
        self.y5 = self.y4 + halfDeclHeight
        self.x6 = self.x2
        self.y6 = self.y5

    def __drawDeclaration(self):
        """Draws the declaration item"""
        s = self.canvas.settings
        penWidth = s.selectPenWidth - 1
        self.setRect(
            self.baseX - s.scopeRectRadius - penWidth,
            self.baseY - s.scopeRectRadius - penWidth,
            self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth,
            self.height + s.scopeRectRadius + penWidth)
        self.scene.addItem(self)

    def __drawDocstring(self):
        """Draws the docstring item"""
        s = self.canvas.settings
        penWidth = s.selectPenWidth - 1
        self.setRect(
            self.baseX - s.scopeRectRadius - penWidth,
            self.baseY - penWidth,
            self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth,
            self.height + 2 * penWidth)
        self.scene.addItem(self)

    def draw(self, scene, baseX, baseY):
        """Draws a scope"""
        self.baseX = baseX
        self.baseY = baseY
        self.scene = scene

        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.__drawTopLeft()
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.__drawDeclaration()
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.__drawDocstring()

    def __paintTopLeft(self, painter):
        """Paints the scope rectangle"""
        s = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        yPos = self.baseY + s.vCellPadding
        height = self.canvas.minHeight - 2 * s.vCellPadding
        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + s.badgeToScopeVPadding
            yPos += badgeShift
            height -= badgeShift

        if self.kind in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]:
            cellBelow = self.canvas.cells[self.addr[1] + 1][self.addr[0]]
            halfDeclHeight = (cellBelow.height + s.scopeRectRadius) / 2
            yPos += halfDeclHeight
            height -= halfDeclHeight

        painter.drawRoundedRect(self.baseX + s.hCellPadding,
                                yPos,
                                self.canvas.minWidth - 2 * s.hCellPadding,
                                height,
                                s.scopeRectRadius, s.scopeRectRadius)

        if self.kind in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]:
            # Brush
            if self.kind == CellElement.FOR_SCOPE:
                painter.setBrush(QBrush(s.forScopeHeaderBGColor))
            else:
                painter.setBrush(QBrush(s.whileScopeHeaderBGColor))

            # Pen, if not selected
            if not self.isSelected():
                if self.kind == CellElement.FOR_SCOPE:
                    pen = QPen(QColor(s.forScopeHeaderBorderColor))
                    pen.setWidth(s.forScopeHeaderPenWidth)
                else:
                    pen = QPen(QColor(s.whileScopeHeaderBorderColor))
                    pen.setWidth(s.whileScopeHeaderPenWidth)
                painter.setPen(pen)

            painter.drawPolygon(
                QPointF(self.x1, self.y1), QPointF(self.x2, self.y2),
                QPointF(self.x3, self.y3), QPointF(self.x4, self.y4),
                QPointF(self.x5, self.y5), QPointF(self.x6, self.y6))

    def __paintDeclaration(self, painter):
        """Paints the scope header"""
        s = self.canvas.settings
        canvasLeft = self.baseX - s.scopeRectRadius
        canvasTop = self.baseY - s.scopeRectRadius

        row = self.addr[1] - 1
        column = self.addr[0] - 1
        topLeftCell = self.canvas.cells[row][column]

        if self.kind not in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]:
            painter.setBrush(QBrush(self.bgColor))

            pen = QPen(self.borderColor)
            pen.setWidth(s.boxLineWidth)
            painter.setPen(pen)

            # If the scope is selected then the line may need to be shorter
            # to avoid covering the outline
            correction = 0.0
            if topLeftCell.isSelected():
                correction = s.selectPenWidth - 1
            painter.drawLine(canvasLeft + correction, self.baseY + self.height,
                             canvasLeft + self.canvas.minWidth -
                             2 * s.hCellPadding - correction,
                             self.baseY + self.height)

        pen = QPen(self.fgColor)
        painter.setFont(s.monoFont)
        painter.setPen(pen)

        if self.kind in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]:
            availWidth = topLeftCell.x3 - topLeftCell.x2
            textWidth = self.textRect.width() + 2 * s.hTextPadding
            textShift = (availWidth - textWidth) / 2
            painter.drawText(topLeftCell.x2 + s.hTextPadding + textShift,
                             canvasTop + s.vHeaderPadding,
                             self.textRect.width(), self.textRect.height(),
                             Qt.AlignLeft | Qt.AlignVCenter, self.text)
        else:
            painter.drawText(canvasLeft + s.hHeaderPadding,
                             canvasTop + s.vHeaderPadding,
                             self.textRect.width(), self.textRect.height(),
                             Qt.AlignLeft, self.text)

    def __paintDocstring(self, painter):
        """Paints the docstring"""
        s = self.canvas.settings
        painter.setBrush(QBrush(self.bgColor))

        canvasLeft = self.baseX - s.scopeRectRadius

        if self.isSelected():
            selectPen = QPen(s.selectColor)
            selectPen.setWidth(s.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
            painter.drawRect(canvasLeft, self.baseY,
                             self.canvas.minWidth - 2 * s.hCellPadding,
                             self.height)
        else:
            # If the scope is selected then the line may need to be shorter
            # to avoid covering the outline
            row = self.addr[1] - 2
            column = self.addr[0] - 1
            correction = 0.0
            if self.canvas.cells[row][column].isSelected():
                correction = s.selectPenWidth - 1

            # The background could also be custom
            pen = QPen(self.bgColor)
            pen.setWidth(s.boxLineWidth)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)

            dsCorr = float(s.boxLineWidth)
            if self.canvas.cells[row][column].isSelected():
                dsCorr = float(s.selectPenWidth) / 2.0 + \
                    float(s.boxLineWidth) / 2.0
            painter.drawRect(float(canvasLeft) + dsCorr,
                             self.baseY + s.boxLineWidth,
                             float(self.canvas.minWidth) -
                             2.0 * float(s.hCellPadding) - 2.0 * dsCorr,
                             self.height - 2 * s.boxLineWidth)

            pen = QPen(self.borderColor)
            pen.setWidth(s.boxLineWidth)
            painter.setPen(pen)
            painter.drawLine(canvasLeft + correction,
                             self.baseY + self.height,
                             canvasLeft + self.canvas.minWidth -
                             2 * s.hCellPadding - correction,
                             self.baseY + self.height)

        pen = QPen(self.fgColor)
        painter.setFont(s.monoFont)
        painter.setPen(pen)
        painter.drawText(canvasLeft + s.hHeaderPadding,
                         self.baseY + s.vHeaderPadding,
                         self.canvas.width - 2 * s.hHeaderPadding,
                         self.height - 2 * s.vHeaderPadding,
                         Qt.AlignLeft, self.text)

    def paint(self, painter, option, widget):
        """Draws the corresponding scope element"""
        del option
        del widget

        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.__paintTopLeft(painter)
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.__paintDeclaration(painter)
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.__paintDocstring(painter)

    def hoverEnterEvent(self, event):
        """Handling mouse enter event"""
        del event
        if self.__navBarUpdate:
            self.__navBarUpdate(self.getCanvasTooltip())

    def hoverLeaveEvent(self, event):
        """Handling mouse enter event"""
        del event
        # if self.__navBarUpdate:
        #     self.__navBarUpdate("")

    def __str__(self):
        """Debugging support"""
        return CellElement.__str__(self) + \
               "(" + scopeCellElementToString(self.subKind) + ")"

    def isComment(self):
        """True if it is a comment"""
        return False

    def isDocstring(self):
        """True if it is a docstring"""
        return self.subKind == self.DOCSTRING

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self.subKind == self.DOCSTRING:
            CellElement.mouseDoubleClickEvent(
                self, event, pos=self.ref.docstring.body.beginPos)
        elif self.subKind == self.DECLARATION:
            if self.kind == CellElement.FILE_SCOPE:
                CellElement.mouseDoubleClickEvent(
                    self, event, line=1, pos=1)
            else:
                CellElement.mouseDoubleClickEvent(
                    self, event, line=self.ref.body.beginLine,
                    pos=self.ref.body.beginPos)

    def getTopLeftItem(self):
        """Provides a top left corner item"""
        if self.subKind == self.DECLARATION:
            # The scope is at (x-1, y-1) location
            column = self.addr[0] - 1
            row = self.addr[1] - 1
            return self.canvas.cells[row][column]
        raise Exception("Logical error: the getTopLeftItem() is designed "
                        "to be called for the DECLARATION only")

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        if self.subKind == self.DOCSTRING:
            return distance(absPos, self.ref.docstring.begin,
                            self.ref.docstring.end)
        if self.subKind == self.DECLARATION:
            if self.kind == CellElement.FILE_SCOPE:
                dist = maxsize
                if self.ref.encodingLine:
                    dist = min(dist, distance(absPos,
                                              self.ref.encodingLine.begin,
                                              self.ref.encodingLine.end))
                if self.ref.bangLine:
                    dist = min(dist, distance(absPos,
                                              self.ref.bangLine.begin,
                                              self.ref.bangLine.end))
                return dist
            # Not a file scope
            return distance(absPos, self.ref.body.begin,
                            self.ref.body.end)
        return maxsize

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        if self.subKind == self.DOCSTRING:
            return distance(line, self.ref.docstring.beginLine,
                            self.ref.docstring.endLine)
        if self.subKind == self.DECLARATION:
            if self.kind == CellElement.FILE_SCOPE:
                dist = maxsize
                if self.ref.encodingLine:
                    dist = min(dist, distance(line,
                                              self.ref.encodingLine.beginLine,
                                              self.ref.encodingLine.endLine))
                if self.ref.bangLine:
                    dist = min(dist, distance(line,
                                              self.ref.bangLine.beginLine,
                                              self.ref.bangLine.endLine))
                return dist
            # Not a file scope
            return distance(line, self.ref.body.beginLine,
                            self.ref.body.endLine)
        return maxsize

    def getFirstLine(self):
        """Provides the first line"""
        if self.isDocstring():
            line = maxsize
            if self.ref.docstring.leadingCMLComments:
                line = CMLVersion.getFirstLine(self.ref.leadingCMLComments)
            if self.ref.docstring.leadingComment:
                if self.ref.docstring.leadingComment.parts:
                    line = min(
                        self.ref.docstring.leadingComment.parts[0].beginLine,
                        line)
            return min(self.ref.docstring.beginLine, line)
        return CellElement.getFirstLine(self)

    def getTooltipSuffix(self):
        """Provides the selection tooltip suffix"""
        if self.subKind == self.TOP_LEFT:
            return ' at ' + CellElement.getLinesSuffix(self.getLineRange())
        if self.subKind == self.DOCSTRING:
            return ' docstring at ' + \
                CellElement.getLinesSuffix(self.getLineRange())
        return ' scope (' + scopeCellElementToString(self.subKind) + ')'

    def needDeclaration(self):
        """Helps for the canvas layout. Some items don't need a declaration"""
        if self.kind in [self.ELSE_SCOPE, self.FINALLY_SCOPE, self.TRY_SCOPE]:
            return False
        if self.kind == self.EXCEPT_SCOPE:
            return self.ref.clause is not None
        return True

    def getColors(self):
        """Custom colors for docstrings"""
        if self.subKind == self.DOCSTRING:
            s = self.canvas.settings
            colorMixin = ColorMixin(self.ref, s.docstringBGColor,
                                    s.docstringFGColor,
                                    s.docstringBorderColor,
                                    isDocstring=True)
            return colorMixin.getColors()
        return ColorMixin.getColors(self)

    def appendSpacerAndBadge(self, groupSpacerAdded, badge):
        s = self.canvas.settings
        if groupSpacerAdded:
            self.aboveBadges.append(AboveBadgesSpacer(s.badgeToBadgeHSpacing))
        else:
            self.aboveBadges.append(AboveBadgesSpacer(s.badgeGroupSpacing))
        self.aboveBadges.append(badge)


_scopeCellElementToString = {
    ScopeCellElement.TOP_LEFT: "TOP_LEFT",
    ScopeCellElement.DECLARATION: "DECLARATION",
    ScopeCellElement.DOCSTRING: "DOCSTRING"}


def scopeCellElementToString(kind):
    """Provides a string representation of a element kind"""
    return _scopeCellElementToString[kind]


class FileScopeCell(ScopeCellElement):

    """Represents a file scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.fileScopeBGColor,
                                  canvas.settings.fileScopeFGColor,
                                  canvas.settings.fileScopeBorderColor)
        self.kind = CellElement.FILE_SCOPE

    def render(self):
        """Renders the file scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, 'module'))
            s = self.canvas.settings
            groupSpacerAdded = False
            if self.ref.docstring and s.hidedocstrings and not s.noDocstring:
                self.appendSpacerAndBadge(groupSpacerAdded,
                                          DocstringBadgeItem(self, 'doc'))
                groupSpacerAdded = True
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            if self.ref.body is None:
                # Special case: the buffer is empty so no body exists
                return [0, 0]
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            if self.ref.body is None:
                # Special case: the buffer is empty so no body exists
                return [0, 0]
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getAbsPosRange()
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides a file scope selected tooltip"""
        return 'Module' + self.getTooltipSuffix()


class FunctionScopeCell(ScopeCellElement):

    """Represents a function scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.funcScopeBGColor,
                                  canvas.settings.funcScopeFGColor,
                                  canvas.settings.funcScopeBorderColor)
        self.kind = CellElement.FUNC_SCOPE

    def render(self):
        """Renders the function scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, 'def'))
            s = self.canvas.settings
            groupSpacerAdded = False
            if self.ref.docstring and s.hidedocstrings and not s.noDocstring:
                self.appendSpacerAndBadge(groupSpacerAdded,
                                          DocstringBadgeItem(self, 'doc'))
                groupSpacerAdded = True
            if self.ref.decorators and s.hidedecors and not s.noDecor:
                for index, _ in enumerate(self.ref.decorators):
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              ScopeDecorBadgeItem(self, index))
                    groupSpacerAdded = True
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getAbsPosRange()
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides a selected function block tooltip"""
        return 'Function' + self.getTooltipSuffix()


class ClassScopeCell(ScopeCellElement):

    """Represents a class scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.classScopeBGColor,
                                  canvas.settings.classScopeFGColor,
                                  canvas.settings.classScopeBorderColor)
        self.kind = CellElement.CLASS_SCOPE

    def render(self):
        """Renders the class scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, 'class'))
            s = self.canvas.settings
            groupSpacerAdded = False
            if self.ref.docstring and s.hidedocstrings and not s.noDocstring:
                self.appendSpacerAndBadge(groupSpacerAdded,
                                          DocstringBadgeItem(self, 'doc'))
                groupSpacerAdded = True
            if self.ref.decorators and s.hidedecors and not s.noDecor:
                for index, _ in enumerate(self.ref.decorators):
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              ScopeDecorBadgeItem(self, index))
                    groupSpacerAdded = True
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getAbsPosRange()
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides the selection tooltip"""
        return 'Class' + self.getTooltipSuffix()


class ForScopeCell(ScopeCellElement):

    """Represents a for-loop scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.forScopeBGColor,
                                  canvas.settings.forScopeFGColor,
                                  canvas.settings.forScopeBorderColor)
        self.kind = CellElement.FOR_SCOPE

    def render(self):
        """Renders the for-loop scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "for"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides a selected for block tooltip"""
        return 'For loop' + self.getTooltipSuffix()


class WhileScopeCell(ScopeCellElement):

    """Represents a while-loop scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.whileScopeBGColor,
                                  canvas.settings.whileScopeFGColor,
                                  canvas.settings.whileScopeBorderColor)
        self.kind = CellElement.WHILE_SCOPE

    def render(self):
        """Renders the while-loop scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "while"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides the selected while scope element tooltip"""
        return 'While loop' + self.getTooltipSuffix()


class TryScopeCell(ScopeCellElement):

    """Represents a try-except scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.tryScopeBGColor,
                                  canvas.settings.tryScopeFGColor,
                                  canvas.settings.tryScopeBorderColor)
        self.kind = CellElement.TRY_SCOPE

    def render(self):
        """Renders the try scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "try"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
            if s.hideexcepts:
                for index, _ in enumerate(self.ref.exceptParts):
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              ExceptBadgeItem(self, index))
                    groupSpacerAdded = True
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            beginLine = self.ref.body.beginLine
            _, endLine = self.ref.suite[-1].getLineRange()
            return [beginLine, endLine]
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        begin = self.ref.body.begin
        _, end = self.ref.suite[-1].getAbsPosRange()
        return [begin, end]

    def getSelectTooltip(self):
        """Provides the selected try block tooltip"""
        return 'Try' + self.getTooltipSuffix()


class WithScopeCell(ScopeCellElement):

    """Represents a with scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.withScopeBGColor,
                                  canvas.settings.withScopeFGColor,
                                  canvas.settings.withScopeBorderColor)
        self.kind = CellElement.WITH_SCOPE

    def render(self):
        """Renders the with block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "with"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides the selected with block tooltip"""
        return 'With' + self.getTooltipSuffix()


class ElseScopeCell(ScopeCellElement):

    """Represents an else scope element"""

    FOR_STATEMENT = 0
    WHILE_STATEMENT = 1
    TRY_STATEMENT = 2

    def __init__(self, ref, canvas, x, y, subKind, statement):
        if statement == self.FOR_STATEMENT:
            bgColor = canvas.settings.forElseScopeBGColor
            fgColor = canvas.settings.forElseScopeFGColor
            borderColor = canvas.settings.forElseScopeBorderColor
        elif statement == self.WHILE_STATEMENT:
            bgColor = canvas.settings.whileElseScopeBGColor
            fgColor = canvas.settings.whileElseScopeFGColor
            borderColor = canvas.settings.whileElseScopeBorderColor
        else:
            # TRY_STATEMENT
            bgColor = canvas.settings.tryElseScopeBGColor
            fgColor = canvas.settings.tryElseScopeFGColor
            borderColor = canvas.settings.tryElseScopeBorderColor
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  bgColor, fgColor, borderColor)
        self.kind = CellElement.ELSE_SCOPE
        self.statement = statement
        self.after = self

    def render(self):
        """Renders the else block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "else"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides the selection tooltip"""
        return 'Else' + self.getTooltipSuffix()


class ForElseScopeCell(ElseScopeCell):

    """Else scope which is bound to a for loop"""

    def __init__(self, ref, canvas, x, y, subKind):
        ElseScopeCell.__init__(self, ref, canvas, x, y, subKind,
                               ElseScopeCell.FOR_STATEMENT)


class WhileElseScopeCell(ElseScopeCell):

    """Else scope which is bound to a while loop"""

    def __init__(self, ref, canvas, x, y, subKind):
        ElseScopeCell.__init__(self, ref, canvas, x, y, subKind,
                               ElseScopeCell.WHILE_STATEMENT)


class TryElseScopeCell(ElseScopeCell):

    """Else scope which is bound to a try block"""

    def __init__(self, ref, canvas, x, y, subKind):
        ElseScopeCell.__init__(self, ref, canvas, x, y, subKind,
                               ElseScopeCell.TRY_STATEMENT)


class ExceptScopeCell(ScopeCellElement):

    """Represents an except scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.exceptScopeBGColor,
                                  canvas.settings.exceptScopeFGColor,
                                  canvas.settings.exceptScopeBorderColor)
        self.kind = CellElement.EXCEPT_SCOPE

    def render(self):
        """Renders the except block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "except"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides the selection tooltip"""
        return 'Except' + self.getTooltipSuffix()


class FinallyScopeCell(ScopeCellElement):

    """Represents a finally scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.finallyScopeBGColor,
                                  canvas.settings.finallyScopeFGColor,
                                  canvas.settings.finallyScopeBorderColor)
        self.kind = CellElement.FINALLY_SCOPE

    def render(self):
        """Renders the finally block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.aboveBadges.append(BadgeItem(self, "finally"))
            s = self.canvas.settings
            groupSpacerAdded = False
            if s.hidecomments and not s.noComment:
                leadingDoc = getDocComment(self.ref.leadingCMLComments)
                if leadingDoc:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              DocLinkBadgeItem(self))
                    groupSpacerAdded = True
                if self.ref.leadingComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, False))
                    groupSpacerAdded = True
                if self.ref.sideComment:
                    self.appendSpacerAndBadge(groupSpacerAdded,
                                              CommentBadgeItem(self, True))
                    groupSpacerAdded = True
        return self.renderCell()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides a tooltip for the selected finally block"""
        return 'Finally' + self.getTooltipSuffix()

