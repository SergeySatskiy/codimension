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

"""Goto line widget implementation"""

from utils.pixmapcache import getIcon
from .qt import (QHBoxLayout, QToolButton, QLabel, QSizePolicy, QComboBox,
                 QWidget, QIntValidator, Qt)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class GotoLineWidget(QWidget):

    """goto bar widget"""

    maxHistory = 32

    def __init__(self, editorsManager, parent=None):

        QWidget.__init__(self, parent)
        self.editorsManager = editorsManager

        self.__gotoHistory = []

        # Common graphics items
        closeButton = QToolButton(self)
        closeButton.setToolTip("Click to close the dialog (ESC)")
        closeButton.setIcon(getIcon("close.png"))
        closeButton.clicked.connect(self.hide)

        lineLabel = QLabel(self)
        lineLabel.setText("Goto line:")

        self.linenumberEdit = QComboBox(self)
        self.linenumberEdit.setEditable(True)
        self.linenumberEdit.setInsertPolicy(QComboBox.InsertAtTop)
        self.linenumberEdit.setCompleter(None)
        self.linenumberEdit.setDuplicatesEnabled(False)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.linenumberEdit.sizePolicy().hasHeightForWidth())
        self.linenumberEdit.setSizePolicy(sizePolicy)
        self.validator = QIntValidator(1, 100000, self)
        self.linenumberEdit.setValidator(self.validator)
        self.linenumberEdit.editTextChanged.connect(self.__onEditTextChanged)
        self.linenumberEdit.lineEdit().returnPressed.connect(self.__onEnter)

        self.goButton = QToolButton(self)
        self.goButton.setToolTip("Click to jump to the line (ENTER)")
        self.goButton.setIcon(getIcon("gotoline.png"))
        self.goButton.setFocusPolicy(Qt.NoFocus)
        self.goButton.setEnabled(False)
        self.goButton.clicked.connect(self.__onGo)

        spacer = QWidget()
        spacer.setFixedWidth(1)

        horizontalLayout = QHBoxLayout(self)
        horizontalLayout.setContentsMargins(0, 0, 0, 0)

        horizontalLayout.addWidget(closeButton)
        horizontalLayout.addWidget(lineLabel)
        horizontalLayout.addWidget(self.linenumberEdit)
        horizontalLayout.addWidget(self.goButton)
        horizontalLayout.addWidget(spacer)

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            activeWindow = self.editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()
            event.accept()
            self.hide()

    def __updateHistory(self, txt):
        """Updates the combo history"""
        while txt in self.__gotoHistory:
            self.__gotoHistory.remove(txt)
        self.__gotoHistory = [txt] + self.__gotoHistory
        self.__gotoHistory = self.__gotoHistory[:GotoLineWidget.maxHistory]

        self.linenumberEdit.clear()
        self.linenumberEdit.addItems(self.__gotoHistory)

    def show(self):
        """Overriden show method"""
        self.linenumberEdit.lineEdit().selectAll()
        QWidget.show(self)
        self.activateWindow()

    def setFocus(self):
        """Overridded setFocus"""
        self.linenumberEdit.setFocus()

    def updateStatus(self):
        """Triggered when the current tab is changed"""
        currentWidget = self.editorsManager.currentWidget()
        status = currentWidget.getType() in \
            [MainWindowTabWidgetBase.PlainTextEditor,
             MainWindowTabWidgetBase.VCSAnnotateViewer]
        self.linenumberEdit.setEnabled(status)
        self.goButton.setEnabled(status and
                                 self.linenumberEdit.currentText() != "")

    def __onGo(self):
        """Triggered when the 'Go!' button is clicked"""
        if self.linenumberEdit.currentText() == "":
            return

        currentWidget = self.editorsManager.currentWidget()
        if not currentWidget.getType() in \
           [MainWindowTabWidgetBase.PlainTextEditor,
            MainWindowTabWidgetBase.VCSAnnotateViewer]:
            return

        txt = self.linenumberEdit.currentText()
        self.__updateHistory(txt)
        editor = currentWidget.getEditor()
        line = min(int(txt), len(editor.lines)) - 1

        editor.cursorPosition = line, 0
        editor.ensureLineOnScreen(line)
        currentWidget.setFocus()

    def __onEditTextChanged(self, text):
        """Triggered when the text has been changed"""
        self.goButton.setEnabled(text != "")

    def __onEnter(self):
        """Triggered when 'Enter' or 'Return' is clicked"""
        self.__onGo()

    def selectAll(self):
        """Selects the line edit content"""
        self.linenumberEdit.lineEdit().selectAll()
