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
from ui.qt import (Qt, QTimer, pyqtSignal, QRect, QEvent,
                   QCursor, QApplication, QTextOption, QAction)
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
                                      getEditorTags,
                                      getCallPosition, getCommaCount)
from autocomplete.completelists import (getCompletionList, getCalltipAndDoc,
                                        getDefinitions, getOccurrences)
from cdmbriefparser import getBriefModuleInfoFromMemory
from .qpartwrap import QutepartWrapper
from .editorcontextmenus import EditorContextMenuMixin
from .linenomargin import CDMLineNumberMargin
from .flakesmargin import CDMFlakesMargin
from .bpmargin import CDMBreakpointMargin


CTRL_SHIFT = int(Qt.ShiftModifier | Qt.ControlModifier)
SHIFT = int(Qt.ShiftModifier)
CTRL = int(Qt.ControlModifier)
ALT = int(Qt.AltModifier)
CTRL_KEYPAD = int(Qt.KeypadModifier | Qt.ControlModifier)
NO_MODIFIER = int(Qt.NoModifier)


class TextEditor(QutepartWrapper, EditorContextMenuMixin):

    """Text editor implementation"""

    sigEscapePressed = pyqtSignal()
    sigCFlowSyncRequested = pyqtSignal(int, int, int)

    def __init__(self, parent, debugger):
        self._parent = parent
        QutepartWrapper.__init__(self, parent)
        EditorContextMenuMixin.__init__(self)

        self.setAttribute(Qt.WA_KeyCompression)

        skin = GlobalData().skin
        self.setPaper(skin['nolexerPaper'])
        self.setColor(skin['nolexerColor'])

        self.onTextZoomChanged()
        self.__initMargins(debugger)

        # self.SCN_DOUBLECLICK.connect(self.__onDoubleClick)
        self.cursorPositionChanged.connect(self._onCursorPositionChanged)

        self.__skipChangeCursor = False

        self.__openedLine = None

        self.setFocusPolicy(Qt.StrongFocus)
        self.indentWidth = 4

        self.updateSettings()

        # Completion support
        self.__completionPrefix = ''
        self.__completionLine = -1
        self.__completionPos = -1
        self.__completer = CodeCompleter(self)
        self.__inCompletion = False
        self.__completer.activated.connect(self.insertCompletion)
        self.__lastTabPosition = None

        # Calltip support
        self.__calltip = None
        self.__callPosition = None
        self.__calltipTimer = QTimer(self)
        self.__calltipTimer.setSingleShot(True)
        self.__calltipTimer.timeout.connect(self.__onCalltipTimer)

        self.__initHotKeys()
        self.installEventFilter(self)

    def dedentLine(self):
        """Dedent the current line or selection"""
        self.decreaseIndentAction.activate(QAction.Trigger)

    def __initHotKeys(self):
        """Initializes a map for the hot keys event filter"""
        self.autoIndentLineAction.setShortcut('Ctrl+Shift+I')
        self.invokeCompletionAction.setEnabled(False)
        self.__hotKeys = {
            CTRL_SHIFT: {Qt.Key_F1: self.onCallHelp,
                         Qt.Key_T: self.onJumpToTop,
                         Qt.Key_M: self.onJumpToMiddle,
                         Qt.Key_B: self.onJumpToBottom},
            SHIFT: {Qt.Key_Delete: self.onShiftDel,
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
                   Qt.Key_Minus: Settings().onTextZoomOut,
                   Qt.Key_Equal: Settings().onTextZoomIn,
                   Qt.Key_0: Settings().onTextZoomReset,
                   Qt.Key_Home: self.onFirstChar,
                   Qt.Key_End: self.onLastChar,
                   Qt.Key_B: self.highlightInOutline,
                   Qt.Key_QuoteLeft: self.highlightInCFlow},
            ALT: {Qt.Key_U: self.onScopeBegin},
            CTRL_KEYPAD: {Qt.Key_Minus: Settings().onTextZoomOut,
                          Qt.Key_Plus: Settings().onTextZoomIn,
                          Qt.Key_0: Settings().onTextZoomReset},
            NO_MODIFIER: {Qt.Key_Home: self.onHome,
                          Qt.Key_End: self.moveToLineEnd,
                          Qt.Key_F12: self.makeLineFirst}}

        # Not all the derived classes need certain tool functionality
        if hasattr(self._parent, "getType" ):
            widgetType = self._parent.getType()
            if widgetType in [MainWindowTabWidgetBase.PlainTextEditor]:
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
                    Settings().onTextZoomIn()
                else:
                    Settings().onTextZoomOut()
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

    def __initMargins(self, debugger):
        """Initializes the editor margins"""
        self.addMargin(CDMLineNumberMargin(self))
        self.addMargin(CDMFlakesMargin(self))
        self.getMargin('cdm_flakes_margin').setVisible(False)

        if debugger:
            self.addMargin(CDMBreakpointMargin(self, debugger))
            self.getMargin('cdm_bpoint_margin').setVisible(False)

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

            # Copied from enki (enki/core/document.py: _readFile()):
            # Strip last EOL. Qutepart adds it when saving file
            if content.endswith('\r\n'):
                content = content[:-2]
            elif content.endswith('\n') or content.endswith('\r'):
                content = content[:-1]

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
                logging.error('Could not detect write encoding for ' +
                              fileName)
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
                if self.__completionPrefix == '':
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
            currentPosition = self.absCursorPosition
            if pos != 0:
                char = self.lines[line][pos - 1]
                if char != ' ' and currentPosition != self.__lastTabPosition:
                    self.onAutoComplete()
                    event.accept()
                else:
                    QutepartWrapper.keyPressEvent(self, event)
                    self.__lastTabPosition = currentPosition
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

    def _onCursorPositionChanged(self):
        """Triggered when the cursor changed the position"""
        self.__lastTabPosition = None
        line, _ = self.cursorPosition

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
        self.__lastTabPosition = None
        if self.isReadOnly():
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.__inCompletion = True
        self.__completionPrefix = self.getWordBeforeCursor()
        words = getCompletionList(self, self._parent.getFileName())
        QApplication.restoreOverrideCursor()

        if len(words) == 0:
            self.setFocus()
            self.__inCompletion = False
            return

        self.__completer.setWordsList(words, self.font())
        self.__completer.setPrefix(self.__completionPrefix)

        count = self.__completer.completionCount()
        if count == 0:
            self.setFocus()
            self.__inCompletion = False
            return

        # Make sure the line is visible
        line, _ = self.cursorPosition
        self.ensureLineOnScreen(line + 1)

        # Remove the selection as it could be interpreted not as expected
        if self.selectedText:
            self.clearSelection()

        if count == 1:
            self.insertCompletion(self.__completer.currentCompletion())
        else:
            cRectangle = self.cursorRect()
            cRectangle.setLeft(cRectangle.left() + self.viewport().x())
            cRectangle.setTop(cRectangle.top() + self.viewport().y() + 2)
            self.__completer.complete(cRectangle)
        self.__inCompletion = False

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
        definitions = getDefinitions(self, self._parent.getFileName())
        QApplication.restoreOverrideCursor()

        if definitions:
            if len(definitions) == 1:
                GlobalData().mainWindow.openFile(
                    definitions[0][0], definitions[0][1],
                    definitions[0][2] + 1)
            else:
                print("More than one definition identified")
        else:
            GlobalData().mainWindow.showStatusBarMessage(
                "Definition is not found")

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
            currentWord = self.getCurrentWord()
            line, pos = self.cursorPosition
            prefixLength = len(self.__completionPrefix)
            if text != currentWord:
                with self:
                    lineContent = self.lines[line]
                    leftPart = lineContent[0:pos - prefixLength]
                    rightPart = lineContent[pos + len(currentWord) - prefixLength:]
                    self.lines[line] = leftPart + text + rightPart
            self.cursorPosition = line, pos + len(text) - prefixLength

            self.__completionPrefix = ''
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
            self.sigCFlowSyncRequested.emit(absPos, line + 1, pos + 1)

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

    def setDebugMode(self, debugOn, disableEditing):
        """Called to switch between debug/development"""
        skin = GlobalData().skin
        if debugOn:
            if disableEditing:
                self.setLinenoMarginBackgroundColor(skin['marginPaperDebug'])
                self.setLinenoMarginForegroundColor(skin['marginColorDebug'])
                self.setReadOnly(True)
        else:
            self.setLinenoMarginBackgroundColor(skin['marginPaper'])
            self.setLinenoMarginForegroundColor(skin['marginColor'])
            self.setReadOnly(False)

        bpointMargin = self.getMargin('cdm_bpoint_margin')
        if bpointMargin:
            bpointMargin.setDebugMode(debugOn, disableEditing)

    def restoreBreakpoints(self):
        """Restores the breakpoints"""
        bpointMargin = self.getMargin('cdm_bpoint_margin')
        if bpointMargin:
            bpointMargin.restoreBreakpoints()

    def isLineBreakable(self):
        """True if a line is breakable"""
        bpointMargin = self.getMargin('cdm_bpoint_margin')
        if bpointMargin:
            return bpointMargin.isLineBreakable()
        return False

    def validateBreakpoints(self):
        """Checks breakpoints and deletes those which are invalid"""
        bpointMargin = self.getMargin('cdm_bpoint_margin')
        if bpointMargin:
            bpointMargin.validateBreakpoints()

    def isPythonBuffer(self):
        """True if it is a python buffer"""
        return isPythonMime(self.mime)

    def setLinenoMarginBackgroundColor(self, color):
        """Sets the margins background"""
        linenoMargin = self.getMargin('cdm_line_number_margin')
        if linenoMargin:
            linenoMargin.setBackgroundColor(color)

    def setLinenoMarginForegroundColor(self, color):
        """Sets the lineno margin foreground color"""
        linenoMargin = self.getMargin('cdm_line_number_margin')
        if linenoMargin:
            linenoMargin.setForegroundColor(color)
