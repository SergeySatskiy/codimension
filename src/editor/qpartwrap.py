# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""qutepart text editor component wrapper"""


from qutepart import Qutepart
from ui.qt import QPalette, pyqtSignal, QFont, QTextCursor
from utils.globals import GlobalData
from utils.settings import Settings


class QutepartWrapper(Qutepart):

    """Convenience qutepart wrapper"""

    sigTextEditorZoom = pyqtSignal(int)

    def __init__(self, parent):
        Qutepart.__init__(self, parent)

        self.encoding = None
        self.newFileUserEncoding = None
        self.mime = None

        # Remove all the default margins
        self.delMargin('mark_area')
        self.delMargin('line_numbers')
        self.completionEnabled = False

        # The minimum possible zoom not to make the margin disappear
        skin = GlobalData().skin
        marginPointSize = skin['lineNumFont'].pointSize()
        mainAreaPointSize = skin['monoFont'].pointSize()
        self.__minZoom = (min(marginPointSize, mainAreaPointSize) - 1) * -1

        self.setFont(QFont(skin['monoFont']))

    def setPaper(self, paperColor):
        """Sets the new paper color"""
        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Base, paperColor)
        palette.setColor(QPalette.Inactive, QPalette.Base, paperColor)
        self.setPalette(palette)

    def setColor(self, textColor):
        """Sets the new text color"""
        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Text, textColor)
        palette.setColor(QPalette.Inactive, QPalette.Text, textColor)
        self.setPalette(palette)

    def onZoomIn(self):
        """Increases the font"""
        self.sigTextEditorZoom.emit(Settings()['zoom'] + 1)

    def onZoomOut(self):
        """Decreases the font"""
        newZoom = Settings()['zoom'] - 1
        if newZoom >= self.__minZoom:
            self.sigTextEditorZoom.emit(newZoom)

    def zoomTo(self, zoomVal):
        """Sets the zoom to a certain value if possible"""
        # zoomVal is an integer: > 0 => larger, < 0 => smaller than the base
        font = QFont(GlobalData().skin['monoFont'])
        zoomVal = max(zoomVal, self.__minZoom)
        fontSize = font.pointSize() + zoomVal
        font.setPointSize(fontSize)
        self.setFont(font)

        for margin in self.getMargins():
            if hasattr(margin, 'zoomTo'):
                margin.zoomTo(zoomVal)

    def clearUndoRedoHistory(self):
        """Clears the undo/redo history"""
        self.document().clearUndoRedoStacks()

    def getEolIndicator(self):
        """Provides the eol indicator for the current eol mode"""
        if self.eol == '\r\n':
            return "CRLF"
        if self.eol == '\r':
            return 'CR'
        return 'LF'

    def firstVisibleLine(self):
        """Provides the first visible line. 0-based"""
        return self.firstVisibleBlock().blockNumber()

    def lastVisibleLine(self):
        """Provides the last visible line. 0-based"""
        editorHeight = self.height()
        bar = self.horizontalScrollBar()
        if bar:
            if bar.isVisible():
                editorHeight -= bar.height()
        block = self.firstVisibleBlock()
        blockRect = self.blockBoundingRect(block)

        lastVisible = block.blockNumber()
        blocksHeight = 0.0
        while block.isValid():
            if not block.isValid():
                break
            blocksHeight += self.blockBoundingRect(block).height()
            if blocksHeight > editorHeight:
                break
            lastVisible = block.blockNumber()
            block = block.next()
        return lastVisible

    def isLineOnScreen(self, line):
        """True if the line is on screen. line is 0-based."""
        if line < self.firstVisibleLine():
            return False
        return line <= self.lastVisibleLine()

    def ensureLineOnScreen(self, line):
        """Makes sure the line is visible on screen. line is 0-based."""
        # Prerequisite: the cursor has to be on the desired position
        if not self.isLineOnScreen(line):
            self.ensureCursorVisible()

    def setHScrollOffset(self, value):
        """Sets the new horizontal scroll bar value"""
        bar = self.horizontalScrollBar()
        if bar:
            bar.setValue(value)

    def moveToLineEnd(self):
        """Moves the cursor to the end of the line"""
        line, pos = self.cursorPosition
        self.cursorPosition = line, len(self.lines[line])

    def moveToLineBegin(self, toFirstNonSpace):
        """Jumps to the first non-space or to position 0"""
        line, pos = self.cursorPosition
        if toFirstNonSpace:
            lStripped = self.lines[line].lstrip()
            if lStripped:
                pos = len(self.lines[line]) - len(lStripped)
                self.cursorPosition = line, pos
            else:
                self.cursorPosition = line, 0
        else:
            self.cursorPosition = line, 0

    def _onHome(self):
        """Triggered when HOME is received"""
        self.moveToLineBegin(Settings()['jumpToFirstNonSpace'])

    def printUserData(self):
        """Debug purpose member to print the highlight data"""
        line, pos = self.cursorPosition
        if self._highlighter is None:
            print(str(line+1) + ":" + str(pos+1) + " no highlight")
            return
        block = self.document().findBlockByNumber(line)
        data = block.userData()
        if data is None:
            print(str(line+1) + ":" + str(pos+1) + " None")
            return
        print(str(line+1) + ":" + str(pos+1) + " " + repr(data.data))

    def isStringLiteral(self, line, pos):
        """True if it is a string literal"""
        if self._highlighter is None:
            return False
        block = self.document().findBlockByNumber(line)
        data = block.userData()
        if data is None:
            return False
        return self._highlighter._syntax._getTextType(data.data, pos) == 's'

    def getCurrentWord(self):
        """Provides the current word"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText()
        return word

    def removeTrailingWhitespaces(self):
        """Removes trailing whitespaces"""
        with self:
            for index in len(self.lines):
                orig = self.lines[index]
                stripped = orig.rstrip()
                if orig != stripped:
                    self.lines[index] = stripped
