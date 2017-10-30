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

"""Dialog with a list of modified but unsaved files"""

from ui.qt import (Qt, QDialog, QDialogButtonBox, QVBoxLayout, QSizePolicy,
                   QLabel, QHBoxLayout, QTreeWidget, QAbstractItemView,
                   QTreeWidgetItem, QWidget)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import getIcon, getPixmap
from utils.fileutils import getFileProperties, isPythonMime
from utils.globals import GlobalData


class ModifiedUnsavedDialog(QDialog):

    """Dialog with a list of modified but unsaved files implementation"""

    # See utils.run for runParameters
    def __init__(self, files, action, parent=None):
        QDialog.__init__(self, parent)

        count = len(files)
        if count >= 2:
            title = str(count) + " project files are modified and not saved"
        else:
            title = "1 project file modified and not saved"
        self.setWindowTitle(title)
        self.setWindowIcon(getIcon('warning.png'))
        self.__createLayout(action, title, files)

    def __createLayout(self, action, title, files):
        """Creates the dialog layout"""
        self.resize(400, 300)
        self.setSizeGripEnabled(True)

        # Top level layout
        layout = QVBoxLayout(self)

        # Pixmap and the message
        topLayout = QHBoxLayout()
        pixmap = QLabel()
        pixmap.setPixmap(getPixmap('warning.png'))
        topLayout.addWidget(pixmap)
        hSpacer = QWidget()
        hSpacer.setFixedSize(15, 15)
        topLayout.addWidget(hSpacer)
        message = QLabel("All the project files must be "
                         "saved before start debugging")
        message.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        message.setWordWrap(True)
        topLayout.addWidget(message)
        layout.addLayout(topLayout)

        vSpacer = QWidget()
        vSpacer.setFixedSize(15, 15)
        layout.addWidget(vSpacer)

        layout.addWidget(QLabel(title + ":"))
        filesList = QTreeWidget()
        filesList.setRootIsDecorated(False)
        filesList.setAlternatingRowColors(True)
        filesList.setUniformRowHeights(True)
        filesList.setItemsExpandable(False)
        filesList.setItemDelegate(NoOutlineHeightDelegate(4))
        filesList.setSelectionMode(QAbstractItemView.NoSelection)
        filesList.setHeaderHidden(True)
        for item in files:
            fileName = item[0]
            fileItem = QTreeWidgetItem([fileName])
            fileType, icon, _ = getFileProperties(fileName)
            fileItem.setIcon(0, icon)
            if isPythonMime(fileType):
                info = GlobalData().briefModinfoCache.get(fileName)
                fileItem.setToolTip(0, info.docstring.text if info.docstring
                                    else '')
            filesList.addTopLevelItem(fileItem)
        layout.addWidget(filesList)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox()
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        continueButton = buttonBox.addButton(action,
                                             QDialogButtonBox.ActionRole)
        continueButton.setDefault(True)
        layout.addWidget(buttonBox)

        continueButton.clicked.connect(self.accept)
        buttonBox.rejected.connect(self.close)
        continueButton.setFocus()
