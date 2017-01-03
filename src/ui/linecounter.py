#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""project line counter dialog"""

import os
import os.path
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (QDialog, QTextEdit, QDialogButtonBox, QVBoxLayout,
                         QSizePolicy, QCursor, QProgressBar, QApplication,
                         QFontMetrics)
from utils.linescounter import LinesCounter
from utils.globals import GlobalData
from utils.misc import splitThousands
from utils.fileutils import isPythonFile
from .fitlabel import FitPathLabel


class LineCounterDialog(QDialog):

    """Line counter dialog implementation"""

    def __init__(self, fName=None, editor=None, parent=None):
        QDialog.__init__(self, parent)

        self.__cancelRequest = False
        self.__inProgress = False
        if fName is not None:
            self.__fName = fName.strip()
        else:
            self.__fName = None
        self.__editor = editor
        self.__createLayout()
        self.setWindowTitle("Line counter")
        QTimer.singleShot(0, self.__process)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(450, 220)
        self.setSizeGripEnabled(True)

        self.verticalLayout = QVBoxLayout(self)

        # Info label
        self.infoLabel = FitPathLabel(self)
        # sizePolicy = QSizePolicy(QSizePolicy.Expanding,
        #                          QSizePolicy.Preferred)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum,
                                 QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.infoLabel.sizePolicy().hasHeightForWidth())
        self.infoLabel.setSizePolicy(sizePolicy)
        self.verticalLayout.addWidget(self.infoLabel)

        # Progress bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        self.progressBar.setOrientation(Qt.Horizontal)
        self.verticalLayout.addWidget(self.progressBar)

        # Result window
        self.resultEdit = QTextEdit(self)
        self.resultEdit.setTabChangesFocus(False)
        self.resultEdit.setAcceptRichText(False)
        self.resultEdit.setReadOnly(True)
        self.resultEdit.setFontFamily(GlobalData().skin.baseMonoFontFace)
        font = self.resultEdit.font()

        # Calculate the vertical size
        fontMetrics = QFontMetrics(font)
        rect = fontMetrics.boundingRect("W")
        # 6 lines, 5 line spacings, 2 frames
        self.resultEdit.setMinimumHeight(rect.height() * 7 + 4 * 5 +
                                         self.resultEdit.frameWidth() * 2)
        self.verticalLayout.addWidget(self.resultEdit)

        # Buttons
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)
        self.verticalLayout.addWidget(self.buttonBox)

        self.buttonBox.rejected.connect(self.__onClose)

    def __scanDir(self, path, files):
        """Recursively builds a list of python files"""
        if path in self.__scannedDirs:
            return

        self.__scannedDirs.append(path)
        for item in os.listdir(path):
            if os.path.isdir(path + item):
                nestedDir = os.path.realpath(path + item)
                if not nestedDir.endswith(os.path.sep):
                    nestedDir += os.path.sep
                self.__scanDir(nestedDir, files)
            else:
                candidate = os.path.realpath(path + item)
                if isPythonFile(candidate):
                    if candidate not in files:
                        files.append(candidate)

    def __onClose(self):
        """Triggered when the close button is clicked"""
        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()

    def __process(self):
        """Accumulation process"""
        self.__inProgress = True
        if self.__fName is not None:
            if os.path.exists(self.__fName):
                if os.path.isdir(self.__fName):
                    self.__fName = os.path.realpath(self.__fName)
                    if not self.__fName.endswith(os.path.sep):
                        self.__fName += os.path.sep
                    files = []
                    self.__scannedDirs = []
                    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                    self.__scanDir(self.__fName, files)
                    QApplication.restoreOverrideCursor()
                else:
                    files = [self.__fName]
            else:
                files = []
        elif self.__editor is not None:
            files = ["buffer"]
        else:
            files = GlobalData().project.filesList
        self.progressBar.setRange(0, len(files))

        accumulator = LinesCounter()
        current = LinesCounter()

        index = 1
        for fileName in files:

            if self.__cancelRequest:
                self.__inProgress = False
                self.close()
                return

            self.infoLabel.setPath('Processing: ' + fileName)

            processed = False
            if self.__editor is not None:
                current.getLinesInBuffer(self.__editor)
                processed = True
            else:
                if isPythonFile(fileName) and os.path.exists(fileName):
                    current.getLines(fileName)
                    processed = True

            if processed:
                accumulator.files += current.files
                accumulator.filesSize += current.filesSize
                accumulator.codeLines += current.codeLines
                accumulator.emptyLines += current.emptyLines
                accumulator.commentLines += current.commentLines
                accumulator.classes += current.classes

            self.progressBar.setValue(index)
            index += 1

            QApplication.processEvents()

        self.infoLabel.setPath('Done')
        self.__inProgress = False

        # Update text in the text window
        nFiles = splitThousands(str(accumulator.files))
        filesSize = splitThousands(str(accumulator.filesSize))
        classes = splitThousands(str(accumulator.classes))
        codeLines = splitThousands(str(accumulator.codeLines))
        emptyLines = splitThousands(str(accumulator.emptyLines))
        commentLines = splitThousands(str(accumulator.commentLines))
        totalLines = splitThousands(str(accumulator.codeLines +
                                        accumulator.emptyLines +
                                        accumulator.commentLines))
        output = '\n'.join(["Classes:                 " + classes,
                            "Code lines:              " + codeLines,
                            "Empty lines:             " + emptyLines,
                            "Comment lines:           " + commentLines,
                            "Total lines:             " + totalLines])

        if self.__editor is None:
            output = 'Number of python files:  ' + nFiles + '\n' \
                     'Total files size:        ' + filesSize + ' bytes\n' + \
                     output
        else:
            output = 'Number of characters:    ' + filesSize + '\n' + \
                     output

        self.resultEdit.setText(output)
