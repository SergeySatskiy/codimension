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


""" imports diagram dialog """


import os, os.path, logging
from PyQt4.QtCore                import Qt, SIGNAL, QTimer
from PyQt4.QtGui                 import QDialog, QDialogButtonBox, \
                                        QVBoxLayout, QCheckBox, QLabel, \
                                        QProgressBar, QApplication, QCursor
from modules                     import buildDirModules
from utils.globals               import GlobalData
from pythonparser.cdmbriefparser import getBriefModuleInfoFromMemory
from utils.fileutils             import detectFileType, PythonFileType, \
                                        Python3FileType


class DgmConnection:
    " Holds information about one connection "

    # Connection types
    ModuleDoc        = 0
    ModuleDependency = 1

    def __init__( self ):
        self.kind = -1          # See connection types
        self.source = ""        # Connection start point
        self.target = ""        # Connection end point
        self.title = ""         # Connection title

        self.refFile = ""       # File for the title
        self.refLine = -1       # Line for the title
        return

class DgmDocstring:
    " Holds information about one docstring "

    def __init__( self ):
        self.name = ""          # unique name
        self.text = ""          # Module docstring

        self.refFile = ""       # File of the docstring
        self.refLine = -1       # Line of the docstring
        return

class DgmModule:
    " Holds information about one module "

    # Module types
    NonProjectModule = 0
    ModuleOfInterest = 1
    OtherProjectModule = 2

    def __init__( self ):
        self.name = ""          # unique name
        self.kind = -1          # See module types
        self.title = ""         # title
        self.classes = []       # list of classes and their line numbers
        self.funcs = []         # list of funcs and their line numbers
        self.globs = []         # list of global vars and their line numbers

        self.refFile = ""       # File of the module
        return


class ImportDiagramModel:
    " Holds information about data model of an import diagram "

    def __init__( self ):
        self.modules = []
        self.docstrings = []
        self.connections = []
        return




class ImportDiagramOptions:
    " Holds the generated diagram settings "
    def __init__( self ):
        self.includeClasses = True
        self.includeFuncs = True
        self.includeGlobs = True
        self.includeDocs = True
        self.includeConnText = True
        return


