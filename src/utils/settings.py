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


""" codimension settings """

import os, os.path, ConfigParser, logging
from PyQt4.QtCore import QObject, SIGNAL, QDir
from filepositions import FilesPositions
from run import TERM_AUTO


settingsDir = os.path.normpath( str( QDir.homePath() ) ) + \
              os.path.sep + ".codimension" + os.path.sep

ropePreferences = { 'ignore_syntax_errors': True,
                    'ignore_bad_imports':   True,
                    'soa_followed_calls':   2,
                    'extension_modules': [
                        "sys", "os", "os.path", "time", "datetime",
                        "thread", "errno", "inspect", "math", "cmath",
                        "socket", "re", "zlib", "shutil",
                        "configParser", "urllib", "urllib2", "xml",
                        "numpy", "collections", "cPickle", "gc",
                        "exceptions", "signal", "imp", "operator",
                        "strop", "zipimport",
                        "PyQt4", "PyQt4.QtGui", "QtGui",
                        "PyQt4.QtCore", "QtCore" ],
                    'ignored_resources': [
                        "*.pyc", "*~", ".ropeproject",
                        ".hg", ".svn", "_svn", ".git", ".cvs" ] }

_maxRecentProjects = 32
_defaultXPos = 50
_defaultYPos = 50
_defaultWidth = 750
_defaultHeight = 550
_defaultScreenWidth = 0
_defaultScreenHeight = 0
_defaultXDelta = 0
_defaultYDelta = 0
_defaultHSplitSize = "200, 450, 575"
_defaultVSplitSize = "400, 150"
_defaultFilesFilters = [ "^\\.", ".*\\~$",
                         ".*\\.pyc$", ".*\\.swp$", ".*\\.pyo$" ]
_defaultProjectLoaded = False
_defaultZoom = 0
_defaultSkin = "default"
_defaultLastSuccessVerCheck = 0
_defaultNewerVerShown = False
_defaultModifiedFormat = "%s *"
_defaultTermType = TERM_AUTO
_defaultEditorEdge = 80
_defaultProfileNodeLimit = 1.0
_defaultProfileEdgeLimit = 1.0
_defaultDebugReportExceptions = True
_defaultDebugTraceInterpreter = True
_defaultDebugStopAtFirstLine = True
_defaultDebugAutofork = False
_defaultDebugFollowChild = True

# Editor settings available via the user interface
_defaultVerticalEdge = True
_defaultShowSpaces = True
_defaultLineWrap = False
_defaultShowEOL = False
_defaultShowBraceMatch = True
_defaultAutoIndent = True
_defaultBackspaceUnindent = True
_defaultTabIndents = True
_defaultIndentationGuides = False
_defaultCurrentLineVisible = True
_defaultJumpToFirstNonSpace = False
_defaultRemoveTrailingOnSave = False

# Tooltip settings
_defaultProjectTooltips = True
_defaultRecentTooltips = True
_defaultClassesTooltips = True
_defaultFunctionsTooltips = True
_defaultOutlineTooltips = True
_defaultFindNameTooltips = True
_defaultFindFileTooltips = True
_defaultEditorTooltips = True


class DebuggerSettings:
    " Holds IDE-wide debugger options "
    def __init__( self ):
        self.reportExceptions = True
        self.traceInterpreter = True
        self.stopAtFirstLine = True
        self.autofork = False
        self.followChild = True
        return

    def __eq__( self, other ):
        return self.reportExceptions == other.reportExceptions and \
               self.traceInterpreter == other.traceInterpreter and \
               self.stopAtFirstLine == other.stopAtFirstLine and \
               self.autofork == other.autofork and \
               self.followChild == other.followChild

class ProfilerSettings:
    " Holds IDE-wide profiler options "
    def __init__( self ):
        self.nodeLimit = 1.0
        self.edgeLimit = 1.0
        return

    def __eq__( self, other ):
        return self.nodeLimit == other.nodeLimit and \
               self.edgeLimit == other.edgeLimit


