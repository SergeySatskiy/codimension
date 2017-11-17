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

"""imports diagram dialog"""

import os
import os.path
import logging
from ui.qt import (Qt, QTimer, QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                   QCheckBox, QProgressBar, QApplication, QGraphicsScene,
                   QGraphicsPixmapItem)
from utils.globals import GlobalData
from utils.fileutils import isPythonFile
from utils.importutils import resolveImports
from utils.pixmapcache import getPixmap
from cdmpyparser import getBriefModuleInfoFromMemory
from .plaindotparser import getGraphFromDescriptionData
from .importsdgmgraphics import (ImportsDgmDocConn, ImportsDgmDependConn,
                                 ImportsDgmSystemWideModule,
                                 ImportsDgmUnknownModule,
                                 ImportsDgmBuiltInModule,
                                 ImportsDgmModuleOfInterest,
                                 ImportsDgmOtherPrjModule,
                                 ImportsDgmDocNote, ImportsDgmEdgeLabel)


class DgmConnection:

    """Holds information about one connection"""

    # Connection types
    ModuleDoc = 0
    ModuleDependency = 1

    def __init__(self):
        self.objName = ""       # Unique object name
        self.kind = -1          # See connection types
        self.source = ""        # Connection start point
        self.target = ""        # Connection end point
        self.labels = []        # Connection labels: list of what imported

    def toGraphviz(self):
        """Serialize the connection in graphviz format"""
        attributes = 'id="' + self.objName + '", arrowhead=none'
        label = ""
        for what in self.labels:
            if label != "":
                label += "\\n"
            label += what
        if label != "":
            attributes += ', label="' + label + \
                          '", fontname=Arial, fontsize=10'

        return self.source + " -> " + self.target + '[ ' + attributes + ' ];'

    def __eq__(self, other):
        """Checks if the connection connects the same objects"""
        return self.source == other.source and self.target == other.target


class DgmDocstring:

    """Holds information about one docstring"""

    def __init__(self):
        self.objName = ""       # Unique object name
        self.docstring = None   # Module docstring object

        self.refFile = ""       # File of the docstring

    def toGraphviz(self):
        """Serialize the docstring box in graphviz format"""
        escapedText = self.docstring.text.replace('\n', '\\n')
        escapedText = escapedText.replace('"', '\\"')
        attributes = 'shape=box, fontname=Arial, fontsize=10'
        return self.objName + \
               ' [ ' + attributes + ', label="' + escapedText + '" ];'


class DgmModule:

    """Holds information about one module"""

    # Module types
    ModuleOfInterest = 0
    OtherProjectModule = 1
    SystemWideModule = 2
    BuiltInModule = 3
    UnknownModule = 4

    def __init__(self):
        self.objName = ""       # Unique object name
        self.kind = -1          # See module types
        self.title = ""         # title
        self.classes = []       # list of classes objects
        self.funcs = []         # list of funcs objects
        self.globs = []         # list of global var objects
        self.imports = []       # list of imports

        self.refFile = ""       # File of the module
        self.docstring = ""

    def toGraphviz(self):
        """Serialize the module box in graphviz format"""
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

        spareForTopBottom = "\\n"

        attributes = 'shape=box, fontname=Arial, fontsize=10'

        if self.isProjectModule():
            return self.objName + ' [ ' + attributes + \
                   ', label="' + spareForTopBottom + self.title + '\\n' + \
                   classesPart + '\\n' + funcsPart + '\\n' + globsPart + '" ];'
        return self.objName + ' [ ' + attributes + \
               ', label="' + self.title + '" ];'

    def isProjectModule(self):
        """True if belongs to the project or the dir of interest"""
        return self.kind in [self.ModuleOfInterest, self.OtherProjectModule]

    def __eq__(self, other):
        """Compares two module boxes when they are added to the data model"""
        if self.isProjectModule() and other.isProjectModule():
            return self.refFile == other.refFile
        return self.refFile == other.refFile and \
               self.kind == other.kind and self.title == other.title

    def getTooltip(self):
        """Provides a tooltip"""
        tooltip = ''
        if self.refFile != "":
            tooltip = self.refFile
        if self.docstring != "":
            if tooltip != "":
                tooltip += "\n\n"
            tooltip += self.docstring
        return tooltip


