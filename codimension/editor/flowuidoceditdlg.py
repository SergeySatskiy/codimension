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

import os.path
from ui.qt import (Qt, QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                   QPushButton, QGridLayout, QLineEdit, QTextEdit, QCheckBox,
                   QFileDialog)
from utils.colorfont import setLineEditBackground
from utils.globals import GlobalData
from utils.misc import preResolveLinkPath


"""Dialog to enter a new text for a graphics item"""

class DocLinkAnchorDialog(QDialog):

    """Replace text input dialog"""

    def __init__(self, windowTitle, cmlDocComment, fileName, parent):
        QDialog.__init__(self, parent)

        # Name of a file from which the doc link is created/edited
        self.__fileName = fileName
        self.setWindowTitle(windowTitle + ' documentation link and/or anchor')

        self.__createLayout()
        self.__invalidInputColor = GlobalData().skin['invalidInputPaper']
        self.__validInputColor = self.linkEdit.palette().color(
            self.linkEdit.backgroundRole())

        if cmlDocComment is not None:
            self.__populate(cmlDocComment)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(450, 150)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        gridLayout = QGridLayout()

        # Link
        gridLayout.addWidget(QLabel('Link', self), 0, 0, 1, 1)
        self.linkEdit = QLineEdit(self)
        self.linkEdit.setClearButtonEnabled(True)
        self.linkEdit.setToolTip(
            'A link to a file or to an external web resource')
        gridLayout.addWidget(self.linkEdit, 0, 1, 1, 1)
        self.linkEdit.textChanged.connect(self.__validate)
        self.fileButton = QPushButton(self)
        self.fileButton.setText('...')
        self.fileButton.setToolTip(
            'Select an existing or non existing file')
        gridLayout.addWidget(self.fileButton, 0, 2, 1, 1)
        self.fileButton.clicked.connect(self.__onSelectPath)
        self.createCheckBox = QCheckBox('Create a markdown file if does not exist', self)
        self.createCheckBox.setChecked(False)
        gridLayout.addWidget(self.createCheckBox, 1, 1, 1, 1)
        self.createCheckBox.stateChanged.connect(self.__validate)

        # Anchor
        gridLayout.addWidget(QLabel('Anchor', self), 2, 0, 1, 1)
        self.anchorEdit = QLineEdit(self)
        self.anchorEdit.setClearButtonEnabled(True)
        gridLayout.addWidget(self.anchorEdit, 2, 1, 1, 1)
        self.anchorEdit.textChanged.connect(self.__validate)

        # Title
        titleLabel = QLabel('Title', self)
        titleLabel.setAlignment(Qt.AlignTop)
        gridLayout.addWidget(titleLabel, 3, 0, 1, 1)
        self.titleEdit = QTextEdit()
        self.titleEdit.setTabChangesFocus(True)
        self.titleEdit.setAcceptRichText(False)
        self.titleEdit.setToolTip(
            'If provided then will be displayed in the rectangle')
        gridLayout.addWidget(self.titleEdit, 3, 1, 1, 1)

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

    def setTitle(self, txt):
        """Sets the title text to be edited"""
        self.titleEdit.setPlainText(txt)

    def title(self):
        """Provides the new title text"""
        return self.titleEdit.toPlainText()

    def needToCreate(self):
        return self.createCheckBox.isEnabled() and self.createCheckBox.isChecked()

    def __populate(self, cmlDocComment):
        """Populates the fields from the comment"""
        if cmlDocComment.link:
            self.linkEdit.setText(cmlDocComment.link)
        if cmlDocComment.anchor:
            self.anchorEdit.setText(cmlDocComment.anchor)
        if cmlDocComment.title:
            self.setTitle(cmlDocComment.getTitle())

    def __onSelectPath(self):
        """Select file or directory"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        selectedPath = QFileDialog.getOpenFileName(
            self, 'Select documentation file', self.linkEdit.text(),
            options=options)
        if isinstance(selectedPath, tuple):
            selectedPath = selectedPath[0]
        if selectedPath:
            self.linkEdit.setText(os.path.normpath(selectedPath))

    def __setLinkValid(self):
        """Sets the link edit valid"""
        self.linkEdit.setToolTip(
            'A link to a file or to an external web resource')
        setLineEditBackground(self.linkEdit, self.__validInputColor,
                              self.__validInputColor)

    def __setLinkInvalid(self, msg):
        """Sets the link edit invalid"""
        self.linkEdit.setToolTip(msg)
        setLineEditBackground(self.linkEdit, self.__invalidInputColor,
                              self.__invalidInputColor)

    def __validateLink(self):
        """Validates the link field content"""
        txt = self.linkEdit.text().strip()
        if txt == '' or txt.startswith('http://') or txt.startswith('https://'):
            self.__setLinkValid()
            self.createCheckBox.setEnabled(False)
            return True

        if txt.endswith(os.path.sep):
            self.__setLinkInvalid('A link must be a file, not a directory')
            return False

        # Not a link; it is supposed to be a file or a creatable file
        # However the invalid values will also be acceptable
        self.createCheckBox.setEnabled(True)
        fromFile = None
        if self.__fileName:
            if os.path.isabs(self.__fileName):
                fromFile = self.__fileName
        fName, anchor, errMsg = preResolveLinkPath(txt, fromFile,
                                                   self.createCheckBox.isChecked())
        del anchor

        if fName:
            self.__setLinkValid()
            return True

        self.__setLinkInvalid(errMsg)
        return not self.createCheckBox.isChecked()

    def __setAnchorValid(self):
        """Sets the anchor edit valid"""
        self.anchorEdit.setToolTip(
            'Anchor may not contain neither spaces nor tabs')
        setLineEditBackground(self.anchorEdit, self.__invalidInputColor,
                              self.__validInputColor)

    def __setAnchorInvalid(self):
        """Sets the anchor edit invalid"""
        self.anchorEdit.setToolTip(
            'Anchor is used to refer to it from the other files')
        setLineEditBackground(self.anchorEdit, self.__validInputColor,
                              self.__validInputColor)

    def __validateAnchor(self):
        """Validates the anchor field"""
        txt = self.anchorEdit.text().strip()
        if ' ' in txt or '\t' in txt:
            self.__setAnchorValid()
            return False
        self.__setAnchorInvalid()
        return True

    def __validate(self, _=None):
        """Validates the input fields and sets the OK button enable"""
        self.__OKButton.setToolTip('')
        valid = self.__validateAnchor() and self.__validateLink()
        if valid:
            if not self.linkEdit.text().strip() and not self.anchorEdit.text().strip():
                valid = False
                self.__OKButton.setToolTip(
                    'At least one of the items: link or anchor must be provided')

        self.__OKButton.setEnabled(valid)
        return valid

