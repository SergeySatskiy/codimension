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

"""Codimension main window status bar"""

from utils.colorfont import colorAsString
from .qt import Qt, QLabel, QPalette, QColor
from .fitlabel import FitPathLabel


class MainWindowStatusBarMixin:

    """Main window status bar mixin"""

    def __init__(self):

        self.__statusBar = None
        self.sbLanguage = None
        self.sbFile = None
        self.sbEol = None
        self.sbPos = None
        self.sbLine = None
        self.sbWritable = None
        self.sbEncoding = None
        self.sbPyflakes = None
        self.sbVCSStatus = None
        self.sbDebugState = None
        self.__createStatusBar()

    def __createStatusBar(self):
        """Creates status bar"""
        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        labelStylesheet = self.__getLabelStylesheet()

        self.sbVCSStatus = FitPathLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbVCSStatus)
        self.sbVCSStatus.setVisible(False)
        self.sbVCSStatus.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sbVCSStatus.customContextMenuRequested.connect(
            self._showVCSLabelContextMenu)

        self.sbDebugState = QLabel("Debugger: unknown", self.__statusBar)
        self.sbDebugState.setStyleSheet(labelStylesheet)
        self.sbDebugState.setAutoFillBackground(True)
        dbgPalette = self.sbDebugState.palette()
        dbgPalette.setColor(QPalette.Background, QColor(255, 255, 127))
        self.sbDebugState.setPalette(dbgPalette)
        self.__statusBar.addPermanentWidget(self.sbDebugState)
        self.sbDebugState.setToolTip("Debugger status")
        self.sbDebugState.setVisible(False)

        self.sbLanguage = QLabel(self.__statusBar)
        self.sbLanguage.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbLanguage)
        self.sbLanguage.setToolTip("Editor language/image format")

        self.sbEncoding = QLabel(self.__statusBar)
        self.sbEncoding.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbEncoding)
        self.sbEncoding.setToolTip("Editor encoding/image size")

        self.sbEol = QLabel(self.__statusBar)
        self.sbEol.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbEol)
        self.sbEol.setToolTip("Editor EOL setting")

        self.sbWritable = QLabel(self.__statusBar)
        self.sbWritable.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbWritable)
        self.sbWritable.setToolTip("Editor file read/write mode")

        # FitPathLabel has support for double click event,
        # so it is used here. Purely it would be better to have another
        # class for a pixmap label. But I am lazy.
        self.sbPyflakes = FitPathLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbPyflakes)

        self.sbFile = FitPathLabel(self.__statusBar)
        self.sbFile.setMaximumWidth(512)
        self.sbFile.setMinimumWidth(128)
        self.sbFile.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbFile, True)
        self.sbFile.setToolTip("Editor file name (double click to copy path)")
        self.sbFile.doubleClicked.connect(self._onPathLabelDoubleClick)
        self.sbFile.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sbFile.customContextMenuRequested.connect(
            self._showPathLabelContextMenu)

        self.sbLine = QLabel(self.__statusBar)
        self.sbLine.setMinimumWidth(72)
        self.sbLine.setAlignment(Qt.AlignCenter)
        self.sbLine.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbLine)
        self.sbLine.setToolTip("Editor line number")

        self.sbPos = QLabel(self.__statusBar)
        self.sbPos.setMinimumWidth(72)
        self.sbPos.setAlignment(Qt.AlignCenter)
        self.sbPos.setStyleSheet(labelStylesheet)
        self.__statusBar.addPermanentWidget(self.sbPos)
        self.sbPos.setToolTip("Editor cursor position")

    def __getLabelStylesheet(self):
        """Generates the status bar labels stylesheet"""
        modelLabel = QLabel(self)
        bgColor = modelLabel.palette().color(modelLabel.backgroundRole())
        del modelLabel

        red = bgColor.red()
        green = bgColor.green()
        blue = bgColor.blue()
        delta = 60

        borderColor = QColor(max(red - delta, 0),
                             max(green - delta, 0),
                             max(blue - delta, 0))
        bgColor = QColor(min(red + delta, 255),
                         min(green + delta, 255),
                         min(blue + delta, 255))

        props = ['border-radius: 3px',
                 'padding: 2px',
                 'background-color: ' + colorAsString(bgColor, True),
                 'border: 1px solid ' + colorAsString(borderColor, True)]
        return '; '.join(props)

    def showStatusBarMessage(self, msg, timeout=10000):
        """Shows a temporary status bar message, default 10sec"""
        self.__statusBar.showMessage(msg, timeout)

    def clearStatusBarMessage(self):
        """Clears the status bar message in the given slot"""
        self.__statusBar.clearMessage()
