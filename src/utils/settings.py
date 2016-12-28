#
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


"""codimension settings"""

import os
import os.path
import sys
import datetime
import json
import logging
from copy import deepcopy
from PyQt5.QtCore import QObject, QDir, pyqtSignal
from .run import TERM_REDIRECT
from .config import SETTINGS_ENCODING, CONFIG_DIR
from .runparamscache import RunParametersCache
from .debugenv import DebuggerEnvironment
from .searchenv import SearchEnvironment
from .fsenv import FileSystemEnvironment
from .filepositions import FilePositions


SETTINGS_DIR = os.path.join(os.path.realpath(QDir.homePath()),
                            CONFIG_DIR) + os.path.sep
THIRDPARTY_DIR = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),
                              'thirdparty') + os.path.sep


class ProfilerSettings:
    """Holds IDE-wide profiler options"""
    def __init__(self):
        self.nodeLimit = 1.0
        self.edgeLimit = 1.0

    def toJSON(self):
        """Converts the instance to a serializable structure"""
        return {'__class__': 'ProfilerSettings',
                '__values__': {'nodeLimit': self.nodeLimit,
                               'edgeLimit': self.edgeLimit}}

    def fromJSON(self, jsonObj):
        """Populates the values from the json object"""
        self.nodeLimit = jsonObj['__values__']['nodeLimit']
        self.edgeLimit = jsonObj['__values__']['edgeLimit']

    def __eq__(self, other):
        return self.nodeLimit == other.nodeLimit and \
               self.edgeLimit == other.edgeLimit


class DebuggerSettings:
    """Holds IDE-wide debugger options"""
    def __init__(self):
        self.reportExceptions = True
        self.traceInterpreter = True
        self.stopAtFirstLine = True
        self.autofork = False
        self.followChild = False

    def toJSON(self):
        """Converts the instance to a serializable structure"""
        return {'__class__': 'DebuggerSettings',
                '__values__': {'reportExceptions': self.reportExceptions,
                               'traceInterpreter': self.traceInterpreter,
                               'stopAtFirstLine': self.stopAtFirstLine,
                               'autofork': self.autofork,
                               'followChild': self.followChild}}

    def fromJSON(self, jsonObj):
        """Populates the values from the json object"""
        self.reportExceptions = jsonObj['__values__']['reportExceptions']
        self.traceInterpreter = jsonObj['__values__']['traceInterpreter']
        self.stopAtFirstLine = jsonObj['__values__']['stopAtFirstLine']
        self.autofork = jsonObj['__values__']['autofork']
        self.followChild = jsonObj['__values__']['followChild']

    def __eq__(self, other):
        return self.reportExceptions == other.reportExceptions and \
               self.traceInterpreter == other.traceInterpreter and \
               self.stopAtFirstLine == other.stopAtFirstLine and \
               self.autofork == other.autofork and \
               self.followChild == other.followChild


