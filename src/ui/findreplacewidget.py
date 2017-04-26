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
from utils.diskvaluesrelay import getFindHistory, setFindHistory
from .qt import (QHBoxLayout, QToolButton, QLabel, QSizePolicy, QComboBox,
                 QGridLayout, QWidget, QCheckBox, QKeySequence, Qt, QSize,
                 QEvent, pyqtSignal, QPalette, QObject)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class ComboBoxNoUndo(QComboBox):

    """Combo box which allows application wide Ctrl+Z etc."""

    sigNext = pyqtSignal()
    sigPrevious = pyqtSignal()

    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.setEditable(True)

    def event(self, event):
        """Skips the Undo/Redo shortcuts.
           They should be processed by the editor
        """
        if event.type() == QEvent.ShortcutOverride:
            if event.matches(QKeySequence.Undo):
                return False
            if event.matches(QKeySequence.Redo):
                return False
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if key in [Qt.Key_Enter, Qt.Key_Return]:
                if modifiers == Qt.NoModifier:
                    self.sigNext.emit()
                else:
                    self.sigPrevious.emit()
                return False
            if modifiers == Qt.ControlModifier:
                if key == Qt.Key_Comma:
                    self.sigPrevious.emit()
                    return False
                if key == Qt.Key_Period:
                    self.sigNext.emit()
                    return False
        return QComboBox.event(self, event)


