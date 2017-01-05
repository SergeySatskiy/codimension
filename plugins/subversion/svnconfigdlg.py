#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

" Codimension SVN plugin config dialog "


import os.path, logging, ConfigParser, string, copy, stat
from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QDialog, QVBoxLayout, QGroupBox, QSizePolicy,
                          QRadioButton, QDialogButtonBox, QPixmap,
                          QHBoxLayout, QLabel, QTabWidget, QWidget, QGridLayout,
                          QLineEdit, QTextBrowser )
import pysvn


AUTH_EXTERNAL = 0               # No user/password or external authorization
AUTH_PASSWD = 1                 # The user name and password are used

STATUS_LOCAL_ONLY = 0           # Checks only the local status
STATUS_REPOSITORY = 1           # Checks both local status and the repository



class SVNSettings:
    " Holds SVN settings "

    def __init__( self ):
        self.authKind = AUTH_EXTERNAL
        self.userName = None
        self.password = None
        self.statusKind = STATUS_REPOSITORY
        return


def caesar( s, k, decode ):
    " Taken from here: http://rosettacode.org/wiki/Caesar_cipher "
    if decode:
        k = 26 - k
    return s.translate( string.maketrans(
            string.ascii_uppercase + string.ascii_lowercase,
            string.ascii_uppercase[k:] + string.ascii_uppercase[:k] +
            string.ascii_lowercase[k:] + string.ascii_lowercase[:k] ) )


def saveSVNSettings( settings, fName ):
    " Saves settings to the file "
    try:
        userNameValue = ""
        passwordValue = ""
        if settings.userName:
            userNameValue = caesar( settings.userName, 7, False )
        if settings.password:
            passwordValue = caesar( settings.password, 7, False )

        f = open( fName, "w" )
        f.write( "# Automatically generated\n"
                 "[svnplugin]\n"
                 "authkind=" + str( settings.authKind ) + "\n"
                 "username=" + userNameValue + "\n"
                 "password=" + passwordValue + "\n"
                 "statuskind=" + str( settings.statusKind ) + "\n" )
        f.close()
        os.chmod( fName, stat.S_IRUSR | stat.S_IWUSR )
    except Exception as exc:
        logging.error( "Error saving SVN plugin settings into " + fName + ".\n"
                       "Exception: " + str( exc ) )
    return


def getSettings( fName ):
    """ Reads settings from the file.
        If the file does not exist - creates default """
    try:
        settings = SVNSettings()
        if os.path.exists( fName ):
            # File exists, read it
            config = ConfigParser.ConfigParser()
            config.read( [ fName ] )
            value = int( config.get( "svnplugin", "authkind" ) )
            if value in [ AUTH_EXTERNAL, AUTH_PASSWD ]:
                settings.authKind = value
                settings.userName = caesar( config.get( "svnplugin", "username" ), 7, True )
                settings.password = caesar( config.get( "svnplugin", "password" ), 7, True )
            else:
                settings.authKind = AUTH_EXTERNAL
                settings.userName = None
                settings.password = None

            value = int( config.get( "svnplugin", "statuskind" ) )
            if value in [ STATUS_LOCAL_ONLY, STATUS_REPOSITORY ]:
                settings.statusKind = value
            else:
                settings.statusKind = STATUS_REPOSITORY
        else:
            # File does not exist - create default settings
            saveSVNSettings( settings, fName )
        return settings
    except Exception as exc:
        logging.error( "Error retrieving SVN plugin settings from " + fName +
                       ". Using default settings.\nException: " + str( exc ) )
        return SVNSettings()