class DgmRank:

    """Holds information about one rank"""

    def __init__(self):
        self.firstObj = ""
        self.secondObj = ""

    def __eq__(self, other):
        """Compares two ranks"""
        return self.firstObj == other.firstObj and \
               self.secondObj == other.secondObj

    def toGraphviz(self):
        """Serialize the rank in graphviz format"""
        return '{ rank=same; "' + self.firstObj + '"; "' + \
               self.secondObj + '"; }'


class ImportDiagramModel:

    """Holds information about data model of an import diagram"""

    def __init__(self):
        self.modules = []
        self.docstrings = []
        self.connections = []
        self.ranks = []

        self.__objectsCounter = -1

    def clear(self):
        """Clears the diagram model"""
        self.modules = []
        self.docstrings = []
        self.connections = []
        self.ranks = []

        self.__objectsCounter = -1

    def toGraphviz(self):
        """Serialize the import diagram in graphviz format"""
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

    def __newName(self):
        """Generates a short name for the graphviz objects"""
        self.__objectsCounter += 1
        return "obj" + str(self.__objectsCounter)

    def addRank(self, rank):
        """Adds a rank"""
        for idx in range(0, len(self.ranks)):
            if self.ranks[idx] == rank:
                return
        self.ranks.append(rank)

    def addConnection(self, conn):
        """Adds a connection and provides its name"""
        # The connections can be added twice if there are two import directives
        index = -1
        for idx in range(0, len(self.connections)):
            if self.connections[idx] == conn:
                index = idx
                break

        if index == -1:
            # new connection, generate name and add
            conn.objName = self.__newName()
            self.connections.append(conn)
            return conn.objName

        # There is already such a connection. So merge labels.
        self.connections[index].labels += conn.labels
        return self.connections[index].objName

    def addDocstringBox(self, docBox):
        """Adds a module docstring"""
        # Docstring boxes cannot appear twice so just add it
        docBox.objName = self.__newName()
        self.docstrings.append(docBox)
        return docBox.objName

    def addModule(self, modBox):
        """Adds a module box"""
        # It might happened that the same module appeared more than once
        index = -1
        for idx in range(0, len(self.modules)):
            if self.modules[idx] == modBox:
                index = idx
                break

        if index == -1:
            # New module box, generate name and add it
            modBox.objName = self.__newName()
            self.modules.append(modBox)
            return modBox.objName

        # There is already such a box, so the box type might need to be
        # adjusted
        if modBox.kind == self.modules[index].kind:
            return self.modules[index].objName

        if modBox.kind == DgmModule.ModuleOfInterest:
            # Replace the existed one with a new one but keep the object name
            modBox.objName = self.modules[index].objName
            self.modules[index] = modBox
            return modBox.objName

        # No need in adjustments
        return self.modules[index].objName

    def findModule(self, name):
        """Searches for a module by the object name"""
        for obj in self.modules:
            if obj.objName == name:
                return obj
        return None

    def findConnection(self, name, tail=""):
        """Searches for a connection by the object name"""
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

    def findDocstring(self, name):
        """Searches for a docstring by the object name"""
        for obj in self.docstrings:
            if obj.objName == name:
                return obj
        return None


class ImportDiagramOptions:

    """Holds the generated diagram settings"""

    def __init__(self):
        self.includeClasses = True
        self.includeFuncs = True
        self.includeGlobs = True
        self.includeDocs = False
        self.includeConnText = True


