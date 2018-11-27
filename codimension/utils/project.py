# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""codimension project"""

import logging
import uuid
import re
import copy
import json
import shutil
import os
from os.path import (realpath, islink, isdir, sep, exists, dirname, isabs,
                     join, relpath, isfile)
from ui.qt import QObject, pyqtSignal
from .settings import Settings, SETTINGS_DIR
from .watcher import Watcher
from .config import DEFAULT_ENCODING
from .debugenv import DebuggerEnvironment
from .searchenv import SearchEnvironment
from .fsenv import FileSystemEnvironment
from .runparamscache import RunParametersCache
from .filepositions import FilePositions
from .userencodings import FileEncodings
from .flowgroups import FlowUICollapsedGroups


# Saved in .cdm3 file
_DEFAULT_PROJECT_PROPS = {'scriptname': '',    # Script to run the project
                          'mddocfile': '',
                          'creationdate': '',
                          'author': '',
                          'license': '',
                          'copyright': '',
                          'version': '',
                          'email': '',
                          'description': '',
                          'uuid': '',
                          'importdirs': [],
                          'encoding': '',
                          'mddocfile': ''}


class CodimensionProject(QObject,
                         DebuggerEnvironment,
                         SearchEnvironment,
                         FileSystemEnvironment,
                         RunParametersCache,
                         FilePositions,
                         FileEncodings,
                         FlowUICollapsedGroups):

    """Provides codimension project singleton facility"""

    # Constants for the sigProjectChanged signal
    CompleteProject = 0     # It is a completely new project
    Properties = 1          # Project properties were updated

    sigProjectChanged = pyqtSignal(int)
    sigFSChanged = pyqtSignal(list)
    sigRestoreProjectExpandedDirs = pyqtSignal()
    sigProjectAboutToUnload = pyqtSignal()
    sigRecentFilesChanged = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        DebuggerEnvironment.__init__(self)
        SearchEnvironment.__init__(self)
        FileSystemEnvironment.__init__(self)
        RunParametersCache.__init__(self)
        FilePositions.__init__(self)
        FileEncodings.__init__(self)
        FlowUICollapsedGroups.__init__(self)

        self.__dirWatcher = None

        # Avoid pylint complains
        self.fileName = ""
        self.userProjectDir = ""    # Directory in ~/.codimension3/uuidNN/
        self.filesList = set()

        self.props = copy.deepcopy(_DEFAULT_PROJECT_PROPS)

        # Precompile the exclude filters for the project files list
        self.__excludeFilter = []
        for flt in Settings()['projectFilesFilters']:
            self.__excludeFilter.append(re.compile(flt))

    def shouldExclude(self, name):
        """Tests if a file must be excluded"""
        for excl in self.__excludeFilter:
            if excl.match(name):
                return True
        return False

    def __resetValues(self):
        """Initializes or resets all the project members"""
        # Empty file name means that the project has not been loaded or
        # created. This must be an absolute path.
        self.fileName = ""
        self.userProjectDir = ""

        # Generated having the project dir Full paths are stored.
        # The set holds all files and directories.
        # The dirs end with os.path.sep
        self.filesList = set()

        self.props = copy.deepcopy(_DEFAULT_PROJECT_PROPS)

        RunParametersCache.reset(self)
        DebuggerEnvironment.reset(self)
        SearchEnvironment.reset(self)
        FileSystemEnvironment.reset(self)
        FilePositions.reset(self)
        FileEncodings.reset(self)
        FlowUICollapsedGroups.reset(self)

        # Reset the dir watchers if so
        if self.__dirWatcher is not None:
            del self.__dirWatcher
            self.__dirWatcher = None

    def createNew(self, fileName, props):
        """Creates a new project"""
        # Try to create the user project directory
        projectUuid = str(uuid.uuid1())
        userProjectDir = SETTINGS_DIR + projectUuid + sep
        if not exists(userProjectDir):
            try:
                os.makedirs(userProjectDir)
            except Exception:
                logging.error('Cannot create user project directory: ' +
                              self.userProjectDir + '. Please check the '
                              'available disk space, permissions and '
                              're-create the project.')
                raise
        else:
            logging.warning('The user project directory exists! '
                            'The content will be overwritten.')
            self.__removeProjectFiles(userProjectDir)

        # Basic pre-requisites are met. We can reset the current project.
        self.__resetValues()

        self.fileName = fileName
        props['uuid'] = projectUuid
        self.props = props
        self.userProjectDir = userProjectDir

        self.__createProjectFile()  # ~/.codimension3/uuidNN/project

        RunParametersCache.setup(self, self.userProjectDir)
        DebuggerEnvironment.setup(self, self.userProjectDir)
        SearchEnvironment.setup(self, self.userProjectDir)
        FileSystemEnvironment.setup(self, self.userProjectDir)
        FilePositions.setup(self, self.userProjectDir)
        FileEncodings.setup(self, self.userProjectDir)
        FlowUICollapsedGroups.setup(self, self.userProjectDir)

        self.__generateFilesList()

        self.saveProject()

        # Update the watcher
        self.__dirWatcher = Watcher(Settings()['projectFilesFilters'],
                                    self.getProjectDir())
        self.__dirWatcher.sigFSChanged.connect(self.onFSChanged)

        self.sigProjectChanged.emit(self.CompleteProject)

    def __removeProjectFiles(self, userProjectDir):
        """Removes user project files"""
        for root, dirs, files in os.walk(userProjectDir):
            for f in files:
                try:
                    os.unlink(join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    shutil.rmtree(join(root, d))
                except Exception:
                    pass

    def __createProjectFile(self):
        """Helper function to create the user project file"""
        try:
            with open(self.userProjectDir + 'project', 'w',
                      encoding=DEFAULT_ENCODING) as diskfile:
                diskfile.write(self.fileName)
        except Exception as exc:
            logging.error('Could not create the ' + self.userProjectDir +
                          'project file: ' + str(exc))

    def saveProject(self):
        """Writes all the settings into the file"""
        if not self.isLoaded():
            return

        # It could be another user project file without write permissions
        skipProjectFile = False
        if exists(self.fileName):
            if not os.access(self.fileName, os.W_OK):
                skipProjectFile = True
        else:
            if not os.access(dirname(self.fileName), os.W_OK):
                skipProjectFile = True

        if not skipProjectFile:
            with open(self.fileName, 'w',
                      encoding=DEFAULT_ENCODING) as diskfile:
                json.dump(self.props, diskfile, indent=4)
        else:
            logging.warning('Skipping updates in ' + self.fileName +
                            ' due to writing permissions')

    def loadProject(self, projectFile):
        """Loads a project from the given file"""
        path = realpath(projectFile)
        if not exists(path):
            raise Exception('Cannot open project file ' + projectFile)
        if not path.endswith('.cdm3'):
            raise Exception('Unexpected project file extension. '
                            'Expected: .cdm3')

        try:
            with open(path, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                props = json.load(diskfile)
        except:
            # Bad error - cannot load project file at all
            raise Exception('Bad project file ' + projectFile)

        self.__resetValues()
        self.fileName = path
        self.props = props

        # Make sure the old projects have the new fields as well
        for key, value in _DEFAULT_PROJECT_PROPS.items():
            if key not in self.props:
                self.props[key] = value

        if self.props['uuid'] == '':
            logging.warning('Project file does not have UUID. '
                            'Re-generate it...')
            self.props['uuid'] = str(uuid.uuid1())
        self.userProjectDir = SETTINGS_DIR + self.props['uuid'] + sep
        if not exists(self.userProjectDir):
            os.makedirs(self.userProjectDir)

        # Read the other config files
        DebuggerEnvironment.setup(self, self.userProjectDir)
        SearchEnvironment.setup(self, self.userProjectDir)
        FileSystemEnvironment.setup(self, self.userProjectDir)
        RunParametersCache.setup(self, self.userProjectDir)
        FilePositions.setup(self, self.userProjectDir)
        FileEncodings.setup(self, self.userProjectDir)
        FlowUICollapsedGroups.setup(self, self.userProjectDir)

        # The project might have been moved...
        self.__createProjectFile()  # ~/.codimension3/uuidNN/project
        self.__generateFilesList()

        # Update the recent list
        Settings().addRecentProject(self.fileName)

        # Setup the new watcher
        self.__dirWatcher = Watcher(Settings()['projectFilesFilters'],
                                    self.getProjectDir())
        self.__dirWatcher.sigFSChanged.connect(self.onFSChanged)

        self.sigProjectChanged.emit(self.CompleteProject)
        self.sigRestoreProjectExpandedDirs.emit()

    def getImportDirsAsAbsolutePaths(self):
        """Provides a list of import dirs as absolute paths"""
        result = []
        for path in self.props['importdirs']:
            if isabs(path):
                result.append(path)
            else:
                result.append(self.getProjectDir() + path)
        return result

    def onFSChanged(self, items):
        """Triggered when the watcher detects changes"""
        for item in items:
            try:
                if item.startswith('+'):
                    self.filesList.add(item[1:])
                else:
                    self.filesList.remove(item[1:])
            except:
                pass
        self.sigFSChanged.emit(items)

    def unloadProject(self, emitSignal=True):
        """Unloads the current project if required"""
        self.sigProjectAboutToUnload.emit()
        self.__resetValues()
        if emitSignal:
            # No need to send a signal e.g. if IDE is closing
            self.sigProjectChanged.emit(self.CompleteProject)

    def setImportDirs(self, paths):
        """Sets a new set of the project import dirs"""
        if self.props['importdirs'] != paths:
            self.props['importdirs'] = paths
            self.saveProject()
            self.sigProjectChanged.emit(self.Properties)

    def __generateFilesList(self):
        """Generates the files list having the list of dirs"""
        self.filesList = set()
        path = self.getProjectDir()
        self.filesList.add(path)
        self.__scanDir(path)

    def __scanDir(self, path):
        """Recursive function to scan one dir"""
        # The path is with '/' at the end
        for item in os.listdir(path):
            if self.shouldExclude(item):
                continue

            # Exclude symlinks if they point to the other project
            # covered pieces
            candidate = path + item
            if islink(candidate):
                realItem = realpath(candidate)
                if isdir(realItem):
                    if self.isProjectDir(realItem):
                        continue
                else:
                    if self.isProjectDir(dirname(realItem)):
                        continue

            if isdir(candidate):
                self.filesList.add(candidate + sep)
                self.__scanDir(candidate + sep)
                continue
            self.filesList.add(candidate)

    def isProjectDir(self, path):
        """Returns True if the path belongs to the project"""
        if not self.isLoaded():
            return False
        path = realpath(path)     # it could be a symlink
        if not path.endswith(sep):
            path += sep
        return path.startswith(self.getProjectDir())

    def isProjectFile(self, path):
        """Returns True if the path belongs to the project"""
        if not self.isLoaded():
            return False
        return self.isProjectDir(dirname(path))

    def isTopLevelDir(self, path):
        """Checks if the path is a top level dir"""
        if not path.endswith(sep):
            path += sep
        return path in self.topLevelDirs

    def updateProperties(self, props):
        """Updates the project properties"""
        if self.props != props:
            self.props = props
            self.saveProject()
            self.sigProjectChanged.emit(self.Properties)

    def onProjectFileUpdated(self):
        """Called when a project file is updated via direct editing"""
        self.props = getProjectProperties(self.fileName)

        # no need to save, but signal just in case
        self.sigProjectChanged.emit(self.Properties)

    def isLoaded(self):
        """Returns True if a project is loaded"""
        return self.fileName != ''

    def getProjectDir(self):
        """Provides an absolute path to the project dir"""
        if not self.isLoaded():
            return None
        return dirname(realpath(self.fileName)) + sep

    def getProjectScript(self):
        """Provides the project script file name"""
        if not self.isLoaded():
            return None
        if self.props['scriptname'] == '':
            return None
        if isabs(self.props['scriptname']):
            return self.props['scriptname']
        return realpath(self.getProjectDir() + self.props['scriptname'])

    def addRecentFile(self, path):
        """Adds a recent file. True if a new file was inserted."""
        ret = FileSystemEnvironment.addRecentFile(self, path)
        if ret:
            self.sigRecentFilesChanged.emit()
        return ret

    def getRelativePath(self, path):
        """Provides a relative path if so"""
        if self.isProjectFile(path):
            return relpath(path, dirname(self.fileName))
        return path

    def getAbsolutePath(self, path):
        """Provides an absolute path if so"""
        if isabs(path):
            return path
        if self.isLoaded():
            return join(dirname(self.fileName), path)
        return path

    def getStartupMarkdownFile(self):
        """Provides the startup documentation markdown file if so"""
        if not self.isLoaded():
            return None
        # Could be in project properties
        if not self.props['mddocfile']:
            return None
        if isabs(self.props['mddocfile']):
            return self.props['mddocfile']
        return realpath(self.getProjectDir() + self.props['mddocfile'])

    def findStartupMarkdownFile(self):
        """Finds the startup MD doc file"""
        if not self.isLoaded():
            return None, None
        fName = self.getStartupMarkdownFile()
        if fName:
            if not isabs(fName):
                fName = self.getAbsolutePath(fName)
            if not exists(fName):
                return None, 'Configured markdown doc file ' + \
                       self.getStartupMarkdownFile() + ' is not found'
            return fName, None

        # check the file system
        projectDir = self.getProjectDir()
        for item in os.listdir(projectDir):
            if isfile(projectDir + item):
                lowerName = item.lower()
                if lowerName.endswith('.md') and lowerName.startswith('readme'):
                    return projectDir + item, None
        return None, None

    def suggestStartupMarkdownFile(self):
        """Suggests the default project doc file name"""
        if not self.isLoaded():
            raise Exception('Invalid logic. A markdown project doc file name '
                            'is requested without a loaded project')
        return self.getProjectDir() + 'README.md'



def getProjectProperties(projectFile):
    """Provides project properties or throws an exception"""
    path = realpath(projectFile)
    if not exists(path):
        raise Exception("Cannot find project file " + projectFile)

    try:
        with open(path, 'r', encoding=DEFAULT_ENCODING) as diskfile:
            return json.load(diskfile)
    except Exception as exc:
        logging.error('Error reading project file ' + projectFile +
                      ': ' + str(exc))
        return {}


def getProjectFileTooltip(fileName):
    """Provides a project file tooltip"""
    props = getProjectProperties(fileName)
    return '\n'.join(['Version: ' + props.get('version', 'n/a'),
                      'Description: ' + props.get('description', 'n/a'),
                      'Author: ' + props.get('author', 'n/a'),
                      'e-mail: ' + props.get('email', 'n/a'),
                      'Copyright: ' + props.get('copyright', 'n/a'),
                      'License: ' + props.get('license', 'n/a'),
                      'Creation date: ' + props.get('creationdate', 'n/a'),
                      'Default encoding: ' + props.get('encoding', 'n/a'),
                      'UUID: ' + props.get('uuid', 'n/a')])