class SVNPluginConfigDialog( QDialog ):
    " SVN Plugin config dialog "

    def __init__( self, ideWideSettings, projectSettings, parent = None ):
        QDialog.__init__( self, parent )
        self.__createLayout()
        self.setWindowTitle( "SVN plugin configuration" )

        self.ideWideSettings = copy.deepcopy( ideWideSettings )
        if projectSettings is None:
            self.projectSettings = None
        else:
            self.projectSettings = copy.deepcopy( projectSettings )

        # Set the values
        self.__setIDEWideValues()
        if projectSettings is None:
            self.__tabWidget.setTabEnabled( 1, False )
        else:
            self.__setProjectValues()
            self.__tabWidget.setCurrentIndex( 1 )
        self.__updateOKStatus()

        self.__idewideUser.textChanged.connect( self.__updateOKStatus )
        self.__projectUser.textChanged.connect( self.__updateOKStatus )
        return

    def __setIDEWideValues( self ):
        " Sets the values in the IDE wide tab "
        if self.ideWideSettings.authKind == AUTH_EXTERNAL:
            self.__idewideAuthExtRButton.setChecked( True )
            self.__idewideUser.setEnabled( False )
            self.__idewidePasswd.setEnabled( False )
        else:
            self.__idewideAuthPasswdRButton.setChecked( True )
            if self.ideWideSettings.userName:
                self.__idewideUser.setText( self.ideWideSettings.userName )
            if self.ideWideSettings.password:
                self.__idewidePasswd.setText( self.ideWideSettings.password )

        if self.ideWideSettings.statusKind == STATUS_REPOSITORY:
            self.__idewideReposRButton.setChecked( True )
        else:
            self.__idewideLocalRButton.setChecked( True )
        return

    def __setProjectValues( self ):
        " Sets the values in the project tab "
        if self.projectSettings.authKind == AUTH_EXTERNAL:
            self.__projectAuthExtRButton.setChecked( True )
            self.__projectUser.setEnabled( False )
            self.__projectPasswd.setEnabled( False )
        else:
            self.__projectAuthPasswdRButton.setChecked( True )
            if self.projectSettings.userName:
                self.__projectUser.setText( self.projectSettings.userName )
            if self.projectSettings.password:
                self.__projectPasswd.setText( self.projectSettings.password )

        if self.projectSettings.statusKind == STATUS_REPOSITORY:
            self.__projectReposRButton.setChecked( True )
        else:
            self.__projectLocalRButton.setChecked( True )
        return

    def __createLayout( self ):
        " Creates the dialog layout "

        self.resize( 640, 420 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )
        hboxLayout = QHBoxLayout()
        iconLabel = QLabel()
        logoPath = os.path.dirname( os.path.abspath( __file__ ) ) + \
                   os.path.sep + "svn-logo.png"
        iconLabel.setPixmap( QPixmap( logoPath ) )
        iconLabel.setScaledContents( True )
        iconLabel.setFixedSize( 48, 48 )
        hboxLayout.addWidget( iconLabel )
        titleLabel = QLabel( "Codimension SVN plugin settings" )
        titleLabel.setSizePolicy( QSizePolicy.Expanding,
                                  QSizePolicy.Expanding )
        titleLabel.setFixedHeight( 48 )
        titleLabel.setAlignment( Qt.AlignCenter )
        hboxLayout.addWidget( titleLabel )
        vboxLayout.addLayout( hboxLayout )

        self.__tabWidget = QTabWidget( self )
        self.__tabWidget.setFocusPolicy( Qt.NoFocus )

        ideWide = self.__createIDEWide()
        self.__tabWidget.addTab( ideWide, "IDE Wide" )
        projectSpecific = self.__createProjectSpecific()
        self.__tabWidget.addTab( projectSpecific, "Project Specific" )
        version = self.__createVersionWidget()
        self.__tabWidget.addTab( version, "Versions" )
        vboxLayout.addWidget( self.__tabWidget )

        # Buttons at the bottom
        self.__buttonBox = QDialogButtonBox( self )
        self.__buttonBox.setOrientation( Qt.Horizontal )
        self.__buttonBox.setStandardButtons( QDialogButtonBox.Ok |
                                             QDialogButtonBox.Cancel )
        self.__buttonBox.accepted.connect( self.userAccept )
        self.__buttonBox.rejected.connect( self.close )
        vboxLayout.addWidget( self.__buttonBox )
        return

    def __createIDEWide( self ):
        " Creates the IDE wide part "
        widget = QWidget()

        verticalLayout = QVBoxLayout( widget )
        infoLabel = QLabel( "Note: the settings below are used "
                            "when there is no project loaded." )
        verticalLayout.addWidget( infoLabel )

        # Authorization group box
        authGroupbox = QGroupBox( self )
        authGroupbox.setTitle( "Authorization" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(
                    authGroupbox.sizePolicy().hasHeightForWidth() )
        authGroupbox.setSizePolicy( sizePolicy )

        layoutAuth = QVBoxLayout( authGroupbox )
        self.__idewideAuthExtRButton = QRadioButton( "External", authGroupbox )
        self.__idewideAuthExtRButton.clicked.connect( self.__idewideAuthChanged )
        layoutAuth.addWidget( self.__idewideAuthExtRButton )
        self.__idewideAuthPasswdRButton = QRadioButton(
                    "Use user name / password", authGroupbox )
        self.__idewideAuthPasswdRButton.clicked.connect( self.__idewideAuthChanged )
        layoutAuth.addWidget( self.__idewideAuthPasswdRButton )

        upLayout = QGridLayout()
        self.__idewideUser = QLineEdit()
        self.__idewideUser.setToolTip( "Attention: user name is "
                                       "saved unencrypted" )
        self.__idewidePasswd = QLineEdit()
        self.__idewidePasswd.setToolTip( "Attention: password is "
                                         "saved unencrypted" )
        spacer = QWidget()
        spacer.setFixedWidth( 16 )
        upLayout.addWidget( spacer, 0, 0 )
        upLayout.addWidget( QLabel( "User name" ), 0, 1 )
        upLayout.addWidget( self.__idewideUser, 0, 2 )
        upLayout.addWidget( QLabel( "Password" ), 1, 1 )
        upLayout.addWidget( self.__idewidePasswd, 1, 2 )
        layoutAuth.addLayout( upLayout )

        # Update status group box
        updateGroupbox = QGroupBox( self )
        updateGroupbox.setTitle( "Update status policy" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(
                    updateGroupbox.sizePolicy().hasHeightForWidth() )
        updateGroupbox.setSizePolicy( sizePolicy )

        layoutUpdate = QVBoxLayout( updateGroupbox )
        self.__idewideReposRButton = QRadioButton( "Check repository",
                                                   updateGroupbox )
        layoutUpdate.addWidget( self.__idewideReposRButton )
        self.__idewideLocalRButton = QRadioButton( "Local only",
                                                   updateGroupbox )
        layoutUpdate.addWidget( self.__idewideLocalRButton )

        verticalLayout.addWidget( authGroupbox )
        verticalLayout.addWidget( updateGroupbox )

        return widget

    def __idewideAuthChanged( self ):
        " Triggered when authorization has been changed "
        if self.__idewideAuthExtRButton.isChecked():
            self.__idewideUser.setEnabled( False )
            self.__idewidePasswd.setEnabled( False )
        else:
            self.__idewideUser.setEnabled( True )
            self.__idewidePasswd.setEnabled( True )
            self.__idewideUser.setFocus()
        self.__updateOKStatus()
        return

    def __createProjectSpecific( self ):
        " Creates the project specific part "
        widget = QWidget()

        verticalLayout = QVBoxLayout( widget )
        infoLabel = QLabel( "Note: the settings below are used "
                            "only for the specific project." )
        verticalLayout.addWidget( infoLabel )

        # Authorization group box
        authGroupbox = QGroupBox( self )
        authGroupbox.setTitle( "Authorization" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(
                    authGroupbox.sizePolicy().hasHeightForWidth() )
        authGroupbox.setSizePolicy( sizePolicy )

        layoutAuth = QVBoxLayout( authGroupbox )
        self.__projectAuthExtRButton = QRadioButton( "External", authGroupbox )
        self.__projectAuthExtRButton.clicked.connect( self.__projectAuthChanged )
        layoutAuth.addWidget( self.__projectAuthExtRButton )
        self.__projectAuthPasswdRButton = QRadioButton(
                    "Use user name / password", authGroupbox )
        self.__projectAuthPasswdRButton.clicked.connect( self.__projectAuthChanged )
        layoutAuth.addWidget( self.__projectAuthPasswdRButton )

        upLayout = QGridLayout()
        self.__projectUser = QLineEdit()
        self.__projectUser.setToolTip( "Attention: user name is "
                                       "saved unencrypted" )
        self.__projectPasswd = QLineEdit()
        self.__projectPasswd.setToolTip( "Attention: password is "
                                         "saved unencrypted" )
        spacer = QWidget()
        spacer.setFixedWidth( 16 )
        upLayout.addWidget( spacer, 0, 0 )
        upLayout.addWidget( QLabel( "User name" ), 0, 1 )
        upLayout.addWidget( self.__projectUser, 0, 2 )
        upLayout.addWidget( QLabel( "Password" ), 1, 1 )
        upLayout.addWidget( self.__projectPasswd, 1, 2 )
        layoutAuth.addLayout( upLayout )

        # Update status group box
        updateGroupbox = QGroupBox( self )
        updateGroupbox.setTitle( "Update status policy" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(
                    updateGroupbox.sizePolicy().hasHeightForWidth() )
        updateGroupbox.setSizePolicy( sizePolicy )

        layoutUpdate = QVBoxLayout( updateGroupbox )
        self.__projectReposRButton = QRadioButton( "Check repository",
                                                   updateGroupbox )
        layoutUpdate.addWidget( self.__projectReposRButton )
        self.__projectLocalRButton = QRadioButton( "Local only",
                                                   updateGroupbox )
        layoutUpdate.addWidget( self.__projectLocalRButton )

        verticalLayout.addWidget( authGroupbox )
        verticalLayout.addWidget( updateGroupbox )

        return widget

    def __projectAuthChanged( self ):
        " Triggered when authorization has been changed "
        if self.__projectAuthExtRButton.isChecked():
            self.__projectUser.setEnabled( False )
            self.__projectPasswd.setEnabled( False )
        else:
            self.__projectUser.setEnabled( True )
            self.__projectPasswd.setEnabled( True )
            self.__projectUser.setFocus()
        self.__updateOKStatus()
        return

    def __createVersionWidget( self ):
        " Creates the version tab content "
        ver = pysvn.svn_version
        svnVersion = ".".join( [ str( ver[ 0 ] ), str( ver[ 1 ] ),
                                 str( ver[ 2 ] ) ] )
        ver = pysvn.version
        pysvnVersion = ".".join( [ str( ver[ 0 ] ), str( ver[ 1 ] ),
                                   str( ver[ 2 ] ) ] )

        text = "<p>The major Codimension SVN plugin components are listed below:</p>" \
               "<ul>" \
               "<li><a href='http://subversion.apache.org/'>Subversion</a><br>" \
               "Version: " + svnVersion + "<br></li>" \
               "<li><a href='http://pysvn.tigris.org/docs/pysvn.html'>PySvn</a><br>" \
               "Version: " + pysvnVersion + "<br>" \
               "License: <a href='http://www.apache.org/licenses/LICENSE-1.1'>Apache License 1.1</a>" \
               "<br></li>" \
               "</ul>"

        browser = QTextBrowser()
        browser.setHtml( text )
        browser.setOpenExternalLinks( True )
        return browser


    def userAccept( self ):
        " Triggered when the user clicks OK "
        # Collect IDE-wide values
        if self.__idewideAuthExtRButton.isChecked():
            self.ideWideSettings.authKind = AUTH_EXTERNAL
            self.ideWideSettings.userName = None
            self.ideWideSettings.password = None
        else:
            self.ideWideSettings.authKind = AUTH_PASSWD
            self.ideWideSettings.userName = self.__idewideUser.text().strip()
            self.ideWideSettings.password = self.__idewidePasswd.text().strip()

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
                self.projectSettings.userName = self.__projectUser.text().strip()
                self.projectSettings.password = self.__projectPasswd.text().strip()

            if self.__projectReposRButton.isChecked():
                self.projectSettings.statusKind = STATUS_REPOSITORY
            else:
                self.projectSettings.statusKind = STATUS_LOCAL_ONLY

        self.accept()
        return

    def __updateOKStatus( self ):
        " Updates the OK button status "
        okButton = self.__buttonBox.button( QDialogButtonBox.Ok )
        if self.__idewideAuthPasswdRButton.isChecked():
            userName = self.__idewideUser.text().strip()
            if not userName:
                okButton.setEnabled( False )
                okButton.setToolTip( "IDE wide SVN user name cannot be empty" )
                return
        if self.projectSettings is not None:
            if self.__projectAuthPasswdRButton.isChecked():
                userName = self.__projectUser.text().strip()
                if not userName:
                    okButton.setEnabled( False )
                    okButton.setToolTip( "Project specific SVN "
                                         "user name cannot be empty" )
                    return

        okButton.setEnabled( True )
        okButton.setToolTip( "" )
        return