class ImportsDiagramDialog( QDialog, object ):
    """ Imports diagram properties dialog implementation """

    # Options of providing a diagram
    SingleFile     = 0
    DirectoryFiles = 1
    ProjectFiles   = 2
    SingleBuffer   = 3

    def __init__( self, option, path = "", parent = None ):

        QDialog.__init__( self, parent )

        self.__cancelRequest = False
        self.__inProgress = False
        self.__option = option
        self.__path = path

        # Avoid pylint complains
        self.includeClassesBox = None
        self.includeFuncsBox = None
        self.includeGlobsBox = None
        self.includeDocsBox = None
        self.includeConnTextBox = None

        self.options = ImportDiagramOptions()

        self.__createLayout()
        title = "Imports diagram settings for "
        if self.__option == self.SingleFile:
            title += os.path.basename( self.__path )
        elif self.__option == self.DirectoryFiles:
            title += "directory " + self.__path
        elif self.__option == self.ProjectFiles:
            title += "the whole project"
        else:
            title += "modified file " + os.path.basename( self.__path )
        self.setWindowTitle( title )
        return

    def __updateOptions( self, state = 0 ):
        " Updates the saved options "
        self.options.includeClasses = self.includeClassesBox.isChecked()
        self.options.includeFuncs = self.includeFuncsBox.isChecked()
        self.options.includeGlobs = self.includeGlobsBox.isChecked()
        self.options.includeDocs = self.includeDocsBox.isChecked()
        self.options.includeConnText = self.includeConnTextBox.isChecked()
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 400, 100 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )

        # Check boxes
        self.includeClassesBox = QCheckBox( self )
        self.includeClassesBox.setText( "Show &classes in modules" )
        self.includeClassesBox.setChecked( True )
        self.connect( self.includeClassesBox, SIGNAL( 'stateChanged(int)' ),
                      self.__updateOptions )
        self.includeFuncsBox = QCheckBox( self )
        self.includeFuncsBox.setText( "Show &functions in modules" )
        self.includeFuncsBox.setChecked( True )
        self.connect( self.includeFuncsBox, SIGNAL( 'stateChanged(int)' ),
                      self.__updateOptions )
        self.includeGlobsBox = QCheckBox( self )
        self.includeGlobsBox.setText( "Show &global variables in modules" )
        self.includeGlobsBox.setChecked( True )
        self.connect( self.includeGlobsBox, SIGNAL( 'stateChanged(int)' ),
                      self.__updateOptions )
        self.includeDocsBox = QCheckBox( self )
        self.includeDocsBox.setText( "Show modules &docstrings" )
        self.includeDocsBox.setChecked( True )
        self.connect( self.includeDocsBox, SIGNAL( 'stateChanged(int)' ),
                      self.__updateOptions )
        self.includeConnTextBox = QCheckBox( self )
        self.includeConnTextBox.setText( "Show connection &labels" )
        self.includeConnTextBox.setChecked( True )
        self.connect( self.includeConnTextBox, SIGNAL( 'stateChanged(int)' ),
                      self.__updateOptions )

        verticalLayout.addWidget( self.includeClassesBox )
        verticalLayout.addWidget( self.includeFuncsBox )
        verticalLayout.addWidget( self.includeGlobsBox )
        verticalLayout.addWidget( self.includeDocsBox )
        verticalLayout.addWidget( self.includeConnTextBox )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Cancel )
        generateButton = buttonBox.addButton( "Generate",
                                              QDialogButtonBox.ActionRole )
        generateButton.setDefault( True )
        self.connect( generateButton, SIGNAL( 'clicked()' ), self.accept )
        verticalLayout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        return


