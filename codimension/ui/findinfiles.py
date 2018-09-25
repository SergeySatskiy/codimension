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

"""find in files dialog"""


from os import listdir
from os.path import sep, isabs, exists, isdir, normpath, isfile, realpath
import re
import time
import logging
from html import escape
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import (isFileSearchable, isPythonFile, getFileContent,
                             resolveLink)
from utils.diskvaluesrelay import getFindInFilesHistory, setFindInFilesHistory
from cdmpyparser import getBriefModuleInfoFromMemory
from .qt import (QCursor, Qt, QDialog, QDialogButtonBox, QVBoxLayout,
                 QSizePolicy, QLabel, QProgressBar, QApplication, QComboBox,
                 QGridLayout, QHBoxLayout, QCheckBox, QRadioButton,
                 QGroupBox, QPushButton, QFileDialog)
from .fitlabel import FitPathLabel
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class Match:

    """Stores info about one match in a file"""

    def __init__(self, line, start, finish):
        self.line = line        # Matched line
        self.start = start      # Match start pos
        self.finish = finish    # Match end pos
        self.tooltip = "not implemented"
        self.text = ""


def getSearchItemIndex(items, fileName):
    """Provides the search item index basing on the file name"""
    index = 0
    for item in items:
        if item.fileName == fileName:
            return index
        index += 1
    return -1


class ItemToSearchIn:

    """Stores information about one item to search in"""

    contextLines = 15

    def __init__(self, fname, bufferID):
        self.fileName = fname       # Could be absolute -> for existing files
                                    # or relative -> for newly created
        self.bufferUUID = bufferID  # Non empty for currently opened files
        self.tooltip = ""           # For python files only -> docstring
        self.matches = []

    def addMatch(self, name, lineNumber, customMessage=None):
        """Used to add a match which was found outside of find in files"""
        match = Match(lineNumber, 0, 0)

        # Load the file and identify matched line and tooltip
        try:
            if self.bufferUUID != "":
                mainWindow = GlobalData().mainWindow
                widget = mainWindow.getWidgetByUUID(self.bufferUUID)
                if widget is not None:
                    content = widget.getEditor().lines
                else:
                    raise Exception('Inconsistency. Buffer disappeared.')
            else:
                content = getFileContent(self.fileName).splitlines()
            self.__fillInMatch(match, content, name, lineNumber, customMessage)
        except Exception as exc:
            logging.error('Error adding match: ' + str(exc))
        self.matches.append(match)

    def __fillInMatch(self, match, content, name, lineNumber, customMessage=None):
        """Fills in the match fields from the content"""
        # Form the regexp corresponding to a single word search
        line = content[lineNumber - 1]
        if customMessage:
            match.text = customMessage
        else:
            match.text = line.strip()

        if name:
            regexpText = re.escape(name)
            regexpText = "\\b%s\\b" % regexpText
            flags = re.UNICODE
            searchRegexp = re.compile(regexpText, flags)

            contains = searchRegexp.search(line)
            match.start = contains.start()
            match.finish = contains.end()
        else:
            match.start = 0
            match.finish = len(line)

        match.tooltip = self.__buildTooltip(content, lineNumber - 1,
                                            len(content),
                                            match.start, match.finish)

        self.__extractDocstring(content)

    def search(self, expression):
        """Perform search within this item"""
        self.matches = []
        if self.bufferUUID != "":
            # Search item is the currently loaded buffer
            mainWindow = GlobalData().mainWindow
            widget = mainWindow.getWidgetByUUID(self.bufferUUID)
            if widget is not None:
                # Search in the buffer

                self.__lookThroughLines(widget.getEditor().lines, expression)
                return

        # Here: there were no buffer or have not found it
        #       try searching in a file
        if not isabs(self.fileName) or not exists(self.fileName):
            # Unfortunately not all network file systems report the
            # fact that a file has been deleted from the disk so
            # let's simply ignore such files
            return

        # File exists, search in the file
        try:
            content = getFileContent(self.fileName).splitlines()
            self.__lookThroughLines(content, expression)
        except Exception as exc:
            logging.error('Error searching in ' +
                          self.fileName + ': ' + str(exc))

    def __buildTooltip(self, content, lineIndex, totalLines,
                       startPos, finishPos):
        """Forms the tooltip for the given match"""
        start, end = self.__calculateContextStart(lineIndex, totalLines)
        lines = content[start:end]
        matchIndex = lineIndex - start

        # Avoid incorrect tooltips for HTML/XML files
        for index in range(0, len(lines)):
            if index != matchIndex:
                lines[index] = escape(lines[index])

        lines[matchIndex] = \
            escape(lines[matchIndex][:startPos]) + \
            "<b>" + \
            escape(lines[matchIndex][startPos:finishPos]) + \
            "</b>" + \
            escape(lines[matchIndex][finishPos:])

        # Strip empty lines at the end and at the beginning
        index = len(lines) - 1
        while index >= 0:
            if lines[index].strip() == '':
                del lines[index]
                index -= 1
                continue
            break
        while len(lines) > 0:
            if lines[0].strip() == '':
                del lines[0]
                continue
            break

        return '<p>' + '<br/>'.join(lines).replace(' ', '&nbsp;') + '</p>'

    def __lookThroughLines(self, content, expression):
        """Searches through all the given lines"""
        lineIndex = 0
        totalLines = len(content)
        while lineIndex < totalLines:
            line = content[lineIndex]
            contains = expression.search(line)
            if contains:
                match = Match(lineIndex + 1, contains.start(), contains.end())
                match.text = line.strip()
                match.tooltip = self.__buildTooltip(content, lineIndex,
                                                    totalLines,
                                                    match.start, match.finish)
                self.matches.append(match)
                if len(self.matches) > 1024:
                    # Too much entries, stop here
                    logging.warning("More than 1024 matches in " +
                                    self.fileName +
                                    ". Stop further search in this file.")
                    break
            lineIndex += 1

        # Extract docsting if applicable
        if len(self.matches) > 0:
            self.__extractDocstring(content)

    def __extractDocstring(self, content):
        """Extracts a docstring and sets it as a tooltip if needed"""
        if self.tooltip != "":
            return

        if isPythonFile(self.fileName):
            info = getBriefModuleInfoFromMemory("\n".join(content))
            self.tooltip = ""
            if info.docstring is not None:
                self.tooltip = info.docstring.text

    @staticmethod
    def __calculateContextStart(matchedLine, totalLines):
        """Calculates the start line number for the context tooltip"""
        # matchedLine is a zero based index
        if ItemToSearchIn.contextLines >= totalLines:
            return 0, totalLines

        start = matchedLine - int(ItemToSearchIn.contextLines / 2)
        if start < 0:
            start = 0
        end = start + ItemToSearchIn.contextLines
        if end < totalLines:
            return start, end
        return totalLines - ItemToSearchIn.contextLines, totalLines


