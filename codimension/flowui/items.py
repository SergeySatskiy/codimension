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

from sys import maxsize
from cgi import escape
from ui.qt import (Qt, QPointF, QPen, QBrush, QPainterPath, QColor,
                   QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem,
                   QStyleOptionGraphicsItem, QStyle)
from .auxitems import SVGItem, Connector, Text, CMLLabel
from .cml import CMLVersion, CMLsw, CMLcc, CMLrt


def getBorderColor(color):
    """Creates a darker version of the color"""
    red = color.red()
    green = color.green()
    blue = color.blue()

    delta = 60
    if isDark(red, green, blue):
        # Need lighter color
        return QColor(min(red + delta, 255),
                      min(green + delta, 255),
                      min(blue + delta, 255), color.alpha())
    # Need darker color
    return QColor(max(red - delta, 0),
                  max(green - delta, 0),
                  max(blue - delta, 0), color.alpha())


def isDark(red, green, blue):
    """True if the color is dark"""
    yiq = ((red * 299) + (green * 587) + (blue * 114)) / 1000
    return yiq < 128


def distance(val, begin, end):
    """Provides a distance between the absPos and an item"""
    if val >= begin and val <= end:
        return 0
    return min(abs(val - begin), abs(val - end))


class CellElement:

    """Base class for all the elements which could be found on the canvas"""

    UNKNOWN = -1

    VCANVAS = 0

    VACANT = 1
    H_SPACER = 2
    V_SPACER = 3

    NO_SCOPE = 99
    FILE_SCOPE = 100
    FUNC_SCOPE = 101
    CLASS_SCOPE = 102
    FOR_SCOPE = 103
    WHILE_SCOPE = 104
    TRY_SCOPE = 105
    WITH_SCOPE = 106
    DECOR_SCOPE = 107
    ELSE_SCOPE = 108
    EXCEPT_SCOPE = 109
    FINALLY_SCOPE = 110

    CODE_BLOCK = 200
    BREAK = 201
    CONTINUE = 202
    RETURN = 203
    RAISE = 204
    ASSERT = 205
    SYSEXIT = 206
    IMPORT = 207
    IF = 208
    LEADING_COMMENT = 209
    INDEPENDENT_COMMENT = 210
    SIDE_COMMENT = 211
    ABOVE_COMMENT = 212

    CONNECTOR = 300

    def __init__(self, ref, canvas, x, y):
        self.kind = self.UNKNOWN
        self.subKind = self.UNKNOWN
        self.ref = ref              # reference to the control flow object
        self.addr = [x, y]          # indexes in the current canvas
        self.canvas = canvas        # reference to the canvas
        self._editor = None
        self.cmlLabelItem = None    # Label near the item to indicate a CML
                                    # presence
        self._text = None

        self.tailComment = False

        # Filled when rendering is called
        self.width = None
        self.height = None
        self.minWidth = None
        self.minHeight = None

        # Filled when draw is called
        self.baseX = None
        self.baseY = None

    def __str__(self):
        return kindToString(self.kind) + \
               "[" + str(self.width) + ":" + str(self.height) + "]"

    def render(self):
        """Renders the graphics considering settings"""
        raise Exception("render() is not implemented for " +
                        kindToString(self.kind))

    def draw(self, scene, baseX, baseY):
        """Draws the element on the real canvas. Should respect settings."""
        del scene   # unused argument
        del baseX   # unused argument
        del baseY   # unused argument
        raise Exception("draw() is not implemented for " +
                        kindToString(self.kind))

    def getBoundingRect(self, text):
        """Provides the bounding rectangle for a monospaced font"""
        return self.canvas.settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, text)

    def getTooltip(self):
        """Provides the tooltip"""
        parts = []
        canvas = self.canvas
        while canvas is not None:
            parts.insert(0, canvas.getScopeName())
            canvas = canvas.canvas
        if self.canvas.settings.debug:
            return "::".join(parts) + "<br>Size: " + \
                str(self.width) + "x" + str(self.height) + \
                " (" + str(self.minWidth) + "x" + str(self.minHeight) + ")" + \
                " Row: " + str(self.addr[1]) + " Column: " + str(self.addr[0])
        return "::".join(parts)

    def getCanvasTooltip(self):
        """Provides the canvas tooltip"""
        parts = []
        canvas = self.canvas
        while canvas is not None:
            if not canvas.isNoScope:
                parts.insert(0, canvas.getScopeName())
            canvas = canvas.canvas
        path = " :: ".join(parts)
        if not path:
            path = " ::"
        if self.canvas.settings.debug:
            return path + "<br>Size: " + str(self.canvas.width) + "x" + \
                   str(self.canvas.height) + \
                   " (" + str(self.canvas.minWidth) + "x" + \
                   str(self.canvas.minHeight) + ")"
        return path

    def setEditor(self, editor):
        """Sets the editor counterpart"""
        self._editor = editor

    def getEditor(self):
        """Provides a reference to the editor"""
        return self._editor

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor.

        default implementation
        """
        if self._editor is None:
            return
        if event:
            if event.buttons() != Qt.LeftButton:
                return

        self._editor.gotoLine(self.ref.body.beginLine,
                              self.ref.body.beginPos)
        self._editor.setFocus()

    def scopedItem(self):
        """True if it is a scoped item"""
        return False

    def isProxyItem(self):
        """True if it is a proxy item"""
        return False

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return None

    def isComment(self):
        """True if it is a comment"""
        return False

    def isDocstring(self):
        """True if it is a docstring"""
        return False

    def getDistance(self, absPos):
        """Default implementation.

        Provides a distance between the absPos and the item
        """
        return distance(absPos, self.ref.body.begin, self.ref.body.end)

    def getLineDistance(self, line):
        """Default implementation.

        Provides a distance between the line and the item
        """
        return distance(line, self.ref.body.beginLine, self.ref.body.endLine)

    def addCMLIndicator(self, baseX, baseY, penWidth, scene, ref=None):
        """Adds a CML indicator for an item if needed"""
        if not self.canvas.settings.showCMLIndicator:
            return

        if ref is None:
            hasCML = self.ref.leadingCMLComments or self.ref.sideCMLComments
        else:
            hasCML = ref.leadingCMLComments or ref.sideCMLComments

        if hasCML:
            settings = self.canvas.settings
            self.cmlLabelItem = CMLLabel()
            self.cmlLabelItem.setPos(baseX + settings.hCellPadding - penWidth -
                                     self.cmlLabelItem.width(),
                                     baseY + settings.vCellPadding)
            scene.addItem(self.cmlLabelItem)

    def getCustomColors(self, defaultBG, defaultFG):
        """Provides the colors to be used for an item"""
        if self.ref.leadingCMLComments:
            colorSpec = CMLVersion.find(self.ref.leadingCMLComments, CMLcc)
            if colorSpec:
                bg = defaultBG
                fg = defaultFG
                if colorSpec.bgColor:
                    bg = colorSpec.bgColor
                if colorSpec.fgColor:
                    fg = colorSpec.fgColor
                if colorSpec.border:
                    border = colorSpec.border
                else:
                    border = getBorderColor(bg)
                return bg, fg, border
        return defaultBG, defaultFG, getBorderColor(defaultBG)

    def getReplacementText(self):
        """Provides the CML replacement text if so"""
        if hasattr(self.ref, "leadingCMLComments"):
            rt = CMLVersion.find(self.ref.leadingCMLComments, CMLrt)
            if rt:
                return rt.getText()
        return None

    def _getText(self):
        """Default implementation of the item text provider"""
        if self._text is None:
            self._text = self.getReplacementText()
            displayText = self.ref.getDisplayValue()
            if self._text is None:
                self._text = displayText
            else:
                self.setToolTip("<pre>" + escape(displayText) + "</pre>")
        return self._text

    def getFirstLine(self):
        """Provides the first line"""
        line = maxsize
        if hasattr(self.ref, "leadingCMLComments"):
            if self.ref.leadingCMLComments:
                line = CMLVersion.getFirstLine(self.ref.leadingCMLComments)
        if hasattr(self.ref, "leadingComment"):
            if self.ref.leadingComment:
                if self.ref.leadingComment.parts:
                    line = min(self.ref.leadingComment.parts[0].beginLine,
                               line)
        return min(self.ref.body.beginLine, line)


__kindToString = {
    CellElement.UNKNOWN: "UNKNOWN",
    CellElement.VACANT: "VACANT",
    CellElement.H_SPACER: "H_SPACER",
    CellElement.V_SPACER: "V_SPACER",
    CellElement.FILE_SCOPE: "FILE_SCOPE",
    CellElement.FUNC_SCOPE: "FUNC_SCOPE",
    CellElement.CLASS_SCOPE: "CLASS_SCOPE",
    CellElement.DECOR_SCOPE: "DECOR_SCOPE",
    CellElement.FOR_SCOPE: "FOR_SCOPE",
    CellElement.WHILE_SCOPE: "WHILE_SCOPE",
    CellElement.ELSE_SCOPE: "ELSE_SCOPE",
    CellElement.WITH_SCOPE: "WITH_SCOPE",
    CellElement.TRY_SCOPE: "TRY_SCOPE",
    CellElement.EXCEPT_SCOPE: "EXCEPT_SCOPE",
    CellElement.FINALLY_SCOPE: "FINALLY_SCOPE",
    CellElement.CODE_BLOCK: "CODE_BLOCK",
    CellElement.BREAK: "BREAK",
    CellElement.CONTINUE: "CONTINUE",
    CellElement.RETURN: "RETURN",
    CellElement.RAISE: "RAISE",
    CellElement.ASSERT: "ASSERT",
    CellElement.SYSEXIT: "SYSEXIT",
    CellElement.IMPORT: "IMPORT",
    CellElement.IF: "IF",
    CellElement.LEADING_COMMENT: "LEADING_COMMENT",
    CellElement.INDEPENDENT_COMMENT: "INDEPENDENT_COMMENT",
    CellElement.SIDE_COMMENT: "SIDE_COMMENT",
    CellElement.ABOVE_COMMENT: "ABOVE_COMMENT",
    CellElement.CONNECTOR: "CONNECTOR"}


def kindToString(kind):
    """Provides a string representation of a element kind"""
    return __kindToString[kind]


class VacantCell(CellElement):

    """A vacant cell which can be later used for some other element"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.VACANT

    def render(self):
        """Renders the cell"""
        self.width = 0
        self.height = 0
        self.minWidth = 0
        self.minHeight = 0
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY


