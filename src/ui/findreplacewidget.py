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

"""Find and replace widgets implementation"""

import re
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from utils.project import CodimensionProject
from utils.diskvaluesrelay import (getFindHistory, setFindHistory)
from .qt import (QHBoxLayout, QToolButton, QLabel, QSizePolicy, QComboBox,
                 QGridLayout, QWidget, QCheckBox, QKeySequence, Qt, QSize,
                 QEvent, pyqtSignal)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class ComboBoxNoUndo(QComboBox):

    """Combo box which allows application wide Ctrl+Z etc."""

    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)

    def event(self, event):
        """Skips the Undo/Redo shortcuts.
           They should be processed by the editor
        """
        if event.type() == QEvent.ShortcutOverride:
            if event.matches(QKeySequence.Undo):
                return False
            if event.matches(QKeySequence.Redo):
                return False
        return QComboBox.event(self, event)


class FindReplaceWidget(QWidget):

    """Find and replace widgets"""

    sigIncSearchDone = pyqtSignal(bool)

    MODE_FIND = 0
    MODE_REPLACE = 1

    def __init__(self, editorsManager, parent=None):
        QWidget.__init__(self, parent)
        self.__skip = True

        self.__maxHistory = Settings()['maxSearchEntries']

        self.editorsManager = editorsManager
        self.__editor = None

        self.__createLayout()
        self.findHistory = getFindHistory()
        self.__populateHistory()

        self.__forward = True

        # Incremental search support
        self.__startPoint = None    # {'absPos': int, 'firstVisible': int}

        self.__skip = False
        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

    def __createLayout(self):
        """Creates the layout of the widget"""
        self.closeButton = QToolButton(self)
        self.closeButton.setToolTip("Close the dialog (ESC)")
        self.closeButton.setIcon(getIcon("close.png"))
        self.closeButton.clicked.connect(self.hide)

        self.findLabel = QLabel("Find:", self)

        self.findtextCombo = ComboBoxNoUndo(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.findtextCombo.sizePolicy().hasHeightForWidth())
        self.findtextCombo.setSizePolicy(sizePolicy)
        self.findtextCombo.setEditable(True)
        self.findtextCombo.setInsertPolicy(QComboBox.InsertAtTop)
        self.findtextCombo.setCompleter(None)
        self.findtextCombo.setDuplicatesEnabled(False)
        self.findtextCombo.setEnabled(False)
        self.findtextCombo.editTextChanged.connect(self.__onEditTextChanged)

        self.findPrevButton = QToolButton(self)
        self.findPrevButton.setToolTip("Previous occurrence (Ctrl+,)")
        self.findPrevButton.setIcon(getIcon("1leftarrow.png"))
        self.findPrevButton.setIconSize(QSize(24, 16))
        self.findPrevButton.setFocusPolicy(Qt.NoFocus)
        self.findPrevButton.setEnabled(False)
        self.findPrevButton.clicked.connect(self.__onPrev)


        self.findNextButton = QToolButton(self)
        self.findNextButton.setToolTip("Next occurrence (Ctrl+.)")
        self.findNextButton.setIcon(getIcon("1rightarrow.png"))
        self.findNextButton.setIconSize(QSize(24, 16))
        self.findNextButton.setFocusPolicy(Qt.NoFocus)
        self.findNextButton.setEnabled(False)
        self.findNextButton.clicked.connect(self.__onNext)

        self.caseCheckBox = QCheckBox(self)
        self.caseCheckBox.setText("Match case")
        self.caseCheckBox.setFocusPolicy(Qt.NoFocus)
        self.caseCheckBox.setEnabled(False)
        self.caseCheckBox.stateChanged.connect(self.__onCheckBoxChange)

        self.wordCheckBox = QCheckBox(self)
        self.wordCheckBox.setText("Whole word")
        self.wordCheckBox.setFocusPolicy(Qt.NoFocus)
        self.wordCheckBox.setEnabled(False)
        self.wordCheckBox.stateChanged.connect(self.__onCheckBoxChange)

        self.regexpCheckBox = QCheckBox(self)
        self.regexpCheckBox.setText("Regexp")
        self.regexpCheckBox.setFocusPolicy(Qt.NoFocus)
        self.regexpCheckBox.setEnabled(False)
        self.regexpCheckBox.stateChanged.connect(self.__onCheckBoxChange)

        self.findtextCombo.lineEdit().returnPressed.connect(
            self.__findByReturnPressed)

        # Replace UI elements
        self.replaceLabel = QLabel("Replace:", self)

        self.replaceCombo = ComboBoxNoUndo(self)

        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.replaceCombo.sizePolicy().hasHeightForWidth())
        self.replaceCombo.setSizePolicy(sizePolicy)
        self.replaceCombo.setEditable(True)
        self.replaceCombo.setInsertPolicy(QComboBox.InsertAtTop)
        self.replaceCombo.setCompleter(None)
        self.replaceCombo.setDuplicatesEnabled(False)
        self.replaceCombo.setEnabled(False)

        self.replaceButton = QToolButton(self)
        self.replaceButton.setToolTip("Replace current occurrence")
        self.replaceButton.setIcon(getIcon("replace.png"))
        self.replaceButton.setEnabled(False)
        self.replaceButton.clicked.connect(self.__onReplace)
        self.replaceButton.setIconSize(QSize(24, 16))

        self.replaceAllButton = QToolButton(self)
        self.replaceAllButton.setToolTip("Replace all occurrences")
        self.replaceAllButton.setIcon(getIcon("replace-all.png"))
        self.replaceAllButton.setIconSize(QSize(24, 16))
        self.replaceAllButton.setEnabled(False)
        self.replaceAllButton.clicked.connect(self.__onReplaceAll)

        self.replaceAndMoveButton = QToolButton(self)
        self.replaceAndMoveButton.setToolTip(
            "Replace current occurrence and move to the next match")
        self.replaceAndMoveButton.setIcon(getIcon("replace-move.png"))
        self.replaceAndMoveButton.setIconSize(QSize(24, 16))
        self.replaceAndMoveButton.setEnabled(False)
        self.replaceAndMoveButton.clicked.connect(self.__onReplaceAndMove)

        # Layout
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        self.gridLayout.addWidget(self.closeButton, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.findLabel, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.findtextCombo, 0, 2, 1, 1)
        self.gridLayout.addWidget(self.findPrevButton, 0, 3, 1, 1)
        self.gridLayout.addWidget(self.findNextButton, 0, 4, 1, 1)
        self.gridLayout.addWidget(self.caseCheckBox, 0, 5, 1, 1)
        self.gridLayout.addWidget(self.wordCheckBox, 0, 6, 1, 1)
        self.gridLayout.addWidget(self.regexpCheckBox, 0, 7, 1, 1)

        self.gridLayout.addWidget(self.replaceLabel, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.replaceCombo, 1, 2, 1, 1)
        self.gridLayout.addWidget(self.replaceButton, 1, 3, 1, 1)
        self.gridLayout.addWidget(self.replaceAndMoveButton, 1, 4, 1, 1)
        self.gridLayout.addWidget(self.replaceAllButton, 1, 5, 1, 1)

        self.setTabOrder(self.findtextCombo, self.replaceCombo)
        self.setTabOrder(self.replaceCombo, self.caseCheckBox)
        self.setTabOrder(self.caseCheckBox, self.wordCheckBox)
        self.setTabOrder(self.wordCheckBox, self.regexpCheckBox)
        self.setTabOrder(self.regexpCheckBox, self.findNextButton)
        self.setTabOrder(self.findNextButton, self.findPrevButton)
        self.setTabOrder(self.findPrevButton, self.replaceAndMoveButton)
        self.setTabOrder(self.replaceButton, self.replaceAllButton)
        self.setTabOrder(self.replaceAndMoveButton, self.replaceAllButton)
        self.setTabOrder(self.replaceAllButton, self.closeButton)

    def keyPressEvent(self, event):
        """Handles the ESC key for the search bar"""
        if event.key() == Qt.Key_Escape:
            self.__startPoint = None
            event.accept()
            self.hide()
            activeWindow = self.editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.__skip = True
            self.findHistory = getFindHistory()
            self.__populateHistory()
            self.__skip = False

    def __populateHistory(self):
        """Populates the history"""


    def __disableAll(self):
        """Disables all the controls"""
        self.findtextCombo.setEnabled(False)
        self.caseCheckBox.setEnabled(False)
        self.wordCheckBox.setEnabled(False)
        self.regexpCheckBox.setEnabled(False)
        self.findPrevButton.setEnabled(False)
        self.findNextButton.setEnabled(False)
        self.replaceButton.setEnabled(False)
        self.replaceAndMoveButton.setEnabled(False)
        self.replaceAllButton.setEnabled(False)
        self.replaceCombo.setEnabled(False)

    def updateStatus(self):
        """Triggered when the current tab is changed"""
        currentWidget = self.editorsManager.currentWidget()
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        if currentWidget.getType() not in validWidgets:
            self.__editor = None
            self.__disableAll()
            return

        self.__editor = currentWidget.getEditor()

        self.findtextCombo.setEnabled(True)
        self.caseCheckBox.setEnabled(True)
        self.wordCheckBox.setEnabled(True)
        self.regexpCheckBox.setEnabled(True)

        criteriaValid = False
        if self.findtextCombo.currentText() != "":
            valid, _ = self.__isSearchRegexpValid()
            if valid:
                criteriaValid = True

        self.findPrevButton.setEnabled(criteriaValid)
        self.findNextButton.setEnabled(criteriaValid)
        self.replaceButton.setEnabled(criteriaValid)
        self.replaceAndMoveButton.setEnabled(criteriaValid)
        self.replaceAllButton.setEnabled(criteriaValid)

    def setFocus(self):
        """Overridded setFocus"""
        self.findtextCombo.lineEdit().selectAll()
        self.findtextCombo.setFocus()

    def show(self, mode, text=''):
        """Overridden show method"""
        self.__skip = True
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.findHistory)
        self.findtextCombo.setEditText(text)
        self.findtextCombo.lineEdit().selectAll()
        self.regexpCheckBox.setChecked(False)
        self.findtextCombo.setFocus()
        self.__forward = True
        self.__skip = False

        replaceVisible = mode == self.MODE_REPLACE
        self.replaceLabel.setVisible(replaceVisible)
        self.replaceCombo.setVisible(replaceVisible)
        self.replaceButton.setVisible(replaceVisible)
        self.replaceAndMoveButton.setVisible(replaceVisible)
        self.replaceAllButton.setVisible(replaceVisible)

        QWidget.show(self)
        self.activateWindow()

        self.__performSearch(True)

    def __onCheckBoxChange(self, newState):
        """Triggered when a search check box state is changed"""
        if not self.__skip:
            self.__performSearch(False)

    def __onEditTextChanged(self, text):
        """Triggered when the search text has been changed"""
        if not self.__skip:
            self.__performSearch(False)

    def __onReplaceAll(self):
        """Triggered when replace all button is clicked"""
        text = self.findtextCombo.currentText()
        isRegexp = self.regexpCheckBox.isChecked()
        isCase = self.caseCheckBox.isChecked()
        isWord = self.wordCheckBox.isChecked()
        replaceText = self.replaceCombo.currentText()

        self.__updateReplaceHistory(text, replaceText)

        # Check that there is at least one target to replace
        found = self._editor.findFirstTarget(text,
                                             isRegexp, isCase, isWord, 0, 0)
        if not found:
            GlobalData().mainWindow.showStatusBarMessage(
                "No matches found. Nothing is replaced.")
            return

        # There is something matching
        count = 0
        self._editor.beginUndoAction()
        while found:
            self._editor.replaceTarget(str(replaceText))
            count += 1
            found = self._editor.findNextTarget()
        self._editor.endUndoAction()
        self.replaceButton.setEnabled(False)
        self.replaceAndMoveButton.setEnabled(False)
        self.__replaceCouldBeEnabled = False

        suffix = ""
        if count > 1:
            suffix = "s"
        GlobalData().mainWindow.showStatusBarMessage(
            str(count) + " occurrence" + suffix + " replaced.")
        GlobalData().mainWindow.clearStatusBarMessage(1)

    def __onReplace(self):
        """Triggered when replace current occurrence button is clicked"""
        replaceText = self.replaceCombo.currentText()
        text = self.findtextCombo.currentText()
        isRegexp = self.regexpCheckBox.isChecked()
        isCase = self.caseCheckBox.isChecked()
        isWord = self.wordCheckBox.isChecked()
        searchAttributes = self._searchSupport.get(self._editorUUID)

        self.__updateReplaceHistory(text, replaceText)

        found = self._editor.findFirstTarget(text, isRegexp, isCase, isWord,
                                             searchAttributes.match[0],
                                             searchAttributes.match[1])
        if found:
            if self._editor.replaceTarget(str(replaceText)):
                GlobalData().mainWindow.showStatusBarMessage(
                    "1 occurrence replaced.")
                GlobalData().mainWindow.clearStatusBarMessage(1)
                # Positioning cursor to the end of the replaced text helps
                # to avoid problems of replacing 'text' with 'prefix_text'
                searchAttributes.match[1] += len(replaceText)
                self._editor.cursorPosition = searchAttributes.match[0], \
                                              searchAttributes.match[1]
                self.replaceButton.setEnabled(False)
                self.replaceAndMoveButton.setEnabled(False)
            else:
                GlobalData().mainWindow.showStatusBarMessage(
                    "No occurrences replaced.")
            # This will prevent highlighting the improper editor positions
            searchAttributes.match = [-1, -1, -1]

    def __onReplaceAndMove(self):
        """Triggered when replace-and-move button is clicked"""
        buttonFocused = self.replaceAndMoveButton.hasFocus()
        self.__onReplace()
        self.onNext(False)

        if buttonFocused:
            self.replaceAndMoveButton.setFocus()

    def __getSearchRegexpAndFlags(self):
        """Provides the search regular expression and flags"""
        pattern = self.findtextCombo.currentText()
        pattern = pattern.replace('\u2029', '\n') # unicode paragraph -> \n

        if not self.regexpCheckBox.isChecked():
            pattern = re.escape(pattern)
        if self.wordCheckBox.isChecked():
            pattern = r'\b' + pattern + r'\b'

        flags = 0
        if not self.caseCheckBox.isChecked():
            flags = re.IGNORECASE
        return pattern, flags

    def __getRegexp(self):
        """Provides a compiled regexp"""
        pattern, flags = self.__getSearchRegexpAndFlags()
        return re.compile(pattern, flags)

    def __isSearchRegexpValid(self):
        """Compilation success and error if so"""
        pattern, flags = self.__getSearchRegexpAndFlags()
        try:
            re.compile(pattern, flags)
        except re.error as ex:
            return False, str(ex)
        return True, None

    def __onInvalidCriteria(self, fromScratch):
        """Called when the search criteria is invalid"""
        self.__editor.resetHighlight()

        self.findNextButton.setEnabled(False)
        self.findPrevButton.setEnabled(False)
        self.replaceButton.setEnabled(False)
        self.replaceAndMoveButton.setEnabled(False)
        self.replaceAllButton.setEnabled(False)

        if not fromScratch:
            self.__editor.absCursorPosition = self.__startPoint['absPos']
            self.__editor.setFirstVisible(self.__startPoint['firstVisible'])

    def __onValidCriteria(self):
        """Enables the controls"""
        self.findNextButton.setEnabled(True)
        self.findPrevButton.setEnabled(True)
        self.replaceButton.setEnabled(True)
        self.replaceAndMoveButton.setEnabled(True)
        self.replaceAllButton.setEnabled(True)

    def __performSearch(self, fromScratch):
        """Performs the incremental search"""
        if self.__editor is None:
            return

        valid, err = self.__isSearchRegexpValid()
        if not valid:
            self.__onInvalidCriteria(fromScratch)
            GlobalData().mainWindow.showStatusBarMessage(err, 3000)
            self.sigIncSearchDone.emit(False)
            return

        if self.findtextCombo.currentText() == '':
            self.__onInvalidCriteria(fromScratch)
            self.sigIncSearchDone.emit(False)
            return

        self.__onValidCriteria()

        if fromScratch:
            # Brand new editor to search in
            self.__startPoint = {
                'absPos': self.__editor.absCursorPosition,
                'firstVisible': self.__editor.firstVisibleLine()}

            count = self.__editor.highlightRegexp(
                self.__getRegexp(), self.__editor.absCursorPosition, True)
        else:
            count = self.__editor.highlightRegexp(self.__getRegexp(),
                                                  self.__startPoint['absPos'],
                                                  True)
            if count == 0:
                self.__editor.absCursorPosition = self.__startPoint['absPos']
                self.__editor.setFirstVisible(
                    self.__startPoint['firstVisible'])
        self.sigIncSearchDone.emit(count > 0)

    def __onNext(self):
        """Triggered when the find next is clicked"""
        if not self.__onPrevNext():
            return
        self.__forward = True
        self.sigIncSearchDone.emit(self.__findNextPrev())

    def __onPrev(self):
        """Triggered when the find prev is clicked"""
        if not self.__onPrevNext():
            return
        self.__forward = False
        self.sigIncSearchDone.emit(self.__findNextPrev())

    def __onPrevNext(self):
        """Checks prerequisites. Returns True if the search could be done"""
        txt = self.findtextCombo.currentText()
        if txt == "" or self.__editor is None:
            return False

        currentWidget = self.editorsManager.currentWidget()
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        return currentWidget.getType() in validWidgets

    def __findByReturnPressed(self):
        """Triggered when 'Enter' or 'Return' is clicked"""
        if self.__forward:
            self.onNext()
        else:
            self.onPrev()

    def __findNextPrev(self):
        """Finds the next occurrence of the search text"""
        if self.__editor is None:
            return False

        if self.__forward:
            count = self.__editor.onNextHighlight()
        else:
            count = self.__editor.onPrevHighlight()
        return count > 0


