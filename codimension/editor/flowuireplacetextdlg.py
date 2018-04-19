# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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
                   QTextEdit)


"""Dialog to enter a new text for a graphics item"""

class ReplaceTextDialog(QDialog):

    """Replace text input dialog"""

    def __init__(self, windowTitle, labelText, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(windowTitle)
        self.__createLayout(labelText)

    def __createLayout(self, labelText):
        """Creates the dialog layout"""
        self.resize(600, 250)
        self.setSizeGripEnabled(True)

        # Top level layout
        layout = QVBoxLayout(self)
 
        layout.addWidget(QLabel(labelText))
        self.__newCaption = QTextEdit()
        self.__newCaption.setAcceptRichText(False)
        layout.addWidget(self.__newCaption)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.__OKButton = buttonBox.button(QDialogButtonBox.Ok)
        self.__OKButton.setDefault(True)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.close)
        layout.addWidget(buttonBox)

        self.__newCaption.setFocus()

    def setText(self, txt):
        """Sets the text to be edited"""
        self.__newCaption.setPlainText(txt)

    def text(self):
        """Provides the new text"""
        return self.__newCaption.toPlainText()
