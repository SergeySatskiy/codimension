# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2019 Sergey Satskiy <sergey.satskiy@gmail.com>
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

from ui.qt import (Qt, QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                   QPushButton, QGridLayout, QLineEdit)


"""Dialog to enter a new text for a graphics item"""

class DocLinkAnchorDialog(QDialog):

    """Replace text input dialog"""

    def __init__(self, windowTitle, cmlDocComment, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(windowTitle + ' documentation link and/or anchor')
        self.__createLayout()

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(600, 250)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        gridLayout = QGridLayout()

        # Link
        linkLabel = QLabel('Link', self)
        gridLayout.addWidget(linkLabel, 0, 0, 1, 1)
        self.linkEdit = QLineEdit(self)
        self.linkEdit.setToolTip(
            'Type a link to a file or to an external web resource')
        gridLayout.addWidget(self.linkEdit, 0, 1, 1, 1)
        self.fileButton = QPushButton(self)
        self.fileButton.setText('...')
        self.fileButton.setToolTip(
            'Select an existing or non existing file')
        gridLayout.addWidget(self.fileButton, 0, 2, 1, 1)

        # Anchor
        anchorLabel = QLabel('Anchor', self)
        gridLayout.addWidget(anchorLabel, 1, 0, 1, 1)
        self.anchorEdit = QLineEdit(self)
        self.anchorEdit.setToolTip(
            'Anchor is used to refer from the other files to rfer to it')
        gridLayout.addWidget(self.anchorEdit, 1, 1, 1, 1)

        # Title
        titleLabel = QLabel('Title', self)
        gridLayout.addWidget(titleLabel, 2, 0, 1, 1)
        self.titleEdit = QLineEdit(self)
        self.titleEdit.setToolTip(
            'If provided then will be displayed in the rectangle')
        gridLayout.addWidget(self.titleEdit, 2, 1, 1, 1)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.__OKButton = buttonBox.button(QDialogButtonBox.Ok)
        self.__OKButton.setDefault(True)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.close)

        verticalLayout.addLayout(gridLayout)
        verticalLayout.addWidget(buttonBox)

        self.linkEdit.setFocus()
