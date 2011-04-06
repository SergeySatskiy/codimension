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
        self.objName = ""       # Unique object name
        self.kind = -1          # See connection types
        self.source = ""        # Connection start point
        self.target = ""        # Connection end point
        self.labels = []        # Connection labels: list of what imported
                                # ImportWhat objects
        return

    def toGraphviz( self ):
        " Serialize the connection in graphviz format "
        attributes = 'id="' + self.objName + '"'
        label = ""
        for what in self.labels:
            if label != "":
                label += "\n"
            label += what.name
        if label != "":
            attributes += ', label="' + label + '"'
        return self.source + " -> " + self.target + '[ ' + attributes + ' ];'

    def __eq__( self, other ):
        " Checks if the connection connects the same objects "
        return self.source == other.source and self.target == other.target


class DgmDocstring:
    " Holds information about one docstring "

    def __init__( self ):
        self.objName = ""       # Unique object name
        self.text = ""          # Module docstring

        self.refFile = ""       # File of the docstring
        return

    def toGraphviz( self ):
        " Serialize the docstring box in graphviz format "
        return self.objName + ' [ shape=box, label="' + self.text + '" ];'


class DgmModule:
    " Holds information about one module "

    # Module types
    NonProjectModule = 0
    ModuleOfInterest = 1
    OtherProjectModule = 2

    def __init__( self ):
        self.objName = ""       # Unique object name
        self.kind = -1          # See module types
        self.title = ""         # title
        self.classes = []       # list of classes objects
        self.funcs = []         # list of funcs objects
        self.globs = []         # list of global var objects

        self.refFile = ""       # File of the module
        return

    def toGraphviz( self ):
        " Serialize the module box in graphviz format "
        classesPart = ""
        for klass in self.classes:
            if classesPart != "":
                classesPart += "\n"
            classesPart += klass.name
        funcsPart = ""
        for func in self.funcs:
            if funcsPart != "":
                funcsPart += "\n"
            funcsPart += func.name
        globsPart = ""
        for glob in self.globs:
            if globsPart != "":
                globsPart += "\n"
            globsPart += glob.name
        return self.objName + ' [ shape=record, label="' + self.title + '|' + \
               classesPart + '|' + funcsPart + '|' + globsPart + '" ];'

    def __eq__( self, other ):
        " Compares two module boxes "
        return self.refFile == other.refFile