__DEFAULT_SETTINGS = {
    # general
    'zoom': 0,
    'xpos': 50,
    'ypos': 50,
    'width': 750,
    'height': 550,
    'screenwidth': 0,
    'screenheight': 0,
    'xdelta': 0,
    'ydelta': 0,
    'skin': 'default',
    'modifiedFormat': '%s *',
    'verticalEdge': True,
    'showSpaces': True,
    'lineWrap': False,
    'showEOL': False,
    'showBraceMatch': True,
    'autoIndent': True,
    'backspaceUnindent': True,
    'tabIndents': True,
    'indentationGuides': False,
    'currentLineVisible': True,
    'jumpToFirstNonSpace': False,
    'removeTrailingOnSave': False,
    'showFSViewer': True,
    'showStackViewer': True,
    'showThreadViewer': True,
    'showIgnoredExcViewer': True,
    'showWatchPointViewer': True,
    'showNavigationBar': True,
    'showCFNavigationBar': True,
    'showMainToolBar': True,
    'terminalType': TERM_REDIRECT,
    'profilerLimits': ProfilerSettings(),
    'debuggerSettings': DebuggerSettings(),
    'debugHideMCF': True,
    'debugGLFilter': 0,
    'editorEdge': 80,
    'projectTooltips': True,
    'recentTooltips': True,
    'classesTooltips': True,
    'functionsTooltips': True,
    'outlineTooltips': True,
    'findNameTooltips': True,
    'findFileTooltips': True,
    'editorTooltips': True,
    'editorCalltips': True,
    'leftBarMinimized': False,
    'bottomBarMinimized': False,
    'rightBarMinimized': False,
    'projectLoaded': False,
    'clearDebugIO': False,
    'hSplitterSizes': [200, 450, 575],
    'vSplitterSizes': [400, 150],
    'flowSplitterSizes': [225, 225],
    'style': 'plastique',
    'vcsstatusupdateinterval': 30,      # seconds
    'tablistsortalpha': True,
    'taborderpreserved': False,
    'flowScale': 1.0,
    'maxRecentProjects': 32,
    'maxRecentFiles': 32,
    'maxSearchEntries': 32,

    # The IO redirect console
    'ioconsolemaxmsgs': 10000,
    'ioconsoledelchunk': 512,
    'ioconsolelinewrap': False,
    'ioconsoleshoweol': False,
    'ioconsoleshowspaces': True,
    'ioconsoleautoscroll': True,
    'ioconsoleshowmargin': True,
    'ioconsoleshowstdin': True,
    'ioconsoleshowstdout': True,
    'ioconsoleshowstderr': True,
    'navbarglobalsimports': False,

    'recentProjects': [],
    'projectFilesFilters': ['^\\.', '.*\\~$', '.*\\.pyc$',
                            '.*\\.swp$', '.*\\.pyo$'],
    'ignoredExceptions': [],
    'disabledPlugins': [],
    'dirSafeModules': ['os', 'sys', 'xml', 'collections',
                       'numpy', 'scipy', 'unittest'],
    'vcsindicators': [[-1, 'vcsunversioned.png', None,
                       '220,220,255,255', 'Not under VCS control'],
                      [-2, 'vcsstatuserror.png', None,
                       '255,160,160,255', 'Error getting status']]}


def settingsFromJSON(jsonObj):
    """Custom deserialization"""
    if '__class__' in jsonObj:
        if jsonObj['__class__'] == 'ProfilerSettings':
            pSettings = ProfilerSettings()
            pSettings.fromJSON(jsonObj)
            return pSettings
        if jsonObj['__class__'] == 'DebuggerSettings':
            dSettings = DebuggerSettings()
            dSettings.fromJSON(jsonObj)
            return dSettings
    return jsonObj


def settingsToJSON(pythonObj):
    """Custom serialization"""
    if isinstance(pythonObj, ProfilerSettings):
        return pythonObj.toJSON()
    if isinstance(pythonObj, DebuggerSettings):
        return pythonObj.toJSON()
    raise TypeError(repr(pythonObj) + ' is not JSON serializable')


