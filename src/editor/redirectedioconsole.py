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
from ui.qt import (Qt, QSize, QEvent, pyqtSignal, QToolBar, QFont,
                   QFontMetrics, QHBoxLayout, QWidget, QAction, QSizePolicy,
                   QMenu, QToolButton, QApplication, QTextOption)
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
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

    def __initHotKeys(self):
        """Initializes a map for the hot keys event filter"""
        self.autoIndentLineAction.setShortcut('Ctrl+Shift+I')
        self.invokeCompletionAction.setEnabled(False)
        self.__hotKeys = {
            CTRL_SHIFT: {Qt.Key_C: self.onCtrlShiftC},
            SHIFT: {Qt.Key_End: self.onShiftEnd,
                    Qt.Key_Home: self.onShiftHome,
                    Qt.Key_Insert: self.insertText,
                    Qt.Key_Delete: self.onShiftDel},
            CTRL: {Qt.Key_V: self.insertText,
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
            QutepartWrapper.keyPressEvent(self, event)
            return

        # It is an input mode
        txt = event.text()
        if len(txt) and txt >= ' ':
            # Printable character
            if self.currentPosition() < self.lastOutputPos:
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
            endPos = self.currentPosition()
            startPos = self.positionBefore(endPos)
            msg = IOConsoleMsg(IOConsoleMsg.STDIN_MESSAGE,
                               userInput + "\n")
            self.__messages.append(msg)
            self.__addTooltip(timestampLine, msg.getTimestamp())
            self.sigUserInput.emit(userInput)
            return
        if key == Qt.Key_Backspace:
            if self.currentPosition() == self.lastOutputPos:
                if self.inputEcho == False:
                    self.inputBuffer = self.inputBuffer[:-1]
                return

        QutepartWrapper.keyPressEvent(self, event)

    def insertText(self):
        """Triggered when insert is requested"""
        if self.isReadOnly():
            return True

        # Check what is in the buffer
        text = QApplication.clipboard().text()
        if '\n' in text or '\r' in text:
            return True

        if not self.inputEcho:
            self.inputBuffer += text
            return True

        self.paste(self)
        return True

    def setReadOnly(self, mode):
        """Overridden version"""
        QutepartWrapper.setReadOnly(self, mode)
        if mode:
            # Otherwise the cursor is suppressed in the RO mode
            self.setTextInteractionFlags(self.textInteractionFlags() |
                                         Qt.TextSelectableByKeyboard)

    def __getUserInput(self):
        """Provides the collected user input"""
        if self.mode != self.MODE_INPUT:
            return ""
        if self.inputEcho:
            line, pos = self.getEndPosition()
            _, startPos = self.lineIndexFromPosition(self.lastOutputPos)
            return self.getTextAtPos(line, startPos, pos - startPos)
        value = self.inputBuffer
        self.inputBuffer = ""
        return value

    def __initGeneralSettings(self):
        """Sets some generic look and feel"""
        skin = GlobalData().skin

        self.updateSettings()

        self.setPaper(skin['ioconsolePaper'])
        self.setColor(skin['ioconsoleColor'])

        self.setReadOnly(True)

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

    def _onCursorPositionChanged(self, line, pos):
        """Called when the cursor changed position"""
        self.setCursorStyle()

    def setCursorStyle(self):
        """Sets the cursor style depending on the mode and the cursor pos"""
        if self.mode == self.MODE_OUTPUT:
            self.setCursorWidth(1)
            self.setReadOnly(True)
        else:
            if self.absCursorPosition >= self.lastOutputPos:
                fontMetrics = QFontMetrics(self.font(), self)
                self.setCursorWidth(fontMetrics.width('W'))
                self.setReadOnly(False)
            else:
                self.setCursorWidth(1)
                self.setReadOnly(True)

    def switchMode(self, newMode):
        """Switches between input/output mode"""
        self.mode = newMode
        if self.mode == self.MODE_OUTPUT:
            self.lastOutputPos = None
            self.setReadOnly(True)
            self.inputEcho = True
            self.inputBuffer = ""
        else:
            line, pos = self.getEndPosition()
            self.cursorPosition = line, pos
            self.lastOutputPos = self.absCursorPosition
            self.setReadOnly(False)
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
            getIcon('pastemenu.png'), '&Paste', self.insertText, "Ctrl+V")
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

    def setTimestampMarginWidth(self):
        """Sets the timestamp margin width"""
        settings = Settings()
        if settings['ioconsoleshowmargin']:
            skin = GlobalData().skin
            font = QFont(skin['lineNumFont'])
            font.setPointSize(font.pointSize() + settings['zoom'])
            # The second parameter of the QFontMetrics is essential!
            # If it is not there then the width is not calculated properly.
            fontMetrics = QFontMetrics(font, self)
            # W is for extra space at the right of the timestamp
            width = fontMetrics.width('88:88:88.888W')
            self.setMarginWidth(self.TIMESTAMP_MARGIN, width)
        else:
            self.setMarginWidth(self.TIMESTAMP_MARGIN, 0)

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
                      not self.isReadOnly()

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
        if self.isReadOnly():
            return False
        minPos = self.getSelectionStart()
        if minPos < self.lastOutputPos:
            return False
        return True

    def onShiftDel(self):
        """Deletes the selected text"""
        if self.hasSelectedText():
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

    def appendStdoutMessage(self, text):
        """Appends an stdout message"""
        msg = IOConsoleMsg(IOConsoleMsg.STDOUT_MESSAGE, text)
        self.__appendMessage(msg)

    def appendStderrMessage(self, text):
        """Appends an stderr message"""
        msg = IOConsoleMsg(IOConsoleMsg.STDERR_MESSAGE, text)
        self.__appendMessage(msg)

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
        timestamp = msg.getTimestamp()
        if msg.msgType == IOConsoleMsg.IDE_MESSAGE:
            # Check the text. Append \n if needed. Append the message
            line, pos = self.getEndPosition()

            startMarkLine = line
            if pos != 0:
                self.append("\n")
                startMarkLine += 1

            self.append(msg.msgText)
            if not msg.msgText.endswith("\n"):
                self.append("\n")

            margin = self.getMargin('cdm_redirected_io_margin')
            line, pos = self.getEndPosition()
            for lineNo in range(startMarkLine, line):
                margin.addData(lineNo + 1, timestamp,
                               timestamp, IOConsoleMsg.IDE_MESSAGE)
        else:
            line, pos = self.getEndPosition()
            if pos != 0:
                self.__addTooltip(line, timestamp)
                startTimestampLine = line + 1
            else:
                startTimestampLine = line
            self.append(msg.msgText)
            line, pos = self.getEndPosition()
            if pos != 0:
                endTimestampLine = line
            else:
                endTimestampLine = line - 1
            for lineNo in range(startTimestampLine, endTimestampLine + 1):
                self.__addTooltip(lineNo, timestamp)

            if msg.msgType == IOConsoleMsg.STDERR_MESSAGE:
                # Highlight as stderr
                styleNo = self.stderrStyle
            elif msg.msgType == IOConsoleMsg.STDOUT_MESSAGE:
                # Highlight as stdout
                styleNo = self.stdoutStyle
            else:
                styleNo = self.stdinStyle

            line, pos = self.getEndPosition()
            endPos = self.positionFromLineIndex(line, pos)

            line, pos = self.getEndPosition()
            endPos = self.positionFromLineIndex(line, pos)

        self.clearUndoRedoHistory()
        if Settings()['ioconsoleautoscroll']:
            line, pos = self.getEndPosition()
            self.gotoLine(line + 1, pos + 1)

    def __addTooltip(self, lineNo, timestamp):
        """Adds a tooltip into the dictionary"""
        if lineNo in self.__marginTooltip:
            self.__marginTooltip[lineNo].append(timestamp)
        else:
            self.__marginTooltip[lineNo] = [timestamp]
            self.setMarginText(lineNo, timestamp, self.marginStyle)

    def clearData(self):
        """Clears the collected data"""
        self.__messages.clear()
        self.getMargin('cdm_redirected_io_margin').clear()

    def clearAll(self):
        """Clears both data and visible content"""
        self.clearData()
        self.clear()
        self.clearUndoRedoHistory()


class IOConsoleTabWidget(QWidget, MainWindowTabWidgetBase):

    """IO console tab widget"""

    sigUserInput = pyqtSignal(str)
    sigSettingsUpdated = pyqtSignal()

    def __init__(self, parent):
        MainWindowTabWidgetBase.__init__(self)
        QWidget.__init__(self, parent)

        self.__viewer = RedirectedIOConsole(self)
        self.__viewer.sigUserInput.connect(self.__onUserInput)

        self.__createLayout()

    def __onUserInput(self, userInput):
        """The user finished input in the redirected IO console"""
        self.sigUserInput.emit(userInput)
        self.__clearButton.setEnabled(True)

    def __createLayout(self):
        """Creates the toolbar and layout"""
        # self.__sendUpButton = QAction(getIcon('sendioup.png'),
        #                               'Send to Main Editing Area', self)
        # self.__sendUpButton.triggered.connect(self.__sendUp)

        self.__settingsMenu = QMenu(self)
        self.__settingsMenu.aboutToShow.connect(self.__settingsAboutToShow)
        self.__wrapLongLinesAct = self.__settingsMenu.addAction(
            "Wrap long lines")
        self.__wrapLongLinesAct.setCheckable(True)
        self.__wrapLongLinesAct.triggered.connect(self.__onWrapLongLines)
        self.__showWhitespacesAct = self.__settingsMenu.addAction(
            "Show whitespaces")
        self.__showWhitespacesAct.setCheckable(True)
        self.__showWhitespacesAct.triggered.connect(self.__onShowWhitespaces)
        self.__autoscrollAct = self.__settingsMenu.addAction("Autoscroll")
        self.__autoscrollAct.setCheckable(True)
        self.__autoscrollAct.triggered.connect(self.__onAutoscroll)
        self.__showMarginAct = self.__settingsMenu.addAction(
            "Show timestamp margin")
        self.__showMarginAct.setCheckable(True)
        self.__showMarginAct.triggered.connect(self.__onShowMargin)

        self.__settingsButton = QToolButton(self)
        self.__settingsButton.setIcon(getIcon('iosettings.png'))
        self.__settingsButton.setToolTip('View settings')
        self.__settingsButton.setPopupMode(QToolButton.InstantPopup)
        self.__settingsButton.setMenu(self.__settingsMenu)
        self.__settingsButton.setFocusPolicy(Qt.NoFocus)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.__clearButton = QAction(getIcon('trash.png'), 'Clear', self)
        self.__clearButton.triggered.connect(self.clear)

        # The toolbar
        toolbar = QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setMovable(False)
        toolbar.setAllowedAreas(Qt.RightToolBarArea)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedWidth(28)
        toolbar.setContentsMargins(0, 0, 0, 0)

        # toolbar.addAction(self.__sendUpButton)
        toolbar.addWidget(self.__settingsButton)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.__clearButton)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(toolbar)
        hLayout.addWidget(self.__viewer)

        self.setLayout(hLayout)

    def setFocus(self):
        """Overridden setFocus"""
        self.__viewer.setFocus()

    def onOpenImport(self):
        """Triggered when Ctrl+I is received"""
        return True

    def __sendUp(self):
        """Triggered when requested to move the console up"""
        return

    def __settingsAboutToShow(self):
        " Settings menu is about to show "
        self.__wrapLongLinesAct.setChecked(Settings()['ioconsolelinewrap'])
        self.__showWhitespacesAct.setChecked(Settings()['ioconsoleshowspaces'])
        self.__autoscrollAct.setChecked(Settings()['ioconsoleautoscroll'])
        self.__showMarginAct.setChecked(Settings()['ioconsoleshowmargin'])

    def __onWrapLongLines(self):
        """Triggered when long lines setting is changed"""
        Settings()['ioconsolelinewrap'] = not Settings()['ioconsolelinewrap']
        self.sigSettingsUpdated.emit()

    def __onShowWhitespaces(self):
        """Triggered when show whitespaces is changed"""
        Settings()['ioconsoleshowspaces'] = \
            not Settings()['ioconsoleshowspaces']
        self.sigSettingsUpdated.emit()

    def __onAutoscroll(self):
        """Triggered when autoscroll is changed"""
        Settings()['ioconsoleautoscroll'] = \
            not Settings()['ioconsoleautoscroll']

    def __onShowMargin(self):
        """Triggered when show margin is changed"""
        Settings()['ioconsoleshowmargin'] = \
            not Settings()['ioconsoleshowmargin']
        self.sigSettingsUpdated.emit()

    def clear(self):
        """Triggered when requested to clear the console"""
        self.__viewer.clearAll()

    def consoleSettingsUpdated(self):
        """Triggered when one of the consoles updated a common setting"""
        self.__viewer.updateSettings()
        self.__viewer.setTimestampMarginWidth()

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)

    def onPylint(self):
        return True

    def onPymetrics(self):
        return True

    def onRunScript(self, action=False):
        return True

    def onRunScriptSettings(self):
        return True

    def onProfileScript(self, action=False):
        return True

    def onProfileScriptSettings(self):
        return True

    def onImportDgm(self, action=None):
        return True

    def onImportDgmTuned(self):
        return True

    def shouldAcceptFocus(self):
        return True

    def writeFile(self, fileName):
        """Writes the text to a file"""
        return self.__viewer.writeFile(fileName)

    def updateModificationTime(self, fileName):
        return

    def appendIDEMessage(self, text):
        """Appends an IDE message"""
        self.__viewer.appendIDEMessage(text)

    def appendStdoutMessage(self, text):
        """Appends an stdout message"""
        self.__viewer.appendStdoutMessage(text)

    def appendStderrMessage(self, text):
        """Appends an stderr message"""
        self.__viewer.appendStderrMessage(text)

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.__viewer.onTextZoomChanged()
        # self.__viewer.setTimestampMarginWidth()

    def rawInput(self, prompt, echo):
        """Triggered when raw input is requested"""
        echo = int(echo)
        if echo == 0:
            self.__viewer.inputEcho = False
        else:
            self.__viewer.inputEcho = True

        if prompt:
            self.appendStdoutMessage(prompt)
        self.__clearButton.setEnabled(False)
        self.__viewer.switchMode(self.__viewer.MODE_INPUT)

    def sessionStopped(self):
        """Triggered when redirecting session is stopped"""
        self.__viewer.switchMode(self.__viewer.MODE_OUTPUT)
        self.__clearButton.setEnabled(True)

    # Mandatory interface part is below

    def getEditor(self):
        """Provides the editor widget"""
        return self.__viewer

    def isModified(self):
        """Tells if the file is modified"""
        return False

    def getRWMode(self):
        """Tells if the file is read only"""
        return "IO"

    def getMime(self):
        """Provides the file type"""
        return None

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.IOConsole

    def getLanguage(self):
        """Tells the content language"""
        return "IO console"

    def setFileName(self, name):
        """Sets the file name"""
        raise Exception("Setting a file name for IO console "
                        "is not applicable")

    def getEol(self):
        """Tells the EOL style"""
        return self.__viewer.getEolIndicator()

    def getLine(self):
        """Tells the cursor line"""
        line, _ = self.__viewer.cursorPosition
        return line

    def getPos(self):
        """Tells the cursor column"""
        _, pos = self.__viewer.cursorPosition
        return pos

    def getEncoding(self):
        """Tells the content encoding"""
        return self.__viewer.encoding

    def setEncoding(self, newEncoding):
        """Sets the new editor encoding"""
        raise Exception("Setting encoding is not supported by the "
                        "IO console widget")

    def getShortName(self):
        """Tells the display name"""
        return "IO console"

    def setShortName(self, name):
        """Sets the display name"""
        raise Exception("Setting short name is not supported by the "
                        "IO console widget")
