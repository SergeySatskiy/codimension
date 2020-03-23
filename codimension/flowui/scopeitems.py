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
from ui.qt import Qt, QPen, QBrush, QGraphicsRectItem, QGraphicsItem
from .auxitems import BadgeItem, Connector, HSpacerCell, VSpacerCell, SpacerCell
from .cellelement import CellElement
from .routines import distance, getNoCellCommentBoxPath
from .cml import CMLVersion
from .colormixin import ColorMixin
from .textmixin import TextMixin
from .iconmixin import IconMixin


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


class ScopeCellElement(CellElement, TextMixin, ColorMixin, IconMixin,
                       QGraphicsRectItem):

    """Base class for the scope items"""

    TOP_LEFT = 0
    DECLARATION = 1
    COMMENT = 2
    DOCSTRING = 3

    def __init__(self, ref, canvas, x, y, subKind,
                 bgColor, fgColor, borderColor):
        isDocstring = subKind == ScopeCellElement.DOCSTRING
        if subKind == ScopeCellElement.DOCSTRING:
            bgColor = canvas.settings.docstringBGColor
            fgColor = canvas.settings.docstringFGColor
            # Border color is borrowed from the scope for docstrings

        commentIconFileName = None
        if subKind == ScopeCellElement.COMMENT:
            if canvas.settings.hidecomments:
                commentIconFileName = 'hiddencomment.svg'

        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, bgColor, fgColor, borderColor,
                            isDocstring=isDocstring)
        IconMixin.__init__(self, canvas, commentIconFileName)
        QGraphicsRectItem.__init__(self)

        self.subKind = subKind
        self.badgeItem = None
        self.__docBadge = None
        self.__navBarUpdate = None
        self._connector = None
        self._topHalfConnector = None
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
        self.minWidth = s.scopeRectRadius + s.hCellPadding

    def __renderDeclaration(self):
        """Renders the scope declaration"""
        # The declaration location uses a bit of the top cell space
        # to make the view more compact
        s = self.canvas.settings
        self.setupText(self)

        badgeItem = self.canvas.cells[
            self.addr[1] - 1][self.addr[0] - 1].badgeItem

        self.minHeight = self.textRect.height() + \
                         2 * s.vHeaderPadding - s.scopeRectRadius
        headerRectWidth = self.textRect.width()
        if badgeItem:
            headerRectWidth = max(headerRectWidth, badgeItem.width)
        self.minWidth = headerRectWidth + s.hHeaderPadding - s.scopeRectRadius
        if badgeItem:
            if badgeItem.withinHeader():
                self.minWidth = badgeItem.width + \
                                s.hHeaderPadding - s.scopeRectRadius
        if hasattr(self.ref, "sideComment"):
            if self.ref.sideComment:
                self.minHeight += 2 * s.vTextPadding
                self.minWidth += s.hCellPadding
            else:
                self.minHeight += s.vTextPadding
                self.minWidth += s.hHeaderPadding
        else:
            self.minWidth += s.hHeaderPadding
        self.minWidth = max(self.minWidth, s.minWidth)

    def __renderComment(self):
        """Renders the scope declaration"""
        s = self.canvas.settings
        self.setupText(self, customText=self.getSideComment(),
                       customReplacement='')
        if s.hidecomments:
            # Visually the icon looks a bit too big so reduce the size to 80%
            self.iconItem.setIconHeight(self.iconItem.iconHeight() * 0.8)

            self.minHeight = self.iconItem.iconHeight() + \
                2 * (s.vHeaderPadding + s.vHiddenCommentPadding) - \
                s.scopeRectRadius
            self.minWidth = s.hCellPadding + self.iconItem.iconWidth() + \
                2 * s.hHiddenCommentPadding + s.hHeaderPadding - \
                s.scopeRectRadius
        else:
            self.minHeight = self.textRect.height() + \
                2 * (s.vHeaderPadding + s.vTextPadding) - \
                s.scopeRectRadius
            self.minWidth = s.hCellPadding + s.hTextPadding + \
                self.textRect.width() + s.hTextPadding + \
                s.hHeaderPadding - s.scopeRectRadius

    def __renderDocstring(self):
        """Renders the scope docstring"""
        s = self.canvas.settings
        self.setupText(self, customText=self.ref.docstring.getDisplayValue(),
                       customReplacement='')

        if s.hidedocstrings:
            self.__docBadge = BadgeItem(self, 'doc')
            self.__docBadge.setToolTip('<pre>' + escape(self.text) + '</pre>')
            self.minHeight = self.__docBadge.height + 2 * (s.selectPenWidth - 1)
            self.minWidth = 2 * (s.hHeaderPadding - s.scopeRectRadius)
        else:
            self.minHeight = self.textRect.height() + 2 * s.vHeaderPadding
            self.minWidth = self.textRect.width() + 2 * (s.hHeaderPadding -
                                                         s.scopeRectRadius)

    def renderCell(self):
        """Provides rendering for the scope elements"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.__renderTopLeft()
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.__renderDeclaration()
        elif self.subKind == ScopeCellElement.COMMENT:
            self.__renderComment()
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
            if cells[row][column].kind == CellElement.VCANVAS:
                return cells[row][column].cells[0][0].kind \
                    in [CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE]
            return False
        except:
            return False

    def __needConnector(self):
        """True if a connector is required"""
        if self.kind in [CellElement.FOR_SCOPE, CellElement.DECOR_SCOPE,
                         CellElement.WHILE_SCOPE, CellElement.FUNC_SCOPE,
                         CellElement.CLASS_SCOPE, CellElement.WITH_SCOPE,
                         CellElement.FINALLY_SCOPE, CellElement.TRY_SCOPE]:
            return True
        if self.kind == CellElement.ELSE_SCOPE:
            return self.statement == ElseScopeCell.TRY_STATEMENT
        return False

    def __needTopHalfConnector(self):
        """True if a half of a connector is needed"""
        if self.kind in [CellElement.ELSE_SCOPE, CellElement.EXCEPT_SCOPE]:
            try:
                parentCanvas = self.canvas.canvas
                cellToTheTop = parentCanvas.cells[
                    self.canvas.addr[1] - 1][self.canvas.addr[0]]
                return cellToTheTop.needConnector
            except:
                pass
        return False

    def __drawTopLeft(self):
        """Draws the top left element of a scope"""
        s = self.canvas.settings

        # Draw connector if needed
        if self.__needConnector() and self._connector is None:
            self._connector = Connector(
                self.canvas, self.baseX + s.mainLine,
                self.baseY, self.baseX + s.mainLine,
                self.baseY + self.canvas.height)
            self.scene.addItem(self._connector)
        if self.__needTopHalfConnector() and self._topHalfConnector is None:
            self._topHalfConnector = Connector(
                self.canvas, self.baseX + s.mainLine, self.baseY,
                self.baseX + s.mainLine, self.baseY + self.canvas.height / 2)
            self.scene.addItem(self._topHalfConnector)

        # Draw the scope rounded rectangle when we see the top left corner
        penWidth = s.selectPenWidth - 1
        self.setRect(
            self.baseX + s.hCellPadding - penWidth,
            self.baseY + s.vCellPadding - penWidth,
            self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth,
            self.canvas.minHeight - 2 * s.vCellPadding + 2 * penWidth)
        self.scene.addItem(self)
        self.canvas.scopeRectangle = self
        if self.badgeItem:
            if self.badgeItem.withinHeader():
                headerHeight = self.canvas.cells[
                    self.addr[1] + 1][self.addr[0]].height
                fullHeight = headerHeight + s.scopeRectRadius
                self.badgeItem.moveTo(
                    self.baseX + s.hCellPadding + s.badgeShift,
                    self.baseY + s.vCellPadding + fullHeight / 2 -
                    self.badgeItem.height / 2)
            else:
                self.badgeItem.moveTo(
                    self.baseX + s.hCellPadding + s.badgeShift,
                    self.baseY + s.vCellPadding - self.badgeItem.height / 2)
            self.scene.addItem(self.badgeItem)
        # Draw a horizontal connector if needed
        if self._connector is None:
            if self.kind == CellElement.EXCEPT_SCOPE or (
                    self.kind == CellElement.ELSE_SCOPE and
                    self.__followLoop()):
                parentCanvas = self.canvas.canvas
                cellToTheLeft = parentCanvas.cells[
                    self.canvas.addr[1]][self.canvas.addr[0] - 1]
                self._connector = Connector(
                    self.canvas,
                    cellToTheLeft.baseX + cellToTheLeft.minWidth -
                    s.hCellPadding + s.boxLineWidth,
                    self.baseY + 2 * s.vCellPadding,
                    self.baseX + s.hCellPadding - s.boxLineWidth,
                    self.baseY + 2 * s.vCellPadding)
                self._connector.penStyle = Qt.DotLine
                self.scene.addItem(self._connector)

        if hasattr(self.scene.parent(), "updateNavigationToolbar"):
            self.__navBarUpdate = self.scene.parent().updateNavigationToolbar
            self.setAcceptHoverEvents(True)

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

    def __drawComment(self):
        """Draws the comment item"""
        s = self.canvas.settings
        canvasTop = self.baseY - s.scopeRectRadius
        movedBaseX = self.canvas.baseX + self.canvas.minWidth - \
            self.width - s.scopeRectRadius - s.vHeaderPadding
        penWidth = s.selectPenWidth - 1
        if s.hidecomments:
            self.setRect(
                movedBaseX + s.hHeaderPadding - penWidth,
                canvasTop + s.vHeaderPadding - penWidth,
                self.iconItem.iconWidth() +
                2 * (s.hHiddenCommentPadding + penWidth),
                self.iconItem.iconHeight() +
                2 * (s.vHiddenCommentPadding + penWidth))
            self.iconItem.setPos(
                movedBaseX + s.hHeaderPadding + s.hHiddenCommentPadding,
                canvasTop + s.vHeaderPadding + s.vHiddenCommentPadding)
            self.iconItem.setToolTip(self.text)

            self.scene.addItem(self)
            self.scene.addItem(self.iconItem)
        else:
            self.setRect(
                movedBaseX + s.hHeaderPadding - penWidth,
                canvasTop + s.vHeaderPadding - penWidth,
                self.textRect.width() +
                2 * s.hTextPadding + 2 * penWidth,
                self.textRect.height() +
                2 * s.vTextPadding + 2 * penWidth)
            self.__sideCommentPath = getNoCellCommentBoxPath(
                movedBaseX + s.hHeaderPadding,
                canvasTop + s.vHeaderPadding,
                self.textRect.width() + 2 * s.hTextPadding,
                self.textRect.height() + 2 * s.vTextPadding,
                s.commentCorner)
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
        if s.hidedocstrings:
            self.scene.addItem(self.__docBadge)
            self.__docBadge.moveTo(
                self.baseX - s.scopeRectRadius + penWidth,
                self.baseY + penWidth)

    def draw(self, scene, baseX, baseY):
        """Draws a scope"""
        self.baseX = baseX
        self.baseY = baseY
        self.scene = scene

        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.__drawTopLeft()
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.__drawDeclaration()
        elif self.subKind == ScopeCellElement.COMMENT:
            self.__drawComment()
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.__drawDocstring()

    def __paintTopLeft(self, painter):
        """Paints the scope rectangle"""
        s = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))
        painter.drawRoundedRect(self.baseX + s.hCellPadding,
                                self.baseY + s.vCellPadding,
                                self.canvas.minWidth - 2 * s.hCellPadding,
                                self.canvas.minHeight - 2 * s.vCellPadding,
                                s.scopeRectRadius, s.scopeRectRadius)

    def __paintDeclaration(self, painter):
        """Paints the scope header"""
        s = self.canvas.settings
        painter.setBrush(QBrush(self.bgColor))
        pen = QPen(self.fgColor)
        painter.setFont(s.monoFont)
        painter.setPen(pen)
        canvasLeft = self.baseX - s.scopeRectRadius
        canvasTop = self.baseY - s.scopeRectRadius
        textHeight = self.textRect.height()
        yShift = 0
        if hasattr(self.ref, 'sideComment'):
            yShift = s.vTextPadding
        painter.drawText(canvasLeft + s.hHeaderPadding,
                         canvasTop + s.vHeaderPadding + yShift,
                         self.textRect.width(), textHeight,
                         Qt.AlignLeft, self.text)

        pen = QPen(self.borderColor)
        pen.setWidth(s.boxLineWidth)
        painter.setPen(pen)

        # If the scope is selected then the line may need to be shorter
        # to avoid covering the outline
        row = self.addr[1] - 1
        column = self.addr[0] - 1
        correction = 0.0
        if self.canvas.cells[row][column].isSelected():
            correction = s.selectPenWidth - 1
        painter.drawLine(canvasLeft + correction, self.baseY + self.height,
                         canvasLeft + self.canvas.minWidth -
                         2 * s.hCellPadding - correction,
                         self.baseY + self.height)

    def __paintComment(self, painter):
        """Paints the side comment"""
        s = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(),
                                          s.commentBorderColor))
        painter.setBrush(QBrush(s.commentBGColor))

        canvasTop = self.baseY - s.scopeRectRadius
        # s.vHeaderPadding below is used intentionally: to have the same
        # spacing on top, bottom and right for the comment box
        movedBaseX = self.canvas.baseX + self.canvas.minWidth - \
            self.width - s.scopeRectRadius - s.vHeaderPadding

        if s.hidecomments:
            painter.drawRoundedRect(
                movedBaseX + s.hHeaderPadding,
                canvasTop + s.vHeaderPadding,
                self.iconItem.iconWidth() + 2 * s.hHiddenCommentPadding,
                self.iconItem.iconHeight() + 2 * s.vHiddenCommentPadding,
                s.hiddenCommentRectRadius, s.hiddenCommentRectRadius)
        else:
            painter.drawPath(self.__sideCommentPath)

            pen = QPen(s.commentFGColor)
            painter.setFont(s.monoFont)
            painter.setPen(pen)
            painter.drawText(
                movedBaseX + s.hHeaderPadding + s.hTextPadding,
                canvasTop + s.vHeaderPadding + s.vTextPadding,
                self.textRect.width(),
                self.textRect.height(),
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

        if not s.hidedocstrings:
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
        elif self.subKind == ScopeCellElement.COMMENT:
            self.__paintComment(painter)
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
        return self.subKind == self.COMMENT

    def isDocstring(self):
        """True if it is a docstring"""
        return self.subKind == self.DOCSTRING

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self.subKind == self.COMMENT:
            CellElement.mouseDoubleClickEvent(
                self, event, pos=self.ref.sideComment.beginPos)
        elif self.subKind == self.DOCSTRING:
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
        if self.subKind == self.COMMENT:
            return distance(absPos, self.ref.sideComment.begin,
                            self.ref.sideComment.end)
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
        if self.subKind == self.COMMENT:
            return distance(line, self.ref.sideComment.beginLine,
                            self.ref.sideComment.endLine)
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
        if self.subKind == self.COMMENT:
            return ' side comment at ' + \
                CellElement.getLinesSuffix(self.getLineRange())
        return ' scope (' + scopeCellElementToString(self.subKind) + ')'


_scopeCellElementToString = {
    ScopeCellElement.TOP_LEFT: "TOP_LEFT",
    ScopeCellElement.DECLARATION: "DECLARATION",
    ScopeCellElement.COMMENT: "COMMENT",
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
            self.badgeItem = BadgeItem(self, "module")
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
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the function
        if self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.name.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()

        # The comment may stop before the end of the arguments list
        linesAfter = self.ref.arguments.endLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the function scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "def")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getAbsPosRange()
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the class
        if self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.name.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()
        if self.ref.baseClasses is None:
            lastLine = self.ref.name.endLine
        else:
            lastLine = self.ref.baseClasses.endLine

        # The comment may stop before the end of the arguments list
        linesAfter = lastLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the class scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "class")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getAbsPosRange()
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the function
        if self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.iteration.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()

        # The comment may stop before the end of the arguments list
        linesAfter = self.ref.iteration.endLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the for-loop scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "for")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the function
        if self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.condition.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()

        # The comment may stop before the end of the arguments list
        linesAfter = self.ref.condition.endLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the while-loop scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "while")
        return self.renderCell()

    def getLineRange(self):
        """Provides the lineRange"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        return self.ref.sideComment.getDisplayValue()

    def render(self):
        """Renders the try scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "try")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            beginLine = self.ref.body.beginLine
            _, endLine = self.ref.suite[-1].getLineRange()
            return [beginLine, endLine]
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            begin = self.ref.body.begin
            _, end = self.ref.suite[-1].getAbsPosRange()
            return [begin, end]
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the function
        if self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.items.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()

        # The comment may stop before the end of the arguments list
        linesAfter = self.ref.items.endLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the with block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "with")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

    def getSelectTooltip(self):
        """Provides the selected with block tooltip"""
        return 'With' + self.getTooltipSuffix()


class DecoratorScopeCell(ScopeCellElement):

    """Represents a decorator scope element"""

    def __init__(self, ref, canvas, x, y, subKind):
        ScopeCellElement.__init__(self, ref, canvas, x, y, subKind,
                                  canvas.settings.decorScopeBGColor,
                                  canvas.settings.decorScopeFGColor,
                                  canvas.settings.decorScopeBorderColor)
        self.kind = CellElement.DECOR_SCOPE

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the function
        if self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.name.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()
        if self.ref.arguments is None:
            lastLine = self.ref.name.endLine
        else:
            lastLine = self.ref.arguments.endLine

        # The comment may stop before the end of the arguments list
        linesAfter = lastLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the decorator"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, " @ ")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

    def getSelectTooltip(self):
        """Provides the selected decorator tooltip"""
        return 'Decorator' + self.getTooltipSuffix()


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

    def getSideComment(self):
        """Provides a side comment"""
        return self.ref.sideComment.getDisplayValue()

    def render(self):
        """Renders the else block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "else")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides a side comment"""
        # The comment may start not at the first line of the except
        if self.ref.clause is None or self.canvas.settings.hidecomments:
            return self.ref.sideComment.getDisplayValue()

        linesBefore = self.ref.sideComment.beginLine - \
                      self.ref.clause.beginLine
        sideComment = '\n' * linesBefore + \
                      self.ref.sideComment.getDisplayValue()
        lastLine = self.ref.clause.endLine

        # The comment may stop before the end of the arguments list
        linesAfter = lastLine - self.ref.sideComment.endLine
        return sideComment + '\n' * linesAfter

    def render(self):
        """Renders the except block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "except")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

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

    def getSideComment(self):
        """Provides the side comment"""
        return self.ref.sideComment.getDisplayValue()

    def render(self):
        """Renders the finally block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.badgeItem = BadgeItem(self, "finally")
        return self.renderCell()

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getLineRange()
        return CellElement.getLineRange(self)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.COMMENT:
            return self.ref.sideComment.getAbsPosRange()
        return CellElement.getAbsPosRange(self)

    def getSelectTooltip(self):
        """Provides a tooltip for the selected finally block"""
        return 'Finally' + self.getTooltipSuffix()

