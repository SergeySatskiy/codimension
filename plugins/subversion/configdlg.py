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


import os.path
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import ( QDialog, QVBoxLayout, QGroupBox, QSizePolicy,
                          QRadioButton, QDialogButtonBox, QPixmap,
                          QHBoxLayout, QLabel, QTabWidget, QWidget, QGridLayout,
                          QLineEdit, QIntValidator )


AUTH_EXTERNAL = 0               # No user/password or external authorization
AUTH_PASSWD = 1                 # The user name and password are used

UPDATE_LOCAL_ONLY = 0           # Checks only the local status
UPDATE_REPOSITORY = 1           # Checks both local status and the repository

UPDATE_INTERVAL_DEFAULT = 30    # 30 seconds



class SVNSettings:
    " Holds SVN settings "

    def __init__( self ):
        self.authKind = AUTH_EXTERNAL
        self.userName = None
        self.password = None
        self.updateKind = UPDATE_REPOSITORY
        self.updateInterval = UPDATE_INTERVAL_DEFAULT
        return


class SVNPluginConfigDialog( QDialog ):
    " SVN Plugin config dialog "

    def __init__( self, sysWideSettings, projectSettings, parent = None ):
        QDialog.__init__( self, parent )
        self.__createLayout()
        self.setWindowTitle( "SVN plugin configuration" )

        self.sysWideSettings = sysWideSettings
        self.projectSettings = projectSettings

        # Set the values
        self.__setSyswideValues()
        if projectSettings is None:
            self.__tabWidget.setTabEnabled( 1, False )
        else:
            self.__setProjectValues()
            self.__tabWidget.setCurrentIndex( 1 )
        self.__updateOKStatus()

        self.connect( self.__syswideUser, SIGNAL( "textChanged(const QString&)" ),
                      self.__updateOKStatus )
        self.connect( self.__projectUser, SIGNAL( "textChanged(const QString&)" ),
                      self.__updateOKStatus )
        return

    def __setSyswideValues( self ):
        " Sets the values in the system wide tab "
        if self.sysWideSettings.authKind == AUTH_EXTERNAL:
            self.__syswideAuthExtRButton.setChecked( True )
            self.__syswideUser.setEnabled( False )
            self.__syswidePasswd.setEnabled( False )
        else:
            self.__syswideAuthPasswdRButton.setChecked( True )
            if self.sysWideSettings.userName:
                self.__syswideUser.setText( self.sysWideSettings.userName )
            if self.sysWideSettings.password:
                self.__syswidePasswd.setText( self.sysWideSettings.password )

        if self.sysWideSettings.updateKind == UPDATE_REPOSITORY:
            self.__syswideReposRButton.setChecked( True )
        else:
            self.__syswideLocalRButton.setChecked( True )

        self.__syswideIntervalEdit.setText( str( self.sysWideSettings.updateInterval ) )
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

        if self.projectSettings.updateKind == UPDATE_REPOSITORY:
            self.__projectReposRButton.setChecked( True )
        else:
            self.__projectLocalRButton.setChecked( True )

        self.__projectIntervalEdit.setText( str( self.projectSettings.updateInterval ) )
        return

    def __createLayout( self ):
        " Creates the dialog layout "

        self.resize( 640, 450 )
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

        systemWide = self.__createSystemWide()
        self.__tabWidget.addTab( systemWide, "System Wide" )
        projectSpecific = self.__createProjectSpecific()
        self.__tabWidget.addTab( projectSpecific, "Project Specific" )
        vboxLayout.addWidget( self.__tabWidget )

        # Buttons at the bottom
        self.__buttonBox = QDialogButtonBox( self )
        self.__buttonBox.setOrientation( Qt.Horizontal )
        self.__buttonBox.setStandardButtons( QDialogButtonBox.Ok |
                                             QDialogButtonBox.Cancel )
        self.connect( self.__buttonBox, SIGNAL( "accepted()" ), self.userAccept )
        self.connect( self.__buttonBox, SIGNAL( "rejected()" ), self.close )
        vboxLayout.addWidget( self.__buttonBox )
        return

    def __createSystemWide( self ):
        " Creates the system wide part "
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
        self.__syswideAuthExtRButton = QRadioButton( "External", authGroupbox )
        self.connect( self.__syswideAuthExtRButton, SIGNAL( "clicked()" ),
                      self.__syswideAuthChanged )
        layoutAuth.addWidget( self.__syswideAuthExtRButton )
        self.__syswideAuthPasswdRButton = QRadioButton(
                    "Use user name / password", authGroupbox )
        self.connect( self.__syswideAuthPasswdRButton, SIGNAL( "clicked()" ),
                      self.__syswideAuthChanged )
        layoutAuth.addWidget( self.__syswideAuthPasswdRButton )

        upLayout = QGridLayout()
        self.__syswideUser = QLineEdit()
        self.__syswideUser.setToolTip( "Attention: user name is "
                                       "saved unencrypted" )
        self.__syswidePasswd = QLineEdit()
        self.__syswidePasswd.setToolTip( "Attention: password is "
                                         "saved unencrypted" )
        spacer = QWidget()
        spacer.setFixedWidth( 16 )
        upLayout.addWidget( spacer, 0, 0 )
        upLayout.addWidget( QLabel( "User name" ), 0, 1 )
        upLayout.addWidget( self.__syswideUser, 0, 2 )
        upLayout.addWidget( QLabel( "Password" ), 1, 1 )
        upLayout.addWidget( self.__syswidePasswd, 1, 2 )
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
        self.__syswideReposRButton = QRadioButton( "Check repository",
                                                   updateGroupbox )
        layoutUpdate.addWidget( self.__syswideReposRButton )
        self.__syswideLocalRButton = QRadioButton( "Local only",
                                                   updateGroupbox )
        layoutUpdate.addWidget( self.__syswideLocalRButton )

        # Update interval
        intervalLayout = QHBoxLayout()
        intervalLayout.addWidget( QLabel( "Update interval, sec." ) )
        self.__syswideIntervalEdit = QLineEdit()
        self.__syswideIntervalEdit.setValidator( QIntValidator( 1, 3600, self ) )
        intervalLayout.addWidget( self.__syswideIntervalEdit )

        verticalLayout.addWidget( authGroupbox )
        verticalLayout.addWidget( updateGroupbox )
        verticalLayout.addLayout( intervalLayout )

        return widget

    def __syswideAuthChanged( self ):
        " Triggered when authorization has been changed "
        if self.__syswideAuthExtRButton.isChecked():
            self.__syswideUser.setEnabled( False )
            self.__syswidePasswd.setEnabled( False )
        else:
            self.__syswideUser.setEnabled( True )
            self.__syswidePasswd.setEnabled( True )
            self.__syswideUser.setFocus()
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
        self.connect( self.__projectAuthExtRButton, SIGNAL( "clicked()" ),
                      self.__projectAuthChanged )
        layoutAuth.addWidget( self.__projectAuthExtRButton )
        self.__projectAuthPasswdRButton = QRadioButton(
                    "Use user name / password", authGroupbox )
        self.connect( self.__projectAuthPasswdRButton, SIGNAL( "clicked()" ),
                      self.__projectAuthChanged )
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

        # Update interval
        intervalLayout = QHBoxLayout()
        intervalLayout.addWidget( QLabel( "Update interval, sec." ) )
        self.__projectIntervalEdit = QLineEdit()
        self.__projectIntervalEdit.setValidator( QIntValidator( 1, 3600, self ) )
        intervalLayout.addWidget( self.__projectIntervalEdit )

        verticalLayout.addWidget( authGroupbox )
        verticalLayout.addWidget( updateGroupbox )
        verticalLayout.addLayout( intervalLayout )

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

    def userAccept( self ):
        " Triggered when the user clicks OK "
        # Collect system-wide values
        if self.__syswideAuthExtRButton.isChecked():
            self.sysWideSettings.authKind = AUTH_EXTERNAL
            self.sysWideSettings.userName = None
            self.sysWideSettings.password = None
        else:
            self.sysWideSettings.authKind = AUTH_PASSWD
            self.sysWideSettings.userName = str( self.__syswideUser.text() ).strip()
            self.sysWideSettings.password = str( self.__syswidePasswd.text() ).strip()

        if self.__syswideReposRButton.isChecked():
            self.sysWideSettings.updateKind = UPDATE_REPOSITORY
        else:
            self.sysWideSettings.updateKind = UPDATE_LOCAL_ONLY

        self.sysWideSettings.updateInterval = int( str( self.__syswideIntervalEdit.text() ) )

        if self.projectSettings is not None:
            if self.__projectAuthExtRButton.isChecked():
                self.projectSettings.authKind = AUTH_EXTERNAL
                self.projectSettings.userName = None
                self.projectSettings.password = None
            else:
                self.projectSettings.authKind = AUTH_PASSWD
                self.projectSettings.userName = str( self.__projectUser.text() ).strip()
                self.projectSettings.password = str( self.__projectPasswd.text() ).strip()

            if self.__projectReposRButton.isChecked():
                self.projectSettings.updateKind = UPDATE_REPOSITORY
            else:
                self.projectSettings.updateKind = UPDATE_LOCAL_ONLY

            self.projectSettings.updateInterval = int( str( self.__projectIntervalEdit.text() ) )

        self.accept()
        return

    def __updateOKStatus( self ):
        " Updates the OK button status "
        okButton = self.__buttonBox.button( QDialogButtonBox.Ok )
        if self.__syswideAuthPasswdRButton.isChecked():
            userName = str( self.__syswideUser.text() ).strip()
            if not userName:
                okButton.setEnabled( False )
                okButton.setToolTip( "System wide SVN user name cannot be empty" )
                return
        if self.projectSettings is not None:
            if self.__projectAuthPasswdRButton.isChecked():
                userName = str( self.__projectUser.text() ).strip()
                if not userName:
                    okButton.setEnabled( False )
                    okButton.setToolTip( "Project specific SVN user name cannot be empty" )
                    return

        okButton.setEnabled( True )
        okButton.setToolTip( "" )
        return
