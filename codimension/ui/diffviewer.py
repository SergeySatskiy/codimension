# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""The diff viewer implementation"""

from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from .qt import (Qt, QSize, QHBoxLayout, QWidget, QAction, QToolBar,
                 QSizePolicy, QVBoxLayout)
from .htmltabwidget import HTMLTabWidget


class DiffViewer(QWidget):

    """The diff viewer widget at the bottom"""

    NODIFF = None

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.viewer = None
        self.__clearButton = None
        self.__sendUpButton = None
        self.__createLayout()
        self.__isEmpty = True
        self.__tooltip = ""
        self.__inClear = False

        paperColor = GlobalData().skin['nolexerPaper'].name()
        NODIFF = '<html><body bgcolor="' + paperColor + '"></body></html>'
        self.viewer.setHTML(self.NODIFF)
        self.__updateToolbarButtons()

    def __createLayout(self):
        """Helper to create the viewer layout"""
        self.viewer = HTMLTabWidget()

        # Buttons
        self.__sendUpButton = QAction(getIcon('senddiffup.png'),
                                      'Send to Main Editing Area', self)
        self.__sendUpButton.triggered.connect(self.__sendUp)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.__clearButton = QAction(getIcon('trash.png'),
                                     'Clear Generated Diff', self)
        self.__clearButton.triggered.connect(self.__clear)

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Vertical)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.LeftToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedWidth(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.addAction(self.__sendUpButton)
        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.__clearButton)

        verticalLayout = QVBoxLayout()
        verticalLayout.setContentsMargins(2, 2, 2, 2)
        verticalLayout.setSpacing(2)
        verticalLayout.addWidget(self.viewer)

        # layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addLayout(verticalLayout)

        self.setLayout(layout)

    def setHTML(self, content, tooltip):
        """Shows the given content"""
        if self.__inClear:
            self.viewer.setHTML(content)
            self.viewer.onTextZoomChanged()
            return

        if content == '' or content is None:
            self.__clear()
        else:
            self.viewer.setHTML(content)
            self.viewer.onTextZoomChanged()
            self.__isEmpty = False
            self.__updateToolbarButtons()
            self.__tooltip = tooltip

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.viewer.onTextZoomChanged()

    def __sendUp(self):
        """Triggered when the content should be sent to the main editor area"""
        if not self.__isEmpty:
            GlobalData().mainWindow.showDiffInMainArea(self.viewer.getHTML(),
                                                       self.__tooltip)

    def __clear(self):
        """Triggered when the content should be cleared"""
        self.__inClear = True
        # Dirty hack - reset the tooltip
        GlobalData().mainWindow.showDiff("", "No diff shown")
        self.viewer.setHTML(DiffViewer.NODIFF)
        self.__inClear = False

        self.__isEmpty = True
        self.__tooltip = ""
        self.__updateToolbarButtons()

    def __updateToolbarButtons(self):
        """Contextually updates toolbar buttons"""
        self.__sendUpButton.setEnabled(not self.__isEmpty)
        self.__clearButton.setEnabled(not self.__isEmpty)
