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

"""Codimension garbage collector plugin config dialog"""


from ui.qt import (Qt, QDialog, QVBoxLayout, QGroupBox, QSizePolicy,
                   QRadioButton, QDialogButtonBox)


class GCPluginConfigDialog(QDialog):

    """Garbage collector config dialog"""

    SILENT = 0
    STATUS_BAR = 1
    LOG = 2

    def __init__(self, where, parent=None):
        QDialog.__init__(self, parent)

        self.__createLayout()
        self.setWindowTitle("Garbage collector plugin configuration")

        if where == GCPluginConfigDialog.SILENT:
            self.__silentRButton.setChecked(True)
        elif where == GCPluginConfigDialog.STATUS_BAR:
            self.__statusbarRButton.setChecked(True)
        else:
            self.__logtabRButton.setChecked(True)

        self.__OKButton.setFocus()

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(450, 150)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)

        whereGroupbox = QGroupBox(self)
        whereGroupbox.setTitle("Garbage collector message destination")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            whereGroupbox.sizePolicy().hasHeightForWidth())
        whereGroupbox.setSizePolicy(sizePolicy)

        layoutWhere = QVBoxLayout(whereGroupbox)
        self.__silentRButton = QRadioButton(whereGroupbox)
        self.__silentRButton.setText("Silent")
        layoutWhere.addWidget(self.__silentRButton)
        self.__statusbarRButton = QRadioButton(whereGroupbox)
        self.__statusbarRButton.setText("Status bar")
        layoutWhere.addWidget(self.__statusbarRButton)
        self.__logtabRButton = QRadioButton(whereGroupbox)
        self.__logtabRButton.setText("Log tab")
        layoutWhere.addWidget(self.__logtabRButton)

        verticalLayout.addWidget(whereGroupbox)

        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        self.__OKButton = buttonBox.button(QDialogButtonBox.Ok)
        self.__OKButton.setDefault(True)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.close)
        verticalLayout.addWidget(buttonBox)

    def getCheckedOption(self):
        """Returns what destination is selected"""
        if self.__silentRButton.isChecked():
            return GCPluginConfigDialog.SILENT
        if self.__statusbarRButton.isChecked():
            return GCPluginConfigDialog.STATUS_BAR
        return GCPluginConfigDialog.LOG
