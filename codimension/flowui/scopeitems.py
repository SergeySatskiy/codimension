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

from sys import maxsize
import os.path
from cgi import escape
from ui.qt import Qt, QPen, QBrush, QGraphicsRectItem, QGraphicsItem
from utils.globals import GlobalData
from .auxitems import BadgeItem, Connector
from .items import CellElement
from .routines import distance, getNoCellCommentBoxPath, getHiddenCommentPath
from .cml import CMLVersion, CMLcc


class ScopeCellElement(CellElement):

    """Base class for the scope items"""

    UNKNOWN = -1
    TOP_LEFT = 0
    LEFT = 1
    BOTTOM_LEFT = 2
    DECLARATION = 3
    SIDE_COMMENT = 4
    DOCSTRING = 5
    TOP = 6
    BOTTOM = 7

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.subKind = self.UNKNOWN
        self.docstringText = None
        self._headerRect = None
        self._sideComment = None
        self._sideCommentRect = None
        self._badgeItem = None
        self.__navBarUpdate = None
        self._connector = None
        self.scene = None
        self.__sideCommentPath = None

        self.__bgColor = None
        self.__fgColor = None
        self.__borderColor = None

        # Will be initialized only for the TOP_LEFT item of the
        # ELSE_SCOPE, EXCEPT_SCOPE and FINALLY_SCOPE
        # It points to TRY, FOR and WHILE approprietely
        self.leaderRef = None

    def getDocstringText(self):
        """Provides the docstring text"""
        if self.docstringText is None:
            self.docstringText = self.ref.docstring.getDisplayValue()
            if self.canvas.settings.hidedocstrings:
                self.setToolTip('<pre>' + escape(self.docstringText) +
                                '</pre>')
                self.docstringText = ''
        return self.docstringText

    def _render(self):
        """Provides rendering for the scope elements"""
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = s.rectRadius + s.hCellPadding
            # The effect is nice but the CPU consumption becomes so high that
            # the diagram could hardly be scrolled ...
            # effect = QGraphicsDropShadowEffect()
            # effect.setBlurRadius( 5.0 )
            # effect.setOffset( 2.0, 2.0 )
            # effect.setColor( QColor( 180, 180, 180, 180 ) )
            # self.setGraphicsEffect( effect )
        elif self.subKind == ScopeCellElement.LEFT:
            self.minHeight = 0
            self.minWidth = s.rectRadius + s.hCellPadding
        elif self.subKind == ScopeCellElement.BOTTOM_LEFT:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = s.rectRadius + s.hCellPadding
        elif self.subKind == ScopeCellElement.TOP:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.BOTTOM:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.DECLARATION:
            # The declaration location uses a bit of the top cell space
            # to make the view more compact
            badgeItem = self.canvas.cells[
                self.addr[1] - 1][self.addr[0] - 1]._badgeItem

            self._headerRect = self.getBoundingRect(self._getText())
            self.minHeight = self._headerRect.height() + \
                             2 * s.vHeaderPadding - s.rectRadius
            w = self._headerRect.width()
            if badgeItem:
                w = max(w, badgeItem.width())
            self.minWidth = w + s.hHeaderPadding - s.rectRadius
            if badgeItem:
                if badgeItem.withinHeader():
                    self.minWidth = badgeItem.width() + \
                                    s.hHeaderPadding - s.rectRadius
            if hasattr( self.ref, "sideComment" ):
                if self.ref.sideComment:
                    self.minHeight += 2 * s.vTextPadding
                    self.minWidth += s.hCellPadding
                else:
                    self.minHeight += s.vTextPadding
                    self.minWidth += s.hHeaderPadding
            else:
                self.minWidth += s.hHeaderPadding
            self.minWidth = max(self.minWidth, s.minWidth)
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            self._sideCommentRect = self.getBoundingRect(
                self._getSideComment())
            if s.hidecomments:
                self.minHeight = self._sideCommentRect.height() + \
                    2 * (s.vHeaderPadding + s.vHiddenTextPadding) - \
                    s.rectRadius
                self.minWidth = s.hCellPadding + s.hHiddenTextPadding + \
                    self._sideCommentRect.width() + s.hHiddenTextPadding + \
                    s.hHeaderPadding - s.rectRadius
            else:
                self.minHeight = self._sideCommentRect.height() + \
                    2 * (s.vHeaderPadding + s.vTextPadding) - \
                    s.rectRadius
                self.minWidth = s.hCellPadding + s.hTextPadding + \
                    self._sideCommentRect.width() + s.hTextPadding + \
                    s.hHeaderPadding - s.rectRadius
        elif self.subKind == ScopeCellElement.DOCSTRING:
            docstringText = self.getDocstringText()
            if not s.hidedocstrings:
                rect = s.monoFontMetrics.boundingRect(0, 0, maxsize, maxsize, 0,
                                                      docstringText)
                self.minHeight = rect.height() + 2 * s.vHeaderPadding
                self.minWidth = rect.width() + 2 * (s.hHeaderPadding -
                                                    s.rectRadius)
            else:
                self.__docBadge = BadgeItem(self, 'doc')
                self.minHeight = self.__docBadge.height() + \
                    2 * (s.selectPenWidth - 1)
                self.minWidth = 2 * (s.hHeaderPadding - s.rectRadius)
        elif self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception("Unknown scope element")
        else:
            raise Exception("Unrecognized scope element: " +
                            str(self.subKind))

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

    def _draw(self, scene, baseX, baseY):
        """Draws a scope"""
        self.scene = scene
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            # Draw connector if needed
            if self.__needConnector() and self._connector is None:
                self._connector = Connector(s, baseX + s.mainLine, baseY,
                                            baseX + s.mainLine,
                                            baseY + self.canvas.height)
                scene.addItem(self._connector)

            # Draw the scope rounded rectangle when we see the top left corner
            penWidth = s.selectPenWidth - 1
            self.setRect(
                baseX + s.hCellPadding - penWidth,
                baseY + s.vCellPadding - penWidth,
                self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                self.canvas.minHeight - 2 * s.vCellPadding + 2 * penWidth)
            scene.addItem(self)
            self.canvas.scopeRectangle = self
            if self._badgeItem:
                if self._badgeItem.withinHeader():
                    headerHeight = self.canvas.cells[
                        self.addr[1] + 1][self.addr[0]].height
                    fullHeight = headerHeight + s.rectRadius
                    self._badgeItem.moveTo(
                        baseX + s.hCellPadding + s.rectRadius,
                        baseY + s.vCellPadding + fullHeight / 2 -
                        self._badgeItem.height() / 2)
                else:
                    self._badgeItem.moveTo(
                        baseX + s.hCellPadding + s.rectRadius,
                        baseY + s.vCellPadding - self._badgeItem.height() / 2)
                scene.addItem(self._badgeItem)
            # Draw a horizontal connector if needed
            if self._connector is None:
                if self.kind == CellElement.EXCEPT_SCOPE or (
                   self.kind == CellElement.ELSE_SCOPE and
                   self.__followLoop()):
                    parentCanvas = self.canvas.canvas
                    cellToTheLeft = parentCanvas.cells[
                        self.canvas.addr[1]][self.canvas.addr[0] - 1]
                    self._connector = Connector(
                        s,
                        cellToTheLeft.baseX + cellToTheLeft.minWidth -
                        s.hCellPadding + s.lineWidth,
                        baseY + 2 * s.vCellPadding,
                        baseX + s.hCellPadding - s.lineWidth,
                        baseY + 2 * s.vCellPadding)
                    self._connector.penStyle = Qt.DotLine
                    scene.addItem(self._connector)

            if hasattr(scene.parent(), "updateNavigationToolbar"):
                self.__navBarUpdate = scene.parent().updateNavigationToolbar
                self.setAcceptHoverEvents(True)

        elif self.subKind == ScopeCellElement.DECLARATION:
            yShift = 0
            if hasattr(self.ref, "sideComment"):
                yShift = s.vTextPadding
            penWidth = s.selectPenWidth - 1
            self.setRect(
                baseX - s.rectRadius - penWidth,
                baseY - s.rectRadius - penWidth,
                self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                self.height + s.rectRadius + penWidth)
            scene.addItem(self)
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            canvasTop = self.baseY - s.rectRadius
            movedBaseX = self.canvas.baseX + self.canvas.minWidth - \
                self.width - s.rectRadius - s.vHeaderPadding
            if s.hidecomments:
                self.__sideCommentPath = getHiddenCommentPath(
                    movedBaseX + s.hHeaderPadding,
                    canvasTop + s.vHeaderPadding,
                    self._sideCommentRect.width() + 2 * s.hHiddenTextPadding,
                    self._sideCommentRect.height() + 2 * s.vHiddenTextPadding)
            else:
                self.__sideCommentPath = getNoCellCommentBoxPath(
                    movedBaseX + s.hHeaderPadding,
                    canvasTop + s.vHeaderPadding,
                    self._sideCommentRect.width() + 2 * s.hTextPadding,
                    self._sideCommentRect.height() + 2 * s.vTextPadding,
                    s.commentCorner)
            penWidth = s.selectPenWidth - 1
            if s.hidecomments:
                self.setRect(
                    movedBaseX + s.hHeaderPadding - penWidth,
                    canvasTop + s.vHeaderPadding - penWidth,
                    self._sideCommentRect.width() +
                    2 * s.hHiddenTextPadding + 2 * penWidth,
                    self._sideCommentRect.height() +
                    2 * s.vHiddenTextPadding + 2 * penWidth)
            else:
                self.setRect(
                    movedBaseX + s.hHeaderPadding - penWidth,
                    canvasTop + s.vHeaderPadding - penWidth,
                    self._sideCommentRect.width() +
                    2 * s.hTextPadding + 2 * penWidth,
                    self._sideCommentRect.height() +
                    2 * s.vTextPadding + 2 * penWidth)
            scene.addItem(self)
        elif self.subKind == ScopeCellElement.DOCSTRING:
            penWidth = s.selectPenWidth - 1
            self.setRect(
                baseX - s.rectRadius - penWidth,
                baseY - penWidth,
                self.canvas.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                self.height + 2 * penWidth)
            scene.addItem(self)
            if s.hidedocstrings:
                scene.addItem(self.__docBadge)
                self.__docBadge.moveTo(
                    baseX - s.rectRadius + penWidth, baseY + penWidth)

    def getColors(self):
        """Provides the item colors"""
        return self.__bgColor, self.__fgColor, self.__borderColor

    def _paint(self, painter, option, widget):
        """Draws the corresponding scope element"""
        s = self.canvas.settings

        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.__bgColor, self.__fgColor, self.__borderColor = \
                self.getCustomColors(painter.brush().color(),
                                     painter.brush().color())
            brush = QBrush(self.__bgColor)
            painter.setBrush(brush)

            if self.isSelected():
                selectPen = QPen(s.selectColor)
                selectPen.setWidth(s.selectPenWidth)
                selectPen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(selectPen)
            else:
                pen = QPen(self.__borderColor)
                pen.setWidth(s.lineWidth)
                painter.setPen(pen)

            painter.drawRoundedRect(self.baseX + s.hCellPadding,
                                    self.baseY + s.vCellPadding,
                                    self.canvas.minWidth - 2 * s.hCellPadding,
                                    self.canvas.minHeight - 2 * s.vCellPadding,
                                    s.rectRadius, s.rectRadius)

        elif self.subKind == ScopeCellElement.DECLARATION:
            self.__bgColor, self.__fgColor, self.__borderColor = \
                self.getCustomColors(painter.brush().color(), s.boxFGColor)
            brush = QBrush(self.__bgColor)
            painter.setBrush(brush)

            pen = QPen(self.__fgColor)
            painter.setFont(s.monoFont)
            painter.setPen(pen)
            canvasLeft = self.baseX - s.rectRadius
            canvasTop = self.baseY - s.rectRadius
            textHeight = self._headerRect.height()
            yShift = 0
            if hasattr(self.ref, "sideComment"):
                yShift = s.vTextPadding
            painter.drawText(canvasLeft + s.hHeaderPadding,
                             canvasTop + s.vHeaderPadding + yShift,
                             self._headerRect.width(), textHeight,
                             Qt.AlignLeft, self._getText())

            pen = QPen(self.__borderColor)
            pen.setWidth(s.lineWidth)
            painter.setPen(pen)

            # If the scope is selected then the line may need to be shorter
            # to avoid covering the outline
            row = self.addr[1] - 1
            column = self.addr[0] - 1
            correction = 0.0
            if self.canvas.cells[row][column].isSelected():
                correction = s.selectPenWidth - 1
            painter.drawLine(canvasLeft + correction,
                             self.baseY + self.height,
                             canvasLeft + self.canvas.minWidth -
                             2 * s.hCellPadding - correction,
                             self.baseY + self.height)

        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            brush = QBrush(s.commentBGColor)
            painter.setBrush(brush)

            if self.isSelected():
                selectPen = QPen(s.selectColor)
                selectPen.setWidth(s.selectPenWidth)
                selectPen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(selectPen)
            else:
                pen = QPen(s.commentLineColor)
                pen.setWidth(s.commentLineWidth)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)

            canvasTop = self.baseY - s.rectRadius
            # s.vHeaderPadding below is used intentionally: to have the same
            # spacing on top, bottom and right for the comment box
            movedBaseX = self.canvas.baseX + self.canvas.minWidth - \
                self.width - s.rectRadius - s.vHeaderPadding
            painter.drawPath(self.__sideCommentPath)

            pen = QPen(s.boxFGColor)
            painter.setFont(s.monoFont)
            painter.setPen(pen)
            if s.hidecomments:
                painter.drawText(movedBaseX + s.hHeaderPadding + s.hHiddenTextPadding,
                                 canvasTop + s.vHeaderPadding + s.vHiddenTextPadding,
                                 self._sideCommentRect.width(),
                                 self._sideCommentRect.height(),
                                 Qt.AlignLeft, self._getSideComment())
            else:
                painter.drawText(movedBaseX + s.hHeaderPadding + s.hTextPadding,
                                 canvasTop + s.vHeaderPadding + s.vTextPadding,
                                 self._sideCommentRect.width(),
                                 self._sideCommentRect.height(),
                                 Qt.AlignLeft, self._getSideComment())
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.__bgColor, self.__fgColor, self.__borderColor = \
                self.getCustomColors(painter.brush().color(), s.boxFGColor)
            if self.ref.docstring.leadingCMLComments:
                colorSpec = CMLVersion.find(
                    self.ref.docstring.leadingCMLComments, CMLcc)
                if colorSpec:
                    if colorSpec.bgColor:
                        self.__bgColor = colorSpec.bgColor
                    if colorSpec.fgColor:
                        self.__fgColor = colorSpec.fgColor

            brush = QBrush(self.__bgColor)
            painter.setBrush(brush)

            canvasLeft = self.baseX - s.rectRadius

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
                pen = QPen(self.__bgColor)
                pen.setWidth(s.lineWidth)
                pen.setJoinStyle(Qt.MiterJoin)
                painter.setPen(pen)

                dsCorr = float(s.lineWidth)
                if self.canvas.cells[row][column].isSelected():
                    dsCorr = float(s.selectPenWidth) / 2.0 + \
                        float(s.lineWidth) / 2.0
                painter.drawRect(float(canvasLeft) + dsCorr,
                                 self.baseY + s.lineWidth,
                                 float(self.canvas.minWidth) -
                                 2.0 * float(s.hCellPadding) - 2.0 * dsCorr,
                                 self.height - 2 * s.lineWidth)

                pen = QPen(self.__borderColor)
                pen.setWidth(s.lineWidth)
                painter.setPen(pen)
                painter.drawLine(canvasLeft + correction,
                                 self.baseY + self.height,
                                 canvasLeft + self.canvas.minWidth -
                                 2 * s.hCellPadding - correction,
                                 self.baseY + self.height)

            if not s.hidedocstrings:
                pen = QPen(self.__fgColor)
                painter.setFont(s.monoFont)
                painter.setPen(pen)
                painter.drawText(canvasLeft + s.hHeaderPadding,
                                 self.baseY + s.vHeaderPadding,
                                 self.canvas.width - 2 * s.hHeaderPadding,
                                 self.height - 2 * s.vHeaderPadding,
                                 Qt.AlignLeft, self.getDocstringText())

    def hoverEnterEvent(self, event):
        """Handling mouse enter event"""
        if self.__navBarUpdate:
            self.__navBarUpdate(self.getCanvasTooltip())

    def hoverLeaveEvent(self, event):
        """Handling mouse enter event"""
        # if self.__navBarUpdate:
        #     self.__navBarUpdate("")
        return

    def __str__(self):
        """Debugging support"""
        return CellElement.__str__(self) + \
               "(" + scopeCellElementToString(self.subKind) + ")"

    def scopedItem(self):
        """True if it is a scoped item"""
        return True

    def isComment(self):
        """True if it is a comment"""
        return self.subKind == self.SIDE_COMMENT

    def isDocstring(self):
        """True if it is a docstring"""
        return self.subKind == self.DOCSTRING

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor is None:
            return
        if event:
            if event.buttons() != Qt.LeftButton:
                return

        if self.subKind == self.SIDE_COMMENT:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self._editor.gotoLine(self.ref.sideComment.beginLine,
                                  self.ref.sideComment.beginPos)
            self._editor.setFocus()
            return
        if self.subKind == self.DOCSTRING:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self._editor.gotoLine(self.ref.docstring.body.beginLine,
                                  self.ref.docstring.body.beginPos)
            self._editor.setFocus()
            return
        if self.subKind == self.DECLARATION:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            if self.kind == CellElement.FILE_SCOPE:
                self._editor.gotoLine(1, 1)   # Good enough for the
                                              # vast majority of the cases
            else:
                self._editor.gotoLine(self.ref.body.beginLine,
                                      self.ref.body.beginPos)
            self._editor.setFocus()
            return

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
        if self.subKind == self.SIDE_COMMENT:
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
            else:
                return distance(absPos, self.ref.body.begin,
                                self.ref.body.end)
        return maxsize

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        if self.subKind == self.DOCSTRING:
            return distance(line, self.ref.docstring.beginLine,
                            self.ref.docstring.endLine)
        if self.subKind == self.SIDE_COMMENT:
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
            else:
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
                    line = min(self.ref.docstring.leadingComment.parts[0].beginLine,
                               line)
            return min(self.ref.docstring.beginLine, line)
        return CellElement.getFirstLine(self)


