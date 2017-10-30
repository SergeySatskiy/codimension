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
from .qt import (QToolButton, QLabel, QSizePolicy, QComboBox,
                 QGridLayout, QWidget, QCheckBox, QKeySequence, Qt, QSize,
                 QEvent, pyqtSignal, QPalette)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class ComboBoxNoUndo(QComboBox):

    """Combo box which allows application wide Ctrl+Z etc."""

    sigNext = pyqtSignal()
    sigPrevious = pyqtSignal()
    sigEnter = pyqtSignal(int)

    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.setEditable(True)

    def event(self, event):
        """Skips the Undo/Redo shortcuts. They're processed by the editor"""
        if event.type() == QEvent.ShortcutOverride:
            if event.matches(QKeySequence.Undo):
                return False
            if event.matches(QKeySequence.Redo):
                return False
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if key in [Qt.Key_Enter, Qt.Key_Return]:
                self.sigEnter.emit(int(modifiers))
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
        self.findtextCombo.setInsertPolicy(QComboBox.NoInsert)
        self.findtextCombo.setCompleter(None)
        self.findtextCombo.setDuplicatesEnabled(False)
        self.findtextCombo.setEnabled(False)
        self.findtextCombo.sigNext.connect(self.onNext)
        self.findtextCombo.sigPrevious.connect(self.onPrev)
        self.findtextCombo.sigEnter.connect(self.__onFindEnter)

        self.findPrevButton = QToolButton(self)
        self.findPrevButton.setToolTip("Previous match (Ctrl+,)")
        self.findPrevButton.setIcon(getIcon("1leftarrow.png"))
        self.findPrevButton.setIconSize(QSize(24, 16))
        self.findPrevButton.setFocusPolicy(Qt.NoFocus)
        self.findPrevButton.setEnabled(False)
        self.findPrevButton.clicked.connect(self.onPrev)

        self.findNextButton = QToolButton(self)
        self.findNextButton.setToolTip("Next match (Ctrl+.)")
        self.findNextButton.setIcon(getIcon("1rightarrow.png"))
        self.findNextButton.setIconSize(QSize(24, 16))
        self.findNextButton.setFocusPolicy(Qt.NoFocus)
        self.findNextButton.setEnabled(False)
        self.findNextButton.clicked.connect(self.onNext)

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
        self.replaceCombo.setInsertPolicy(QComboBox.NoInsert)
        self.replaceCombo.setCompleter(None)
        self.replaceCombo.setDuplicatesEnabled(False)
        self.replaceCombo.setEnabled(False)
        self.replaceCombo.sigNext.connect(self.onNext)
        self.replaceCombo.sigPrevious.connect(self.onPrev)
        self.replaceCombo.sigEnter.connect(self.__onReplaceEnter)

        self.replaceButton = QToolButton(self)
        self.replaceButton.setToolTip("Replace current match")
        self.replaceButton.setIcon(getIcon("replace.png"))
        self.replaceButton.setEnabled(False)
        self.replaceButton.setFocusPolicy(Qt.NoFocus)
        self.replaceButton.clicked.connect(self.__onReplace)
        self.replaceButton.setIconSize(QSize(24, 16))

        self.replaceAllButton = QToolButton(self)
        self.replaceAllButton.setToolTip("Replace all matches")
        self.replaceAllButton.setIcon(getIcon("replace-all.png"))
        self.replaceAllButton.setIconSize(QSize(24, 16))
        self.replaceAllButton.setEnabled(False)
        self.replaceAllButton.setFocusPolicy(Qt.NoFocus)
        self.replaceAllButton.clicked.connect(self.__onReplaceAll)

        self.replaceAndMoveButton = QToolButton(self)
        self.replaceAndMoveButton.setToolTip(
            "Replace current match and move to the next one")
        self.replaceAndMoveButton.setIcon(getIcon("replace-move.png"))
        self.replaceAndMoveButton.setIconSize(QSize(24, 16))
        self.replaceAndMoveButton.setEnabled(False)
        self.replaceAndMoveButton.setFocusPolicy(Qt.NoFocus)
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
        replaceItems = []
        for props in self.__history:
            self.findtextCombo.addItem(props['term'], index)
            replaceItem = props['replace']
            if replaceItem and replaceItem not in replaceItems:
                self.replaceCombo.addItem(props['replace'])
                replaceItems.append(props['replace'])
            index += 1
        self.replaceCombo.addItem('')
        self.__connectOnChanges()

    def __historyIndexByFindText(self, text):
        """Provides the history index by the find text"""
        if text:
            for index in range(self.findtextCombo.count()):
                if self.findtextCombo.itemText(index) == text:
                    return index, self.findtextCombo.itemData(index)
        return None, None

    def __replaceIndex(self, text):
        """Provides the replace combo index by the text"""
        if text is not None:
            for index in range(self.replaceCombo.count()):
                if self.replaceCombo.itemText(index) == text:
                    return index
        return None

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
        comboIndex, historyIndex = self.__historyIndexByFindText(currentText)
        self.findtextCombo.setCurrentIndex(comboIndex)

        replaceText = self.__history[historyIndex]['replace']
        replaceIndex = self.__replaceIndex(replaceText)
        if replaceIndex:
            self.replaceCombo.setCurrentIndex(replaceIndex)
        else:
            self.replaceCombo.setEditText(
                self.__history[historyIndex]['replace'])
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
        self.__setBackgroundColor(self.BG_IDLE)

    def updateStatus(self):
        """Triggered when the current tab is changed"""
        self.__unsubscribeFromEditorSignals()
        currentWidget = self.editorsManager.currentWidget()
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        if currentWidget.getType() not in validWidgets:
            self.__editor = None
            self.__disableAll()
            return

        self.__editor = currentWidget.getEditor()
        self.__editor.onTabChanged()
        self.__startPoint = None

        self.findtextCombo.setEnabled(True)
        self.caseCheckBox.setEnabled(True)
        self.wordCheckBox.setEnabled(True)
        self.regexpCheckBox.setEnabled(True)

        criteriaValid = self.__isCriteriaValid()
        if criteriaValid:
            _, totalMatches = self.__editor.getMatchesInfo()
            if totalMatches is None or totalMatches == 0:
                self.__setBackgroundColor(self.BG_NOMATCH)
            else:
                self.__setBackgroundColor(self.BG_MATCH)
        else:
            self.__setBackgroundColor(self.BG_BROKEN)

        self.findPrevButton.setEnabled(criteriaValid)
        self.findNextButton.setEnabled(criteriaValid)

        self.replaceCombo.setEnabled(True)
        self.replaceButton.setEnabled(False)
        self.replaceAndMoveButton.setEnabled(False)
        self.replaceAllButton.setEnabled(False)
        self.__subscribeToEditorSignals()

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
        if mode == self.MODE_FIND:
            self.findtextCombo.lineEdit().selectAll()
        self.replaceCombo.setEditText('')
        self.replaceCombo.setCurrentIndex(self.__replaceIndex(''))
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

        self.__subscribeToEditorSignals()

    def hide(self):
        """Overriden hide method"""
        self.__unsubscribeFromEditorSignals()
        QWidget.hide(self)

    def onQuickHighlight(self, text, wordFlag, count):
        """Called when the editor receives Ctrl+' or < or >"""
        if self.findtextCombo.isVisible():
            if text:
                self.__disconnectOnChanges()
                self.regexpCheckBox.setChecked(False)
                self.caseCheckBox.setChecked(False)
                self.wordCheckBox.setChecked(wordFlag == 1)
                self.findtextCombo.setEditText(text)
                self.__connectOnChanges()
                self.__setBackgroundColor(self.BG_NOMATCH if count == 0 else
                                          self.BG_MATCH)
                self.findPrevButton.setEnabled(count > 0)
                self.findNextButton.setEnabled(count > 0)
                self.__cursorPositionChanged()

    def __onCriteriaChanged(self, _):
        """Triggered when the search text or a checkbox state changed"""
        # All the opened buffers match cache needs to be reset to trigger
        # re-search next time the user switches the buffer
        self.editorsManager.resetTextSearchMatchCache()

        self.__performSearch(True, True)

    def __appendReplaceMessage(self):
        """Appends a proper message to the status bar after replace"""
        mainWindow = GlobalData().mainWindow
        currentMessage = mainWindow.getCurrentStatusBarMessage()
        currentIndex, totalMatches = self.__editor.getMatchesInfo()
        if totalMatches is None or totalMatches == 0:
            msg = currentMessage + '; no more matches'
        else:
            if currentIndex is not None:
                msg = currentMessage + '; match %d of %d' % (currentIndex,
                                                             totalMatches)
            else:
                if totalMatches == 1:
                    msg = currentMessage + '; 1 match left'
                else:
                    msg = currentMessage + '; %d matches left' % totalMatches
            if totalMatches > Settings()['maxHighlightedMatches']:
                msg += ' (too many to highlight)'

        mainWindow.showStatusBarMessage(msg)

    def __onReplaceAll(self):
        """Triggered when replace all button is clicked"""
        if self.replaceCombo.isVisible():
            if self.replaceAllButton.isEnabled():
                replaceText = self.replaceCombo.currentText()
                self.__editor.replaceAllMatches(replaceText)
                self.__appendReplaceMessage()
                self.__cursorPositionChanged()
                self.__updateHistory()

                count = self.__editor.getCurrentMatchesCount()
                self.__setBackgroundColor(self.BG_NOMATCH if count == 0 else
                                          self.BG_MATCH)

    # I had to use negative logic because by default the QToolButton.clicked
    # sends False as the checked status value
    def __onReplace(self, suppressMessage=False):
        """Triggered when replace current match button is clicked"""
        if self.replaceCombo.isVisible():
            if self.replaceButton.isEnabled():
                replaceText = self.replaceCombo.currentText()
                self.__editor.replaceMatch(replaceText)
                if not suppressMessage:
                    self.__appendReplaceMessage()
                self.__cursorPositionChanged()
                self.__updateHistory()

                count = self.__editor.getCurrentMatchesCount()
                self.__setBackgroundColor(self.BG_NOMATCH if count == 0 else
                                          self.BG_MATCH)

    def __onReplaceAndMove(self):
        """Triggered when replace-and-move button is clicked"""
        if self.replaceCombo.isVisible():
            if self.replaceAndMoveButton.isEnabled():
                self.__onReplace(True)
                if self.__editor.getCurrentMatchesCount() > 0:
                    self.__performSearch(False, True,
                                         self.__editor.absCursorPosition + 1,
                                         False)
                self.__appendReplaceMessage()

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

    def __moveToStartPoint(self):
        """Moves the editor cursor to the start point"""
        if self.__editor is not None and self.__startPoint is not None:
            self.__editor.absCursorPosition = self.__startPoint['absPos']
            self.__editor.setFirstVisible(self.__startPoint['firstVisible'])

    def __performSearch(self, fromScratch, forward,
                        absPos=None, needMessage=True):
        """Performs the incremental search"""
        if self.__editor is None:
            return

        if self.__startPoint is None:
            self.__setStartPoint()

        valid, err = self.__isSearchRegexpValid()
        if not valid:
            self.__onInvalidCriteria(fromScratch)
            GlobalData().mainWindow.showStatusBarMessage(err, 8000)
            self.__moveToStartPoint()
            return

        if self.findtextCombo.currentText() == '':
            self.__onInvalidCriteria(fromScratch)
            self.__setBackgroundColor(self.BG_IDLE)
            self.__moveToStartPoint()
            return

        # The search criteria is good, so enable the controls
        self.findNextButton.setEnabled(True)
        self.findPrevButton.setEnabled(True)

        if fromScratch:
            # Brand new editor to search in
            self.__setStartPoint()
            startPos = self.__editor.absCursorPosition
            if absPos is not None:
                startPos = absPos
            count = self.__editor.highlightRegexp(self.__getRegexp(), startPos,
                                                  forward, needMessage)
        else:
            startPos = self.__startPoint['absPos']
            if absPos is not None:
                startPos = absPos
            count = self.__editor.highlightRegexp(self.__getRegexp(), startPos,
                                                  forward, needMessage)
            if count == 0:
                self.__moveToStartPoint()
        self.__setBackgroundColor(self.BG_MATCH if count > 0
                                  else self.BG_NOMATCH)

        # The curson might not change its position so trigger the controls
        # enabling/disabling explicitly
        self.__cursorPositionChanged()

    def __onFindEnter(self, modifier):
        """Triggered when ENTER is pressed in the find combo"""
        if modifier == int(Qt.NoModifier):
            self.onNext()
        else:
            self.onPrev()

    def __onReplaceEnter(self, modifier):
        """Triggered when ENTER is pressed in the replace combo"""
        if modifier == int(Qt.NoModifier):
            self.__onReplace()
        else:
            self.__onReplaceAndMove()

    def onNext(self):
        """Triggered when the find next is clicked"""
        if self.__onPrevNext():
            self.__performSearch(False, True,
                                 self.__editor.absCursorPosition + 1)
            self.__updateHistory()

    def onPrev(self):
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

    def __subscribeToEditorSignals(self):
        """Subscribes for the cursor position notification"""
        if not self.__subscribedToCursor:
            if self.__editor:
                self.__editor.cursorPositionChanged.connect(
                    self.__cursorPositionChanged)
                self.__editor.sigHighlighted.connect(self.onQuickHighlight)
                self.__editor.textChanged.connect(self.__onTextChanged)
                self.__subscribedToCursor = True

    def __unsubscribeFromEditorSignals(self):
        """Unsubscribes from the cursor position notification"""
        if self.__subscribedToCursor:
            if self.__editor:
                try:
                    self.__editor.textChanged.disconnect(
                        self.__onTextChanged)
                    self.__editor.sigHighlighted.disconnect(
                        self.onQuickHighlight)
                    self.__editor.cursorPositionChanged.disconnect(
                        self.__cursorPositionChanged)
                except:
                    pass
            self.__subscribedToCursor = False

    def __onTextChanged(self):
        """Triggered when there are changes, i.e. the highlight is off"""
        if self.findtextCombo.isVisible():
            self.__setBackgroundColor(self.BG_IDLE)
            if self.replaceCombo.isVisible():
                self.replaceButton.setEnabled(False)
                self.replaceAndMoveButton.setEnabled(False)
                self.replaceAllButton.setEnabled(False)

    def __cursorPositionChanged(self):
        """Triggered when the cursor position is changed"""
        if self.replaceCombo.isVisible():
            onMatch = self.__editor.isCursorOnMatch()

            self.replaceButton.setEnabled(onMatch)
            self.replaceAndMoveButton.setEnabled(onMatch)

            self.replaceAllButton.setEnabled(
                self.__isCriteriaValid() and
                self.__editor.getCurrentMatchesCount() > 0)
