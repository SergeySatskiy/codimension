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
from PyQt4.QtCore import Qt, SIGNAL, QTimer
from PyQt4.QtGui import QDialog, QDialogButtonBox, QVBoxLayout, QCheckBox, \
                        QLabel, QProgressBar, QApplication, QGraphicsScene
from utils.globals import GlobalData
from cdmbriefparser import getBriefModuleInfoFromMemory
from plaindotparser import getGraphFromDescriptionData
from importsdgmgraphics import ImportsDgmDocConn, ImportsDgmDependConn, \
                               ImportsDgmSystemWideModule, \
                               ImportsDgmUnknownModule, \
                               ImportsDgmBuiltInModule, \
                               ImportsDgmModuleOfInterest, \
                               ImportsDgmOtherPrjModule, \
                               ImportsDgmDocNote, ImportsDgmEdgeLabel
from autocomplete.completelists import getSystemWideModules



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
        attributes = 'id="' + self.objName + '", arrowhead=none'
        label = ""
        for what in self.labels:
            if label != "":
                label += "\\n"
            label += what.name
        if label != "":
            attributes += ', label="' + label + \
                          '", fontname=Arial, fontsize=10'

        return self.source + " -> " + self.target + '[ ' + attributes + ' ];'

    def __eq__( self, other ):
        " Checks if the connection connects the same objects "
        return self.source == other.source and self.target == other.target


class DgmDocstring:
    " Holds information about one docstring "

    def __init__( self ):
        self.objName = ""       # Unique object name
        self.docstring = None   # Module docstring object

        self.refFile = ""       # File of the docstring
        return

    def toGraphviz( self ):
        " Serialize the docstring box in graphviz format "
        escapedText = self.docstring.text.replace( '\n', '\\n' )
        escapedText = escapedText.replace( '"', '\\"' )
        attributes = 'shape=box, fontname=Arial, fontsize=10'
        return self.objName + \
               ' [ ' + attributes + ', label="' + escapedText + '" ];'


class DgmModule:
    " Holds information about one module "

    # Module types
    ModuleOfInterest = 0
    OtherProjectModule = 1
    SystemWideModule = 2
    BuiltInModule = 3
    UnknownModule = 4

    def __init__( self ):
        self.objName = ""       # Unique object name
        self.kind = -1          # See module types
        self.title = ""         # title
        self.classes = []       # list of classes objects
        self.funcs = []         # list of funcs objects
        self.globs = []         # list of global var objects
        self.imports = []       # list of imports

        self.refFile = ""       # File of the module
        self.docstring = ""
        return

    def toGraphviz( self ):
        " Serialize the module box in graphviz format "
        classesPart = ""
        funcsPart = ""
        globsPart = ""

        for klass in self.classes:
            if classesPart != "":
                classesPart += "\\n"
            classesPart += klass.name
        for func in self.funcs:
            if funcsPart != "":
                funcsPart += "\\n"
            funcsPart += func.name
        for glob in self.globs:
            if globsPart != "":
                globsPart += "\\n"
            globsPart += glob.name

        attributes = 'shape=record, fontname=Arial, fontsize=10'
        title = self.title
        if title.startswith( '__init__' ):
            # This is a directory import, use thr dir name instead
            title = os.path.basename( os.path.dirname( self.refFile ) )

        if self.kind in [ DgmModule.ModuleOfInterest,
                          DgmModule.OtherProjectModule ]:
            return self.objName + ' [ ' + attributes + \
                   ', label="{' + title + '|' + \
                   classesPart + '|' + funcsPart + '|' + globsPart + '}" ];'
        return self.objName + ' [ ' + attributes + \
               ', label="{' + title + '}" ];'

    def __eq__( self, other ):
        " Compares two module boxes "
        return self.objName == other.objName
#        if self.kind == DgmModule.NonProjectModule and \
#           other.kind == DgmModule.NonProjectModule:
#            return self.title == other.title
#        return self.refFile == other.refFile


class DgmRank:
    " Holds information about one rank "

    def __init__( self ):
        self.firstObj = ""
        self.secondObj = ""
        return

    def __eq__( self, other ):
        " Compares two ranks "
        return self.firstObj == other.firstObj and \
               self.secondObj == other.secondObj

    def toGraphviz( self ):
        " Serialize the rank in graphviz format "
        return '{ rank=same; "' + self.firstObj + '"; "' + \
               self.secondObj + '"; }'


