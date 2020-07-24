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

"""Various items used to represent a control flow on a virtual canvas"""

# pylint: disable=C0305

from ui.qt import Qt, QPointF, QPen, QBrush, QGraphicsRectItem, QGraphicsItem
from .auxitems import Connector, BadgeItem, SVGItem, DecorBadgeItem
from .cml import CMLVersion, CMLsw
from .colormixin import ColorMixin
from .iconmixin import IconMixin
from .cellelement import CellElement
from .textmixin import TextMixin
from .routines import getDocComment
from .abovebadges import AboveBadgesDivider, AboveBadgesSpacer


class CodeBlockCell(CellElement, TextMixin, ColorMixin, QGraphicsRectItem):

    """Represents a single code block"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.codeBlockBGColor,
                            self.canvas.settings.codeBlockFGColor,
                            self.canvas.settings.codeBlockBorderColor)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.CODE_BLOCK
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.textRect.height() + vPadding
        hPadding = 2 * (settings.hCellPadding + settings.hTextPadding)
        self.minWidth = max(self.textRect.width() + hPadding,
                            settings.minWidth)

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

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        # Add the connector as a separate scene item to make the selection
        # working properly
        settings = self.canvas.settings
        self.connector = Connector(self.canvas, baseX + settings.mainLine,
                                   baseY,
                                   baseX + settings.mainLine,
                                   baseY + self.height)
        scene.addItem(self.connector)

        # Draw comment badges
        self.aboveBadges.draw(scene, settings, baseX, baseY, self.minWidth)
        takenByBadges = 0
        if self.aboveBadges.hasAny():
            takenByBadges = self.aboveBadges.height + settings.badgeToScopeVPadding

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        xPos = baseX + settings.hCellPadding
        yPos = baseY + settings.vCellPadding
        penWidth = settings.selectPenWidth - 1
        self.setRect(
            xPos - penWidth, yPos - penWidth + takenByBadges,
            self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
            self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)
        scene.addItem(self)

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        yPos = self.baseY + settings.vCellPadding
        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + settings.badgeToScopeVPadding
            yPos += badgeShift
            rectHeight -= badgeShift

        painter.drawRect(self.baseX + settings.hCellPadding,
                         yPos, rectWidth, rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        textWidth = self.textRect.width() + 2 * settings.hTextPadding
        textShift = (rectWidth - textWidth) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding +
            settings.hTextPadding + textShift,
            yPos + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Code block at ' + \
            CellElement.getLinesSuffix(self.getLineRange())


class ReturnCell(CellElement,
                 TextMixin, ColorMixin, IconMixin, QGraphicsRectItem):

    """Represents a single return statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.returnBGColor,
                            self.canvas.settings.returnFGColor,
                            self.canvas.settings.returnBorderColor)
        IconMixin.__init__(self, canvas, 'return.svg', 'return')
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.RETURN
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        customText = self.ref.getDisplayValue()
        if not customText:
            customText = 'None'
        self.setupText(self, customText=customText)

        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.textRect.height() + vPadding
        self.minWidth = max(
            self.textRect.width() + 2 * settings.hCellPadding +
            settings.hTextPadding + settings.returnRectRadius +
            2 * settings.hTextPadding + self.iconItem.iconWidth(),
            settings.minWidth)

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
        self.connector = Connector(self.canvas, baseX + settings.mainLine,
                                   baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding + takenByBadges)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth + takenByBadges,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight/2 - self.iconItem.iconHeight()/2 + takenByBadges/2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        yPos = self.baseY + settings.vCellPadding
        xPos = self.baseX + settings.hCellPadding

        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + settings.badgeToScopeVPadding
            yPos += badgeShift
            rectHeight -= badgeShift

        painter.drawRoundedRect(
            xPos, yPos, rectWidth, rectHeight,
            settings.returnRectRadius, settings.returnRectRadius)
        lineXPos = xPos + self.iconItem.iconWidth() + \
                   2 * settings.hTextPadding
        painter.drawLine(lineXPos, yPos, lineXPos, yPos + rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        availWidth = self.minWidth - 2 * settings.hCellPadding - \
                     self.iconItem.iconWidth() - 2 * settings.hTextPadding - \
                     settings.hTextPadding - settings.returnRectRadius
        textShift = (availWidth - self.textRect.width()) / 2
        painter.drawText(
            xPos + self.iconItem.iconWidth() +
            3 * settings.hTextPadding + textShift,
            yPos + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getLineRange(self):
        """Provides the item line range"""
        if self.ref.value is not None:
            return [self.ref.body.beginLine, self.ref.value.endLine]
        return [self.ref.body.beginLine, self.ref.body.endLine]

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.ref.value is not None:
            return [self.ref.body.begin, self.ref.value.end]
        return [self.ref.body.begin, self.ref.body.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Return at ' + CellElement.getLinesSuffix(self.getLineRange())


class RaiseCell(CellElement,
                TextMixin, ColorMixin, IconMixin, QGraphicsRectItem):

    """Represents a single raise statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.raiseBGColor,
                            self.canvas.settings.raiseFGColor,
                            self.canvas.settings.raiseBorderColor)
        IconMixin.__init__(self, canvas, 'raise.svg', 'raise')
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.RAISE
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.textRect.height() + vPadding
        self.minWidth = max(
            self.textRect.width() + 2 * settings.hCellPadding +
            settings.hTextPadding + settings.returnRectRadius +
            2 * settings.hTextPadding + self.iconItem.iconWidth(),
            settings.minWidth)

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
        self.connector = Connector(self.canvas, baseX + settings.mainLine,
                                   baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding + takenByBadges)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth + takenByBadges,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight/2 - self.iconItem.iconHeight()/2 + takenByBadges/2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the raise statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        yPos = self.baseY + settings.vCellPadding
        xPos = self.baseX + settings.hCellPadding

        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + settings.badgeToScopeVPadding
            yPos += badgeShift
            rectHeight -= badgeShift

        painter.drawRoundedRect(
            xPos, yPos, rectWidth, rectHeight,
            settings.returnRectRadius, settings.returnRectRadius)

        lineXPos = xPos + self.iconItem.iconWidth() + \
                   2 * settings.hTextPadding
        painter.drawLine(lineXPos, yPos, lineXPos, yPos + rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        availWidth = self.minWidth - 2 * settings.hCellPadding - \
                     self.iconItem.iconWidth() - 2 * settings.hTextPadding - \
                     settings.hTextPadding - settings.returnRectRadius
        textShift = (availWidth - self.textRect.width()) / 2
        painter.drawText(
            xPos + self.iconItem.iconWidth() +
            3 * settings.hTextPadding + textShift,
            yPos + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getLineRange(self):
        """Provides the line range"""
        if self.ref.value is not None:
            return [self.ref.body.beginLine, self.ref.value.endLine]
        return [self.ref.body.beginLine, self.ref.body.endLine]

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.ref.value is not None:
            return [self.ref.body.begin, self.ref.value.end]
        return [self.ref.body.begin, self.ref.body.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Raise at ' + CellElement.getLinesSuffix(self.getLineRange())


class AssertCell(CellElement,
                 TextMixin, ColorMixin, IconMixin, QGraphicsRectItem):

    """Represents a single assert statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.assertBGColor,
                            self.canvas.settings.assertFGColor,
                            self.canvas.settings.assertBorderColor)
        IconMixin.__init__(self, canvas, 'assert.svg', 'assert')
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.ASSERT
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        # for an arrow box
        singleCharRect = self.getBoundingRect('W')
        self.__diamondHeight = singleCharRect.height() + \
                               2 * settings.vTextPadding
        self.__diamondWidth = settings.ifWidth * 2 + singleCharRect.width() + \
                              2 * settings.hTextPadding

        self.minHeight = self.textRect.height() + \
                         2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = max(
            self.textRect.width() + 2 * settings.hCellPadding +
            2 * settings.hTextPadding + self.__diamondWidth,
            settings.minWidth)

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
        self.connector = Connector(self.canvas, baseX + settings.mainLine,
                                   baseY,
                                   baseX + settings.mainLine,
                                   baseY + self.height)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth + takenByBadges,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)

        settings = self.canvas.settings
        self.iconItem.setPos(
            baseX + self.__diamondWidth / 2 +
            settings.hCellPadding - self.iconItem.iconWidth() / 2,
            baseY + self.minHeight / 2 - self.iconItem.iconHeight() / 2 + takenByBadges/2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        takenByBadges = 0
        if self.aboveBadges.hasAny():
            takenByBadges = self.aboveBadges.height + settings.badgeToScopeVPadding

        dHalf = int(self.__diamondHeight / 2.0)
        dx1 = self.baseX + settings.hCellPadding
        dy1 = self.baseY + takenByBadges + int((self.minHeight - takenByBadges)/2)
        dx2 = dx1 + settings.ifWidth
        dy2 = dy1 - dHalf
        dx3 = dx1 + self.__diamondWidth - settings.ifWidth
        dy3 = dy2
        dx4 = dx3 + settings.ifWidth
        dy4 = dy1
        dx5 = dx3
        dy5 = dy2 + 2 * dHalf
        dx6 = dx2
        dy6 = dy5

        painter.drawPolygon(QPointF(dx1, dy1), QPointF(dx2, dy2),
                            QPointF(dx3, dy3), QPointF(dx4, dy4),
                            QPointF(dx5, dy5), QPointF(dx6, dy6))

        painter.drawRect(dx4 + 1, self.baseY + settings.vCellPadding + takenByBadges,
                         self.minWidth - 2 * settings.hCellPadding -
                         self.__diamondWidth,
                         self.minHeight - 2 * settings.vCellPadding - takenByBadges)


        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        availWidth = \
            self.minWidth - 2 * settings.hCellPadding - self.__diamondWidth
        textWidth = self.textRect.width() + 2 * settings.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText(
            dx4 + settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding + takenByBadges,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getLineRange(self):
        """Provides the line range"""
        if self.ref.message is not None:
            return [self.ref.body.beginLine, self.ref.message.endLine]
        if self.ref.test is not None:
            return[self.ref.body.beginLine, self.ref.test.endLine]
        return [self.ref.body.beginLine, self.ref.body.endLine]

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        if self.ref.message is not None:
            return [self.ref.body.begin, self.ref.message.end]
        if self.ref.test is not None:
            return[self.ref.body.begin, self.ref.test.end]
        return [self.ref.body.begin, self.ref.body.end]

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Assert at ' + CellElement.getLinesSuffix(self.getLineRange())


class SysexitCell(CellElement,
                  TextMixin, ColorMixin, IconMixin, QGraphicsRectItem):

    """Represents a single sys.exit(...) statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.sysexitBGColor,
                            self.canvas.settings.sysexitFGColor,
                            self.canvas.settings.sysexitBorderColor)
        IconMixin.__init__(self, canvas, 'sysexit.svg', 'sys.exit()')
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.SYSEXIT
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        self.minHeight = \
            self.textRect.height() + \
            2 * (settings.vCellPadding + settings.vTextPadding)
        self.minWidth = max(
            self.textRect.width() + 2 * settings.hCellPadding +
            settings.hTextPadding + settings.returnRectRadius +
            2 * settings.hTextPadding + self.iconItem.iconWidth(),
            settings.minWidth)

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
        self.connector = Connector(self.canvas, baseX + settings.mainLine,
                                   baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding + takenByBadges)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth + takenByBadges,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight/2 - self.iconItem.iconHeight() / 2 + takenByBadges / 2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the sys.exit call"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        yPos = self.baseY + settings.vCellPadding
        xPos = self.baseX + settings.hCellPadding

        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + settings.badgeToScopeVPadding
            yPos += badgeShift
            rectHeight -= badgeShift

        painter.drawRoundedRect(
            xPos, yPos, rectWidth, rectHeight,
            settings.returnRectRadius, settings.returnRectRadius)
        lineXPos = xPos + self.iconItem.iconWidth() + \
                   2 * settings.hTextPadding
        painter.drawLine(lineXPos, yPos, lineXPos, yPos + rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        availWidth = \
            self.minWidth - 2 * settings.hCellPadding - \
            self.iconItem.iconWidth() - \
            2 * settings.hTextPadding - \
            settings.hTextPadding - settings.returnRectRadius
        textShift = (availWidth - self.textRect.width()) / 2
        painter.drawText(
            xPos + self.iconItem.iconWidth() +
            3 * settings.hTextPadding + textShift,
            yPos + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getSelectTooltip(self):
        """Provides tooltip"""
        return 'Sys.exit() at ' + \
            CellElement.getLinesSuffix(self.getLineRange())


class ImportCell(CellElement,
                 TextMixin, ColorMixin, IconMixin, QGraphicsRectItem):

    """Represents a single import statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.importBGColor,
                            self.canvas.settings.importFGColor,
                            self.canvas.settings.importBorderColor)
        IconMixin.__init__(self, canvas, 'import.svg', 'import')
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.IMPORT
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        self.minHeight = \
            self.textRect.height() + 2 * settings.vCellPadding + \
            2 * settings.vTextPadding
        self.minWidth = max(
            self.textRect.width() + 2 * settings.hCellPadding +
            2 * settings.hTextPadding + self.iconItem.iconWidth() +
            2 * settings.hTextPadding, settings.minWidth)

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
        self.connector = Connector(self.canvas, baseX + settings.mainLine,
                                   baseY,
                                   baseX + settings.mainLine,
                                   baseY + self.height)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth + takenByBadges,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight / 2 - self.iconItem.iconHeight() / 2 + takenByBadges / 2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the import statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        yPos = self.baseY + settings.vCellPadding
        xPos = self.baseX + settings.hCellPadding

        if self.aboveBadges.hasAny():
            badgeShift = self.aboveBadges.height + settings.badgeToScopeVPadding
            yPos += badgeShift
            rectHeight -= badgeShift

        painter.drawRect(xPos, yPos, rectWidth, rectHeight)
        lineXPos = xPos + self.iconItem.iconWidth() + \
                   2 * settings.hTextPadding
        painter.drawLine(lineXPos, yPos, lineXPos, yPos + rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        textRectWidth = self.minWidth - 2 * settings.hCellPadding - \
                        4 * settings.hTextPadding - self.iconItem.iconWidth()
        textShift = (textRectWidth - self.textRect.width()) / 2
        painter.drawText(
            xPos + self.iconItem.iconWidth() +
            3 * settings.hTextPadding + textShift,
            yPos + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getSelectTooltip(self):
        """Provides the select tooltip"""
        return 'Import at ' + CellElement.getLinesSuffix(self.getLineRange())


class DecoratorCell(CellElement,
                    TextMixin, ColorMixin, QGraphicsRectItem):

    """Represents a single decorator statement"""

    def __init__(self, ref, canvas, x, y, scopeItem):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)

        self.scopeItem = scopeItem
        self.isFirst = False

        if self.scopeItem.kind == CellElement.CLASS_SCOPE:
            bgColor = self.canvas.settings.classScopeBGColor
            fgColor = self.canvas.settings.classScopeFGColor
            borderColor = self.canvas.settings.classScopeBorderColor
        else:
            bgColor = self.canvas.settings.funcScopeBGColor
            fgColor = self.canvas.settings.funcScopeFGColor
            borderColor = self.canvas.settings.funcScopeBorderColor

        ColorMixin.__init__(self, ref, bgColor, fgColor, borderColor)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.DECORATOR
        self.upperConnector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        s = self.canvas.settings

        self.aboveBadges.append(DecorBadgeItem(self))
        self.aboveBadges.append(AboveBadgesSpacer(s.badgeGroupSpacing))
        self.aboveBadges.append(AboveBadgesDivider())
        self.appendCommentBadges()

        self.setupText(self)

        vPadding = 2 * (s.vCellPadding + s.vTextPadding)
        textHeight = self.textRect.height()
        self.minHeight = vPadding + textHeight + self.aboveBadges.height + s.badgeToScopeVPadding

        self.minWidth = max(
            self.textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
            self.aboveBadges.width + 2 * s.hCellPadding,
            s.minWidth)

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

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

        # Add dotted connection
        if self.isFirst:
            parentCanvas = self.canvas.canvas
            cellToTheLeft = parentCanvas.cells[
                self.canvas.addr[1]][self.canvas.addr[0] - 1]
            if cellToTheLeft.kind == CellElement.SIDE_COMMENT:
                cellToTheLeft = parentCanvas.cells[
                    self.canvas.addr[1]][self.canvas.addr[0] - 2]
            cellToTheLeft = cellToTheLeft.cells[0][0]

            startXPos = cellToTheLeft.baseX + settings.hCellPadding + cellToTheLeft.aboveBadges[0].width
            yPos = self.baseY + settings.vCellPadding + self.aboveBadges.height / 2

            self._connector = Connector(
                    self.canvas,
                    startXPos,
                    yPos,
                    self.baseX + settings.hCellPadding - settings.boxLineWidth,
                    yPos)
            self._connector.penStyle = Qt.DotLine
            scene.addItem(self._connector)

            cellToTheLeft.aboveBadges.raizeAllButFirst()
        else:
            # find the above decorator
            decorAbove = None
            dRow = self.addr[1] - 1
            dCol = self.addr[0]
            while True:
                decorAbove = self.canvas.cells[dRow][dCol]
                if decorAbove.kind == CellElement.DECORATOR:
                    break
                dRow -= 1

            yBeginPos = decorAbove.baseY + settings.vCellPadding + decorAbove.aboveBadges[0].height / 2
            yEndPos = self.baseY + settings.vCellPadding + self.aboveBadges[0].height / 2

            self._vDotConnector = Connector(
                    self.canvas, self.baseX, yBeginPos,
                    self.baseX, yEndPos)
            self._vDotConnector.penStyle = Qt.DotLine
            scene.addItem(self._vDotConnector)

            self._hDotConnector = Connector(
                    self.canvas, self.baseX, yEndPos,
                    self.baseX + settings.hCellPadding, yEndPos)
            self._hDotConnector.penStyle = Qt.DotLine
            scene.addItem(self._hDotConnector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth + takenByBadges,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth - takenByBadges)

        scene.addItem(self)

    def paint(self, painter, option, widget):
        """Draws the import statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        takenByBadges = self.aboveBadges.height + settings.badgeToScopeVPadding
        yPos = self.baseY + settings.vCellPadding + takenByBadges
        xPos = self.baseX + settings.hCellPadding

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding - takenByBadges

        painter.drawRoundedRect(xPos, yPos, rectWidth, rectHeight,
                                settings.decorRectRadius,
                                settings.decorRectRadius)

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        painter.drawText(
            xPos + settings.hTextPadding,
            yPos + settings.vTextPadding,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft, self.text)

    def getSelectTooltip(self):
        """Provides the select tooltip"""
        return 'Decorator at ' + CellElement.getLinesSuffix(self.getLineRange())

    def getParentIfID(self):
        return self.scopeItem.ref.getParentIfID()


class IfCell(CellElement, TextMixin, ColorMixin, QGraphicsRectItem):

    """Represents a single if statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        TextMixin.__init__(self)
        ColorMixin.__init__(self, ref, self.canvas.settings.ifBGColor,
                            self.canvas.settings.ifFGColor,
                            self.canvas.settings.ifBorderColor)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.IF
        self.vConnector = None
        self.rhsConnector = None
        self.leftBadge = None
        self.yBelow = False
        self.needHConnector = True
        self.rhsShift = 0

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.setupText(self)

        self.minHeight = self.textRect.height() + \
                         2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = max(
            self.textRect.width() +
            2 * settings.hCellPadding + 2 * settings.hTextPadding +
            2 * settings.ifWidth,
            settings.minWidth)
        self.minWidth += self.hShift * 2 * settings.openGroupHSpacer

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

    def __calcPolygon(self, takenByBadges):
        """Calculates the polygon"""
        settings = self.canvas.settings

        shift = self.hShift * 2 * settings.openGroupHSpacer
        baseX = self.baseX + shift

        self.x1 = baseX + settings.hCellPadding
        self.y1 = self.baseY + (self.minHeight - takenByBadges)/ 2 + takenByBadges
        self.x2 = self.x1 + settings.ifWidth
        self.y2 = self.baseY + settings.vCellPadding + takenByBadges
        self.x3 = baseX + self.minWidth - \
                  settings.hCellPadding - settings.ifWidth - shift
        self.y3 = self.y2
        self.x4 = self.x3 + settings.ifWidth
        self.y4 = self.y1
        self.x5 = self.x3
        self.y5 = self.y1 + (self.y1 - self.y2)
        self.x6 = self.x2
        self.y6 = self.y5

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

        self.__calcPolygon(takenByBadges)

        hShift = self.hShift * 2 * settings.openGroupHSpacer
        self.baseX += hShift

        # Add the connectors as separate scene items to make the selection
        # working properly
        settings = self.canvas.settings
        self.vConnector = Connector(self.canvas,
                                    self.baseX + settings.mainLine,
                                    self.baseY,
                                    self.baseX + settings.mainLine,
                                    self.baseY + self.height)
        scene.addItem(self.vConnector)

        if self.needHConnector:
            # Need the RHS connector
            self.rhsConnector = Connector(self.canvas, self.x4, self.y4,
                                          self.baseX + self.width - hShift,
                                          self.y4)
        else:
            # Need the bottom connector because the RHS layout used some space
            # at the left
            xPos = self.baseX + self.width - self.rhsShift + settings.mainLine - hShift
            self.rhsConnector = Connector(self.canvas,
                                          xPos,
                                          self.y5,
                                          xPos,
                                          self.baseY + self.height)

        scene.addItem(self.rhsConnector)

        self.yBelow = CMLVersion.find(self.ref.leadingCMLComments,
                                      CMLsw) is not None
        if self.yBelow:
            self.leftBadge = BadgeItem(self, 'y')
            self.leftBadge.setFGColor(settings.ifYBranchTextColor)
        else:
            self.leftBadge = BadgeItem(self, 'n')
            self.leftBadge.setFGColor(settings.ifNBranchTextColor)

        self.leftBadge.setNeedRectangle(False)
        self.leftBadge.moveTo(self.x1 - self.leftBadge.width / 2,
                              self.y3 - self.leftBadge.height / 2)

        penWidth = settings.selectPenWidth - 1
        self.setRect(self.x1 - penWidth, self.y2 - penWidth,
                     self.x4 - self.x1 + 2 * penWidth,
                     self.y6 - self.y2 + 2 * penWidth)
        scene.addItem(self)
        scene.addItem(self.leftBadge)

        self.baseX -= hShift

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        takenByBadges = 0
        if self.aboveBadges.hasAny():
            takenByBadges = self.aboveBadges.height + settings.badgeToScopeVPadding

        painter.drawPolygon(
            QPointF(self.x1, self.y1), QPointF(self.x2, self.y2),
            QPointF(self.x3, self.y3), QPointF(self.x4, self.y4),
            QPointF(self.x5, self.y5), QPointF(self.x6, self.y6))

        # Draw the text in the rectangle
        pen = QPen(self.fgColor)
        painter.setPen(pen)
        painter.setFont(settings.monoFont)
        availWidth = self.x3 - self.x2
        textWidth = self.textRect.width() + 2 * settings.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText(
            self.x2 + settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding + takenByBadges,
            self.textRect.width(), self.textRect.height(),
            Qt.AlignLeft | Qt.AlignVCenter, self.text)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'If at ' + CellElement.getLinesSuffix(self.getLineRange())

