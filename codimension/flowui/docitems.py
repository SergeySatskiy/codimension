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
from math import ceil
from ui.qt import (Qt, QPen, QBrush, QPainterPath, QGraphicsPathItem,
                   QGraphicsItem, QStyleOptionGraphicsItem, QStyle, QFont,
                   QGraphicsRectItem, QCursor, QDesktopServices, QUrl)
from utils.globals import GlobalData
from utils.misc import resolveLinkPath
from .auxitems import Connector, SVGItem
from .items import CellElement
from .routines import distance, getCommentBoxPath, getDocBoxPath
from .commentitems import CommentCellBase



class DocCellBase(CommentCellBase, QGraphicsRectItem):

    """Base class for all doc cells"""

    def __init__(self, itemRef, cmlRef, canvas, x, y):
        CommentCellBase.__init__(self, itemRef, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.cmlRef = cmlRef

        # They all have the same icon
        if cmlRef.link is not None and cmlRef.anchor is not None:
            self.iconItem = SVGItem('docanchor.svg', self)
            self.iconItem.setToolTip('Jump to the documentation')
            self.iconItem.setCursor(QCursor(Qt.PointingHandCursor))
        else:
            if cmlRef.link is not None:
                self.iconItem = SVGItem('doclink.svg', self)
                self.iconItem.setToolTip('Jump to the documentation')
                self.iconItem.setCursor(QCursor(Qt.PointingHandCursor))
            else:
                self.iconItem = SVGItem('anchor.svg', self)
                self.iconItem.setToolTip('Documentation anchor')


        # They all are double clickable
        # This makes double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def _getText(self):
        """Provides text"""
        if self._text is None:
            self._text = self.cmlRef.getTitle()
            if self.canvas.settings.hidecomments:
                self.setToolTip('<pre>' + escape(self._text) + '</pre>')
                self._text = ''
        return self._text

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        self.onDoubleClick(self.cmlRef.ref.parts[0].beginLine,
                           self.cmlRef.ref.parts[0].beginPos)

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

        fileName, lineNo = resolveLinkPath(self.cmlRef.link,
                                           self._editor.getFileName())
        if fileName:
            GlobalData().mainWindow.openFile(fileName, lineNo)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self._getText()

        self.iconItem.setHeight(self.getIconHeight())
        if self._text:
            self._textRect = self.getBoundingRect(self._text)
            self.minWidth = self._textRect.width() + settings.hDocLinkPadding
            self.minHeight = self._textRect.height()
        else:
            self.minWidth = 0
            self.minHeight = self.iconItem.height()

        self.minHeight += 2 * (settings.vCellPadding + settings.vDocLinkPadding)
        self.minWidth += 2 * (settings.hCellPadding + settings.hDocLinkPadding) + \
                         self.iconItem.width()

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
        cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # Not implemented yet
            return

        settings = self.canvas.settings
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

        settings = self.canvas.settings
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)
        scene.addItem(self)

        self.iconItem.setPos(
            baseX + settings.hCellPadding + settings.hDocLinkPadding,
            baseY + self.minHeight / 2 - self.iconItem.height() / 2)
        scene.addItem(self.iconItem)

    def paint(self, painter, option, widget):
        """Draws the independent comment"""
        settings = self.canvas.settings

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(settings.docLinkLineColor)
            pen.setWidth(settings.docLinkLineWidth)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

        brush = QBrush(settings.docLinkBGColor)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                rectWidth, rectHeight, 3, 3)

        if self._text:
            # Draw the text in the rectangle
            font = QFont(settings.monoFont)
            font.setItalic(True)
            painter.setFont(font)
            pen = QPen(settings.docLinkFGColor)
            painter.setPen(pen)
            painter.drawText(
                self._leftEdge + settings.hCellPadding +
                    settings.hDocLinkPadding + self.iconItem.width() +
                    settings.hDocLinkPadding,
                self.baseY + settings.vCellPadding + settings.vDocLinkPadding,
                self._textRect.width(), self._textRect.height(),
                Qt.AlignLeft, self._text)

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return self.cmlRef.getAbsPosRange()

    def getLineRange(self):
        """Provides the line range"""
        return self.cmlRef.getLineRange()

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        return distance(absPos, self.cmlRef.ref.parts[0].begin,
                        self.cmlRef.ref.parts[-1].end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        return distance(line, self.cmlRef.ref.parts[0].beginLine,
                        self.cmlRef.ref.parts[-1].endLine)

    def copyToClipboard(self):
        """Copies the item to a clipboard"""
        self._copyToClipboard(self.cmlRef.ref.parts)



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
        self.connector.penColor = settings.docLinkLineColor
        self.connector.penWidth = settings.docLinkLineWidth

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Independent CML doc comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])



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

        self.connector = Connector(settings, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.docLinkLineColor
        self.connector.penWidth = settings.docLinkLineWidth

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Leading CML doc comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])


class AboveDocCell(DocCellBase):

    """Represents a single leading doc link which is above certain blocks.

    Blocks are: try/except or for/else or while/else
    i.e. those which are scopes located in a single row
    """

    def __init__(self, itemRef, cmlRef, canvas, x, y):
        DocCellBase.__init__(self, itemRef, cmlRef, canvas, x, y)
        self.kind = CellElement.ABOVE_DOC
        self.needConnector = False

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        if self.needConnector:
            settings = self.canvas.settings
            self.connector = Connector(
                settings, baseX + settings.mainLine, baseY,
                baseX + settings.mainLine, baseY + self.height)
            scene.addItem(self.connector)

        DocCellBase.draw(self, scene,
                         baseX + self.canvas.settings.mainLine +
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

        self.connector = Connector(settings, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self._leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self._leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.docLinkLineColor
        self.connector.penWidth = settings.docLinkLineWidth

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.getLineRange()
        return "Leading CML doc comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