class Settings( object ):
    """
    Implementation idea is taken from here:
    http://wiki.forum.nokia.com/index.php/How_to_make_a_singleton_in_Python
    """

    iInstance = None
    class Singleton( QObject ):
        """ Provides settings singleton facility """


        def __init__( self ):

            QObject.__init__( self )

            # make sure that the directory exists
            if not os.path.exists( settingsDir ):
                os.mkdir( settingsDir )

            # Save the config file name
            self.fullFileName = settingsDir + "settings"

            # Load previous sessions files positions and tabs status
            self.filePositions = FilesPositions( settingsDir )
            self.tabsStatus = self.__loadTabsStatus()
            self.findFilesWhat, \
            self.findFilesDirs, \
            self.findFilesMasks = self.__loadFindFilesHistory()
            self.findNameHistory = self.__loadFindNameHistory()
            self.findFileHistory = self.__loadFindFileHistory()

            self.__setDefaultValues()

            # Create file if does not exist
            if not os.path.exists( self.fullFileName ):
                # Save to file
                self.flushSettings()
                return

            self.formatOK = True
            config = ConfigParser.ConfigParser()

            try:
                config.read( [ self.fullFileName ] )
            except:
                # Bad error - save default
                config = None
                logging.warning( "Bad format of settings detected. " \
                                 "Overwriting the settings file." )
                self.flushSettings()
                return

            self.zoom = self.__getInt( config, 'general',
                        'zoom', _defaultZoom )
            self.xpos = self.__getInt( config, 'general',
                        'xpos', _defaultXPos )
            self.ypos = self.__getInt( config, 'general',
                        'ypos', _defaultYPos )
            self.width = self.__getInt( config, 'general',
                        'width', _defaultWidth )
            self.height = self.__getInt( config, 'general',
                        'height', _defaultHeight )
            self.xdelta = self.__getInt( config, 'general',
                        'xdelta', _defaultXDelta )
            self.ydelta = self.__getInt( config, 'general',
                        'ydelta', _defaultYDelta )
            self.screenWidth = self.__getInt( config, 'general',
                        'screenwidth', _defaultScreenWidth )
            self.screenHeight = self.__getInt( config, 'general',
                        'screenheight', _defaultScreenHeight )
            self.leftBarMinimized = self.__getBool( config, 'general',
                        'leftBarMinimized', False )
            self.bottomBarMinimized = self.__getBool( config, 'general',
                        'bottomBarMinimized', False )
            self.rightBarMinimized = self.__getBool( config, 'general',
                        'rightBarMinimized', False )
            self.projectLoaded = self.__getBool( config, 'general',
                        'projectLoaded', _defaultProjectLoaded )
            self.skinName = self.__getStr( config, 'general',
                        'skin', _defaultSkin )
            self.verticalEdge = self.__getBool( config, 'general',
                        'verticalEdge', _defaultVerticalEdge )
            self.showSpaces = self.__getBool( config, 'general',
                        'showSpaces', _defaultShowSpaces )
            self.lineWrap = self.__getBool( config, 'general',
                        'lineWrap', _defaultLineWrap )
            self.showEOL = self.__getBool( config, 'general',
                        'showEOL', _defaultShowEOL )
            self.showBraceMatch = self.__getBool( config, 'general',
                        'showBraceMatch', _defaultShowBraceMatch )
            self.autoIndent = self.__getBool( config, 'general',
                        'autoIndent', _defaultAutoIndent )
            self.backspaceUnindent = self.__getBool( config, 'general',
                        'backspaceUnindent', _defaultBackspaceUnindent )
            self.tabIndents = self.__getBool( config, 'general',
                        'tabIndents', _defaultTabIndents )
            self.indentationGuides = self.__getBool( config, 'general',
                        'indentationGuides', _defaultIndentationGuides )
            self.currentLineVisible = self.__getBool( config, 'general',
                        'currentLineVisible', _defaultCurrentLineVisible )
            self.jumpToFirstNonSpace = self.__getBool( config, 'general',
                        'jumpToFirstNonSpace', _defaultJumpToFirstNonSpace )
            self.removeTrailingOnSave = self.__getBool( config, 'general',
                        'removeTrailingOnSave', _defaultRemoveTrailingOnSave )
            self.lastSuccessVerCheck = self.__getInt( config, 'general',
                        'lastSuccessVerCheck', _defaultLastSuccessVerCheck )
            self.newerVerShown = self.__getBool( config, 'general',
                        'newerVerShown', _defaultNewerVerShown )
            self.showFSViewer = self.__getBool( config, 'general',
                        'showFSViewer', True )
            self.modifiedFormat = self.__getStr( config, 'general',
                        'modifiedFormat', _defaultModifiedFormat )
            self.terminalType = self.__getInt( config, 'general',
                        'terminalType', _defaultTermType )

            self.projectTooltips = self.__getBool( config, "general",
                        "projectTooltips", _defaultProjectTooltips )
            self.recentTooltips = self.__getBool( config, "general",
                        "recentTooltips", _defaultRecentTooltips )
            self.classesTooltips = self.__getBool( config, "general",
                        "classesTooltips", _defaultClassesTooltips )
            self.functionsTooltips = self.__getBool( config, "general",
                        "functionsTooltips", _defaultFunctionsTooltips )
            self.outlineTooltips = self.__getBool( config, "general",
                        "outlineTooltips", _defaultOutlineTooltips )
            self.findNameTooltips = self.__getBool( config, "general",
                        "findNameTooltips", _defaultFindNameTooltips )
            self.findFileTooltips = self.__getBool( config, "general",
                        "findFileTooltips", _defaultFindFileTooltips )
            self.editorTooltips = self.__getBool( config, "general",
                        "editorTooltips", _defaultEditorTooltips )

            # Profile parameters, IDE wide
            self.profileNodeLimit = self.__getFloat( config, 'general',
                        'profileNodeLimit', _defaultProfileNodeLimit )
            self.profileEdgeLimit = self.__getFloat( config, 'general',
                        'profileEdgeLimit', _defaultProfileEdgeLimit )

            # Debug parameters, IDE wide
            self.debugReportExceptions = self.__getBool( config, 'general',
                        'debugReportExceptions', _defaultDebugReportExceptions )
            self.debugTraceInterpreter = self.__getBool( config, 'general',
                        'debugTraceInterpreter', _defaultDebugTraceInterpreter )
            self.debugStopAtFirstLine = self.__getBool( config, 'general',
                        'debugStopAtFirstLine', _defaultDebugStopAtFirstLine )
            self.debugAutofork = self.__getBool( config, 'general',
                        'debugAutofork', _defaultDebugAutofork )
            self.debugFollowChild = self.__getBool( config, 'general',
                        'debugFollowChild', _defaultDebugFollowChild )

            self.editorEdge = self.__getInt( config, 'general',
                        'editorEdge', _defaultEditorEdge )

            asString = self.__getStr( config, 'general',
                        'hSplitterSizes', _defaultHSplitSize ).split( ',' )
            if len( asString ) != 3:
                asString = _defaultHSplitSize.split( ',' )
                self.formatOK = False
            self.hSplitterSizes = [ int(asString[0]),
                                    int(asString[1]),
                                    int(asString[0]) ]

            asString = self.__getStr( config, 'general',
                        'vSplitterSizes', _defaultVSplitSize ).split( ',' )
            if len( asString ) != 2:
                asString = _defaultVSplitSize.split( ',' )
                self.formatOK = False
            self.vSplitterSizes = [ int(asString[0]), int(asString[1]) ]

            # recent projects part
            self.recentProjects = []
            index = 0
            try:
                while True:
                    projectFile = config.get( 'recentProjects',
                                              'project' + str(index) ).strip()
                    self.recentProjects.append( str( projectFile ) )
                    index += 1
            except ConfigParser.NoSectionError:
                self.formatOK = False
            except ConfigParser.NoOptionError:
                # Just continue
                pass
            except:
                self.formatOK = False

            # Filters part
            self.projectFilesFilters = []
            index = 0
            try:
                while True:
                    flt = config.get( 'projectFilesFilters',
                                      'filter' + str(index) ).strip()
                    self.projectFilesFilters.append( flt )
                    index += 1
            except ConfigParser.NoSectionError:
                self.formatOK = False
                self.projectFilesFilters = _defaultFilesFilters
            except ConfigParser.NoOptionError:
                # Just continue
                pass
            except:
                self.formatOK = False
                self.projectFilesFilters = _defaultFilesFilters


            config = None

            # If format is bad then overwrite the file
            if self.formatOK == False:
                logging.info( "Some settings missed or bad format of the "
                              "settings file. Restoring the settings file." )
                self.flushSettings()

            return

        def __setDefaultValues( self ):
            " Sets the default values to the members "

            self.zoom = _defaultZoom
            self.xpos = _defaultXPos
            self.ypos = _defaultXPos
            self.width = _defaultWidth
            self.height = _defaultHeight
            self.screenWidth = _defaultScreenWidth
            self.screenHeight = _defaultScreenHeight
            self.xdelta = _defaultXDelta
            self.ydelta = _defaultYDelta
            self.skinName = _defaultSkin

            self.verticalEdge = _defaultVerticalEdge
            self.showSpaces = _defaultShowSpaces
            self.lineWrap = _defaultLineWrap
            self.showEOL = _defaultShowEOL
            self.showBraceMatch = _defaultShowBraceMatch
            self.autoIndent = _defaultAutoIndent
            self.backspaceUnindent = _defaultBackspaceUnindent
            self.tabIndents = _defaultTabIndents
            self.indentationGuides = _defaultIndentationGuides
            self.currentLineVisible = _defaultCurrentLineVisible
            self.jumpToFirstNonSpace = _defaultJumpToFirstNonSpace
            self.removeTrailingOnSave = _defaultRemoveTrailingOnSave
            self.modifiedFormat = _defaultModifiedFormat

            self.projectTooltips = _defaultProjectTooltips
            self.recentTooltips = _defaultRecentTooltips
            self.classesTooltips = _defaultClassesTooltips
            self.functionsTooltips = _defaultFunctionsTooltips
            self.outlineTooltips = _defaultOutlineTooltips
            self.findNameTooltips = _defaultFindNameTooltips
            self.findFileTooltips = _defaultFindFileTooltips
            self.editorTooltips = _defaultEditorTooltips

            self.leftBarMinimized = False
            self.bottomBarMinimized = False
            self.rightBarMinimized = False
            self.hSplitterSizes = [ 200, 450, 550 ]
            self.vSplitterSizes = [ 400, 150 ]
            self.recentProjects = []
            self.projectFilesFilters = _defaultFilesFilters
            self.projectLoaded = _defaultProjectLoaded
            self.lastSuccessVerCheck = _defaultLastSuccessVerCheck
            self.newerVerShown = _defaultNewerVerShown
            self.showFSViewer = True
            self.terminalType = _defaultTermType
            self.editorEdge = _defaultEditorEdge
            self.profileNodeLimit = _defaultProfileNodeLimit
            self.profileEdgeLimit = _defaultProfileEdgeLimit
            self.debugReportExceptions = _defaultDebugReportExceptions
            self.debugTraceInterpreter = _defaultDebugTraceInterpreter
            self.debugStopAtFirstLine = _defaultDebugStopAtFirstLine
            self.debugAutofork = _defaultDebugAutofork
            self.debugFollowChild = _defaultDebugFollowChild
            return

        def __getInt( self, conf, sec, key, default ):
            " Helper to read a config value "
            try:
                return conf.getint( sec, key )
            except:
                self.formatOK = False
            return default

        def __getFloat( self, conf, sec, key, default ):
            " Helper to read a config value "
            try:
                return conf.getfloat( sec, key )
            except:
                self.formatOK = False
            return default

        def __getBool( self, conf, sec, key, default ):
            " Helper to read a config value "
            try:
                return conf.getboolean( sec, key )
            except:
                self.formatOK = False
            return default

        def __getStr( self, conf, sec, key, default ):
            " Helper to read a config value "
            try:
                return conf.get( sec, key ).strip()
            except:
                self.formatOK = False
            return default

        def flushSettings( self ):
            """ Writes all the settings into the file """

            # Save the tabs status
            self.__saveTabsStatus()
            self.__saveFindFilesHistory()
            self.__saveFindNameHistory()
            self.__saveFindFileHistory()

            # Recent projects part
            recentPart = "[recentProjects]\n"
            index = 0
            for item in self.recentProjects:
                recentPart += "project" + str(index) + "=" + item + "\n"
                index += 1

            filterPart = "[projectFilesFilters]\n"
            index = 0
            for item in self.projectFilesFilters:
                filterPart += "filter" + str(index) + "=" + item + "\n"
                index += 1

            f = open( self.fullFileName, "w" )
            self.__writeHeader( f )
            f.write(
            "[general]\n"
            "zoom=" + str( self.zoom ) + "\n"
            "xpos=" + str( self.xpos ) + "\n"
            "ypos=" + str( self.ypos ) + "\n"
            "width=" + str( self.width ) + "\n"
            "height=" + str( self.height ) + "\n"
            "screenwidth=" + str( self.screenWidth ) + "\n"
            "screenheight=" + str( self.screenHeight ) + "\n"
            "xdelta=" + str( self.xdelta ) + "\n"
            "ydelta=" + str( self.ydelta ) + "\n"
            "skin=" + self.skinName + "\n"
            "modifiedFormat=" + self.modifiedFormat + "\n"
            "verticalEdge=" + str( self.verticalEdge ) + "\n"
            "showSpaces=" + str( self.showSpaces ) + "\n"
            "lineWrap=" + str( self.lineWrap ) + "\n"
            "showEOL=" + str( self.showEOL ) + "\n"
            "showBraceMatch=" + str( self.showBraceMatch ) + "\n"
            "autoIndent=" + str( self.autoIndent ) + "\n"
            "backspaceUnindent=" + str( self.backspaceUnindent ) + "\n"
            "tabIndents=" + str( self.tabIndents ) + "\n"
            "indentationGuides=" + str( self.indentationGuides ) + "\n"
            "currentLineVisible=" + str( self.currentLineVisible ) + "\n"
            "jumpToFirstNonSpace=" + str( self.jumpToFirstNonSpace ) + "\n"
            "removeTrailingOnSave=" + str( self.removeTrailingOnSave ) + "\n"
            "lastSuccessVerCheck=" + str( self.lastSuccessVerCheck ) + "\n"
            "newerVerShown=" + str( self.newerVerShown ) + "\n"
            "showFSViewer=" + str( self.showFSViewer ) + "\n"
            "terminalType=" + str( self.terminalType ) + "\n"
            "profileNodeLimit=" + str( self.profileNodeLimit ) + "\n"
            "profileEdgeLimit=" + str( self.profileEdgeLimit ) + "\n"
            "debugReportExceptions=" + str( self.debugReportExceptions ) + "\n"
            "debugTraceInterpreter=" + str( self.debugTraceInterpreter ) + "\n"
            "debugStopAtFirstLine=" + str( self.debugStopAtFirstLine ) + "\n"
            "debugAutofork=" + str( self.debugAutofork ) + "\n"
            "debugFollowChild=" + str( self.debugFollowChild ) + "\n"
            "editorEdge=" + str( self.editorEdge ) + "\n"
            "leftBarMinimized=" + str( int( self.leftBarMinimized ) ) + "\n"
            "projectTooltips=" + str( self.projectTooltips ) + "\n"
            "recentTooltips=" + str( self.recentTooltips ) + "\n"
            "classesTooltips=" + str( self.classesTooltips ) + "\n"
            "functionsTooltips=" + str( self.functionsTooltips ) + "\n"
            "outlineTooltips=" + str( self.outlineTooltips ) + "\n"
            "findNameTooltips=" + str( self.findNameTooltips ) + "\n"
            "findFileTooltips=" + str( self.findFileTooltips ) + "\n"
            "editorTooltips=" + str( self.editorTooltips ) + "\n"
            "bottomBarMinimized=" +
                    str( int( self.bottomBarMinimized ) ) + "\n"
            "rightBarMinimized=" +
                    str( int( self.rightBarMinimized ) ) + "\n"
            "projectLoaded=" + str( int( self.projectLoaded ) ) + "\n"
            "hSplitterSizes=" +
                    str( self.hSplitterSizes[0] ) + "," +
                    str( self.hSplitterSizes[1] ) + "," +
                    str( self.hSplitterSizes[2] ) + "\n"
            "vSplitterSizes=" +
                    str( self.vSplitterSizes[0] ) + "," +
                    str( self.vSplitterSizes[1] ) + "\n\n" +
                 recentPart + "\n\n" +
                 filterPart + "\n" )

            f.flush()
            f.close()
            self.formatOK = True
            return

        def addRecentProject( self, projectFile ):
            " Adds the recent project to the list "
            absProjectFile = os.path.abspath( projectFile )
            if absProjectFile in self.recentProjects:
                self.recentProjects.remove( absProjectFile )

            self.recentProjects.insert( 0, absProjectFile )
            if len( self.recentProjects ) > _maxRecentProjects:
                self.recentProjects = \
                            self.recentProjects[ 0 : _maxRecentProjects ]
            self.flushSettings()
            self.emit( SIGNAL('recentListChanged') )
            return

        def deleteRecentProject( self, projectFile ):
            " Deletes the recent project from the list "
            absProjectFile = os.path.abspath( projectFile )
            if absProjectFile in self.recentProjects:
                self.recentProjects.remove( absProjectFile )
                self.flushSettings()
                self.emit( SIGNAL('recentListChanged') )
            return

        @staticmethod
        def getDefaultGeometry():
            " Provides the default window size and location "
            return _defaultXPos, _defaultYPos, \
                   _defaultWidth, _defaultHeight

        @staticmethod
        def __writeHeader( fileObj ):
            " Helper to write a header with a warning "
            fileObj.write( "#\n"
                           "# Generated automatically.\n"
                           "# Don't edit it manually unless you "
                           "know what you are doing.\n"
                           "#\n\n" )
            return

        @staticmethod
        def __writeList( fileObj, header, prefix, items ):
            " Helper to write a list "
            fileObj.write( "[" + header + "]\n" )
            index = 0
            for item in items:
                fileObj.write( prefix + str( index ) + "=" + item + "\n" )
                index += 1
            fileObj.write( "\n" )
            return

        @staticmethod
        def __loadListSection( config, section, listPrefix ):
            " Loads a list off the given section from the given file "
            items = []
            index = 0
            try:
                while True:
                    item = config.get( section,
                                       listPrefix + str( index ) ).strip()
                    index += 1
                    items.append( item )
            except:
                pass
            return items

        def __loadTabsStatus( self ):
            " Loads the last saved tabs statuses "

            config = ConfigParser.ConfigParser()
            try:
                config.read( settingsDir + "tabsstatus" )
            except:
                config = None
                return []

            # tabs part
            items = self.__loadListSection( config, 'tabsstatus', 'tab' )
            config = None
            return items

        def __saveTabsStatus( self ):
            " Saves the tabs status "
            fName = settingsDir + "tabsstatus"
            try:
                f = open( fName, "w" )
                self.__writeHeader( f )
                self.__writeList( f, "tabsstatus", "tab", self.tabsStatus )
                f.close()
            except:
                # Do nothing, it's not vital important to have this file
                pass
            return

        def __loadFindFilesHistory( self ):
            " Loads the saved find files dialog history "
            config = ConfigParser.ConfigParser()
            try:
                config.read( settingsDir + "findinfiles" )
            except:
                return [], [], []

            what = self.__loadListSection( config, 'whathistory', 'what' )
            dirs = self.__loadListSection( config, 'dirhistory', 'dir' )
            mask = self.__loadListSection( config, 'maskhistory', 'mask' )
            return what, dirs, mask

        def __loadFindNameHistory( self ):
            " Loads the saved find name dialog history "
            config = ConfigParser.ConfigParser()
            try:
                config.read( settingsDir + "findinfiles" )
            except:
                return []
            return self.__loadListSection( config, 'findnamehistory', 'find' )

        def __loadFindFileHistory( self ):
            " Loads the saved find file dialog history "
            config = ConfigParser.ConfigParser()
            try:
                config.read( settingsDir + "findfile" )
            except:
                return []
            return self.__loadListSection( config, 'findfilehistory', 'find' )

        def __saveFindFilesHistory( self ):
            " Saves the find in files dialog history "
            fName = settingsDir + "findinfiles"
            try:
                f = open( fName, "w" )
                self.__writeHeader( f )
                self.__writeList( f, "whathistory", "what",
                                  self.findFilesWhat )
                self.__writeList( f, "dirhistory", "dir",
                                  self.findFilesDirs )
                self.__writeList( f, "maskhistory", "mask",
                                  self.findFilesMasks )
                f.close()
            except:
                # Do nothing, it's not vital important to have this file
                pass
            return

        def __saveFindNameHistory( self ):
            " Saves the find name dialog history "
            fName = settingsDir + "findinfiles"
            try:
                f = open( fName, "w" )
                self.__writeList( f, "findnamehistory", "find",
                                  self.findNameHistory )
                f.close()
            except:
                # Do nothing, it's not vital important to have this file
                pass
            return

        def __saveFindFileHistory( self ):
            " Saves the find file dialog history "
            fName = settingsDir + "findfile"
            try:
                f = open( fName, "w" )
                self.__writeList( f, 'findfilehistory', 'find',
                                  self.findFileHistory )
                f.close()
            except:
                pass
            return


    def __init__( self ):
        if Settings.iInstance is None:
            Settings.iInstance = Settings.Singleton()

        self.__dict__[ '_Settings__iInstance' ] = Settings.iInstance
        return

    def __getattr__( self, aAttr ):
        return getattr( self.iInstance, aAttr )

    def __setattr__( self, aAttr, aValue ):
        setattr( self.iInstance, aAttr, aValue )
        self.flushSettings()
        return

    def getProfilerSettings( self ):
        " Provides the profiler IDE-wide settings "
        profSettings = ProfilerSettings()
        profSettings.edgeLimit = self.iInstance.profileEdgeLimit
        profSettings.nodeLimit = self.iInstance.profileNodeLimit
        return profSettings

    def setProfilerSettings( self, newValues ):
        " Updates the profiler settings "
        self.iInstance.profileEdgeLimit = newValues.edgeLimit
        self.iInstance.profileNodeLimit = newValues.nodeLimit
        self.flushSettings()
        return

    def getDebuggerSettings( self ):
        " Provides the debugger IDE-wide settings "
        dbgSettings = DebuggerSettings()
        dbgSettings.autofork = self.iInstance.debugAutofork
        dbgSettings.followChild = self.iInstance.debugFollowChild
        dbgSettings.reportExceptions = self.iInstance.debugReportExceptions
        dbgSettings.stopAtFirstLine = self.iInstance.debugStopAtFirstLine
        dbgSettings.traceInterpreter = self.iInstance.debugTraceInterpreter
        return dbgSettings

    def setDebuggerSettings( self, newValues ):
        " Updates the debugger settings "
        self.iInstance.debugAutofork = newValues.autofork
        self.iInstance.debugFollowChild = newValues.followChild
        self.iInstance.debugReportExceptions = newValues.reportExceptions
        self.iInstance.debugStopAtFirstLine = newValues.stopAtFirstLine
        self.iInstance.debugTraceInterpreter = newValues.traceInterpreter
        self.flushSettings()
        return