class ImportsDiagramProgress( QDialog ):
    " Progress of the diagram generator "

    def __init__( self, what, options, path = "", buf = "", parent = None ):
        QDialog.__init__( self, parent )
        self.__cancelRequest = False
        self.__inProgress = False

        self.__what = what
        self.__options = options
        self.__path = path          # could be a dir or a file
        self.__buf = buf            # content in case of a modified file

        self.__projectModules = {}  # dir -> [ imports ]
        self.__filesInfo = {}       # file -> parsed content

        self.__createLayout()
        self.setWindowTitle( 'Imports diagram generator' )
        QTimer.singleShot( 0, self.__process )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 450, 20 )
        self.setSizeGripEnabled( True )

        self.verticalLayout = QVBoxLayout( self )

        # Info label
        self.infoLabel = QLabel( self )
        self.verticalLayout.addWidget( self.infoLabel )

        # Progress bar
        self.progressBar = QProgressBar( self )
        self.progressBar.setValue( 0 )
        self.progressBar.setOrientation( Qt.Horizontal )
        self.verticalLayout.addWidget( self.progressBar )

        # Buttons
        self.buttonBox = QDialogButtonBox( self )
        self.buttonBox.setOrientation( Qt.Horizontal )
        self.buttonBox.setStandardButtons( QDialogButtonBox.Close )
        self.verticalLayout.addWidget( self.buttonBox )

        self.connect( self.buttonBox, SIGNAL( "rejected()" ), self.__onClose )
        return

    def __onClose( self ):
        " triggered when the close button is clicked "

        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()
        return

    def __process( self ):
        " Accumulation process "

        self.__inProgress = True
        self.progressBar.setRange( 0, 5 )

        # Stage 1 - building a list of the project modules
        self.infoLabel.setText( "Building a list of the project modules..." )
        self.progressBar.setValue( 1 )
        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            projectDirs = GlobalData().project.getProjectDirs()
            for path in projectDirs:
                if self.__buildProjectModules( path ) == False:
                    QApplication.restoreOverrideCursor()
                    self.__inProgress = False
                    self.__onClose()
                    return
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            self.__inProgress = False
            self.__onClose()
            return

        # Stage 2 - process input python files
        self.progressBar.setValue( 2 )

        try:
            self.__buildContentInfo()
            if self.__cancelRequest:
                QApplication.restoreOverrideCursor()
                self.__inProgress = False
                self.__onClose()
                return
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            self.__inProgress = False
            self.__onClose()
            return

        if len( self.__filesInfo ) == 0:
            logging.warning( "No modules were identified to build diagram for" )
            QApplication.restoreOverrideCursor()
            self.__inProgress = False
            self.__onClose()
            return

        # Stage 3 - build the diagram objects
        self.progressBar.setValue( 3 )



        QApplication.restoreOverrideCursor()
        self.infoLabel.setText( 'Done' )
        self.__inProgress = False

        return

    def __buildProjectModules( self, path ):
        " Builds the projects modules list "

        imports = buildDirModules( path, self.infoLabel )
        if len( imports ) > 0:
            self.__projectModules[ path ] = imports
            print path + " -> " + str( imports )
        QApplication.processEvents()
        if self.__cancelRequest:
            return False
        for item in os.listdir( path ):
            if item in [ ".svn", ".cvs" ]:
                continue
            candidate = path + item + os.path.sep
            if os.path.isdir( candidate ):
                if self.__buildProjectModules( candidate ) == False:
                    return False
        return True

    def __buildContentInfo( self ):
        " Builds a map of file names and the parsed info "
        if self.__what == ImportsDiagramDialog.SingleBuffer:
            self.infoLabel.setText( "Parsing " + self.__path + "..." )
            QApplication.processEvents()
            self.__filesInfo[ self.__path ] = \
                        getBriefModuleInfoFromMemory( self.__buf )
            return

        if self.__what == ImportsDiagramDialog.SingleFile:
            self.__path = os.path.realpath( self.__path )
            if GlobalData().project.isProjectFile( self.__path ):
                infoSrc = GlobalData().project.briefModinfoCache
            else:
                infoSrc = GlobalData().briefModinfoCache
            self.infoLabel.setText( "Parsing " + self.__path + "..." )
            QApplication.processEvents()
            self.__filesInfo[ self.__path ] = infoSrc.get( self.__path )
            return

        if self.__what == ImportsDiagramDialog.ProjectFiles:
            # The whole project was requested
            infoSrc = GlobalData().project.briefModinfoCache
            for fName in GlobalData().project.filesList:
                if fName.endswith( os.path.sep ):
                    continue
                fileType = detectFileType( fName )
                if fileType in [ PythonFileType, Python3FileType ]:
                    self.infoLabel.setText( "Parsing " + fName + "..." )
                    QApplication.processEvents()
                    self.__filesInfo[ fName ] = infoSrc.get( fName )
            return

        # Recursive dir was required
        self.__path = os.path.realpath( self.__path )
        if not self.__path.endswith( os.path.sep ):
            self.__path += os.path.sep
        if GlobalData().project.isProjectDir( self.__path ):
            self.__buildDirContentInfo( self.__path,
                             GlobalData().project.briefModinfoCache )
        else:
            self.__buildDirContentInfo( self.__path,
                             GlobalData().briefModinfoCache )
        return

    def __buildDirContentInfo( self, path, srcInfo ):
        " Recursively builds the info for a directory "

        for item in os.listdir( path ):
            if os.path.isdir( path + item ):
                self.__buildDirContentInfo( path + item + os.path.sep,
                                            srcInfo )
                continue
            if self.__cancelRequest:
                return
            fileType = detectFileType( path + item )
            if fileType in [ PythonFileType, Python3FileType ]:
                # Avoid symlinks
                fName = os.path.realpath( path + item )
                self.infoLabel.setText( "Parsing " + fName + "..." )
                QApplication.processEvents()
                self.__filesInfo[ fName ] = infoSrc.get( fName )

        return


