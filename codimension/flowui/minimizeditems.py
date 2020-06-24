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
from ui.qt import Qt, QBrush, QGraphicsRectItem, QGraphicsItem, QPainterPath, QPen
from .auxitems import Connector, SVGItem
from .colormixin import ColorMixin
from .cellelement import CellElement
from .routines import distance, getDoclinkIconAndTooltip


class MinimizedIndependentCommentCell(CellElement, QGraphicsRectItem):

    """Represents a minimized independent comment"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)

        self.kind = CellElement.INDEPENDENT_MINIMIZED_COMMENT

        self.__setTooltip()

        self.leadingForElse = False
        self.sideForElse = False

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __setTooltip(self):
        """Sets the item tooltip"""
        displayValue = self.ref.getDisplayValue()
        if displayValue:
            self.setToolTip('<pre>' + escape(displayValue) + '</pre>')

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
        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def render(self):
        """Renders the cell"""
        s = self.canvas.settings
        self.text = '#'
        self.textRect = s.badgeFontMetrics.boundingRect(0, 0, maxsize,
                                                        maxsize, 0, self.text)
        self.badgeWidth = self.textRect.width() + 2 * s.badgeHSpacing
        self.badgeHeight = self.textRect.height() + 2 * s.badgeVSpacing
        self.badgeWidth = max(self.badgeWidth, self.badgeHeight)

        self.minWidth = self.badgeWidth + 2 * s.hCellPadding
        self.minHeight = self.badgeHeight + 2 * s.vCellPadding

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        self.__setupConnector()
        scene.addItem(self.connector)

        # xPos matches the connector (which could be drawn in any direction)
        xPos = max(self.connector.getFirstPoint()[0],
                   self.connector.getLastPoint()[0])

        settings = self.canvas.settings
        penWidth = settings.selectPenWidth - 1
        self.setRect(xPos - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.badgeWidth + 2 * penWidth,
                     self.badgeHeight + 2 * penWidth)
        scene.addItem(self)

        self.iconItem = SVGItem(self.canvas, 'hiddencomment.svg', self)
        sideSize = self.badgeHeight - 2 * settings.badgePixmapSpacing
        self.iconItem.setIconHeight(sideSize)

        self.iconItem.setPos(xPos + (self.badgeWidth - sideSize) / 2,
                             baseY + settings.vCellPadding +
                             (self.badgeHeight - sideSize) / 2)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(),
                                          settings.commentBorderColor))
        painter.setBrush(QBrush(settings.commentBGColor))

        # xPos matches the connector (which could be drawn in any direction)
        xPos = max(self.connector.getFirstPoint()[0],
                   self.connector.getLastPoint()[0])
        painter.drawRoundedRect(xPos,
                                self.baseY + settings.vCellPadding,
                                self.badgeWidth, self.badgeHeight,
                                settings.badgeRadius,
                                settings.badgeRadius)

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
        return 'Comment at ' + CellElement.getLinesSuffix(self.getLineRange())


class MinimizedIndependentDocCell(CellElement, ColorMixin, QGraphicsRectItem):

    """Represents a minimized independent doc link"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        ColorMixin.__init__(self, None, canvas.settings.docLinkBGColor,
                            canvas.settings.docLinkFGColor,
                            canvas.settings.docLinkBorderColor,
                            colorSpec=ref)
        QGraphicsRectItem.__init__(self)
        self.pixmapFile, tooltip = getDoclinkIconAndTooltip(ref, hidden=True)
        if tooltip:
            self.setToolTip('<pre>' + escape(tooltip) + '</pre>')

        self.kind = CellElement.INDEPENDENT_MINIMIZED_DOC

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __setupConnector(self):
        """Prepares the connector"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        leftEdge = \
            cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding

        self.connector = Connector(
            self.canvas, leftEdge + settings.hCellPadding,
            self.baseY + self.minHeight / 2,
            cellToTheLeft.baseX + settings.mainLine,
            self.baseY + self.minHeight / 2)
        self.connector.penColor = settings.commentBorderColor
        self.connector.penWidth = settings.boxLineWidth

    def render(self):
        """Renders the cell"""
        s = self.canvas.settings
        self.textRect = s.badgeFontMetrics.boundingRect(0, 0, maxsize,
                                                        maxsize, 0, '#')
        self.badgeWidth = self.textRect.width() + 2 * s.badgeHSpacing
        self.badgeHeight = self.textRect.height() + 2 * s.badgeVSpacing
        self.badgeWidth = max(self.badgeWidth, self.badgeHeight)

        self.minWidth = self.badgeWidth + 2 * s.hCellPadding
        self.minHeight = self.badgeHeight + 2 * s.vCellPadding

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        self.__setupConnector()
        scene.addItem(self.connector)

        # xPos matches the connector (which could be drawn in any direction)
        xPos = max(self.connector.getFirstPoint()[0],
                   self.connector.getLastPoint()[0])

        settings = self.canvas.settings
        penWidth = settings.selectPenWidth - 1
        self.setRect(xPos - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.badgeWidth + 2 * penWidth,
                     self.badgeHeight + 2 * penWidth)
        scene.addItem(self)

        self.iconItem = SVGItem(self.canvas, self.pixmapFile, self)
        sideSize = self.badgeHeight - 2 * settings.badgePixmapSpacing
        self.iconItem.setIconHeight(sideSize)

        self.iconItem.setPos(xPos + (self.badgeWidth - sideSize) / 2,
                             baseY + settings.vCellPadding +
                             (self.badgeHeight - sideSize) / 2)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(),
                                          settings.docLinkBorderColor))
        painter.setBrush(QBrush(self.bgColor))

        # xPos matches the connector (which could be drawn in any direction)
        xPos = max(self.connector.getFirstPoint()[0],
                   self.connector.getLastPoint()[0])
        painter.drawRoundedRect(xPos,
                                self.baseY + settings.vCellPadding,
                                self.badgeWidth, self.badgeHeight,
                                settings.badgeRadius,
                                settings.badgeRadius)

    def adjustWidth(self):
        """No need to adjust the width"""

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        CellElement.mouseDoubleClickEvent(self, event,
                                          pos=self.ref.ref.parts[0].beginPos)

    def getLineRange(self):
        """Provides the line range"""
        return self.ref.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.ref.getAbsPosRange()

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Link/anchor at ' + CellElement.getLinesSuffix(self.getLineRange())

