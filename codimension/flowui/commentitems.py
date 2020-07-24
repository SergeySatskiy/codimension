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

# pylint: disable=C0305
# pylint: disable=R0902

from sys import maxsize
from ui.qt import (Qt, QPen, QBrush, QPainterPath, QGraphicsPathItem,
                   QGraphicsItem, QStyleOptionGraphicsItem, QStyle)
from .auxitems import Connector
from .cellelement import CellElement
from .routines import distance, getCommentBoxPath
from .textmixin import TextMixin



class CommentCellBase(CellElement, TextMixin):

    """Base class for comment items"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        self._leftEdge = None
        self.connector = None

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

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Comment at ' + CellElement.getLinesSuffix(self.getLineRange())



class IndependentCommentCell(CommentCellBase, QGraphicsPathItem):

    """Represents a single independent comment"""

    def __init__(self, ref, canvas, x, y):
        CommentCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.INDEPENDENT_COMMENT
        self.leadingForElse = False
        self.sideForElse = False

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        self.minHeight = self.textRect.height() + \
                         2 * (settings.vCellPadding + settings.vTextPadding)
        self.minWidth = self.textRect.width() + \
                        2 * (settings.hCellPadding + settings.hTextPadding)
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
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
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
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
        boxWidth = max(boxWidth, settings.minWidth)
        path = getCommentBoxPath(settings, self._leftEdge, self.baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        # May be later the connector will look different for two cases below
        if self.leadingForElse:
            self.connector = Connector(
                self.canvas, self._leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        else:
            self.connector = Connector(
                self.canvas, self._leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        settings = self.canvas.settings
        self.setPen(self.getPainterPen(self.isSelected(),
                                       settings.commentBorderColor))
        self.setBrush(QBrush(settings.commentBGColor))

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
            self._leftEdge + settings.hCellPadding + settings.hTextPadding,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        # Needed custom because this item is used for ifs 'else' side comment
        CellElement.mouseDoubleClickEvent(self, event,
                                          pos=self.ref.beginPos)

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.parts)



class LeadingCommentCell(CommentCellBase, QGraphicsPathItem):

    """Represents a single leading comment"""

    def __init__(self, ref, canvas, x, y):
        CommentCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.LEADING_COMMENT

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self,
                       customText=self.ref.leadingComment.getDisplayValue(),
                       customReplacement='')

        self.minHeight = \
            self.textRect.height() + \
            2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = \
            self.textRect.width() + \
            2 * settings.hCellPadding + 2 * settings.hTextPadding
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
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
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
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
        boxWidth = max(boxWidth, settings.minWidth)

        shift = self.hShift * 2 * settings.openGroupHSpacer
        self._leftEdge += shift
        path = getCommentBoxPath(settings, self._leftEdge, baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        self.connector = Connector(self.canvas, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

        self._leftEdge -= shift

    def paint(self, painter, option, widget):
        """Draws the leading comment"""
        settings = self.canvas.settings
        self.setPen(self.getPainterPen(self.isSelected(),
                                       settings.commentBorderColor))
        self.setBrush(QBrush(settings.commentBGColor))

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        # Left adjustments
        shift = self.hShift * 2 * settings.openGroupHSpacer
        self._leftEdge += shift

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
            self._leftEdge + settings.hCellPadding + settings.hTextPadding,
            baseY + settings.vCellPadding + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

        self._leftEdge -= shift

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.leadingComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.leadingComment.getAbsPosRange()

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.leadingComment.parts)



class SideCommentCell(CommentCellBase, QGraphicsPathItem):

    """Represents a single side comment"""

    def __init__(self, ref, canvas, x, y):
        CommentCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.SIDE_COMMENT

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        self.__vDecorShift = 0

    def getCommentText(self):
        """Provides the text"""
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind == CellElement.IMPORT:
            importRef = cellToTheLeft.ref
            linesBefore = self.ref.sideComment.beginLine - \
                          importRef.whatPart.beginLine
            if importRef.fromPart is not None:
                linesBefore += 1
        else:
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.body.beginLine
        return '\n' * linesBefore + self.ref.sideComment.getDisplayValue()

    def __calcVDecorShift(self):
        settings = self.canvas.settings
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind == CellElement.VCANVAS:
            topLeft = cellToTheLeft.cells[0][0]
            if topLeft.aboveBadges.hasAny():
                self.__vDecorShift = topLeft.aboveBadges.height + \
                                     settings.badgeToScopeVPadding
        elif cellToTheLeft.kind == CellElement.DECORATOR:
            self.__vDecorShift = cellToTheLeft.aboveBadges.height + \
                                 settings.badgeToScopeVPadding

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self, customText=self.getCommentText(),
                       customReplacement='')

        self.minHeight = self.textRect.height() + \
            2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = self.textRect.width() + \
                        2 * settings.hCellPadding + 2 * settings.hTextPadding
        self.minWidth = max(self.minWidth, settings.minWidth)

        self.__calcVDecorShift()
        self.minHeight += self.__vDecorShift

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
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
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

        self.baseY += self.__vDecorShift
        self.minHeight -= self.__vDecorShift
        self.__setupPath()
        self.minHeight += self.__vDecorShift

        scene.addItem(self.connector)
        scene.addItem(self)

    def __setupPath(self):
        """Sets the comment path"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
        boxWidth = max(boxWidth, settings.minWidth)
        if cellToTheLeft.kind == CellElement.CONNECTOR:
            ifCell = None
            for cell in self.canvas.cells[self.addr[1]]:
                if cell.kind == CellElement.IF:
                    ifCell = cell
                    break
        elif cellToTheLeft.kind == CellElement.IF:
            ifCell = cellToTheLeft
        else:
            ifCell = None

        if cellToTheLeft.kind == CellElement.CONNECTOR:
            # 'if' or 'elif' side comment when there is a connector
            self._leftEdge = \
                cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding
            boxBaseY = self.baseY
            path = getCommentBoxPath(settings, self._leftEdge, boxBaseY,
                                     boxWidth, self.minHeight)

            width = 0
            index = self.addr[0] - 1
            while self.canvas.cells[self.addr[1]][index].kind == \
                  CellElement.CONNECTOR:
                width += self.canvas.cells[self.addr[1]][index].width
                index -= 1

            yPos = self.baseY + settings.vCellPadding + \
                   settings.ifSideCommentVShift

            self.connector = Connector(
                self.canvas, self._leftEdge + settings.hCellPadding,
                yPos,
                ifCell.baseX + ifCell.minWidth - settings.hCellPadding,
                yPos)
        else:
            # Regular box or 'if' without an rhs connector
            if ifCell:
                self._leftEdge = ifCell.baseX + ifCell.minWidth
            else:
                self._leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
            path = getCommentBoxPath(settings, self._leftEdge, self.baseY,
                                     boxWidth, self.minHeight)


            if ifCell:
                yPos = self.baseY + settings.vCellPadding + \
                       settings.ifSideCommentVShift
                self.connector = Connector(
                    self.canvas, self._leftEdge + settings.hCellPadding,
                    yPos,
                    ifCell.baseX + ifCell.minWidth - settings.hCellPadding,
                    yPos)
            else:
                if cellToTheLeft.kind == CellElement.DECORATOR:
                    cellHeight = cellToTheLeft.minHeight - \
                                 cellToTheLeft.aboveBadges.height - \
                                 settings.badgeToScopeVPadding
                    height = min(self.minHeight / 2, cellHeight / 2)
                else:
                    height = min(self.minHeight / 2, cellToTheLeft.minHeight / 2)
                self.connector = Connector(
                    self.canvas, self._leftEdge + settings.hCellPadding,
                    self.baseY + height,
                    cellToTheLeft.baseX +
                    cellToTheLeft.minWidth - settings.hCellPadding,
                    self.baseY + height)

        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

        self.setPath(path)

    def paint(self, painter, option, widget):
        """Draws the side comment"""
        settings = self.canvas.settings
        self.setPen(self.getPainterPen(self.isSelected(),
                                       settings.commentBorderColor))
        self.setBrush(QBrush(settings.commentBGColor))

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
        painter.drawText(
            self._leftEdge + settings.hCellPadding + settings.hTextPadding,
            boxBaseY + settings.vCellPadding + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        CellElement.mouseDoubleClickEvent(self, event,
                                          pos=self.ref.sideComment.beginPos)

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.sideComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.sideComment.getAbsPosRange()

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



class AboveCommentCell(CommentCellBase, QGraphicsPathItem):

    """Represents a single leading comment which is above certain blocks.

    Blocks are: try/except or for/else or while/else
    i.e. those which are scopes located in a single row
    """

    def __init__(self, ref, canvas, x, y):
        CommentCellBase.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.ABOVE_COMMENT
        self.needConnector = False
        self.commentConnector = None

        # Decorators have a small badge so the connector needs to touch it
        # more to the left than the usual main line
        self.smallBadge = False
        self.hanging = False
        self.commentMainLine = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.commentMainLine = settings.mainLine
        if self.smallBadge:
            self.commentMainLine = settings.decorMainLine

        self.setupText(self,
                       customText=self.ref.leadingComment.getDisplayValue(),
                       customReplacement='')

        self.minHeight = self.textRect.height() + \
                         2 * (settings.vCellPadding + settings.vTextPadding)
        # Width of the comment box itself
        self.minWidth = self.textRect.width() + \
                        2 * (settings.hCellPadding + settings.hTextPadding)
        self.minWidth = max(self.minWidth, settings.minWidth)

        # Add the connector space
        self.minWidth += self.commentMainLine + settings.hCellPadding

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
            yShift = 0
            if self.hanging:
                yShift = settings.vCellPadding

            self.connector = Connector(
                self.canvas,
                baseX + self.commentMainLine,
                baseY + yShift,
                baseX + self.commentMainLine,
                baseY + self.height + yShift)
            self.connector.penWidth = settings.boxLineWidth
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
            self.baseX + self.commentMainLine + settings.hCellPadding
        boxWidth = self.textRect.width() + \
                   2 * (settings.hCellPadding + settings.hTextPadding)
        boxWidth = max(boxWidth, settings.minWidth)

        path = getCommentBoxPath(settings, self._leftEdge, baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        self.commentConnector = Connector(self.canvas, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.commentConnector.setPath(connectorPath)
        self.commentConnector.penColor = settings.commentBorderColor
        self.commentConnector.penWidth = settings.boxLineWidth

    def paint(self, painter, option, widget):
        """Draws the leading comment"""
        settings = self.canvas.settings
        self.setPen(self.getPainterPen(self.isSelected(),
                                       settings.commentBorderColor))
        self.setBrush(QBrush(settings.commentBGColor))

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

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
            self._leftEdge + settings.hCellPadding + settings.hTextPadding,
            baseY + settings.vCellPadding + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def adjustWidth(self):
        """No adjustment needed"""

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.leadingComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.leadingComment.getAbsPosRange()

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.ref.leadingComment.parts)

