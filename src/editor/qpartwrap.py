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


import re
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
        self.explicitUserEncoding = None
        self.mime = None

        # Remove all the default margins
        self.delMargin('mark_area')
        self.delMargin('line_numbers')
        self.completionEnabled = False

        # The minimum possible zoom not to make the margin disappear
        skin = GlobalData().skin
        self.setFont(QFont(skin['monoFont']))

        # Search/replace support
        self.__matchesCache = None
        self.__matchesRegexp = None
        self.textToIterate = None
        self.textChanged.connect(self.__resetMatchCache)

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
        if newZoom >= GlobalData().skin.minTextZoom:
            self.sigTextEditorZoom.emit(newZoom)

    def onZoomReset(self):
        """Resets zoom"""
        if Settings()['zoom'] != 0:
            self.sigTextEditorZoom.emit(0)

    def zoomTo(self, zoomVal):
        """Sets the zoom to a certain value if possible"""
        # zoomVal is an integer: > 0 => larger, < 0 => smaller than the base
        font = QFont(GlobalData().skin['monoFont'])
        zoomVal = max(zoomVal, GlobalData().skin.minTextZoom)
        fontSize = font.pointSize() + zoomVal
        font.setPointSize(fontSize)
        self.setFont(font)

        for margin in self.getMargins():
            if hasattr(margin, 'zoomTo'):
                margin.zoomTo(zoomVal)
        self._setSolidEdgeGeometry()

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
        hBar = self.horizontalScrollBar()
        if hBar:
            if hBar.isVisible():
                editorHeight -= hBar.height()
        block = self.firstVisibleBlock()

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
        line, _ = self.cursorPosition
        self.cursorPosition = line, len(self.lines[line])

    @staticmethod
    def firstNonSpaceIndex(text):
        """Provides a pos (0-based of a first non-space char in the text"""
        lStripped = text.lstrip()
        if lStripped:
            return len(text) - len(lStripped)
        return None

    def moveToLineBegin(self, toFirstNonSpace):
        """Jumps to the first non-space or to position 0"""
        line, pos = self.cursorPosition
        newPos = 0
        if toFirstNonSpace:
            lStripped = self.lines[line].lstrip()
            if lStripped:
                calcPos = len(self.lines[line]) - len(lStripped)
                newPos = 0 if pos <= calcPos else calcPos
        self.cursorPosition = line, newPos

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
        return cursor.selectedText()

    def removeTrailingWhitespaces(self):
        """Removes trailing whitespaces"""
        with self:
            for index in len(self.lines):
                orig = self.lines[index]
                stripped = orig.rstrip()
                if orig != stripped:
                    self.lines[index] = stripped

    def getEncoding(self):
        """Provides the encoding"""
        if self.explicitUserEncoding:
            return self.explicitUserEncoding
        return self.encoding

    def isCommentLine(self, line):
        """True if it is a comment line. line is 0-based"""
        if line >= len(self.lines):
            return False
        txt = self.lines[line]
        nonSpaceIndex = self.firstNonSpaceIndex(txt)
        if nonSpaceIndex is None:
            return False
        if txt[nonSpaceIndex] != '#':
            return False
        return not self.isStringLiteral(line, nonSpaceIndex)

    def isLineEmpty(self, line):
        """Returns True if the line is empty. Line is 0 based"""
        return self.lines[line].strip() == ""

    def getSearchText(self, selectionOnly=False):
        """Provides the guessed text for searching"""
        if self.selectedText:
            if '\r' in self.selectedText or '\n' in self.selectedText:
                # The selection contains at least a newline, it is
                # unlikely to be the expression to search for
                return ''
            return self.selectedText

        return '' if selectionOnly else self.getCurrentWord()

    # Search supporting members

    def __resetMatchCache(self):
        """Resets the cached search results"""
        self.__matchesCache = None
        self.__matchesRegexp = None

    def __searchInText(self, regExp, startPoint, forward):
        """Search in text and return the nearest match"""
        self.findAllMatches(regExp)
        if self.__matchesCache:
            if forward:
                for match in self.__matchesCache:
                    if match.start() >= startPoint:
                        break
                else:  # wrap, search from start
                    match = self.__matchesCache[0]
            else:  # reverse search
                for match in self.__matchesCache[::-1]:
                    if match.start() < startPoint:
                        break
                else:  # wrap, search from end
                    match = self.__matchesCache[-1]
            return match
        return None

    def getCurrentOrSelection(self):
        """Provides what should be used for search.

        Returns a tuple:
        - word
        - True if it was a selection
        - start abs pos
        - end abs pos
        """
        cursor = self.textCursor()
        if cursor.hasSelection():
            word = cursor.selectedText()
            if '\r' not in word and '\n' not in word:
                return word, True, cursor.anchor(), cursor.position()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText(), False, cursor.anchor(), cursor.position()

    def findAllMatches(self, regExp):
        """Find all matches of regExp"""
        if self.__matchesRegexp != regExp or self.__matchesCache is None:
            self.__matchesRegexp = regExp
            self.__matchesCache = [match
                                   for match in regExp.finditer(self.text)]
        return self.__matchesCache

    def updateFoundItemsHighlighting(self, regExp):
        """Updates the highlight. Returns False if there were too many."""
        matches = self.findAllMatches(regExp)
        count = len(matches)
        if count > Settings()['maxHighlightedMatches']:
            self.setExtraSelections([])
            return False

        self.setExtraSelections([(match.start(), len(match.group(0)))
                                for match in matches])
        return True

    def __highlightRegexp(self, regExp, searchPos, forward):
        """Highlights the matches, moves cursor, displays message"""
        highlighted = self.updateFoundItemsHighlighting(regExp)
        match = self.__searchInText(regExp, searchPos, forward)
        if match is not None:
            matchIndex = self.__matchesCache.index(match) + 1
            totalMatches = len(self.__matchesCache)
            self.absCursorPosition = match.start()
            self.ensureCursorVisible()

        if highlighted:
            if self.__matchesCache:
                msg = 'Match %d of %d' % (matchIndex, totalMatches)
            else:
                msg = 'No matches'
        else:
            msg = 'Too many matches to highlight (%d exceeds the limit of %d' + \
                '). Match %d of %d' % \
                (len(self.__matchesCache), Settings()['maxHighlightedMatches'],
                 matchIndex, totalMatches)

        mainWindow = GlobalData().mainWindow
        mainWindow.showStatusBarMessage(msg, 5000)

    def onHighlight(self):
        """Triggered when Ctrl+' is clicked"""
        word, wasSelection, _, absEnd = self.getCurrentOrSelection()
        if not word or '\r' in word or '\n' in word:
            return

        if wasSelection:
            regExp = re.compile('%s' % re.escape(word), re.IGNORECASE)
        else:
            regExp = re.compile('\\b%s\\b' % re.escape(word), re.IGNORECASE)

        self.__highlightRegexp(regExp, absEnd, False)

    def onNextHighlight(self):
        """Triggered when Ctrl+. is clicked"""
        if self.__matchesRegexp is None or self.__matchesCache is None:
            self.onHighlight()
        else:
            self.__highlightRegexp(self.__matchesRegexp,
                                   self.absCursorPosition + 1, True)

    def onPrevHighlight(self):
        """Triggered when Ctrl+, is clicked"""
        if self.__matchesRegexp is None or self.__matchesCache is None:
            self.onHighlight()
        else:
            self.__highlightRegexp(self.__matchesRegexp,
                                   self.absCursorPosition - 1, False)
