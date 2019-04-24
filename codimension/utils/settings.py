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
import datetime
import json
import logging
from copy import deepcopy
from ui.qt import QObject, QDir, pyqtSignal
from .config import SETTINGS_ENCODING, CONFIG_DIR
from .runparamscache import RunParametersCache
from .debugenv import DebuggerEnvironment
from .searchenv import SearchEnvironment
from .fsenv import FileSystemEnvironment
from .filepositions import FilePositions
from .userencodings import FileEncodings
from .flowgroups import FlowUICollapsedGroups
from .webresourcecache import WebResourceCache


SETTINGS_DIR = os.path.join(os.path.realpath(QDir.homePath()),
                            CONFIG_DIR) + os.path.sep

CLEAR_AND_REUSE = 0
NO_CLEAR_AND_REUSE = 1
NO_REUSE = 2


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


_DEFAULT_SETTINGS = {
    # general
    'zoom': 0,
    'flowZoom': 0,
    'smartZoom': 0,
    'xpos': 50,
    'ypos': 50,
    'width': 750,
    'height': 550,
    'rendererxpos': 425,
    'rendererypos': 75,
    'rendererwidth': 375,
    'rendererheight': 550,
    'screenwidth': 0,
    'screenheight': 0,
    'xdelta': 0,
    'ydelta': 0,
    'skin': 'default',
    'modifiedFormat': '%s *',
    'verticalEdge': True,
    'showSpaces': True,
    'lineWrap': False,
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
    'profilerLimits': ProfilerSettings(),
    'debuggerSettings': DebuggerSettings(),
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
    'floatingRenderer': False,
    'hSplitterSizes': [200, 450, 575],
    'vSplitterSizes': [400, 150],
    'flowSplitterSizes': [225, 225],
    'style': 'fusion',
    'vcsstatusupdateinterval': 30,      # seconds
    'tablistsortalpha': True,
    'taborderpreserved': False,
    'maxRecentProjects': 32,
    'maxRecentFiles': 32,
    'maxSearchEntries': 32,
    'maxHighlightedMatches': 256,
    'maxBreakpoints': 63,               # per file
    'encoding': 'utf-8',
    'hidedocstrings': False,
    'hidecomments': False,
    'hideexcepts': False,

    # Debug variable filters
    'dbgfltlocal': True,
    'dbgfltglobal': True,
    'dbgflthidden': True,
    'dbgflttype': False,
    'dbgfltmethod': False,
    'dbgfltfunc': False,
    'dbgfltbuiltin': False,
    'dbgfltmodule': False,
    'dbgfltnotype': False,

    'calltrace': True,

    # The IO redirect console
    'ioconsolemaxmsgs': 10000,
    'ioconsoledelchunk': 512,
    'ioconsolelinewrap': False,
    'ioconsoleshowspaces': True,
    'ioconsoleautoscroll': True,
    'ioconsolereuse': CLEAR_AND_REUSE,

    'navbarglobalsimports': False,

    'recentProjects': [],
    'projectFilesFilters': ['^\\.', '.*\\~$', '.*\\.pyc$',
                            '.*\\.swp$', '.*\\.pyo$', '__pycache__'],
    'ignoredExceptions': [],
    'disabledPlugins': [],
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
                      FilePositions,
                      FileEncodings,
                      FlowUICollapsedGroups):

    """Provides settings singleton facility"""

    MAX_SMART_ZOOM = 3

    sigRecentListChanged = pyqtSignal()
    sigFlowSplitterChanged = pyqtSignal()
    sigFlowZoomChanged = pyqtSignal()
    sigTextZoomChanged = pyqtSignal()
    sigHideDocstringsChanged = pyqtSignal()
    sigHideCommentsChanged = pyqtSignal()
    sigHideExceptsChanged = pyqtSignal()
    sigSmartZoomChanged = pyqtSignal()
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

        self.minTextZoom = None
        self.minCFlowZoom = None

        self.__values = deepcopy(_DEFAULT_SETTINGS)

        # make sure that the directory exists
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)

        RunParametersCache.setup(self, SETTINGS_DIR)
        DebuggerEnvironment.setup(self, SETTINGS_DIR)
        SearchEnvironment.setup(self, SETTINGS_DIR)
        FileSystemEnvironment.setup(self, SETTINGS_DIR)
        FilePositions.setup(self, SETTINGS_DIR)
        FileEncodings.setup(self, SETTINGS_DIR)
        FlowUICollapsedGroups.setup(self, SETTINGS_DIR)

        self.webResourceCache = WebResourceCache(SETTINGS_DIR + os.path.sep +
                                                 'webresourcecache')

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
            with open(self.__fullFileName, "r",
                      encoding=SETTINGS_ENCODING) as diskfile:
                diskValues = json.load(diskfile, object_hook=settingsFromJSON)
        except Exception as exc:
            # Bad error - save default
            self.__saveErrors('Could not read setting from ' +
                              self.__fullFileName + ': ' + str(exc) +
                              'Overwriting with the default settings...')
            self.flush()
            return

        for item, val in diskValues.items():
            if item in self.__values:
                if type(self.__values[item]) != type(val):
                    readErrors.append("Settings '" + item +
                                      "' type from the disk file " +
                                      self.__fullFileName +
                                      ' does not match the expected one. '
                                      'The default value is used.')
                else:
                    self.__values[item] = val
            else:
                readErrors.append('Disk file ' + self.__fullFileName +
                                  " contains extra value '" + item +
                                  "'. It will be lost.")

        # If format is bad then overwrite the file
        if readErrors:
            self.__saveErrors("\n".join(readErrors))
            self.flush()

        SearchEnvironment.setLimit(self, self.__values['maxSearchEntries'])
        FileSystemEnvironment.setLimit(self, self.__values['maxRecentFiles'])

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
                json.dump(self.__values, diskfile,
                          default=settingsToJSON, indent=4)
        except Exception as exc:
            logging.error('Errol saving setting (to ' + self.__fullFileName +
                          '): ' + str(exc))

    def addRecentProject(self, projectFile, needFlush=True):
        """Adds the recent project to the list"""
        absProjectFile = os.path.realpath(projectFile)
        recentProjects = self.__values['recentProjects']

        if absProjectFile in recentProjects:
            recentProjects.remove(absProjectFile)

        recentProjects.insert(0, absProjectFile)
        limit = self.__values['maxRecentProjects']
        if len(recentProjects) > limit:
            recentProjects = recentProjects[0:limit]
        self.__values['recentProjects'] = recentProjects
        if needFlush:
            self.flush()
        self.sigRecentListChanged.emit()

    def deleteRecentProject(self, projectFile, needFlush=True):
        """Deletes the recent project from the list"""
        absProjectFile = os.path.realpath(projectFile)
        recentProjects = self.__values['recentProjects']

        if absProjectFile in recentProjects:
            recentProjects.remove(absProjectFile)
            self.__values['recentProjects'] = recentProjects
            if needFlush:
                self.flush()
            self.sigRecentListChanged.emit()

    @staticmethod
    def getDefaultGeometry():
        """Provides the default window size and location"""
        return _DEFAULT_SETTINGS['xpos'], _DEFAULT_SETTINGS['ypos'], \
               _DEFAULT_SETTINGS['width'], _DEFAULT_SETTINGS['height']

    @staticmethod
    def getDefaultRendererWindowGeometry():
        """Provides the default renderer window size and location"""
        # A bit shifted down and half of the width of the main window
        return _DEFAULT_SETTINGS['rendererxpos'], \
               _DEFAULT_SETTINGS['rendererypos'], \
               _DEFAULT_SETTINGS['rendererwidth'], \
               _DEFAULT_SETTINGS['rendererheight']

    def getProfilerSettings(self):
        """Provides the profiler IDE-wide settings"""
        return self.__values['profilerLimits']

    def setProfilerSettings(self, newValue, needFlush=True):
        """Updates the profiler settings"""
        if self.__values['profilerLimits'] != newValue:
            self.__values['profilerLimits'] = newValue
            if needFlush:
                self.flush()

    def getDebuggerSettings(self):
        """Provides the debugger IDE-wide settings"""
        return self.__values['debuggerSettings']

    def setDebuggerSettings(self, newValue, needFlush=True):
        """Updates the debugger settings"""
        if self.__values['debuggerSettings'] != newValue:
            self.__values['debuggerSettings'] = newValue
            if needFlush:
                self.flush()

    def validateZoom(self, minTextZoom, minCFlowZoom):
        """Validates the min zoom values"""
        self.minTextZoom = minTextZoom
        self.minCFlowZoom = minCFlowZoom
        warnings = []
        if self.__values['zoom'] < minTextZoom:
            warnings.append('The current text zoom (' +
                            str(self.__values['zoom']) +
                            ') will be adjusted to ' + str(minTextZoom) +
                            ' due to it is less than min fonts allowed.')
            self.__values['zoom'] = minTextZoom
        if self.__values['flowZoom'] < minCFlowZoom:
            warnings.append('The current flow zoom (' +
                            str(self.__values['flowZoom']) +
                            ') will be adjusted to ' + str(minCFlowZoom) +
                            ' due to it is less than min fonts allowed.')
            self.__values['flowZoom'] = minCFlowZoom
        if self.__values['smartZoom'] < 0:
            warnings.append('The current smart zoom (' +
                            str(self.__values['smartZoom']) +
                            ') will be adjusted to 0 due to it must be >= 0')
            self.__values['smartZoom'] = 0
        elif self.__values['smartZoom'] > SettingsWrapper.MAX_SMART_ZOOM:
            warnings.append('The current smart zoom (' +
                            str(self.__values['smartZoom']) +
                            ') will be adjusted to ' +
                            str(SettingsWrapper.MAX_SMART_ZOOM) +
                            ' due to it is larger than max allowed.')
            self.__values['smartZoom'] = SettingsWrapper.MAX_SMART_ZOOM

        if warnings:
            self.flush()
        return warnings

    def __getitem__(self, key):
        return self.__values[key]

    def __setitem__(self, key, value):
        self.__values[key] = value
        if key == 'flowSplitterSizes':
            self.sigFlowSplitterChanged.emit()
        elif key == 'flowZoom':
            self.sigFlowZoomChanged.emit()
        elif key == 'zoom':
            self.sigTextZoomChanged.emit()
        elif key == 'smartZoom':
            self.sigSmartZoomChanged.emit()
        elif key == 'hidedocstrings':
            self.sigHideDocstringsChanged.emit()
        elif key == 'hidecomments':
            self.sigHideCommentsChanged.emit()
        elif key == 'hideexcepts':
            self.sigHideExceptsChanged.emit()
        self.flush()

    def onTextZoomIn(self):
        """Triggered when the text is zoomed in"""
        self.__values['zoom'] += 1
        self.flush()
        self.sigTextZoomChanged.emit()

    def onTextZoomOut(self):
        """Triggered when the text is zoomed out"""
        if self.__values['zoom'] > self.minTextZoom:
            self.__values['zoom'] -= 1
            self.flush()
            self.sigTextZoomChanged.emit()

    def onTextZoomReset(self):
        """Triggered when the text zoom is reset"""
        if self.__values['zoom'] != 0:
            self.__values['zoom'] = 0
            self.flush()
            self.sigTextZoomChanged.emit()

    def onSmartZoomIn(self):
        """Triggered when the smart zoom is changed"""
        if self.__values['smartZoom'] < SettingsWrapper.MAX_SMART_ZOOM:
            self.__values['smartZoom'] += 1
            self.flush()
            self.sigSmartZoomChanged.emit()

    def onSmartZoomOut(self):
        """Triggered when the smart zoom is changed"""
        if self.__values['smartZoom'] > 0:
            self.__values['smartZoom'] -= 1
            self.flush()
            self.sigSmartZoomChanged.emit()

    def onFlowZoomIn(self):
        """Triggered when the flow is zoomed in"""
        self.__values['flowZoom'] += 1
        self.flush()
        self.sigFlowZoomChanged.emit()

    def onFlowZoomOut(self):
        """Triggered when the flow is zoomed out"""
        if self.__values['flowZoom'] > self.minCFlowZoom:
            self.__values['flowZoom'] -= 1
            self.flush()
            self.sigFlowZoomChanged.emit()

    def onFlowZoomReset(self):
        """Triggered when the flow zoom is reset"""
        if self.__values['flowZoom'] != 0:
            self.__values['flowZoom'] = 0
            self.flush()
            self.sigFlowZoomChanged.emit()

    def addRecentFile(self, path):
        """Adds a recent file. True if a new file was inserted."""
        ret = FileSystemEnvironment.addRecentFile(self, path)
        if ret:
            self.sigRecentFilesChanged.emit()
        return ret


SETTINGS_SINGLETON = SettingsWrapper()


def Settings():
    """Settings singleton access"""
    return SETTINGS_SINGLETON
