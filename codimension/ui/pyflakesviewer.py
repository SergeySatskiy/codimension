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

from html import escape
from utils.pixmapcache import getIcon, getPixmap
from utils.fileutils import isPythonMime, isPythonFile
from analysis.ierrors import getBufferErrors
from radon.complexity import cc_rank
from .qt import QTimer, QObject, Qt, QMenu
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


COMPLEXITY_PIXMAPS = {
    'A': 'complexity-a.png',
    'B': 'complexity-b.png',
    'C': 'complexity-c.png',
    'D': 'complexity-d.png',
    'E': 'complexity-e.png',
    'F': 'complexity-f.png'}



class PyflakesAttributes:

    """Holds all the attributes associated with pyflakes results"""

    def __init__(self):
        self.messages = []      # Complains
        self.ccMessages = []
        self.changed = False

    def hasComplains(self):
        """True if there are any complains"""
        if self.messages:
            return True
        return False


class PyflakesViewer(QObject):

    """The pyflakes viewer"""

    def __init__(self, editorsManager, uiLabel, ccLabel, parent=None):
        QObject.__init__(self, parent)

        self.__editorsManager = editorsManager
        self.__uiLabel = uiLabel
        self.__ccLabel = ccLabel
        self.setAnalysisNotAvailable(self.__uiLabel, self.__ccLabel)

        self.__editorsManager.currentChanged.connect(self.__onTabChanged)
        self.__editorsManager.sigTabClosed.connect(self.__onTabClosed)
        self.__editorsManager.sigBufferSavedAs.connect(self.__onSavedBufferAs)
        self.__editorsManager.sigFileTypeChanged.connect(
            self.__onFileTypeChanged)

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

        # Context menu for the CC icon
        self.__ccLabel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.__ccLabel.customContextMenuRequested.connect(
            self.__showCCContextMenu)

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
            self.setAnalysisNotAvailable(self.__uiLabel, self.__ccLabel)
            return

        if widget.getType() not in [MainWindowTabWidgetBase.PlainTextEditor,
                                    MainWindowTabWidgetBase.VCSAnnotateViewer]:
            self.__currentUUID = None
            self.setAnalysisNotAvailable(self.__uiLabel, self.__ccLabel)
            return

        # This is text editor, detect the file type
        if not isPythonMime(widget.getMime()):
            self.__currentUUID = None
            self.setAnalysisNotAvailable(self.__uiLabel, self.__ccLabel)
            return

        # This is a python file, check if we already have the parsed info in
        # the cache
        uuid = widget.getUUID()
        self.__currentUUID = uuid
        if uuid in self.__flakesResults:
            # We have it, change the icon and the tooltip correspondingly
            results = self.__flakesResults[uuid].messages
            ccResults = self.__flakesResults[uuid].ccMessages
            self.setAnalysisResults(self.__uiLabel, results,
                                    self.__ccLabel, ccResults, None)
            return

        # It is first time we are here, create a new
        editor = widget.getEditor()
        editor.textChanged.connect(self.__onBufferChanged)
        editor.cursorPositionChanged.connect(self.__cursorPositionChanged)

        results, ccResults = getBufferErrors(editor.text)
        attributes = PyflakesAttributes()
        attributes.messages = results
        attributes.ccMessages = ccResults
        attributes.changed = False
        self.__flakesResults[uuid] = attributes
        self.__currentUUID = uuid

        self.setAnalysisResults(self.__uiLabel, results,
                                self.__ccLabel, ccResults, editor)

    def __cursorPositionChanged(self):
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
        if self.parent().debugMode:
            return

        self.__updateTimer.stop()
        if self.__currentUUID in self.__flakesResults:
            if not self.__flakesResults[self.__currentUUID].changed:
                self.__flakesResults[self.__currentUUID].changed = True
                self.setAnalysisWaiting(self.__uiLabel, self.__ccLabel)
        self.__updateTimer.start(1500)

    def __updateView(self):
        """Updates the view when a file is changed"""
        self.__updateTimer.stop()
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return

        if not self.__flakesResults[self.__currentUUID].changed:
            return

        editor = widget.getEditor()
        results, ccResults = getBufferErrors(editor.text)

        self.__flakesResults[self.__currentUUID].messages = results
        self.__flakesResults[self.__currentUUID].ccMessages = ccResults
        self.__flakesResults[self.__currentUUID].changed = False

        self.setAnalysisResults(self.__uiLabel, results,
                                self.__ccLabel, ccResults, editor)

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
                self.setAnalysisNotAvailable(self.__uiLabel, self.__ccLabel)

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered when the current buffer file type is changed, e.g. .cgi"""
        del fileName    # unused argument
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
                self.setAnalysisNotAvailable(self.__uiLabel, self.__ccLabel)

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
        lineNumbers = list(messages.keys())
        for lineno in lineNumbers:
            if lineno > 0:
                break
        else:
            return

        # OK, we have something to show
        lineNumbers.sort()
        contextMenu = QMenu(self.__uiLabel)
        for lineno in lineNumbers:
            if lineno > 0:
                for item in messages[lineno]:
                    act = contextMenu.addAction(
                        getIcon('pyflakesmsgmarker.png'),
                        "Line " + str(lineno) + ": " + item)
                    act.setData(lineno)
        contextMenu.triggered.connect(self.__onContextMenu)
        contextMenu.popup(self.__uiLabel.mapToGlobal(pos))

    def __showCCContextMenu(self, pos):
        """Triggered when the cc icon context menu is requested"""
        if self.__currentUUID is None:
            return
        if self.__currentUUID not in self.__flakesResults:
            return

        count = 0
        contextMenu = QMenu(self.__ccLabel)
        for item in self.__flakesResults[self.__currentUUID].ccMessages:
            complexity = cc_rank(item.complexity)

            if complexity != 'A':
                count += 1
                title = complexity + '(' + str(item.complexity) + ') ' + \
                        item.fullname
                if item.letter in ('F', 'M'):
                    title += '()'
                act = contextMenu.addAction(getIcon('ccmarker.png'), title)
                act.setData(item.lineno)
        if count > 0:
            contextMenu.triggered.connect(self.__onContextMenu)
            contextMenu.popup(self.__ccLabel.mapToGlobal(pos))
        else:
            del contextMenu

    def __onContextMenu(self, act):
        """Triggered when a context menu item is selected"""
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget:
            self.__editorsManager.jumpToLine(act.data())

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
        if widget:
            lineNumbers = list(messages.keys())
            lineNumbers.sort()
            for lineno in lineNumbers:
                if lineno > 0:
                    self.__editorsManager.jumpToLine(lineno)
                    break

    @staticmethod
    def setAnalysisResults(label, results, ccLabel, ccResults, editor):
        """Displays the appropriate icon:

        - pyflakes has no complains
        - pyflakes found errors
        """
        if editor is not None:
            editor.clearAnalysisMessages()
            editor.setAnalysisMessages(results, ccResults)

        if results:
            # There are complains
            complains = "Buffer checked: there are pyflakes complains<br/>"
            lineNumbers = list(results.keys())
            lineNumbers.sort()
            for lineNo in lineNumbers:
                for item in results[lineNo]:
                    complains += '<br/>'
                    if lineNo == -1:
                        # Special case: compilation error
                        complains += escape(item)
                    else:
                        complains += "Line " + str(lineNo) + \
                                     ": " + escape(item)
            label.setToolTip(complains.replace(' ', '&nbsp;'))
            label.setPixmap(getPixmap('flakeserrors.png'))
        else:
            # There are no complains
            label.setToolTip('Buffer checked: no pyflakes complains')
            label.setPixmap(getPixmap('flakesok.png'))

        if ccResults:
            complains = 'Buffer cyclomatic complexity:<br/>'
            worstComplexity = 'A'
            for item in ccResults:
                complexity = cc_rank(item.complexity)
                worstComplexity = max(complexity, worstComplexity)

                if complexity != 'A':
                    complains += '<br/>' + complexity + \
                                 '(' + str(item.complexity) + ') ' + \
                                 escape(item.fullname)
                    if item.letter in ('F', 'M'):
                        complains += '()'

            if worstComplexity == 'A':
                ccLabel.setToolTip('Buffer cyclomatic complexity: no complains')
            else:
                ccLabel.setToolTip(complains.replace(' ', '&nbsp;'))
            ccLabel.setPixmap(getPixmap(COMPLEXITY_PIXMAPS[worstComplexity]))
        else:
            ccLabel.setToolTip('No complexity information available')
            ccLabel.setPixmap(getPixmap('ccmarker.png'))

    @staticmethod
    def setAnalysisWaiting(label, ccLabel):
        """Displays the waiting for a time slice to start checking icon"""
        label.setToolTip('File is modified: '
                         'pyflakes is waiting for time slice')
        label.setPixmap(getPixmap('flakesmodified.png'))

        ccLabel.setToolTip('File is modified: '
                           'radon is waiting for time slice')
        ccLabel.setPixmap(getPixmap('flakesmodified.png'))

    @staticmethod
    def setAnalysisNotAvailable(label, ccLabel):
        """Displays the appropriate icon that pyflakes is not available"""
        label.setToolTip('Not a python file: pyflakes is sleeping')
        label.setPixmap(getPixmap('flakessleep.png'))

        ccLabel.setToolTip('Not a python file: radon is sleeping')
        ccLabel.setPixmap(getPixmap('flakessleep.png'))
