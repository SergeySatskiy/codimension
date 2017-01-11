# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Debugger break and watch point viewer"""

from ui.qt import Qt, QVBoxLayout, QWidget, QSplitter
from .bpointviewer import BreakPointViewer
from .wpointviewer import WatchPointViewer


class DebuggerBreakWatchPoints(QWidget):

    """Implements the debugger break and watch point viewer"""

    def __init__(self, parent, debugger):
        QWidget.__init__(self, parent)

        self.__debugger = debugger
        self.__createLayout()

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(1, 1, 1, 1)

        self.splitter = QSplitter(Qt.Vertical)
        self.breakPointViewer = BreakPointViewer(
            self.splitter, self.__debugger.getBreakPointModel())
        self.__watchPointViewer = WatchPointViewer(
            self.splitter, self.__debugger.getWatchPointModel())
        # TODO: temporary
        self.__watchPointViewer.setVisible(False)

        self.splitter.addWidget(self.breakPointViewer)
        self.splitter.addWidget(self.__watchPointViewer)

        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        verticalLayout.addWidget(self.splitter)

    def clear(self):
        """Clears everything"""
        self.breakPointViewer.clear()
        self.__watchPointViewer.clear()

    def setFocus(self):
        """Sets the focus to the break points window"""
        self.breakPointViewer.setFocus()
