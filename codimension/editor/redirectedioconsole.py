# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Redirected IO console implementation"""

import logging
from qutepart import Qutepart
from ui.qt import (Qt, QEvent, pyqtSignal, QFontMetrics, QMenu,
                   QApplication, QTextOption)
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from .qpartwrap import QutepartWrapper
from .redirectedmsg import IOConsoleMessages, IOConsoleMsg
from .redirectediomargin import CDMRedirectedIOMargin


CTRL_SHIFT = int(Qt.ShiftModifier | Qt.ControlModifier)
SHIFT = int(Qt.ShiftModifier)
CTRL = int(Qt.ControlModifier)
CTRL_KEYPAD = int(Qt.KeypadModifier | Qt.ControlModifier)
NO_MODIFIER = int(Qt.NoModifier)


class RedirectedIOConsole(QutepartWrapper):

    """Widget which implements the redirected IO console"""

    sigUserInput = pyqtSignal(str)

    MODE_OUTPUT = 0
    MODE_INPUT = 1

    def __init__(self, parent):
        QutepartWrapper.__init__(self, parent)

        self.setAttribute(Qt.WA_KeyCompression)

        self.mode = self.MODE_OUTPUT
        self.lastOutputPos = None
        self.inputEcho = True
        self.inputBuffer = ""
        self.__messages = IOConsoleMessages()

        self.__initGeneralSettings()
        self.__initMargins()
        self._initContextMenu()
        self.onTextZoomChanged()

        self.__hotKeys = {}
        self.__initHotKeys()
        self.installEventFilter(self)

        self.cursorPositionChanged.connect(self.setCursorStyle)

    def __initHotKeys(self):
        """Initializes a map for the hot keys event filter"""
        self.autoIndentLineAction.setShortcut('Ctrl+Shift+I')
        self.invokeCompletionAction.setEnabled(False)
        self.__hotKeys = {
            CTRL_SHIFT: {Qt.Key_C: self.onCtrlShiftC},
            SHIFT: {Qt.Key_End: self.onShiftEnd,
                    Qt.Key_Home: self.onShiftHome,
                    Qt.Key_Insert: self.onPasteText,
                    Qt.Key_Delete: self.onShiftDel},
            CTRL: {Qt.Key_V: self.onPasteText,
                   Qt.Key_X: self.onShiftDel,
                   Qt.Key_C: self.onCtrlC,
                   Qt.Key_Insert: self.onCtrlC,
                   Qt.Key_Minus: Settings().onTextZoomOut,
                   Qt.Key_Equal: Settings().onTextZoomIn,
                   Qt.Key_0: Settings().onTextZoomReset,
                   Qt.Key_Home: self.onFirstChar,
                   Qt.Key_End: self.onLastChar},
            CTRL_KEYPAD: {Qt.Key_Minus: Settings().onTextZoomOut,
                          Qt.Key_Plus: Settings().onTextZoomIn,
                          Qt.Key_0: Settings().onTextZoomReset},
            NO_MODIFIER: {Qt.Key_Home: self.onHome,
                          Qt.Key_End: self.moveToLineEnd}}

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

                if modifiers == NO_MODIFIER:
                    if key in [Qt.Key_Delete, Qt.Key_Backspace]:
                        if not self.__isCutDelAvailable():
                            return True
            except Exception as exc:
                logging.warning(str(exc))
        return False

    def keyPressEvent(self, event):
        """Triggered when a key is pressed"""
        key = event.key()
        if key == Qt.Key_Escape:
            self.clearSearchIndicators()
            return

        if self.mode == self.MODE_OUTPUT:
            if key in [Qt.Key_Left, Qt.Key_Up, Qt.Key_Right, Qt.Key_Down,
                       Qt.Key_PageUp, Qt.Key_PageDown]:
                QutepartWrapper.keyPressEvent(self, event)
            return

        # It is an input mode
        txt = event.text()
        if len(txt) and txt >= ' ':
            # Printable character
            if self.absCursorPosition < self.lastOutputPos:
                # Out of the input zone
                return

            if self.inputEcho:
                QutepartWrapper.keyPressEvent(self, event)
            else:
                self.inputBuffer += txt
            return

        # Non-printable character or some other key
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            userInput = self.__getUserInput()
            self.switchMode(self.MODE_OUTPUT)
            timestampLine, _ = self.getEndPosition()
            self.append('\n')
            self.clearUndoRedoHistory()
            line, pos = self.getEndPosition()
            self.cursorPosition = line, pos
            self.ensureLineOnScreen(line)
            msg = IOConsoleMsg(IOConsoleMsg.STDIN_MESSAGE,
                               userInput + '\n')
            self.__messages.append(msg)

            # margin data
            timestamp = msg.getTimestamp()
            margin = self.getMargin('cdm_redirected_io_margin')
            margin.addData(timestampLine + 1, timestamp,
                           timestamp, IOConsoleMsg.STDIN_MESSAGE)

            self.sigUserInput.emit(userInput)
            return

        if key == Qt.Key_Backspace:
            if self.absCursorPosition == self.lastOutputPos:
                if not self.inputEcho:
                    self.inputBuffer = self.inputBuffer[:-1]
                return

        QutepartWrapper.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Disable search highlight on double click"""
        Qutepart.mouseDoubleClickEvent(self, event)

    def onPasteText(self):
        """Triggered when insert is requested"""
        if self.mode == self.MODE_OUTPUT:
            return
        if self.absCursorPosition < self.lastOutputPos:
            return

        # Check what is in the buffer
        text = QApplication.clipboard().text()
        if '\n' in text or '\r' in text:
            return

        if not self.inputEcho:
            self.inputBuffer += text
            return

        self.paste()

    def __getUserInput(self):
        """Provides the collected user input"""
        if self.mode != self.MODE_INPUT:
            return ''
        if self.inputEcho:
            _, endPos = self.getEndPosition()
            _, beginPos = self.mapToLineCol(self.lastOutputPos)
            return self.lines[-1][beginPos:endPos]
        value = self.inputBuffer
        self.inputBuffer = ""
        return value

    def __initGeneralSettings(self):
        """Sets some generic look and feel"""
        skin = GlobalData().skin

        self.updateSettings()

        self.setPaper(skin['ioconsolePaper'])
        self.setColor(skin['ioconsoleColor'])

        self.currentLineColor = None
        self.lineLengthEdge = None
        self.setCursorStyle()

    def updateSettings(self):
        """Updates the IO console settings"""
        if Settings()['ioconsolelinewrap']:
            self.setWordWrapMode(QTextOption.WrapAnywhere)
        else:
            self.setWordWrapMode(QTextOption.NoWrap)

        self.drawAnyWhitespace = Settings()['ioconsoleshowspaces']
        self.drawIncorrectIndentation = Settings()['ioconsoleshowspaces']

    def setCursorStyle(self):
        """Sets the cursor style depending on the mode and the cursor pos"""
        if self.mode == self.MODE_OUTPUT:
            if self.cursorWidth() != 1:
                self.setCursorWidth(1)
        else:
            if self.absCursorPosition >= self.lastOutputPos:
                if self.cursorWidth() == 1:
                    fontMetrics = QFontMetrics(self.font(), self)
                    self.setCursorWidth(fontMetrics.width('W'))
                    self.update()
            else:
                if self.cursorWidth() != 1:
                    self.setCursorWidth(1)
                    self.update()

    def switchMode(self, newMode):
        """Switches between input/output mode"""
        self.mode = newMode
        if self.mode == self.MODE_OUTPUT:
            self.lastOutputPos = None
            self.inputEcho = True
            self.inputBuffer = ""
        else:
            line, pos = self.getEndPosition()
            self.cursorPosition = line, pos
            self.lastOutputPos = self.absCursorPosition
            self.ensureLineOnScreen(line)
        self.setCursorStyle()

    def __initMargins(self):
        """Initializes the IO console margins"""
        # The supported margins: timestamp
        self.addMargin(CDMRedirectedIOMargin(self))

    def _initContextMenu(self):
        """Called to initialize a context menu"""
        self._menu = QMenu(self)
        self.__menuUndo = self._menu.addAction(
            getIcon('undo.png'), '&Undo', self.onUndo, "Ctrl+Z")
        self.__menuRedo = self._menu.addAction(
            getIcon('redo.png'), '&Redo', self.onRedo, "Ctrl+Y")
        self._menu.addSeparator()
        self.__menuCut = self._menu.addAction(
            getIcon('cutmenu.png'), 'Cu&t', self.onShiftDel, "Ctrl+X")
        self.__menuCopy = self._menu.addAction(
            getIcon('copymenu.png'), '&Copy', self.onCtrlC, "Ctrl+C")
        self.__menucopyTimestamp = self._menu.addAction(
            getIcon('copymenu.png'), '&Copy all with timestamps',
            self.onCtrlShiftC, "Ctrl+Shift+C")
        self.__menuPaste = self._menu.addAction(
            getIcon('pastemenu.png'), '&Paste', self.onPasteText, "Ctrl+V")
        self.__menuSelectAll = self._menu.addAction(
            getIcon('selectallmenu.png'), 'Select &all',
            self.selectAll, "Ctrl+A")
        self._menu.addSeparator()
        self.__menuOpenAsFile = self._menu.addAction(
            getIcon('filemenu.png'), 'O&pen as file', self.openAsFile)
        self.__menuDownloadAndShow = self._menu.addAction(
            getIcon('filemenu.png'), 'Do&wnload and show',
            self.downloadAndShow)
        self.__menuOpenInBrowser = self._menu.addAction(
            getIcon('homepagemenu.png'), 'Open in browser', self.openInBrowser)
        self._menu.addSeparator()

        self._menu.aboutToShow.connect(self._contextMenuAboutToShow)
        self._menu.aboutToHide.connect(self._contextMenuAboutToHide)

    def contextMenuEvent(self, event):
        """Called just before showing a context menu"""
        event.accept()
        self._menu.popup(event.globalPos())

    def _contextMenuAboutToShow(self):
        """IO Console context menu is about to show"""
        self.__menuUndo.setEnabled(self.document().isUndoAvailable())
        self.__menuRedo.setEnabled(self.document().isRedoAvailable())

        pasteText = QApplication.clipboard().text()
        pasteEnable = pasteText != "" and \
                      '\n' not in pasteText and \
                      '\r' not in pasteText and \
                      self.mode != self.MODE_OUTPUT
        if pasteEnable:
            if self.absCursorPosition < self.lastOutputPos:
                pasteEnable = False

        # Need to make decision about menu items for modifying the input
        self.__menuCut.setEnabled(self.__isCutDelAvailable())
        self.__menuCopy.setEnabled(self.__messages.size > 0)
        self.__menucopyTimestamp.setEnabled(self.__messages.size > 0)
        self.__menuPaste.setEnabled(pasteEnable)
        self.__menuSelectAll.setEnabled(self.__messages.size > 0)

        self.__menuOpenAsFile.setEnabled(self.openAsFileAvailable())
        self.__menuDownloadAndShow.setEnabled(
            self.downloadAndShowAvailable())
        self.__menuOpenInBrowser.setEnabled(
            self.downloadAndShowAvailable())

    def _contextMenuAboutToHide(self):
        """IO console context menu is about to hide"""
        self.__menuUndo.setEnabled(True)
        self.__menuRedo.setEnabled(True)
        self.__menuCut.setEnabled(True)
        self.__menuCopy.setEnabled(True)
        self.__menucopyTimestamp.setEnabled(True)
        self.__menuPaste.setEnabled(True)
        self.__menuSelectAll.setEnabled(True)
        self.__menuOpenAsFile.setEnabled(True)
        self.__menuDownloadAndShow.setEnabled(True)
        self.__menuOpenInBrowser.setEnabled(True)

    def __isCutDelAvailable(self):
        """Returns True if cutting or deletion is possible"""
        if self.mode == self.MODE_OUTPUT:
            return False
        if self.selectedText:
            startPosition, cursorPosition = self.absSelectedPosition
            minPos = min(startPosition, cursorPosition)
            return minPos >= self.lastOutputPos
        return self.absCursorPosition > self.lastOutputPos

    def onShiftDel(self):
        """Deletes the selected text"""
        if self.selectedText:
            if self.__isCutDelAvailable():
                self.cut()
            return True
        return True

    def onUndo(self):
        """undo implementation"""
        if self.document().isUndoAvailable():
            self.undo()

    def onRedo(self):
        """redo implementation"""
        if self.document().isRedoAvailable():
            self.redo()

    def onCtrlShiftC(self):
        """Copy all with timestamps"""
        QApplication.clipboard().setText(
            self.__messages.renderWithTimestamps())

    def appendIDEMessage(self, text):
        """Appends an IDE message"""
        msg = IOConsoleMsg(IOConsoleMsg.IDE_MESSAGE, text)
        self.__appendMessage(msg)
        return msg

    def appendStdoutMessage(self, text):
        """Appends an stdout message"""
        msg = IOConsoleMsg(IOConsoleMsg.STDOUT_MESSAGE, text)
        self.__appendMessage(msg)
        return msg

    def appendStderrMessage(self, text):
        """Appends an stderr message"""
        msg = IOConsoleMsg(IOConsoleMsg.STDERR_MESSAGE, text)
        self.__appendMessage(msg)
        return msg

    def __appendMessage(self, message):
        """Appends a new message to the console"""
        if not self.__messages.append(message):
            # There was no trimming of the message list
            self.__renderMessage(message)
        else:
            # Some messages were stripped
            self.renderContent()

    def renderContent(self):
        """Regenerates the viewer content"""
        self.clear()
        self.getMargin('cdm_redirected_io_margin').clear()
        for msg in self.__messages.msgs:
            self.__renderMessage(msg)

    def __renderMessage(self, msg):
        """Adds a single message"""
        margin = self.getMargin('cdm_redirected_io_margin')
        timestamp = msg.getTimestamp()
        if msg.msgType == IOConsoleMsg.IDE_MESSAGE:
            line, pos = self.getEndPosition()

            txt = msg.msgText
            startMarkLine = line
            if pos != 0:
                txt = '\n' + txt
                startMarkLine += 1

            self.append(txt)

            line, _ = self.getEndPosition()
            for lineNo in range(startMarkLine, line + 1):
                margin.addData(lineNo + 1, timestamp,
                               timestamp, IOConsoleMsg.IDE_MESSAGE)
        else:
            line, pos = self.getEndPosition()
            txt = msg.msgText

            startTimestampLine = line
            if pos != 0:
                lastMsgType = margin.getLineMessageType(line + 1)
                if lastMsgType == IOConsoleMsg.IDE_MESSAGE:
                    txt = '\n' + txt
                    startTimestampLine = line + 1

            self.append(txt)
            endTimestampLine, pos = self.getEndPosition()
            if pos == 0:
                endTimestampLine -= 1

            for lineNo in range(startTimestampLine, endTimestampLine + 1):
                margin.addData(lineNo + 1, timestamp, timestamp,
                               msg.msgType)

        self.clearUndoRedoHistory()
        if Settings()['ioconsoleautoscroll']:
            line, pos = self.getEndPosition()
            self.gotoLine(line + 1, pos + 1)

    def clearData(self):
        """Clears the collected data"""
        self.__messages.clear()
        self.getMargin('cdm_redirected_io_margin').clear()

    def clearAll(self):
        """Clears both data and visible content"""
        self.clearData()
        self.clear()
        self.clearUndoRedoHistory()