class ImportsDiagramDialog(QDialog):

    """Imports diagram properties dialog implementation"""

    # Options of providing a diagram
    SingleFile = 0
    DirectoryFiles = 1
    ProjectFiles = 2
    SingleBuffer = 3

    def __init__(self, option, path="", parent=None):
        QDialog.__init__(self, parent)

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
            title += os.path.basename(self.__path)
        elif self.__option == self.DirectoryFiles:
            title += "directory " + self.__path
        elif self.__option == self.ProjectFiles:
            title += "the whole project"
        else:
            title += "modified file " + os.path.basename(self.__path)
        self.setWindowTitle(title)

    def __updateOptions(self, state=None):
        """Updates the saved options"""
        self.options.includeClasses = self.includeClassesBox.isChecked()
        self.options.includeFuncs = self.includeFuncsBox.isChecked()
        self.options.includeGlobs = self.includeGlobsBox.isChecked()
        self.options.includeDocs = self.includeDocsBox.isChecked()
        self.options.includeConnText = self.includeConnTextBox.isChecked()

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(400, 100)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)

        # Check boxes
        self.includeClassesBox = QCheckBox(self)
        self.includeClassesBox.setText("Show &classes in modules")
        self.includeClassesBox.setChecked(self.options.includeClasses)
        self.includeClassesBox.stateChanged.connect(self.__updateOptions)
        self.includeFuncsBox = QCheckBox(self)
        self.includeFuncsBox.setText("Show &functions in modules")
        self.includeFuncsBox.setChecked(self.options.includeFuncs)
        self.includeFuncsBox.stateChanged.connect(self.__updateOptions)
        self.includeGlobsBox = QCheckBox(self)
        self.includeGlobsBox.setText("Show &global variables in modules")
        self.includeGlobsBox.setChecked(self.options.includeGlobs)
        self.includeGlobsBox.stateChanged.connect(self.__updateOptions)
        self.includeDocsBox = QCheckBox(self)
        self.includeDocsBox.setText("Show modules &docstrings")
        self.includeDocsBox.setChecked(self.options.includeDocs)
        self.includeDocsBox.stateChanged.connect(self.__updateOptions)
        self.includeConnTextBox = QCheckBox(self)
        self.includeConnTextBox.setText("Show connection &labels")
        self.includeConnTextBox.setChecked(self.options.includeConnText)
        self.includeConnTextBox.stateChanged.connect(self.__updateOptions)

        verticalLayout.addWidget(self.includeClassesBox)
        verticalLayout.addWidget(self.includeFuncsBox)
        verticalLayout.addWidget(self.includeGlobsBox)
        verticalLayout.addWidget(self.includeDocsBox)
        verticalLayout.addWidget(self.includeConnTextBox)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        generateButton = buttonBox.addButton("Generate",
                                             QDialogButtonBox.ActionRole)
        generateButton.setDefault(True)
        generateButton.clicked.connect(self.accept)
        verticalLayout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.close)