class SettingsWrapper(QObject,
                      DebuggerEnvironment,
                      SearchEnvironment,
                      FileSystemEnvironment,
                      RunParametersCache,
                      FilePositions):
    """Provides settings singleton facility"""

    recentListChanged = pyqtSignal()
    flowSplitterChanged = pyqtSignal()
    flowScaleChanged = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        DebuggerEnvironment.__init__(self)
        SearchEnvironment.__init__(self)
        FileSystemEnvironment.__init__(self)
        RunParametersCache.__init__(self)
        FilePositions.__init__(self)

        self.__values = deepcopy(__DEFAULT_SETTINGS)

        # make sure that the directory exists
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)

        RunParametersCache.setup(self, SETTINGS_DIR)
        DebuggerEnvironment.setup(self, SETTINGS_DIR)
        SearchEnvironment.setup(self, SETTINGS_DIR)
        FileSystemEnvironment.setup(self, SETTINGS_DIR)
        FilePositions.setup(self, SETTINGS_DIR)

        # Save the config file name
        self.__fullFileName = SETTINGS_DIR + "settings.json"

        # Create file if does not exist
        if not os.path.exists(self.__fullFileName):
            # Save to file
            self.flush()
            return

        readErrors = []

        # Load the previous session settings
        try:
            with open(self.fullFileName, "r",
                      encoding=SETTINGS_ENCODING) as diskfile:
                diskValues = json.load(diskfile, object_hook=settingsFromJSON)
        except Exception as exc:
            # Bad error - save default
            self.__saveErrors('Could not read setting from ' +
                              self.fullFileName + ': ' + str(exc) +
                              'Overwriting with the default settings...')
            self.flush()
            return

        for item, val in diskValues.items():
            if item in self.values:
                if type(self.values[item]) != type(val):
                    readErrors.append("Settings '" + item +
                                      "' type from the disk file " +
                                      self.fullFileName +
                                      ' does not match the expected one. '
                                      'The default value is used.')
                else:
                    self.values[item] = val
            else:
                readErrors.append('Disk file ' + self.fullFileName +
                                  " contains extra value '" + item +
                                  "'. It will be lost.")

        # If format is bad then overwrite the file
        if readErrors:
            self.__saveErrors("\n".join(readErrors))
            self.flush()

    @staticmethod
    def __saveErrors(message):
        """Appends the message to the startup errors file"""
        try:
            with open(SETTINGS_DIR + 'startupmessages.log', 'a',
                      encoding=SETTINGS_ENCODING) as diskfile:
                diskfile.write('------ Startup report at ' +
                               str(datetime.datetime.now()) + '\n')
                diskfile.write(message)
                diskfile.write('\n------\n\n')
        except:
            # This is not that important
            pass

    def flush(self):
        """Writes the settings to the disk"""
        try:
            with open(self.__fullFileName, 'w',
                      encoding=SETTINGS_ENCODING) as diskfile:
                json.dump(self.values, diskfile,
                          default=settingsToJSON, indent=4)
        except Exception as exc:
            logging.error('Errol saving setting (to ' + self.__fullFileName +
                          '): ' + str(exc))

    def addRecentProject(self, projectFile, needFlush=True):
        """Adds the recent project to the list"""
        absProjectFile = os.path.realpath(projectFile)
        recentProjects = self.values['recentProjects']

        if absProjectFile in recentProjects:
            recentProjects.remove(absProjectFile)

        recentProjects.insert(0, absProjectFile)
        limit = self.values['maxRecentProjects']
        if len(recentProjects) > limit:
            recentProjects = recentProjects[0:limit]
        self.values['recentProjects'] = recentProjects
        if needFlush:
            self.flush()
        self.recentListChanged.emit()

    def deleteRecentProject(self, projectFile, needFlush=True):
        """Deletes the recent project from the list"""
        absProjectFile = os.path.realpath(projectFile)
        recentProjects = self.values['recentProjects']

        if absProjectFile in recentProjects:
            recentProjects.remove(absProjectFile)
            self.values['recentProjects'] = recentProjects
            if needFlush:
                self.flush()
            self.recentListChanged.emit()
        return

    @staticmethod
    def getDefaultGeometry():
        """Provides the default window size and location"""
        return __DEFAULT_SETTINGS['xpos'], __DEFAULT_SETTINGS['ypos'], \
               __DEFAULT_SETTINGS['width'], __DEFAULT_SETTINGS['height']

    def getProfilerSettings(self):
        """Provides the profiler IDE-wide settings"""
        return self.values['profilerLimits']

    def setProfilerSettings(self, newValue, needFlush=True):
        """Updates the profiler settings"""
        if self.values['profilerLimits'] != newValue:
            self.values['profilerLimits'] = newValue
            if needFlush:
                self.flush()

    def getDebuggerSettings(self):
        """Provides the debugger IDE-wide settings"""
        return self.values['debuggerSettings']

    def setDebuggerSettings(self, newValue, needFlush=True):
        """Updates the debugger settings"""
        if self.values['debuggerSettings'] != newValue:
            self.values['debuggerSettings'] = newValue
            if needFlush:
                self.flush()

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value
        self.flush()


settingsSingleton = SettingsWrapper()


def Settings():
    " Settings singleton access "
    return settingsSingleton
