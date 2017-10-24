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

"""HTML viewer tab widget"""

import os.path
from utils.fileutils import getFileContent
from utils.colorfont import getZoomedMonoFont
from .qt import QFrame, QHBoxLayout, QTextBrowser, Qt, pyqtSignal
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class HTMLViewer(QTextBrowser):

    """HTML viewer (web browser)"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):
        QTextBrowser.__init__(self, parent)

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            self.sigEscapePressed.emit()
            event.accept()
        else:
            QTextBrowser.keyPressEvent(self, event)

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed.
           It is mostly used in diff viewers
        """
        self.setFont(getZoomedMonoFont())


class HTMLTabWidget(MainWindowTabWidgetBase, QFrame):

    """The widget which displays a RO HTML page"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):

        MainWindowTabWidgetBase.__init__(self)
        QFrame.__init__(self, parent)

        self.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.__editor = HTMLViewer(self)
        self.__editor.sigEscapePressed.connect(self.__onEsc)
        layout.addWidget(self.__editor)

        self.__fileName = ""
        self.__shortName = ""
        self.__encoding = "n/a"

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

    def setHTML(self, content):
        """Sets the content from the given string"""
        self.__editor.setHtml(content)

    def getHTML(self):
        """Provides the currently shown HTML"""
        return self.__editor.toHtml()

    def loadFormFile(self, path):
        """Loads the content from the given file"""
        self.setHTML(getFileContent(path))
        self.__fileName = path
        self.__shortName = os.path.basename(path)

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.__editor.onTextZoomChanged()

    def getViewer(self):
        """Provides the QWebView"""
        return self.__editor

    def setFocus(self):
        """Overridden setFocus"""
        self.__editor.setFocus()

    def isModified(self):
        """Tells if the file is modifed"""
        return False

    def getRWMode(self):
        """Tells the read/write mode"""
        return "RO"

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.HTMLViewer

    def getLanguage(self):
        """Tells the content language"""
        return "HTML"

    def getFileName(self):
        """Tells what file name of the widget"""
        return self.__fileName

    def setFileName(self, path):
        """Sets the file name"""
        self.__fileName = path
        self.__shortName = os.path.basename(path)

    def getEncoding(self):
        """Tells the content encoding"""
        return self.__encoding

    def setEncoding(self, newEncoding):
        """Sets the encoding - used for Diff files"""
        self.__encoding = newEncoding

    def getShortName(self):
        """Tells the display name"""
        return self.__shortName

    def setShortName(self, name):
        """Sets the display name"""
        self.__shortName = name
