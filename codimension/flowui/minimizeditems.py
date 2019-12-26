# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015-2019  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Various minimized items for a virtual canvas"""

# pylint: disable=C0305

from sys import maxsize
from html import escape
from ui.qt import Qt, QBrush, QGraphicsRectItem, QGraphicsItem, QPainterPath
from .auxitems import Connector
from .iconmixin import IconMixin
from .cellelement import CellElement
from .routines import distance


class MinimizedCellBase(CellElement, IconMixin, QGraphicsRectItem):

    """Base for all minimized cells"""

    def __init__(self, iconFileName, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        IconMixin.__init__(self, canvas, iconFileName)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)

        # Visually the icon looks a bit too big so reduce the size to 80%
        self.iconItem.setIconHeight(self.iconItem.iconHeight() * 0.8)

        self.rectWidth = None
        self.rectHeight = None
        self.connector = None
        self.rectRadius = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def renderCell(self, hIconPadding, vIconPadding):
        """Renders the cell"""
        settings = self.canvas.settings

        if self.kind == CellElement.EXCEPT_MINIMIZED:
            self.rectRadius = settings.hiddenExceptRectRadius
        else:
            self.rectRadius = settings.hiddenCommentRectRadius

        self.rectWidth = self.iconItem.iconWidth() + 2 * hIconPadding
        self.rectHeight = self.iconItem.iconHeight() + 2 * vIconPadding

        self.minWidth = self.rectWidth + 2 * settings.hCellPadding
        self.minHeight = self.rectHeight + 2 * settings.vCellPadding

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def drawCell(self, scene, baseX, baseY, hIconPadding,
                 setupConnector):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        # derived class method; it uses self.baseX and self.baseY
        setupConnector()
        scene.addItem(self.connector)

        # xPos matches the connector (which could be drawn in any direction)
        xPos = max(self.connector.getFirstPoint()[0],
                   self.connector.getFirstPoint()[0])

        settings = self.canvas.settings
        penWidth = settings.selectPenWidth - 1
        self.setRect(xPos - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.rectWidth + 2 * penWidth,
                     self.rectHeight + 2 * penWidth)
        scene.addItem(self)

        self.iconItem.setPos(
            xPos + hIconPadding,
            baseY + self.minHeight / 2 - self.iconItem.iconHeight() / 2)
        scene.addItem(self.iconItem)

    def paintCell(self, painter, bgColor, borderColor,
                  option, widget):
        """Paints the comment"""
        del option
        del widget

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), borderColor))
        painter.setBrush(QBrush(bgColor))

        # xPos matches the connector (which could be drawn in any direction)
        xPos = max(self.connector.getFirstPoint()[0],
                   self.connector.getFirstPoint()[0])

        painter.drawRoundedRect(xPos,
                                self.baseY + settings.vCellPadding,
                                self.rectWidth, self.rectHeight,
                                self.rectRadius, self.rectRadius)


