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

"""Base class for everything Codimension puts on the graphics scene"""

# pylint: disable=C0305

from sys import maxsize
from ui.qt import QMimeData, Qt, QApplication, QPen
from utils.globals import GlobalData
from utils.config import DEFAULT_ENCODING
from .cml import CMLVersion
from .routines import distance


class CellElement:

    """Base class for all the elements which could be found on the canvas"""

    UNKNOWN = -1

    VCANVAS = 0

    VACANT = 1
    H_SPACER = 2
    V_SPACER = 3
    H_GROUP_SPACER = 4
    SPACER = 5

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
    SCOPE_H_SIDE_EDGE = 111
    SCOPE_V_SIDE_EDGE = 112
    SCOPE_CORNER_EDGE = 113

    # The three items below will be mapped to ELSE_SCOPE
    # They are needed to distinguish the constructors which use individual
    # color settings for each kind of else scope. I.e. the graphics scene
    # will have no items of these types ever
    FOR_ELSE_SCOPE = 120
    WHILE_ELSE_SCOPE = 121
    TRY_ELSE_SCOPE = 122

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
    EXCEPT_MINIMIZED = 213
    INDEPENDENT_DOC = 214
    LEADING_DOC = 215
    ABOVE_DOC = 216
    INDEPENDENT_MINIMIZED_COMMENT = 217
    LEADING_MINIMIZED_COMMENT = 218
    SIDE_MINIMIZED_COMMENT = 219
    ABOVE_MINIMIZED_COMMENT = 220

    CONNECTOR = 300
    SVG = 301
    BADGE = 302
    DEPENDENT_CONNECTOR = 303
    TEXT = 304
    RUBBER_BAND = 305
    LINE = 306
    RECTANGLE = 307
    GROUP_CORNER_CONROL = 308

    EMPTY_GROUP = 500
    OPENED_GROUP_BEGIN = 501
    OPENED_GROUP_END = 502
    COLLAPSED_GROUP = 503

    def __init__(self, ref, canvas, x, y):
        self.kind = self.UNKNOWN
        self.subKind = self.UNKNOWN
        self.ref = ref              # reference to the control flow object
        self.addr = [x, y]          # indexes in the current canvas
        self.canvas = canvas        # reference to the canvas

        self.tailComment = False

        # Filled when rendering is called
        self.width = None
        self.height = None
        self.minWidth = None
        self.minHeight = None

        # Filled when draw is called
        self.baseX = None
        self.baseY = None

        # Shift is used when open groups are involved
        self.hShift = 0

        # Unique sequential ID
        self.itemID = canvas.settings.itemID
        canvas.settings.itemID += 1

    def __str__(self):
        return kindToString(self.kind) + \
            '[' + str(self.minWidth) + 'x' + str(self.minHeight) + '] -> [' + \
            str(self.width) + 'x' + str(self.height) + ']'

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

    def getEditor(self):
        """Provides a reference to the editor"""
        canvas = self.canvas
        while canvas.canvas is not None:
            canvas = canvas.canvas
        return canvas.editor

    def getPainterPen(self, selected, borderColor):
        """Provides the painter pen for the item"""
        if selected:
            pen = QPen(self.canvas.settings.selectColor)
            pen.setWidth(self.canvas.settings.selectPenWidth)
        else:
            pen = QPen(borderColor)
            pen.setWidth(self.canvas.settings.boxLineWidth)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def mouseDoubleClickEvent(self, event, line=None, pos=None):
        """Jump to the appropriate line in the text editor.

        default implementation
        """
        editor = self.getEditor()
        if editor is not None:
            if event:
                if event.buttons() != Qt.LeftButton:
                    return

            GlobalData().mainWindow.raise_()
            GlobalData().mainWindow.activateWindow()

            if line is None:
                line = self.getLineRange()[0]
            if pos is None:
                lineContent = editor.lines[line - 1]
                pos = len(lineContent) - len(lineContent.lstrip()) + 1

            editor.gotoLine(line, pos)
            editor.setFocus()

    def scopedItem(self):
        """True if it is a scoped item"""
        return self.kind in (self.FILE_SCOPE, self.FUNC_SCOPE,
                             self.CLASS_SCOPE, self.FOR_SCOPE,
                             self.WHILE_SCOPE, self.TRY_SCOPE,
                             self.WITH_SCOPE, self.DECOR_SCOPE,
                             self.ELSE_SCOPE, self.EXCEPT_SCOPE,
                             self.FINALLY_SCOPE,
                             self.SCOPE_H_SIDE_EDGE, self.SCOPE_V_SIDE_EDGE,
                             self.SCOPE_CORNER_EDGE)

    def isProxyItem(self):
        """True if it is a proxy item"""
        return self.kind in (self.BADGE, self.SVG, self.CONNECTOR,
                             self.DEPENDENT_CONNECTOR, self.TEXT,
                             self.RUBBER_BAND, self.LINE, self.RECTANGLE,
                             self.GROUP_CORNER_CONROL)

    def isSpacerItem(self):
        """True is it is a some kind of a spacer"""
        return self.kind in (self.VACANT, self.H_SPACER, self.V_SPACER,
                             self.H_GROUP_SPACER, self.SPACER)

    @staticmethod
    def getProxiedItem():
        """Provides the real item for a proxy one"""
        return None

    def isComment(self):
        """True if it is a comment"""
        return self.kind in (self.INDEPENDENT_COMMENT,
                             self.LEADING_COMMENT,
                             self.SIDE_COMMENT,
                             self.ABOVE_COMMENT,
                             self.INDEPENDENT_MINIMIZED_COMMENT,
                             self.LEADING_MINIMIZED_COMMENT,
                             self.SIDE_MINIMIZED_COMMENT,
                             self.ABOVE_MINIMIZED_COMMENT)

    def isCMLDoc(self):
        """True if it is a CML doc item"""
        return self.kind in (self.INDEPENDENT_DOC, self.LEADING_DOC,
                             self.ABOVE_DOC)

    def isGroupItem(self):
        """True if it is some kind of a group item"""
        return self.kind in (self.OPENED_GROUP_BEGIN, self.OPENED_GROUP_END,
                             self.COLLAPSED_GROUP, self.EMPTY_GROUP)

    @staticmethod
    def isDocstring():
        """True if it is a docstring"""
        return False

    def isMinimizedItem(self):
        """True if it is a minimized item"""
        return self.kind in (self.INDEPENDENT_MINIMIZED_COMMENT,
                             self.LEADING_MINIMIZED_COMMENT,
                             self.EXCEPT_MINIMIZED,
                             self.SIDE_MINIMIZED_COMMENT,
                             self.ABOVE_MINIMIZED_COMMENT)

    def getDistance(self, absPos):
        """Default implementation.

        Provides a distance between the absPos and the item
        """
        absPosRange = self.getAbsPosRange()
        return distance(absPos, absPosRange[0], absPosRange[1])

    def getLineDistance(self, line):
        """Default implementation.

        Provides a distance between the line and the item
        """
        lineRange = self.getLineRange()
        return distance(line, lineRange[0], lineRange[1])

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

    def getLineRange(self):
        """Default implementation of the line range"""
        return self.ref.body.getLineRange()

    def getAbsPosRange(self):
        """Provides the absolute position range"""
        return [self.ref.body.begin, self.ref.body.end]

    @staticmethod
    def getLinesSuffix(lineRange):
        """Provides the proper suffix for the selected item tooltips"""
        if lineRange[0] == lineRange[1]:
            return 'line ' + str(lineRange[0])
        return 'lines ' + str(lineRange[0]) + "-" + str(lineRange[1])

    @staticmethod
    def _putMimeToClipboard(value):
        """Copies the value (string) to a clipboard as mime data"""
        mimeData = QMimeData()
        mimeData.setData('text/codimension', value.encode(DEFAULT_ENCODING))
        QApplication.clipboard().setMimeData(mimeData)

    def copyToClipboard(self):
        """Placeholder"""
        return