_scopeCellElementToString = {
    ScopeCellElement.UNKNOWN: "UNKNOWN",
    ScopeCellElement.TOP_LEFT: "TOP_LEFT",
    ScopeCellElement.LEFT: "LEFT",
    ScopeCellElement.BOTTOM_LEFT: "BOTTOM_LEFT",
    ScopeCellElement.DECLARATION: "DECLARATION",
    ScopeCellElement.SIDE_COMMENT: "SIDE_COMMENT",
    ScopeCellElement.DOCSTRING: "DOCSTRING",
    ScopeCellElement.TOP: "TOP",
    ScopeCellElement.BOTTOM: "BOTTOM"}


def scopeCellElementToString(kind):
    """Provides a string representation of a element kind"""
    return _scopeCellElementToString[kind]


class FileScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a file scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.FILE_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the file scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "module")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the file scope element"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the file scope element"""
        brush = QBrush(self.canvas.settings.fileScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            if self.ref.body is None:
                # Special case: the buffer is empty so no body exists
                return [0, 0]
            return self.ref.body.getLineRange()
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            if self.ref.body is None:
                # Special case: the buffer is empty so no body exists
                return [0, 0]
            return [self.ref.body.begin, self.ref.body.end]
        if self.subKind == self.DOCSTRING:
            return [self.ref.docstring.body.begin,
                    self.ref.docstring.body.end]

    def getSelectTooltip(self):
        """Provides a file scope selected tooltip"""
        lineRange = self.getLineRange()
        if self.subKind == self.TOP_LEFT:
            return "Module scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.DOCSTRING:
            return "Module docstring at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])

        # Must not really happen
        return "Module scope (" + scopeCellElementToString(self.subKind) + ")"


class FunctionScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a function scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.FUNC_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.name.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()

            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
            else:
                # The comment may stop before the end of the arguments list
                linesAfter = self.ref.arguments.endLine - \
                             self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render(self):
        """Renders the function scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "def")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the function scope element"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the function scope element"""
        brush = QBrush(self.canvas.settings.funcScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.DOCSTRING:
            return [self.ref.docstring.body.begin, self.ref.docstring.body.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin, self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides a selected function block tooltip"""
        lineRange = self.getLineRange()
        tooltip = "Function " + self.ref.name.getContent() + " "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.DOCSTRING:
            return tooltip + "docstring at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + \
            "scope (" + scopeCellElementToString(self.subKind) + ")"


class ClassScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a class scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.CLASS_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the class
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.name.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            if self.ref.baseClasses is None:
                lastLine = self.ref.name.endLine
            else:
                lastLine = self.ref.baseClasses.endLine

            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
            else:
                # The comment may stop before the end of the arguments list
                linesAfter = lastLine - self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render(self):
        """Renders the class scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "class")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the class scope element"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the class scope element"""
        brush = QBrush(self.canvas.settings.classScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.DOCSTRING:
            return self.ref.docstring.body.getLineRange()
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.DOCSTRING:
            return [self.ref.docstring.body.begin, self.ref.docstring.body.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin, self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides the selection tooltip"""
        lineRange = self.getLineRange()
        tooltip = "Class " + self.ref.name.getContent() + " "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.DOCSTRING:
            return tooltip + "docstring at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class ForScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a for-loop scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.FOR_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.iteration.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()

            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
            else:
                # The comment may stop before the end of the arguments list
                linesAfter = self.ref.iteration.endLine - \
                             self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render(self):
        """Renders the for-loop scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "for")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the for-loop scope element"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the for-loop scope element"""
        brush = QBrush(self.canvas.settings.forScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides a selected for block tooltip"""
        lineRange = self.getLineRange()
        tooltip = "For loop "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class WhileScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a while-loop scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.WHILE_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.condition.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()

            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
            else:
                # The comment may stop before the end of the arguments list
                linesAfter = self.ref.condition.endLine - \
                             self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render(self):
        """Renders the while-loop scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "while")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the while-loop scope element"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the while-loop scope element"""
        brush = QBrush(self.canvas.settings.whileScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the lineRange"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides the selected while scope element tooltip"""
        lineRange = self.getLineRange()
        tooltip = "While loop "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class TryScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a try-except scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.TRY_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
        return self._sideComment

    def render(self):
        """Renders the try scope element"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "try")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the try scope element"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the try scope element"""
        brush = QBrush(self.canvas.settings.tryScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.suite[-1].endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.suite[-1].end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides the selected try block tooltip"""
        lineRange = self.getLineRange()
        tooltip = "Try "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class WithScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a with scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.WITH_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.items.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
            else:
                # The comment may stop before the end of the arguments list
                linesAfter = self.ref.items.endLine - \
                             self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render(self):
        """Renders the with block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "with")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the with block"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the with scope element"""
        brush = QBrush(self.canvas.settings.withScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides the selected with block tooltip"""
        lineRange = self.getLineRange()
        tooltip = "With "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class DecoratorScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a decorator scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.DECOR_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.name.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            if self.ref.arguments is None:
                lastLine = self.ref.name.endLine
            else:
                lastLine = self.ref.arguments.endLine
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
            else:
                # The comment may stop before the end of the arguments list
                linesAfter = lastLine - self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render(self):
        """Renders the decorator"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, " @ ")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the decorator"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the decorator scope element"""
        brush = QBrush(self.canvas.settings.decorScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin, self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides the selected decorator tooltip"""
        lineRange = self.getLineRange()
        tooltip = "Decorator "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class ElseScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents an else scope element"""

    FOR_STATEMENT = 0
    WHILE_STATEMENT = 1
    TRY_STATEMENT = 2

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.ELSE_SCOPE
        self.subKind = kind
        self.after = self
        self.statement = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
        return self._sideComment

    def render(self):
        """Renders the else block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "else")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the else block"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the else scope element"""
        brush = QBrush(self.canvas.settings.elseScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        lineRange = self.getLineRange()
        tooltip = "Else "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class ExceptScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents an except scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.EXCEPT_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides a side comment"""
        if self._sideComment is None:
            # The comment may start not at the first line of the except
            if self.ref.clause is None:
                self._sideComment = self.ref.sideComment.getDisplayValue()
            else:
                if self.canvas.settings.hidecomments:
                    linesBefore = 0
                else:
                    linesBefore = self.ref.sideComment.beginLine - \
                                  self.ref.clause.beginLine
                self._sideComment = '\n' * linesBefore + \
                                    self.ref.sideComment.getDisplayValue()
                lastLine = self.ref.clause.endLine
                if not self.canvas.settings.hidecomments:
                    # The comment may stop before the end of the arguments list
                    linesAfter = lastLine - self.ref.sideComment.endLine
                    if linesAfter > 0:
                        self._sideComment += '\n' * linesAfter
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
        return self._sideComment

    def render(self):
        """Renders the except block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "except")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the except block"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the except scope element"""
        brush = QBrush(self.canvas.settings.exceptScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        lineRange = self.getLineRange()
        tooltip = "Except "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"


class FinallyScopeCell(ScopeCellElement, QGraphicsRectItem):

    """Represents a finally scope element"""

    def __init__(self, ref, canvas, x, y, kind):
        ScopeCellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.FINALLY_SCOPE
        self.subKind = kind

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getSideComment(self):
        """Provides the side comment"""
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._sideComment) + '</pre>')
                self._sideComment = self.canvas.settings.hiddenCommentText
        return self._sideComment

    def render(self):
        """Renders the finally block"""
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem(self, "finally")
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the finally block"""
        self.baseX = baseX
        self.baseY = baseY
        self._draw(scene, baseX, baseY)

    def paint(self, painter, option, widget):
        """Draws the finally scope element"""
        brush = QBrush(self.canvas.settings.finallyScopeBGColor)
        painter.setBrush(brush)
        self._paint(painter, option, widget)

    def getLineRange(self):
        """Provides the line range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.beginLine, self.ref.endLine]
        if self.subKind == self.SIDE_COMMENT:
            return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.subKind == self.TOP_LEFT:
            return [self.ref.body.begin, self.ref.end]
        if self.subKind == self.SIDE_COMMENT:
            return [self.ref.sideComment.begin,
                    self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides a tooltip for the selected finally block"""
        lineRange = self.getLineRange()
        tooltip = "Finally "
        if self.subKind == self.TOP_LEFT:
            return tooltip + "scope at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        if self.subKind == self.SIDE_COMMENT:
            return tooltip + "side comment at lines " + \
                str(lineRange[0]) + "-" + str(lineRange[1])
        return tooltip + "scope (" + \
            scopeCellElementToString(self.subKind) + ")"
