# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2014-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Redirected IO console widget for running and profiling scripts"""

from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from ui.qt import (Qt, QSize, pyqtSignal, QToolBar, QHBoxLayout, QWidget,
                   QAction, QSizePolicy, QMenu, QToolButton, QActionGroup)
from utils.pixmapcache import getIcon
from utils.settings import Settings
from .redirectedmsg import IOConsoleMsg
from .redirectedioconsole import RedirectedIOConsole


class RunConsoleTabWidget(QWidget, MainWindowTabWidgetBase):

    """IO console tab widget"""

    textEditorZoom = pyqtSignal(int)
    settingUpdated = pyqtSignal()

    def __init__(self, threadID, parent=None):

        MainWindowTabWidgetBase.__init__(self)
        QWidget.__init__(self, parent)

        self.__viewer = RedirectedIOConsole(self)
        self.__viewer.UserInput.connect(self.__onUserInput)

        self.__threadID = threadID
        self.__showstdin = True
        self.__showstdout = True
        self.__showstderr = True

        self.__createLayout()

    def threadID(self):
        """Provides the thread ID the console linked to"""
        return self.__threadID

    def __onUserInput(self, userInput):
        """Triggered when the user finished input"""
        self.UserInput.emit(self.__threadID, userInput)
        self.__clearButton.setEnabled(True)

    def __createLayout(self):
        """Creates the toolbar and layout"""
        # Buttons
        self.__printButton = QAction(getIcon('printer.png'), 'Print', self)
        self.__printButton.triggered.connect(self.__onPrint)
        self.__printButton.setEnabled(False)
        self.__printButton.setVisible(False)

        self.__printPreviewButton = QAction(
            getIcon('printpreview.png'), 'Print preview', self)
        self.__printPreviewButton.triggered.connect(self.__onPrintPreview)
        self.__printPreviewButton.setEnabled(False)
        self.__printPreviewButton.setVisible(False)

        # self.__sendUpButton = QAction(getIcon('sendioup.png'),
        #                               'Send to Main Editing Area', self)
        # self.__sendUpButton.triggered.connect(self.__sendUp)

        self.__filterMenu = QMenu(self)
        self.__filterMenu.aboutToShow.connect(self.__filterAboutToShow)
        self.__filterGroup = QActionGroup(self)
        self.__filterShowAllAct = self.__filterMenu.addAction("Show all")
        self.__filterShowAllAct.setCheckable(True)
        self.__filterShowAllAct.setActionGroup(self.__filterGroup)
        self.__filterShowAllAct.triggered.connect(self.__onFilterShowAll)
        self.__filterShowStdoutAct = self.__filterMenu.addAction(
            "Show stdin and stdout")
        self.__filterShowStdoutAct.setCheckable(True)
        self.__filterShowStdoutAct.setActionGroup(self.__filterGroup)
        self.__filterShowStdoutAct.triggered.connect(self.__onFilterShowStdout)
        self.__filterShowStderrAct = self.__filterMenu.addAction(
            "Show stdin and stderr")
        self.__filterShowStderrAct.setCheckable(True)
        self.__filterShowStderrAct.setActionGroup(self.__filterGroup)
        self.__filterShowStderrAct.triggered.connect(self.__onFilterShowStderr)
        self.__filterButton = QToolButton(self)
        self.__filterButton.setIcon(getIcon('iofilter.png'))
        self.__filterButton.setToolTip('Filtering settings')
        self.__filterButton.setPopupMode(QToolButton.InstantPopup)
        self.__filterButton.setMenu(self.__filterMenu)
        self.__filterButton.setFocusPolicy(Qt.NoFocus)

        self.__settingsMenu = QMenu(self)
        self.__settingsMenu.aboutToShow.connect(self.__settingsAboutToShow)
        self.__wrapLongLinesAct = self.__settingsMenu.addAction(
            "Wrap long lines")
        self.__wrapLongLinesAct.setCheckable(True)
        self.__wrapLongLinesAct.triggered.connect(self.__onWrapLongLines)
        self.__showEOLAct = self.__settingsMenu.addAction("Show EOL")
        self.__showEOLAct.setCheckable(True)
        self.__showEOLAct.triggered.connect(self.__onShowEOL)
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

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight(8)

        self.__stopButton = QAction(getIcon('runconsolestop.png'),
                                    'Stop process', self)
        self.__stopButton.triggered.connect(self.stop)

        self.__stopAndCloseButton = QAction(getIcon('runconsolestopclose.png'),
                                            'Stop process and close tab', self)
        self.__stopAndCloseButton.triggered.connect(self.stopAndClose)

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
        toolbar.addAction(self.__printPreviewButton)
        toolbar.addAction(self.__printButton)
        toolbar.addWidget(self.__filterButton)
        toolbar.addWidget(self.__settingsButton)
        toolbar.addWidget(fixedSpacer)
        toolbar.addAction(self.__stopButton)
        toolbar.addAction(self.__stopAndCloseButton)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.__clearButton)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(toolbar)
        hLayout.addWidget(self.__viewer)

        self.setLayout(hLayout)

    def onZoomReset(self):
        """Triggered when the zoom reset button is pressed"""
        if self.__viewer.zoom != 0:
            self.textEditorZoom.emit(0)
        return True

    def onZoomIn(self):
        """Triggered when the zoom in button is pressed"""
        if self.__viewer.zoom < 20:
            self.textEditorZoom.emit(self.__viewer.zoom + 1)
        return True

    def onZoomOut(self):
        """Triggered when the zoom out button is pressed"""
        if self.__viewer.zoom > -10:
            self.textEditorZoom.emit(self.__viewer.zoom - 1)
        return True

    def __onPrint(self):
        """Triggered when the print button is pressed"""
        pass

    def __onPrintPreview(self):
        """Triggered when the print preview button is pressed"""
        pass

    def setFocus(self):
        """Overridden setFocus"""
        self.__viewer.setFocus()

    def onOpenImport( self ):
        " Triggered when Ctrl+I is received "
        return True

    def __sendUp(self):
        """Triggered when requested to move the console up"""
        pass

    def __filterAboutToShow(self):
        """Triggered when filter menu is about to show"""
        showAll = self.__showstdin and \
                  self.__showstdout and \
                  self.__showstderr
        onlyStdout = self.__showstdin and \
                     self.__showstdout and \
                     not self.__showstderr
        onlyStderr = self.__showstdin and \
                     not self.__showstdout and \
                     self.__showstderr
        self.__filterShowAllAct.setChecked(showAll)
        self.__filterShowStdoutAct.setChecked(onlyStdout)
        self.__filterShowStderrAct.setChecked(onlyStderr)

    def __onFilterShowAll(self):
        """Triggered when filter show all is clicked"""
        if self.__showstdin == True and \
           self.__showstdout == True and \
           self.__showstderr == True:
            return

        self.__showstdin = True
        self.__showstdout = True
        self.__showstderr = True
        self.__viewer.renderContent()

    def __onFilterShowStdout(self):
        """Triggered when filter show stdout only is clicked"""
        if self.__showstdin == True and \
           self.__showstdout == True and \
           self.__showstderr == False:
            return

        self.__showstdin = True
        self.__showstdout = True
        self.__showstderr = False
        self.__viewer.renderContent()

    def __onFilterShowStderr(self):
        """Triggered when filter show stderr only is clicked"""
        if self.__showstdin == True and \
           self.__showstdout == False and \
           self.__showstderr == True:
            return

        self.__showstdin = True
        self.__showstdout = False
        self.__showstderr = True
        self.__viewer.renderContent()

    def __settingsAboutToShow(self):
        """Settings menu is about to show"""
        self.__wrapLongLinesAct.setChecked(Settings().ioconsolelinewrap)
        self.__showEOLAct.setChecked(Settings().ioconsoleshoweol)
        self.__showWhitespacesAct.setChecked(Settings().ioconsoleshowspaces)
        self.__autoscrollAct.setChecked(Settings().ioconsoleautoscroll)
        self.__showMarginAct.setChecked(Settings().ioconsoleshowmargin)

    def __onWrapLongLines(self):
        """Triggered when long lines setting is changed"""
        Settings().ioconsolelinewrap = not Settings().ioconsolelinewrap
        self.settingUpdated.emit()

    def __onShowEOL(self):
        """Triggered when show EOL is changed"""
        Settings().ioconsoleshoweol = not Settings().ioconsoleshoweol
        self.settingUpdated.emit()

    def __onShowWhitespaces(self):
        """Triggered when show whitespaces is changed"""
        Settings().ioconsoleshowspaces = not Settings().ioconsoleshowspaces
        self.settingUpdated.emit()

    def __onAutoscroll(self):
        """Triggered when autoscroll is changed"""
        Settings().ioconsoleautoscroll = not Settings().ioconsoleautoscroll

    def __onShowMargin(self):
        """Triggered when show margin is changed"""
        Settings().ioconsoleshowmargin = not Settings().ioconsoleshowmargin
        self.settingUpdated.emit()

    def clear(self):
        """Triggered when requested to clear the console"""
        self.__viewer.clearAll()

    def consoleSettingsUpdated(self):
        """Triggered when one of the consoles updated a common setting"""
        if Settings().ioconsolelinewrap:
            self.__viewer.setWrapMode(QsciScintilla.WrapWord)
        else:
            self.__viewer.setWrapMode(QsciScintilla.WrapNone)
        self.__viewer.setEolVisibility(Settings().ioconsoleshoweol)
        if Settings().ioconsoleshowspaces:
            self.__viewer.setWhitespaceVisibility(QsciScintilla.WsVisible)
        else:
            self.__viewer.setWhitespaceVisibility(QsciScintilla.WsInvisible)
        self.__viewer.setTimestampMarginWidth()

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)

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

    def hiddenMessage(self, msg):
        """Returns True if the message should not be shown"""
        if msg.msgType == IOConsoleMsg.STDERR_MESSAGE and \
           not self.__showstderr:
            return True
        if msg.msgType == IOConsoleMsg.STDOUT_MESSAGE and \
           not self.__showstdout:
            return True
        return False

    def zoomTo(self, zoomValue):
        """Sets the new zoom value"""
        self.__viewer.zoomTo(zoomValue)
        self.__viewer.setTimestampMarginWidth()

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

    def stop(self):
        """Triggered when the user requesed to stop the process"""
        self.KillIOConsoleProcess.emit(self.__threadID)

    def stopAndClose(self):
        """The user requested to stop the process and close console"""
        self.stop()
        self.close()

    def close(self):
        """Triggered when the console should be closed"""
        self.CloseIOConsole.emit(self.__threadID)

    def scriptFinished(self):
        """Triggered when the script process finished"""
        self.__stopButton.setEnabled(False)
        self.__stopAndCloseButton.setToolTip("Close tab")
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

    def getFileType(self):
        """Provides the file type"""
        return ""

    def setFileType(self, typeToSet):
        """Sets the file type explicitly"""
        raise Exception("Setting a file type is not supported by the "
                        "IO console widget")

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.IOConsole

    def getLanguage(self):
        """Tells the content language"""
        return "IO console"

    def getFileName(self):
        """Tells what file name of the widget content"""
        return "n/a"

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
        return int(line)

    def getPos(self):
        """Tells the cursor column"""
        _, pos = self.__viewer.cursorPosition
        return int(pos)

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
