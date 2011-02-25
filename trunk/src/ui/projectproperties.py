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


""" project properties dialog """


from PyQt4.QtCore import Qt, SIGNAL, QEvent, QObject
from PyQt4.QtGui import QDialog, QLineEdit, QGridLayout, QLabel, QTextEdit, \
                        QDialogButtonBox, QVBoxLayout, QPushButton, \
                        QFileDialog, QMessageBox
from completers import DirCompleter
import os, pwd, socket, datetime
from utils.project import getProjectProperties



class ProjectPropertiesDialog( QDialog, object ):
    """ project properties dialog implementation """

    def __init__( self, project = None, parent = None ):

        QDialog.__init__( self, parent )

        self.__createLayout()

        if project is None:
            # It a new project creation
            self.setWindowTitle( "New Project Properties" )

            userRecord = pwd.getpwuid( os.getuid() )

            if not userRecord[ 5 ].endswith( os.path.sep ):
                self.dirEdit.setText( userRecord[ 5 ] + os.path.sep )
            else:
                self.dirEdit.setText( userRecord[ 5 ] )
            self.initialDirName = self.dirEdit.text()
            self.lastProjectName = ""

            if userRecord[ 4 ] != "":
                self.authorEdit.setText( userRecord[ 4 ] )
            else:
                self.authorEdit.setText( userRecord[ 0 ] )

            try:
                self.emailEdit.setText( userRecord[ 0 ] + \
                                        "@" + socket.gethostname() )
            except:
                pass

            self.versionEdit.setText( "0.0.1" )
            self.licenseEdit.setText( "GPL v3" )
            self.copyrightEdit.setText( "Copyright (c) " + \
                                        self.authorEdit.text() + ", " + \
                                        str( datetime.date.today().year ) )
            self.creationDateEdit.setText( str( datetime.date.today() ) )
            self.nameEdit.setFocus()

        elif type( project ) == type( "" ):
            self.setWindowTitle( "Viewing Project Properties" )

            # This is viewing properties and the argument is the path to the
            # project file
            creationDate, author, lic, \
            copy_right, description, \
            version, email = getProjectProperties( project )

            self.nameEdit.setText( os.path.basename( project ) )
            self.dirEdit.setText( os.path.dirname( project ) )
            self.versionEdit.setText( version )
            self.authorEdit.setText( author )
            self.emailEdit.setText( email )
            self.licenseEdit.setText( lic )
            self.copyrightEdit.setText( copy_right )
            self.descriptionEdit.setText( description )
            self.creationDateEdit.setText( creationDate )
            self.disableEditing()

        else:
            self.setWindowTitle( "Editing Project Properties" )

            # This is editing the existing project
            self.nameEdit.setText( os.path.basename( project.fileName ) )
            self.dirEdit.setText( os.path.dirname( project.fileName ) )
            self.versionEdit.setText( project.version )
            self.authorEdit.setText( project.author )
            self.emailEdit.setText( project.email )
            self.licenseEdit.setText( project.license )
            self.copyrightEdit.setText( project.copyright )
            self.descriptionEdit.setText( project.description )
            self.creationDateEdit.setText( project.creationDate )
            self.setReadOnly()
            self.versionEdit.setFocus()

        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 600, 400 )
        self.setSizeGripEnabled( True )

        self.verticalLayout = QVBoxLayout( self )
        self.gridLayout = QGridLayout()

        # Project name
        nameLabel = QLabel( self )
        nameLabel.setText( "Project name:" )
        self.gridLayout.addWidget( nameLabel, 0, 0, 1, 1 )
        self.nameEdit = QLineEdit( self )
        self.nameEdit.setToolTip( "Type a project name without a path" )
        self.nameEdit.installEventFilter( self )
        self.gridLayout.addWidget( self.nameEdit, 0, 1, 1, 1 )

        # Project dir
        dirLabel = QLabel( self )
        dirLabel.setText( "Project directory:" )
        self.gridLayout.addWidget( dirLabel, 1, 0, 1, 1 )
        self.dirEdit = QLineEdit( self )
        self.dirEdit.setToolTip( "Not existed directories will be created" )
        self.gridLayout.addWidget( self.dirEdit, 1, 1, 1, 1 )
        self.dirButton = QPushButton( self )
        self.dirButton.setText( "..." )
        self.gridLayout.addWidget( self.dirButton, 1, 2, 1, 1 )
        self.dirCompleter = DirCompleter( self.dirEdit )

        # Version
        versionLabel = QLabel( self )
        versionLabel.setText( "Version:" )
        self.gridLayout.addWidget( versionLabel, 2, 0, 1, 1 )
        self.versionEdit = QLineEdit( self )
        self.gridLayout.addWidget( self.versionEdit, 2, 1, 1, 1 )

        # Author
        authorLabel = QLabel( self )
        authorLabel.setText( "Author:" )
        self.gridLayout.addWidget( authorLabel, 3, 0, 1, 1 )
        self.authorEdit = QLineEdit( self )
        self.gridLayout.addWidget( self.authorEdit, 3, 1, 1, 1 )

        # E-mail
        emailLabel = QLabel( self )
        emailLabel.setText( "E-mail:" )
        self.gridLayout.addWidget( emailLabel, 4, 0, 1, 1 )
        self.emailEdit = QLineEdit( self )
        self.gridLayout.addWidget( self.emailEdit, 4, 1, 1, 1 )

        # License
        licenseLabel = QLabel( self )
        licenseLabel.setText( "License:" )
        self.gridLayout.addWidget( licenseLabel, 5, 0, 1, 1 )
        self.licenseEdit = QLineEdit( self )
        self.gridLayout.addWidget( self.licenseEdit, 5, 1, 1, 1 )

        # Copyright
        copyrightLabel = QLabel( self )
        copyrightLabel.setText( "Copyright:" )
        self.gridLayout.addWidget( copyrightLabel, 6, 0, 1, 1 )
        self.copyrightEdit = QLineEdit( self )
        self.gridLayout.addWidget( self.copyrightEdit, 6, 1, 1, 1 )

        # Description
        descriptionLabel = QLabel( self )
        descriptionLabel.setText( "Description:" )
        descriptionLabel.setAlignment( Qt.AlignTop )
        self.gridLayout.addWidget( descriptionLabel, 7, 0, 1, 1 )
        self.descriptionEdit = QTextEdit( self )
        self.descriptionEdit.setTabChangesFocus( True )
        self.descriptionEdit.setAcceptRichText( False )
        self.gridLayout.addWidget( self.descriptionEdit, 7, 1, 1, 1 )

        # Creation date
        creationDateLabel = QLabel( self )
        creationDateLabel.setText( "Creation date:" )
        self.gridLayout.addWidget( creationDateLabel, 8, 0, 1, 1 )
        self.creationDateEdit = QLineEdit( self )
        self.creationDateEdit.setReadOnly( True )
        self.creationDateEdit.setFocusPolicy( Qt.NoFocus )
        self.creationDateEdit.setDisabled( True )
        self.gridLayout.addWidget( self.creationDateEdit, 8, 1, 1, 1 )

        self.verticalLayout.addLayout( self.gridLayout )

        # Buttons at the bottom
        self.buttonBox = QDialogButtonBox( self )
        self.buttonBox.setOrientation( Qt.Horizontal )
        self.buttonBox.setStandardButtons( QDialogButtonBox.Cancel | \
                                           QDialogButtonBox.Ok )
        self.verticalLayout.addWidget( self.buttonBox )

        nameLabel.setBuddy( self.nameEdit )
        dirLabel.setBuddy( self.dirEdit )
        versionLabel.setBuddy( self.versionEdit )
        authorLabel.setBuddy( self.authorEdit )
        emailLabel.setBuddy( self.emailEdit )
        licenseLabel.setBuddy( self.licenseEdit )
        copyrightLabel.setBuddy( self.copyrightEdit )
        descriptionLabel.setBuddy( self.descriptionEdit )


        self.connect( self.buttonBox, SIGNAL( "accepted()" ), self.onOKButton )
        self.connect( self.buttonBox, SIGNAL( "rejected()" ), self.reject )
        self.connect( self.dirButton, SIGNAL( "clicked()" ), self.onDirButton )
        self.connect( self.nameEdit,  SIGNAL( "textEdited(const QString &)" ),
                      self.onProjectNameChanged )

        self.setTabOrder( self.nameEdit, self.dirEdit )
        self.setTabOrder( self.dirEdit, self.dirButton )
        self.setTabOrder( self.dirButton, self.versionEdit )
        self.setTabOrder( self.versionEdit, self.authorEdit )
        self.setTabOrder( self.authorEdit, self.emailEdit )
        self.setTabOrder( self.emailEdit, self.licenseEdit )
        self.setTabOrder( self.licenseEdit, self.copyrightEdit )
        self.setTabOrder( self.copyrightEdit, self.descriptionEdit )
        self.setTabOrder( self.descriptionEdit, self.buttonBox )

        return

    def eventFilter( self, obj, event ):
        " Event filter for the project name field "

        # Do not allow path separators
        if event.type() == QEvent.KeyPress:
            if event.key() == ord( os.path.sep ):
                return True
        return QObject.eventFilter( self, obj, event )


    def onDirButton( self ):
        " Displays a directory selection dialog "

        dirName = QFileDialog.getExistingDirectory( self,
                    "Select project directory",
                    self.dirEdit.text(),
                    QFileDialog.Options( QFileDialog.ShowDirsOnly ) )

        if not dirName.isEmpty():
            self.dirEdit.setText( os.path.normpath( str( dirName ) ) )
        return

    def onOKButton( self ):
        " Checks that the mandatory fields are filled properly "

        # The checks must be done for a new project only
        if not self.nameEdit.isEnabled():
            self.accept()
            return

        # Check that the project name does not have path separators and is not
        # empty
        if str( self.nameEdit.text() ).strip() == "":
            QMessageBox.critical( self, "Error",
                                  "The project name must not be empty" )
            return
        if os.path.sep in str( self.nameEdit.text() ):
            QMessageBox.critical( self, "Error",
                                  "The project name must not " \
                                  "contain path separators" )
            return

        # Check that the project directory is given
        dirName = str( self.dirEdit.text() ).strip()
        if dirName == "":
            QMessageBox.critical( self, "Error",
                                  "The project directory must not be empty" )
            return

        dirName = os.path.abspath( dirName )
        self.dirEdit.setText( dirName )
        # Check that the project file does not exist
        self.projectFileName = dirName
        if not self.projectFileName.endswith( os.path.sep ):
            self.projectFileName += os.path.sep
        self.projectFileName += str( self.nameEdit.text() ).strip()
        if not self.projectFileName.endswith( ".cdm" ):
            self.projectFileName += ".cdm"

        if os.path.exists( self.projectFileName ):
            QMessageBox.critical( self, "Error",
                                  "The project file " + self.projectFileName + \
                                  " exists. Please provide another " \
                                  "directory / project name." )
            return

        # Check that the project dir is not a file
        if os.path.exists( dirName ):
            # It might be a link, so read it first
            dirName = os.path.realpath( dirName )
            if not os.path.exists( dirName ):
                QMessageBox.critical( self, "Error",
                                      "Broken link: " + dirName )
                return
            if not os.path.isdir( dirName ):
                QMessageBox.critical( self, "Error",
                                      "The project directory may not be a file" )
                return
            # Check that the dir is writable
            if not os.access( dirName, os.W_OK ):
                QMessageBox.critical( self, "Error",
                                      "You don't have write permissions on " + \
                                      dirName )
                return
        else:
            # Create the directory
            try:
                os.makedirs( dirName )
            except OSError:
                QMessageBox.critical( self, "Error",
                                      "Cannot create the project directory" )
                return

        # The minimum is provided so we can accept it
        self.accept()
        return

    def onProjectNameChanged( self, newName ):
        " Called when the project name changed "

        newName = str( newName )
        if newName.endswith( ".cdm" ):
            newName = newName[ :-4 ]
        if str( self.dirEdit.text() ).strip() == (self.initialDirName + \
                                                  self.lastProjectName):
            self.dirEdit.setText( self.initialDirName + newName )
            self.lastProjectName = newName
        return

    def setReadOnly( self ):
        """ Disables editing some fields """

        self.dirEdit.setReadOnly( True )
        self.dirEdit.setFocusPolicy( Qt.NoFocus )
        self.dirEdit.setDisabled( True )
        self.dirButton.setDisabled( True )
        self.dirButton.setFocusPolicy( Qt.NoFocus )
        self.nameEdit.setReadOnly( True )
        self.nameEdit.setFocusPolicy( Qt.NoFocus )
        self.nameEdit.setDisabled( True )
        return

    def disableEditing( self ):
        " Disables all the editing "

        self.nameEdit.setDisabled( True )
        self.dirEdit.setDisabled( True )
        self.dirButton.setDisabled( True )
        self.versionEdit.setDisabled( True )
        self.authorEdit.setDisabled( True )
        self.emailEdit.setDisabled( True )
        self.licenseEdit.setDisabled( True )
        self.copyrightEdit.setDisabled( True )
        self.descriptionEdit.setDisabled( True )
        self.creationDateEdit.setDisabled( True )
        return

