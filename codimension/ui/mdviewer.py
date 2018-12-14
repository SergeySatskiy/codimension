# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Markdown viewer tab widget"""

from .qt import (QWidget, Qt, pyqtSignal)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase

class MarkdownTabWidget(QWidget, MainWindowTabWidgetBase):

    """Markdown widget"""

    sigEscapePressed = pyqtSignal()

    READONLY = 0
    READWRITE = 1

    def __init__(self, mode, parent=None):
        MainWindowTabWidgetBase.__init__(self)
        QWidget.__init__(self, parent)

        self.__mode = mode
        self.__fName = None

        self.__createLayout()

    def __createLayout(self):
        """Creates the toolbar and layout"""
        printButton = QAction(getIcon('printer.png'), 'Print', self)
        printButton.triggered.connect(self.__onPrint)

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight(16)

        self.__backButton = QAction(getIcon('mdback.png'), 'Back', self)
        self.__backButton.triggered.connect(self.__onBack)
        self.__backButton.setEnabled(False)

        self.__fwdButton = QAction(getIcon('mdfwd.png'), 'Forward', self)
        self.__fwdButton.triggered.connect(self.__onForward)
        self.__fwdButton.setEnabled(False)

        if self.__mode == MarkdownTabWidget.READWRITE:
            self.__switchToEditButton = QAction(getIcon('switchtoedit.png'),
                                                'Switch to Editing', self)
            self.__switchToEditButton.triggered.connect(self.__onSwitchToEdit)
            self.__switchToEditButton.setEnabled(False)

        # Toolbar
        toolbar = QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setMovable(False)
        toolbar.setAllowedAreas(Qt.RightToolBarArea)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedWidth(28)
        toolbar.setContentsMargins(0, 0, 0, 0)

        toolbar.addAction(printButton)
        toolbar.addWidget(fixedSpacer)
        toolbar.addAction(self.__backButton)
        toolbar.addAction(self.__fwdButton)

        if self.__mode == MarkdownTabWidget.READWRITE:
            fixedSpacer2 = QWidget()
            fixedSpacer2.setFixedHeight(16)
            toolbar.addWidget(fixedSpacer2)
            toolbar.addAction(self.__switchToEditButton)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(self.__viewer)
        hLayout.addWidget(toolbar)

        self.setLayout(hLayout)


