# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Text editor implementation"""


import os.path
import logging
from ui.qt import (Qt, QTimer, pyqtSignal, QRect, QEvent, QModelIndex,
                   QCursor, QApplication, QTextOption)
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from ui.completer import CodeCompleter
from ui.findinfiles import ItemToSearchIn, getSearchItemIndex
from ui.calltip import Calltip
from utils.globals import GlobalData
from utils.settings import Settings
from utils.encoding import (readEncodedFile, detectEolString,
                            detectWriteEncoding, writeEncodedFile)
from utils.fileutils import getFileProperties, isPythonMime
from utils.diskvaluesrelay import setFileEncoding, getFileEncoding
from autocomplete.bufferutils import (getContext, getPrefixAndObject,
                                      getEditorTags, isStringLiteral,
                                      getCallPosition, getCommaCount)
from autocomplete.completelists import (getCompletionList, getCalltipAndDoc,
                                        getDefinitionLocation, getOccurrences)
from cdmbriefparser import getBriefModuleInfoFromMemory
from debugger.bputils import getBreakpointLines
from debugger.breakpoint import Breakpoint
from .qpartwrap import QutepartWrapper
from .editorcontextmenus import EditorContextMenuMixin
from .linenomargin import CDMLineNumberMargin
from .flakesmargin import CDMFlakesMargin


CTRL_SHIFT = int(Qt.ShiftModifier | Qt.ControlModifier)
SHIFT = int(Qt.ShiftModifier)
CTRL = int(Qt.ControlModifier)
ALT = int(Qt.AltModifier)
CTRL_KEYPAD = int(Qt.KeypadModifier | Qt.ControlModifier)
NO_MODIFIER = int(Qt.NoModifier)


