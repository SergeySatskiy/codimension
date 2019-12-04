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

"""break and continue cells"""

from html import escape
from ui.qt import QGraphicsRectItem, QPen, Qt, QGraphicsItem, QBrush
from .items import CellElement
from .colormixin import ColorMixin
from .auxitems import Connector


class BreakCell(CellElement, ColorMixin, QGraphicsRectItem):

    """Represents a single break statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        ColorMixin.__init__(self, ref, self.canvas.settings.breakBGColor,
                            self.canvas.settings.breakFGColor,
                            self.canvas.settings.breakBorderColor)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.BREAK
        self.__textRect = None
        self.__vSpacing = 0
        self.__hSpacing = 4
        self.connector = None

        # Cache for the size
        self.x1 = None
        self.y1 = None
        self.w = None
        self.h = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getText(self):
        """Provides the text"""
        if self._text is None:
            self._text = self.getReplacementText()
            displayText = 'break'
            if self._text is None:
                self._text = displayText
            else:
                if displayText:
                    self.setToolTip('<pre>' + escape(displayText) + '</pre>')
            if self.canvas.settings.noContent:
                if displayText:
                    self.setToolTip('<pre>' + escape(displayText) + '</pre>')
                self._text = ''
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect(self._getText())
        vPadding = 2 * (self.__vSpacing + settings.vCellPadding)
        self.minHeight = self.__textRect.height() + vPadding
        hPadding = 2 * (self.__hSpacing + settings.hCellPadding)
        self.minWidth = self.__textRect.width() + hPadding
        if settings.noContent:
            self.minWidth = max(self.minWidth, settings.minWidth)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize(self):
        """Calculates the size"""
        settings = self.canvas.settings
        self.x1 = self.baseX + settings.hCellPadding
        self.y1 = self.baseY + settings.vCellPadding
        self.w = self.minWidth - 2 * settings.hCellPadding
        self.h = self.minHeight - 2 * settings.hCellPadding

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        # Add the connector as a separate scene item to make the selection
        # working properly
        settings = self.canvas.settings
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding)
        scene.addItem(self.connector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.__calculateSize()
        self.setRect(self.x1 - penWidth, self.y1 - penWidth,
                     self.w + 2 * penWidth, self.h + 2 * penWidth)
        scene.addItem(self)

    def paint(self, painter, option, widget):
        """Draws the break statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            pen = QPen(settings.selectColor)
            pen.setWidth(settings.selectPenWidth)
            pen.setJoinStyle(Qt.RoundJoin)
        else:
            pen = QPen(self.borderColor)
        painter.setPen(pen)

        brush = QBrush(self.bgColor)
        painter.setBrush(brush)

        painter.drawRoundedRect(self.x1, self.y1, self.w, self.h, 2, 2)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        hShift = (self.w - self.__textRect.width()) / 2
        vShift = (self.h - self.__textRect.height()) / 2
        painter.drawText(self.x1 + hShift, self.y1 + vShift,
                         self.__textRect.width(), self.__textRect.height(),
                         Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return 'Break at lines ' + str(lineRange[0]) + '-' + str(lineRange[1])


class ContinueCell(CellElement, ColorMixin, QGraphicsRectItem):

    """Represents a single continue statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        ColorMixin.__init__(self, ref, self.canvas.settings.continueBGColor,
                            self.canvas.settings.continueFGColor,
                            self.canvas.settings.continueBorderColor)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.CONTINUE
        self.__textRect = None
        self.__vSpacing = 0
        self.__hSpacing = 4
        self.connector = None

        # Cache for the size
        self.x1 = None
        self.y1 = None
        self.w = None
        self.h = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getText(self):
        """Provides the text"""
        if self._text is None:
            self._text = self.getReplacementText()
            displayText = 'continue'
            if self._text is None:
                self._text = displayText
            else:
                if displayText:
                    self.setToolTip('<pre>' + escape(displayText) + '</pre>')
            if self.canvas.settings.noContent:
                if displayText:
                    self.setToolTip('<pre>' + escape(displayText) + '</pre>')
                self._text = ''
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect(self._getText())
        vPadding = 2 * (self.__vSpacing + settings.vCellPadding)
        self.minHeight = self.__textRect.height() + vPadding
        hPadding = 2 * (self.__hSpacing + settings.hCellPadding)
        self.minWidth = self.__textRect.width() + hPadding
        if settings.noContent:
            self.minWidth = max(self.minWidth, settings.minWidth)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize(self):
        """Calculates the size"""
        settings = self.canvas.settings
        self.x1 = self.baseX + settings.hCellPadding
        self.y1 = self.baseY + settings.vCellPadding
        self.w = self.minWidth - 2 * settings.hCellPadding
        self.h = self.minHeight - 2 * settings.hCellPadding

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        # Add the connector as a separate scene item to make the selection
        # working properly
        settings = self.canvas.settings
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding)
        scene.addItem(self.connector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.__calculateSize()
        self.setRect(self.x1 - penWidth, self.y1 - penWidth,
                     self.w + 2 * penWidth, self.h + 2 * penWidth)

        scene.addItem(self)

    def paint(self, painter, option, widget):
        """Draws the break statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            pen = QPen(settings.selectColor)
            pen.setWidth(settings.selectPenWidth)
            pen.setJoinStyle(Qt.RoundJoin)
        else:
            pen = QPen(self.borderColor)
        painter.setPen(pen)

        brush = QBrush(self.bgColor)
        painter.setBrush(brush)

        painter.drawRoundedRect(self.x1, self.y1, self.w, self.h, 2, 2)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        hShift = (self.w - self.__textRect.width()) / 2
        vShift = (self.h - self.__textRect.height()) / 2
        painter.drawText(self.x1 + hShift, self.y1 + vShift,
                         self.__textRect.width(), self.__textRect.height(),
                         Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Continue at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