class ImportsDiagramProgress(QDialog):

    """Progress of the diagram generator"""

    def __init__(self, what, options, path="", buf="", parent=None):
        QDialog.__init__(self, parent)
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
        self.setWindowTitle('Imports/dependencies diagram generator')
        QTimer.singleShot(0, self.__process)

    def keyPressEvent(self, event):
        """Processes the ESC key specifically"""
        if event.key() == Qt.Key_Escape:
            self.__onClose()
        else:
            QDialog.keyPressEvent(self, event)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(450, 20)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)

        # Info label
        self.infoLabel = QLabel(self)
        verticalLayout.addWidget(self.infoLabel)

        # Progress bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        self.progressBar.setOrientation(Qt.Horizontal)
        verticalLayout.addWidget(self.progressBar)

        # Buttons
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Close)
        verticalLayout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.__onClose)

    def __onClose(self):
        """triggered when the close button is clicked"""
        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()

    def __buildParticipants(self):
        """Builds a list of participating files and dirs"""
        if self.__what in [ImportsDiagramDialog.SingleBuffer,
                           ImportsDiagramDialog.SingleFile]:
            # File exists but could be modified
            self.__path = os.path.realpath(self.__path)
            self.__participantFiles.append(self.__path)
            return

        if self.__what == ImportsDiagramDialog.ProjectFiles:
            self.__scanProjectDirs()
            return

        # This is a recursive directory
        self.__path = os.path.realpath(self.__path)
        self.__scanDirForPythonFiles(self.__path + os.path.sep)

    def __scanDirForPythonFiles(self, path):
        """Scans the directory for the python files recursively"""
        for item in os.listdir(path):
            if item in [".svn", ".cvs", '.git', '.hg']:
                continue
            if os.path.isdir(path + item):
                self.__scanDirForPythonFiles(path + item + os.path.sep)
                continue
            if isPythonFile(path + item):
                self.__participantFiles.append(os.path.realpath(path + item))

    def __scanProjectDirs(self):
        """Populates participant lists from the project files"""
        for fName in GlobalData().project.filesList:
            if isPythonFile(fName):
                self.__participantFiles.append(fName)

    def __addBoxInfo(self, box, info):
        """Adds information to the given box if so configured"""
        if info.docstring is not None:
            box.docstring = info.docstring.text

        if self.__options.includeClasses:
            for klass in info.classes:
                box.classes.append(klass)

        if self.__options.includeFuncs:
            for func in info.functions:
                box.funcs.append(func)

        if self.__options.includeGlobs:
            for glob in info.globals:
                box.globs.append(glob)

        if self.__options.includeConnText:
            for imp in info.imports:
                box.imports.append(imp)

    def __addDocstringBox(self, info, fName, modBoxName):
        """Adds a docstring box if needed"""
        if self.__options.includeDocs:
            if info.docstring is not None:
                docBox = DgmDocstring()
                docBox.docstring = info.docstring
                docBox.refFile = fName

                # Add the box and its connection
                docBoxName = self.dataModel.addDocstringBox(docBox)

                conn = DgmConnection()
                conn.kind = DgmConnection.ModuleDoc
                conn.source = modBoxName
                conn.target = docBoxName
                self.dataModel.addConnection(conn)

                # Add rank for better layout
                rank = DgmRank()
                rank.firstObj = modBoxName
                rank.secondObj = docBoxName
                self.dataModel.addRank(rank)

    def __getSytemWideImportDocstring(self, path):
        """Provides the system wide module docstring"""
        if isPythonFile(path):
            try:
                info = GlobalData().briefModinfoCache.get(path)
                if info.docstring is not None:
                    return info.docstring.text
            except:
                pass
        return ''

    @staticmethod
    def __getModuleTitle(fName):
        """Extracts a module name out of the file name"""
        baseTitle = os.path.basename(fName).split('.')[0]
        if baseTitle != "__init__":
            return baseTitle

        # __init__ is not very descriptive. Add a top level dir.
        dirName = os.path.dirname(fName)
        topDir = os.path.basename(dirName)
        return topDir + "(" + baseTitle + ")"

    @staticmethod
    def __isLocalOrProject(fName, resolvedPath):
        """True if the module is a project one or is in the nested dirs"""
        if resolvedPath is None:
            return False
        if not os.path.isabs(resolvedPath):
            return False
        if GlobalData().project.isProjectFile(resolvedPath):
            return True

        resolvedDir = os.path.dirname(resolvedPath)
        baseDir = os.path.dirname(fName)
        return resolvedDir.startswith(baseDir)

    def __addSingleFileToDataModel(self, info, fName):
        """Adds a single file to the data model"""
        if fName.endswith('__init__.py'):
            if not info.classes and not info.functions and \
               not info.globals and not info.imports:
                # Skip dummy init files
                return

        modBox = DgmModule()
        modBox.refFile = fName

        modBox.kind = DgmModule.ModuleOfInterest
        modBox.title = self.__getModuleTitle(fName)

        self.__addBoxInfo(modBox, info)
        modBoxName = self.dataModel.addModule(modBox)
        self.__addDocstringBox(info, fName, modBoxName)

        # Analyze what was imported
        resolvedImports, errors = resolveImports(fName, info.imports)
        if errors:
            message = 'Errors while analyzing ' + fName + ':'
            for err in errors:
                message += '\n    ' + err
            logging.warning(message)

        for item in resolvedImports:
            importName = item[0]        # from name
            resolvedPath = item[1]      # 'built-in', None or absolute path
            importedNames = item[2]     # list of strings

            impBox = DgmModule()
            impBox.title = importName

            if self.__isLocalOrProject(fName, resolvedPath):
                impBox.kind = DgmModule.OtherProjectModule
                impBox.refFile = resolvedPath
                if isPythonFile(resolvedPath):
                    otherInfo = GlobalData().briefModinfoCache.get(
                        resolvedPath)
                    self.__addBoxInfo(impBox, otherInfo)
            else:
                if resolvedPath is None:
                    # e.g. 'import sys' will have None for the path
                    impBox.kind = DgmModule.UnknownModule
                elif os.path.isabs(resolvedPath):
                    impBox.kind = DgmModule.SystemWideModule
                    impBox.refFile = resolvedPath
                    impBox.docstring = \
                        self.__getSytemWideImportDocstring(resolvedPath)
                else:
                    # e.g. 'import time' will have 'built-in' in the path
                    impBox.kind = DgmModule.BuiltInModule

            impBoxName = self.dataModel.addModule(impBox)

            impConn = DgmConnection()
            impConn.kind = DgmConnection.ModuleDependency
            impConn.source = modBoxName
            impConn.target = impBoxName

            if self.__options.includeConnText:
                for impWhat in importedNames:
                    if impWhat:
                        impConn.labels.append(impWhat)
            self.dataModel.addConnection(impConn)

    def __process(self):
        """Accumulation process"""
        # Intermediate working data
        self.__participantFiles = []
        self.__projectImportDirs = []
        self.__projectImportsCache = {}

        self.dataModel.clear()
        self.__inProgress = True

        try:
            self.infoLabel.setText('Building the list of files to analyze...')
            QApplication.processEvents()

            # Build the list of participating python files
            self.__buildParticipants()
            self.__projectImportDirs = \
                GlobalData().project.getImportDirsAsAbsolutePaths()


            QApplication.processEvents()
            if self.__cancelRequest:
                QApplication.restoreOverrideCursor()
                self.close()
                return

            self.progressBar.setRange(0, len(self.__participantFiles))
            index = 1

            # Now, parse the files and build the diagram data model
            if self.__what == ImportsDiagramDialog.SingleBuffer:
                info = getBriefModuleInfoFromMemory(str(self.__buf))
                self.__addSingleFileToDataModel(info, self.__path)
            else:
                infoSrc = GlobalData().briefModinfoCache
                for fName in self.__participantFiles:
                    self.progressBar.setValue(index)
                    self.infoLabel.setText('Analyzing ' + fName + "...")
                    QApplication.processEvents()
                    if self.__cancelRequest:
                        QApplication.restoreOverrideCursor()
                        self.dataModel.clear()
                        self.close()
                        return
                    info = infoSrc.get(fName)
                    self.__addSingleFileToDataModel(info, fName)
                    index += 1

            # The import caches and other working data are not needed anymore
            self.__participantFiles = None
            self.__projectImportDirs = None
            self.__projectImportsCache = None

            # Generating the graphviz layout
            self.infoLabel.setText('Generating layout using graphviz...')
            QApplication.processEvents()

            graph = getGraphFromDescriptionData(self.dataModel.toGraphviz())
            graph.normalize(self.physicalDpiX(), self.physicalDpiY())
            QApplication.processEvents()
            if self.__cancelRequest:
                QApplication.restoreOverrideCursor()
                self.dataModel.clear()
                self.close()
                return

            # Generate graphics scene
            self.infoLabel.setText('Generating graphics scene...')
            QApplication.processEvents()
            self.__buildGraphicsScene(graph)

            # Clear the data model
            self.dataModel = None
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            logging.error(str(exc))
            self.__inProgress = False
            self.__onClose()
            return

        QApplication.restoreOverrideCursor()
        self.infoLabel.setText('Done')
        QApplication.processEvents()
        self.__inProgress = False

        self.accept()

    def __buildGraphicsScene(self, graph):
        """Builds the QT graphics scene"""
        self.scene.clear()
        self.scene.setSceneRect(0, 0, graph.width, graph.height)

        for edge in graph.edges:
            # self.scene.addItem( GraphicsEdge( edge, self ) )
            dataModelObj = self.dataModel.findConnection(edge.tail, edge.head)
            if dataModelObj is None:
                raise Exception("Cannot find the following connection: " +
                                edge.tail + " -> " + edge.head)

            if dataModelObj.kind == DgmConnection.ModuleDoc:
                modObj = self.dataModel.findModule(dataModelObj.source)
                if modObj is None:
                    raise Exception("Cannot find module object: " +
                                    dataModelObj.source)
                self.scene.addItem(ImportsDgmDocConn(edge, modObj))
                continue
            if dataModelObj.kind == DgmConnection.ModuleDependency:
                # Find the source module object first
                modObj = self.dataModel.findModule(dataModelObj.source)
                if modObj is None:
                    raise Exception("Cannot find module object: " +
                                    dataModelObj.source)
                self.scene.addItem(
                    ImportsDgmDependConn(edge, modObj, dataModelObj))

                if edge.label != "":
                    self.scene.addItem(ImportsDgmEdgeLabel(edge, modObj))
                continue

            raise Exception("Unexpected type of connection: " +
                            str(dataModelObj.kind))

        for node in graph.nodes:
            dataModelObj = self.dataModel.findModule(node.name)
            if dataModelObj is None:
                dataModelObj = self.dataModel.findDocstring(node.name)
            if dataModelObj is None:
                raise Exception("Cannot find object " + node.name)

            if isinstance(dataModelObj, DgmDocstring):
                self.scene.addItem(ImportsDgmDocNote(node,
                                                     dataModelObj.refFile,
                                                     dataModelObj.docstring))
                continue

            # OK, this is a module rectangle. Switch by type of the module.
            if dataModelObj.kind == DgmModule.ModuleOfInterest:
                self.scene.addItem(
                    ImportsDgmModuleOfInterest(node, dataModelObj.refFile,
                                               dataModelObj,
                                               self.physicalDpiX()))
            elif dataModelObj.kind == DgmModule.OtherProjectModule:
                self.scene.addItem(
                    ImportsDgmOtherPrjModule(node, dataModelObj.refFile,
                                             dataModelObj,
                                             self.physicalDpiX()))
            elif dataModelObj.kind == DgmModule.SystemWideModule:
                self.scene.addItem(
                    ImportsDgmSystemWideModule(node,
                                               dataModelObj.refFile,
                                               dataModelObj.docstring))
            elif dataModelObj.kind == DgmModule.BuiltInModule:
                self.scene.addItem(ImportsDgmBuiltInModule(node))
            elif dataModelObj.kind == DgmModule.UnknownModule:
                self.scene.addItem(ImportsDgmUnknownModule(node))
            else:
                raise Exception("Unexpected type of module: " +
                                str(dataModelObj.kind))

            tooltip = dataModelObj.getTooltip()
            if tooltip:
                pixmap = getPixmap('diagramdoc.png')
                docItem = QGraphicsPixmapItem(pixmap)
                docItem.setToolTip(tooltip)
                posX = node.posX + node.width / 2.0 - pixmap.width() / 2.0
                posY = node.posY - node.height / 2.0 - pixmap.height() / 2.0
                docItem.setPos(posX, posY)
                self.scene.addItem(docItem)
