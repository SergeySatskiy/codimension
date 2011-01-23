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


_maxRecentProjects = 32
_defaultXPos = 50
_defaultYPos = 50
_defaultWidth = 750
_defaultHeight = 550
_defaultScreenWidth = 0
_defaultScreenHeight = 0
_defaultXDelta = 0
_defaultYDelta = 0
_defaultHSplitSize = "200, 550"
_defaultVSplitSize = "400, 150"
_defaultFilesFilters = [ "\.svn", "\.cvs", ".*\~$",
                         ".*\.pyc$", ".*\.swp$", ".*\.pyo$" ]
_defaultProjectLoaded = False
_defaultZoom = 0
_defaultEditorFont = ""


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
            self.basedir = os.path.normpath( str( QDir.homePath() ) ) + \
                           os.path.sep + ".codimension"

            # make sure that the directory exists
            if not os.path.exists( self.basedir ):
                os.mkdir( self.basedir )
            self.basedir += os.path.sep

            # Save the config file name
            self.fullFileName = self.basedir + "settings"

            # Load previous sessions files positions and tabs status
            self.filePositions = FilesPositions( self.basedir )
            self.tabsStatus = self.__loadTabsStatus()

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

            self.zoom = self.__getInt( config, 'general', 'zoom', _defaultZoom )
            self.xpos = self.__getInt( config, 'general', 'xpos', _defaultXPos )
            self.ypos = self.__getInt( config, 'general', 'ypos', _defaultYPos )
            self.width = self.__getInt( config, 'general', 'width',
                                        _defaultWidth )
            self.height = self.__getInt( config, 'general', 'height',
                                         _defaultHeight )
            self.xdelta = self.__getInt( config, 'general', 'xdelta',
                                         _defaultXDelta )
            self.ydelta = self.__getInt( config, 'general', 'ydelta',
                                         _defaultYDelta )
            self.screenWidth = self.__getInt( config, 'general', 'screenwidth',
                                              _defaultScreenWidth )
            self.screenHeight = self.__getInt( config, 'general',
                                               'screenheight',
                                               _defaultScreenHeight )
            self.leftBarMinimized = self.__getBool( config, 'general',
                                                    'leftBarMinimized',
                                                    False )
            self.bottomBarMinimized = self.__getBool( config, 'general',
                                                      'bottomBarMinimized',
                                                      False )
            self.projectLoaded = self.__getBool( config, 'general',
                                                 'projectLoaded',
                                                 _defaultProjectLoaded )

            asString = self.__getStr( config, 'general', 'hSplitterSizes',
                                      _defaultHSplitSize ).split( ',' )
            if len( asString ) != 2:
                asString = _defaultHSplitSize.split( ',' )
                self.formatOK = False
            self.hSplitterSizes = [ int(asString[0]), int(asString[1]) ]

            asString = self.__getStr( config, 'general', 'vSplitterSizes',
                                      _defaultVSplitSize ).split( ',' )
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
                logging.warning( "Bad format of settings detected. " \
                                 "Overwriting the settings file." )
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
            self.leftBarMinimized = False
            self.bottomBarMinimized = False
            self.hSplitterSizes = [ 200, 550 ]
            self.vSplitterSizes = [ 400, 150 ]
            self.recentProjects = []
            self.projectFilesFilters = _defaultFilesFilters
            self.projectLoaded = _defaultProjectLoaded
            return

        def __getInt( self, conf, sec, key, default ):
            " Helper to read a config value "
            try:
                return conf.getint( sec, key )
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

            # Recent projects part
            if len( self.recentProjects ) > _maxRecentProjects:
                self.recentProjects = \
                    self.recentProjects[ len(self.recentProjects) - \
                                         _maxRecentProjects : ]
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
            f.write( "[general]\n" \
                     "zoom=" + str( self.zoom ) + "\n" \
                     "xpos=" + str( self.xpos ) + "\n" \
                     "ypos=" + str( self.ypos ) + "\n" \
                     "width=" + str( self.width ) + "\n" \
                     "height=" + str( self.height ) + "\n" \
                     "screenwidth=" + str( self.screenWidth ) + "\n" \
                     "screenheight=" + str( self.screenHeight ) + "\n" \
                     "xdelta=" + str( self.xdelta ) + "\n" \
                     "ydelta=" + str( self.ydelta ) + "\n" \
                     "leftBarMinimized=" + \
                        str( int( self.leftBarMinimized ) ) + "\n" \
                     "bottomBarMinimized=" + \
                        str( int( self.bottomBarMinimized ) ) + "\n" \
                     "projectLoaded=" + \
                        str( int( self.projectLoaded ) ) + "\n" \
                     "hSplitterSizes=" + \
                        str( self.hSplitterSizes[0] ) + "," + \
                        str( self.hSplitterSizes[1] ) + "\n" \
                     "vSplitterSizes=" + \
                        str( self.vSplitterSizes[0] ) + "," + \
                        str( self.vSplitterSizes[1] ) + "\n\n" + \
                     recentPart + "\n\n" + \
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

            self.recentProjects.append( absProjectFile )
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
        def __writeHeader( fileObj ):
            " Helper to write a header with a warning "
            fileObj.write( "#\n" \
                           "# Generated automatically.\n" \
                           "# Don't edit it manually unless you " \
                           "know what you are doing.\n" \
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
                config.read( self.basedir + "tabsstatus" )
            except:
                config = None
                return []

            # tabs part
            items = self.__loadListSection( config, 'tabsstatus', 'tab' )
            config = None
            return items

        def __saveTabsStatus( self ):
            " Saves the tabs status "
            fName = self.basedir + "tabsstatus"
            try:
                f = open( fName, "w" )
                self.__writeHeader( f )
                self.__writeList( f, "tabsstatus", "tab", self.tabsStatus )
                f.close()
            except:
                # Do nothing, it's not vital important to have this file
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

