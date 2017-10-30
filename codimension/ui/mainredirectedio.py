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

from utils.pixmapcache import getIcon
from utils.runparams import RUN, PROFILE, DEBUG
from .qt import QApplication, QCursor, Qt, QTabBar


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
        self._bottomSideBar.removeTab(index)

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

    def __getCaptionNameTooltip(self, kind):
        """Provides the tab caption, name and tooltip"""
        if kind == PROFILE:
            index = str(self.__getNewProfileIndex())
            return ('Profiling #' + index, 'profiling#' + index,
                    'Redirected IO profile console #' + index + ' (running)')
        if kind == RUN:
            index = str(self.__getNewRunIndex())
            return ('Run #' + index, 'running#' + index,
                    'Redirected IO run console #' + index + ' (running)')
        index = str(self.__getNewDebugIndex())
        return ('Debug #' + index, 'debugging#' + index,
                'Redirected IO debug console #' + index + ' (running)')

    def addIOConsole(self, widget, consoleType):
        """Installs a new widget at the bottom"""
        if consoleType not in [RUN, PROFILE, DEBUG]:
            raise Exception('Undefined redirected IO console type')

        caption, name, tooltip = self.__getCaptionNameTooltip(consoleType)

        widget.sigKillIOConsoleProcess.connect(self.__onKillIOConsoleProcess)
        widget.sigSettingsUpdated.connect(self.onIOConsoleSettingsUpdated)

        self._bottomSideBar.addTab(
            widget, getIcon('ioconsole.png'), caption, name, None)
        self._bottomSideBar.tabButton(widget, QTabBar.RightSide).hide()
        self._bottomSideBar.setTabToolTip(name, tooltip)
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab(name)
        self._bottomSideBar.raise_()
        widget.setFocus()

    def __onKillIOConsoleProcess(self, procuuid):
        """Kills the process linked to the IO console"""
        self._runManager.kill(procuuid)

    def onIOConsoleSettingsUpdated(self):
        """Initiates updating all the IO consoles settings"""
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, 'procuuid'):
                if hasattr(widget, 'consoleSettingsUpdated'):
                    widget.consoleSettingsUpdated()
            index -= 1

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

    def updateIOConsoleTooltip(self, procuuid, msg):
        """Updates the IO console tooltip"""
        index = self.__getIOConsoleIndex(procuuid)
        if index is not None:
            tooltip = self._bottomSideBar.tabToolTip(index)
            tooltip = tooltip.replace("(running)", "(" + msg + ")")
            self._bottomSideBar.setTabToolTip(index, tooltip)

    def __getIOConsoleIndex(self, procuuid):
        """Provides the IO console index by the thread ID"""
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "procuuid"):
                if widget.procuuid == procuuid:
                    return index
            index -= 1
        return None

    def __onCloseIOConsole(self, procuuid):
        """Closes the tab with the corresponding widget"""
        index = self.__getIOConsoleIndex(procuuid)
        if index is not None:
            self._bottomSideBar.removeTab(index)

    def closeAllIOConsoles(self):
        """Closes all IO run/profile tabs and clears the debug IO console"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, 'procuuid'):
                if hasattr(widget, "stopAndClose"):
                    widget.stopAndClose()
            index -= 1
        QApplication.restoreOverrideCursor()

    def getIOConsoles(self):
        """Provides a list of the current IO consoles"""
        consoles = []
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, 'procuuid'):
                consoles.append(widget)
            index -= 1
        return consoles

    def onReuseConsole(self, widget, kind):
        """Called when a console is reused"""
        caption, name, tooltip = self.__getCaptionNameTooltip(kind)
        self._bottomSideBar.tabButton(widget, QTabBar.RightSide).hide()
        self._bottomSideBar.updateTabName(widget, name)
        self._bottomSideBar.setTabText(widget, caption)
        self._bottomSideBar.setTabToolTip(widget, tooltip)
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab(widget)
        self._bottomSideBar.raise_()
        widget.setFocus()

    def onConsoleFinished(self, widget):
        """Triggered when a process finished one way or another"""
        self._bottomSideBar.tabButton(widget, QTabBar.RightSide).show()
