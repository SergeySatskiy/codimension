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

"""Python code parser errors dialog"""


from os.path import exists, basename
from utils.globals import GlobalData
from utils.fileutils import isPythonFile
from utils.colorfont import getZoomedMonoFont
from .qt import (Qt, QDialog, QTextEdit, QDialogButtonBox, QVBoxLayout,
                 QSizePolicy)
from .fitlabel import FitLabel


class ParserErrorsDialog(QDialog):

    """Python code parser errors dialog implementation"""

    def __init__(self, fileName, info=None, parent=None):
        QDialog.__init__(self, parent)

        if info is None:
            if not exists(fileName):
                raise Exception('Cannot open ' + fileName)

            if not isPythonFile(fileName):
                raise Exception('Unexpected file type (' + fileName +
                                '). A python file is expected.')

        self.__createLayout(fileName, info)
        self.setWindowTitle('Lexer/parser errors: ' + basename(fileName))
        self.show()

    def __createLayout(self, fileName, info):
        """Creates the dialog layout"""
        self.resize(600, 220)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)

        # Info label
        infoLabel = FitLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            infoLabel.sizePolicy().hasHeightForWidth())
        infoLabel.setSizePolicy(sizePolicy)
        infoLabel.setText('Lexer/parser errors for ' + fileName)
        verticalLayout.addWidget(infoLabel)

        # Result window
        resultEdit = QTextEdit(self)
        resultEdit.setTabChangesFocus(False)
        resultEdit.setAcceptRichText(False)
        resultEdit.setReadOnly(True)
        resultEdit.setFont(getZoomedMonoFont())
        if info is not None:
            modInfo = info
        else:
            modInfo = GlobalData().briefModinfoCache.get(fileName)
        if modInfo.isOK:
            resultEdit.setText('No errors found')
        else:
            resultEdit.setText('\n'.join(modInfo.lexerErrors +
                                         modInfo.errors))
        verticalLayout.addWidget(resultEdit)

        # Buttons
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Close)
        verticalLayout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.close)