__kindToString = {
    CellElement.UNKNOWN: 'UNKNOWN',
    CellElement.VCANVAS: 'VCANVAS',
    CellElement.VACANT: 'VACANT',
    CellElement.H_SPACER: 'H_SPACER',
    CellElement.V_SPACER: 'V_SPACER',
    CellElement.H_GROUP_SPACER: 'H_GROUP_SPACER',
    CellElement.SPACER: 'SPACER',
    CellElement.NO_SCOPE: 'NO_SCOPE',
    CellElement.FILE_SCOPE: 'FILE_SCOPE',
    CellElement.FUNC_SCOPE: 'FUNC_SCOPE',
    CellElement.CLASS_SCOPE: 'CLASS_SCOPE',
    CellElement.DECOR_SCOPE: 'DECOR_SCOPE',
    CellElement.FOR_SCOPE: 'FOR_SCOPE',
    CellElement.WHILE_SCOPE: 'WHILE_SCOPE',
    CellElement.ELSE_SCOPE: 'ELSE_SCOPE',
    CellElement.WITH_SCOPE: 'WITH_SCOPE',
    CellElement.TRY_SCOPE: 'TRY_SCOPE',
    CellElement.EXCEPT_SCOPE: 'EXCEPT_SCOPE',
    CellElement.FINALLY_SCOPE: 'FINALLY_SCOPE',
    CellElement.SCOPE_H_SIDE_EDGE: 'SCOPE_H_SIDE_EDGE',
    CellElement.SCOPE_V_SIDE_EDGE: 'SCOPE_V_SIDE_EDGE',
    CellElement.SCOPE_CORNER_EDGE: 'SCOPE_CORNER_EDGE',
    CellElement.CODE_BLOCK: 'CODE_BLOCK',
    CellElement.BREAK: 'BREAK',
    CellElement.CONTINUE: 'CONTINUE',
    CellElement.RETURN: 'RETURN',
    CellElement.RAISE: 'RAISE',
    CellElement.ASSERT: 'ASSERT',
    CellElement.SYSEXIT: 'SYSEXIT',
    CellElement.IMPORT: 'IMPORT',
    CellElement.IF: 'IF',
    CellElement.LEADING_COMMENT: 'LEADING_COMMENT',
    CellElement.INDEPENDENT_COMMENT: 'INDEPENDENT_COMMENT',
    CellElement.SIDE_COMMENT: 'SIDE_COMMENT',
    CellElement.ABOVE_COMMENT: 'ABOVE_COMMENT',
    CellElement.INDEPENDENT_MINIMIZED_COMMENT: 'INDEPENDENT_MINIMIZED_COMMENT',
    CellElement.LEADING_MINIMIZED_COMMENT: 'LEADING_MINIMIZED_COMMENT',
    CellElement.SIDE_MINIMIZED_COMMENT: 'SIDE_MINIMIZED_COMMENT',
    CellElement.ABOVE_MINIMIZED_COMMENT: 'ABOVE_MINIMIZED_COMMENT',
    CellElement.EXCEPT_MINIMIZED: 'EXCEPT_MINIMIZED',
    CellElement.CONNECTOR: 'CONNECTOR',
    CellElement.DEPENDENT_CONNECTOR: 'DEPENDENT_CONNECTOR',
    CellElement.SVG: 'SVG',
    CellElement.BADGE: 'BADGE',
    CellElement.TEXT: 'TEXT',
    CellElement.RUBBER_BAND: 'RUBBER_BAND',
    CellElement.LINE: 'LINE',
    CellElement.RECTANGLE: 'RECTANGLE',
    CellElement.GROUP_CORNER_CONROL: 'GROUP_CORNER_CONROL',
    CellElement.INDEPENDENT_DOC: 'INDEPENDENT_DOC',
    CellElement.LEADING_DOC: 'LEADING_DOC',
    CellElement.ABOVE_DOC: 'ABOVE_DOC',
    CellElement.EMPTY_GROUP: 'EMPTY_GROUP',
    CellElement.OPENED_GROUP_BEGIN: 'OPENED_GROUP_BEGIN',
    CellElement.OPENED_GROUP_END: 'OPENED_GROUP_END',
    CellElement.COLLAPSED_GROUP: 'COLLAPSED_GROUP'}


def kindToString(kind):
    """Provides a string representation of a element kind"""
    return __kindToString[kind]

