#
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

"""Pyflakes results viewer"""
 
import cgi
from PyQt5.QtCore import QTimer, QObject, Qt, QVariant
from PyQt5.QtGui import QMenu
from utils.pixmapcache import getIcon, getPixmap
from utils.fileutils import isPythonMime, isPythonFile
from analysis.ierrors import getFileErrors
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class PyflakesAttributes:

    """Holds all the attributes associated with pyflakes results"""

    def __init__(self):
        self.messages = []      # Complains
        self.changed = False

    def hasComplains(self):
        """True if there are any complains"""
        if self.messages:
            return True
        return False


class PyflakesViewer(QObject):

    """The pyflakes viewer"""

    def __init__(self, editorsManager, uiLabel, parent=None):
        QObject.__init__(self, parent)

        self.__editorsManager = editorsManager
        self.__uiLabel = uiLabel
        self.setFlakesNotAvailable(self.__uiLabel)

        self.__editorsManager.currentChanged.connect(self.__onTabChanged)
        self.__editorsManager.tabClosed.connect(self.__onTabClosed)
        self.__editorsManager.bufferSavedAs.connect(self.__onSavedBufferAs)
        self.__editorsManager.fileTypeChanged.connect(self.__onFileTypeChanged)

        self.__flakesResults = {}  # UUID -> PyflakesAttributes
        self.__currentUUID = None
        self.__updateTimer = QTimer(self)
        self.__updateTimer.setSingleShot(True)
        self.__updateTimer.timeout.connect(self.__updateView)

        # Context menu for the messages icon
        self.__uiLabel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.__uiLabel.customContextMenuRequested.connect(
            self.__showPyflakesContextMenu)
        self.__uiLabel.doubleClicked.connect(self.__jumpToFirstMessage)

    def __onTabChanged(self, index):
        """Triggered when another tab becomes active"""
        # If the timer is still active that means the tab was switched before
        # the handler had a chance to work. Therefore update the previous tab
        # first if so.
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
            self.__updateView()

        # Now, switch the pyflakes browser to the new tab
        if index == -1:
            widget = self.__editorsManager.currentWidget()
        else:
            widget = self.__editorsManager.getWidgetByIndex(index)
        if widget is None:
            self.__currentUUID = None
            self.setFlakesNotAvailable(self.__uiLabel)
            return

        if widget.getType() not in [MainWindowTabWidgetBase.PlainTextEditor,
                                    MainWindowTabWidgetBase.VCSAnnotateViewer]:
            self.__currentUUID = None
            self.setFlakesNotAvailable(self.__uiLabel)
            return

        # This is text editor, detect the file type
        if isPythonMime(widget.getFileType()):
            self.__currentUUID = None
            self.setFlakesNotAvailable(self.__uiLabel)
            return

        # This is a python file, check if we already have the parsed info in
        # the cache
        uuid = widget.getUUID()
        self.__currentUUID = uuid
        if uuid in self.__flakesResults:
            # We have it, change the icon and the tooltip correspondingly
            results = self.__flakesResults[uuid].messages
            self.setFlakesResults(self.__uiLabel, results, None)
            return

        # It is first time we are here, create a new
        editor = widget.getEditor()
        editor.SCEN_CHANGE.connect(self.__onBufferChanged)
        editor.cursorPositionChanged.connect(self.__cursorPositionChanged)

        results = getFileErrors(editor.text())
        attributes = PyflakesAttributes()
        attributes.messages = results
        attributes.changed = False
        self.__flakesResults[uuid] = attributes
        self.__currentUUID = uuid

        self.setFlakesResults(self.__uiLabel, results, editor)

    def __cursorPositionChanged(self, xpos, ypos):
        """Triggered when a cursor position is changed"""
        if self.__updateTimer.isActive():
            # If a file is very large and the cursor is moved
            # straight after changes this will delay the update till
            # the real pause.
            self.__updateTimer.stop()
            self.__updateTimer.start(1500)

    def __onBufferChanged(self):
        """Triggered when a change in the buffer is identified"""
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return
        if widget.getEditor().ignoreBufferChangedSignal:
            return
        if self.parent().debugMode:
            return

        self.__updateTimer.stop()
        if self.__currentUUID in self.__flakesResults:
            if self.__flakesResults[self.__currentUUID].changed == False:
                self.__flakesResults[self.__currentUUID].changed = True
                self.setFlakesWaiting(self.__uiLabel)
        self.__updateTimer.start(1500)

    def __updateView(self):
        """Updates the view when a file is changed"""
        self.__updateTimer.stop()
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return

        if self.__flakesResults[self.__currentUUID].changed == False:
            return

        editor = widget.getEditor()
        results = getFileErrors(editor.text())

        self.__flakesResults[self.__currentUUID].messages = results
        self.__flakesResults[self.__currentUUID].changed = False

        self.setFlakesResults(self.__uiLabel, results, editor)

    def __onTabClosed(self, uuid):
        """Triggered when a tab is closed"""
        if uuid in self.__flakesResults:
            del self.__flakesResults[uuid]

    def __onSavedBufferAs(self, fileName, uuid):
        """Triggered when a file is saved with a new name"""
        if uuid in self.__flakesResults:
            if not isPythonFile(fileName):
                # It's not a python file anymore
                self.__currentUUID = None
                del self.__flakesResults[uuid]
                self.setFlakesNotAvailable(self.__uiLabel)

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered when the current buffer file type is changed, e.g. .cgi"""
        if isPythonMime(newFileType):
            # The file became a python one
            if uuid not in self.__flakesResults:
                self.__onTabChanged(-1)
        else:
            if uuid in self.__flakesResults:
                # It's not a python file any more
                if uuid == self.__currentUUID:
                    self.__currentUUID = None

                del self.__flakesResults[uuid]
                self.setFlakesNotAvailable(self.__uiLabel)

    def __showPyflakesContextMenu(self, pos):
        """Triggered when the icon context menu is requested"""
        if self.__currentUUID is None:
            return
        if self.__currentUUID not in self.__flakesResults:
            return

        messages = self.__flakesResults[self.__currentUUID].messages
        if not messages:
            return

        # Check that there is at least one non -1 lineno message
        foundLinedMessage = False
        for item in messages:
            if item[1] != -1:
                foundLinedMessage = True
                break
        if not foundLinedMessage:
            return

        # OK, we have something to show
        contextMenu = QMenu(self.__uiLabel)
        for item in messages:
            act = contextMenu.addAction(
                getIcon('pyflakesmsgmarker.png'),
                "Line " + str(item[1]) + ": " + item[0])
            act.setData(QVariant(item[1]))
        contextMenu.triggered.connect(self.__onContextMenu)
        contextMenu.popup(self.__uiLabel.mapToGlobal(pos))

    def __onContextMenu(self, act):
        """Triggered when a context menu item is selected"""
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return

        lineNum, isOK = act.data().toInt()
        if not isOK:
            return

        self.__editorsManager.jumpToLine(lineNum)

    def __jumpToFirstMessage(self):
        """Double click on the icon"""
        if self.__currentUUID is None:
            return
        if self.__currentUUID not in self.__flakesResults:
            return

        messages = self.__flakesResults[self.__currentUUID].messages
        if not messages:
            return

        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return

        linedIndex = -1
        for index in range(len(messages)):
            if messages[index][1] != -1:
                linedIndex = index
                break

        if linedIndex != -1:
            self.__editorsManager.jumpToLine(messages[linedIndex][1])

    @staticmethod
    def setFlakesResults(label, results, editor):
        """Displays the appropriate icon:
           - pyflakes has no complains
           - pyflakes found errors
        """
        if editor is not None:
            editor.clearPyflakesMessages()

        if results:
            # There are complains
            complains = "File checked: there are pyflakes complains<br>"
            for item in results:
                if complains:
                    complains += "<br/>"
                msg = item[0]
                lineno = item[1]
                if lineno == -1:
                    # Special case: compilation error
                    complains += cgi.escape(msg)
                else:
                    complains += "Line " + str(lineno) + ": " + cgi.escape(msg)
                if editor is not None and lineno != -1:
                    # item[ 1 ] -> lineno, -1 is a special case for the
                    # buffer compilation problems
                    editor.addPyflakesMessage(lineno, msg)
            label.setToolTip(complains.replace(' ', '&nbsp;'))
            label.setPixmap(getPixmap('flakeserrors.png'))
        else:
            # There are no complains
            label.setToolTip("File checked: no pyflakes complains")
            label.setPixmap(getPixmap('flakesok.png'))

    @staticmethod
    def setFlakesWaiting(label):
        """Displays the appropriate icon that pyflakes is waiting
           for a time slice to start checking
        """
        label.setToolTip("File is modified: "
                         "pyflakes is waiting for time slice")
        label.setPixmap(getPixmap('flakesmodified.png'))

    @staticmethod
    def setFlakesNotAvailable(label):
        """Displays the appropriate icon that pyflakes is not available"""
        label.setToolTip("Not a python file: pyflakes is sleeping")
        label.setPixmap(getPixmap('flakessleep.png'))
