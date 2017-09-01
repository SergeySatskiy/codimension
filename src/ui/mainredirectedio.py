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

"""Codimension main window redirected io support"""

from editor.redirectedioconsole import IOConsoleTabWidget
from utils.pixmapcache import getIcon
from utils.runparams import RUN, PROFILE, DEBUG
from .qt import QApplication, QCursor, Qt


class MainWindowRedirectedIOMixin:

    """Main window redirected IO mixin"""

    def __init__(self):
        self.redirectedIOConsole = None
        self.__newRunIndex = -1
        self.__newProfileIndex = -1
        self.__newDebugIndex = -1

    def _initRedirectedIO(self):
        """Connects the signals etc."""
        # The only redirected IO consoles are cloasable
        self._bottomSideBar.sigTabCloseRequested.connect(self.__onCloseRequest)

    def __onCloseRequest(self, index):
        """User wants to close a redirected IO console"""
        print("Request to close: " + str(index))

    def __getNewRunIndex(self):
        """Provides the new run index"""
        self.__newRunIndex += 1
        return self.__newRunIndex

    def __getNewProfileIndex(self):
        """Provides the new profile index"""
        self.__newProfileIndex += 1
        return self.__newProfileIndex

    def __getNewDebugIndex(self):
        """Provides a new debug console index"""
        self.__newDebugIndex += 1
        return self.__newDebugIndex

    def installIOConsole(self, widget, consoleType):
        """Installs a new widget at the bottom"""
        if consoleType not in [RUN, PROFILE, DEBUG]:
            raise Exception('Undefined redirected IO console type')

        if consoleType == PROFILE:
            index = str(self.__getNewProfileIndex())
            caption = 'Profiling #' + index
            name = 'profiling#' + index
            tooltip = 'Redirected IO profile console #' + index + ' (running)'
        elif consoleType == RUN:
            index = str(self.__getNewRunIndex())
            caption = 'Run #' + index
            name = 'running#' + index
            tooltip = 'Redirected IO run console #' + index + ' (running)'
        else:
            index = str(__getNewDebugIndex())
            caption = 'Debug #' + index
            name = 'debugging#' + index
            tooltip = 'Redirected IO debug console #' + index + ' (running)'

        widget.sigKillIOConsoleProcess.connect(self.__onKillIOConsoleProcess)
        widget.sigSettingsUpdated.connect(self.onIOConsoleSettingsUpdated)

        self._bottomSideBar.addTab(
            widget, getIcon('ioconsole.png'), caption, name, None)
        self._bottomSideBar.setTabToolTip(name, tooltip)
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab(name)
        self._bottomSideBar.raise_()
        widget.setFocus()

    def __onKillIOConsoleProcess(self, threadID):
        """Kills the process linked to the IO console"""
        self.__runManager.kill(threadID)

    def onIOConsoleSettingsUpdated(self):
        """Initiates updating all the IO consoles settings"""
        index = self._bottomSideBar.count() - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.consoleSettingsUpdated()
            index -= 1

    def installRedirectedIOConsole(self):
        """Create redirected IO console"""
        self.redirectedIOConsole = IOConsoleTabWidget(self)
        self.redirectedIOConsole.sigUserInput.connect(self.__onUserInput)
        self.redirectedIOConsole.sigSettingsUpdated.connect(
            self.onIOConsoleSettingsUpdated)
        self._bottomSideBar.addTab(
            self.redirectedIOConsole, getIcon('ioconsole.png'),
            'IO console', 'ioredirect', None)
        self._bottomSideBar.setTabToolTip('ioredirect',
                                           'Redirected IO debug console')

    def clearDebugIOConsole(self):
        """Clears the content of the debug IO console"""
        if self.redirectedIOConsole:
            self.redirectedIOConsole.clear()

    def __onClientStdout(self, data):
        """Triggered when the client reports stdout"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.appendStdoutMessage(data)

    def __onClientStderr(self, data):
        """Triggered when the client reports stderr"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.appendStderrMessage(data)

    def __ioconsoleIDEMessage(self, message):
        """Sends an IDE message to the IO console"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.appendIDEMessage(message)

    def __onClientRawInput(self, prompt, echo):
        """Triggered when the client input is requested"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.rawInput(prompt, echo)
        self.redirectedIOConsole.setFocus()

    def __onUserInput(self, userInput):
        """Triggered when the user finished input in the redirected IO tab"""
        self.__debugger.remoteRawInput(userInput)

    def updateIOConsoleTooltip(self, threadID, msg):
        """Updates the IO console tooltip"""
        index = self.__getIOConsoleIndex(threadID)
        if index is not None:
            tooltip = self._bottomSideBar.tabToolTip(index)
            tooltip = tooltip.replace("(running)", "(" + msg + ")")
            self._bottomSideBar.setTabToolTip(index, tooltip)

    def __getIOConsoleIndex(self, threadID):
        """Provides the IO console index by the thread ID"""
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "threadID"):
                if widget.threadID() == threadID:
                    return index
            index -= 1
        return None

    def __onCloseIOConsole(self, threadID):
        """Closes the tab with the corresponding widget"""
        index = self.__getIOConsoleIndex(threadID)
        if index is not None:
            self._bottomSideBar.removeTab(index)

    def closeAllIOConsoles(self):
        """Closes all IO run/profile tabs and clears the debug IO console"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    if hasattr(widget, "stopAndClose"):
                        widget.stopAndClose()
            index -= 1

        self.clearDebugIOConsole()
        QApplication.restoreOverrideCursor()