class VSpacerCell(CellElement):

    """Represents a vertical spacer cell"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.V_SPACER

    def render(self):
        """Renders the cell"""
        self.width = 0
        self.height = self.canvas.settings.vSpacer
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        # There is no need to draw anything. The cell just reserves some
        # vertical space for better appearance
        self.baseX = baseX
        self.baseY = baseY


class HSpacerCell(CellElement):

    """Represents a horizontal spacer cell"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.H_SPACER

    def render(self):
        """Renders the cell"""
        self.width = self.canvas.settings.hSpacer
        self.height = 0
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        # There is no need to draw anything. The cell just reserves some
        # horizontal space for better appearance
        self.baseX = baseX
        self.baseY = baseY


class CodeBlockCell(CellElement, QGraphicsRectItem):

    """Represents a single code block"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.CODE_BLOCK
        self.__textRect = None
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.boxBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect(self._getText())

        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.__textRect.height() + vPadding
        hPadding = 2 * (settings.hCellPadding + settings.hTextPadding)
        self.minWidth = max(self.__textRect.width() + hPadding,
                            settings.minWidth)
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
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + self.height)
        scene.addItem(self.connector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)
        scene.addItem(self)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        rectWidth = self.minWidth - 2 * settings.hCellPadding
        rectHeight = self.minHeight - 2 * settings.vCellPadding

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)
        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRect(self.baseX + settings.hCellPadding,
                         self.baseY + settings.vCellPadding,
                         rectWidth, rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        textWidth = self.__textRect.width() + 2 * settings.hTextPadding
        textShift = (rectWidth - textWidth) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding +
            settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.body.getLineRange()
        return 'Code block at lines ' + \
               str(lineRange[0]) + "-" + str(lineRange[1])


class BreakCell(CellElement, QGraphicsRectItem):

    """Represents a single break statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
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

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.breakBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect("break")
        vPadding = 2 * (self.__vSpacing + settings.vCellPadding)
        self.minHeight = self.__textRect.height() + vPadding
        hPadding = 2 * (self.__hSpacing + settings.hCellPadding)
        self.minWidth = self.__textRect.width() + hPadding
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize(self):
        """Calculates the size"""
        settings = self.canvas.settings
        self.x1 = self.baseX + settings.hCellPadding
        self.y1 = self.baseY + settings.vCellPadding
        self.w = 2 * self.__hSpacing + self.__textRect.width()
        self.h = 2 * self.__vSpacing + self.__textRect.height()

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

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the break statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)

        painter.drawRoundedRect(self.x1, self.y1, self.w, self.h, 2, 2)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        painter.drawText(self.x1 + self.__hSpacing, self.y1 + self.__vSpacing,
                         self.__textRect.width(), self.__textRect.height(),
                         Qt.AlignLeft, "break")

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.body.getLineRange()
        return 'Break at lines ' + str(lineRange[0]) + '-' + str(lineRange[1])


