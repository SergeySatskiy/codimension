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

"""Codimension SVN plugin config dialog"""


import os.path
import logging
import copy
import stat
import base64
from subprocess import check_output
import svn
from cryptography.fernet import Fernet
from ui.qt import (Qt, QDialog, QVBoxLayout, QGroupBox, QSizePolicy,
                   QRadioButton, QDialogButtonBox, QPixmap, QHBoxLayout,
                   QLabel, QTabWidget, QWidget, QGridLayout, QLineEdit,
                   QTextBrowser)
from utils.fileutils import saveJSON, loadJSON


AUTH_EXTERNAL = 0               # No user/password or external authorization
AUTH_PASSWD = 1                 # The user name and password are used

STATUS_LOCAL_ONLY = 0           # Checks only the local status
STATUS_REPOSITORY = 1           # Checks both local status and the repository


class SVNSettings:

    """Holds SVN settings"""

    def __init__(self):
        self.authKind = AUTH_EXTERNAL
        self.userName = None    # if so then encrypted with self.key when saved
        self.password = None    # if so then encrypted with self.key when saved
        self.key = None
        self.statusKind = STATUS_REPOSITORY

def __getDefaultJSONContent():
    """Provides the default settings dictionary"""
    settings = SVNSettings()
    content = {'authKind': settings.authKind,
               'statusKind': settings.statusKind,
               'userName': None,
               'password': None,
               'key': None}
    return content


def __binToString(value):
    """Encodes the input value as base64 bin and converts it to string"""
    base64Bin = base64.b64encode(value)
    return str(base64Bin, 'utf-8')

def __stringToBin(value):
    """Decodes the value from string and converts it to bin"""
    base64bin = value.encode('utf-8')
    return base64.b64decode(base64bin)