class FindReplaceWidget(QWidget):

    """Find and replace widgets"""

    sigIncSearchDone = pyqtSignal(bool)

    MODE_FIND = 0
    MODE_REPLACE = 1

    # Background colors
    BG_IDLE = 0
    BG_NOMATCH = 1
    BG_MATCH = 2
    BG_BROKEN = 3

    def __init__(self, editorsManager, parent=None):
        QWidget.__init__(self, parent)

        self.__maxEntries = Settings()['maxSearchEntries']

        self.editorsManager = editorsManager
        self.__editor = None
        self.__subscribedToCursor = False

        self.__createLayout()
        self.__changesConnected = False
        self.__connectOnChanges()

        self.__history = getFindHistory()
        self.__populateHistory()

        # Incremental search support
        self.__startPoint = None    # {'absPos': int, 'firstVisible': int}

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

        self.__stateColors = {
            self.BG_IDLE:
                self.findtextCombo.lineEdit().palette().color(QPalette.Base),
            self.BG_NOMATCH:
                GlobalData().skin['findNoMatchPaper'],
            self.BG_MATCH:
                GlobalData().skin['findMatchPaper'],
            self.BG_BROKEN:
                GlobalData().skin['findInvalidPaper']}

    def __setBackgroundColor(self, state):
        """Sets the search combo background color to reflect the state"""
        widget = self.findtextCombo.lineEdit()
        color = self.__stateColors[state]
        if state != self.BG_IDLE:
            color.setAlpha(100)

        palette = widget.palette()
        palette.setColor(widget.backgroundRole(), color)
        widget.setPalette(palette)

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
        self.findtextCombo.setInsertPolicy(QComboBox.InsertAtTop)
        self.findtextCombo.setCompleter(None)
        self.findtextCombo.setDuplicatesEnabled(False)
        self.findtextCombo.setEnabled(False)
        self.findtextCombo.sigNext.connect(self.__onNext)
        self.findtextCombo.sigPrevious.connect(self.__onPrev)

        self.findPrevButton = QToolButton(self)
        self.findPrevButton.setToolTip("Previous match (Ctrl+,)")
        self.findPrevButton.setIcon(getIcon("1leftarrow.png"))
        self.findPrevButton.setIconSize(QSize(24, 16))
        self.findPrevButton.setFocusPolicy(Qt.NoFocus)
        self.findPrevButton.setEnabled(False)
        self.findPrevButton.clicked.connect(self.__onPrev)

        self.findNextButton = QToolButton(self)
        self.findNextButton.setToolTip("Next match (Ctrl+.)")
        self.findNextButton.setIcon(getIcon("1rightarrow.png"))
        self.findNextButton.setIconSize(QSize(24, 16))
        self.findNextButton.setFocusPolicy(Qt.NoFocus)
        self.findNextButton.setEnabled(False)
        self.findNextButton.clicked.connect(self.__onNext)

        self.caseCheckBox = QCheckBox(self)
        self.caseCheckBox.setText("Match case")
        self.caseCheckBox.setFocusPolicy(Qt.NoFocus)
        self.caseCheckBox.setEnabled(False)

        self.wordCheckBox = QCheckBox(self)
        self.wordCheckBox.setText("Whole word")
        self.wordCheckBox.setFocusPolicy(Qt.NoFocus)
        self.wordCheckBox.setEnabled(False)

        self.regexpCheckBox = QCheckBox(self)
        self.regexpCheckBox.setText("Regexp")
        self.regexpCheckBox.setFocusPolicy(Qt.NoFocus)
        self.regexpCheckBox.setEnabled(False)


        # Replace UI elements
        self.replaceLabel = QLabel("Replace:", self)

        self.replaceCombo = ComboBoxNoUndo(self)

        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.replaceCombo.sizePolicy().hasHeightForWidth())
        self.replaceCombo.setSizePolicy(sizePolicy)
        self.replaceCombo.setInsertPolicy(QComboBox.InsertAtTop)
        self.replaceCombo.setCompleter(None)
        self.replaceCombo.setDuplicatesEnabled(False)
        self.replaceCombo.setEnabled(False)

        self.replaceButton = QToolButton(self)
        self.replaceButton.setToolTip("Replace current match")
        self.replaceButton.setIcon(getIcon("replace.png"))
        self.replaceButton.setEnabled(False)
        self.replaceButton.clicked.connect(self.__onReplace)
        self.replaceButton.setIconSize(QSize(24, 16))

        self.replaceAllButton = QToolButton(self)
        self.replaceAllButton.setToolTip("Replace all matches")
        self.replaceAllButton.setIcon(getIcon("replace-all.png"))
        self.replaceAllButton.setIconSize(QSize(24, 16))
        self.replaceAllButton.setEnabled(False)
        self.replaceAllButton.clicked.connect(self.__onReplaceAll)

        self.replaceAndMoveButton = QToolButton(self)
        self.replaceAndMoveButton.setToolTip(
            "Replace current match and move to the next one")
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
            self.__history = getFindHistory()
            self.__populateHistory()

    def __serialize(self):
        """Sirializes a current search/replace parameters"""
        termText = self.findtextCombo.currentText()
        if self.replaceCombo.isVisible():
            replaceText = self.replaceCombo.currentText()
        else:
            replaceText = ''

        return {'term': termText,
                'replace': replaceText,
                'cbCase': self.caseCheckBox.isChecked(),
                'cbWord': self.wordCheckBox.isChecked(),
                'cbRegexp': self.regexpCheckBox.isChecked()}

    def __deserialize(self, item):
        """Deserializes the history item"""
        self.__disconnectOnChanges()
        self.findtextCombo.setEditText(item['term'])
        self.replaceCombo.setEditText(item['replace'])
        self.caseCheckBox.setChecked(item['cbCase'])
        self.wordCheckBox.setChecked(item['cbWord'])
        self.regexpCheckBox.setChecked(item['cbRegexp'])
        self.__connectOnChanges()

    def __connectOnChanges(self):
        """Connects all the UI controls to their on change handlers"""
        if not self.__changesConnected:
            self.findtextCombo.editTextChanged.connect(
                self.__onCriteriaChanged)
            self.findtextCombo.currentIndexChanged[int].connect(
                self.__onfindIndexChanged)
            self.caseCheckBox.stateChanged.connect(self.__onCriteriaChanged)
            self.wordCheckBox.stateChanged.connect(self.__onCriteriaChanged)
            self.regexpCheckBox.stateChanged.connect(self.__onCriteriaChanged)
            self.__changesConnected = True

    def __disconnectOnChanges(self):
        """Disconnects all the UI controls from their on change handlers"""
        if self.__changesConnected:
            self.findtextCombo.editTextChanged.disconnect(
                self.__onCriteriaChanged)
            self.findtextCombo.currentIndexChanged[int].disconnect(
                self.__onfindIndexChanged)
            self.caseCheckBox.stateChanged.disconnect(self.__onCriteriaChanged)
            self.wordCheckBox.stateChanged.disconnect(self.__onCriteriaChanged)
            self.regexpCheckBox.stateChanged.disconnect(
                self.__onCriteriaChanged)
            self.__changesConnected = False

    def __populateHistory(self):
        """Populates the history"""
        self.__disconnectOnChanges()
        index = 0
        for props in self.__history:
            self.findtextCombo.addItem(props['term'], index)
            self.replaceCombo.addItem(props['replace'])
            index += 1
        self.__connectOnChanges()

    def __historyIndexByFindText(self, text):
        """Provides the history index by the find text"""
        if text:
            for index in range(self.findtextCombo.count()):
                if self.findtextCombo.itemText(index) == text:
                    return index, self.findtextCombo.itemData(index)
        return None, None

    def __updateHistory(self):
        """Updates history if needed"""
        # Add entries to the combo box if required
        self.__disconnectOnChanges()
        currentText = self.findtextCombo.currentText()
        historyItem = self.__serialize()
        _, historyIndex = self.__historyIndexByFindText(currentText)
        if historyIndex is not None:
            self.__history[historyIndex] = historyItem
        else:
            self.__history.insert(0, historyItem)
            if len(self.__history) > self.__maxEntries:
                self.__history = self.__history[:self.__maxEntries]

        self.findtextCombo.clear()
        self.replaceCombo.clear()
        self.__populateHistory()

        self.__disconnectOnChanges()
        comboIndex, _ = self.__historyIndexByFindText(currentText)
        self.findtextCombo.setCurrentIndex(comboIndex)
        self.__connectOnChanges()

        # Save the combo values for further usage
        setFindHistory(self.__history)

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
        self.__unsubscribeFromCursorChangePos()
        currentWidget = self.editorsManager.currentWidget()
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        if currentWidget.getType() not in validWidgets:
            self.__editor = None
            self.__disableAll()
            return

        self.__editor = currentWidget.getEditor()
        self.__editor.resetHighlight()
        self.__startPoint = None

        self.findtextCombo.setEnabled(True)
        self.caseCheckBox.setEnabled(True)
        self.wordCheckBox.setEnabled(True)
        self.regexpCheckBox.setEnabled(True)

        criteriaValid = self.__isCriteriaValid()
        if criteriaValid:
            self.__setBackgroundColor(self.BG_IDLE)

        self.findPrevButton.setEnabled(criteriaValid)
        self.findNextButton.setEnabled(criteriaValid)

        self.replaceCombo.setEnabled(True)
        self.replaceButton.setEnabled(False)
        self.replaceAndMoveButton.setEnabled(False)
        self.replaceAllButton.setEnabled(criteriaValid)

    def __isCriteriaValid(self):
        """True if the search criteria is valid"""
        if self.findtextCombo.currentText() != "":
            valid, _ = self.__isSearchRegexpValid()
            if valid:
                return True
        return False

    def show(self, mode, text=''):
        """Overridden show method"""
        self.__disconnectOnChanges()
        self.findtextCombo.clear()
        self.replaceCombo.clear()
        self.regexpCheckBox.setChecked(False)
        self.caseCheckBox.setChecked(False)
        self.wordCheckBox.setChecked(False)

        self.__populateHistory()

        self.__disconnectOnChanges()
        self.findtextCombo.setEditText(text)
        self.findtextCombo.lineEdit().selectAll()
        self.__connectOnChanges()

        replaceVisible = mode == self.MODE_REPLACE
        self.replaceLabel.setVisible(replaceVisible)
        self.replaceCombo.setVisible(replaceVisible)
        self.replaceButton.setVisible(replaceVisible)
        self.replaceAndMoveButton.setVisible(replaceVisible)
        self.replaceAllButton.setVisible(replaceVisible)

        QWidget.show(self)
        self.activateWindow()

        if self.__editor is not None:
            # Even if the cursor is in a middle of a word, the Ctrl+F does not
            # move to the next match. It is done in the editorsmanager handler.
            # When a search is initiated the cursor is moved to the begiining
            # of a word if so. Thus, here we always start to search forward
            # without jumping to the next match.
            self.__performSearch(True, True)

        if mode == self.MODE_REPLACE:
            self.replaceCombo.setFocus()
        else:
            self.findtextCombo.setFocus()

        self.__subscribeToCursorChangePos()

    def hide(self):
        """Overriden hide method"""
        self.__unsubscribeFromCursorChangePos()
        QWidget.hide(self)

    def __onCriteriaChanged(self, _):
        """Triggered when the search text or a checkbox state changed"""
        self.__performSearch(True, True)

    def __onReplaceAll(self):
        """Triggered when replace all button is clicked"""
        if self.replaceCombo.isVisible():
            if self.replaceAllButton.isEnabled():
                replaceText = self.replaceCombo.currentText()
                self.__editor.replaceAllMatches(replaceText)
                self.__cursorPositionChanged()
                self.__updateHistory()

    def __onReplace(self):
        """Triggered when replace current match button is clicked"""
        if not self.replaceCombo.isVisible():
            return
        if not self.replaceButton.isEnabled():
            return

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
        if not self.replaceCombo.isVisible():
            return
        if not self.replaceAndMoveButton.isEnabled():
            return

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
            self.__setBackgroundColor(self.BG_BROKEN)
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

    def __moveToStartPoint(self):
        """Moves the editor cursor to the start point"""
        if self.__editor is not None and self.__startPoint is not None:
            self.__editor.absCursorPosition = self.__startPoint['absPos']
            self.__editor.setFirstVisible(self.__startPoint['firstVisible'])

    def __performSearch(self, fromScratch, forward, absPos=None):
        """Performs the incremental search"""
        print("Perform search: scratch: " + str(fromScratch) + " forward: " + str(forward) + " start pos: " + str(absPos))
        import traceback
        traceback.print_stack()
        if self.__editor is None:
            return

        if self.__startPoint is None:
            self.__setStartPoint()

        valid, err = self.__isSearchRegexpValid()
        if not valid:
            self.__onInvalidCriteria(fromScratch)
            GlobalData().mainWindow.showStatusBarMessage(err, 8000)
            self.sigIncSearchDone.emit(False)
            self.__moveToStartPoint()
            return

        if self.findtextCombo.currentText() == '':
            self.__onInvalidCriteria(fromScratch)
            self.sigIncSearchDone.emit(False)
            self.__setBackgroundColor(self.BG_IDLE)
            self.__moveToStartPoint()
            return

        self.__onValidCriteria()

        if fromScratch:
            # Brand new editor to search in
            self.__setStartPoint()
            startPos = self.__editor.absCursorPosition
            if absPos is not None:
                startPos = absPos
            count = self.__editor.highlightRegexp(self.__getRegexp(),
                                                  startPos, forward)
        else:
            startPos = self.__startPoint['absPos']
            if absPos is not None:
                startPos = absPos
            count = self.__editor.highlightRegexp(self.__getRegexp(),
                                                  startPos, forward)
            if count == 0:
                self.__moveToStartPoint()
        self.sigIncSearchDone.emit(count > 0)
        self.__setBackgroundColor(self.BG_MATCH if count > 0
                                  else self.BG_NOMATCH)

    def __onNext(self):
        """Triggered when the find next is clicked"""
        if self.__onPrevNext():
            self.__performSearch(False, True,
                                 self.__editor.absCursorPosition + 1)
            self.__updateHistory()

    def __onPrev(self):
        """Triggered when the find prev is clicked"""
        if self.__onPrevNext():
            self.__performSearch(False, False,
                                 self.__editor.absCursorPosition - 1)
            self.__updateHistory()

    def __onPrevNext(self):
        """Checks prerequisites. Returns True if the search could be done"""
        txt = self.findtextCombo.currentText()
        if txt == "" or self.__editor is None:
            return False

        currentWidget = self.editorsManager.currentWidget()
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        return currentWidget.getType() in validWidgets

    def __setStartPoint(self):
        """Sets the new start point"""
        if self.__editor:
            self.__startPoint = {
                'absPos': self.__editor.absCursorPosition,
                'firstVisible': self.__editor.firstVisibleLine()}

    def __onfindIndexChanged(self, index):
        """Index in history has changed"""
        if index != -1:
            historyIndex = self.findtextCombo.itemData(index)
            if historyIndex is not None:
                self.__deserialize(self.__history[historyIndex])
            else:
                self.__updateHistory()

    def __subscribeToCursorChangePos(self):
        """Subscribes for the cursor position notification"""
        if not self.__subscribedToCursor:
            if self.__editor:
                self.__editor.cursorPositionChanged.connect(
                    self.__cursorPositionChanged)
                self.__subscribedToCursor = True

    def __unsubscribeFromCursorChangePos(self):
        """Unsubscribes from the cursor position notification"""
        if self.__subscribedToCursor:
            if self.__editor:
                try:
                    self.__editor.cursorPositionChanged.disconnect(
                        self.__cursorPositionChanged)
                except:
                    pass
            self.__subscribedToCursor = False

    def __cursorPositionChanged(self):
        """Triggered when the cursor position is changed"""
        if self.replaceCombo.isVisible():
            onMatch = self.__editor.isCursorOnMatch()

            self.replaceButton.setEnabled(onMatch)
            self.replaceAndMoveButton.setEnabled(onMatch)

            self.replaceAllButton.setEnabled(
                self.__isCriteriaValid() and
                self.__editor.getCurrentMatchesCount() > 0)