class ReplaceWidget():

    """Find and replace in the current file widget"""

    def __init__(self, editorsManager, parent=None):
        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)
        self.sigIncSearchDone.connect(self.__onSearchDone)
        self.replaceCombo.editTextChanged.connect(self.__onReplaceTextChanged)
        self.replaceCombo.lineEdit().returnPressed.connect(
            self.__onReplaceAndMove)
        self.__connected = False
        self.__replaceCouldBeEnabled = False
        self._skip = False

    def __updateReplaceAllButtonStatus(self):
        """Updates the replace all button status"""
        self.replaceCombo.setEnabled(self._isTextEditor)
        textAvailable = self.findtextCombo.currentText() != ""
        self.replaceAllButton.setEnabled(self._isTextEditor and textAvailable)

    def show(self, text=''):
        """Overriden show method"""
        self._skip = True
        self.replaceCombo.clear()
        self.replaceCombo.addItems(self.replaceHistory)
        self.replaceCombo.setEditText('')
        self._skip = False

        FindReplaceBase.show(self, text)
        self.__subscribeToCursorChangePos()

    def hide(self):
        """Overriden hide method"""
        if self.__connected:
            self.__unsubscribeFromCursorChange()
        FindReplaceBase.hide(self)

    def __onSearchDone(self, found):
        """Triggered when incremental search is done"""
        self.replaceButton.setEnabled(found)
        self.replaceAndMoveButton.setEnabled(found)
        self.replaceAllButton.setEnabled(found)
        self.__replaceCouldBeEnabled = True

    def __onReplaceTextChanged(self, text):
        """Triggered when replace with text is changed"""
        self.__updateReplaceAllButtonStatus()
        self.replaceButton.setEnabled(self.__replaceCouldBeEnabled)
        self.replaceAndMoveButton.setEnabled(self.__replaceCouldBeEnabled)

    def __subscribeToCursorChangePos(self):
        """Subscribes for the cursor position notification"""
        if self._editor is not None:
            self._editor.cursorPositionChanged.connect(
                self.__cursorPositionChanged)
            self.__connected = True

    def __unsubscribeFromCursorChange(self):
        """Unsubscribes from the cursor position notification"""
        if self._editor is not None:
            try:
                self._editor.cursorPositionChanged.disconnect(
                    self.__cursorPositionChanged)
            except:
                pass
            self.__connected = False

    def __cursorPositionChanged(self):
        """Triggered when the cursor position is changed"""
        if self._searchSupport.hasEditor(self._editorUUID):
            line, pos = self._editor.cursorPosition
            searchAttributes = self._searchSupport.get(self._editorUUID)
            enable = line == searchAttributes.match[0] and \
                     pos == searchAttributes.match[1]
        else:
            enable = False

        self.replaceButton.setEnabled(enable)
        self.replaceAndMoveButton.setEnabled(enable)
        self.__replaceCouldBeEnabled = enable

    def __updateReplaceHistory(self, text, replaceText):
        """Updates the history in the project and in the combo boxes"""
        changedWhat = self._addToHistory(self.findtextCombo,
                                         self.findHistory, text)
        changedReplace = self._addToHistory(self.replaceCombo,
                                            self.replaceHistory, replaceText)
        if changedWhat or changedReplace:
            prj = GlobalData().project
            prj.setReplaceHistory(self.findHistory, self.replaceHistory)

    def onNext(self, clearSBMessage=True):
        """Triggered when the find next button is clicked"""
        oldLine = self._currentWidget.getLine()
        oldPos = self._currentWidget.getPos()
        FindReplaceBase.onNext(self, clearSBMessage)
        if oldLine == self._currentWidget.getLine() and \
           oldPos == self._currentWidget.getPos():
            FindReplaceBase.onNext(self, clearSBMessage)

        self.__updateReplaceHistory(self.findtextCombo.currentText(),
                                    self.replaceCombo.currentText())

    def onPrev(self):
        """Triggered when the find previous button is clicked"""
        FindReplaceBase.onPrev(self)
        self.__updateReplaceHistory(self.findtextCombo.currentText(),
                                    self.replaceCombo.currentText())
