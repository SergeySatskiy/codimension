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
# pylint: disable=R0913

from html import escape
from ui.qt import (Qt, QPen, QBrush, QPainterPath, QGraphicsItem, QFont,
                   QGraphicsRectItem, QCursor, QDesktopServices, QUrl)
from utils.globals import GlobalData
from utils.misc import resolveLinkPath
from .auxitems import Connector
from .cellelement import CellElement
from .commentitems import CommentCellBase
from .colormixin import ColorMixin
from .iconmixin import IconMixin
from .routines import getDoclinkIconAndTooltip


class DocCellBase(CommentCellBase, ColorMixin, IconMixin, QGraphicsRectItem):

    """Base class for all doc cells"""

    def __init__(self, itemRef, cmlRef, canvas, x, y):
        CommentCellBase.__init__(self, itemRef, canvas, x, y)
        ColorMixin.__init__(self, None, canvas.settings.docLinkBGColor,
                            canvas.settings.docLinkFGColor,
                            canvas.settings.docLinkBorderColor,
                            colorSpec=cmlRef)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.cmlRef = cmlRef
        pixmapFile, tooltip = getDoclinkIconAndTooltip(self.cmlRef)

        # They all have an icon
        if cmlRef.link is not None and cmlRef.anchor is not None:
            IconMixin.__init__(self, canvas, pixmapFile, tooltip)
            self.iconItem.setCursor(QCursor(Qt.PointingHandCursor))
        else:
            if cmlRef.link is not None:
                IconMixin.__init__(self, canvas, pixmapFile, tooltip)
                self.iconItem.setCursor(QCursor(Qt.PointingHandCursor))
            else:
                IconMixin.__init__(self, canvas, pixmapFile, tooltip)

        # They all are double clickable
        # This makes double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def mouseClickLinkIcon(self):
        """Follows the link"""
        if self.cmlRef.link is None:
            return

        # http://... an external browser will be invoked
        # https://... an external browser will be invoked
        # [file:]absolute path
        # [file:]relative path. The relative is tried to the current file
        #                       and then to the project root
        if self.cmlRef.link.startswith('http://') or \
           self.cmlRef.link.startswith('https://'):
            QDesktopServices.openUrl(QUrl(self.cmlRef.link))
            return

        fileName, anchorOrLine = resolveLinkPath(
            self.cmlRef.link, self.getEditor().getFileName())
        if fileName:
            GlobalData().mainWindow.openFile(fileName, anchorOrLine)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        title = self.cmlRef.getTitle()
        self.setupText(self, customText=title, customReplacement='')

        if self.text:
            self.minWidth = self.textRect.width() + settings.hDocLinkPadding
            self.minHeight = self.textRect.height()
        else:
            self.minWidth = 0
            self.minHeight = self.iconItem.iconHeight()
            if settings.hidecomments:
                if title:
                    self.iconItem.setToolTip(self.iconItem.toolTip() +
                                             '<hr/><pre>' + escape(title) +
                                             '</pre>')

        self.minHeight += 2 * (settings.vCellPadding + \
                          settings.vDocLinkPadding)
        self.minWidth += 2 * (settings.hCellPadding + \
                         settings.hDocLinkPadding) + \
                         self.iconItem.iconWidth()

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
        if self.kind == CellElement.ABOVE_DOC:
            return

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # Not implemented yet
            return

        spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth
        boxWidth = self.minWidth
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        self._setupConnector()
        scene.addItem(self.connector)

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        settings = self.canvas.settings
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)
        scene.addItem(self)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hDocLinkPadding,
            baseY + self.minHeight / 2 - self.iconItem.iconHeight() / 2)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings
        painter.setPen(self.getPainterPen(self.isSelected(), self.borderColor))
        painter.setBrush(QBrush(self.bgColor))

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                baseY + settings.vCellPadding,
                                rectWidth, rectHeight, 0, 0)

        if self.text:
            # Draw the text in the rectangle
            font = QFont(settings.monoFont)
            font.setItalic(True)
            painter.setFont(font)
            pen = QPen(self.fgColor)
            painter.setPen(pen)
            painter.drawText(
                self._leftEdge + settings.hCellPadding +
                settings.hDocLinkPadding + self.iconItem.iconWidth() +
                settings.hDocLinkPadding,
                baseY + settings.vCellPadding + settings.vDocLinkPadding,
                self.textRect.width(), self.textRect.height(),
                Qt.AlignLeft, self.text)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.cmlRef.getAbsPosRange()

    def getLineRange(self):
        """Provides the line range"""
        return self.cmlRef.getLineRange()

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.cmlRef.ref.parts)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Link/anchor at ' + \
               CellElement.getLinesSuffix(self.getLineRange())


class IndependentDocCell(DocCellBase):

    """Represents a single independent CML doc comment"""

    def __init__(self, ref, canvas, x, y):
        DocCellBase.__init__(self, ref, ref, canvas, x, y)
        self.kind = CellElement.INDEPENDENT_DOC
        self.leadingForElse = False
        self.sideForElse = False

    def _setupConnector(self):
        """Sets the path for painting"""
        settings = self.canvas.settings

        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        self._leftEdge = \
            cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding

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
        self.connector.penColor = self.borderColor
        self.connector.penWidth = settings.boxLineWidth



class LeadingDocCell(DocCellBase):

    """Represents a single leading CML doc comment"""

    def __init__(self, itemRef, cmlRef, canvas, x, y):
        DocCellBase.__init__(self, itemRef, cmlRef, canvas, x, y)
        self.kind = CellElement.LEADING_DOC

    def _setupConnector(self):
        """Sets the path for painting"""
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

        shift = self.hShift * 2 * settings.openGroupHSpacer
        self._leftEdge += shift

        self.connector = Connector(self.canvas, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = self.borderColor
        self.connector.penWidth = settings.boxLineWidth



class AboveDocCell(DocCellBase):

    """Represents a single leading doc link which is above certain blocks.

    Blocks are: try/except or for/else or while/else
    i.e. those which are scopes located in a single row
    """

    def __init__(self, itemRef, cmlRef, canvas, x, y):
        DocCellBase.__init__(self, itemRef, cmlRef, canvas, x, y)
        self.kind = CellElement.ABOVE_DOC
        self.needConnector = False

        # Decorators have a small badge so the connector needs to touch it
        # more to the left than the usual main line
        self.smallBadge = False
        self.hanging = False

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        settings = self.canvas.settings
        mainLine = settings.mainLine
        if self.smallBadge:
            mainLine = settings.decorMainLine
        if self.needConnector:
            yShift = 0
            if self.hanging:
                yShift = settings.vCellPadding
            self.connector = Connector(
                self.canvas, baseX + mainLine, baseY + yShift,
                baseX + mainLine, baseY + self.height + yShift)
            scene.addItem(self.connector)

        DocCellBase.draw(self, scene,
                         baseX + mainLine +
                         self.canvas.settings.hCellPadding, baseY)

    def _setupConnector(self):
        """Sets the path for painting"""
        settings = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        # Dirty hack: see the overriden draw() member: the baseX has already
        # been adjusted with mainLine and hCellPadding
        self._leftEdge = self.baseX

        self.connector = Connector(self.canvas, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = self.borderColor
        self.connector.penWidth = settings.boxLineWidth

