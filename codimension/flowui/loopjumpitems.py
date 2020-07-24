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

# pylint: disable=C0305
# pylint: disable=R0902
# pylint: disable=R0913

from ui.qt import QGraphicsRectItem, QPen, Qt, QGraphicsItem, QBrush
from .cellelement import CellElement
from .colormixin import ColorMixin
from .textmixin import TextMixin
from .auxitems import Connector


class LoopJumpBase(CellElement, TextMixin, ColorMixin, QGraphicsRectItem):

    """Base class for 'break' and 'continue'"""

    def __init__(self, ref, canvas, x, y, bgColor, fgColor, borderColor):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, bgColor, fgColor, borderColor)
        QGraphicsRectItem.__init__(self)

        self.connector = None

        # Cache for the size
        self.xPos = None
        self.yPos = None
        self.rectWidth = None
        self.rectHeight = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def renderCell(self, customText, hPadding, vPadding):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self, customText=customText)

        vPadding = 2 * (vPadding + settings.vCellPadding)
        self.minHeight = self.textRect.height() + vPadding

        hPadding = 2 * (hPadding + settings.hCellPadding)
        self.minWidth = self.textRect.width() + hPadding

        if settings.noContent:
            self.minWidth = max(self.minWidth, settings.minWidth)

        # Add comment and documentation badges
        self.appendCommentBadges()
        if self.aboveBadges.hasAny():
            self.minHeight += self.aboveBadges.height + settings.badgeToScopeVPadding
        self.minWidth = max(settings.mainLine + settings.badgeGroupSpacing +
                            self.aboveBadges.width + settings.hCellPadding,
                            self.minWidth)

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize(self):
        """Calculates the size"""
        settings = self.canvas.settings
        self.xPos = self.baseX + settings.hCellPadding
        self.yPos = self.baseY + settings.vCellPadding
        self.rectWidth = self.minWidth - 2 * settings.hCellPadding
        self.rectHeight = self.minHeight - 2 * settings.vCellPadding

        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + settings.badgeToScopeVPadding
            self.yPos += badgeShift
            self.rectHeight -= badgeShift

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY
        settings = self.canvas.settings

        # Draw comment badges
        self.aboveBadges.draw(scene, settings, baseX, baseY, self.minWidth)
        takenByBadges = 0
        if self.aboveBadges.hasAny():
            takenByBadges = self.aboveBadges.height + settings.badgeToScopeVPadding

        # Add the connector as a separate scene item to make the selection
        # working properly
        self.connector = Connector(self.canvas,
                                   baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding + takenByBadges)
        scene.addItem(self.connector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.__calculateSize()
        self.setRect(self.xPos - penWidth,
                     self.yPos - penWidth,
                     self.rectWidth + 2 * penWidth,
                     self.rectHeight + 2 * penWidth)
        scene.addItem(self)

    def paintCell(self, painter, rectRadius):
        """Draws the cell"""
        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        painter.drawRoundedRect(self.xPos, self.yPos,
                                self.rectWidth, self.rectHeight,
                                rectRadius, rectRadius)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        hShift = (self.rectWidth - self.textRect.width()) / 2
        vShift = (self.rectHeight - self.textRect.height()) / 2
        painter.drawText(self.xPos + hShift, self.yPos + vShift,
                         self.textRect.width(), self.textRect.height(),
                         Qt.AlignLeft, self.text)


class BreakCell(LoopJumpBase):

    """Represents a single break statement"""

    def __init__(self, ref, canvas, x, y):
        LoopJumpBase.__init__(self, ref, canvas, x, y,
                              canvas.settings.breakBGColor,
                              canvas.settings.breakFGColor,
                              canvas.settings.breakBorderColor)
        self.kind = CellElement.BREAK

    def render(self):
        """Renders the cell"""
        return self.renderCell('break',
                               self.canvas.settings.breakHPadding,
                               self.canvas.settings.breakVPadding)

    def paint(self, painter, option, widget):
        """Draws the cell"""
        del option
        del widget

        self.paintCell(painter, self.canvas.settings.breakRectRadius)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Break at ' + CellElement.getLinesSuffix(self.getLineRange())


class ContinueCell(LoopJumpBase):

    """Represents a single continue statement"""

    def __init__(self, ref, canvas, x, y):
        LoopJumpBase.__init__(self, ref, canvas, x, y,
                              canvas.settings.continueBGColor,
                              canvas.settings.continueFGColor,
                              canvas.settings.continueBorderColor)
        self.kind = CellElement.CONTINUE

    def render(self):
        """Renders the cell"""
        return self.renderCell('continue',
                               self.canvas.settings.continueHPadding,
                               self.canvas.settings.continueVPadding)

    def paint(self, painter, option, widget):
        """Draws the break statement"""
        del option      # unused argument
        del widget      # unused argument

        self.paintCell(painter, self.canvas.settings.continueRectRadius)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return "Continue at " + CellElement.getLinesSuffix(self.getLineRange())