class TextEditor(QutepartWrapper, EditorContextMenuMixin):

    """Text editor implementation"""


    sigEscapePressed = pyqtSignal()
    cflowSyncRequested = pyqtSignal(int, int, int)

    def __init__(self, parent, debugger):
        self._parent = parent
        QutepartWrapper.__init__(self, parent)
        EditorContextMenuMixin.__init__(self)

        self.setAttribute(Qt.WA_KeyCompression)

        self.__debugger = debugger

        skin = GlobalData().skin
        self.setPaper(skin['nolexerPaper'])
        self.setColor(skin['nolexerColor'])
        self.setFont(skin['monoFont'])

        self.__initMargins()

        # self.SCN_DOUBLECLICK.connect(self.__onDoubleClick)
        # self.cursorPositionChanged.connect(self._onCursorPositionChanged)

        # self.SCN_MODIFIED.connect(self.__onSceneModified)
        self.__skipChangeCursor = False

        self.__openedLine = None

        self.__breakpoints = {}         # marker handle -> Breakpoint

        self.setFocusPolicy(Qt.StrongFocus)
        self.indentWidth = 4

        self.updateSettings()

        # Completion support
        self.__completionObject = ""
        self.__completionPrefix = ""
        self.__completionLine = -1
        self.__completionPos = -1
        self.__completer = CodeCompleter(self)
        self.__inCompletion = False
        self.__completer.activated.connect(self.insertCompletion)
        self.__lastTabPosition = -1

        # Calltip support
        self.__calltip = None
        self.__callPosition = None
        self.__calltipTimer = QTimer(self)
        self.__calltipTimer.setSingleShot(True)
        self.__calltipTimer.timeout.connect(self.__onCalltipTimer)

        # Breakpoint support
        self.__inLinesChanged = False
        if self.__debugger:
            bpointModel = self.__debugger.getBreakPointModel()
            bpointModel.rowsAboutToBeRemoved.connect(self.__deleteBreakPoints)
            bpointModel.sigDataAboutToBeChanged.connect(
                self.__breakPointDataAboutToBeChanged)
            bpointModel.dataChanged.connect(self.__changeBreakPoints)
            bpointModel.rowsInserted.connect(self.__addBreakPoints)

        self.__initHotKeys()
        self.installEventFilter(self)

    def dedentLine(self):
        pass

    def __initHotKeys(self):
        """Initializes a map for the hot keys event filter"""
        self.__hotKeys = {
            CTRL_SHIFT: {Qt.Key_F1: self.onCallHelp,
                         Qt.Key_T: self.onJumpToTop,
                         Qt.Key_M: self.onJumpToMiddle,
                         Qt.Key_B: self.onJumpToBottom},
            SHIFT: {Qt.Key_Delete: self.onShiftDel,
                    Qt.Key_Tab: self.dedentLine,
                    Qt.Key_Backtab: self.dedentLine,
                    Qt.Key_End: self.onShiftEnd,
                    Qt.Key_Home: self.onShiftHome},
            CTRL: {Qt.Key_X: self.onShiftDel,
                   Qt.Key_C: self.onCtrlC,
                   Qt.Key_Insert: self.onCtrlC,
                   Qt.Key_Apostrophe: self.onHighlight,
                   Qt.Key_Period: self.onNextHighlight,
                   Qt.Key_Comma: self.onPrevHighlight,
                   Qt.Key_M: self.onCommentUncomment,
                   Qt.Key_Space: self.onAutoComplete,
                   Qt.Key_F1: self.onTagHelp,
                   Qt.Key_Backslash: self.onGotoDefinition,
                   Qt.Key_BracketRight: self.onOccurences,
                   Qt.Key_Slash: self.onShowCalltip,
                   Qt.Key_Minus: self.onZoomOut,
                   Qt.Key_Equal: self.onZoomIn,
                   Qt.Key_0: self.onZoomReset,
                   Qt.Key_Home: self.onFirstChar,
                   Qt.Key_End: self.onLastChar,
                   Qt.Key_B: self.highlightInOutline,
                   Qt.Key_QuoteLeft: self.highlightInCFlow},
            ALT: {Qt.Key_U: self.onScopeBegin},
            CTRL_KEYPAD: {Qt.Key_Minus: self.onZoomOut,
                          Qt.Key_Plus: self.onZoomIn,
                          Qt.Key_0: self.onZoomReset},
            NO_MODIFIER: {Qt.Key_Home: self.onHome,
                          Qt.Key_End: self.moveToLineEnd,
                          Qt.Key_F12: self.makeLineFirst}}

        # Not all the derived classes need certain tool functionality
        if hasattr(self._parent, "onOpenImport" ):
            self.__hotKeys[CTRL][Qt.Key_I] = self._parent.onOpenImport
        if hasattr(self._parent, "onNavigationBar"):
            self.__hotKeys[NO_MODIFIER][Qt.Key_F2] = \
                self._parent.onNavigationBar

    # Arguments: obj, event
    def eventFilter(self, _, event):
        """Event filter to catch shortcuts on UBUNTU"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = int(event.modifiers())
            try:
                if modifiers in self.__hotKeys:
                    if key in self.__hotKeys[modifiers]:
                        self.__hotKeys[modifiers][key]()
                        return True
            except Exception as exc:
                logging.warning(str(exc))
        return False

    def wheelEvent(self, event):
        """Mouse wheel event"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            angleDelta = event.angleDelta()
            if not angleDelta.isNull():
                if angleDelta.y() > 0:
                    self.onZoomIn()
                else:
                    self.onZoomOut()
            event.accept()
        else:
            QutepartWrapper.wheelEvent(self, event)

    def focusInEvent(self, event):
        """Enable Shift+Tab when the focus is received"""
        if self._parent.shouldAcceptFocus():
            QutepartWrapper.focusInEvent(self, event)
        else:
            self._parent.setFocus()

    def focusOutEvent(self, event):
        """Disable Shift+Tab when the focus is lost"""
        self.__completer.hide()
        if not self.__inCompletion:
            self.__resetCalltip()
        QutepartWrapper.focusOutEvent(self, event)

    def updateSettings(self):
        """Updates the editor settings"""
        settings = Settings()

        if settings['verticalEdge']:
            self.lineLengthEdge = settings['editorEdge']
            self.lineLengthEdgeColor = GlobalData().skin['edgeColor']
            self.drawSolidEdge = True
        else:
            self.lineLengthEdge = None

        self.drawAnyWhitespace = settings['showSpaces']
        self.drawIncorrectIndentation = settings['showSpaces']

        if settings['lineWrap']:
            self.setWordWrapMode(QTextOption.WrapAnywhere)
        else:
            self.setWordWrapMode(QTextOption.NoWrap)

        if hasattr(self._parent, "getNavigationBar"):
            navBar = self._parent.getNavigationBar()
            if navBar:
                navBar.updateSettings()

    def __initMargins(self):
        """Initializes the editor margins"""
        self.addMargin(CDMLineNumberMargin(self))
        self.addMargin(CDMFlakesMargin(self))
        self.getMargin('cdm_flakes_margin').setVisible(False)

    def highlightCurrentDebuggerLine(self, line, asException):
        """Highlights the current debugger line"""
        if asException:
            self.markerAdd(line - 1, self.__exceptionLineMarker)
            self.markerAdd(line - 1, self.__excptMarker)
        else:
            self.markerAdd(line - 1, self.__currentDebuggerLineMarker)
            self.markerAdd(line - 1, self.__dbgMarker)

    def clearCurrentDebuggerLine(self):
        """Removes the current debugger line marker"""
        pass

    def readFile(self, fileName):
        """Reads the text from a file"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            content, self.encoding = readEncodedFile(fileName)
            self.eol = detectEolString(content)

            # Hack to avoid breakpoints reset when a file is reload
            self.__breakpoints = {}
            self.text = content

            self.mime, _, xmlSyntaxFile = getFileProperties(fileName)
            if xmlSyntaxFile:
                self.detectSyntax(xmlSyntaxFile)

            self.document().setModified(False)
        except:
            QApplication.restoreOverrideCursor()
            raise

        QApplication.restoreOverrideCursor()

    def writeFile(self, fileName):
        """Writes the text to a file"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        if Settings()['removeTrailingOnSave']:
            self.removeTrailingWhitespaces()

        try:
            encoding = detectWriteEncoding(self, fileName)
            if encoding is None:
                QApplication.restoreOverrideCursor()
                return False

            writeEncodedFile(fileName, self.textForSaving(), encoding)
        except Exception as exc:
            logging.error(str(exc))
            QApplication.restoreOverrideCursor()
            return False

        self.encoding = encoding
        if self.explicitUserEncoding:
            userEncoding = getFileEncoding(fileName)
            if userEncoding != self.explicitUserEncoding:
                setFileEncoding(fileName, self.explicitUserEncoding)
            self.explicitUserEncoding = None

        self._parent.updateModificationTime(fileName)
        self._parent.setReloadDialogShown(False)
        QApplication.restoreOverrideCursor()
        return True

    def clearSearchIndicators(self):
        """Hides the search indicator"""
        self.resetHighlight()
        GlobalData().mainWindow.clearStatusBarMessage()

    def keyPressEvent(self, event):
        """Handles the key press events"""
        self.__skipChangeCursor = True
        key = event.key()
        if self.__completer.isVisible():
            self.__skipChangeCursor = False
            if key == Qt.Key_Escape:
                self.__completer.hide()
                self.setFocus()
                return
            # There could be backspace or printed characters only
            QutepartWrapper.keyPressEvent(self, event)
            QApplication.processEvents()
            if key == Qt.Key_Backspace:
                if self.__completionPrefix == "":
                    self.__completer.hide()
                    self.setFocus()
                else:
                    self.__completionPrefix = self.__completionPrefix[:-1]
                    self.__completer.setPrefix(self.__completionPrefix)
            else:
                self.__completionPrefix += event.text()
                self.__completer.setPrefix(self.__completionPrefix)
                if self.__completer.completionCount() == 0:
                    self.__completer.hide()
                    self.setFocus()

        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            QApplication.processEvents()
            line, _ = self.cursorPosition

            QutepartWrapper.keyPressEvent(self, event)
            QApplication.processEvents()

            if line == self.__openedLine:
                self.lines[line] = ''

            # If the new line has one or more spaces then it is a candidate for
            # automatic trimming
            line, pos = self.cursorPosition
            text = self.lines[line]
            self.__openedLine = None
            if pos > 0 and len(text.strip()) == 0:
                self.__openedLine = line

        elif key in [Qt.Key_Up, Qt.Key_PageUp,
                     Qt.Key_Down, Qt.Key_PageDown]:
            line, _ = self.cursorPosition
            lineToTrim = line if line == self.__openedLine else None

            QutepartWrapper.keyPressEvent(self, event)
            QApplication.processEvents()

            if lineToTrim is not None:
                line, _ = self.cursorPosition
                if line != lineToTrim:
                    # The cursor was really moved to another line
                    self.lines[lineToTrim] = ''
            self.__openedLine = None

        elif key == Qt.Key_Escape:
            self.__resetCalltip()
            self.sigEscapePressed.emit()
            event.accept()

        elif key == Qt.Key_Tab:
            line, pos = self.cursorPosition
            currentPosition = self.cursorPosition
            if pos != 0:
                char = self.lines[line][pos - 1]
                if (char.isalnum() or char in ['_', '.']) and \
                   currentPosition != self.__lastTabPosition:
                    self.onAutoComplete()
                    event.accept()
                else:
                    QutepartWrapper.keyPressEvent(self, event)
            else:
                QutepartWrapper.keyPressEvent(self, event)
            self.__lastTabPosition = currentPosition
        elif key == Qt.Key_Z and \
            int(event.modifiers()) == (Qt.ControlModifier + Qt.ShiftModifier):
            event.accept()

        elif key == Qt.Key_ParenLeft:
            if Settings()['editorCalltips']:
                QutepartWrapper.keyPressEvent(self, event)
                self.onShowCalltip(False, False)
            else:
                QutepartWrapper.keyPressEvent(self, event)
        else:
            # Special keyboard keys are delivered as 0 values
            if key != 0:
                self.__openedLine = None
                QutepartWrapper.keyPressEvent(self, event)

        self.__skipChangeCursor = False

    def _onCursorPositionChanged(self, line, pos):
        """Triggered when the cursor changed the position"""
        if self.__calltip:
            if self.__calltipTimer.isActive():
                self.__calltipTimer.stop()
            self.__calltipTimer.start(500)

        if not self.__skipChangeCursor:
            if line == self.__openedLine:
                self.__openedLine = None
                return

            if self.__openedLine is not None:
                self.__skipChangeCursor = True
                self.lines[self.__openedLine] = ''
                self.__skipChangeCursor = False
                self.__openedLine = None

    def getCurrentPosFont(self):
        """Provides the font of the current character"""
        if self.lexer_ is not None:
            font = self.lexer_.font(self.styleAt(self.currentPosition()))
        else:
            font = self.font()
        font.setPointSize(font.pointSize() + self.getZoom())
        return font

    def __onDoubleClick(self, position, line, modifier):
        """Triggered when the user double clicks in the editor"""
        QApplication.processEvents()
        self.onHighlight()

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

    def onCommentUncomment(self):
        """Triggered when Ctrl+M is received"""
        if self.isReadOnly() or not self.isPythonBuffer():
            return

        with self:
            # Detect what we need - comment or uncomment
            line, _ = self.cursorPosition
            txt = self.lines[line]
            nonSpaceIndex = self.firstNonSpaceIndex(txt)
            if self.isCommentLine(line):
                # need to uncomment
                if nonSpaceIndex == len(txt) - 1:
                    # Strip the only '#' character
                    stripCount = 1
                else:
                    # Strip up to two characters if the next char is a ' '
                    if txt[nonSpaceIndex + 1] == ' ':
                        stripCount = 2
                    else:
                        stripCount = 1
                newTxt = txt[:nonSpaceIndex] + txt[nonSpaceIndex +
                                                   stripCount:]
                if not newTxt.strip():
                    newTxt = ''
                self.lines[line] = newTxt
            else:
                # need to comment
                if nonSpaceIndex is None:
                    self.lines[line] = '# '
                else:
                    newTxt = '# '.join((txt[:nonSpaceIndex],
                                        txt[nonSpaceIndex:]))
                    self.lines[line] = newTxt

            # Jump to the beginning of the next line
            if line + 1 < len(self.lines):
                line += 1
            self.cursorPosition = line, 0
            self.ensureLineOnScreen(line)

    def onAutoComplete(self):
        """Triggered when ctrl+space or TAB is clicked"""
        if self.isReadOnly():
            return True

        self.__inCompletion = True
        self.__completionObject, \
        self.__completionPrefix = getPrefixAndObject(self)

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        if not self.isPythonBuffer():
            words = list( getEditorTags(self, self.__completionPrefix))
            isModName = False
        else:
            text = self.text
            info = getBriefModuleInfoFromMemory(text)
            context = getContext(self, info)

            words, isModName = getCompletionList(self._parent.getFileName(),
                                                 context,
                                                 self.__completionObject,
                                                 self.__completionPrefix,
                                                 self, text, info)
        QApplication.restoreOverrideCursor()

        if len(words) == 0:
            self.setFocus()
            self.__inCompletion = False
            return True

        line, pos = self.cursorPosition
        if isModName:
            # The prefix should be re-taken because a module name may have '.'
            # in it.
            self.__completionPrefix = str(self.getWord(line, pos, 1,
                                                       True, "."))

        currentPosFont = self.getCurrentPosFont()
        self.__completer.setWordsList(words, currentPosFont)
        self.__completer.setPrefix(self.__completionPrefix)

        count = self.__completer.completionCount()
        if count == 0:
            self.setFocus()
            self.__inCompletion = False
            return True

        # Make sure the line is visible
        self.ensureLineOnScreen(line)
        xPos, yPos = self.getCurrentPixelPosition()
        if self.hasSelectedText():
            # Remove the selection as it could be interpreted not as expected
            self.setSelection(line, pos, line, pos)

        if count == 1:
            self.insertCompletion(self.__completer.currentCompletion())
            self.__inCompletion = False
            return True

        if self._charWidth <= 0:
            self.__detectCharWidth()
        if self._lineHeight <= 0:
            self.__detectLineHeight()

        # All the X Servers I tried have a problem with the line height, so I
        # have some spare points in the height
        cursorRectangle = QRect(xPos, yPos - 2,
                                self._charWidth, self._lineHeight + 8)
        self.__completer.complete(cursorRectangle)
        self.__inCompletion = False
        return True

    def onTagHelp(self):
        """Provides help for an item if available"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        calltip, docstring = getCalltipAndDoc(self._parent.getFileName(), self)
        if calltip is None and docstring is None:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage("Doc is not found")
            return True

        QApplication.restoreOverrideCursor()
        GlobalData().mainWindow.showTagHelp(calltip, docstring)
        return True

    def onCallHelp(self):
        """Provides help for the current call"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        callPosition = getCallPosition(self)
        if callPosition is None:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage("Not a function call")
            return True

        calltip, docstring = getCalltipAndDoc(self._parent.getFileName(),
                                              self, callPosition)
        if calltip is None and docstring is None:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage("Doc is not found")
            return True

        QApplication.restoreOverrideCursor()
        GlobalData().mainWindow.showTagHelp(calltip, docstring)
        return True

    def makeLineFirst(self):
        """Make the cursor line the first on the screen"""
        currentLine, _ = self.cursorPosition
        self.setFirstVisibleLine(currentLine)
        return True

    def onJumpToTop(self):
        """Jumps to the first position of the first visible line"""
        self.cursorPosition = self.firstVisibleLine(), 0

    def onJumpToMiddle(self):
        """Jumps to the first line pos in a middle of the editing area"""
        # Count the number of the visible line
        count = 0
        firstVisible = self.firstVisibleLine()
        lastVisible = self.lastVisibleLine()
        candidate = firstVisible
        while candidate <= lastVisible:
            if self.isLineVisible(candidate):
                count += 1
            candidate += 1

        shift = int(count / 2)
        jumpTo = firstVisible
        while shift > 0:
            if self.isLineVisible(jumpTo):
                shift -= 1
            jumpTo += 1
        self.cursorPosition = jumpTo, 0
        return True

    def onJumpToBottom(self):
        """Jumps to the first position of the last line"""
        currentFirstVisible = self.firstVisibleLine()
        self.cursorPosition = self.lastVisibleLine(), 0
        safeLastVisible = self.lastVisibleLine()

        while self.firstVisibleLine() != currentFirstVisible:
            # Here: a partially visible last line caused scrolling. So the
            # cursor needs to be set to the previous visible line
            self.cursorPosition = currentFirstVisible, 0
            safeLastVisible -= 1
            while not self.isLineVisible(safeLastVisible):
                safeLastVisible -= 1
            self.cursorPosition = safeLastVisible, 0
        return True

    def onGotoDefinition(self):
        """The user requested a jump to definition"""
        if not self.isPythonBuffer():
            return True

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        location = getDefinitionLocation(self._parent.getFileName(), self)
        QApplication.restoreOverrideCursor()
        if location is None:
            GlobalData().mainWindow.showStatusBarMessage(
                "Definition is not found")
        else:
            if location.resource is None:
                # That was an unsaved yet buffer, but something has been found
                GlobalData().mainWindow.jumpToLine(location.lineno)
            else:
                path = os.path.realpath(location.resource.real_path)
                GlobalData().mainWindow.openFile(path, location.lineno)
        return True

    def onScopeBegin(self):
        """The user requested jumping to the current scope begin"""
        if self.isPythonBuffer():
            info = getBriefModuleInfoFromMemory(self.text)
            context = getContext(self, info, True)
            if context.getScope() != context.GlobalScope:
                GlobalData().mainWindow.jumpToLine(context.getLastScopeLine())
        return True

    def onShowCalltip(self, showMessage=True, showKeyword=True):
        """The user requested show calltip"""
        if self.__calltip is not None:
            self.__resetCalltip()
            return True
        if not self.isPythonBuffer():
            return True

        # Temporary
        return True

        if self.styleAt(self.currentPosition()) in [
            QsciLexerPython.TripleDoubleQuotedString,
            QsciLexerPython.TripleSingleQuotedString,
            QsciLexerPython.DoubleQuotedString,
            QsciLexerPython.SingleQuotedString,
            QsciLexerPython.UnclosedString]:
            return True

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        callPosition = getCallPosition(self)
        if callPosition is None:
            QApplication.restoreOverrideCursor()
            self.__resetCalltip()
            if showMessage:
                GlobalData().mainWindow.showStatusBarMessage(
                    "Not a function call")
            return True

        if not showKeyword and \
           self.styleAt(callPosition) == QsciLexerPython.Keyword:
            QApplication.restoreOverrideCursor()
            self.__resetCalltip()
            return True

        calltip, docstring = getCalltipAndDoc(self._parent.getFileName(),
                                              self, callPosition, True)
        if calltip is None:
            QApplication.restoreOverrideCursor()
            self.__resetCalltip()
            if showMessage:
                GlobalData().mainWindow.showStatusBarMessage(
                    "Calltip is not found")
            return True

        currentPos = self.currentPosition()
        commas = getCommaCount(self, callPosition, currentPos)
        self.__calltip = Calltip(self)
        self.__calltip.showCalltip(str(calltip), commas)
        QApplication.restoreOverrideCursor()

        # Memorize how the tooltip was shown
        self.__callPosition = callPosition
        return True

    def __resetCalltip(self):
        """Hides the calltip and resets how it was shown"""
        self.__calltipTimer.stop()
        if self.__calltip is not None:
            self.__calltip.hide()
            self.__calltip = None
        self.__callPosition = None

    def resizeCalltip(self):
        """Resizes the calltip if so"""
        if self.__calltip:
            self.__calltip.resize()

    def __onCalltipTimer(self):
        """Handles the calltip update timer"""
        if self.__calltip:
            currentPos = self.currentPosition()
            if currentPos < self.__callPosition:
                self.__resetCalltip()
                return
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            callPosition = getCallPosition(self, currentPos)
            if callPosition != self.__callPosition:
                self.__resetCalltip()
            else:
                # It is still the same call, check the commas
                commas = getCommaCount(self, callPosition, currentPos)
                self.__calltip.highlightParameter(commas)
            QApplication.restoreOverrideCursor()

    def onOccurences(self):
        """The user requested a list of occurences"""
        if not self.isPythonBuffer():
            return True
        if self._parent.getType() in [MainWindowTabWidgetBase.VCSAnnotateViewer]:
            return True
        if not os.path.isabs(self._parent.getFileName()):
            GlobalData().mainWindow.showStatusBarMessage(
                "Save the buffer first")
            return True
        if self.document().isModified():
            # Check that the directory is writable for a temporary file
            dirName = os.path.dirname(self._parent.getFileName())
            if not os.access(dirName, os.W_OK):
                GlobalData().mainWindow.showStatusBarMessage(
                    "File directory is not writable. Cannot run rope.")
                return True

        # Prerequisites were checked, run the rope library
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        name, locations = getOccurrences(self._parent.getFileName(), self)
        if len(locations) == 0:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage(
                "No occurences of " + name + " found")
            return True

        # There are found items
        result = []
        for loc in locations:
            index = getSearchItemIndex(result, loc[0])
            if index < 0:
                widget = GlobalData().mainWindow.getWidgetForFileName(loc[0])
                if widget is None:
                    uuid = ""
                else:
                    uuid = widget.getUUID()
                newItem = ItemToSearchIn(loc[0], uuid)
                result.append(newItem)
                index = len(result) - 1
            result[index].addMatch(name, loc[1])

        QApplication.restoreOverrideCursor()

        GlobalData().mainWindow.displayFindInFiles("", result)
        return True

    def insertCompletion(self, text):
        """Triggered when a completion is selected"""
        if text:
            currentWord = str(self.getCurrentWord())
            prefixLength = len(str(self.__completionPrefix).decode('utf-8'))
            # wordLength = len( currentWord.decode( 'utf-8' ) )
            line, pos = self.cursorPosition

            if text == currentWord:
                # No changes, just possible cursor position change
                self.cursorPosition = line, pos + len(text) - prefixLength
            else:
                oldBuffer = QApplication.clipboard().text()
                with self:
                    self.setSelection(line, pos - prefixLength, line, pos)
                    self.removeSelectedText()
                    self.insert(text)
                    self.cursorPosition = line, pos + len(text) - prefixLength
                QApplication.clipboard().setText(oldBuffer)

            self.__completionPrefix = ""
            self.__completionObject = ""
            self.__completer.hide()

    def insertLines(self, text, line):
        """Inserts the given text into new lines starting from 1-based line"""
        toInsert = text.splitlines()
        with self:
            if line > 0:
                line -= 1
            for item in toInsert:
                self.lines.insert(line, item)
                line += 1

    def hideCompleter(self):
        """Hides the completer if visible"""
        self.__completer.hide()

    def clearPyflakesMessages(self):
        """Clears all the pyflakes markers"""
        self.getMargin('cdm_flakes_margin').clearPyflakesMessages()

    def setPyflakesMessages(self, messages):
        """Shows up a pyflakes messages"""
        self.getMargin('cdm_flakes_margin').setPyflakesMessages(messages)

    def highlightInCFlow(self):
        """Triggered when highlight in the control flow is requested"""
        if self.isPythonBuffer():
            line, pos = self.cursorPosition
            absPos = self.positionFromLineIndex(line, pos)
            self.cflowSyncRequested.emit(absPos, line + 1, pos + 1)

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

    ## Break points support

    def __breakpointMarginClicked(self, line):
        """Margin has been clicked. Line is 1 - based"""
        for handle, bpoint in self.__breakpoints.items():
            if self.markerLine(handle) == line - 1:
                # Breakpoint marker is set for this line already
                self.__toggleBreakpoint(line)
                return

        # Check if it is a python file
        if not self.isPythonBuffer():
            return

        fileName = self._parent.getFileName()
        if fileName is None or fileName == "" or not os.path.isabs(fileName):
            logging.warning("The buffer has to be saved "
                            "before breakpoints could be set")
            return


        breakableLines = getBreakpointLines("", self.text, True, False)
        if breakableLines is None:
            logging.warning("The breakable lines could not be identified "
                            "due to the file compilation errors. Fix the code "
                            "first and try again.")
            return

        breakableLines = list(breakableLines)
        breakableLines.sort()
        if not breakableLines:
            # There are no breakable lines
            return

        if line in breakableLines:
            self.__toggleBreakpoint(line)
            return

        # There are breakable lines however the user requested a line which
        # is not breakable
        candidateLine = breakableLines[0]
        if line < breakableLines[0]:
            candidateLine = breakableLines[0]
        elif line > breakableLines[-1]:
            candidateLine = breakableLines[-1]
        else:
            direction = 0
            if isStringLiteral(self,
                               self.positionFromLineIndex(line - 1, 0)):
                direction = 1
            elif self.isLineEmpty(line):
                direction = 1
            else:
                direction = -1

            for breakableLine in breakableLines[1:]:
                if direction > 0:
                    if breakableLine > line:
                        candidateLine = breakableLine
                        break
                else:
                    if breakableLine < line:
                        candidateLine = breakableLine
                    else:
                        break

        if not self.isLineOnScreen(candidateLine - 1):
            # The redirected breakpoint line is not on the screen, scroll it
            self.ensureLineOnScreen(candidateLine - 1)
            currentFirstVisible = self.firstVisibleLine()
            requiredVisible = candidateLine - 2
            if requiredVisible < 0:
                requiredVisible = 0
            self.scrollVertical(requiredVisible - currentFirstVisible)
        self.__toggleBreakpoint(candidateLine)

    def __toggleBreakpoint(self, line, temporary=False):
        """Toggles the line breakpoint"""
        fileName = self._parent.getFileName()
        model = self.__debugger.getBreakPointModel()
        for handle, bpoint in self.__breakpoints.items():
            if self.markerLine(handle) == line - 1:
                index = model.getBreakPointIndex(fileName, line)
                if not model.isBreakPointTemporaryByIndex(index):
                    model.deleteBreakPointByIndex(index)
                    self.__addBreakpoint(line, True)
                else:
                    model.deleteBreakPointByIndex(index)
                return
        self.__addBreakpoint(line, temporary)

    def __addBreakpoint(self, line, temporary):
        """Adds a new breakpoint"""
        # The prerequisites:
        # - it is saved buffer
        # - it is a python buffer
        # - it is a breakable line
        # are checked in the function
        if not self._parent.isLineBreakable(line, True, True):
            return

        bpoint = Breakpoint(self._parent.getFileName(),
                            line, "", temporary, True, 0)
        self.__debugger.getBreakPointModel().addBreakpoint(bpoint)

    def __deleteBreakPoints(self, parentIndex, start, end):
        """Deletes breakpoints"""
        bpointModel = self.__debugger.getBreakPointModel()
        for row in range(start, end + 1):
            index = bpointModel.index(row, 0, parentIndex)
            bpoint = bpointModel.getBreakPointByIndex(index)
            fileName = bpoint.getAbsoluteFileName()

            if fileName == self._parent.getFileName():
                self.clearBreakpoint(bpoint.getLineNumber())

    def clearBreakpoint(self, line):
        """Clears a breakpoint"""
        if self.__inLinesChanged:
            return

        for handle, bpoint in self.__breakpoints.items():
            if self.markerLine(handle) == line - 1:
                del self.__breakpoints[handle]
                self.markerDeleteHandle(handle)
                return
        # Ignore the request if not found

    def __breakPointDataAboutToBeChanged(self, startIndex, endIndex):
        """Handles the dataAboutToBeChanged signal of the breakpoint model"""
        self.__deleteBreakPoints(QModelIndex(),
                                 startIndex.row(), endIndex.row())

    def __changeBreakPoints(self, startIndex, endIndex):
        """Sets changed breakpoints"""
        self.__addBreakPoints(QModelIndex(),
                              startIndex.row(), endIndex.row())

    def __addBreakPoints(self, parentIndex, start, end):
        """Adds breakpoints"""
        bpointModel = self.__debugger.getBreakPointModel()
        for row in range(start, end + 1):
            index = bpointModel.index(row, 0, parentIndex)
            bpoint = bpointModel.getBreakPointByIndex(index)
            fileName = bpoint.getAbsoluteFileName()

            if fileName == self._parent.getFileName():
                self.newBreakpointWithProperties(bpoint)

    def newBreakpointWithProperties(self, bpoint):
        """Sets a new breakpoint and its properties"""
        if not bpoint.isEnabled():
            marker = self.__disbpointMarker
        elif bpoint.isTemporary():
            marker = self.__tempbpointMarker
        else:
            marker = self.__bpointMarker

        line = bpoint.getLineNumber()
        if self.markersAtLine(line - 1) & self.__bpointMarginMask == 0:
            handle = self.markerAdd(line - 1, marker)
            self.__breakpoints[handle] = bpoint

    def restoreBreakpoints(self):
        """Restores the breakpoints"""
        # self.markerDeleteAll(self.__bpointMarker)
        # self.markerDeleteAll(self.__tempbpointMarker)
        # self.markerDeleteAll(self.__disbpointMarker)
        self.__addBreakPoints(QModelIndex(), 0,
                              self.__debugger.getBreakPointModel().rowCount() - 1)

    def __onSceneModified(self, position, modificationType, text,
                          length, linesAdded, line, foldLevelNow,
                          foldLevelPrev, token, annotationLinesAdded):
        if not self.__breakpoints:
            return

        opLine, opIndex = self.lineIndexFromPosition(position)

        if linesAdded == 0:
            if self.isLineEmpty(opLine + 1):
                self.__deleteBreakPointsInLineRange(opLine + 1, 1)
            return

        # We are interested in inserted or deleted lines
        if linesAdded < 0:
            # Some lines were deleted
            linesDeleted = abs(linesAdded)
            if opIndex != 0:
                linesDeleted -= 1
                if self.isLineEmpty(opLine + 1):
                    self.__deleteBreakPointsInLineRange(opLine + 1, 1)
                if linesDeleted == 0:
                    self.__onLinesChanged(opLine + 1)
                    return
                opLine += 1

            # Some lines were fully deleted
            self.__deleteBreakPointsInLineRange(opLine + 1, linesDeleted)
            self.__onLinesChanged(opLine + 1)
        else:
            # Some lines were added
            self.__onLinesChanged(opLine + 1)

    def __deleteBreakPointsInLineRange(self, startFrom, count):
        """Deletes breakpoints which fall into the given lines range"""
        toBeDeleted = []
        limit = startFrom + count - 1
        for handle, bpoint in self.__breakpoints.items():
            bpointLine = bpoint.getLineNumber()
            if bpointLine >= startFrom and bpointLine <= limit:
                toBeDeleted.append(bpointLine)

        if toBeDeleted:
            model = self.__debugger.getBreakPointModel()
            fileName = self._parent.getFileName()
            for line in toBeDeleted:
                index = model.getBreakPointIndex(fileName, line)
                model.deleteBreakPointByIndex(index)

    def deleteAllBreakpoints(self):
        """Deletes all the breakpoints in the buffer"""
        self.__deleteBreakPointsInLineRange(1, self.lines())

    def validateBreakpoints(self):
        """Checks breakpoints and deletes those which are invalid"""
        if not self.__breakpoints:
            return

        fileName = self._parent.getFileName()
        breakableLines = getBreakpointLines(fileName, self.text,
                                            True, False)

        toBeDeleted = []
        for handle, bpoint in self.__breakpoints.items():
            bpointLine = bpoint.getLineNumber()
            if breakableLines is None or bpointLine not in breakableLines:
                toBeDeleted.append(bpointLine)

        if toBeDeleted:
            model = self.__debugger.getBreakPointModel()
            for line in toBeDeleted:
                if breakableLines is None:
                    logging.warning("Breakpoint at " + fileName + ":" +
                                    str(line) + " does not point to a "
                                    "breakable line (file is not compilable). "
                                    "The breakpoint is deleted.")
                else:
                    logging.warning("Breakpoint at " + fileName + ":" +
                                    str(line) + " does not point to a breakable "
                                    "line anymore. The breakpoint is deleted.")
                index = model.getBreakPointIndex(fileName, line)
                model.deleteBreakPointByIndex(index)

    def __onLinesChanged(self, startFrom):
        """Tracks breakpoints when some lines were inserted.
           startFrom is 1 based
        """
        if self.__breakpoints:
            bpointModel = self.__debugger.getBreakPointModel()
            bps = []    # list of breakpoints
            for handle, bpoint in self.__breakpoints.items():
                line = self.markerLine(handle) + 1
                if line < startFrom:
                    continue

                self.markerDeleteHandle(handle)
                bps.append((bpoint, line, handle))

            self.__inLinesChanged = True
            for bp, newLineNumber, oldHandle in bps:
                del self.__breakpoints[oldHandle]

                index = bpointModel.getBreakPointIndex(bp.getAbsoluteFileName(),
                                                       bp.getLineNumber())
                bpointModel.updateLineNumberByIndex(index, newLineNumber)
            self.__inLinesChanged = False

    def isPythonBuffer(self):
        """True if it is a python buffer"""
        return isPythonMime(self.mime)

    def setMarginsBackgroundColor(self, color):
        """Sets the margins background"""
        pass

    def setMarginsForegroundColor(self, color):
        """Sets the margins foreground"""
        pass
