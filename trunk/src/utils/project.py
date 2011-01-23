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


""" codimension project """

import os, os.path, ConfigParser, logging, uuid, re
from briefmodinfocache import BriefModuleInfoCache
from PyQt4.QtCore      import QObject, SIGNAL
from settings          import Settings
from watcher           import Watcher



class CodimensionProject( QObject ):
    " Provides codimension project singleton facility "

    # Constants for the projectChanged signal
    CompleteProject = 0     # It is a completely new project
    Properties      = 1     # Project properties were updated

    def __init__( self ):
        QObject.__init__( self )

        self.__dirWatcher = None
        self.__formatOK = True

        # Avoid pylint complains
        self.fileName = ""
        self.userProjectDir = ""
        self.__dirList = set()
        self.filesList = set()

        self.creationDate = ""
        self.author = ""
        self.license = ""
        self.copyright = ""
        self.version = ""
        self.email = ""
        self.description = ""
        self.uuid = ""

        # Coming from separate files from ~/.codimension/uuidN/
        self.todos = []
        self.bookmarks = []
        self.briefModinfoCache = BriefModuleInfoCache()
        self.topLevelDirs = []
        self.findHistory = []
        self.replaceHistory = []
        self.replaceWhatHistory = []
        self.tabsStatus = []

        # Precompile the exclude filters
        self.__excludeFilter = []
        for flt in Settings().projectFilesFilters:
            self.__excludeFilter.append( re.compile( flt ) )

        return

    def shouldExclude( self, name ):
        " Tests if a file must be excluded "
        for excl in self.__excludeFilter:
            if excl.match( name ):
                return True
        return False

    def __resetValues( self ):
        """ Initializes or resets all the project members """

        # Empty file name means that the project has not been loaded or
        # created. This must be an absolute path.
        self.fileName = ""
        self.userProjectDir = ""
        self.__dirList = set()

        # Generated having the self.__dirList. Full paths are stored.
        # The holds all files and directories. The dirs end with os.path.sep
        self.filesList = set()

        self.creationDate = ""
        self.author = ""
        self.license = ""
        self.copyright = ""
        self.version = ""
        self.email = ""
        self.description = ""
        self.uuid = ""

        # Coming from separate files from ~/.codimension/uuidN/
        self.todos = []
        self.bookmarks = []
        self.briefModinfoCache = BriefModuleInfoCache()
        self.topLevelDirs = []
        self.findHistory = []
        self.replaceHistory = []
        self.replaceWhatHistory = []
        self.tabsStatus = []

        # Reset the dir watchers if so
        if self.__dirWatcher is not None:
            del self.__dirWatcher
        self.__dirWatcher = None
        return

    def createNew( self, fileName, author, lic, copyRight,
                   description, creationDate, version, email ):
        " Creates a new project "

        # Try to create the user project directory
        projectUuid = str( uuid.uuid1() )
        userProjectDir = Settings().basedir + projectUuid + os.path.sep
        if not os.path.exists( userProjectDir ):
            try:
                os.mkdir( userProjectDir )
            except:
                logging.error( "Cannot create user project directory: " + \
                               self.userProjectDir + ". Please check the " \
                               "available disk space and re-create the " \
                               "project." )
                raise
        else:
            logging.warning( "The user project directory existed! " \
                             "The content will be overwritten." )
            self.__removeProjectFiles( userProjectDir )

        # Basic pre-requisites are met. We can reset the current project
        self.__resetValues()

        self.fileName = str( fileName )
        self.__dirList.update( [ "." + os.path.sep ] )
        self.creationDate = creationDate
        self.author = author
        self.license = lic
        self.copyright = copyRight
        self.version = version
        self.email = email
        self.description = description
        self.uuid = projectUuid
        self.userProjectDir = userProjectDir

        self.__createProjectFile()  # ~/.codimension/uuidNN/project

        self.__generateFilesList()
        self.__updateModinfoCache()

        self.saveProject()

        # Update the watcher
        self.__dirWatcher = Watcher( Settings().projectFilesFilters,
                                     self.getProjectDirs()  )
        self.connect( self.__dirWatcher, SIGNAL( 'fsCahanged' ),
                      self.onFSChanged )

        self.emit( SIGNAL( 'projectChanged' ), self.CompleteProject )
        return

    @staticmethod
    def __safeRemove( path ):
        " Safe file removal "
        try:
            os.remove( path )
        except:
            return

    def __removeProjectFiles( self, userProjectDir ):
        " Removes user project files "

        self.__safeRemove( userProjectDir + "project" )
        self.__safeRemove( userProjectDir + "bookmarks" )
        self.__safeRemove( userProjectDir + "todos" )
        self.__safeRemove( userProjectDir + "briefinfocache" )
        self.__safeRemove( userProjectDir + "searchhistory" )
        self.__safeRemove( userProjectDir + "topleveldirs" )
        self.__safeRemove( userProjectDir + "tabsstatus" )
        return

    def __createProjectFile( self ):
        " Helper function to create the user project file "
        try:
            f = open( self.userProjectDir + "project", "w" )
            f.write( self.fileName )
            f.close()
        except:
            return

    def __updateModinfoCache( self ):
        " Helper to hit each cache item "
        for item in self.filesList:
            if item.endswith( '.py' ) or item.endswith( '.py3' ):
                self.briefModinfoCache.get( item )
        return

    def saveProject( self ):
        " Writes all the settings into the file "
        if self.fileName == "":
            return

        # Project properties part
        propertiesPart = "[properties]\n" \
                         "creationdate=" + self.creationDate + "\n" \
                         "author=" + self.author + "\n" \
                         "license=" + self.license + "\n" \
                         "copyright=" + self.copyright + "\n" \
                         "description=" + \
                            self.description.replace( '\n', '<CR><LF>' ) + \
                            "\n" \
                         "version=" + self.version + "\n" \
                         "email=" + self.email + "\n" \
                         "uuid=" + self.uuid + "\n"

        f = open( self.fileName, "w" )
        self.__writeHeader( f )
        self.__writeList( f, "dirs", "dir", self.__dirList )
        f.write( propertiesPart + "\n" + \
                 "\n\n" )
        f.close()

        # Save brief cache
        self.briefModinfoCache.serialize( self.userProjectDir + \
                                          "briefinfocache" )
        self.__saveTopLevelDirs()
        self.__saveSearchHistory()
        self.__saveTabsStatus()

        self.__formatOK = True
        return

    def __saveTabsStatus( self ):
        " Helper to save tabs status "
        if self.fileName == "":
            return
        f = open( self.userProjectDir + "tabsstatus", "w" )
        self.__writeHeader( f )
        self.__writeList( f, "tabsstatus", "tab", self.tabsStatus )
        f.close()
        return

    def __saveSearchHistory( self ):
        " Helper to save the project search history "
        if self.fileName == "":
            return
        f = open( self.userProjectDir + "searchhistory", "w" )
        self.__writeHeader( f )
        self.__writeList( f, "findhistory", "find", self.findHistory )
        self.__writeList( f, "replacewhathistory", "replacewhat",
                             self.replaceWhatHistory )
        self.__writeList( f, "replacehistory", "replace", self.replaceHistory )
        f.close()
        return

    def __saveTopLevelDirs( self ):
        " Helper to save the project top level dirs "
        if self.fileName == "":
            return
        f = open( self.userProjectDir + "topleveldirs", "w" )
        self.__writeHeader( f )
        self.__writeList( f, "topleveldirs", "dir", self.topLevelDirs )
        f.close()
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

    def __getStr( self, conf, sec, key, default ):
        " Helper to read a config value "
        try:
            return conf.get( sec, key ).strip()
        except:
            self.__formatOK = False
        return default

    def loadProject( self, projectFile ):
        """ Loads a project from the given file """

        absPath = os.path.abspath( projectFile )
        if not os.path.exists( absPath ):
            raise Exception( "Cannot open project file " + projectFile )
        if not absPath.endswith( ".cdm" ):
            raise Exception( "Unexpected project file extension. " \
                             "Expected: .cdm" )

        config = ConfigParser.ConfigParser()

        try:
            config.read( absPath )
        except:
            # Bad error - cannot load project file at all
            config = None
            raise Exception( "Bad project file" )


        self.__resetValues()
        self.fileName = str( absPath )

        # Properties part
        self.creationDate = self.__getStr( config, 'properties',
                                                   'creationdate', '' )
        self.author = self.__getStr( config, 'properties', 'author', '' )
        self.license = self.__getStr( config, 'properties', 'license', '' )
        self.copyright = self.__getStr( config, 'properties', 'copyright', '' )
        self.description = self.__getStr( config, 'properties', 'description',
                                          '' ).replace( '<CR><LF>', '\n' )
        self.version = self.__getStr( config, 'properties', 'version', '' )
        self.email = self.__getStr( config, 'properties', 'email', '' )
        self.uuid = self.__getStr( config, 'properties', 'uuid', '' )
        if self.uuid == "":
            logging.error( "Project file does not have UUID. " \
                           "Re-generate it..." )
            self.uuid = str( uuid.uuid1() )
        self.userProjectDir = Settings().basedir + self.uuid + os.path.sep
        if not os.path.exists( self.userProjectDir ):
            os.mkdir( self.userProjectDir )

        # dirs part
        index = 0
        try:
            while True:
                dirName = config.get( 'dirs',
                                      'dir' + str(index) ).strip()
                index += 1
                absPath = self.__makeAbsolute( dirName )
                if not os.path.exists( absPath ):
                    logging.error( "Codimension project: cannot find " \
                                   "project directory: " + dirName )
                elif not os.path.isdir( absPath ):
                    logging.error( "Codimension project: the item: " + \
                                   dirName + \
                                   " is not a directory. Ignoring..." )
                    continue
                self.__dirList.update( [ dirName ] )

        except ConfigParser.NoSectionError:
            self.__formatOK = False
        except ConfigParser.NoOptionError:
            # Just continue
            pass
        except:
            self.__formatOK = False

        config = None

        if not '.' + os.path.sep in self.__dirList:
            self.__dirList.update( [ '.' + os.path.sep ] )

        # Read the other config files
        self.__loadTopLevelDirs()
        self.__loadSearchHistory()
        self.__loadTabsStatus()

        # The project might have been moved...
        self.__createProjectFile()  # ~/.codimension/uuidNN/project
        self.__generateFilesList()

        if os.path.exists( self.userProjectDir + "briefinfocache" ):
            self.briefModinfoCache.deserialize( self.userProjectDir + \
                                                "briefinfocache" )

        # Get each file info as it could be out of date
        self.__updateModinfoCache()

        if not self.__formatOK:
            logging.warning( "Bad project file format detected. " \
                             "Overwriting the project files." )
            self.saveProject()

        # Update the recent list
        Settings().addRecentProject( self.fileName )

        # Setup the new watcher
        self.__dirWatcher = Watcher( Settings().projectFilesFilters,
                                     self.getProjectDirs() )
        self.connect( self.__dirWatcher, SIGNAL( 'fsCahanged' ),
                      self.onFSChanged )

        self.emit( SIGNAL( 'projectChanged' ), self.CompleteProject )
        return

    def onFSChanged( self, items ):
        " Triggered when the watcher detects changes "
        report = "REPORT: "
        for item in items:
            item = str( item )
            report += " " + item
            try:
                if item.startswith( '+' ):
                    self.filesList.update( [ item[ 1: ] ] )
                else:
                    self.filesList.remove( item[ 1: ] )
            except:
                print "EXCEPTION for '" + item + "'"
                pass
        print "'" + report + "'"
        self.emit( SIGNAL( 'fsChanged' ), items )
        self.__dirWatcher.debug()
        return

    def __loadTabsStatus( self ):
        " Loads the last tabs status "
        configFile = self.userProjectDir + "tabsstatus"
        if not os.path.exists( configFile ):
            logging.warning( "Cannot find tabsstatus project file. " \
                             "Expected here: " + configFile )
            self.__formatOK = False
            return

        config = ConfigParser.ConfigParser()
        try:
            config.read( configFile )
        except:
            # Bad error - cannot load project file at all
            config = None
            self.__formatOK = False
            logging.warning( "Cannot read tabsstatus project file " \
                             "from here: " + configFile )
            return

        # tabs part
        self.tabsStatus = self.__loadListSection( \
                config, 'tabsstatus', 'tab' )

        config = None
        return

    def __loadTopLevelDirs( self ):
        " Loads the top level dirs "
        configFile = self.userProjectDir + "topleveldirs"
        if not os.path.exists( configFile ):
            logging.warning( "Cannot find topleveldirs project file. " \
                             "Expected here: " + configFile )
            self.__formatOK = False
            return

        config = ConfigParser.ConfigParser()
        try:
            config.read( configFile )
        except:
            # Bad error - cannot load project file at all
            config = None
            self.__formatOK = False
            logging.warning( "Cannot read topleveldirs project file " \
                             "from here: " + configFile )
            return

        # dirs part
        self.topLevelDirs = self.__loadListSection( \
                config, 'topleveldirs', 'dir' )

        config = None
        return

    def __loadSearchHistory( self ):
        " Load the search history file content "
        confFile = self.userProjectDir + "searchhistory"
        if not os.path.exists( confFile ):
            logging.warning( "Cannot find searchhistory project file. " \
                             "Expected here: " + confFile )
            self.__formatOK = False
            return

        config = ConfigParser.ConfigParser()
        try:
            config.read( confFile )
        except:
            # Bad error - cannot load project file at all
            config = None
            self.__formatOK = False
            logging.warning( "Cannot read searchhistory project file " \
                             "from here: " + confFile )
            return

        # find part
        self.findHistory = self.__loadListSection( \
                config, 'findhistory', 'find' )

        # replace part
        self.replaceHistory = self.__loadListSection( \
                config, 'replacehistory', 'replace' )

        # replace what part
        self.replaceWhatHistory = self.__loadListSection( \
                config, 'replacewhathistory', 'replacewhat' )
        config = None
        return

    def __loadListSection( self, config, section, listPrefix ):
        " Loads a list off the given section from the given file "
        items = []
        index = 0
        try:
            while True:
                item = config.get( section, listPrefix + str(index) ).strip()
                index += 1
                items.append( item )
        except ConfigParser.NoSectionError:
            self.__formatOK = False
        except ConfigParser.NoOptionError:
            pass    # Just continue
        except:
            self.__formatOK = False
        return items

    def unloadProject( self ):
        """ Unloads the current project if required """
        self.__resetValues()
        self.emit( SIGNAL( 'projectChanged' ), self.CompleteProject )
        return

    def addProjectDir( self, dirPath ):
        " Adds the directory to the project "
        if self.fileName == "":
            return

        # Absolute path is expected
        if not os.path.exists( dirPath ):
            logging.error( "Codimension project: cannot find " \
                           "directory: " + dirPath )
            return
        if not os.path.isdir( dirPath ):
            logging.error( "Codimension project: " + dirPath + \
                           " is not a directory" )
            return

        if self.isProjectDir( dirPath ):
            logging.debug( "The path " + dirPath + \
                           " already belongs to the project. Skipping..." )
            return

        if not dirPath.endswith( os.path.sep ):
            dirPath += os.path.sep

        # Check that it covers the existed paths
        coveredDir = self.doesDirCoverProjectDir( dirPath )
        while coveredDir != "":
            # This path is covered by new - remove it
            logging.debug( "The dir " + dirPath + \
                           " covers project dir: " + \
                           coveredDir + \
                           ". Remove the covered dir." )
            self.__dirList.remove( coveredDir )
            self.__dirWatcher.deregiserDir( self.__makeAbsolute( coveredDir ) )
            coveredDir = self.doesDirCoverProjectDir( dirPath )

        # Calc the relative path and insert it
        relativePath = os.path.relpath( dirPath,
                                        os.path.dirname( self.fileName ) )
        if not relativePath.endswith( os.path.sep ):
            relativePath += os.path.sep
        self.__dirList.update( [ relativePath ] )
        self.__dirWatcher.registerDir( dirPath )

        self.saveProject()
        self.emit( SIGNAL('projectChanged'), self.CompleteProject )
        return

    def doesDirCoverProjectDir( self, path ):
        " returns  of the covered directory or -1 if none are covered "
        " Returns the name of the covered dir or an empty string "
        for item in self.__dirList:
            if self.__makeAbsolute( item ).startswith( path ):
                return item
        return ""

    def removeProjectDir( self, dirPath ):
        """ Removes the directory from the project """
        if self.fileName == "":
            return

        # It is possible that a disappeared from the file system directory is
        # to be removed from the project
        # if not os.path.exists( dirPath ):
        #     return

        # Absolute path is expected
        # Calc the relative path and insert it
        relativePath = os.path.relpath( dirPath,
                                        os.path.dirname( self.fileName ) )
        if not relativePath.endswith( os.path.sep ):
            relativePath += os.path.sep

        if not relativePath in self.__dirList:
            return

        self.__dirList.remove( relativePath )
        self.__dirWatcher.deregisterDir( dirPath )
        self.saveProject()
        self.emit( SIGNAL('projectChanged'), self.CompleteProject )
        return

    def __generateFilesList( self ):
        """ Generates the files list having the list of dirs """
        self.filesList = set()
        for path in self.__dirList:
            path = self.__makeAbsolute( path )
            if os.path.exists( path ):
                self.filesList.update( [ path ] )
                self.__scanDir( path )
        return

    def __scanDir( self, path ):
        """ Recursive function to scan one dir """
        # The path is with '/' at the end
        for item in os.listdir( path ):
            if self.shouldExclude( item ):
                continue

            # Exclude symlinks if they point to the other project
            # covered pieces
            if os.path.islink( path + item ):
                realItem = os.path.realpath( path + item )
                if os.path.isdir( realItem ):
                    if self.isProjectDir( realItem ):
                        continue
                else:
                    if self.isProjectDir( os.path.dirname( realItem ) ):
                        continue

            if os.path.isdir( path + item ):
                self.filesList.update( [ path + item + os.path.sep ] )
                self.__scanDir( path + item + os.path.sep )
                continue
            self.filesList.update( [ path + item ] )
        return

    def __makeAbsolute( self, path ):
        " Returns absolute path for the relative path "
        return os.path.normpath( os.path.dirname( self.fileName ) + \
                                 os.path.sep + path ) + os.path.sep

    def isProjectDir( self, path ):
        " Returns True if the path belongs to the project "
        path = os.path.realpath( path )     # it could be a symlink
        if not path.endswith( os.path.sep ):
            path += os.path.sep

        for item in self.__dirList:
            # It could be that a nested project dir is given
            if path.startswith( self.__makeAbsolute( item ) ):
                return True

    def isProjectFile( self, path ):
        " Returns True if the path belongs to the project "
        return self.isProjectDir( os.path.dirname( path ) )

    def isTopLevelDir( self, path ):
        " Checks if the path is a top level dir "
        if not path.endswith( os.path.sep ):
            path += os.path.sep
        return path in self.topLevelDirs

    def addTopLevelDir( self, path ):
        " Adds the path to the top level dirs list "
        if not path.endswith( os.path.sep ):
            path += os.path.sep
        if path in self.topLevelDirs:
            logging.warning( "Top level dir " + path + \
                             " is already in the list of dirs. " \
                             "Ignore adding..." )
            return
        self.topLevelDirs.append( path )
        self.__saveTopLevelDirs()
        return

    def removeTopLevelDir( self, path ):
        " Removes the path from the top level dirs list "
        if not path.endswith( os.path.sep ):
            path += os.path.sep
        if path not in self.topLevelDirs:
            logging.warning( "Top level dir " + path + \
                             " is not in the list of dirs. Ignore removing..." )
            return
        self.topLevelDirs.remove( path )
        self.__saveTopLevelDirs()
        return

    def setFindHistory( self, history ):
        " Sets the new find history and save it into a file "
        self.findHistory = history
        self.__saveSearchHistory()
        return

    def setReplaceHistory( self, whatHistory, toHistory ):
        " Sets the new replace history and save it into a file "
        self.replaceWhatHistory = whatHistory
        self.replaceHistory = toHistory
        self.__saveSearchHistory()
        return

    def setTabsStatus( self, status ):
        " Sets the new tabs status and save it into a file "
        self.tabsStatus = status
        self.__saveTabsStatus()
        return

    def updateProperties( self, creationDate, author,
                          lic, copy_right, version,
                          email, description ):
        " Updates the project properties "

        if self.creationDate == creationDate and \
           self.author == author and \
           self.license == lic and \
           self.copyright == copy_right and \
           self.version == version and \
           self.email == email and \
           self.description == description:
            # No real changes
            return

        self.creationDate = creationDate
        self.author = author
        self.license = lic
        self.copyright = copy_right
        self.version = version
        self.email = email
        self.description = description
        self.saveProject()
        self.emit( SIGNAL( 'projectChanged' ), self.Properties )
        return

    def getProjectDirs( self ):
        " Provides a list of absolute project paths "
        result = []
        for path in self.__dirList:
            result.append( self.__makeAbsolute( path ) )
        return result


def getProjectProperties( projectFile ):
    """ Provides project properties or throws an exception """

    def readValue( conf, sec, key ):
        " Helper function for try block "
        try:
            return conf.get( sec, key ).strip()
        except:
            return ""

    absPath = os.path.abspath( projectFile )
    if not os.path.exists( absPath ):
        raise Exception( "Cannot find project file " + projectFile )

    config = ConfigParser.ConfigParser()
    config.read( absPath )

    # We are interested in properties only
    creationDate = readValue( config, 'properties', 'creationdate' )
    author = readValue( config, 'properties', 'author' )
    lic = readValue( config, 'properties', 'license' )
    copy_right = readValue( config, 'properties', 'copyright' )
    description = readValue( config, 'properties',
                             'description' ).replace( '<CR><LF>', '\n' )
    version = readValue( config, 'properties', 'version' )
    email = readValue( config, 'properties', 'email' )

    config = None

    return creationDate, author, lic, copy_right, description, version, email

