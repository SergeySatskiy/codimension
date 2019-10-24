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

"""Text viewer tab widget"""

import os.path
import logging
from .qt import (QTextBrowser, QHBoxLayout, QWidget, Qt, pyqtSignal,
                 QDesktopServices)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.misc import resolveLinkPath
from utils.globals import GlobalData


class TextViewer(QTextBrowser):

    """Text viewer"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):
        QTextBrowser.__init__(self, parent)

        self._parentWidget = parent
        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)

        self.__copyAvailable = False
        self.copyAvailable.connect(self.__onCopyAvailable)
        self.anchorClicked.connect(self._onAnchorClicked)

    def __onCopyAvailable(self, available):
        """Triggered when copying is available"""
        self.__copyAvailable = available

    def _resolveLink(self, link):
        """Resolves the link to a file and optional anchor/line number"""
        scheme = link.scheme().lower()
        if scheme in ['http', 'https']:
            QDesktopServices.openUrl(link)
            return None, None

        if scheme == '':
            fileName = link.path()
        elif scheme == 'file':
            if link.isValid():
                fileName = link.path()
            else:
                logging.error('Invalid link: ' + link.errorString())
                return None, None
        elif scheme == 'action':
            if link.isValid():
                # The action is stored in the host part
                action = link.host()
                # The actions are predefined. I did not find a generic way
                # to find what the key is bound to
                if action.lower() == 'embedded-help':
                    GlobalData().mainWindow._onEmbeddedHelp()
                elif action.lower() == 'f1':
                    GlobalData().mainWindow.em.onHelp()
                elif action.lower() == 'project-cocumentation':
                    GlobalData().mainWindow.projectDocClicked()
                else:
                    # must be a keyboard shortcut
                    logging.error("Unsupported action '" + link.host() + "'")
            return None, None
        else:
            logging.error("Unsupported url scheme '" + link.scheme() +
                          "'. Supported schemes are 'http', 'https', 'file' "
                          "and an empty scheme for files")
            return None, None

        if not fileName:
            logging.error('Could not get a file name. Check the link format. '
                          'Valid examples: file:./relative/fname or '
                          'file:relative/fname or file:/absolute/fname or '
                          'file:///absolute/fname')
            return None, None

        fileName, anchorOrLine = resolveLinkPath(fileName,
                                                 self._parentWidget.getFileName())
        if anchorOrLine is None:
            if link.hasFragment():
                return fileName, link.fragment()
        return fileName, anchorOrLine

    def _onAnchorClicked(self, link):
        """Handles a URL click"""
        fileName, anchorOrLine = self._resolveLink(link)
        if fileName:
            GlobalData().mainWindow.openFile(fileName, anchorOrLine)

    def isCopyAvailable(self):
        """True if text copying is available"""
        return self.__copyAvailable

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            self.sigEscapePressed.emit()
            event.accept()
        else:
            QTextBrowser.keyPressEvent(self, event)


class TextTabWidget(QWidget, MainWindowTabWidgetBase):

    """The widget which displays a RO HTML page"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        MainWindowTabWidgetBase.__init__(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.__editor = TextViewer(self)
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
        f = open(path, 'r')
        content = f.read()
        f.close()
        self.setHTML(content)
        self.__fileName = path
        self.__shortName = os.path.basename(path)

    def getViewer(self):
        """Provides the QTextBrowser"""
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
        return "n/a"

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
