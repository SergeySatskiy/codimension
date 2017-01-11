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

"""New nested project directory dialog"""

import os
from .qt import (Qt, QEvent, QObject, QDialog, QLineEdit, QLabel,
                 QDialogButtonBox, QVBoxLayout)


class NewProjectDirDialog(QDialog):

    """New project directory dialog"""

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.__dirnameEdit = None
        self.__buttonBox = None
        self.__createLayout()

        self.okButton = self.__buttonBox.button(QDialogButtonBox.Ok)
        self.okButton.setEnabled(False)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(400, 100)
        self.setWindowTitle("Create subdirectory")
        vboxlayout = QVBoxLayout(self)

        inputLabel = QLabel(self)
        inputLabel.setText("Type new subdirectory name")
        vboxlayout.addWidget(inputLabel)

        self.__dirnameEdit = QLineEdit(self)
        self.__dirnameEdit.setToolTip("Subdirectory name without "
                                      "path separators")
        self.__dirnameEdit.installEventFilter(self)
        self.__dirnameEdit.textEdited.connect(self.__onTextChanged)
        vboxlayout.addWidget(self.__dirnameEdit)

        self.__buttonBox = QDialogButtonBox(self)
        self.__buttonBox.setOrientation(Qt.Horizontal)
        self.__buttonBox.setStandardButtons(QDialogButtonBox.Cancel |
                                            QDialogButtonBox.Ok)
        vboxlayout.addWidget(self.__buttonBox)

        self.__buttonBox.accepted.connect(self.accept)
        self.__buttonBox.rejected.connect(self.reject)

    def __onTextChanged(self, text):
        """Triggered when the input text has been changed"""
        self.okButton.setEnabled(text != '')

    def getDirName(self):
        """Provides the user input"""
        return self.__dirnameEdit.text()

    def eventFilter(self, obj, event):
        """Event filter for the project name field"""
        # Do not allow path separators
        if event.type() == QEvent.KeyPress:
            if event.key() == ord(os.path.sep):
                return True
        return QObject.eventFilter(self, obj, event)