class ImportDiagramModel:
    " Holds information about data model of an import diagram "

    def __init__( self ):
        self.modules = []
        self.docstrings = []
        self.connections = []

        self.__objectsCounter = -1
        return

    def clear( self ):
        " Clears the diagram model "
        self.modules = []
        self.docstrings = []
        self.connections = []

        self.__objectsCounter = -1
        return

    def toGraphviz( self ):
        " Serialize the import diagram in graphviz format "
        result = "digraph ImportsDiagram { "
        for item in self.docstrings:
            result += item.toGraphviz() + "\n"
        for item in self.modules:
            result += item.toGraphviz() + "\n"
        for item in self.connections:
            result += item.toGraphviz() + "\n"
        result += " }"
        return result

    def __newName( self ):
        " Generates a short name for the graphviz objects "
        self.__objectsCounter += 1
        return "obj" + str( self.__objectsCounter )

    def addConnection( self, conn ):
        " Adds a connection and provides its name "
        # The connections can be added twice if there are two import directives
        index = -1
        for idx in xrange( 0, len( self.connections ) ):
            if self.connections[ idx ] == conn:
                index = idx
                break

        if index == -1:
            # new connection, generate name and add
            conn.objName = self.__newName()
            self.connections.append( conn )
            return conn.objName

        # There is already such a connection. So merge labels.
        self.connections[ index ].labels += conn.labels
        return self.connections[ index ].objName

    def addDocstringBox( self, docBox ):
        " Adds a module docstring "
        # Docstring boxes cannot appear twice so just add it
        docBox.objName = self.__newName()
        self.docstrings.append( docBox )
        return docBox.objName

    def addModule( self, modBox ):
        " Adds a module box "
        # It might happened that the same module appeared more than once
        index = -1
        for idx in xrange( 0, len( self.modules ) ):
            if self.modules[ idx ] == modBox:
                index = idx
                break

        if index == -1:
            # New module box, generate name and add it
            modBox.objName = self.__newName()
            self.modules.append( modBox )
            return modBox.objName

        # There is already such a box, so the box type might need to be
        # adjusted
        if modBox.kind == self.modules[ index ].kind:
            return self.modules[ index ].objName

        # It must not be a replacement of the out of the project module
        if modBox.kind == DgmModule.NonProjectModule or \
           self.modules[ index ].kind == DgmModule.NonProjectModule:
            raise Exception( "Inconsistency. There must be no replacements " \
                             "for a system module." )

        if modBox.kind == DgmModule.ModuleOfInterest:
            # Replace the existed one with a new one but keep the object name
            modBox.objName = self.modules[ index ].objName
            self.modules[ index ] = modBox
            return modBox.objName

        # No need in adjustments
        return self.modules[ index ].objName

    def findModule( self, name ):
        " Searches for a module by the object name "
        for obj in self.modules:
            if obj.objName == name:
                return obj
        return None

    def findConnection( self, name ):
        " Searches for a connection by the object name "
        for obj in self.connections:
            if obj.objName == name:
                return obj
        return None

    def findDocstring( self, name ):
        " Searches for a docstring by the object name "
        for obj in self.docstrings:
            if obj.objName == name:
                return obj
        return None



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

        state = state   # Avoid pylint complains
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

        self.__projectModules = {}              # dir -> [ imports ]
        self.__filesInfo = {}                   # file -> parsed content
        self.__dataModel = ImportDiagramModel()

        # Avoid pylint complains
        self.progressBar = None
        self.infoLabel = None

        self.__createLayout()
        self.setWindowTitle( 'Imports diagram generator' )
        QTimer.singleShot( 0, self.__process )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 450, 20 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )

        # Info label
        self.infoLabel = QLabel( self )
        verticalLayout.addWidget( self.infoLabel )

        # Progress bar
        self.progressBar = QProgressBar( self )
        self.progressBar.setValue( 0 )
        self.progressBar.setOrientation( Qt.Horizontal )
        verticalLayout.addWidget( self.progressBar )

        # Buttons
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Close )
        verticalLayout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.__onClose )
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
        try:
            self.__buildDiagramDataModel()
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

        # Stage 4 - generating the graphviz layout
        self.progressBar.setValue( 4 )

        print self.__dataModel.toGraphviz()


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
                self.__filesInfo[ fName ] = srcInfo.get( fName )

        return

    def __buildDiagramDataModel( self ):
        " Builds the diargam data model "
        self.__dataModel.clear()

        for fName in self.__filesInfo:
            # Generate the module box
            modBox = DgmModule()
            modBox.refFile = fName

            modBox.kind = DgmModule.ModuleOfInterest
            modBox.title = os.path.basename( fName ).split( '.' )[ 0 ]

            info = self.__filesInfo[ fName ]
            if self.__options.includeClasses:
                for klass in info.classes:
                    modBox.classes.append( klass )

            if self.__options.includeFuncs:
                for func in info.functions:
                    modBox.funcs.append( func )

            if self.__options.includeGlobs:
                for glob in info.globals:
                    modBox.globs.append( glob )

            # Add the module box
            modBoxName = self.__dataModel.addModule( modBox )

            # Docstring box
            if self.__options.includeDocs:
                if info.docstring != "":
                    docBox = DgmDocstring()
                    docBox.text = info.docstring
                    docBox.refFile = fName

                    # Add the box and its connection
                    docBoxName = self.__dataModel.addDocstringBox( docBox )

                    conn = DgmConnection()
                    conn.kind = DgmConnection.ModuleDoc
                    conn.source = modBoxName
                    conn.target = docBoxName
                    self.__dataModel.addConnection( conn )

            # Other modules, in/out of the project
            for item in info.imports:

                impBox = DgmModule()
                impFilePath = self.__getProjectPathForImport( fName, item.name )
                if impFilePath == "":
                    impBox.kind = DgmModule.NonProjectModule
                    impBox.title = item.name
                else:
                    impBox.kind = DgmModule.OtherProjectModule
                    impBox.title = os.path.basename( impFilePath ).split('.')[0]
                    impBox.refFile = impFilePath

                    cache = GlobalData().project.briefModinfoCache
                    otherInfo = cache.get( impFilePath )
                    if self.__options.includeClasses:
                        for klass in otherInfo.clesses:
                            impBox.classes.append( klass )

                    if self.__options.includeFuncs:
                        for func in otherInfo.functions:
                            impBox.funcs.append( func )

                    if self.__options.includeGlobs:
                        for glob in otherInfo.globals:
                            impBox.globs.append( glob )

                # Add the box
                impBoxName = self.__dataModel.addModule( impBox )

                impConn = DgmConnection()
                impConn.kind = DgmConnection.ModuleDependency
                impConn.source = modBoxName
                impConn.target = impBoxName

                if self.__options.includeConnText:
                    for impWhat in item.what:
                        if impWhat.name != "":
                            impConn.labels.append( impWhat )

                self.__dataModel.addConnection( impConn )
        return

    def __getProjectPathForImport( self, originatorPath, importName ):
        """ Provides a path to a project file or
            empty string if it is an outside import.
            originatorPath - abs path of a file from which something is imported
            importName - how import looks like, e.g.: os.path
        """
        candidatePath = os.path.dirname( originatorPath ) + os.path.sep
        while True:
            path = self.__getPathForKey( candidatePath, importName )
            if path is not None:
                return path
            # strip one tail dir
            newCandidate = os.path.dirname( candidatePath[ : -1 ] ) + \
                           os.path.sep
            if newCandidate == candidatePath:
                break
            candidatePath = newCandidate
        return ""

    def __getPathForKey( self, path, importName ):
        " Checks a single key in the imports map "
        importsList = None
        try:
            importsList = self.__projectModules[ path ]
        except:
            return None

        if importName not in importsList:
            return None

        # OK, this is a project scope import. Get the name.
        inclompete = path + importName.replace( '.', os.path.sep )
        dirName = os.path.dirname( inclompete ) + os.path.sep
        fileNameBegin = os.path.basename( inclompete ) + "."

        for item in os.listdir( dirName ):
            if item.startswith( fileNameBegin ):
                if detectFileType( dirName + item ) in [ PythonFileType,
                                                         Python3FileType ]:
                    return dirName + item

        raise Exception( "Inconsistency detected: disappeared import '" + \
                         importName + "' for " + path )