def saveSVNSettings(settings, fName):
    """Saves settings to the file"""
    if settings.userName or settings.password:
        if not settings.key:
            # Generate a new key
            settings.key = Fernet.generate_key()
        fernet = Fernet(settings.key)

    content = __getDefaultJSONContent()
    if settings.key:
        content['key'] = __binToString(settings.key)
    if settings.userName:
        encoded = fernet.encrypt(settings.userName.encode('utf-8'))
        content['userName'] = str(encoded, 'utf-8')
    if settings.password:
        encoded = fernet.encrypt(settings.password.encode('utf-8'))
        content['password'] = str(encoded, 'utf-8')

    if saveJSON(fName, content, 'SVN plugin settings'):
        try:
            os.chmod(fName, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as exc:
            logging.error('Error changing SVN plugin settings permissions (' +
                          fName + '): ' + str(exc))


def getSettings(fName):
    """Reads settings. If the file does not exist - creates default"""
    try:
        settings = SVNSettings()
        if os.path.exists(fName):
            # File exists, read it
            content = loadJSON(fName, 'SVN plugin settings',
                               __getDefaultJSONContent())

            if content['authKind'] in [AUTH_EXTERNAL, AUTH_PASSWD]:
                settings.authKind = content['authKind']
                if content['key']:
                    settings.key = __stringToBin(content['authKind'])
                    fernet = Fernet(settings.key)

                if content['userName']:
                    if not settings.key:
                        raise Exception('Inconsistency detected: a key is '
                                        'required if user name is provided')
                    settings.userName = fernet.decrypt(
                        __stringToBin(content['userName']))
                if content['password']:
                    if not settings.key:
                        raise Exception('Inconsistency detected: a key is '
                                        'required if password is provided')
                    settings.password = fernet.decrypt(
                        __stringToBin(content['password']))
            else:
                logging.error('Unexpected SVN plugin authirization kind '
                              'setting value. Reset to default.')
                settings.authKind = AUTH_EXTERNAL


            if content['statusKind'] in [STATUS_LOCAL_ONLY, STATUS_REPOSITORY]:
                settings.statusKind = content['statusKind']
            else:
                logging.error('Unexpected SVN plugin status kind '
                              'setting value. Reset to default.')
                settings.statusKind = STATUS_REPOSITORY
        else:
            # File does not exist - create default settings
            saveSVNSettings(settings, fName)
        return settings
    except Exception as exc:
        logging.error("Error retrieving SVN plugin settings from " + fName +
                      ". Using default settings.\nException: " + str(exc))
        return SVNSettings()


class SVNPluginConfigDialog(QDialog):

    """
    SVN Plugin config dialog
    """

    def __init__(self, ideWideSettings, projectSettings, parent=None):
        QDialog.__init__(self, parent)

        self.__projectLocalRButton = None
        self.__idewideUser = None
        self.__idewideLocalRButton = None
        self.__projectReposRButton = None
        self.__idewideAuthPasswdRButton = None
        self.__projectPasswd = None
        self.__projectUser = None
        self.__projectAuthExtRButton = None
        self.__idewidePasswd = None
        self.__idewideAuthExtRButton = None
        self.__projectAuthPasswdRButton = None
        self.__idewideReposRButton = None

        self.__createLayout()
        self.setWindowTitle("SVN plugin configuration")

        self.ideWideSettings = copy.deepcopy(ideWideSettings)
        if projectSettings is None:
            self.projectSettings = None
        else:
            self.projectSettings = copy.deepcopy(projectSettings)

        # Set the values
        self.__setIDEWideValues()
        if projectSettings is None:
            self.__tabWidget.setTabEnabled(1, False)
        else:
            self.__setProjectValues()
            self.__tabWidget.setCurrentIndex(1)
        self.__updateOKStatus()

        self.__idewideUser.textChanged.connect(self.__updateOKStatus)
        self.__projectUser.textChanged.connect(self.__updateOKStatus)

    def __setIDEWideValues(self):
        """Sets the values in the IDE wide tab"""
        if self.ideWideSettings.authKind == AUTH_EXTERNAL:
            self.__idewideAuthExtRButton.setChecked(True)
            self.__idewideUser.setEnabled(False)
            self.__idewidePasswd.setEnabled(False)
        else:
            self.__idewideAuthPasswdRButton.setChecked(True)
            if self.ideWideSettings.userName:
                self.__idewideUser.setText(self.ideWideSettings.userName)
            if self.ideWideSettings.password:
                self.__idewidePasswd.setText(self.ideWideSettings.password)

        if self.ideWideSettings.statusKind == STATUS_REPOSITORY:
            self.__idewideReposRButton.setChecked(True)
        else:
            self.__idewideLocalRButton.setChecked(True)

    def __setProjectValues(self):
        """Sets the values in the project tab"""
        if self.projectSettings.authKind == AUTH_EXTERNAL:
            self.__projectAuthExtRButton.setChecked(True)
            self.__projectUser.setEnabled(False)
            self.__projectPasswd.setEnabled(False)
        else:
            self.__projectAuthPasswdRButton.setChecked(True)
            if self.projectSettings.userName:
                self.__projectUser.setText(self.projectSettings.userName)
            if self.projectSettings.password:
                self.__projectPasswd.setText(self.projectSettings.password)

        if self.projectSettings.statusKind == STATUS_REPOSITORY:
            self.__projectReposRButton.setChecked(True)
        else:
            self.__projectLocalRButton.setChecked(True)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(640, 420)
        self.setSizeGripEnabled(True)

        vboxLayout = QVBoxLayout(self)
        hboxLayout = QHBoxLayout()
        iconLabel = QLabel()
        logoPath = os.path.dirname(os.path.abspath(__file__)) + \
                   os.path.sep + "svn-logo.png"
        iconLabel.setPixmap(QPixmap(logoPath))
        iconLabel.setScaledContents(True)
        iconLabel.setFixedSize(48, 48)
        hboxLayout.addWidget(iconLabel)
        titleLabel = QLabel("Codimension SVN plugin settings")
        titleLabel.setSizePolicy(QSizePolicy.Expanding,
                                 QSizePolicy.Expanding)
        titleLabel.setFixedHeight(48)
        titleLabel.setAlignment(Qt.AlignCenter)
        hboxLayout.addWidget(titleLabel)
        vboxLayout.addLayout(hboxLayout)

        self.__tabWidget = QTabWidget(self)
        self.__tabWidget.setFocusPolicy(Qt.NoFocus)

        ideWide = self.__createIDEWide()
        self.__tabWidget.addTab(ideWide, "IDE Wide")
        projectSpecific = self.__createProjectSpecific()
        self.__tabWidget.addTab(projectSpecific, "Project Specific")
        version = self.__createVersionWidget()
        self.__tabWidget.addTab(version, "Versions")
        vboxLayout.addWidget(self.__tabWidget)

        # Buttons at the bottom
        self.__buttonBox = QDialogButtonBox(self)
        self.__buttonBox.setOrientation(Qt.Horizontal)
        self.__buttonBox.setStandardButtons(QDialogButtonBox.Ok |
                                            QDialogButtonBox.Cancel)
        self.__buttonBox.accepted.connect(self.userAccept)
        self.__buttonBox.rejected.connect(self.close)
        vboxLayout.addWidget(self.__buttonBox)

    def __createIDEWide(self):
        """Creates the IDE wide part"""
        widget = QWidget()

        verticalLayout = QVBoxLayout(widget)
        infoLabel = QLabel("Note: the settings below are used "
                           "when there is no project loaded.")
        verticalLayout.addWidget(infoLabel)

        # Authorization group box
        authGroupbox = QGroupBox(self)
        authGroupbox.setTitle("Authorization")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            authGroupbox.sizePolicy().hasHeightForWidth())
        authGroupbox.setSizePolicy(sizePolicy)

        layoutAuth = QVBoxLayout(authGroupbox)
        self.__idewideAuthExtRButton = QRadioButton("External", authGroupbox)
        self.__idewideAuthExtRButton.clicked.connect(self.__idewideAuthChanged)
        layoutAuth.addWidget(self.__idewideAuthExtRButton)
        self.__idewideAuthPasswdRButton = QRadioButton(
            "Use user name / password", authGroupbox)
        self.__idewideAuthPasswdRButton.clicked.connect(
            self.__idewideAuthChanged)
        layoutAuth.addWidget(self.__idewideAuthPasswdRButton)

        upLayout = QGridLayout()
        self.__idewideUser = QLineEdit()
        self.__idewideUser.setToolTip("Attention: user name is "
                                      "saved unencrypted")
        self.__idewidePasswd = QLineEdit()
        self.__idewidePasswd.setToolTip("Attention: password is "
                                        "saved unencrypted")
        spacer = QWidget()
        spacer.setFixedWidth(16)
        upLayout.addWidget(spacer, 0, 0)
        upLayout.addWidget(QLabel("User name"), 0, 1)
        upLayout.addWidget(self.__idewideUser, 0, 2)
        upLayout.addWidget(QLabel("Password"), 1, 1)
        upLayout.addWidget(self.__idewidePasswd, 1, 2)
        layoutAuth.addLayout(upLayout)

        # Update status group box
        updateGroupbox = QGroupBox(self)
        updateGroupbox.setTitle("Update status policy")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            updateGroupbox.sizePolicy().hasHeightForWidth())
        updateGroupbox.setSizePolicy(sizePolicy)

        layoutUpdate = QVBoxLayout(updateGroupbox)
        self.__idewideReposRButton = QRadioButton("Check repository",
                                                  updateGroupbox)
        layoutUpdate.addWidget(self.__idewideReposRButton)
        self.__idewideLocalRButton = QRadioButton("Local only",
                                                  updateGroupbox)
        layoutUpdate.addWidget(self.__idewideLocalRButton)

        verticalLayout.addWidget(authGroupbox)
        verticalLayout.addWidget(updateGroupbox)
        return widget

    def __idewideAuthChanged(self):
        """Triggered when authorization has been changed"""
        if self.__idewideAuthExtRButton.isChecked():
            self.__idewideUser.setEnabled(False)
            self.__idewidePasswd.setEnabled(False)
        else:
            self.__idewideUser.setEnabled(True)
            self.__idewidePasswd.setEnabled(True)
            self.__idewideUser.setFocus()
        self.__updateOKStatus()

    def __createProjectSpecific(self):
        """Creates the project specific part"""
        widget = QWidget()

        verticalLayout = QVBoxLayout(widget)
        infoLabel = QLabel("Note: the settings below are used "
                           "only for the specific project.")
        verticalLayout.addWidget(infoLabel)

        # Authorization group box
        authGroupbox = QGroupBox(self)
        authGroupbox.setTitle("Authorization")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            authGroupbox.sizePolicy().hasHeightForWidth())
        authGroupbox.setSizePolicy(sizePolicy)

        layoutAuth = QVBoxLayout(authGroupbox)
        self.__projectAuthExtRButton = QRadioButton("External", authGroupbox)
        self.__projectAuthExtRButton.clicked.connect(self.__projectAuthChanged)
        layoutAuth.addWidget(self.__projectAuthExtRButton)
        self.__projectAuthPasswdRButton = QRadioButton(
            "Use user name / password", authGroupbox)
        self.__projectAuthPasswdRButton.clicked.connect(
            self.__projectAuthChanged)
        layoutAuth.addWidget(self.__projectAuthPasswdRButton)

        upLayout = QGridLayout()
        self.__projectUser = QLineEdit()
        self.__projectUser.setToolTip("Attention: user name is "
                                      "saved unencrypted")
        self.__projectPasswd = QLineEdit()
        self.__projectPasswd.setToolTip("Attention: password is "
                                        "saved unencrypted")
        spacer = QWidget()
        spacer.setFixedWidth(16)
        upLayout.addWidget(spacer, 0, 0)
        upLayout.addWidget(QLabel("User name"), 0, 1)
        upLayout.addWidget(self.__projectUser, 0, 2)
        upLayout.addWidget(QLabel("Password"), 1, 1)
        upLayout.addWidget(self.__projectPasswd, 1, 2)
        layoutAuth.addLayout(upLayout)

        # Update status group box
        updateGroupbox = QGroupBox(self)
        updateGroupbox.setTitle("Update status policy")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            updateGroupbox.sizePolicy().hasHeightForWidth())
        updateGroupbox.setSizePolicy(sizePolicy)

        layoutUpdate = QVBoxLayout(updateGroupbox)
        self.__projectReposRButton = QRadioButton("Check repository",
                                                  updateGroupbox)
        layoutUpdate.addWidget(self.__projectReposRButton)
        self.__projectLocalRButton = QRadioButton("Local only",
                                                  updateGroupbox)
        layoutUpdate.addWidget(self.__projectLocalRButton)

        verticalLayout.addWidget(authGroupbox)
        verticalLayout.addWidget(updateGroupbox)
        return widget

    def __projectAuthChanged(self):
        """Triggered when authorization has been changed"""
        if self.__projectAuthExtRButton.isChecked():
            self.__projectUser.setEnabled(False)
            self.__projectPasswd.setEnabled(False)
        else:
            self.__projectUser.setEnabled(True)
            self.__projectPasswd.setEnabled(True)
            self.__projectUser.setFocus()
        self.__updateOKStatus()

    @staticmethod
    def __getSVNVersion():
        """Provides an svn binary version"""
        try:
            output = check_output(['svn', '--version'])
            for line in output.decode('utf-8').splitlines():
                parts = line.split(' ')
                for index, part in enumerate(parts):
                    if part.lower() == 'version':
                        return parts[index + 1]
        except Exception as exc:
            logging.error(str(exc))
            return None
        return None

    def __createVersionWidget(self):
        """Creates the version tab content"""
        svnVersion = str(self.__getSVNVersion())
        svnModuleVersion = str(svn.__version__)

        text = "<p>The major Codimension SVN plugin " \
               "components are listed below:</p>" \
               "<ul>" \
               "<li><a href='http://subversion.apache.org/'>" \
               "Subversion</a><br>" \
               "Version: " + svnVersion + "<br></li>" \
               "<li><a href='https://github.com/dsoprea/PySvn'>" \
               "Subversion wrapper</a><br>" \
               "Version: " + svnModuleVersion + "<br>" \
               "License: <a href='http://www.gnu.org/licenses/gpl-2.0.html'>" \
               "GPL 2</a>" \
               "<br></li>" \
               "</ul>"

        browser = QTextBrowser()
        browser.setHtml(text)
        browser.setOpenExternalLinks(True)
        return browser

    def userAccept(self):
        """Triggered when the user clicks OK"""
        # Collect IDE-wide values
        if self.__idewideAuthExtRButton.isChecked():
            self.ideWideSettings.authKind = AUTH_EXTERNAL
            self.ideWideSettings.userName = None
            self.ideWideSettings.password = None
        else:
            self.ideWideSettings.authKind = AUTH_PASSWD
            strippedUser = self.__idewideUser.text().strip()
            self.ideWideSettings.userName = strippedUser
            strippedPasswd = self.__idewidePasswd.text().strip()
            self.ideWideSettings.password = strippedPasswd

        if self.__idewideReposRButton.isChecked():
            self.ideWideSettings.statusKind = STATUS_REPOSITORY
        else:
            self.ideWideSettings.statusKind = STATUS_LOCAL_ONLY

        if self.projectSettings is not None:
            if self.__projectAuthExtRButton.isChecked():
                self.projectSettings.authKind = AUTH_EXTERNAL
                self.projectSettings.userName = None
                self.projectSettings.password = None
            else:
                self.projectSettings.authKind = AUTH_PASSWD
                strippedUser = self.__projectUser.text().strip()
                self.projectSettings.userName = strippedUser
                strippedPasswd = self.__projectPasswd.text().strip()
                self.projectSettings.password = strippedPasswd

            if self.__projectReposRButton.isChecked():
                self.projectSettings.statusKind = STATUS_REPOSITORY
            else:
                self.projectSettings.statusKind = STATUS_LOCAL_ONLY
        self.accept()

    def __updateOKStatus(self):
        """Updates the OK button status"""
        okButton = self.__buttonBox.button(QDialogButtonBox.Ok)
        if self.__idewideAuthPasswdRButton.isChecked():
            userName = self.__idewideUser.text().strip()
            if not userName:
                okButton.setEnabled(False)
                okButton.setToolTip("IDE wide SVN user name cannot be empty")
                return
        if self.projectSettings is not None:
            if self.__projectAuthPasswdRButton.isChecked():
                userName = self.__projectUser.text().strip()
                if not userName:
                    okButton.setEnabled(False)
                    okButton.setToolTip("Project specific SVN "
                                        "user name cannot be empty")
                    return

        okButton.setEnabled(True)
        okButton.setToolTip("")