class ImportDiagramModel:
    " Holds information about data model of an import diagram "

    def __init__( self ):
        self.modules = []
        self.docstrings = []
        self.connections = []
        self.ranks = []

        self.__objectsCounter = -1
        return

    def clear( self ):
        " Clears the diagram model "
        self.modules = []
        self.docstrings = []
        self.connections = []
        self.ranks = []

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
        for item in self.ranks:
            result += item.toGraphviz() + "\n"
        result += "}"
        return result

    def __newName( self ):
        " Generates a short name for the graphviz objects "
        self.__objectsCounter += 1
        return "obj" + str( self.__objectsCounter )

    def addRank( self, rank ):
        " Adds a rank "
        for idx in xrange( 0, len( self.ranks ) ):
            if self.ranks[ idx ] == rank:
                return
        self.ranks.append( rank )
        return

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

    def findConnection( self, name, tail = "" ):
        " Searches for a connection by the object name "
        if tail == "":
            # Search by the connection name
            for obj in self.connections:
                if obj.objName == name:
                    return obj
            return None

        # Search by the name of the objects it connects
        for obj in self.connections:
            if obj.source == name and obj.target == tail:
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
        self.includeDocs = False
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

        # Working process data
        self.__participantFiles = []    # Collected list of files
        self.__projectImportDirs = []
        self.__projectImportsCache = {} # utils.settings -> /full/path/to.py
        self.__dirsToImportsCache = {}  # /dir/path -> { my.mod: path.py, ... }

        self.dataModel = ImportDiagramModel()
        self.scene = QGraphicsScene()

        # Avoid pylint complains
        self.progressBar = None
        self.infoLabel = None

        self.__createLayout()
        self.setWindowTitle( 'Imports/dependencies diagram generator' )
        QTimer.singleShot( 0, self.__process )
        return

    def keyPressEvent( self, event ):
        " Processes the ESC key specifically "
        if event.key() == Qt.Key_Escape:
            self.__onClose()
        else:
            QDialog.keyPressEvent( self, event )
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

    def __buildParticipants( self ):
        " Builds a list of participating files and dirs "
        if self.__what in [ ImportsDiagramDialog.SingleBuffer,
                            ImportsDiagramDialog.SingleFile ]:
            # File exists but could be modified
            self.__path = os.path.realpath( self.__path )
            self.__participantFiles.append( self.__path )
            return

        if self.__what == ImportsDiagramDialog.ProjectFiles:
            self.__scanProjectDirs()
            return

        # This is a recursive directory
        self.__path = os.path.realpath( self.__path )
        self.__scanDirForPythonFiles( self.__path + os.path.sep )
        return

    def __scanDirForPythonFiles( self, path ):
        " Scans the directory for the python files recursively "
        for item in os.listdir( path ):
            if item in [ ".svn",  ".cvs" ]:
                continue
            if os.path.isdir( path + item ):
                self.__scanDirForPythonFiles( path + item + os.path.sep )
                continue
            if item.endswith( ".py" ) or item.endswith( ".py3" ):
                fName = os.path.realpath( path + item )
                # If it was a link, the target could be non-python
                if fName.endswith( ".py" ) or fName.endswith( ".py3" ):
                    self.__participantFiles.append( fName )
        return

    def __scanProjectDirs( self ):
        " Populates participant lists from the project files "
        for fName in GlobalData().project.filesList:
            if fName.endswith( ".py" ) or fName.endswith( ".py3" ):
                self.__participantFiles.append( fName )
        return

    def isProjectImport( self, importString ):
        " Checks if it is a project import string and provides a path if so "
        if self.__projectImportsCache.has_key( importString ):
            return self.__projectImportsCache[ importString ]

        subpath = importString.replace( '.', os.path.sep )
        candidates = [ subpath + ".py", subpath + ".py3",
                       subpath + os.path.sep + "__init__.py",
                       subpath + os.path.sep + "__init__.py3" ]
        for path in self.__projectImportDirs:
            for item in candidates:
                fName = path + os.path.sep + item
                if os.path.isfile( fName ):
                    self.__projectImportsCache[ importString ] = fName
                    return fName
        return None

    def isLocalImport( self, dirName, importString ):
        " Checks if it is local dir import string and provides a path if so "
        dirFound = False
        if self.__dirsToImportsCache.has_key( dirName ):
            dirFound = True
            importsDict = self.__dirsToImportsCache[ dirName ]
            if importsDict.has_key( importString ):
                return importsDict[ importString ]

        subpath = importString.replace( '.', os.path.sep )
        candidates = [ subpath + ".py", subpath + ".py3",
                       subpath + os.path.sep + "__init__.py",
                       subpath + os.path.sep + "__init__.py3" ]
        for item in candidates:
            fName = dirName + os.path.sep + item
            if os.path.isfile( fName ):
                # Found on the FS. Add to the dictionary
                if dirFound:
                    importsDict[ importString ] = fName
                else:
                    self.__dirsToImportsCache[ dirName ] = { importString: fName }
                return fName
        return None

    def isSystemWideImport( self, importString ):
        " Provides a path to the system wide import or None "
        # Systemwide modules may not have a path if it is a
        # binary module, e.g. an .so library
        try:
            return True, getSystemWideModules()[ importString ]
        except:
            return False, None

    def __addBoxInfo( self, box, info ):
        " Adds information to the given box if so configured "
        if info.docstring is not None:
            box.docstring = info.docstring.text

        if self.__options.includeClasses:
            for klass in info.classes:
                box.classes.append( klass )

        if self.__options.includeFuncs:
            for func in info.functions:
                box.funcs.append( func )

        if self.__options.includeGlobs:
            for glob in info.globals:
                box.globs.append( glob )

        if self.__options.includeConnText:
            for imp in info.imports:
                box.imports.append( imp )

        return

    def __addDocstringBox( self, info, fName, modBoxName ):
        " Adds a docstring box if needed "
        if self.__options.includeDocs:
            if info.docstring is not None:
                docBox = DgmDocstring()
                docBox.docstring = info.docstring
                docBox.refFile = fName

                # Add the box and its connection
                docBoxName = self.dataModel.addDocstringBox( docBox )

                conn = DgmConnection()
                conn.kind = DgmConnection.ModuleDoc
                conn.source = modBoxName
                conn.target = docBoxName
                self.dataModel.addConnection( conn )

                # Add rank for better layout
                rank = DgmRank()
                rank.firstObj = modBoxName
                rank.secondObj = docBoxName
                self.dataModel.addRank( rank )
        return

    def __getSytemWideImportDocstring( self, path ):
        " Provides the system wide module docstring "
        try:
            info = GlobalData().project.briefModinfoCache.get( path )
            if info.docstring is not None:
                return info.docstring.text
            return ""
        except:
            return ""

    def __addSingleFileToDataModel( self, info, fName ):
        " Adds a single file to the data model "
        if fName.endswith( "__init__.py" ) or \
           fName.endswith( "__init__.py3" ):
            if not info.classes and not info.functions and \
               not info.globals and not info.imports:
                # Skip dummy init files
                return

        modBox = DgmModule()
        modBox.refFile = fName

        modBox.kind = DgmModule.ModuleOfInterest
        modBox.title = os.path.basename( fName ).split( '.' )[ 0 ]

        self.__addBoxInfo( modBox, info )
        modBoxName = self.dataModel.addModule( modBox )
        self.__addDocstringBox( info, fName, modBoxName )

        # Add what is imported
        isProjectFile = GlobalData().project.isProjectFile( fName )
        for item in info.imports:
            impBox = DgmModule()

            importPath = None
            systemWideImportPath = None
            if isProjectFile:
                importPath = self.isProjectImport( item.name )
            if importPath is None:
                importPath = self.isLocalImport( os.path.dirname( fName ), item.name )

            if importPath is not None:
                impBox.kind = DgmModule.OtherProjectModule
                impBox.title = os.path.basename( importPath ).split( '.' )[ 0 ]
                impBox.refFile = importPath
                otherInfo = GlobalData().project.briefModinfoCache.get( importPath )

                # It's a local or project import
                self.__addBoxInfo( impBox, otherInfo )

            else:
                impBox.kind = DgmModule.UnknownModule
                impBox.title = item.name

                found, systemWideImportPath = self.isSystemWideImport( item.name )
                if found:
                    if systemWideImportPath is not None:
                        impBox.kind = DgmModule.SystemWideModule
                        impBox.refFile = systemWideImportPath
                        impBox.docstring = \
                            self.__getSytemWideImportDocstring( \
                                            systemWideImportPath )
                    else:
                        impBox.kind = DgmModule.BuiltInModule

            impBoxName = self.dataModel.addModule( impBox )

            impConn = DgmConnection()
            impConn.kind = DgmConnection.ModuleDependency
            impConn.source = modBoxName
            impConn.target = impBoxName

            if self.__options.includeConnText:
                for impWhat in item.what:
                    if impWhat.name != "":
                        impConn.labels.append( impWhat )
            self.dataModel.addConnection( impConn )

        return

    def __process( self ):
        " Accumulation process "

        # Intermediate working data
        self.__participantFiles = []
        self.__projectImportDirs = []
        self.__projectImportsCache = {}

        self.dataModel.clear()
        self.__inProgress = True

        try:
            self.infoLabel.setText( 'Building the list of files to analyze...' )
            QApplication.processEvents()

            # Build the list of participating python files
            self.__buildParticipants()
            self.__projectImportDirs = \
                        GlobalData().project.getImportDirsAsAbsolutePaths()


            QApplication.processEvents()
            if self.__cancelRequest == True:
                QApplication.restoreOverrideCursor()
                self.close()
                return

            self.progressBar.setRange( 0, len( self.__participantFiles ) )
            index = 1

            # Now, parse the files and build the diagram data model
            if self.__what == ImportsDiagramDialog.SingleBuffer:
                info = getBriefModuleInfoFromMemory( str( self.__buf ) )
                self.__addSingleFileToDataModel( info, self.__path )
            else:
                if GlobalData().project.isLoaded():
                    infoSrc = GlobalData().project.briefModinfoCache
                else:
                    infoSrc = GlobalData().briefModinfoCache
                for fName in self.__participantFiles:
                    self.progressBar.setValue( index )
                    self.infoLabel.setText( 'Analyzing ' + fName + "..." )
                    QApplication.processEvents()
                    if self.__cancelRequest == True:
                        QApplication.restoreOverrideCursor()
                        self.dataModel.clear()
                        self.close()
                        return
                    info = infoSrc.get( fName )
                    self.__addSingleFileToDataModel( info, fName )
                    index += 1

            # The import caches and other working data are not needed anymore
            self.__participantFiles = None
            self.__projectImportDirs = None
            self.__projectImportsCache = None


            # Generating the graphviz layout
            self.infoLabel.setText( 'Generating layout using graphviz...' )
            QApplication.processEvents()

            graph = getGraphFromDescriptionData( self.dataModel.toGraphviz() )
            graph.normalize( self.physicalDpiX(), self.physicalDpiY() )
            QApplication.processEvents()
            if self.__cancelRequest == True:
                QApplication.restoreOverrideCursor()
                self.dataModel.clear()
                self.close()
                return

            # Generate graphics scene
            self.infoLabel.setText( 'Generating graphics scene...' )
            QApplication.processEvents()
            self.__buildGraphicsScene( graph )

            # TODO
            # Clear the data model
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            self.__inProgress = False
            self.__onClose()
            return

        QApplication.restoreOverrideCursor()
        self.infoLabel.setText( 'Done' )
        QApplication.processEvents()
        self.__inProgress = False

        self.accept()
        return

    def __buildGraphicsScene( self, graph ):
        " Builds the QT graphics scene "
        self.scene.clear()
        self.scene.setSceneRect( 0, 0, graph.width, graph.height )

        for edge in graph.edges:
            # self.scene.addItem( GraphicsEdge( edge, self ) )
            dataModelObj = self.dataModel.findConnection( edge.tail,
                                                          edge.head )
            if dataModelObj is None:
                raise Exception( "Cannot find the following connection: " + \
                                 edge.tail + " -> " + edge.head )

            if dataModelObj.kind == DgmConnection.ModuleDoc:
                modObj = self.dataModel.findModule( dataModelObj.source )
                if modObj is None:
                    raise Exception( "Cannot find module object: " + \
                                     dataModelObj.source )
                self.scene.addItem( ImportsDgmDocConn( edge, modObj ) )
                continue
            if dataModelObj.kind == DgmConnection.ModuleDependency:
                # Find the source module object first
                modObj = self.dataModel.findModule( dataModelObj.source )
                if modObj is None:
                    raise Exception( "Cannot find module object: " + \
                                     dataModelObj.source )
                self.scene.addItem( \
                        ImportsDgmDependConn( edge, modObj, dataModelObj ) )

                if edge.label != "":
                    self.scene.addItem( ImportsDgmEdgeLabel( edge, modObj ) )
                continue

            raise Exception( "Unexpected type of connection: " + \
                             str( dataModelObj.kind ) )


        for node in graph.nodes:
            dataModelObj = self.dataModel.findModule( node.name )
            if dataModelObj is None:
                dataModelObj = self.dataModel.findDocstring( node.name )
            if dataModelObj is None:
                raise Exception( "Cannot find object " + node.name )

            if isinstance( dataModelObj, DgmDocstring ):
                self.scene.addItem( ImportsDgmDocNote( node, dataModelObj ) )
                continue

            # OK, this is a module rectangle. Switch by type of the module.
            if dataModelObj.kind == DgmModule.ModuleOfInterest:
                self.scene.addItem( \
                        ImportsDgmModuleOfInterest( node, dataModelObj,
                                                    self.physicalDpiX() ) )
                continue

            if dataModelObj.kind == DgmModule.OtherProjectModule:
                self.scene.addItem( \
                        ImportsDgmOtherPrjModule( node, dataModelObj,
                                                  self.physicalDpiX() ) )
                continue

            if dataModelObj.kind == DgmModule.SystemWideModule:
                self.scene.addItem( \
                        ImportsDgmSystemWideModule( node, dataModelObj ) )
                continue

            if dataModelObj.kind == DgmModule.BuiltInModule:
                self.scene.addItem( \
                        ImportsDgmBuiltInModule( node, dataModelObj ) )
                continue

            if dataModelObj.kind == DgmModule.UnknownModule:
                self.scene.addItem( \
                        ImportsDgmUnknownModule( node, dataModelObj ) )
                continue

            raise Exception( "Unexpected type of module: " + \
                             str( dataModelObj.kind ) )

        return

