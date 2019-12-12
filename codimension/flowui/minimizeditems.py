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

from html import escape
from ui.qt import Qt, QBrush, QGraphicsRectItem, QGraphicsItem
from utils.globals import GlobalData
from .auxitems import Connector
from .routines import distance
from .iconmixin import IconMixin
from .cellelement import CellElement


class MinimizedExceptCell(CellElement, IconMixin, QGraphicsRectItem):

    """Represents a minimized except block"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        IconMixin.__init__(self, canvas, 'hiddenexcept.svg')
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.EXCEPT_MINIMIZED

        self.__setTooltip()
        self.__leftEdge = None
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

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
        self.__leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
        height = min(self.minHeight / 2, cellToTheLeft.minHeight / 2)

        self.connector = Connector(
            self.canvas, self.__leftEdge + settings.hCellPadding,
            self.baseY + height,
            cellToTheLeft.baseX +
            cellToTheLeft.minWidth - settings.hCellPadding,
            self.baseY + height)

        self.connector.penStyle = Qt.DotLine

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings

        self.minWidth = self.iconItem.iconWidth() + \
                        2 * (settings.hCellPadding + \
                             settings.hHiddenExceptPadding)
        self.minHeight = self.iconItem.iconHeight() + \
                         2 * (settings.vCellPadding + \
                              settings.vHiddenExceptPadding)

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        self.__setupConnector()
        scene.addItem(self.connector)

        settings = self.canvas.settings
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)
        scene.addItem(self)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hHiddenExceptPadding,
            baseY + self.minHeight / 2 - self.iconItem.iconHeight() / 2)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        del option
        del widget

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(),
                                          settings.hiddenExceptBorderColor))
        painter.setBrush(QBrush(settings.hiddenExceptBGColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                rectWidth, rectHeight,
                                settings.scopeRectRadius,
                                settings.scopeRectRadius)

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self.editor:
            firstExcept = self.ref.exceptParts[0]
            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()
            self.editor.gotoLine(firstExcept.body.beginLine,
                                 firstExcept.body.beginPos)
            self.editor.setFocus()

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
            return 'Minimized except block at lines ' + \
                   str(lineRange[0]) + "-" + str(lineRange[1])
        return str(count) + ' minimized except blocks at lines ' + \
               str(lineRange[0]) + "-" + str(lineRange[1])

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        absPosRange = self.getAbsPosRange()
        return distance(absPos, absPosRange[0], absPosRange[1])

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        lineRange = self.getLineRange()
        return distance(line, lineRange[0], lineRange[1])


class MinimizedIndependentCommentCell(CellElement, IconMixin,
                                      QGraphicsRectItem):

    """Represents a minimized except block"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        IconMixin.__init__(self, canvas, 'hiddencomment.svg')
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.INDEPENDENT_MINIMIZED_COMMENT

        self.__setTooltip()

        self.leadingForElse = False
        self.sideForElse = False
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __setTooltip(self):
        """Sets the item tooltip"""
        displayValue = self.ref.getDisplayValue()
        if displayValue:
            self.iconItem.setToolTip('<pre>' + escape(displayValue) + '</pre>')

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings

        self.minWidth = self.iconItem.iconWidth() + \
                        2 * (settings.hCellPadding + \
                             settings.hHiddenCommentPadding)
        self.minHeight = self.iconItem.iconHeight() + \
                         2 * (settings.vCellPadding + \
                              settings.vHiddenCommentPadding)

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

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

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        self.__setupConnector()
        scene.addItem(self.connector)

        settings = self.canvas.settings
        rectWidth = self.iconItem.iconWidth() + \
                    2 * settings.hHiddenCommentPadding
        rectHeight = self.iconItem.iconHeight() + \
                     2 * settings.vHiddenCommentPadding

        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     rectWidth + 2 * penWidth,
                     rectHeight + 2 * penWidth)
        scene.addItem(self)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hHiddenCommentPadding,
            baseY + self.minHeight / 2 - self.iconItem.iconHeight() / 2)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        del option
        del widget

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(),
                                          settings.hiddenCommentBorderColor))
        painter.setBrush(QBrush(settings.hiddenCommentBGColor))

        rectWidth = self.iconItem.iconWidth() + \
                    2 * settings.hHiddenCommentPadding
        rectHeight = self.iconItem.iconHeight() + \
                     2 * settings.vHiddenCommentPadding

        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                rectWidth, rectHeight,
                                settings.scopeRectRadius,
                                settings.scopeRectRadius)

    def adjustWidth(self):
        settings = self.canvas.settings
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        spareWidth = \
            cellToTheLeft.width - settings.mainLine - settings.hCellPadding
        boxWidth = self.minWidth - 2 * settings.hCellPadding
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth

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

