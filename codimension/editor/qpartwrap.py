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
import logging
import os.path
import socket
import urllib.request
from qutepart import Qutepart
from ui.qt import (QPalette, pyqtSignal, QTextCursor, QApplication,
                   QCursor, Qt, QDesktopServices, QUrl)
from utils.globals import GlobalData
from utils.settings import Settings
from utils.colorfont import getZoomedMonoFont
from utils.encoding import decodeURLContent


WORD_AT_END_REGEXP = re.compile("\w+$")
WORD_AT_START_REGEXP = re.compile("^\w+")


class QutepartWrapper(Qutepart):

    """Convenience qutepart wrapper"""

    sigHighlighted = pyqtSignal(str, int, int)

    # Shared between buffers
    matchesRegexp = None
    highlightOn = False

    def __init__(self, parent):
        Qutepart.__init__(self, parent)

        self.encoding = None
        self.explicitUserEncoding = None
        self.mime = None

        # Remove all the default margins
        self.delMargin('mark_area')
        self.delMargin('line_numbers')
        self.completionEnabled = False

        # Search/replace support
        self.__matchesCache = None
        self.textChanged.connect(self.__resetMatchCache)

    def _dropUserExtraSelections(self):
        """Suppressing highlight removal when the text is changed"""
        pass

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

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.setFont(getZoomedMonoFont())
        for margin in self.getMargins():
            if hasattr(margin, 'onTextZoomChanged'):
                margin.onTextZoomChanged()
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

    def setFirstVisible(self, lineno):
        """Scrolls the editor to make sure the first visible line is lineno"""
        currentVisible = self.firstVisibleLine()
        if currentVisible == lineno:
            return

        # Initial setting
        self.verticalScrollBar().setValue(lineno)
        currentVisible = self.firstVisibleLine()

        while currentVisible != lineno:
            vbValue = self.verticalScrollBar().value()
            distance = lineno - currentVisible
            if distance > 0:
                distance = min(2, distance)
            else:
                distance = max(-2, distance)
            self.verticalScrollBar().setValue(vbValue + distance)
            vbValueAfter = self.verticalScrollBar().value()
            if vbValueAfter == vbValue:
                break
            currentVisible = self.firstVisibleLine()
        self.setHScrollOffset(0)

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
        hBar = self.horizontalScrollBar()
        if hBar:
            hBar.setValue(value)

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

    def __getNewHomePos(self, toFirstNonSpace):
        """Provides the new cursor position for a HOME click"""
        line, pos = self.cursorPosition
        newPos = 0
        if toFirstNonSpace:
            lStripped = self.lines[line].lstrip()
            if lStripped:
                calcPos = len(self.lines[line]) - len(lStripped)
                newPos = 0 if pos <= calcPos else calcPos
        return line, newPos

    def moveToLineBegin(self, toFirstNonSpace):
        """Jumps to the first non-space or to position 0"""
        newLine, newPos = self.__getNewHomePos(toFirstNonSpace)
        self.cursorPosition = newLine, newPos

    def selectTillLineBegin(self, toFirstNonSpace):
        """Selects consistently with HOME behavior"""
        newLine, newPos = self.__getNewHomePos(toFirstNonSpace)
        cursor = self.textCursor()
        cursor.setPosition(self.mapToAbsPosition(newLine, newPos),
                           QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def onHome(self):
        """Triggered when HOME is received"""
        self.moveToLineBegin(Settings()['jumpToFirstNonSpace'])

    def onShiftHome(self):
        """Triggered when Shift+HOME is received"""
        self.selectTillLineBegin(Settings()['jumpToFirstNonSpace'])

    def onShiftEnd(self):
        """Selects till the end of line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def onShiftDel(self):
        """Triggered when Shift+Del is received"""
        if self.selectedText:
            QApplication.clipboard().setText(self.selectedText)
            self.selectedText = ''
        else:
            line, _ = self.cursorPosition
            if self.lines[line]:
                QApplication.clipboard().setText(self.lines[line] + '\n')
                del self.lines[line]

    def onCtrlC(self):
        """Handles copying"""
        if self.selectedText:
            QApplication.clipboard().setText(self.selectedText)
        else:
            line, _ = self.cursorPosition
            if self.lines[line]:
                QApplication.clipboard().setText(self.lines[line] + '\n')

    def openAsFile(self):
        """Opens a selection or a current tag as a file"""
        path = self.selectedText.strip()
        if path == "" or '\n' in path or '\r' in path:
            return

        # Now the processing
        if os.path.isabs(path):
            GlobalData().mainWindow.detectTypeAndOpenFile(path)
            return

        # This is not an absolute path but could be a relative path for the
        # current buffer file. Let's try it.
        fileName = self._parent.getFileName()
        if fileName != "":
            # There is a file name
            fName = os.path.dirname(fileName) + os.path.sep + path
            fName = os.path.abspath(os.path.realpath(fName))
            if os.path.exists(fName):
                GlobalData().mainWindow.detectTypeAndOpenFile(fName)
                return
        if GlobalData().project.isLoaded():
            # Try it as a relative path to the project
            prjFile = GlobalData().project.fileName
            fName = os.path.dirname(prjFile) + os.path.sep + path
            fName = os.path.abspath(os.path.realpath(fName))
            if os.path.exists(fName):
                GlobalData().mainWindow.detectTypeAndOpenFile(fName)
                return
        # The last hope - open as is
        if os.path.exists(path):
            path = os.path.abspath(os.path.realpath(path))
            GlobalData().mainWindow.detectTypeAndOpenFile(path)
            return

        logging.error("Cannot find '" + path + "' to open")

    def downloadAndShow(self):
        """Triggered when the user wants to download and see the file"""
        url = self.selectedText.strip()
        if url.lower().startswith("www."):
            url = "http://" + url

        oldTimeout = socket.getdefaulttimeout()
        newTimeout = 5      # Otherwise the pause is too long
        socket.setdefaulttimeout(newTimeout)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        try:
            response = urllib.request.urlopen(url)
            content = decodeURLContent(response.read())

            # The content has been read sucessfully
            mainWindow = GlobalData().mainWindow
            mainWindow.editorsManager().newTabClicked(content,
                                                      os.path.basename(url))
        except Exception as exc:
            logging.error("Error downloading '" + url + "'\n" + str(exc))

        QApplication.restoreOverrideCursor()
        socket.setdefaulttimeout(oldTimeout)

    def openInBrowser(self):
        """Triggered when a selected URL should be opened in a browser"""
        url = self.selectedText.strip()
        if url.lower().startswith("www."):
            url = "http://" + url
        QDesktopServices.openUrl(QUrl(url))

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

    def removeTrailingWhitespaces(self):
        """Removes trailing whitespaces"""
        # Note: two loops are for the case when there is nothing to expand.
        # The 'with' statement leads to a detection of a changed position
        # which triggers the other actions.
        index = 0
        for index, line in enumerate(self.lines):
            stripped = line.rstrip()
            if stripped != line:
                break
        else:
            self.__showStatusBarMessage('No trailing spaces found')
            return

        with self:
            lastIndex = len(self.lines) - 1
            while index <= lastIndex:
                stripped = self.lines[index].rstrip()
                if stripped != self.lines[index]:
                    self.lines[index] = stripped
                index += 1

    def expandTabs(self, tabsize):
        """Expands tabs if needed"""
        # Note: two loops are for the case when there is nothing to expand.
        # The 'with' statement leads to a detection of a changed position
        # which triggers the other actions.
        index = 0
        for index, line in enumerate(self.lines):
            expanded = line.expandtabs(tabsize)
            if expanded != line:
                break
        else:
            self.__showStatusBarMessage('No tabs found')
            return

        with self:
            lastIndex = len(self.lines) - 1
            while index <= lastIndex:
                expanded = self.lines[index].expandtabs(tabsize)
                if expanded != self.lines[index]:
                    self.lines[index] = expanded
                index += 1

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

    def isStringLiteral(self, line, pos):
        """True if it is a string literal"""
        if self._highlighter is None:
            return False
        if pos < 0:
            # May happened if the line is empty
            return False

        block = self.document().findBlockByNumber(line)
        data = block.userData()
        if data is None:
            return False
        try:
            return self._highlighter._syntax._getTextType(data.data,
                                                          pos) == 's'
        except IndexError:
            return False

    # Search supporting members

    def resetHighlight(self):
        """Resets the highlight if so"""
        self.resetMatchCache()
        self.setExtraSelections([])
        QutepartWrapper.highlightOn = False

    def __resetMatchCache(self):
        """Resets the matches cache when the text is modified"""
        # The highlight does not need to be switched off
        self.__matchesCache = None

    def resetMatchCache(self):
        """Resets the matches cache.

        Happens when a search criteria changed in the otehr editors.
        """
        if not self.isVisible():
            if self._userExtraSelections:
                self.setExtraSelections([])
        self.__matchesCache = None

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
                    if match.start() <= startPoint:
                        break
                else:  # wrap, search from end
                    match = self.__matchesCache[-1]
            return match
        return None

    def isCursorOnMatch(self):
        """True if the cursor is on the first pos of any match"""
        if self.__matchesCache:
            pos = self.absCursorPosition
            for match in self.__matchesCache:
                if match.start() == pos:
                    return True
        return False

    def getCurrentMatchesCount(self):
        """Provides the number of the current matches"""
        if self.__matchesCache:
            return len(self.__matchesCache)
        return 0

    def getMatchesInfo(self):
        """Returns match number or None and total number of matches"""
        matchNumber = None
        totalMatches = None
        if self.__matchesCache:
            pos = self.absCursorPosition
            totalMatches = 0
            for match in self.__matchesCache:
                totalMatches += 1
                if match.start() == pos:
                    matchNumber = totalMatches
        return matchNumber, totalMatches

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

    def getCurrentWord(self):
        """Provides the current word if so"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def getWordBeforeCursor(self):
        """Provides a word before the cursor"""
        cursor = self.textCursor()
        textBeforeCursor = cursor.block().text()[:cursor.positionInBlock()]
        match = WORD_AT_END_REGEXP.search(textBeforeCursor)
        return match.group(0) if match else ''

    def getWordAfterCursor(self):
        """Provides a word after cursor"""
        cursor = self.textCursor()
        textAfterCursor = cursor.block().text()[cursor.positionInBlock():]
        match = WORD_AT_START_REGEXP.search(textAfterCursor)
        return match.group(0) if match else ''

    def onFirstChar(self):
        """Jump to the first character in the buffer"""
        self.cursorPosition = 0, 0
        self.ensureLineOnScreen(0)
        self.setHScrollOffset(0)

    def onLastChar(self):
        """Jump to the last char"""
        line = len(self.lines)
        if line != 0:
            line -= 1
        pos = len(self.lines[line])
        self.cursorPosition = line, pos
        self.ensureLineOnScreen(line)
        self.setHScrollOffset(0)

    def clearSelection(self):
        """Clears the current selection if so"""
        cursor = self.textCursor()
        cursor.clearSelection()

    def findAllMatches(self, regExp):
        """Find all matches of regExp"""
        if QutepartWrapper.matchesRegexp != regExp or \
                self.__matchesCache is None:
            QutepartWrapper.matchesRegexp = regExp
            self.__matchesCache = [match
                                   for match in regExp.finditer(self.text)]
        QutepartWrapper.highlightOn = True
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

    def highlightRegexp(self, regExp, searchPos, forward, needMessage=True):
        """Highlights the matches, moves cursor, displays message"""
        highlighted = self.updateFoundItemsHighlighting(regExp)
        match = self.__searchInText(regExp, searchPos, forward)
        if match is not None:
            matchIndex = self.__matchesCache.index(match) + 1
            totalMatches = len(self.__matchesCache)
            self.absCursorPosition = match.start()
            self.ensureCursorVisible()

        if needMessage:
            if highlighted:
                if self.__matchesCache:
                    msg = 'match %d of %d' % (matchIndex, totalMatches)
                else:
                    msg = 'no matches'
            else:
                msg = 'match %d of %d (too many to highlight, ' \
                      'exceeds the limit of %d)' % \
                      (matchIndex, totalMatches,
                       Settings()['maxHighlightedMatches'])
            self.__showStatusBarMessage(msg)
        return len(self.__matchesCache)

    def clearSearchIndicators(self):
        """Hides the search indicator"""
        self.resetHighlight()
        GlobalData().mainWindow.clearStatusBarMessage()

    def onHighlight(self):
        """Triggered when Ctrl+' is clicked"""
        if self.isCursorOnHighlight():
            return self.onNextHighlight()

        word, wasSelection, _, absEnd = self.getCurrentOrSelection()
        if not word or '\r' in word or '\n' in word:
            return 0

        # Reset match cashe in all the buffers
        # Otherwise they keep an old highlight when the user switches to them
        mainWindow = GlobalData().mainWindow
        mainWindow.editorsManager().resetTextSearchMatchCache()

        wordFlag = 0
        if wasSelection:
            regExp = re.compile('%s' % re.escape(word), re.IGNORECASE)
        else:
            regExp = re.compile('\\b%s\\b' % re.escape(word), re.IGNORECASE)
            wordFlag = 1

        count = self.highlightRegexp(regExp, absEnd, False)
        self.sigHighlighted.emit(word, wordFlag, count)
        return count

    def mouseDoubleClickEvent(self, event):
        """Highlight the current word keeping the selection"""
        Qutepart.mouseDoubleClickEvent(self, event)
        if self.selectedText:
            selectedPos = self.absSelectedPosition
            self.onHighlight()
            self.absSelectedPosition = selectedPos

    def onNextHighlight(self):
        """Triggered when Ctrl+. is clicked"""
        if QutepartWrapper.matchesRegexp is None:
            return self.onHighlight()

        if QutepartWrapper.highlightOn:
            # The current highlight is on
            return self.highlightRegexp(QutepartWrapper.matchesRegexp,
                                        self.absCursorPosition + 1, True)

        # Not highlighted. If within the currently matched word, then the
        # cursor should stay on it.
        wordBefore = self.getWordBeforeCursor()
        return self.highlightRegexp(QutepartWrapper.matchesRegexp,
                                    self.absCursorPosition - len(wordBefore),
                                    True)

    def onPrevHighlight(self):
        """Triggered when Ctrl+, is clicked"""
        if QutepartWrapper.matchesRegexp is None:
            return self.onHighlight()

        if QutepartWrapper.highlightOn:
            # The current highlight is on
            return self.highlightRegexp(QutepartWrapper.matchesRegexp,
                                        self.absCursorPosition - 1, False)

        # Not highlighted. If within the currently matched word, then the
        # cursor should stay on it.
        return self.highlightRegexp(QutepartWrapper.matchesRegexp,
                                    self.absCursorPosition, False)

    def replaceAllMatches(self, replaceText):
        """Replaces all the current matches with the other text"""
        if not self.__matchesCache:
            return

        replaceCount = 0
        noReplaceCount = 0
        for match in self.__matchesCache[::-1]:
            textToReplace = self.text[match.start():
                                      match.start() + len(match.group(0))]
            if textToReplace == replaceText:
                noReplaceCount += 1
            else:
                replaceCount += 1

        if replaceCount > 0:
            cursorPos = None
            delta = 0
            regExp = QutepartWrapper.matchesRegexp
            with self:
                # reverse order, because replacement may move indexes
                for match in self.__matchesCache[::-1]:
                    textToReplace = self.text[match.start():
                                              match.start() +
                                              len(match.group(0))]
                    if textToReplace != replaceText:
                        self.replaceText(match.start(), len(match.group(0)),
                                         replaceText)

                    if cursorPos is None:
                        cursorPos = self.absCursorPosition
                    else:
                        delta += len(replaceText) - len(textToReplace)

            self.resetHighlight()
            self.updateFoundItemsHighlighting(regExp)
            self.absCursorPosition = cursorPos + delta

        if replaceCount == 1:
            msg = '1 match replaced'
        else:
            msg = '%d matches replaced' % replaceCount

        if noReplaceCount > 0:
            msg += '; %d skipped ' \
                   '(the highlight matches replacement)' % noReplaceCount

        self.__showStatusBarMessage(msg)

    def replaceMatch(self, replaceText):
        """Replaces the match on which the cursor is"""
        if self.__matchesCache:
            pos = self.absCursorPosition
            for match in self.__matchesCache:
                if match.start() == pos:
                    regExp = QutepartWrapper.matchesRegexp
                    textToReplace = self.text[match.start():
                                              match.start() +
                                              len(match.group(0))]
                    if textToReplace == replaceText:
                        msg = "no replace: the highlight matches replacement"
                    else:
                        self.replaceText(match.start(), len(match.group(0)),
                                         replaceText)
                        self.__matchesCache = None
                        self.updateFoundItemsHighlighting(regExp)
                        msg = "1 match replaced"

                    self.__showStatusBarMessage(msg)
                    break

    def isCursorOnHighlight(self):
        """True if the current cursor position is on the highlighted text"""
        if QutepartWrapper.highlightOn:
            pos = self.absCursorPosition
            self.findAllMatches(QutepartWrapper.matchesRegexp)
            for match in self.__matchesCache:
                if pos >= match.start() and pos < match.end():
                    return True
        return False

    def onTabChanged(self):
        """Called by find/replace widget"""
        if QutepartWrapper.highlightOn:
            # Highlight the current regexp without changing the cursor position
            self.updateFoundItemsHighlighting(QutepartWrapper.matchesRegexp)
        else:
            self.resetHighlight()

    @staticmethod
    def __showStatusBarMessage(msg):
        """Shows a main window status bar message"""
        mainWindow = GlobalData().mainWindow
        mainWindow.showStatusBarMessage(msg, 8000)

    def getEndPosition(self):
        """Provides the end position, 0 based"""
        line = len(self.lines) - 1
        return (line, len(self.lines[line]))

    def append(self, text):
        """Appends the given text to the end"""
        if not text:
            return

        # Tail separator could be stripped otherwise; also there are so many
        # separators:
        # https://docs.python.org/3.5/library/stdtypes.html#str.splitlines
        partsNoEnd = text.splitlines()
        partsWithEnd = text.splitlines(True)

        lastIndex = len(partsNoEnd) - 1
        with self:
            for index, value in enumerate(partsNoEnd):
                if value:
                    self.lines[-1] += value
                if index == lastIndex:
                    if value != partsWithEnd[index]:
                        self.lines.append('')
                else:
                    self.lines.append('')

    def gotoLine(self, line, pos=None, firstVisible=None):
        """Jumps to the given position and scrolls if needed.

        line and pos and firstVisible are 1-based
        """
        # Normalize editor line and pos
        editorLine = line - 1
        if editorLine < 0:
            editorLine = 0
        if pos is None or pos <= 0:
            editorPos = 0
        else:
            editorPos = pos - 1

        if self.isLineOnScreen(editorLine):
            if firstVisible is None:
                self.cursorPosition = editorLine, editorPos
                return

        self.ensureLineOnScreen(editorLine)

        # Otherwise we would deal with scrolling any way, so normalize
        # the first visible line
        if firstVisible is None:
            editorFirstVisible = editorLine - 1
        else:
            editorFirstVisible = firstVisible - 1
        if editorFirstVisible < 0:
            editorFirstVisible = 0

        self.cursorPosition = editorLine, editorPos
        self.setFirstVisible(editorFirstVisible)

    def openAsFileAvailable(self):
        """True if there is something to try to open as a file"""
        selectedText = self.selectedText.strip()
        if selectedText:
            return '\n' not in selectedText and '\r' not in selectedText
        return False

    def downloadAndShowAvailable(self):
        """True if download and show available"""
        selectedText = self.selectedText.strip()
        if '\n' not in selectedText and '\r' not in selectedText:
            return selectedText.lower().startswith('http://') or \
                   selectedText.lower().startswith('www.')
        return False
