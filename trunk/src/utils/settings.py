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

import os, os.path, ConfigParser, sys, datetime
from PyQt4.QtCore import QObject, SIGNAL, QDir
from filepositions import FilesPositions
from run import TERM_AUTO


settingsDir = os.path.normpath( str( QDir.homePath() ) ) + \
              os.path.sep + ".codimension" + os.path.sep
thirdpartyDir = os.path.dirname( os.path.abspath( sys.argv[ 0 ] ) ) + \
                os.path.sep + "thirdparty" + os.path.sep

_H_SPLITTER_SIZES_DEFAULT = [ 200, 450, 575 ]
_V_SPLITTER_SIZES_DEFAULT = [ 400, 150 ]
_X_POS_DEFAULT = 50
_Y_POS_DEFAULT = 50
_WIDTH_DEFAULT = 750
_HEIGHT_DEFAULT = 550
_MAX_RECENT_PROJECTS = 32


ropePreferences = { 'ignore_syntax_errors': True,
                    'ignore_bad_imports':   True,
                    'soa_followed_calls':   2,
                    'extension_modules': [
                        "sys", "os", "os.path", "time", "datetime",
                        "thread", "errno", "inspect", "math", "cmath",
                        "socket", "re", "zlib", "shutil",
                        "ConfigParser", "urllib", "urllib2", "xml",
                        "numpy", "scipy", "collections", "cPickle", "gc",
                        "exceptions", "signal", "imp", "operator",
                        "strop", "zipimport",
                        "PyQt4", "PyQt4.QtGui", "QtGui",
                        "PyQt4.QtCore", "QtCore" ],
                    'ignored_resources': [
                        "*.pyo", "*.pyc", "*~", ".ropeproject",
                        ".hg", ".svn", "_svn", ".git", ".cvs" ] }


class CDMSetting:
    " Holds a single CDM setting description "
    TYPE_INT = 0
    TYPE_FLOAT = 1
    TYPE_BOOL = 2
    TYPE_STR = 3
    TYPE_STR_LST = 4
    TYPE_INT_LST = 5

    def __init__( self, name, sType, default ):
        self.name = name
        self.sType = sType
        self.default = default
        return


CDM_SETTINGS = {
"general": [
    CDMSetting( "zoom", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "xpos", CDMSetting.TYPE_INT, _X_POS_DEFAULT ),
    CDMSetting( "ypos", CDMSetting.TYPE_INT, _Y_POS_DEFAULT ),
    CDMSetting( "width", CDMSetting.TYPE_INT, _WIDTH_DEFAULT ),
    CDMSetting( "height", CDMSetting.TYPE_INT, _HEIGHT_DEFAULT ),
    CDMSetting( "screenwidth", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "screenheight", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "xdelta", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "ydelta", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "skin", CDMSetting.TYPE_STR, "default" ),
    CDMSetting( "modifiedFormat", CDMSetting.TYPE_STR, "%s *" ),
    CDMSetting( "verticalEdge", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "showSpaces", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "lineWrap", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "showEOL", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "showBraceMatch", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "autoIndent", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "backspaceUnindent", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "tabIndents", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "indentationGuides", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "currentLineVisible", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "jumpToFirstNonSpace", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "removeTrailingOnSave", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "lastSuccessVerCheck", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "newerVerShown", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "showFSViewer", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "showStackViewer", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "showThreadViewer", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "showIgnoredExcViewer", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "showWatchPointViewer", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "terminalType", CDMSetting.TYPE_INT, TERM_AUTO ),
    CDMSetting( "profileNodeLimit", CDMSetting.TYPE_FLOAT, 1.0 ),
    CDMSetting( "profileEdgeLimit", CDMSetting.TYPE_FLOAT, 1.0 ),
    CDMSetting( "debugReportExceptions", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "debugTraceInterpreter", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "debugStopAtFirstLine", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "debugAutofork", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "debugFollowChild", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "debugHideMCF", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "debugGLFilter", CDMSetting.TYPE_INT, 0 ),
    CDMSetting( "editorEdge", CDMSetting.TYPE_INT, 80 ),
    CDMSetting( "projectTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "recentTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "classesTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "functionsTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "outlineTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "findNameTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "findFileTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "editorTooltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "editorCalltips", CDMSetting.TYPE_BOOL, True ),
    CDMSetting( "leftBarMinimized", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "bottomBarMinimized", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "rightBarMinimized", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "projectLoaded", CDMSetting.TYPE_BOOL, False ),
    CDMSetting( "hSplitterSizes", CDMSetting.TYPE_INT_LST,
                _H_SPLITTER_SIZES_DEFAULT ),
    CDMSetting( "vSplitterSizes", CDMSetting.TYPE_INT_LST,
                _V_SPLITTER_SIZES_DEFAULT ),
    CDMSetting( "style", CDMSetting.TYPE_STR, "plastique" ),
           ],
"recentProjects" : [
    CDMSetting( "project", CDMSetting.TYPE_STR_LST, [] )
                   ],
"projectFilesFilters" : [
    CDMSetting( "filter", CDMSetting.TYPE_STR_LST, [ "^\\.", ".*\\~$",
                                                     ".*\\.pyc$", ".*\\.swp$",
                                                     ".*\\.pyo$" ] )
                        ],
"ignoredExceptions" : [
    CDMSetting( "exceptiontype", CDMSetting.TYPE_STR_LST, [] )
                      ],
"disabledPlugins" : [
    CDMSetting( "disabledplugins", CDMSetting.TYPE_STR_LST, [] )
                    ],
"dirSafeModules" : [
    CDMSetting( "module", CDMSetting.TYPE_STR_LST, [ "os", "sys", "xml", "collections",
                                                     "numpy", "scipy", "unittest" ] )
                   ],
               }



