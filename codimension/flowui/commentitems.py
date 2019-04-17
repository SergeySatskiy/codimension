# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Various comment items on a virtual canvas"""

from sys import maxsize
from cgi import escape
from ui.qt import (Qt, QPen, QBrush, QPainterPath, QGraphicsPathItem,
                   QGraphicsItem, QStyleOptionGraphicsItem, QStyle)
from utils.globals import GlobalData
from .auxitems import Connector
from .items import CellElement
from .routines import distance, getCommentBoxPath



class CommenCellBase(CellElement):

    """Base class for comment items"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self._textRect = None
        self._leftEdge = None
        self.connector = None

        self._vTextPadding = canvas.settings.vTextPadding
        self._hTextPadding = canvas.settings.hTextPadding
        if canvas.settings.hidecomments:
            self._vTextPadding = canvas.settings.vHiddenTextPadding
            self._hTextPadding = canvas.settings.hHiddenTextPadding

    def isComment(self):
        """True if it is a comment"""
        return True

    def _copyToClipboard(self, parts):
        """Copies the item to a clipboard"""
        commonLeadingSpaces = maxsize
        for part in parts:
            commonLeadingSpaces = min(commonLeadingSpaces, part.beginPos - 1)

        content = []
        currentLine = parts[0].beginLine
        for part in parts:
            while part.beginLine - currentLine > 1:
                content.append('#')
                currentLine += 1

            content.append(part.getLineContent()[commonLeadingSpaces:])
            currentLine = part.beginLine
        self._putMimeToClipboard('\n'.join(content))



class IndependentCommentCell(CommenCellBase, QGraphicsPathItem):

    """Represents a single independent comment"""

    def __init__(self, ref, canvas, x, y):
        CommenCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.INDEPENDENT_COMMENT
        self.leadingForElse = False
        self.sideForElse = False

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides text"""
        if self._text is None:
            self._text = self.ref.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._text) + '</pre>')
                self._text = self.canvas.settings.hiddenCommentText
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self._textRect = self.getBoundingRect(self.__getText())

        self.minHeight = self._textRect.height() + \
                         2 * (settings.vCellPadding + self._vTextPadding)
        self.minWidth = self._textRect.width() + \
                        2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            self.minWidth = max(self.minWidth, settings.minWidth)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def adjustWidth(self):
        """Used during rendering to adjust the width of the cell.

        The comment now can take some space on the left and the left hand
        side cell has to be rendered already.
        The width of this cell will take whatever is needed considering
        the comment shift to the left.
        """
        settings = self.canvas.settings
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        spareWidth = \
            cellToTheLeft.width - settings.mainLine - settings.hCellPadding
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY
        self.__setupPath()
        scene.addItem(self.connector)
        scene.addItem(self)

    def __setupPath(self):
        """Sets the path for painting"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        self._leftEdge = \
            cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)
        path = getCommentBoxPath(settings, self._leftEdge, self.baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        # May be later the connector will look different for two cases below
        if self.leadingForElse:
            self.connector = Connector(
                settings, self._leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        else:
            self.connector = Connector(
                settings, self._leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        self.connector.penColor = settings.commentLineColor
        self.connector.penWidth = settings.commentLineWidth

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        settings = self.canvas.settings

        brush = QBrush(settings.commentBGColor)
        self.setBrush(brush)

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            self.setPen(selectPen)
        else:
            pen = QPen(settings.commentLineColor)
            pen.setWidth(settings.commentLineWidth)
            pen.setJoinStyle(Qt.RoundJoin)
            self.setPen(pen)

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem(option)
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint(self, painter, itemOption, widget)

        # Draw the text in the rectangle
        pen = QPen(settings.commentFGColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        painter.drawText(
            self._leftEdge + settings.hCellPadding + self._hTextPadding,
            self.baseY + settings.vCellPadding + self._vTextPadding,
            self._textRect.width(), self._textRect.height(),
            Qt.AlignLeft, self.__getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self._editor.gotoLine(self.ref.beginLine,
                                  self.ref.beginPos)
            self._editor.setFocus()

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.begin, self.ref.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Independent comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        return distance(absPos, self.ref.begin, self.ref.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        return distance(line, self.ref.beginLine, self.ref.endLine)

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.parts)



class LeadingCommentCell(CommenCellBase, QGraphicsPathItem):

    """Represents a single leading comment"""

    def __init__(self, ref, canvas, x, y):
        CommenCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.LEADING_COMMENT

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides text"""
        if self._text is None:
            self._text = self.ref.leadingComment.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._text) + '</pre>')
                self._text = self.canvas.settings.hiddenCommentText
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self._textRect = self.getBoundingRect(self.__getText())

        self.minHeight = \
            self._textRect.height() + \
            2 * settings.vCellPadding + 2 * self._vTextPadding
        self.minWidth = \
            self._textRect.width() + \
            2 * settings.hCellPadding + 2 * self._hTextPadding
        if not settings.hidecomments:
            self.minWidth = max(self.minWidth, settings.minWidth)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def adjustWidth(self):
        """Used during rendering to adjust the width of the cell.

        The comment now can take some space on the left and the left hand
        side cell has to be rendered already.
        The width of this cell will take whatever is needed considering
        the comment shift to the left
        """
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # Not implemented yet
            return

        # Here: there is a connector on the left so we can move the comment
        #       safely
        settings = self.canvas.settings
        spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY
        self.__setupPath()
        scene.addItem(self.connector)
        scene.addItem(self)

    def __setupPath(self):
        """Sets the comment path"""
        settings = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # not implemented yet
            self._leftEdge = self.baseX
        else:
            self._leftEdge = \
                cellToTheLeft.baseX + \
                settings.mainLine + settings.hCellPadding
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)

        shift = self.hShift * 2 * settings.openGroupHSpacer
        self._leftEdge += shift
        path = getCommentBoxPath(settings, self._leftEdge, baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        self.connector = Connector(settings, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.commentLineColor
        self.connector.penWidth = settings.commentLineWidth

        self._leftEdge -= shift

    def paint(self, painter, option, widget):
        """Draws the leading comment"""
        settings = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        # Left adjustments
        shift = self.hShift * 2 * settings.openGroupHSpacer
        self._leftEdge += shift

        brush = QBrush(settings.commentBGColor)
        self.setBrush(brush)

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            self.setPen(selectPen)
        else:
            pen = QPen(settings.commentLineColor)
            pen.setWidth(settings.commentLineWidth)
            pen.setJoinStyle(Qt.RoundJoin)
            self.setPen(pen)

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem(option)
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint(self, painter, itemOption, widget)

        # Draw the text in the rectangle
        pen = QPen(settings.commentFGColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        painter.drawText(
            self._leftEdge + settings.hCellPadding + self._hTextPadding,
            baseY + settings.vCellPadding + self._vTextPadding,
            self._textRect.width(), self._textRect.height(),
            Qt.AlignLeft, self.__getText())

        self._leftEdge -= shift

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self._editor.gotoLine(self.ref.leadingComment.beginLine,
                                  self.ref.leadingComment.beginPos)
            self._editor.setFocus()

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.leadingComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.leadingComment.begin, self.ref.leadingComment.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Leading comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        return distance(absPos, self.ref.leadingComment.begin,
                        self.ref.leadingComment.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        return distance(line, self.ref.leadingComment.beginLine,
                        self.ref.leadingComment.endLine)

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.leadingComment.parts)



class SideCommentCell(CommenCellBase, QGraphicsPathItem):

    """Represents a single side comment"""

    IF_SIDE_SHIFT = 6

    def __init__(self, ref, canvas, x, y):
        CommenCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.SIDE_COMMENT
        self.__isIfSide = False

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides the text"""
        if self._text is None:
            self._text = ""
            cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
            if self.canvas.settings.hidecomments:
                linesBefore = 0
            else:
                if cellToTheLeft.kind == CellElement.IMPORT:
                    importRef = cellToTheLeft.ref
                    linesBefore = self.ref.sideComment.beginLine - \
                                  importRef.whatPart.beginLine
                    if importRef.fromPart is not None:
                        linesBefore += 1
                else:
                    linesBefore = self.ref.sideComment.beginLine - \
                                  self.ref.body.beginLine
            self._text = '\n' * linesBefore + \
                         self.ref.sideComment.getDisplayValue()

            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._text) + '</pre>')
                self._text = self.canvas.settings.hiddenCommentText
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self._textRect = self.getBoundingRect(self.__getText())

        self.minHeight = self._textRect.height() + \
            2 * settings.vCellPadding + 2 * self._vTextPadding
        self.minWidth = self._textRect.width() + \
                        2 * settings.hCellPadding + 2 * self._hTextPadding
        if not settings.hidecomments:
            self.minWidth = max(self.minWidth, settings.minWidth)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def adjustWidth(self):
        """Used during rendering to adjust the width of the cell.

        The comment now can take some space on the left and the left hand
        side cell has to be rendered already.
        The width of this cell will take whatever is needed considering
        the comment shift to the left.
        """
        settings = self.canvas.settings
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY
        self.__setupPath()
        scene.addItem(self.connector)
        scene.addItem(self)

    def __setupPath(self):
        """Sets the comment path"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)
        self._leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
        cellKind = self.canvas.cells[self.addr[1]][self.addr[0] - 1].kind
        if cellKind == CellElement.CONNECTOR:
            # 'if' or 'elif' side comment
            self.__isIfSide = True
            self._leftEdge = \
                cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding
            boxBaseY = self.baseY
            if self.canvas.settings.hidecomments:
                boxBaseY += self.IF_SIDE_SHIFT
            path = getCommentBoxPath(settings, self._leftEdge, boxBaseY,
                                     boxWidth, self.minHeight)

            width = 0
            index = self.addr[0] - 1
            while self.canvas.cells[self.addr[1]][index].kind == \
                  CellElement.CONNECTOR:
                width += self.canvas.cells[self.addr[1]][index].width
                index -= 1

            # The first non-connector cell must be the 'if' cell
            ifCell = self.canvas.cells[self.addr[1]][index]

            self.connector = Connector(
                settings, self._leftEdge + settings.hCellPadding,
                self.baseY + ifCell.minHeight / 2 + self.IF_SIDE_SHIFT,
                ifCell.baseX + ifCell.minWidth - settings.hCellPadding,
                self.baseY + ifCell.minHeight / 2 + self.IF_SIDE_SHIFT)
        else:
            # Regular box
            self._leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
            path = getCommentBoxPath(settings, self._leftEdge, self.baseY,
                                     boxWidth, self.minHeight)

            height = min(self.minHeight / 2, cellToTheLeft.minHeight / 2)

            self.connector = Connector(
                settings, self._leftEdge + settings.hCellPadding,
                self.baseY + height,
                cellToTheLeft.baseX +
                cellToTheLeft.minWidth - settings.hCellPadding,
                self.baseY + height)

        self.connector.penColor = settings.commentLineColor
        self.connector.penWidth = settings.commentLineWidth

        self.setPath(path)

    def paint(self, painter, option, widget):
        """Draws the side comment"""
        settings = self.canvas.settings

        brush = QBrush(settings.commentBGColor)
        self.setBrush(brush)

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            self.setPen(selectPen)
        else:
            pen = QPen(settings.commentLineColor)
            pen.setWidth(settings.commentLineWidth)
            pen.setJoinStyle(Qt.RoundJoin)
            self.setPen(pen)

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem(option)
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint(self, painter, itemOption, widget)

        # Draw the text in the rectangle
        pen = QPen(settings.commentFGColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        boxBaseY = self.baseY
        if settings.hidecomments and self.__isIfSide:
            boxBaseY += self.IF_SIDE_SHIFT
        painter.drawText(
            self._leftEdge + settings.hCellPadding + self._hTextPadding,
            boxBaseY + settings.vCellPadding + self._vTextPadding,
            self._textRect.width(), self._textRect.height(),
            Qt.AlignLeft, self.__getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self._editor.gotoLine(self.ref.sideComment.beginLine,
                                  self.ref.sideComment.beginPos)
            self._editor.setFocus()

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.sideComment.begin, self.ref.sideComment.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Side comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        retval = maxsize
        for part in self.ref.sideComment.parts:
            # +1 is for finishing \n character
            dist = distance(absPos, part.begin, part.end + 1)
            if dist == 0:
                return 0
            retval = min(retval, dist)
        return retval

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        retval = maxsize
        for part in self.ref.sideComment.parts:
            dist = distance(line, part.beginLine, part.endLine)
            if dist == 0:
                return 0
            retval = min(retval, dist)
        return retval

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.sideComment.parts)



class AboveCommentCell(CommenCellBase, QGraphicsPathItem):

    """Represents a single leading comment which is above certain blocks.

    Blocks are: try/except or for/else or while/else
    i.e. those which are scopes located in a single row
    """

    def __init__(self, ref, canvas, x, y):
        CommenCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.ABOVE_COMMENT
        self.needConnector = False
        self.commentConnector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides text"""
        if self._text is None:
            self._text = self.ref.leadingComment.getDisplayValue()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._text) + '</pre>')
                self._text = self.canvas.settings.hiddenCommentText
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self._textRect = self.getBoundingRect(self.__getText())

        self.minHeight = self._textRect.height() + \
                         2 * (settings.vCellPadding + self._vTextPadding)
        # Width of the comment box itself
        self.minWidth = self._textRect.width() + \
                        2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            self.minWidth = max(self.minWidth, settings.minWidth)

        # Add the connector space
        self.minWidth += settings.mainLine + settings.hCellPadding

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY
        self.__setupPath()

        if self.needConnector:
            settings = self.canvas.settings
            self.connector = Connector(
                settings, baseX + settings.mainLine, baseY,
                baseX + settings.mainLine, baseY + self.height)
            scene.addItem(self.connector)

        scene.addItem(self.commentConnector)
        scene.addItem(self)

    def __setupPath(self):
        """Sets the comment path"""
        settings = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        self._leftEdge = \
            self.baseX + settings.mainLine + settings.hCellPadding
        boxWidth = self._textRect.width() + \
                   2 * (settings.hCellPadding + self._hTextPadding)
        if not settings.hidecomments:
            boxWidth = max(boxWidth, settings.minWidth)

        path = getCommentBoxPath(settings, self._leftEdge, baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        self.commentConnector = Connector(settings, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.commentConnector.setPath(connectorPath)
        self.commentConnector.penColor = settings.commentLineColor
        self.commentConnector.penWidth = settings.commentLineWidth

    def paint(self, painter, option, widget):
        """Draws the leading comment"""
        settings = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        brush = QBrush(settings.commentBGColor)
        self.setBrush(brush)
        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            self.setPen(selectPen)
        else:
            pen = QPen(settings.commentLineColor)
            pen.setWidth(settings.commentLineWidth)
            pen.setJoinStyle(Qt.RoundJoin)
            self.setPen(pen)

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem(option)
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint(self, painter, itemOption, widget)

        # Draw the text in the rectangle
        pen = QPen(settings.commentFGColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        painter.drawText(
            self._leftEdge + settings.hCellPadding + self._hTextPadding,
            baseY + settings.vCellPadding + self._vTextPadding,
            self._textRect.width(), self._textRect.height(),
            Qt.AlignLeft, self.__getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self._editor.gotoLine(self.ref.leadingComment.beginLine,
                                  self.ref.leadingComment.beginPos)
            self._editor.setFocus()
        return

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.leadingComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.leadingComment.begin, self.ref.leadingComment.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Leading comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        return distance(absPos, self.ref.leadingComment.begin,
                        self.ref.leadingComment.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        return distance(line, self.ref.leadingComment.beginLine,
                        self.ref.leadingComment.endLine)

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.leadingComment.parts)