class ContinueCell(CellElement, QGraphicsRectItem):

    """Represents a single continue statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
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

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.continueBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect("continue")
        vPadding = 2 * (self.__vSpacing + settings.vCellPadding)
        self.minHeight = self.__textRect.height() + vPadding
        hPadding = 2 * (self.__hSpacing + settings.hCellPadding)
        self.minWidth = self.__textRect.width() + hPadding
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize(self):
        """Calculates the size"""
        settings = self.canvas.settings
        self.x1 = self.baseX + settings.hCellPadding
        self.y1 = self.baseY + settings.vCellPadding
        self.w = 2 * self.__hSpacing + self.__textRect.width()
        self.h = 2 * self.__vSpacing + self.__textRect.height()

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

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the break statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)

        painter.drawRoundedRect(self.x1, self.y1, self.w, self.h, 2, 2)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        painter.drawText(self.x1 + self.__hSpacing, self.y1 + self.__vSpacing,
                         self.__textRect.width(), self.__textRect.height(),
                         Qt.AlignLeft, "continue")

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.body.getLineRange()
        return "Continue at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])


class ReturnCell(CellElement, QGraphicsRectItem):

    """Represents a single return statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self)
        self.kind = CellElement.RETURN
        self.__textRect = None
        self.__arrowWidth = 16
        self.connector = None

        self.arrowItem = SVGItem("return.svgz", self)
        self.arrowItem.setWidth(self.__arrowWidth)
        self.arrowItem.setToolTip("return")

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.boxBGColor,
                                    self.canvas.settings.boxFGColor)

    def _getText(self):
        """Provides the text"""
        if self._text is None:
            self._text = self.getReplacementText()
            displayText = self.ref.getDisplayValue()
            if self._text is None:
                self._text = displayText
                if not self._text:
                    self._text = "None"
            else:
                self.setToolTip("<pre>" + escape(displayText) + "</pre>")
        return self._text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect(self._getText())

        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.__textRect.height() + vPadding
        self.minWidth = max(
            self.__textRect.width() + 2 * settings.hCellPadding +
            settings.hTextPadding + settings.returnRectRadius +
            2 * settings.hTextPadding + self.__arrowWidth,
            settings.minWidth)

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
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)

        self.arrowItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight/2 - self.arrowItem.height()/2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.arrowItem)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRoundedRect(
            self.baseX + settings.hCellPadding,
            self.baseY + settings.vCellPadding,
            self.minWidth - 2 * settings.hCellPadding,
            self.minHeight - 2 * settings.vCellPadding,
            settings.returnRectRadius, settings.returnRectRadius)
        painter.drawRoundedRect(
            self.baseX + settings.hCellPadding,
            self.baseY + settings.vCellPadding,
            self.__arrowWidth + 2 * settings.hTextPadding,
            self.minHeight - 2 * settings.vCellPadding,
            settings.returnRectRadius, settings.returnRectRadius)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        availWidth = self.minWidth - 2 * settings.hCellPadding - \
                     self.__arrowWidth - 2 * settings.hTextPadding - \
                     settings.hTextPadding - settings.returnRectRadius
        textShift = (availWidth - self.__textRect.width()) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding + self.__arrowWidth +
            3 * settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        beginLine = self.ref.body.beginLine
        if self.ref.value is not None:
            endLine = self.ref.value.endLine
        else:
            endLine = self.ref.body.endLine
        return "Return at lines " + str(beginLine) + "-" + str(endLine)

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        if self.ref.value is not None:
            return distance(absPos, self.ref.body.begin, self.ref.value.end)
        return distance(absPos, self.ref.body.begin, self.ref.body.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        if self.ref.value is not None:
            return distance(line, self.ref.body.beginLine,
                            self.ref.value.endLine)
        return distance(line, self.ref.body.beginLine, self.ref.body.endLine)


class RaiseCell(CellElement, QGraphicsRectItem):

    """Represents a single raise statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.RAISE
        self.__textRect = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem("raise.svg", self)
        self.arrowItem.setWidth(self.__arrowWidth)
        self.arrowItem.setToolTip("raise")
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.boxBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect(self._getText())

        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.__textRect.height() + vPadding
        self.minWidth = max(
            self.__textRect.width() + 2 * settings.hCellPadding +
            settings.hTextPadding + settings.returnRectRadius +
            2 * settings.hTextPadding + self.__arrowWidth,
            settings.minWidth)
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
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)

        self.arrowItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight/2 - self.arrowItem.height()/2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.arrowItem)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the raise statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                self.minWidth - 2 * settings.hCellPadding,
                                self.minHeight - 2 * settings.vCellPadding,
                                settings.returnRectRadius,
                                settings.returnRectRadius)
        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                self.__arrowWidth + 2 * settings.hTextPadding,
                                self.minHeight - 2 * settings.vCellPadding,
                                settings.returnRectRadius,
                                settings.returnRectRadius)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        availWidth = self.minWidth - 2 * settings.hCellPadding - \
                     self.__arrowWidth - 2 * settings.hTextPadding - \
                     settings.hTextPadding - settings.returnRectRadius
        textShift = (availWidth - self.__textRect.width()) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding + self.__arrowWidth +
            3 * settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        beginLine = self.ref.body.beginLine
        if self.ref.value is not None:
            endLine = self.ref.value.endLine
        else:
            endLine = self.ref.body.endLine
        return "Raise at lines " + str(beginLine) + "-" + str(endLine)

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        if self.ref.value is not None:
            return distance(absPos, self.ref.body.begin, self.ref.value.end)
        return distance(absPos, self.ref.body.begin, self.ref.body.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        if self.ref.value is not None:
            return distance(line,
                            self.ref.body.beginLine, self.ref.value.endLine)
        return distance(line, self.ref.body.beginLine, self.ref.body.endLine)


class AssertCell(CellElement, QGraphicsRectItem):

    """Represents a single assert statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.ASSERT
        self.__textRect = None
        self.__diamondDiagonal = None
        self.__arrowWidth = 16
        self.connector = None

        self.arrowItem = SVGItem("assert.svg", self)
        self.arrowItem.setWidth(self.__arrowWidth)
        self.arrowItem.setToolTip("assert")

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.boxBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self._getText())

        # for an arrow box
        singleCharRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, "W")
        self.__diamondDiagonal = \
            singleCharRect.height() + 2 * settings.vTextPadding

        self.minHeight = self.__textRect.height() + \
                         2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = max(
            self.__textRect.width() + 2 * settings.hCellPadding +
            2 * settings.hTextPadding + self.__diamondDiagonal,
            settings.minWidth)
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
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + self.height)
        scene.addItem(self.connector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)

        settings = self.canvas.settings
        self.arrowItem.setPos(
            baseX + self.__diamondDiagonal / 2 +
            settings.hCellPadding - self.arrowItem.width() / 2,
            baseY + self.minHeight / 2 - self.arrowItem.height() / 2)

        scene.addItem(self)
        scene.addItem(self.arrowItem)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)

        dHalf = int(self.__diamondDiagonal / 2.0)
        dx1 = self.baseX + settings.hCellPadding
        dy1 = self.baseY + int(self.minHeight / 2)
        dx2 = dx1 + dHalf
        dy2 = dy1 - dHalf
        dx3 = dx1 + 2 * dHalf
        dy3 = dy1
        dx4 = dx2
        dy4 = dy2 + 2 * dHalf

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawPolygon(QPointF(dx1, dy1), QPointF(dx2, dy2),
                            QPointF(dx3, dy3), QPointF(dx4, dy4))

        painter.drawRect(dx3 + 1, self.baseY + settings.vCellPadding,
                         self.minWidth - 2 * settings.hCellPadding -
                         self.__diamondDiagonal,
                         self.minHeight - 2 * settings.vCellPadding)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        availWidth = \
            self.minWidth - 2 * settings.hCellPadding - self.__diamondDiagonal
        textWidth = self.__textRect.width() + 2 * settings.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText(
            dx3 + settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        beginLine = self.ref.body.beginLine
        if self.ref.message is not None:
            endLine = self.ref.message.endLine
        elif self.ref.test is not None:
            endLine = self.ref.test.endLine
        else:
            endLine = self.ref.body.endLine
        return "Assert at lines " + str(beginLine) + "-" + str(endLine)

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        if self.ref.message is not None:
            return distance(absPos, self.ref.body.begin, self.ref.message.end)
        if self.ref.test is not None:
            return distance(absPos, self.ref.body.begin, self.ref.test.end)
        return distance(absPos, self.ref.body.begin, self.ref.body.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        if self.ref.message is not None:
            return distance(line,
                            self.ref.body.beginLine, self.ref.message.endLine)
        if self.ref.test is not None:
            return distance(line,
                            self.ref.body.beginLine, self.ref.test.endLine)
        return distance(line, self.ref.body.beginLine, self.ref.body.endLine)


class SysexitCell(CellElement, QGraphicsRectItem):

    """Represents a single sys.exit(...) statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.SYSEXIT
        self.__textRect = None
        self.__xWidth = 16
        self.connector = None

        self.xItem = SVGItem("sysexit.svgz", self)
        self.xItem.setWidth(self.__xWidth)
        self.xItem.setToolTip("sys.exit()")

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.boxBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = self.getBoundingRect(self._getText())

        self.minHeight = \
            self.__textRect.height() + \
            2 * (settings.vCellPadding + settings.vTextPadding)
        self.minWidth = max(
            self.__textRect.width() + 2 * settings.hCellPadding +
            settings.hTextPadding + settings.returnRectRadius +
            2 * settings.hTextPadding + self.__xWidth,
            settings.minWidth)
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
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + settings.vCellPadding)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)

        self.xItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight/2 - self.xItem.height() / 2)

        scene.addItem(self.connector)
        scene.addItem(self)
        scene.addItem(self.xItem)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the sys.exit call"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                self.minWidth - 2 * settings.hCellPadding,
                                self.minHeight - 2 * settings.vCellPadding,
                                settings.returnRectRadius,
                                settings.returnRectRadius)
        painter.drawRoundedRect(self.baseX + settings.hCellPadding,
                                self.baseY + settings.vCellPadding,
                                self.__xWidth + 2 * settings.hTextPadding,
                                self.minHeight - 2 * settings.vCellPadding,
                                settings.returnRectRadius,
                                settings.returnRectRadius)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        availWidth = \
            self.minWidth - 2 * settings.hCellPadding - self.__xWidth - \
            2 * settings.hTextPadding - \
            settings.hTextPadding - settings.returnRectRadius
        textShift = (availWidth - self.__textRect.width()) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding + self.__xWidth +
            3 * settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides tooltip"""
        lineRange = self.ref.body.getLineRange()
        return "Sys.exit() at lines " + str(lineRange[0]) + \
               "-" + str(lineRange[1])


class ImportCell(CellElement, QGraphicsRectItem):

    """Represents a single import statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.IMPORT
        self.__arrowWidth = 16
        self.__textRect = None
        self.arrowItem = SVGItem("import.svgz", self)
        self.arrowItem.setWidth(self.__arrowWidth)
        self.arrowItem.setToolTip("import")
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.boxBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self._getText())
        self.minHeight = \
            self.__textRect.height() + 2 * settings.vCellPadding + \
            2 * settings.vTextPadding
        self.minWidth = max(
            self.__textRect.width() + 2 * settings.hCellPadding +
            2 * settings.hTextPadding + self.__arrowWidth +
            2 * settings.hTextPadding, settings.minWidth)
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
        self.connector = Connector(settings, baseX + settings.mainLine, baseY,
                                   baseX + settings.mainLine,
                                   baseY + self.height)
        scene.addItem(self.connector)

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = settings.selectPenWidth - 1
        self.setRect(baseX + settings.hCellPadding - penWidth,
                     baseY + settings.vCellPadding - penWidth,
                     self.minWidth - 2 * settings.hCellPadding + 2 * penWidth,
                     self.minHeight - 2 * settings.vCellPadding + 2 * penWidth)

        self.arrowItem.setPos(
            baseX + settings.hCellPadding + settings.hTextPadding,
            baseY + self.minHeight / 2 - self.arrowItem.height() / 2)
        scene.addItem(self)
        scene.addItem(self.arrowItem)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the import statement"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            painter.setPen(pen)
        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRect(self.baseX + settings.hCellPadding,
                         self.baseY + settings.vCellPadding,
                         self.minWidth - 2 * settings.hCellPadding,
                         self.minHeight - 2 * settings.vCellPadding)
        painter.drawLine(self.baseX + settings.hCellPadding +
                         self.__arrowWidth + 2 * settings.hTextPadding,
                         self.baseY + settings.vCellPadding,
                         self.baseX + settings.hCellPadding +
                         self.__arrowWidth + 2 * settings.hTextPadding,
                         self.baseY + self.minHeight - settings.vCellPadding)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)
        textRectWidth = self.minWidth - 2 * settings.hCellPadding - \
                        4 * settings.hTextPadding - self.__arrowWidth
        textShift = (textRectWidth - self.__textRect.width()) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding + self.__arrowWidth +
            3 * settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.body.getLineRange()
        return "Import at lines " + str(lineRange[0]) + "-" + str(lineRange[1])


class IfCell(CellElement, QGraphicsRectItem):

    """Represents a single if statement"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsRectItem.__init__(self, canvas.scopeRectangle)
        self.kind = CellElement.IF
        self.__textRect = None
        self.vConnector = None
        self.hConnector = None
        self.rightLabel = None
        self.yBelow = False

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def getColors(self):
        """Provides the item colors"""
        return self.getCustomColors(self.canvas.settings.ifBGColor,
                                    self.canvas.settings.boxFGColor)

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self._getText())

        self.minHeight = self.__textRect.height() + \
                         2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = max(
            self.__textRect.width() +
            2 * settings.hCellPadding + 2 * settings.hTextPadding +
            2 * settings.ifWidth, settings.minWidth)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calcPolygon(self):
        """Calculates the polygon"""
        settings = self.canvas.settings

        self.x1 = self.baseX + settings.hCellPadding
        self.y1 = self.baseY + self.minHeight / 2
        self.x2 = self.baseX + settings.hCellPadding + settings.ifWidth
        self.y2 = self.baseY + settings.vCellPadding
        self.x3 = self.baseX + self.minWidth - \
                  settings.hCellPadding - settings.ifWidth
        self.y3 = self.y2
        self.x4 = self.x3 + settings.ifWidth
        self.y4 = self.y1
        self.x5 = self.x3
        self.y5 = self.baseY + (self.minHeight - settings.vCellPadding)
        self.x6 = self.x2
        self.y6 = self.y5

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        self.__calcPolygon()

        # Add the connectors as separate scene items to make the selection
        # working properly
        settings = self.canvas.settings
        self.vConnector = Connector(settings, baseX + settings.mainLine, baseY,
                                    baseX + settings.mainLine,
                                    baseY + self.height)
        scene.addItem(self.vConnector)

        self.hConnector = Connector(settings, self.x4, self.y4,
                                    self.baseX + self.width,
                                    self.y4)
        scene.addItem(self.hConnector)

        self.yBelow = CMLVersion.find(self.ref.leadingCMLComments,
                                      CMLsw) is not None
        if self.yBelow:
            self.rightLabel = Text(settings, "N")
            f = self.rightLabel.font()
            f.setBold(True)
            self.rightLabel.setFont(f)
        else:
            self.rightLabel = Text(settings, "Y")

        self.rightLabel.setPos(
            self.x4 + 2,
            self.y4 - self.rightLabel.boundingRect().height() - 2)
        scene.addItem(self.rightLabel)

        penWidth = settings.selectPenWidth - 1
        self.setRect(self.x1 - penWidth, self.y2 - penWidth,
                     self.x4 - self.x1 + 2 * penWidth,
                     self.y6 - self.y2 + 2 * penWidth)
        scene.addItem(self)

        self.addCMLIndicator(baseX, baseY, penWidth, scene)
        self.__bgColor, self.__fgColor, self.__borderColor = self.getColors()

    def paint(self, painter, option, widget):
        """Draws the code block"""
        del option      # unused argument
        del widget      # unused argument

        settings = self.canvas.settings

        if self.isSelected():
            selectPen = QPen(settings.selectColor)
            selectPen.setWidth(settings.selectPenWidth)
            selectPen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(selectPen)
        else:
            pen = QPen(self.__borderColor)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawPolygon(
            QPointF(self.x1, self.y1), QPointF(self.x2, self.y2),
            QPointF(self.x3, self.y3), QPointF(self.x4, self.y4),
            QPointF(self.x5, self.y5), QPointF(self.x6, self.y6))

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setPen(pen)
        painter.setFont(settings.monoFont)
        availWidth = self.x3 - self.x2
        textWidth = self.__textRect.width() + 2 * settings.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText(
            self.x2 + settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.body.getLineRange()
        return "If at lines " + str(lineRange[0]) + "-" + str(lineRange[1])


def getCommentBoxPath(settings, baseX, baseY, width, height):
    """Provides the comomment box path"""
    return getNoCellCommentBoxPath(baseX + settings.hCellPadding,
                                   baseY + settings.vCellPadding,
                                   width - 2 * settings.hCellPadding,
                                   height - 2 * settings.vCellPadding,
                                   settings.commentCorner)


def getNoCellCommentBoxPath(x, y, width, height, corner):
    """Provides the path for exactly specified rectangle"""
    path = QPainterPath()
    path.moveTo(x, y)
    path.lineTo(x + width - corner, y)
    path.lineTo(x + width, y + corner)
    path.lineTo(x + width, y + height)
    path.lineTo(x, y + height)
    path.lineTo(x, y)

    # -1 is to avoid sharp corners of the lines
    path.moveTo(x + width - corner, y + 1)
    path.lineTo(x + width - corner, y + corner)
    path.lineTo(x + width - 1, y + corner)
    return path


class IndependentCommentCell(CellElement, QGraphicsPathItem):

    """Represents a single independent comment"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.INDEPENDENT_COMMENT
        self.__textRect = None
        self.leadingForElse = False
        self.sideForElse = False
        self.__leftEdge = None
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def render(self):
        """Renders the cell"""
        setings = self.canvas.settings
        self.__textRect = setings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self._getText())

        self.minHeight = self.__textRect.height() + \
                         2 * (setings.vCellPadding + setings.vTextPadding)
        self.minWidth = max(self.__textRect.width() +
                            2 * (setings.hCellPadding + setings.hTextPadding),
                            setings.minWidth)
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
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)
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
        self.__leftEdge = \
            cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)
        path = getCommentBoxPath(settings, self.__leftEdge, self.baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        # May be later the connector will look different for two cases below
        if self.leadingForElse:
            self.connector = Connector(
                settings, self.__leftEdge + settings.hCellPadding,
                self.baseY + self.minHeight / 2,
                cellToTheLeft.baseX + settings.mainLine,
                self.baseY + self.minHeight / 2)
        else:
            self.connector = Connector(
                settings, self.__leftEdge + settings.hCellPadding,
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
            self.__leftEdge + settings.hCellPadding + settings.hTextPadding,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self._getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            self._editor.gotoLine(self.ref.beginLine,
                                  self.ref.beginPos)
            self._editor.setFocus()

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.getLineRange()
        return "Independent comment at lines " + \
               str(lineRange[0]) + "-" + str(lineRange[1])

    def getDistance(self, absPos):
        """Provides a distance between the absPos and the item"""
        return distance(absPos, self.ref.begin, self.ref.end)

    def getLineDistance(self, line):
        """Provides a distance between the line and the item"""
        return distance(line, self.ref.beginLine, self.ref.endLine)

    def isComment(self):
        """True if it is a comment"""
        return True


class LeadingCommentCell(CellElement, QGraphicsPathItem):

    """Represents a single leading comment"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.LEADING_COMMENT
        self.__text = None
        self.__textRect = None
        self.__leftEdge = None
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides text"""
        if self.__text is None:
            self.__text = self.ref.leadingComment.getDisplayValue()
        return self.__text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self.__getText())

        self.minHeight = \
            self.__textRect.height() + \
            2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = max(
            self.__textRect.width() +
            2 * settings.hCellPadding + 2 * settings.hTextPadding,
            settings.minWidth)
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
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)
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
            self.__leftEdge = self.baseX
        else:
            self.__leftEdge = \
                cellToTheLeft.baseX + \
                settings.mainLine + settings.hCellPadding
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)

        path = getCommentBoxPath(settings, self.__leftEdge, baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        self.connector = Connector(settings, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self.__leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self.__leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self.__leftEdge - settings.hCellPadding,
                             baseY + self.minHeight + settings.vCellPadding)
        self.connector.setPath(connectorPath)
        self.connector.penColor = settings.commentLineColor
        self.connector.penWidth = settings.commentLineWidth

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
            self.__leftEdge + settings.hCellPadding + settings.hTextPadding,
            baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self.__getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            self._editor.gotoLine(self.ref.leadingComment.beginLine,
                                  self.ref.leadingComment.beginPos)
            self._editor.setFocus()

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.leadingComment.getLineRange()
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

    def isComment(self):
        """True if it is a comment"""
        return True


class SideCommentCell(CellElement, QGraphicsPathItem):

    """Represents a single side comment"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.SIDE_COMMENT
        self.__text = None
        self.__textRect = None
        self.__leftEdge = None
        self.connector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides the text"""
        if self.__text is None:
            self.__text = ""
            cellToTheLeft = self.canvas.cells[self.addr[1]][self.addr[0] - 1]
            if cellToTheLeft.kind == CellElement.IMPORT:
                importRef = cellToTheLeft.ref
                if importRef.fromPart is not None:
                    self.__text = "\n"
                self.__text += \
                    '\n' * (self.ref.sideComment.beginLine -
                            importRef.whatPart.beginLine) + \
                    self.ref.sideComment.getDisplayValue()
            else:
                self.__text = \
                    '\n' * (self.ref.sideComment.beginLine -
                            self.ref.body.beginLine) + \
                    self.ref.sideComment.getDisplayValue()
        return self.__text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self.__getText())

        self.minHeight = self.__textRect.height() + \
            2 * settings.vCellPadding + 2 * settings.vTextPadding
        self.minWidth = max(
            self.__textRect.width() + 2 * settings.hCellPadding +
            2 * settings.hTextPadding, settings.minWidth)
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
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)
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
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)
        self.__leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
        cellKind = self.canvas.cells[self.addr[1]][self.addr[0] - 1].kind
        if cellKind == CellElement.CONNECTOR:
            # 'if' or 'elif' side comment
            self.__leftEdge = \
                cellToTheLeft.baseX + settings.mainLine + settings.hCellPadding
            path = getCommentBoxPath(settings, self.__leftEdge, self.baseY,
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
                settings, self.__leftEdge + settings.hCellPadding,
                self.baseY + ifCell.minHeight / 2 + 6,
                ifCell.baseX + ifCell.minWidth - settings.hCellPadding,
                self.baseY + ifCell.minHeight / 2 + 6)
        else:
            # Regular box
            self.__leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
            path = getCommentBoxPath(settings, self.__leftEdge, self.baseY,
                                     boxWidth, self.minHeight)

            height = min(self.minHeight / 2, cellToTheLeft.minHeight / 2)

            self.connector = Connector(
                settings, self.__leftEdge + settings.hCellPadding,
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
        painter.drawText(
            self.__leftEdge + settings.hCellPadding + settings.hTextPadding,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self.__getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            self._editor.gotoLine(self.ref.sideComment.beginLine,
                                  self.ref.sideComment.beginPos)
            self._editor.setFocus()

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.sideComment.getLineRange()
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

    def isComment(self):
        """True if it is a comment"""
        return True


class AboveCommentCell(CellElement, QGraphicsPathItem):

    """Represents a single leading comment which is above certain blocks.

    Blocks are: try/except or for/else or while/else
    i.e. those which are scopes located in a single row
    """

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.ABOVE_COMMENT
        self.__text = None
        self.__textRect = None
        self.__leftEdge = None
        self.needConnector = False
        self.connector = None
        self.commentConnector = None

        # To make double click delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def __getText(self):
        """Provides text"""
        if self.__text is None:
            self.__text = self.ref.leadingComment.getDisplayValue()
        return self.__text

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings
        self.__textRect = settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, self.__getText())

        self.minHeight = self.__textRect.height() + \
                         2 * (settings.vCellPadding + settings.vTextPadding)
        # Width of the comment box itself
        self.minWidth = max(self.__textRect.width() +
                            2 * (settings.hCellPadding +
                                 settings.hTextPadding), settings.minWidth)
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

        self.__leftEdge = \
            self.baseX + settings.mainLine + settings.hCellPadding
        boxWidth = max(self.__textRect.width() +
                       2 * (settings.hCellPadding + settings.hTextPadding),
                       settings.minWidth)

        path = getCommentBoxPath(settings, self.__leftEdge, baseY,
                                 boxWidth, self.minHeight)
        self.setPath(path)

        self.commentConnector = Connector(settings, 0, 0, 0, 0)
        connectorPath = QPainterPath()
        connectorPath.moveTo(self.__leftEdge + settings.hCellPadding,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self.__leftEdge,
                             baseY + self.minHeight / 2)
        connectorPath.lineTo(self.__leftEdge - settings.hCellPadding,
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
            self.__leftEdge + settings.hCellPadding + settings.hTextPadding,
            baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, self.__getText())

    def mouseDoubleClickEvent(self, event):
        """Jump to the appropriate line in the text editor"""
        if self._editor:
            self._editor.gotoLine(self.ref.leadingComment.beginLine,
                                  self.ref.leadingComment.beginPos)
            self._editor.setFocus()
        return

    def getSelectTooltip(self):
        """Provides the tooltip"""
        lineRange = self.ref.leadingComment.getLineRange()
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

    def isComment(self):
        """True if it is a comment"""
        return True


class ConnectorCell(CellElement, QGraphicsPathItem):

    """Represents a single connector cell"""

    NORTH = 0
    SOUTH = 1
    WEST = 2
    EAST = 3
    CENTER = 4

    def __init__(self, connections, canvas, x, y):
        """Connections are supposed to be a list of tuples.

        Eample: [ (NORTH, SOUTH), (EAST, CENTER) ]
        """
        CellElement.__init__(self, None, canvas, x, y)
        QGraphicsPathItem.__init__(self)
        self.kind = CellElement.CONNECTOR
        self.connections = connections

    def __hasVertical(self):
        """True if has a vertical part"""
        for conn in self.connections:
            if self.NORTH in conn or self.SOUTH in conn:
                return True
        return False

    def __hasHorizontal(self):
        """True if has a horizontal part"""
        for conn in self.connections:
            if self.EAST in conn or self.WEST in conn:
                return True
        return False

    def render(self):
        """Renders the cell"""
        settings = self.canvas.settings

        if self.__hasVertical():
            self.minWidth = settings.mainLine + settings.hCellPadding
        else:
            self.minWidth = 0

        if self.__hasHorizontal():
            self.minHeight = 2 * settings.vCellPadding
        else:
            self.minHeight = 0

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __getY(self):
        """Provides the Y coordinate"""
        row = self.addr[1]
        column = self.addr[0]
        cells = self.canvas.cells
        for index in range(column - 1, -1, -1):
            kind = cells[row][index].kind
            if kind in [CellElement.VACANT, CellElement.H_SPACER,
                        CellElement.V_SPACER]:
                continue
            if kind in [CellElement.FILE_SCOPE, CellElement.FUNC_SCOPE,
                        CellElement.CLASS_SCOPE, CellElement.FOR_SCOPE,
                        CellElement.WHILE_SCOPE, CellElement.TRY_SCOPE,
                        CellElement.WITH_SCOPE, CellElement.DECOR_SCOPE,
                        CellElement.ELSE_SCOPE, CellElement.EXCEPT_SCOPE,
                        CellElement.FINALLY_SCOPE]:
                break
            if kind != CellElement.CONNECTOR:
                return cells[row][index].minHeight / 2
        return self.height / 2

    def __getXY(self, location):
        """Provides the location coordinates"""
        settings = self.canvas.settings
        if location == self.NORTH:
            return self.baseX + settings.mainLine, self.baseY
        if location == self.SOUTH:
            return self.baseX + settings.mainLine, self.baseY + self.height
        if location == self.WEST:
            return self.baseX, self.baseY + self.__getY()
        if location == self.EAST:
            return self.baseX + self.width, self.baseY + self.__getY()
        # It is CENTER
        return self.baseX + settings.mainLine, self.baseY + self.__getY()

    def __angled(self, begin, end):
        """Returns True if the connection is not straight"""
        if begin in [self.NORTH, self.SOUTH] and \
           end in [self.WEST, self.EAST]:
            return True
        return end in [self.NORTH, self.SOUTH] and \
               begin in [self.WEST, self.EAST]

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        self.baseX = baseX
        self.baseY = baseY

        path = QPainterPath()
        for connection in self.connections:
            startX, startY = self.__getXY(connection[0])
            endX, endY = self.__getXY(connection[1])
            if self.__angled(connection[0], connection[1]):
                centerX, centerY = self.__getXY(self.CENTER)
                path.moveTo(startX, startY)
                path.lineTo(centerX, centerY)
                path.lineTo(endX, endY)
            else:
                path.moveTo(startX, startY)
                path.lineTo(endX, endY)
        self.setPath(path)
        scene.addItem(self)

    def paint(self, painter, option, widget):
        """Draws the code block"""
        settings = self.canvas.settings

        pen = QPen(settings.lineColor)
        pen.setWidth(settings.lineWidth)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        painter.setPen(pen)
        QGraphicsPathItem.paint(self, painter, option, widget)

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return None

    def mouseDoubleClickEvent(self, event):
        """Handles the mouse double click"""
        return  # To be on the safe side: override the default implementation

    def setEditor(self, editor):
        """Sets the editor"""
        return  # To be on the safe side: override the default implementation