class DebuggerSettings:
    " Holds IDE-wide debugger options "
    def __init__( self ):
        self.reportExceptions = True
        self.traceInterpreter = True
        self.stopAtFirstLine = True
        self.autofork = False
        self.followChild = False
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
            self.values = {}
            self.__setDefaultValues()

            # make sure that the directory exists
            if not os.path.exists( settingsDir ):
                os.mkdir( settingsDir )

            # Save the config file name
            self.fullFileName = settingsDir + "settings"

            # Load previous sessions files positions and tabs status
            self.values[ "filePositions" ] = FilesPositions( settingsDir )
            self.values[ "tabsStatus" ] = self.__loadTabsStatus()
            self.values[ "findFilesWhat" ], \
            self.values[ "findFilesDirs" ], \
            self.values[ "findFilesMasks" ] = self.__loadFindFilesHistory()
            self.values[ "findNameHistory" ] = self.__loadFindNameHistory()
            self.values[ "findFileHistory" ] = self.__loadFindFileHistory()
            self.values[ "breakpoints" ] = self.__loadBreakpoints()
            self.values[ "watchpoints" ] = self.__loadWatchpoints()

            # Create file if does not exist
            if not os.path.exists( self.fullFileName ):
                # Save to file
                self.flushSettings()
                return

            self.__readErrors = []
            self.__config = ConfigParser.ConfigParser()

            try:
                self.__config.read( [ self.fullFileName ] )
            except:
                # Bad error - save default
                self.__config = None
                self.__saveErrors( "Bad format of settings detected. "
                                   "Overwriting the settings file..." )
                self.flushSettings()
                return

            for section in CDM_SETTINGS:
                for setting in CDM_SETTINGS[ section ]:
                    if setting.sType == CDMSetting.TYPE_INT:
                        self.values[ setting.name ] = self.__getInt(
                                section, setting.name, setting.default )
                    elif setting.sType == CDMSetting.TYPE_FLOAT:
                        self.values[ setting.name ] = self.__getFloat(
                                section, setting.name, setting.default )
                    elif setting.sType == CDMSetting.TYPE_BOOL:
                        self.values[ setting.name ] = self.__getBool(
                                section, setting.name, setting.default )
                    elif setting.sType == CDMSetting.TYPE_STR:
                        self.values[ setting.name ] = self.__getStr(
                                section, setting.name, setting.default )
                    elif setting.sType == CDMSetting.TYPE_STR_LST:
                        self.values[ section ] = self.__getStrList(
                                section, setting.name, setting.default )
                    elif setting.sType == CDMSetting.TYPE_INT_LST:
                        self.values[ setting.name ] = self.__getIntList(
                                section, setting.name, setting.default )
                    else:
                        raise Exception( "Unexpected setting type: " +
                                         str( setting.sType ) )

            # Special checks
            if len( self.values[ "hSplitterSizes" ] ) != \
                                    len( _H_SPLITTER_SIZES_DEFAULT ):
                self.__readErrors.append( "Unexpected number of values in the "
                                          "[general]/hSplitterSizes setting. "
                                          "Using default: " +
                                          str( _H_SPLITTER_SIZES_DEFAULT ) )
                self.values[ "hSplitterSizes" ] = _H_SPLITTER_SIZES_DEFAULT

            if len( self.values[ "vSplitterSizes" ] ) != \
                                    len( _V_SPLITTER_SIZES_DEFAULT ):
                self.__readErrors.append( "Unexpected number of values in the "
                                          "[general]/vSplitterSizes setting. "
                                          "Using default: " +
                                          str( _V_SPLITTER_SIZES_DEFAULT ) )
                self.values[ "vSplitterSizes" ] = _V_SPLITTER_SIZES_DEFAULT

            self.__config = None

            # If format is bad then overwrite the file
            if self.__readErrors:
                self.__saveErrors( "\n".join( self.__readErrors ) )
                self.flushSettings()
            return

        def __saveErrors( self, message ):
            fileName = settingsDir + "startupmessages.log"
            try:
                f = open( fileName, "a" )
                f.write( "------ Startup report at " +
                         str( datetime.datetime.now() ) + "\n" )
                f.write( message )
                f.write( "\n------\n\n" )
                f.close()
            except:
                pass

        def __setDefaultValues( self ):
            " Sets the default values to the members "
            for section in CDM_SETTINGS:
                for setting in CDM_SETTINGS[ section ]:
                    if setting.sType == CDMSetting.TYPE_STR_LST:
                        self.values[ section ] = setting.default
                    else:
                        self.values[ setting.name ] = setting.default
            return

        def __getInt( self, sec, key, default ):
            " Helper to read a config value "
            try:
                return self.__config.getint( sec, key )
            except:
                self.__readErrors.append( "Cannot get [" + sec + "]/" + key +
                                          " setting. Using default: " +
                                          str( default ) )
            return default

        def __getFloat( self, sec, key, default ):
            " Helper to read a config value "
            try:
                return self.__config.getfloat( sec, key )
            except:
                self.__readErrors.append( "Cannot get [" + sec + "]/" + key +
                                          " setting. Using default: " +
                                          str( default ) )
            return default

        def __getBool( self, sec, key, default ):
            " Helper to read a config value "
            try:
                return self.__config.getboolean( sec, key )
            except:
                self.__readErrors.append( "Cannot get [" + sec + "]/" + key +
                                          " setting. Using default: " +
                                          str( default ) )
            return default

        def __getStr( self, sec, key, default ):
            " Helper to read a config value "
            try:
                return self.__config.get( sec, key ).strip()
            except:
                self.__readErrors.append( "Cannot get [" + sec + "]/" + key +
                                          " setting. Using default: " +
                                          str( default ) )
            return default

        def __getIntList( self, sec, key, default ):
            " Helper to read a list of integer values "
            try:
                values = self.__config.get( sec, key ).split( ',' )
                return [ int( x ) for x in values ]
            except:
                self.__readErrors.append( "Cannot get [" + sec + "]/" + key +
                                          " setting. Using default: " +
                                          str( default ) )
            return default

        def __getStrList( self, sec, key, default ):
            " Helper to read a list of string values "
            try:
                return [ value for name, value in self.__config.items( sec )
                               if name.startswith( key ) ]
            except ConfigParser.NoSectionError:
                self.__readErrors.append( "Section [" + sec + "] is not found. "
                                          "Using default values: " +
                                          str( default ) )
            except:
                self.__readErrors.append( "Cannot get a setting from section [" +
                                          sec + "]. Using default values for "
                                          "the section: " + str( default ) )
            return default


        def flushSettings( self ):
            """ Writes all the settings into the file """

            # Save the tabs status
            self.__saveTabsStatus()
            self.__saveFindFilesHistory()
            self.__saveFindNameHistory()
            self.__saveFindFileHistory()
            self.__saveBreakpoints()
            self.__saveWatchpoints()

            f = open( self.fullFileName, "w" )
            self.__writeHeader( f )
            for section in CDM_SETTINGS:
                f.write( "\n[" + section + "]\n" )
                for setting in CDM_SETTINGS[ section ]:
                    if setting.sType in [ CDMSetting.TYPE_INT,
                                          CDMSetting.TYPE_FLOAT,
                                          CDMSetting.TYPE_BOOL,
                                          CDMSetting.TYPE_STR ]:
                        f.write( setting.name + "=" +
                                 str( self.values[ setting.name ] ) + "\n" )
                    elif setting.sType == CDMSetting.TYPE_INT_LST:
                        strVal = [ str( x ) for x in
                                            self.values[ setting.name ] ]
                        f.write( setting.name + "=" +
                                 ",".join( strVal ) + "\n" )
                    elif setting.sType == CDMSetting.TYPE_STR_LST:
                        index = 0
                        for item in self.values[ section ]:
                            f.write( setting.name + str( index ) + "=" +
                                     item + "\n" )
                            index += 1
                    else:
                        raise Exception( "Unexpected setting type: " +
                                         str( setting.sType ) )

            f.flush()
            f.close()
            self.__readErrors = []
            return

        def addRecentProject( self, projectFile ):
            " Adds the recent project to the list "
            absProjectFile = os.path.abspath( projectFile )
            recentProjects = self.values[ "recentProjects" ]

            if absProjectFile in recentProjects:
                recentProjects.remove( absProjectFile )

            recentProjects.insert( 0, absProjectFile )
            if len( recentProjects ) > _MAX_RECENT_PROJECTS:
                recentProjects = recentProjects[ 0 : _MAX_RECENT_PROJECTS ]
            self.values[ "recentProjects" ] = recentProjects
            self.flushSettings()
            self.emit( SIGNAL('recentListChanged') )
            return

        def deleteRecentProject( self, projectFile ):
            " Deletes the recent project from the list "
            absProjectFile = os.path.abspath( projectFile )
            recentProjects = self.values[ "recentProjects" ]

            if absProjectFile in recentProjects:
                recentProjects.remove( absProjectFile )
                self.values[ "recentProjects" ] = recentProjects
                self.flushSettings()
                self.emit( SIGNAL('recentListChanged') )
            return

        def addExceptionFilter( self, excptType ):
            " Adds a new exception filter "
            if excptType not in self.values[ "ignoredExceptions" ]:
                self.values[ "ignoredExceptions" ].append( excptType )
                self.flushSettings()
            return

        def deleteExceptionFilter( self, excptType ):
            " Deletes the exception filter "
            if excptType in self.values[ "ignoredExceptions" ]:
                self.values[ "ignoredExceptions" ].remove( excptType )
                self.flushSettings()
            return

        def setExceptionFilters( self, newFilters ):
            " Sets the new exception filters "
            self.values[ "ignoredExceptions" ] = newFilters
            self.flushSettings()
            return

        @staticmethod
        def __writeHeader( fileObj ):
            " Helper to write a header with a warning "
            fileObj.write( "#\n"
                           "# Generated automatically\n"
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
            if config.has_section( section):
                return [ value for name, value in config.items( section )
                               if name.startswith( listPrefix ) ]
            return []

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
                self.__writeList( f, "tabsstatus",
                                  "tab", self.values[ "tabsStatus" ] )
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

        def __loadStringSectionFromFile( self, fileName, sectionName,
                                         itemName ):
            " Loads a string section from a file "
            config = ConfigParser.ConfigParser()
            try:
                config.read( settingsDir + fileName )
            except:
                return []
            return self.__loadListSection( config, sectionName, itemName )

        def __loadFindNameHistory( self ):
            " Loads the saved find name dialog history "
            return self.__loadStringSectionFromFile( "findinfiles",
                                                     "findnamehistory", "find" )

        def __loadFindFileHistory( self ):
            " Loads the saved find file dialog history "
            return self.__loadStringSectionFromFile( "findfile",
                                                     "findfilehistory", "find" )

        def __loadBreakpoints( self ):
            " Loads the saved breakpoints "
            return self.__loadStringSectionFromFile( "breakpoints",
                                                     "breakpoints", "bpoint" )

        def __loadWatchpoints( self ):
            " Loads the saved watchpoints "
            return self.__loadStringSectionFromFile( "watchpoints",
                                                     "watchpoints", "wpoint" )

        def __saveFindFilesHistory( self ):
            " Saves the find in files dialog history "
            fName = settingsDir + "findinfiles"
            try:
                f = open( fName, "w" )
                self.__writeHeader( f )
                self.__writeList( f, "whathistory", "what",
                                  self.values[ "findFilesWhat" ] )
                self.__writeList( f, "dirhistory", "dir",
                                  self.values[ "findFilesDirs" ] )
                self.__writeList( f, "maskhistory", "mask",
                                  self.values[ "findFilesMasks" ] )
                f.close()
            except:
                # Do nothing, it's not vital important to have this file
                pass
            return

        def __saveStringSectionToFile( self, fileName, sectionName,
                                       itemName, valuesName ):
            " Saves a string section into a file "
            fName = settingsDir + fileName
            try:
                f = open( fName, "w" )
                self.__writeList( f, sectionName, itemName,
                                  self.values[ valuesName ] )
                f.close()
            except:
                # This method is for files which existance is not vitally
                # important
                pass
            return

        def __saveFindNameHistory( self ):
            " Saves the find name dialog history "
            self.__saveStringSectionToFile( "findinfiles", "findnamehistory",
                                            "find", "findNameHistory" )
            return

        def __saveFindFileHistory( self ):
            " Saves the find file dialog history "
            self.__saveStringSectionToFile( "findfile", "findfilehistory",
                                            "find", "findFileHistory" )
            return

        def __saveBreakpoints( self ):
            " Saves the breakpoints "
            self.__saveStringSectionToFile( "breakpoints", "breakpoints",
                                            "bpoint", "breakpoints" )
            return

        def __saveWatchpoints( self ):
            " Saves the watchpoints "
            self.__saveStringSectionToFile( "watchpoints", "watchpoints",
                                            "wpoint", "watchpoints" )
            return


    def __init__( self ):
        if Settings.iInstance is None:
            Settings.iInstance = Settings.Singleton()

        self.__dict__[ '_Settings__iInstance' ] = Settings.iInstance
        return

    def __getattr__( self, aAttr ):
        return self.iInstance.values[ aAttr ]

    def __setattr__( self, aAttr, aValue ):
        if self.iInstance.values[ aAttr ] != aValue:
            self.iInstance.values[ aAttr ] = aValue
            self.iInstance.flushSettings()
        return

    def addRecentProject( self, projectFile ):
        self.iInstance.addRecentProject( projectFile )
        return

    def deleteRecentProject( self, projectFile ):
        self.iInstance.deleteRecentProject( projectFile )
        return

    def addExceptionFilter( self, excptType ):
        self.iInstance.addExceptionFilter( excptType )
        return

    def deleteExceptionFilter( self, excptType ):
        self.iInstance.deleteExceptionFilter( excptType )
        return

    def flushSettings( self ):
        self.iInstance.flushSettings()
        return

    @staticmethod
    def getDefaultGeometry():
        " Provides the default window size and location "
        return _X_POS_DEFAULT, _Y_POS_DEFAULT, \
               _WIDTH_DEFAULT, _HEIGHT_DEFAULT

    def getProfilerSettings( self ):
        " Provides the profiler IDE-wide settings "
        profSettings = ProfilerSettings()
        profSettings.edgeLimit = self.iInstance.values[ "profileEdgeLimit" ]
        profSettings.nodeLimit = self.iInstance.values[ "profileNodeLimit" ]
        return profSettings

    def setProfilerSettings( self, newValues ):
        " Updates the profiler settings "
        if self.iInstance.values[ "profileEdgeLimit" ] != newValues.edgeLimit or \
           self.iInstance.values[ "profileNodeLimit" ] != newValues.nodeLimit:
            self.iInstance.values[ "profileEdgeLimit" ] = newValues.edgeLimit
            self.iInstance.values[ "profileNodeLimit" ] = newValues.nodeLimit
            self.iInstance.flushSettings()
        return

    def getDebuggerSettings( self ):
        " Provides the debugger IDE-wide settings "
        dbgSettings = DebuggerSettings()
        dbgSettings.autofork = self.iInstance.values[ "debugAutofork" ]
        dbgSettings.followChild = self.iInstance.values[ "debugFollowChild" ]
        dbgSettings.reportExceptions = self.iInstance.values[ "debugReportExceptions" ]
        dbgSettings.stopAtFirstLine = self.iInstance.values[ "debugStopAtFirstLine" ]
        dbgSettings.traceInterpreter = self.iInstance.values[ "debugTraceInterpreter" ]
        return dbgSettings

    def setDebuggerSettings( self, newValues ):
        " Updates the debugger settings "
        if self.iInstance.values[ "debugAutofork" ] != newValues.autofork or \
           self.iInstance.values[ "debugFollowChild" ] != newValues.followChild or \
           self.iInstance.values[ "debugReportExceptions" ] != newValues.reportExceptions or \
           self.iInstance.values[ "debugStopAtFirstLine" ] != newValues.stopAtFirstLine or \
           self.iInstance.values[ "debugTraceInterpreter" ] != newValues.traceInterpreter:
            self.iInstance.values[ "debugAutofork" ] = newValues.autofork
            self.iInstance.values[ "debugFollowChild" ] = newValues.followChild
            self.iInstance.values[ "debugReportExceptions" ] = newValues.reportExceptions
            self.iInstance.values[ "debugStopAtFirstLine" ] = newValues.stopAtFirstLine
            self.iInstance.values[ "debugTraceInterpreter" ] = newValues.traceInterpreter
            self.iInstance.flushSettings()
        return