class FindInFilesDialog(QDialog):

    """find in files dialog implementation"""

    IN_PROJECT = 0
    IN_DIRECTORY = 1
    IN_OPEN_FILES = 2

    def __init__(self, where, what=None, dirPath=None):
        QDialog.__init__(self, GlobalData().mainWindow)

        mainWindow = GlobalData().mainWindow
        self.editorsManager = mainWindow.editorsManagerWidget.editorsManager

        self.__cancelRequest = False
        self.__inProgress = False
        self.searchRegexp = None
        self.searchResults = []

        # Avoid pylint complains
        self.findCombo = None
        self.caseCheckBox = None
        self.wordCheckBox = None
        self.regexpCheckBox = None
        self.projectRButton = None
        self.openFilesRButton = None
        self.dirRButton = None
        self.dirEditCombo = None
        self.dirSelectButton = None
        self.filterCombo = None
        self.fileLabel = None
        self.progressBar = None
        self.findButton = None

        self.__createLayout()
        self.setWindowTitle("Find in files")

        self.__maxEntries = Settings()['maxSearchEntries']

        # Restore the combo box values
        # [ {'term': ., 'dir': ., 'filters': .,
        #    'cbCase': ., 'cbWord': ., 'cbRegexp': .,
        #    'rbProject': ., 'rbOpen': ., 'rbDir': .}, ... ]
        self.__history = getFindInFilesHistory()
        self.__populateHistory()
        self.findCombo.setEditText('')
        self.dirEditCombo.setEditText('')
        self.filterCombo.setEditText('')

        if where == self.IN_PROJECT:
            self.setSearchInProject(what)
        elif where == self.IN_DIRECTORY:
            self.setSearchInDirectory(what, dirPath)
        else:
            self.setSearchInOpenFiles(what)

    def __serialize(self):
        """Serializes the current search parameters"""
        termText = self.findCombo.currentText()
        filtText = self.__normalizeFilters(self.filterCombo.currentText())
        dirText = ''
        if self.dirRButton.isChecked():
            dirText = self.dirEditCombo.currentText().strip()

        return {'term': termText,
                'dir': dirText,
                'filters': filtText,
                'cbCase': self.caseCheckBox.isChecked(),
                'cbWord': self.wordCheckBox.isChecked(),
                'cbRegexp': self.regexpCheckBox.isChecked(),
                'rbProject': self.projectRButton.isChecked(),
                'rbOpen': self.openFilesRButton.isChecked(),
                'rbDir': self.dirRButton.isChecked()}

    def __deserialize(self, item):
        """Deserializes the history item"""
        self.findCombo.setEditText(item['term'])
        self.dirEditCombo.setEditText(item['dir'])
        self.filterCombo.setEditText(item['filters'])
        self.caseCheckBox.setChecked(item['cbCase'])
        self.wordCheckBox.setChecked(item['cbWord'])
        self.regexpCheckBox.setChecked(item['cbRegexp'])

        self.projectRButton.setChecked(item['rbProject'])
        self.openFilesRButton.setChecked(item['rbOpen'])
        self.dirRButton.setChecked(item['rbDir'])

        self.dirEditCombo.setEnabled(item['rbDir'])
        self.dirSelectButton.setEnabled(item['rbDir'])

    def __populateHistory(self):
        """Populates the search history in the combo boxes"""
        # No need to react to the change of the current index
        self.findCombo.currentIndexChanged[int].disconnect(
            self.__whatIndexChanged)
        index = 0
        for props in self.__history:
            self.findCombo.addItem(props['term'], index)
            directory = props['dir']
            if directory:
                self.dirEditCombo.addItem(directory)
            filt = props['filters']
            if filt:
                self.filterCombo.addItem(filt)
            index += 1
        # Restore the handler
        self.findCombo.currentIndexChanged[int].connect(
            self.__whatIndexChanged)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(600, 300)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        gridLayout = QGridLayout()

        # Combo box for the text to search
        findLabel = QLabel(self)
        findLabel.setText("Find text:")
        self.findCombo = QComboBox(self)
        self.__tuneCombo(self.findCombo)
        self.findCombo.lineEdit().setToolTip(
            "Regular expression to search for")
        self.findCombo.editTextChanged.connect(self.__someTextChanged)
        self.findCombo.currentIndexChanged[int].connect(
            self.__whatIndexChanged)

        gridLayout.addWidget(findLabel, 0, 0, 1, 1)
        gridLayout.addWidget(self.findCombo, 0, 1, 1, 1)
        verticalLayout.addLayout(gridLayout)

        # Check boxes
        horizontalCBLayout = QHBoxLayout()
        self.caseCheckBox = QCheckBox(self)
        self.caseCheckBox.setText("Match &case")
        horizontalCBLayout.addWidget(self.caseCheckBox)
        self.wordCheckBox = QCheckBox(self)
        self.wordCheckBox.setText("Match whole &word")
        horizontalCBLayout.addWidget(self.wordCheckBox)
        self.regexpCheckBox = QCheckBox(self)
        self.regexpCheckBox.setText("Regular &expression")
        horizontalCBLayout.addWidget(self.regexpCheckBox)

        verticalLayout.addLayout(horizontalCBLayout)

        # Files groupbox
        filesGroupbox = QGroupBox(self)
        filesGroupbox.setTitle("Find in")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            filesGroupbox.sizePolicy().hasHeightForWidth())
        filesGroupbox.setSizePolicy(sizePolicy)

        gridLayoutFG = QGridLayout(filesGroupbox)
        self.projectRButton = QRadioButton(filesGroupbox)
        self.projectRButton.setText("&Project")
        gridLayoutFG.addWidget(self.projectRButton, 0, 0)
        self.projectRButton.clicked.connect(self.__projectClicked)

        self.openFilesRButton = QRadioButton(filesGroupbox)
        self.openFilesRButton.setText("&Opened files only")
        gridLayoutFG.addWidget(self.openFilesRButton, 1, 0)
        self.openFilesRButton.clicked.connect(self.__openFilesOnlyClicked)

        self.dirRButton = QRadioButton(filesGroupbox)
        self.dirRButton.setText("&Directory tree")
        gridLayoutFG.addWidget(self.dirRButton, 2, 0)
        self.dirRButton.clicked.connect(self.__dirClicked)

        self.dirEditCombo = QComboBox(filesGroupbox)
        self.__tuneCombo(self.dirEditCombo)
        self.dirEditCombo.lineEdit().setToolTip("Directory to search in")
        gridLayoutFG.addWidget(self.dirEditCombo, 2, 1)
        self.dirEditCombo.editTextChanged.connect(self.__someTextChanged)

        self.dirSelectButton = QPushButton(filesGroupbox)
        self.dirSelectButton.setText("...")
        gridLayoutFG.addWidget(self.dirSelectButton, 2, 2)
        self.dirSelectButton.clicked.connect(self.__selectDirClicked)

        filterLabel = QLabel(filesGroupbox)
        filterLabel.setText("Files filter:")
        gridLayoutFG.addWidget(filterLabel, 3, 0)
        self.filterCombo = QComboBox(filesGroupbox)
        self.__tuneCombo(self.filterCombo)
        self.filterCombo.lineEdit().setToolTip("File names regular expression")
        gridLayoutFG.addWidget(self.filterCombo, 3, 1)
        self.filterCombo.editTextChanged.connect(self.__someTextChanged)

        verticalLayout.addWidget(filesGroupbox)

        # File label
        self.fileLabel = FitPathLabel(self)
        self.fileLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        verticalLayout.addWidget(self.fileLabel)

        # Progress bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        self.progressBar.setOrientation(Qt.Horizontal)
        verticalLayout.addWidget(self.progressBar)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        self.findButton = buttonBox.addButton("Find",
                                              QDialogButtonBox.AcceptRole)
        self.findButton.setDefault(True)
        self.findButton.clicked.connect(self.__process)
        verticalLayout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.__onClose)

    @staticmethod
    def __tuneCombo(comboBox):
        """Sets the common settings for a combo box"""
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            comboBox.sizePolicy().hasHeightForWidth())
        comboBox.setSizePolicy(sizePolicy)
        comboBox.setEditable(True)
        comboBox.setInsertPolicy(QComboBox.InsertAtTop)
        comboBox.setCompleter(None)
        comboBox.setDuplicatesEnabled(False)

    def __onClose(self):
        """Triggered when the close button is clicked"""
        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()

    def __historyIndexByWhat(self, what):
        """Provides the history index by 'what' value"""
        if what:
            for index in range(self.findCombo.count()):
                if self.findCombo.itemText(index) == what:
                    return index, self.findCombo.itemData(index)
        return None, None

    @staticmethod
    def __indexByText(combo, text):
        """Provides the text entry index"""
        index = 0
        for index in range(combo.count()):
            if combo.itemText(index) == text:
                return index
            index += 1
        return -1

    def setSearchInProject(self, what=None):
        """Set search ready for the whole project"""
        if not GlobalData().project.isLoaded():
            # No project loaded, fallback to opened files
            self.setSearchInOpenFiles(what)
            return

        # Select the project radio button
        self.projectRButton.setEnabled(True)
        self.projectRButton.setChecked(True)
        self.dirEditCombo.setEnabled(False)
        self.dirSelectButton.setEnabled(False)

        openedFiles = self.editorsManager.getTextEditors()
        self.openFilesRButton.setEnabled(len(openedFiles) != 0)

        if what:
            # Pick up the history values if so
            comboIndex, historyIndex = self.__historyIndexByWhat(what)
            if historyIndex is not None:
                self.__deserialize(self.__history[historyIndex])
                self.findCombo.setCurrentIndex(comboIndex)
            else:
                self.findCombo.setCurrentText(what)
            self.findCombo.lineEdit().selectAll()
        self.findCombo.setFocus()

        # Check searchability
        self.__testSearchability()

    def setSearchInOpenFiles(self, what=None):
        """Sets search ready for the opened files"""
        openedFiles = self.editorsManager.getTextEditors()
        if not openedFiles:
            # No opened files, fallback to search in dir
            self.setSearchInDirectory(what, None)
            return

        # Select the radio buttons
        self.projectRButton.setEnabled(GlobalData().project.isLoaded())
        self.openFilesRButton.setEnabled(True)
        self.openFilesRButton.setChecked(True)
        self.dirEditCombo.setEnabled(False)
        self.dirSelectButton.setEnabled(False)

        if what:
            # Pick up the history values if so
            comboIndex, historyIndex = self.__historyIndexByWhat(what)
            if historyIndex is not None:
                self.__deserialize(self.__history[historyIndex])
                self.findCombo.setCurrentIndex(comboIndex)
            else:
                self.findCombo.setCurrentText(what)
            self.findCombo.lineEdit().selectAll()
        self.findCombo.setFocus()

        # Check searchability
        self.__testSearchability()

    def setSearchInDirectory(self, what=None, dirPath=None):
        """Sets search ready for the given directory"""
        # Select radio buttons
        self.projectRButton.setEnabled(GlobalData().project.isLoaded())
        openedFiles = self.editorsManager.getTextEditors()
        self.openFilesRButton.setEnabled(len(openedFiles) != 0)
        self.dirRButton.setEnabled(True)
        self.dirRButton.setChecked(True)
        self.dirEditCombo.setEnabled(True)
        self.dirSelectButton.setEnabled(True)

        if what:
            # Pick up the history values if so
            comboIndex, historyIndex = self.__historyIndexByWhat(what)
            if historyIndex is not None:
                self.__deserialize(self.__history[historyIndex])
                self.findCombo.setCurrentIndex(comboIndex)
            else:
                self.findCombo.setCurrentText(what)
            self.findCombo.lineEdit().selectAll()

        if dirPath:
            self.dirEditCombo.setEditText(dirPath)

        self.findCombo.setFocus()

        # Check searchability
        self.__testSearchability()

    @staticmethod
    def __normalizeFilters(text):
        """Normalizes the filters string"""
        normParts = []
        for part in text.strip().split(';'):
            part = part.strip()
            if part:
                normParts.append(part)
        return '; '.join(normParts)

    def __testSearchability(self):
        """Tests the searchability and sets the Find button status"""
        startTime = time.time()
        if self.findCombo.currentText().strip() == "":
            self.findButton.setEnabled(False)
            self.findButton.setToolTip("No text to search")
            return

        if self.dirRButton.isChecked():
            dirname = self.dirEditCombo.currentText().strip()
            if dirname == "":
                self.findButton.setEnabled(False)
                self.findButton.setToolTip("No directory path")
                return
            if not isdir(dirname):
                self.findButton.setEnabled(False)
                self.findButton.setToolTip("Path is not a directory")
                return

        # Now we need to match file names if there is a filter
        filtersText = self.filterCombo.currentText().strip()
        if filtersText == "":
            self.findButton.setEnabled(True)
            self.findButton.setToolTip("Find in files")
            return

        # Need to check the files match
        try:
            filters = self.__compileFilters()
        except:
            self.findButton.setEnabled(False)
            self.findButton.setToolTip("Incorrect files "
                                       "filter regular expression")
            return

        matched = False
        tooLong = False
        if self.projectRButton.isChecked():
            # Whole project
            for fname in GlobalData().project.filesList:
                if fname.endswith(sep):
                    continue
                matched = self.__filterMatch(filters, fname)
                if matched:
                    break
                # Check the time, it might took too long
                if time.time() - startTime > 0.1:
                    tooLong = True
                    break

        elif self.openFilesRButton.isChecked():
            # Opened files
            openedFiles = self.editorsManager.getTextEditors()
            for record in openedFiles:
                matched = self.__filterMatch(filters, record[1])
                if matched:
                    break
                # Check the time, it might took too long
                if time.time() - startTime > 0.1:
                    tooLong = True
                    break

        else:
            # Search in the dir
            if not dirname.endswith(sep):
                dirname += sep
            matched, tooLong = self.__matchInDir(dirname, filters, startTime)

        if matched:
            self.findButton.setEnabled(True)
            self.findButton.setToolTip("Find in files")
        else:
            if tooLong:
                self.findButton.setEnabled(True)
                self.findButton.setToolTip("Find in files")
            else:
                self.findButton.setEnabled(False)
                self.findButton.setToolTip("No files matched to search in")

    @staticmethod
    def __matchInDir(path, filters, startTime):
        """Provides the 'match' and 'too long' statuses"""
        matched = False
        tooLong = False
        for item in listdir(path):
            if time.time() - startTime > 0.1:
                tooLong = True
                return matched, tooLong
            if isdir(path + item):
                dname = path + item + sep
                matched, tooLong = FindInFilesDialog.__matchInDir(dname,
                                                                  filters,
                                                                  startTime)
                if matched or tooLong:
                    return matched, tooLong
                continue
            if FindInFilesDialog.__filterMatch(filters, path + item):
                matched = True
                return matched, tooLong
        return matched, tooLong

    def __projectClicked(self):
        """project radio button clicked"""
        self.dirEditCombo.setEnabled(False)
        self.dirSelectButton.setEnabled(False)
        self.__testSearchability()

    def __openFilesOnlyClicked(self):
        """open files only radio button clicked"""
        self.dirEditCombo.setEnabled(False)
        self.dirSelectButton.setEnabled(False)
        self.__testSearchability()

    def __dirClicked(self):
        """dir radio button clicked"""
        self.dirEditCombo.setEnabled(True)
        self.dirSelectButton.setEnabled(True)
        self.dirEditCombo.setFocus()
        self.__testSearchability()

    def __someTextChanged(self, text):
        """Text to search, filter or dir name has been changed"""
        del text    # unused argument
        self.__testSearchability()

    def __whatIndexChanged(self, index):
        """Index in history has changed"""
        if index != -1:
            historyIndex = self.findCombo.itemData(index)
            if historyIndex is not None:
                self.__deserialize(self.__history[historyIndex])
        self.__testSearchability()

    def __selectDirClicked(self):
        """The user selects a directory"""
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        dirName = QFileDialog.getExistingDirectory(
            self, 'Select directory to search in',
            self.dirEditCombo.currentText(), options)

        if dirName:
            self.dirEditCombo.setEditText(normpath(dirName))
        self.__testSearchability()

    @staticmethod
    def __filterMatch(filters, fname):
        """True if the file should be taken into consideration"""
        if filters:
            for filt in filters:
                if filt.match(fname):
                    return True
            return False
        return True

    def __projectFiles(self, filters):
        """Project files list respecting the mask"""
        mainWindow = GlobalData().mainWindow
        files = []
        for fname in GlobalData().project.filesList:
            if fname.endswith(sep):
                continue
            if self.__filterMatch(filters, fname):
                widget = mainWindow.getWidgetForFileName(fname)
                if widget is None:
                    # Do not check for broken symlinks
                    if isFileSearchable(fname, False):
                        files.append(ItemToSearchIn(fname, ""))
                else:
                    if widget.getType() in \
                                [MainWindowTabWidgetBase.PlainTextEditor]:
                        files.append(ItemToSearchIn(fname,
                                                    widget.getUUID()))
            QApplication.processEvents()
            if self.__cancelRequest:
                raise Exception("Cancel request")
        return files

    def __openedFiles(self, filters):
        """Currently opened editor buffers"""
        files = []
        openedFiles = self.editorsManager.getTextEditors()
        for record in openedFiles:
            uuid = record[0]
            fname = record[1]
            if self.__filterMatch(filters, fname):
                files.append(ItemToSearchIn(fname, uuid))
            QApplication.processEvents()
            if self.__cancelRequest:
                raise Exception("Cancel request")
        return files

    def __dirFiles(self, path, filters, files):
        """Files recursively for the dir"""
        for item in listdir(path):
            QApplication.processEvents()
            if self.__cancelRequest:
                raise Exception("Cancel request")
            if isdir(path + item):
                if item in ['.svn', '.cvs', '.git', '.hg']:
                    # It does not make sense to search in revision control dirs
                    continue
                anotherDir, isLoop = resolveLink(path + item)
                if not isLoop:
                    self.__dirFiles(anotherDir + sep,
                                    filters, files)
                continue
            if not isfile(path + item):
                continue
            realItem, isLoop = resolveLink(path + item)
            if isLoop:
                continue
            if self.__filterMatch(filters, realItem):
                found = False
                for itm in files:
                    if itm.fileName == realItem:
                        found = True
                        break
                if not found:
                    mainWindow = GlobalData().mainWindow
                    widget = mainWindow.getWidgetForFileName(realItem)
                    if widget is None:
                        if isFileSearchable(realItem):
                            files.append(ItemToSearchIn(realItem, ""))
                    else:
                        if widget.getType() in \
                                    [MainWindowTabWidgetBase.PlainTextEditor]:
                            files.append(ItemToSearchIn(realItem,
                                                        widget.getUUID()))

    def __compileFilters(self):
        """Compiles the filters"""
        filtersText = self.filterCombo.currentText().strip()
        filtersRe = []
        if filtersText != "":
            for filt in filtersText.split(';'):
                filtersRe.append(re.compile(filt.strip(), re.IGNORECASE))
        return filtersRe

    def __buildFilesList(self):
        """Builds the list of files to search in"""
        filtersRe = self.__compileFilters()

        if self.projectRButton.isChecked():
            return self.__projectFiles(filtersRe)

        if self.openFilesRButton.isChecked():
            return self.__openedFiles(filtersRe)

        dirname = realpath(self.dirEditCombo.currentText().strip())
        files = []
        self.__dirFiles(dirname + sep, filtersRe, files)
        return files

    def __updateHistory(self):
        """Updates history if needed"""
        # Add entries to the combo box if required
        historyItem = self.__serialize()
        _, historyIndex = self.__historyIndexByWhat(
            self.findCombo.currentText())
        if historyIndex is not None:
            self.__history[historyIndex] = historyItem
        else:
            historyIndex = 0
            self.__history.insert(0, historyItem)
            if len(self.__history) > self.__maxEntries:
                self.__history = self.__history[:self.__maxEntries]

        self.findCombo.clear()
        self.filterCombo.clear()
        self.dirEditCombo.clear()
        self.__populateHistory()

        self.findCombo.setCurrentIndex(historyIndex)
        self.findCombo.setCurrentText(historyItem['term'])

        fltValue = historyItem['filters']
        if fltValue:
            index = self.__indexByText(self.filterCombo, fltValue)
            self.filterCombo.setCurrentIndex(index)
        self.filterCombo.setCurrentText(fltValue)

        dirValue = historyItem['dir']
        if dirValue:
            index = self.__indexByText(self.dirEditCombo, dirValue)
            self.dirEditCombo.setCurrentIndex(index)
        self.dirEditCombo.setCurrentText(dirValue)

        # Save the combo values for further usage
        setFindInFilesHistory(self.__history)

    def __process(self):
        """Search process"""
        self.__updateHistory()

        self.__inProgress = True
        numberOfMatches = 0
        self.searchResults = []
        self.searchRegexp = None

        # Form the regexp to search
        regexpText = self.findCombo.currentText()
        if not self.regexpCheckBox.isChecked():
            regexpText = re.escape(regexpText)
        if self.wordCheckBox.isChecked():
            regexpText = "\\b%s\\b" % regexpText
        flags = re.UNICODE
        if not self.caseCheckBox.isChecked():
            flags |= re.IGNORECASE

        try:
            self.searchRegexp = re.compile(regexpText, flags)
        except Exception as exc:
            logging.error("Invalid search expression: " + str(exc))
            self.close()
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.fileLabel.setPath('Building list of files to search in...')
        QApplication.processEvents()
        try:
            files = self.__buildFilesList()
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            if 'Cancel request' not in str(exc):
                logging.error(str(exc))
            self.close()
            return
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()

        if not files:
            self.fileLabel.setPath('No files to search in')
            return

        self.progressBar.setRange(0, len(files))

        index = 1
        for item in files:

            if self.__cancelRequest:
                self.__inProgress = False
                self.close()
                return

            self.fileLabel.setPath('Matches: ' + str(numberOfMatches) +
                                   ' Processing: ' + item.fileName)

            item.search(self.searchRegexp)
            found = len(item.matches)
            if found > 0:
                numberOfMatches += found
                self.searchResults.append(item)

            self.progressBar.setValue(index)
            index += 1

            QApplication.processEvents()

        if numberOfMatches == 0:
            msg = 'No matches in ' + str(len(files)) + 'file'
            if len(files) > 1:
                msg += 's'
            self.fileLabel.setPath(msg)
            self.__inProgress = False
        else:
            self.close()
