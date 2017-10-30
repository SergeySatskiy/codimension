# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Dialog to edit a single breakpoint"""


from ui.qt import (Qt, QDialog, QDialogButtonBox, QVBoxLayout,
                   QLabel, QGridLayout, QSpinBox, QCheckBox)
from utils.pixmapcache import getIcon
from ui.combobox import CDMComboBox
from .breakpoint import Breakpoint


class BreakpointEditDialog( QDialog ):

    """Dialog with a list of modified but unsaved files implementation"""

    # See utils.run for runParameters
    def __init__(self, bpoint, parent=None):
        QDialog.__init__(self, parent)

        self.__origBpoint = bpoint
        self.setWindowTitle("Edit breakpoint properties")
        self.setWindowIcon(getIcon('bpprops.png'))
        self.__createLayout(bpoint)
        self.__OKButton.setEnabled(False)

        self.__conditionValue.lineEdit().textChanged.connect(self.__changed)
        self.__ignoreValue.valueChanged.connect(self.__changed)
        self.__enabled.stateChanged.connect(self.__changed)
        self.__tempCheckbox.stateChanged.connect(self.__changed)

    def __createLayout(self, bpoint):
        """Creates the dialog layout"""
        self.resize(400, 150)
        self.setSizeGripEnabled(True)

        # Top level layout
        layout = QVBoxLayout(self)

        gridLayout = QGridLayout()
        fileLabel = QLabel("File name:")
        gridLayout.addWidget(fileLabel, 0, 0)
        fileValue = QLabel(bpoint.getAbsoluteFileName())
        gridLayout.addWidget(fileValue, 0, 1)
        lineLabel = QLabel("Line:")
        gridLayout.addWidget(lineLabel, 1, 0)
        lineValue = QLabel(str(bpoint.getLineNumber()))
        gridLayout.addWidget(lineValue, 1, 1)
        conditionLabel = QLabel("Condition:")
        gridLayout.addWidget(conditionLabel, 2, 0)
        self.__conditionValue = CDMComboBox(True)
        self.__conditionValue.lineEdit().setText(bpoint.getCondition())
        gridLayout.addWidget(self.__conditionValue, 2, 1)
        ignoreLabel = QLabel("Ignore count:")
        gridLayout.addWidget(ignoreLabel, 3, 0)
        self.__ignoreValue = QSpinBox()
        self.__ignoreValue.setMinimum(0)
        self.__ignoreValue.setValue(bpoint.getIgnoreCount())
        gridLayout.addWidget(self.__ignoreValue, 3, 1)
        layout.addLayout(gridLayout)

        # Checkboxes part
        self.__tempCheckbox = QCheckBox("&Temporary")
        self.__tempCheckbox.setChecked(bpoint.isTemporary())
        layout.addWidget(self.__tempCheckbox)
        self.__enabled = QCheckBox("&Enabled")
        self.__enabled.setChecked(bpoint.isEnabled())
        layout.addWidget(self.__enabled)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        self.__OKButton = buttonBox.button(QDialogButtonBox.Ok)
        self.__OKButton.setDefault(True)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.close)
        layout.addWidget(buttonBox)

        self.__conditionValue.setFocus()

    def __changed(self, skipped=None):
        """Triggered when something has been changed"""
        self.__OKButton.setEnabled(True)

    def getData(self):
        """Provides a new instance of a breakpoint"""
        newBPoint = Breakpoint(self.__origBpoint.getAbsoluteFileName(),
                               self.__origBpoint.getLineNumber(),
                               self.__conditionValue.lineEdit().text().strip(),
                               self.__tempCheckbox.isChecked(),
                               self.__enabled.isChecked(),
                               self.__ignoreValue.value())
        return newBPoint
