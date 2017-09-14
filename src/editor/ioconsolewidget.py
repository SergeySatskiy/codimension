# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy sergey.satskiy@gmail.com
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


"""Redirected IO console widget for running/profiling/debugging scripts"""


from ui.qt import (Qt, QSize, pyqtSignal, QToolBar, QHBoxLayout, QWidget,
                   QAction, QSizePolicy, QMenu, QToolButton)
from utils.runparams import DEBUG
from utils.settings import Settings
from utils.pixmapcache import getIcon
from .redirectedioconsole import RedirectedIOConsole


class IOConsoleWidget(QWidget):

    """IO Console widget"""

    sigSettingsUpdated = pyqtSignal()
    sigUserInput = pyqtSignal(str, str)
    sigKillIOConsoleProcess = pyqtSignal(str)
    sigCloseIOConsole = pyqtSignal(int)

    def __init__(self, procuuid, kind, parent=None):
        QWidget.__init__(self, parent)
        self.procuuid = procuuid
        self.kind = kind    # RUN/DEBUG/PROFILE

        self.__viewer = RedirectedIOConsole(self)
        self.__viewer.sigUserInput.connect(self.__onUserInput)

        self.__createLayout()

    def setFocus(self):
        """Overridden setFocus"""
        self.__viewer.setFocus()

    def __onUserInput(self, userInput):
        """The user finished input in the redirected IO console"""
        self.sigUserInput.emit(self.procuuid, userInput)
        self.__clearButton.setEnabled(True)

    def __createLayout(self):
        """Creates the toolbar and layout"""
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

        self.__settingsButton = QToolButton(self)
        self.__settingsButton.setIcon(getIcon('iosettings.png'))
        self.__settingsButton.setToolTip('View settings')
        self.__settingsButton.setPopupMode(QToolButton.InstantPopup)
        self.__settingsButton.setMenu(self.__settingsMenu)
        self.__settingsButton.setFocusPolicy(Qt.NoFocus)

        if self.kind != DEBUG:
            fixedSpacer = QWidget()
            fixedSpacer.setFixedHeight(8)

            self.__stopButton = QAction(getIcon('runconsolestop.png'),
                                        'Stop process', self)
            self.__stopButton.triggered.connect(self.stop)

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

        toolbar.addWidget(self.__settingsButton)

        if self.kind != DEBUG:
            toolbar.addWidget(fixedSpacer)
            toolbar.addAction(self.__stopButton)

        toolbar.addWidget(spacer)
        toolbar.addAction(self.__clearButton)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(toolbar)
        hLayout.addWidget(self.__viewer)

        self.setLayout(hLayout)

    def __settingsAboutToShow(self):
        """Settings menu is about to show"""
        self.__wrapLongLinesAct.setChecked(Settings()['ioconsolelinewrap'])
        self.__showWhitespacesAct.setChecked(Settings()['ioconsoleshowspaces'])
        self.__autoscrollAct.setChecked(Settings()['ioconsoleautoscroll'])

    def __onWrapLongLines(self):
        """Triggered when long lines setting is changed"""
        Settings()['ioconsolelinewrap'] = not Settings()['ioconsolelinewrap']
        self.sigSettingsUpdated.emit()

    def __onShowWhitespaces(self):
        """Triggered when show whitespaces is changed"""
        Settings()['ioconsoleshowspaces'] = \
            not Settings()['ioconsoleshowspaces']
        self.sigSettingsUpdated.emit()

    @staticmethod
    def __onAutoscroll():
        """Triggered when autoscroll is changed"""
        Settings()['ioconsoleautoscroll'] = \
            not Settings()['ioconsoleautoscroll']

    def clear(self):
        """Triggered when requested to clear the console"""
        self.__viewer.clearAll()

    def consoleSettingsUpdated(self):
        """Triggered when one of the consoles updated a common setting"""
        self.__viewer.updateSettings()

    def resizeEvent(self, event):
        """Handles the widget resize"""
        QWidget.resizeEvent(self, event)

    def writeFile(self, fileName):
        """Writes the text to a file"""
        return self.__viewer.writeFile(fileName)

    def appendIDEMessage(self, text):
        """Appends an IDE message"""
        return self.__viewer.appendIDEMessage(text)

    def appendStdoutMessage(self, _, text):
        """Appends an stdout message"""
        return self.__viewer.appendStdoutMessage(text)

    def appendStderrMessage(self, _, text):
        """Appends an stderr message"""
        return self.__viewer.appendStderrMessage(text)

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.__viewer.onTextZoomChanged()

    def input(self, procuuid, prompt, echo):
        """Triggered when input is requested"""
        self.__viewer.inputEcho = echo
        if prompt:
            self.appendStdoutMessage(procuuid, prompt)
        self.__clearButton.setEnabled(False)
        self.__viewer.switchMode(self.__viewer.MODE_INPUT)

    def sessionStopped(self):
        """Triggered when redirecting session is stopped"""
        self.__viewer.switchMode(self.__viewer.MODE_OUTPUT)
        self.__clearButton.setEnabled(True)

    def stop(self):
        """Triggered when the user requesed to stop the process"""
        self.sigKillIOConsoleProcess.emit(self.procuuid)

    def scriptFinished(self):
        """Triggered when the script process finished"""
        if self.kind != DEBUG:
            self.__stopButton.setEnabled(False)
        self.__viewer.switchMode(self.__viewer.MODE_OUTPUT)
        self.__clearButton.setEnabled(True)

    def onReuse(self, procuuid):
        """Triggered when the console is reused"""
        self.procuuid = procuuid
        if self.kind != DEBUG:
            self.__stopButton.setEnabled(True)
