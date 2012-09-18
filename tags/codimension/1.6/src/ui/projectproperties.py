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
                        QFileDialog, QMessageBox, QListWidget, QAbstractItemView
from completers import DirCompleter, FileCompleter
import os, pwd, socket, datetime, logging
from utils.project import getProjectProperties
from itemdelegates import NoOutlineHeightDelegate
from utils.compatibility import relpath
from utils.misc import getLocaleDate


class ProjectPropertiesDialog( QDialog, object ):
    """ project properties dialog implementation """

    def __init__( self, project = None, parent = None ):

        QDialog.__init__( self, parent )

        # The dialog caller reads this member if the dialog was finished
        # successfully.
        self.absProjectFileName = None

        self.__createLayout()
        self.__project = project

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
            self.creationDateEdit.setText( getLocaleDate() )
            self.nameEdit.setFocus()

        elif type( project ) == type( "" ):
            self.setWindowTitle( "Viewing Project Properties" )

            # This is viewing properties and the argument is the path to the
            # project file
            scriptName, importDirs, creationDate, author, lic, \
            copy_right, description, \
            version, email, uuid = getProjectProperties( project )

            if not os.path.isabs( scriptName ) and scriptName != "":
                scriptName = os.path.normpath( os.path.dirname( project ) + \
                                               os.path.sep + scriptName )

            self.nameEdit.setText( os.path.basename( project ) )
            self.dirEdit.setText( os.path.dirname( project ) )
            self.scriptEdit.setText( scriptName )
            self.versionEdit.setText( version )
            self.authorEdit.setText( author )
            self.emailEdit.setText( email )
            self.licenseEdit.setText( lic )
            self.copyrightEdit.setText( copy_right )
            self.descriptionEdit.setText( description )
            self.creationDateEdit.setText( creationDate )
            self.uuidEdit.setText( uuid )

            for item in importDirs:
                self.importDirList.addItem( item )

            self.disableEditing()

        else:
            self.setWindowTitle( "Editing Project Properties" )

            # This is editing the loaded project
            self.nameEdit.setText( os.path.basename( project.fileName ) )
            self.dirEdit.setText( project.getProjectDir() )
            self.scriptEdit.setText( project.getProjectScript() )
            self.versionEdit.setText( project.version )
            self.authorEdit.setText( project.author )
            self.emailEdit.setText( project.email )
            self.licenseEdit.setText( project.license )
            self.copyrightEdit.setText( project.copyright )
            self.descriptionEdit.setText( project.description )
            self.creationDateEdit.setText( project.creationDate )
            self.uuidEdit.setText( str( project.uuid ) )
            self.setReadOnly()

            for item in project.importDirs:
                self.importDirList.addItem( item )
            if self.importDirList.count() > 0:
                self.importDirList.setCurrentRow( 0 )
                self.delImportDirButton.setEnabled( True )

            self.scriptEdit.setFocus()

        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 600, 400 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )
        gridLayout = QGridLayout()

        # Project name
        nameLabel = QLabel( self )
        nameLabel.setText( "Project name:" )
        gridLayout.addWidget( nameLabel, 0, 0, 1, 1 )
        self.nameEdit = QLineEdit( self )
        self.nameEdit.setToolTip( "Type a project name without a path" )
        self.nameEdit.installEventFilter( self )
        gridLayout.addWidget( self.nameEdit, 0, 1, 1, 1 )

        # Project dir
        dirLabel = QLabel( self )
        dirLabel.setText( "Project directory:" )
        gridLayout.addWidget( dirLabel, 1, 0, 1, 1 )
        self.dirEdit = QLineEdit( self )
        self.dirEdit.setToolTip( "Not existed directories will be created" )
        gridLayout.addWidget( self.dirEdit, 1, 1, 1, 1 )
        self.dirButton = QPushButton( self )
        self.dirButton.setText( "..." )
        gridLayout.addWidget( self.dirButton, 1, 2, 1, 1 )
        self.dirCompleter = DirCompleter( self.dirEdit )

        # Project script
        mainScriptLabel = QLabel( "Main script:", self )
        gridLayout.addWidget( mainScriptLabel, 2, 0, 1, 1 )
        self.scriptEdit = QLineEdit( self )
        self.scriptEdit.setToolTip( "Project main script, " \
                                    "used when the project is run" )
        gridLayout.addWidget( self.scriptEdit, 2, 1, 1, 1 )
        self.scriptButton = QPushButton( "...", self )
        gridLayout.addWidget( self.scriptButton, 2, 2, 1, 1 )
        self.fileCompleter = FileCompleter( self.scriptEdit )

        # Import dirs
        importLabel = QLabel( self )
        importLabel.setText( "Import directories:" )
        importLabel.setAlignment( Qt.AlignTop )
        gridLayout.addWidget( importLabel, 3, 0, 1, 1 )
        self.importDirList = QListWidget( self )
        self.importDirList.setAlternatingRowColors( True )
        self.importDirList.setSelectionMode( QAbstractItemView.SingleSelection )
        self.importDirList.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.importDirList.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.importDirList.setToolTip( "Directories where to look for " \
                                       "project specific imports" )
        gridLayout.addWidget( self.importDirList, 3, 1, 1, 1 )

        self.addImportDirButton = QPushButton( self )
        self.addImportDirButton.setText( "Add dir" )
        self.delImportDirButton = QPushButton( self )
        self.delImportDirButton.setText( "Delete dir" )
        self.delImportDirButton.setEnabled( False )
        vLayout = QVBoxLayout()
        vLayout.addWidget( self.addImportDirButton )
        vLayout.addWidget( self.delImportDirButton )
        vLayout.addStretch( 0 )
        gridLayout.addLayout( vLayout, 3, 2, 1, 1 )

        # Version
        versionLabel = QLabel( self )
        versionLabel.setText( "Version:" )
        gridLayout.addWidget( versionLabel, 4, 0, 1, 1 )
        self.versionEdit = QLineEdit( self )
        gridLayout.addWidget( self.versionEdit, 4, 1, 1, 1 )

        # Author
        authorLabel = QLabel( self )
        authorLabel.setText( "Author:" )
        gridLayout.addWidget( authorLabel, 5, 0, 1, 1 )
        self.authorEdit = QLineEdit( self )
        gridLayout.addWidget( self.authorEdit, 5, 1, 1, 1 )

        # E-mail
        emailLabel = QLabel( self )
        emailLabel.setText( "E-mail:" )
        gridLayout.addWidget( emailLabel, 6, 0, 1, 1 )
        self.emailEdit = QLineEdit( self )
        gridLayout.addWidget( self.emailEdit, 6, 1, 1, 1 )

        # License
        licenseLabel = QLabel( self )
        licenseLabel.setText( "License:" )
        gridLayout.addWidget( licenseLabel, 7, 0, 1, 1 )
        self.licenseEdit = QLineEdit( self )
        gridLayout.addWidget( self.licenseEdit, 7, 1, 1, 1 )

        # Copyright
        copyrightLabel = QLabel( self )
        copyrightLabel.setText( "Copyright:" )
        gridLayout.addWidget( copyrightLabel, 8, 0, 1, 1 )
        self.copyrightEdit = QLineEdit( self )
        gridLayout.addWidget( self.copyrightEdit, 8, 1, 1, 1 )

        # Description
        descriptionLabel = QLabel( self )
        descriptionLabel.setText( "Description:" )
        descriptionLabel.setAlignment( Qt.AlignTop )
        gridLayout.addWidget( descriptionLabel, 9, 0, 1, 1 )
        self.descriptionEdit = QTextEdit( self )
        self.descriptionEdit.setTabChangesFocus( True )
        self.descriptionEdit.setAcceptRichText( False )
        gridLayout.addWidget( self.descriptionEdit, 9, 1, 1, 1 )

        # Creation date
        creationDateLabel = QLabel( self )
        creationDateLabel.setText( "Creation date:" )
        gridLayout.addWidget( creationDateLabel, 10, 0, 1, 1 )
        self.creationDateEdit = QLineEdit( self )
        self.creationDateEdit.setReadOnly( True )
        self.creationDateEdit.setFocusPolicy( Qt.NoFocus )
        self.creationDateEdit.setDisabled( True )
        gridLayout.addWidget( self.creationDateEdit, 10, 1, 1, 1 )

        # Project UUID
        uuidLabel = QLabel( self )
        uuidLabel.setText( "UUID:" )
        gridLayout.addWidget( uuidLabel, 11, 0, 1, 1 )
        self.uuidEdit = QLineEdit( self )
        self.uuidEdit.setReadOnly( True )
        self.uuidEdit.setFocusPolicy( Qt.NoFocus )
        self.uuidEdit.setDisabled( True )
        gridLayout.addWidget( self.uuidEdit, 11, 1, 1, 1 )

        verticalLayout.addLayout( gridLayout )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Cancel | \
                                      QDialogButtonBox.Ok )
        verticalLayout.addWidget( buttonBox )

        nameLabel.setBuddy( self.nameEdit )
        dirLabel.setBuddy( self.dirEdit )
        versionLabel.setBuddy( self.versionEdit )
        authorLabel.setBuddy( self.authorEdit )
        emailLabel.setBuddy( self.emailEdit )
        licenseLabel.setBuddy( self.licenseEdit )
        copyrightLabel.setBuddy( self.copyrightEdit )
        descriptionLabel.setBuddy( self.descriptionEdit )


        self.connect( buttonBox, SIGNAL( "accepted()" ), self.onOKButton )
        self.connect( buttonBox, SIGNAL( "rejected()" ), self.reject )
        self.connect( self.dirButton, SIGNAL( "clicked()" ), self.onDirButton )
        self.connect( self.scriptButton, SIGNAL( "clicked()" ),
                      self.onScriptButton )
        self.connect( self.importDirList, SIGNAL( "currentRowChanged(int)" ),
                      self.onImportDirRowChanged )
        self.connect( self.addImportDirButton,
                      SIGNAL( "clicked()" ), self.onAddImportDir )
        self.connect( self.delImportDirButton,
                      SIGNAL( "clicked()" ), self.onDelImportDir )
        self.connect( self.nameEdit,  SIGNAL( "textEdited(const QString &)" ),
                      self.onProjectNameChanged )

        self.setTabOrder( self.nameEdit, self.dirEdit )
        self.setTabOrder( self.dirEdit, self.dirButton )
        self.setTabOrder( self.dirButton, self.scriptEdit )
        self.setTabOrder( self.scriptEdit, self.scriptButton )
        self.setTabOrder( self.scriptButton, self.importDirList )
        self.setTabOrder( self.importDirList, self.addImportDirButton )
        self.setTabOrder( self.addImportDirButton, self.delImportDirButton )
        self.setTabOrder( self.delImportDirButton, self.versionEdit )
        self.setTabOrder( self.versionEdit, self.authorEdit )
        self.setTabOrder( self.authorEdit, self.emailEdit )
        self.setTabOrder( self.emailEdit, self.licenseEdit )
        self.setTabOrder( self.licenseEdit, self.copyrightEdit )
        self.setTabOrder( self.copyrightEdit, self.descriptionEdit )
        self.setTabOrder( self.descriptionEdit, buttonBox )
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

    def onScriptButton( self ):
        " Displays a file selection dialog "
        scriptName = QFileDialog.getOpenFileName( self,
                        "Select project main script",
                        self.dirEdit.text() )

        if not scriptName.isEmpty():
            self.scriptEdit.setText( os.path.normpath( str( scriptName ) ) )
        return

    def onImportDirRowChanged( self, row ):
        " Triggered when a current row in the import dirs is changed "
        self.delImportDirButton.setEnabled( row != -1 )
        return

    def onAddImportDir( self ):
        " Displays a directory selection dialog "

        dirName = QFileDialog.getExistingDirectory( self,
                    "Select import directory",
                    self.dirEdit.text(),
                    QFileDialog.Options( QFileDialog.ShowDirsOnly ) )

        if dirName.isEmpty():
            return

        dirName = str( dirName )

        # There are 2 cases: new project or
        # editing the existed project properties
        if self.__project is None:
            # It a new project; the project path could be editedd
            dirToInsert = dirName
        else:
            # This is an existed project; no way the project path is changed
            # Let's decide it a relative path should be used here
            if self.__project.isProjectDir( dirName ):
                dirToInsert = relpath( dirName, str( self.dirEdit.text() ) )
            else:
                dirToInsert = dirName

        index = 0
        while index < self.importDirList.count():
            if self.importDirList.item( index ).text() == dirToInsert:
                logging.warning( "The directory '" + dirName +
                                 "' is already in the list of " \
                                 "imported directories and is not added." )
                return
            index += 1

        self.importDirList.addItem( dirToInsert )
        self.importDirList.setCurrentRow( self.importDirList.count() - 1 )
        return

    def onDelImportDir( self ):
        " Triggered when an import dir should be deleted "

        rowToDelete = self.importDirList.currentRow()
        if  rowToDelete == -1:
            self.delImportDirButton.setEnabled( False )
            return

        self.importDirList.takeItem( rowToDelete )
        if self.importDirList.count() == 0:
            self.delImportDirButton.setEnabled( False )
        else:
            self.importDirList.setCurrentRow( self.importDirList.count() - 1 )
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
        projectFileName = dirName
        if not projectFileName.endswith( os.path.sep ):
            projectFileName += os.path.sep
        projectFileName += str( self.nameEdit.text() ).strip()
        if not projectFileName.endswith( ".cdm" ):
            projectFileName += ".cdm"

        if os.path.exists( projectFileName ):
            QMessageBox.critical( self, "Error",
                                  "The project file " + projectFileName + \
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
                                      "The project directory " \
                                      "may not be a file" )
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

        # Save the absolute file name for further reading it by the caller
        self.absProjectFileName = projectFileName

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
        self.scriptEdit.setDisabled( True )
        self.scriptButton.setDisabled( True )
        self.importDirList.setDisabled( True )
        self.addImportDirButton.setDisabled( True )
        self.delImportDirButton.setDisabled( True )
        self.versionEdit.setDisabled( True )
        self.authorEdit.setDisabled( True )
        self.emailEdit.setDisabled( True )
        self.licenseEdit.setDisabled( True )
        self.copyrightEdit.setDisabled( True )
        self.descriptionEdit.setDisabled( True )
        self.creationDateEdit.setDisabled( True )
        self.uuidEdit.setDisabled( True )
        return