class MinimizedExceptCell(MinimizedCellBase):

    """Represents a minimized except block"""

    def __init__(self, ref, canvas, x, y):
        MinimizedCellBase.__init__(self, 'hiddenexcept.svg', ref, canvas, x, y)
        self.kind = CellElement.EXCEPT_MINIMIZED

        self.__setTooltip()

    def __setTooltip(self):
        """Sets the item tooltip"""
        parts = []
        for part in self.ref.exceptParts:
            lines = part.getDisplayValue().splitlines()
            if len(lines) > 1:
                parts.append('except: ' + lines[0] + '...')
            elif len(lines) == 1:
                parts.append('except: ' + lines[0])
            else:
                parts.append('except:')
        self.iconItem.setToolTip('<pre>' + escape('\n'.join(parts)) + '</pre>')

    def __setupConnector(self):
        """Sets the connector"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
        height = min(self.minHeight / 2, cellToTheLeft.minHeight / 2)

        self.connector = Connector(
            self.canvas, leftEdge + settings.hCellPadding,
            self.baseY + height,
            cellToTheLeft.baseX +
            cellToTheLeft.minWidth - settings.hCellPadding,
            self.baseY + height)

        self.connector.penStyle = Qt.DotLine

    def render(self):
        """Renders the cell"""
        return self.renderCell(self.canvas.settings.hHiddenExceptPadding,
                               self.canvas.settings.vHiddenExceptPadding)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.drawCell(scene, baseX, baseY,
                      self.canvas.settings.hHiddenExceptPadding,
                      self.__setupConnector)

    def paint(self, painter, option, widget):
        """Paints the cell"""
        self.paintCell(painter,
                       self.canvas.settings.hiddenExceptBGColor,
                       self.canvas.settings.hiddenExceptBorderColor,
                       option, widget)

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        firstExcept = self.ref.exceptParts[0]
        CellElement.mouseDoubleClickEvent(self, event,
                                          line=firstExcept.body.beginLine,
                                          pos=firstExcept.body.beginPos)

    def getLineRange(self):
        """Provides the line range"""
        firstLineRange = self.ref.exceptParts[0].getLineRange()
        lastLineRange = self.ref.exceptParts[-1].getLineRange()
        return [firstLineRange[0], lastLineRange[1]]

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        firstExcept = self.ref.exceptParts[0]
        lastExcept = self.ref.exceptParts[-1]
        return [firstExcept.begin, lastExcept.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        count = len(self.ref.exceptParts)
        if count == 1:
            return 'Minimized except block at ' + \
                   CellElement.getLinesSuffix(lineRange)
        return str(count) + ' minimized except blocks at ' + \
               CellElement.getLinesSuffix(lineRange)


class MinimizedCommentBase:

    """Base class for all the minimized comment cells"""

    def __init__(self):
        pass

    @staticmethod
    def selectTooltip(lineRange):
        """Provides the tooltip"""
        return 'Minimized comment at ' + CellElement.getLinesSuffix(lineRange)



class MinimizedIndependentCommentCell(MinimizedCommentBase, MinimizedCellBase):

    """Represents a minimized independent comment"""

    def __init__(self, ref, canvas, x, y):
        MinimizedCommentBase.__init__(self)
        MinimizedCellBase.__init__(self, 'hiddencomment.svg',
                                   ref, canvas, x, y)
        self.kind = CellElement.INDEPENDENT_MINIMIZED_COMMENT

        self.__setTooltip()

        self.leadingForElse = False
        self.sideForElse = False

    def __setTooltip(self):
        """Sets the item tooltip"""
        displayValue = self.ref.getDisplayValue()
        if displayValue:
            self.iconItem.setToolTip('<pre>' + escape(displayValue) + '</pre>')

    def __setupConnector(self):
        """Prepares the connector"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        leftEdge = \
            cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding

        if self.leadingForElse:
            self.connector = Connector(
                self.canvas, leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        else:
            self.connector = Connector(
                self.canvas, leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        self.connector.penColor = settings.hiddenCommentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def render(self):
        """Renders the cell"""
        return self.renderCell(self.canvas.settings.hHiddenCommentPadding,
                               self.canvas.settings.vHiddenCommentPadding)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.drawCell(scene, baseX, baseY,
                      self.canvas.settings.hHiddenCommentPadding,
                      self.__setupConnector)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        self.paintCell(painter,
                       self.canvas.settings.hiddenCommentBGColor,
                       self.canvas.settings.hiddenCommentBorderColor,
                       option, widget)

    def adjustWidth(self):
        """No need to adjust the width"""

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
        return [self.ref.begin, self.ref.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return MinimizedCommentBase.selectTooltip(self.getLineRange())


class MinimizedLeadingCommentCell(MinimizedCommentBase, MinimizedCellBase):

    """Represents a minimized leading comment"""

    def __init__(self, ref, canvas, x, y):
        MinimizedCommentBase.__init__(self)
        MinimizedCellBase.__init__(self, 'hiddencomment.svg',
                                   ref, canvas, x, y)
        self.kind = CellElement.LEADING_MINIMIZED_COMMENT

        self.__setTooltip()

    def __setTooltip(self):
        """Sets the item tooltip"""
        displayValue = self.ref.leadingComment.getDisplayValue()
        if displayValue:
            self.iconItem.setToolTip('<pre>' + escape(displayValue) + '</pre>')

    def __setupConnector(self):
        """Prepares the connector"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            leftEdge = self.baseX
        else:
            leftEdge = \
                cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding

        shift = self.hShift * 2 * settings.openGroupHSpacer
        leftEdge += shift

        self.connector = Connector(self.canvas, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(leftEdge + settings.hCellPadding,
                             self.baseY + self.minHeight / 2)
        connectorPath.lineTo(leftEdge, self.baseY + self.minHeight / 2)
        connectorPath.lineTo(leftEdge - settings.hCellPadding,
                             self.baseY + self.minHeight +
                             settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.hiddenCommentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def render(self):
        """Renders the cell"""
        return self.renderCell(self.canvas.settings.hHiddenCommentPadding,
                               self.canvas.settings.vHiddenCommentPadding)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.drawCell(scene, baseX, baseY,
                      self.canvas.settings.hHiddenCommentPadding,
                      self.__setupConnector)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        self.paintCell(painter,
                       self.canvas.settings.hiddenCommentBGColor,
                       self.canvas.settings.hiddenCommentBorderColor,
                       option, widget)

    def adjustWidth(self):
        """Adjust the width"""
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            return

        settings = self.canvas.settings
        spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth
        boxWidth = self.minWidth - 2 * settings.hCellPadding
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.leadingComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.leadingComment.begin, self.ref.leadingComment.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return MinimizedCommentBase.selectTooltip(self.getLineRange())



class MinimizedAboveCommentCell(MinimizedCommentBase, MinimizedCellBase):

    """Represents a minimized above comment"""

    def __init__(self, ref, canvas, x, y):
        MinimizedCommentBase.__init__(self)
        MinimizedCellBase.__init__(self, 'hiddencomment.svg',
                                   ref, canvas, x, y)
        self.kind = CellElement.ABOVE_MINIMIZED_COMMENT
        self.needConnector = False
        self.vConnector = None
        self.__setTooltip()

    def __setTooltip(self):
        """Sets the item tooltip"""
        displayValue = self.ref.leadingComment.getDisplayValue()
        if displayValue:
            self.iconItem.setToolTip('<pre>' + escape(displayValue) + '</pre>')

    def __setupConnector(self):
        """Prepares the connector"""
        settings = self.canvas.settings

        leftEdge = \
            self.baseX + settings.mainLine + settings.hCellPadding

        self.connector = Connector(self.canvas, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(leftEdge + settings.hCellPadding,
                             self.baseY + self.minHeight / 2)
        connectorPath.lineTo(leftEdge,
                             self.baseY + self.minHeight / 2)
        connectorPath.lineTo(leftEdge - settings.hCellPadding,
                             self.baseY + self.minHeight +
                             settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def render(self):
        """Renders the cell"""
        self.renderCell(self.canvas.settings.hHiddenCommentPadding,
                        self.canvas.settings.vHiddenCommentPadding)
        self.minWidth += self.canvas.settings.mainLine
        self.minWidth += self.canvas.settings.hCellPadding
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        settings = self.canvas.settings
        if self.needConnector:
            self.vConnector = Connector(
                self.canvas, baseX + settings.mainLine, baseY,
                baseX + settings.mainLine, baseY + self.height)
            scene.addItem(self.vConnector)

        self.drawCell(scene, baseX, baseY,
                      settings.hHiddenCommentPadding,
                      self.__setupConnector)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        settings = self.canvas.settings
        self.paintCell(painter,
                       settings.hiddenCommentBGColor,
                       settings.hiddenCommentBorderColor,
                       option, widget)

    def adjustWidth(self):
        """No need to adjust the width"""

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.leadingComment.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.leadingComment.begin, self.ref.leadingComment.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return MinimizedCommentBase.selectTooltip(self.getLineRange())



class MinimizedSideCommentCell(MinimizedCommentBase, MinimizedCellBase):

    """Represents a minimized side comment"""

    def __init__(self, ref, canvas, x, y):
        MinimizedCommentBase.__init__(self)
        MinimizedCellBase.__init__(self, 'hiddencomment.svg',
                                   ref, canvas, x, y)
        self.kind = CellElement.SIDE_MINIMIZED_COMMENT

        self.__setTooltip()

    def __setTooltip(self):
        """Sets the item tooltip"""
        displayValue = self.ref.sideComment.getDisplayValue()
        if displayValue:
            self.iconItem.setToolTip('<pre>' + escape(displayValue) + '</pre>')

    def __setupConnector(self):
        """Prepares the connector"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]

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
            leftEdge = \
                cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding

            index = self.addr[0] - 1
            while self.canvas.cells[self.addr[1]][index].kind == \
                    CellElement.CONNECTOR:
                index -= 1

            yPos = self.baseY + settings.vCellPadding + \
                   settings.ifSideCommentVShift

            self.connector = Connector(
                self.canvas, leftEdge + settings.hCellPadding,
                yPos,
                ifCell.baseX + ifCell.minWidth - settings.hCellPadding,
                yPos)
        else:
            # Regular box or 'if' without an rhs connector
            if ifCell:
                leftEdge = ifCell.baseX + ifCell.minWidth
            else:
                leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth

            if ifCell:
                yPos = self.baseY + settings.vCellPadding + \
                       settings.ifSideCommentVShift
                self.connector = Connector(
                    self.canvas, leftEdge + settings.hCellPadding,
                    yPos,
                    ifCell.baseX + ifCell.minWidth - settings.hCellPadding,
                    yPos)
            else:
                height = min(self.minHeight / 2, cellToTheLeft.minHeight / 2)
                self.connector = Connector(
                    self.canvas, leftEdge + settings.hCellPadding,
                    self.baseY + height,
                    cellToTheLeft.baseX +
                    cellToTheLeft.minWidth - settings.hCellPadding,
                    self.baseY + height)

        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def render(self):
        """Renders the cell"""
        return self.renderCell(self.canvas.settings.hHiddenCommentPadding,
                               self.canvas.settings.vHiddenCommentPadding)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.drawCell(scene, baseX, baseY,
                      self.canvas.settings.hHiddenCommentPadding,
                      self.__setupConnector)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        self.paintCell(painter,
                       self.canvas.settings.hiddenCommentBGColor,
                       self.canvas.settings.hiddenCommentBorderColor,
                       option, widget)

    def adjustWidth(self):
        """Adjusting the cell width"""
        settings = self.canvas.settings
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth
        if spareWidth > 0:
            self.minWidth = max(0, self.minWidth - spareWidth)
        self.width = self.minWidth

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

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return MinimizedCommentBase.selectTooltip(self.getLineRange())

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
