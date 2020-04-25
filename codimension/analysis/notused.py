# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2012-2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""not used code analysis using vulture"""


import os
import os.path
import logging
import tempfile
from subprocess import Popen, PIPE
from ui.qt import (QCursor, Qt, QTimer, QDialog, QDialogButtonBox, QVBoxLayout,
                   QLabel, QApplication)
from search.searchsupport import ItemToSearchIn, getSearchItemIndex
from search.vultureprovider import VultureSearchProvider
from utils.globals import GlobalData
from utils.config import DEFAULT_ENCODING



class NotUsedAnalysisProgress(QDialog):

    """Progress of the not used analysis"""

    def __init__(self, path, newSearch=True):
        QDialog.__init__(self, GlobalData().mainWindow)

        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise Exception('Dead code analysis path must exist. '
                            'The provide path "' + path + '" does not.')

        self.__path = path

        self.__newSearch = newSearch
        self.candidates = None
        self.__cancelRequest = False
        self.__inProgress = False

        self.__infoLabel = None
        self.__foundLabel = None
        self.__found = 0        # Number of found

        self.__createLayout()
        title = 'Dead code analysis for '
        if os.path.isdir(path):
            project = GlobalData().project
            if project.isLoaded() and project.getProjectDir() == path:
                title += 'all project files'
            else:
                title += 'dir ' + os.path.basename(os.path.normpath(path))
        else:
            title += os.path.basename(path)

        if not self.__newSearch:
            title += ' (do again)'

        self.setWindowTitle(title)
        self.__updateFoundLabel()

    def exec_(self):
        """Executes the dialog"""
        QTimer.singleShot(1, self.__process)
        QDialog.exec_(self)

    def keyPressEvent(self, event):
        """Processes the ESC key specifically"""
        if event.key() == Qt.Key_Escape:
            self.__onClose()
        else:
            QDialog.keyPressEvent(self, event)

    def __updateFoundLabel(self):
        """Updates the found label"""
        text = "Found: " + str(self.__found) + " candidate"
        if self.__found != 1:
            text += "s"
        self.__foundLabel.setText(text)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(450, 20)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)

        # Note label
        noteLabel = QLabel("<b>Note</b>: the analysis is "
                           "suggestive and not precise. "
                           "Use the results with caution.\n", self)
        verticalLayout.addWidget(noteLabel)

        # Info label
        self.__infoLabel = QLabel(self)
        verticalLayout.addWidget(self.__infoLabel)

        # Found label
        self.__foundLabel = QLabel(self)
        verticalLayout.addWidget(self.__foundLabel)

        # Buttons
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Close)
        verticalLayout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.__onClose)

    def __onClose(self):
        """triggered when the close button is clicked"""
        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()

    def __run(self):
        """Runs vulture"""
        errTmp = tempfile.mkstemp()
        errStream = os.fdopen(errTmp[0])
        process = Popen(['vulture', self.__path],
                        stdin=PIPE,
                        stdout=PIPE, stderr=errStream)
        process.stdin.close()
        processStdout = process.stdout.read()
        process.stdout.close()
        errStream.seek(0)
        err = errStream.read()
        errStream.close()
        process.wait()
        try:
            os.unlink(errTmp[1])
        except:
            pass
        return processStdout.decode(DEFAULT_ENCODING), err.strip()

    def __process(self):
        """Analysis process"""
        self.__inProgress = True
        mainWindow = GlobalData().mainWindow

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        # return code gives really nothing. So the error in running the utility
        # is detected by the stderr content.
        # Also, there could be a mix of messages for a project. Some files
        # could have syntax errors - there will be messages on stderr. The
        # other files are fine so there will be messages on stdout
        stdout, stderr = self.__run()
        self.candidates = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                # Line is like file.py:2: unused variable 'a' (60% confidence)
                try:
                    startIndex = line.find(':')
                    if startIndex < 0:
                        continue
                    endIndex = line.find(':', startIndex + 1)
                    if endIndex < 0:
                        continue
                    fileName = line[:startIndex]
                    startIndex = line.find(':')
                    if startIndex < 0:
                        continue
                    endIndex = line.find(':', startIndex + 1)
                    if endIndex < 0:
                        continue
                    fileName = os.path.abspath(line[:startIndex])
                    lineno = int(line[startIndex + 1:endIndex])
                    message = line[endIndex + 1:].strip()
                except:
                    continue

                index = getSearchItemIndex(self.candidates, fileName)
                if index < 0:
                    widget = mainWindow.getWidgetForFileName(fileName)
                    if widget is None:
                        uuid = ''
                    else:
                        uuid = widget.getUUID()
                    newItem = ItemToSearchIn(fileName, uuid)
                    self.candidates.append(newItem)
                    index = len(self.candidates) - 1
                self.candidates[index].addMatch('', lineno, message)

                self.__found += 1
                self.__updateFoundLabel()
                QApplication.processEvents()

        if self.__newSearch:
            # Do the action only for the new search.
            # Redo action will handle the results on its own
            if self.__found == 0:
                if stderr:
                    logging.error('Error running vulture for ' + self.__path +
                                  ':\n' + stderr)
                else:
                    logging.info('No unused candidates found')
            else:
                mainWindow.displayFindInFiles(VultureSearchProvider.getName(),
                                              self.candidates,
                                              {'path': self.__path})

        QApplication.restoreOverrideCursor()
        self.__infoLabel.setText('Done')
        self.__inProgress = False

        self.accept()

