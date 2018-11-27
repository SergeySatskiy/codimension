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

"""project properties dialog"""

import os
from os.path import relpath
import pwd
import socket
import datetime
import logging
from utils.project import getProjectProperties
from utils.misc import getLocaleDate
from utils.settings import SETTINGS_DIR
from utils.encoding import SUPPORTED_CODECS, isValidEncoding
from .qt import (Qt, QEvent, QObject, QDialog, QLineEdit, QGridLayout, QLabel,
                 QTextEdit, QDialogButtonBox, QVBoxLayout, QPushButton,
                 QFileDialog, QMessageBox, QListWidget, QAbstractItemView,
                 QApplication, QComboBox)
from .fitlabel import FramedLabelWithDoubleClick
from .itemdelegates import NoOutlineHeightDelegate
from .completers import DirCompleter, FileCompleter


class ProjectPropertiesDialog(QDialog):

    """project properties dialog implementation"""

    def __init__(self, project=None, parent=None):
        QDialog.__init__(self, parent)

        # The dialog caller reads this member if the dialog was finished
        # successfully.
        self.absProjectFileName = None

        self.__createLayout()
        self.__project = project

        if project is None:
            # It a new project creation
            self.setWindowTitle("New Project Properties")

            userRecord = pwd.getpwuid(os.getuid())

            if not userRecord[5].endswith(os.path.sep):
                self.dirEdit.setText(userRecord[5] + os.path.sep)
            else:
                self.dirEdit.setText(userRecord[5])
            self.initialDirName = self.dirEdit.text()
            self.lastProjectName = ""

            if userRecord[4] != "":
                self.authorEdit.setText(userRecord[4].split(',')[0].strip())
            else:
                self.authorEdit.setText(userRecord[0])

            try:
                self.emailEdit.setText(userRecord[0] + "@" +
                                       socket.gethostname())
            except:
                pass

            self.versionEdit.setText("0.0.1")
            self.licenseEdit.setText("GPL v3")
            self.copyrightEdit.setText("Copyright (c) " +
                                       self.authorEdit.text() + ", " +
                                       str(datetime.date.today().year))
            self.creationDateEdit.setText(getLocaleDate())
            self.nameEdit.setFocus()

        elif isinstance(project, str):
            self.setWindowTitle("Viewing Project Properties")

            # This is viewing properties and the argument is the path to the
            # project file
            props = getProjectProperties(project)

            scriptName = props['scriptname']
            if not os.path.isabs(scriptName) and scriptName != "":
                scriptName = os.path.normpath(os.path.dirname(project) +
                                              os.path.sep + scriptName)
            mdDocName = props['mddocfile']
            if not os.path.isabs(mdDocName) and mdDocName != '':
                mdDocName = os.path.normpath(os.path.dirname(project) +
                                             os.path.sep + mdDocName)

            self.nameEdit.setText(os.path.basename(project))
            self.nameEdit.setToolTip("")
            self.dirEdit.setText(os.path.dirname(project))
            self.dirEdit.setToolTip("")
            self.scriptEdit.setText(scriptName)
            self.mdDocEdit.setText(mdDocName)
            self.versionEdit.setText(props['version'])
            self.authorEdit.setText(props['author'])
            self.emailEdit.setText(props['email'])
            self.licenseEdit.setText(props['license'])
            self.copyrightEdit.setText(props['copyright'])
            self.descriptionEdit.setText(props['description'])
            self.encodingCombo.setCurrentText(props['encoding'])
            self.creationDateEdit.setText(props['creationdate'])
            self.uuidEdit.setText(props['uuid'])
            self.uuidEdit.setToolTip(SETTINGS_DIR + props['uuid'] +
                                     os.path.sep +
                                     " (double click to copy path)")

            for item in props['importdirs']:
                self.importDirList.addItem(item)

            self.disableEditing()
        else:
            self.setWindowTitle("Editing Project Properties")

            # This is editing the loaded project.
            self.nameEdit.setText(os.path.basename(project.fileName))
            self.nameEdit.setToolTip("")
            self.dirEdit.setText(project.getProjectDir())
            self.dirEdit.setToolTip("")
            self.scriptEdit.setText(project.getProjectScript())
            self.mdDocEdit.setText(project.getStartupMarkdownFile())
            self.versionEdit.setText(project.props['version'])
            self.authorEdit.setText(project.props['author'])
            self.emailEdit.setText(project.props['email'])
            self.licenseEdit.setText(project.props['license'])
            self.copyrightEdit.setText(project.props['copyright'])
            self.descriptionEdit.setText(project.props['description'])
            self.encodingCombo.setCurrentText(project.props['encoding'])
            self.creationDateEdit.setText(project.props['creationdate'])
            self.uuidEdit.setText(project.props['uuid'])
            self.uuidEdit.setToolTip(project.userProjectDir +
                                     " (double click to copy path)")
            self.setReadOnly()

            for item in project.props['importdirs']:
                self.importDirList.addItem(item)
            if self.importDirList.count() > 0:
                self.importDirList.setCurrentRow(0)
                self.delImportDirButton.setEnabled(True)

            # The project could be the one belonging to another user
            # so there might be no write permissions.
            if not os.access(project.fileName, os.W_OK):
                # Disable editing
                self.setWindowTitle("Viewing Project Properties "
                                    "(no write permissions)")
                self.disableEditing()
            else:
                self.scriptEdit.setFocus()

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(600, 400)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        gridLayout = QGridLayout()

        # Project name
        nameLabel = QLabel("Project name:", self)
        gridLayout.addWidget(nameLabel, 0, 0, 1, 1)
        self.nameEdit = QLineEdit(self)
        self.nameEdit.setToolTip("Type a project name without a path")
        self.nameEdit.installEventFilter(self)
        gridLayout.addWidget(self.nameEdit, 0, 1, 1, 1)

        # Project dir
        dirLabel = QLabel("Project directory:", self)
        gridLayout.addWidget(dirLabel, 1, 0, 1, 1)
        self.dirEdit = QLineEdit(self)
        self.dirEdit.setToolTip("Not existed directories will be created")
        gridLayout.addWidget(self.dirEdit, 1, 1, 1, 1)
        self.dirButton = QPushButton(self)
        self.dirButton.setText("...")
        gridLayout.addWidget(self.dirButton, 1, 2, 1, 1)
        self.dirCompleter = DirCompleter(self.dirEdit)

        # Project script
        mainScriptLabel = QLabel("Main script:", self)
        gridLayout.addWidget(mainScriptLabel, 2, 0, 1, 1)
        self.scriptEdit = QLineEdit(self)
        self.scriptEdit.setToolTip("Project main script, "
                                   "used when the project is run")
        gridLayout.addWidget(self.scriptEdit, 2, 1, 1, 1)
        self.scriptButton = QPushButton("...", self)
        gridLayout.addWidget(self.scriptButton, 2, 2, 1, 1)
        self.fileCompleter = FileCompleter(self.scriptEdit)

        # Project markdown doc file
        mddocLabel = QLabel('Markdown doc file:', self)
        gridLayout.addWidget(mddocLabel, 3, 0, 1, 1)
        self.mdDocEdit = QLineEdit(self)
        self.mdDocEdit.setToolTip('Project documentation start file')
        gridLayout.addWidget(self.mdDocEdit, 3, 1, 1, 1)
        self.mdDocButton = QPushButton("...", self)
        gridLayout.addWidget(self.mdDocButton, 3, 2, 1, 1)
        self.mdFileCompleter = FileCompleter(self.mdDocEdit)

        # Import dirs
        importLabel = QLabel("Import directories:", self)
        importLabel.setAlignment(Qt.AlignTop)
        gridLayout.addWidget(importLabel, 4, 0, 1, 1)
        self.importDirList = QListWidget(self)
        self.importDirList.setAlternatingRowColors(True)
        self.importDirList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.importDirList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.importDirList.setItemDelegate(NoOutlineHeightDelegate(4))
        self.importDirList.setToolTip("Directories where to look for "
                                      "project specific imports")
        gridLayout.addWidget(self.importDirList, 4, 1, 1, 1)

        self.addImportDirButton = QPushButton(self)
        self.addImportDirButton.setText("Add dir")
        self.delImportDirButton = QPushButton(self)
        self.delImportDirButton.setText("Delete dir")
        self.delImportDirButton.setEnabled(False)
        vLayout = QVBoxLayout()
        vLayout.addWidget(self.addImportDirButton)
        vLayout.addWidget(self.delImportDirButton)
        vLayout.addStretch(0)
        gridLayout.addLayout(vLayout, 4, 2, 1, 1)

        # Version
        versionLabel = QLabel("Version:", self)
        gridLayout.addWidget(versionLabel, 5, 0, 1, 1)
        self.versionEdit = QLineEdit(self)
        gridLayout.addWidget(self.versionEdit, 5, 1, 1, 1)

        # Author
        authorLabel = QLabel("Author:", self)
        gridLayout.addWidget(authorLabel, 6, 0, 1, 1)
        self.authorEdit = QLineEdit(self)
        gridLayout.addWidget(self.authorEdit, 6, 1, 1, 1)

        # E-mail
        emailLabel = QLabel("E-mail:", self)
        gridLayout.addWidget(emailLabel, 7, 0, 1, 1)
        self.emailEdit = QLineEdit(self)
        gridLayout.addWidget(self.emailEdit, 7, 1, 1, 1)

        # License
        licenseLabel = QLabel("License:", self)
        gridLayout.addWidget(licenseLabel, 8, 0, 1, 1)
        self.licenseEdit = QLineEdit(self)
        gridLayout.addWidget(self.licenseEdit, 8, 1, 1, 1)

        # Copyright
        copyrightLabel = QLabel("Copyright:", self)
        gridLayout.addWidget(copyrightLabel, 9, 0, 1, 1)
        self.copyrightEdit = QLineEdit(self)
        gridLayout.addWidget(self.copyrightEdit, 9, 1, 1, 1)

        # Description
        descriptionLabel = QLabel("Description:", self)
        descriptionLabel.setAlignment(Qt.AlignTop)
        gridLayout.addWidget(descriptionLabel, 10, 0, 1, 1)
        self.descriptionEdit = QTextEdit(self)
        self.descriptionEdit.setTabChangesFocus(True)
        self.descriptionEdit.setAcceptRichText(False)
        gridLayout.addWidget(self.descriptionEdit, 10, 1, 1, 1)

        # Default encoding
        encodingLabel = QLabel('Default encoding:', self)
        gridLayout.addWidget(encodingLabel, 11, 0, 1, 1)
        self.encodingCombo = QComboBox(self)
        self.encodingCombo.addItem('')
        self.encodingCombo.addItems(sorted(SUPPORTED_CODECS))
        self.encodingCombo.setEditable(True)
        gridLayout.addWidget(self.encodingCombo, 11, 1, 1, 1)

        # Creation date
        creationDateLabel = QLabel("Creation date:", self)
        gridLayout.addWidget(creationDateLabel, 12, 0, 1, 1)
        self.creationDateEdit = FramedLabelWithDoubleClick()
        self.creationDateEdit.setToolTip("Double click to copy")
        gridLayout.addWidget(self.creationDateEdit, 12, 1, 1, 1)

        # Project UUID
        uuidLabel = QLabel("UUID:", self)
        gridLayout.addWidget(uuidLabel, 13, 0, 1, 1)
        self.uuidEdit = FramedLabelWithDoubleClick("", self.__copyProjectPath)
        gridLayout.addWidget(self.uuidEdit, 13, 1, 1, 1)

        verticalLayout.addLayout(gridLayout)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel |
                                     QDialogButtonBox.Ok)
        verticalLayout.addWidget(buttonBox)

        nameLabel.setBuddy(self.nameEdit)
        dirLabel.setBuddy(self.dirEdit)
        versionLabel.setBuddy(self.versionEdit)
        authorLabel.setBuddy(self.authorEdit)
        emailLabel.setBuddy(self.emailEdit)
        licenseLabel.setBuddy(self.licenseEdit)
        copyrightLabel.setBuddy(self.copyrightEdit)
        descriptionLabel.setBuddy(self.descriptionEdit)

        buttonBox.accepted.connect(self.onOKButton)
        buttonBox.rejected.connect(self.reject)
        self.dirButton.clicked.connect(self.onDirButton)
        self.scriptButton.clicked.connect(self.onScriptButton)
        self.mdDocButton.clicked.connect(self.onMdDocButton)
        self.importDirList.currentRowChanged.connect(self.onImportDirRowChanged)
        self.addImportDirButton.clicked.connect(self.onAddImportDir)
        self.delImportDirButton.clicked.connect(self.onDelImportDir)
        self.nameEdit.textEdited.connect(self.onProjectNameChanged)

        self.setTabOrder(self.nameEdit, self.dirEdit)
        self.setTabOrder(self.dirEdit, self.dirButton)
        self.setTabOrder(self.dirButton, self.scriptEdit)
        self.setTabOrder(self.scriptEdit, self.scriptButton)
        self.setTabOrder(self.scriptButton, self.mdDocEdit)
        self.setTabOrder(self.mdDocEdit, self.mdDocButton)
        self.setTabOrder(self.mdDocButton, self.importDirList)
        self.setTabOrder(self.importDirList, self.addImportDirButton)
        self.setTabOrder(self.addImportDirButton, self.delImportDirButton)
        self.setTabOrder(self.delImportDirButton, self.versionEdit)
        self.setTabOrder(self.versionEdit, self.authorEdit)
        self.setTabOrder(self.authorEdit, self.emailEdit)
        self.setTabOrder(self.emailEdit, self.licenseEdit)
        self.setTabOrder(self.licenseEdit, self.copyrightEdit)
        self.setTabOrder(self.copyrightEdit, self.descriptionEdit)
        self.setTabOrder(self.descriptionEdit, buttonBox)

    def eventFilter(self, obj, event):
        """Event filter for the project name field"""
        # Do not allow path separators
        if event.type() == QEvent.KeyPress:
            if event.key() == ord(os.path.sep):
                return True
        return QObject.eventFilter(self, obj, event)

    def onDirButton(self):
        """Displays a directory selection dialog"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly
        dirName = QFileDialog.getExistingDirectory(
            self, "Select project directory", self.dirEdit.text(),
            options)
        if dirName:
            self.dirEdit.setText(os.path.normpath(dirName))

    def onScriptButton(self):
        """Displays a file selection dialog"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        scriptName = QFileDialog.getOpenFileName(
            self, 'Select project main script', self.dirEdit.text(),
            'Python Files (*.py);;All Files (*)',
            options=options)
        if isinstance(scriptName, tuple):
            scriptName = scriptName[0]
        if scriptName:
            self.scriptEdit.setText(os.path.normpath(scriptName))

    def onMdDocButton(self):
        """Displays an md file selection dialog"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        mdFileName = QFileDialog.getOpenFileName(
            self, 'Select project doc startup MD file', self.dirEdit.text(),
            'Markdown Files (*.md);;All Files (*)',
            options=options)
        if isinstance(mdFileName, tuple):
            mdFileName = mdFileName[0]
        if mdFileName:
            self.mdDocEdit.setText(os.path.normpath(mdFileName))

    def onImportDirRowChanged(self, row):
        """Triggered when a current row in the import dirs is changed"""
        self.delImportDirButton.setEnabled(row != -1)

    def onAddImportDir(self):
        """Displays a directory selection dialog"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly
        dirName = QFileDialog.getExistingDirectory(
            self, 'Select import directory', self.dirEdit.text(),
            options=options)

        if not dirName:
            return

        # There are 2 cases: new project or
        # editing the existed project properties
        if self.__project is None:
            # It a new project; the project path could be editedd
            dirToInsert = dirName
        else:
            # This is an existed project; no way the project path is changed
            # Let's decide it a relative path should be used here
            if self.__project.isProjectDir(dirName):
                dirToInsert = relpath(dirName, self.dirEdit.text())
            else:
                dirToInsert = dirName

        index = 0
        while index < self.importDirList.count():
            if self.importDirList.item(index).text() == dirToInsert:
                logging.warning("The directory '" + dirName +
                                "' is already in the list of "
                                "imported directories and is not added.")
                return
            index += 1

        self.importDirList.addItem(dirToInsert)
        self.importDirList.setCurrentRow(self.importDirList.count() - 1)

    def onDelImportDir(self):
        """Triggered when an import dir should be deleted"""
        rowToDelete = self.importDirList.currentRow()
        if  rowToDelete == -1:
            self.delImportDirButton.setEnabled(False)
            return

        self.importDirList.takeItem(rowToDelete)
        if self.importDirList.count() == 0:
            self.delImportDirButton.setEnabled(False)
        else:
            self.importDirList.setCurrentRow(self.importDirList.count() - 1)

    def onOKButton(self):
        """Checks that the mandatory fields are filled properly"""
        # The checks must be done for a new project only
        if not self.nameEdit.isEnabled():
            if self.__checkEncoding():
                self.accept()
            return

        # Check that the project name does not have path separators and is not
        # empty
        if not self.nameEdit.text().strip():
            QMessageBox.critical(self, "Error",
                                 "The project name must not be empty")
            return
        if os.path.sep in self.nameEdit.text():
            QMessageBox.critical(self, "Error",
                                 "The project name must not "
                                 "contain path separators")
            return

        # Check that the project directory is given
        dirName = self.dirEdit.text().strip()
        if not dirName:
            QMessageBox.critical(self, "Error",
                                 "The project directory must not be empty")
            return

        dirName = os.path.abspath(dirName)
        self.dirEdit.setText(dirName)
        # Check that the project file does not exist
        projectFileName = dirName
        if not projectFileName.endswith(os.path.sep):
            projectFileName += os.path.sep
        projectFileName += self.nameEdit.text().strip()
        if not projectFileName.endswith(".cdm3"):
            projectFileName += ".cdm3"

        if os.path.exists(projectFileName):
            QMessageBox.critical(self, "Error",
                                 "The project file " + projectFileName +
                                 " exists. Please provide another "
                                 "directory / project name.")
            return

        # Check that the project dir is not a file
        if os.path.exists(dirName):
            # It might be a link, so read it first
            dirName = os.path.realpath(dirName)
            if not os.path.exists(dirName):
                QMessageBox.critical(self, "Error",
                                     "Broken link: " + dirName)
                return
            if not os.path.isdir(dirName):
                QMessageBox.critical(self, "Error",
                                     "The project directory may not be a file")
                return
            # Check that the dir is writable
            if not os.access(dirName, os.W_OK):
                QMessageBox.critical(self, "Error",
                                     "You don't have write permissions on " +
                                     dirName)
                return
        else:
            # Create the directory
            try:
                os.makedirs(dirName)
            except OSError:
                QMessageBox.critical(self, "Error",
                                     "Cannot create the project directory")
                return

        if not self.__checkEncoding():
            return

        # Save the absolute file name for further reading it by the caller
        self.absProjectFileName = projectFileName

        # The minimum is provided so we can accept it
        self.accept()

    def __checkEncoding(self):
        """True if OK"""
        enc = self.encodingCombo.currentText().strip()
        if enc:
            if not isValidEncoding(enc):
                QMessageBox.critical(self, "Error",
                                     "Unsupported default project encoding")
                return False
        return True

    def onProjectNameChanged(self, newName):
        """Called when the project name changed"""
        if newName.endswith(".cdm3"):
            newName = newName[:-5]
        if self.dirEdit.text().strip() == (self.initialDirName +
                                           self.lastProjectName):
            self.dirEdit.setText(self.initialDirName + newName)
            self.lastProjectName = newName

    def setReadOnly(self):
        """Disables editing some fields"""
        self.dirEdit.setReadOnly(True)
        self.dirEdit.setFocusPolicy(Qt.NoFocus)
        self.dirEdit.setDisabled(True)
        self.dirButton.setDisabled(True)
        self.dirButton.setFocusPolicy(Qt.NoFocus)
        self.nameEdit.setReadOnly(True)
        self.nameEdit.setFocusPolicy(Qt.NoFocus)
        self.nameEdit.setDisabled(True)

    def disableEditing(self):
        """Disables all the editing"""
        self.nameEdit.setDisabled(True)
        self.dirEdit.setDisabled(True)
        self.dirButton.setDisabled(True)
        self.scriptEdit.setDisabled(True)
        self.scriptButton.setDisabled(True)
        self.mdDocEdit.setDisabled(True)
        self.mdDocButton.setDisabled(True)
        self.importDirList.setDisabled(True)
        self.addImportDirButton.setDisabled(True)
        self.delImportDirButton.setDisabled(True)
        self.versionEdit.setDisabled(True)
        self.authorEdit.setDisabled(True)
        self.emailEdit.setDisabled(True)
        self.licenseEdit.setDisabled(True)
        self.copyrightEdit.setDisabled(True)
        self.descriptionEdit.setDisabled(True)
        self.encodingCombo.setDisabled(True)

    def __copyProjectPath(self):
        """Copies the project path when a label is double clicked"""
        text = self.uuidEdit.text().strip()
        if text:
            path = SETTINGS_DIR + text + os.path.sep
            QApplication.clipboard().setText(path)
