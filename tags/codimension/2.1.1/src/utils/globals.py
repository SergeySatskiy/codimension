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
# $Id: globals.py 1635 2013-07-26 02:26:44Z sergey.satskiy@gmail.com $
#

""" global data singleton """

import os, sys,  copy
from rope.base.project import Project as RopeProject
from project import CodimensionProject
from briefmodinfocache import BriefModuleInfoCache
from runparamscache import RunParametersCache
from settings import ropePreferences, settingsDir
from PyQt4.QtCore import QDir
from compatibility import relpath
from plugins.manager.pluginmanager import CDMPluginManager


# This function needs to have a rope project built smart
def getSubdirs( path, baseNamesOnly = True, excludePythonModulesDirs = True ):
    " Provides a list of sub directories for the given path "
    subdirs = []
    try:
        path = os.path.realpath( path ) + os.path.sep
        for item in os.listdir( path ):
            candidate = path + item
            if os.path.isdir( candidate ):
                if excludePythonModulesDirs:
                    modFile1 = candidate + os.path.sep + "__init__.py"
                    modFile2 = candidate + os.path.sep + "__init__.py3"
                    if os.path.exists( modFile1 ) or \
                       os.path.exists( modFile2 ):
                        continue
                if baseNamesOnly:
                    subdirs.append( item )
                else:
                    subdirs.append( candidate )
    except:
        pass
    return subdirs


class GlobalData( object ):
    """ Global data singleton """
    _iInstance = None
    class Singleton:
        """ Provides singleton facility """

        def __init__( self ):
            self.application = None
            self.splash = None
            self.mainWindow = None
            self.skin = None
            self.screenWidth = 0
            self.screenHeight = 0
            self.version = "unknown"
            self.project = CodimensionProject()

            self.pluginManager = CDMPluginManager()

            self.briefModinfoCache = BriefModuleInfoCache()
            self.runParamsCache = RunParametersCache()
            if os.path.isfile( settingsDir + "runparamscache" ):
                self.runParamsCache.deserialize( settingsDir +
                                                 "runparamscache" )

            self.magicAvailable = self.__checkMagic()
            self.pylintAvailable = self.__checkPylint()
            self.graphvizAvailable = self.__checkGraphviz()
            return

        def getRunParameters( self, fileName ):
            " Provides the run parameters "
            if self.project.isLoaded():
                if self.project.isProjectFile( fileName ):
                    key = relpath( fileName,
                                   os.path.dirname( self.project.fileName ) )
                else:
                    key = fileName
                return self.project.runParamsCache.get( key )

            # No project loaded
            return self.runParamsCache.get( fileName )

        def addRunParams( self, fileName, params ):
            " Registers new latest run parameters "
            if self.project.isLoaded():
                if self.project.isProjectFile( fileName ):
                    key = relpath( fileName,
                                   os.path.dirname( self.project.fileName ) )
                else:
                    key = fileName
                self.project.runParamsCache.add( key, params )
                self.project.serializeRunParameters()
                return

            # No project loaded
            self.runParamsCache.add( fileName, params )
            self.runParamsCache.serialize( settingsDir + "runparamscache" )
            return

        def getProfileOutputPath( self ):
            " Provides the path to the profile output file "
            if self.project.isLoaded():
                return self.project.userProjectDir + "profile.out"

            # No project loaded
            return settingsDir + "profile.out"

        def getRopeProject( self, fileName = "" ):
            " Provides existed or creates a new rope project "
            if self.project.isLoaded():
                return self.project.getRopeProject()

            # There is no current project so create a temporary one.
            # Two cases: the buffer has been saved
            #            not saved buffer
            if os.path.isabs( fileName ):
                dirName = os.path.dirname( fileName )
            else:
                # Unsaved buffer, make an assumption that
                # it is in home directory
                dirName = str( QDir.homePath() )

            prefs = copy.deepcopy( ropePreferences )

            # Exclude nested dirs as it could take too long
            # Get only dir names and do not get those dirs
            # where __init__.py[3] are present
            subdirsToExclude = getSubdirs( dirName, True, True )

            if "ignored_resources" in prefs:
                prefs[ "ignored_resources" ] += subdirsToExclude
            else:
                prefs[ "ignored_resources" ] = subdirsToExclude

            project = RopeProject( dirName, None, None, **prefs )
            project.validate( project.root )
            return project

        def validateRopeProject( self, fileName = "" ):
            " Validates the existed rope project if so "
            if not self.project.isLoaded():
                return

            # Currently rope supports validating of directories only
            # There is a hope that it will support validating a single file
            # one day. So the fileName argument is ignored by now and the whole
            # project is invalidated.
            if fileName != "":
                if not fileName.endswith( ".py" ) and \
                   not fileName.endswith( ".py3" ) and \
                   not fileName.endswith( ".pyw" ):
                    return
            self.project.validateRopeProject( fileName )
            return

        def getProjectImportDirs( self ):
            """ Provides a list of the project import dirs if so.
                Note: the paths do not have '/' at the end due to
                os.path.normpath """
            if not self.project.isLoaded():
                return []

            basePath = self.project.getProjectDir()
            result = list( self.project.importDirs )
            index = len( result ) - 1
            while index >= 0:
                path = result[ index ]
                if not os.path.isabs( path ):
                    result[ index ] = os.path.normpath( basePath + path )
                index -= 1
            return result

        def isProjectScriptValid( self ):
            " True if the project script valid "
            scriptName = self.project.getProjectScript()
            if not os.path.exists( scriptName ):
                return False
            scriptName = os.path.realpath( scriptName )
            if not os.path.isfile( scriptName ):
                return False
            if scriptName.endswith( ".py" ) or \
               scriptName.endswith( ".py3" ) or \
               scriptName.endswith( ".pyw" ):
                return True
            return False

        def getFileLineDocstring( self, fName, line ):
            " Provides a docstring if so for the given file and line "
            if not ( fName.endswith( '.py' ) or
                     fName.endswith( '.py3' ) or
                     fName.endswith( '.pyw' ) ):
                return ""

            if self.project.isLoaded():
                infoCache = self.project.briefModinfoCache
            else:
                infoCache = self.briefModinfoCache

            def checkFuncObject( obj, line ):
                " Checks docstring for a function or a class "
                if obj.line == line or obj.keywordLine == line:
                    if obj.docstring is None:
                        return True, ""
                    return True, obj.docstring.text
                for item in obj.classes + obj.functions:
                    found, docstring = checkFuncObject( item, line )
                    if found:
                        return True, docstring
                return False, ""

            try:
                info = infoCache.get( fName )
                for item in info.classes + info.functions:
                    found, docstring = checkFuncObject( item, line )
                    if found:
                        return docstring
            except:
                pass
            return ""

        def getModInfo( self, path ):
            " Provides a module info for the given file "
            if not ( path.endswith( '.py' ) or
                     path.endswith( '.py3' ) or
                     path.endswith( '.pyw' ) ):
                raise Exception( "Trying to parse non-python file: " + path +
                                 ". Expected extensions .py or .py3 or .pyw" )

            if self.project.isLoaded():
                return self.project.briefModinfoCache.get( path )
            return self.briefModinfoCache.get( path )

        @staticmethod
        def __checkMagic():
            " Checks if the magic module is able to be loaded "

            try:
                import magic
                m = magic.Magic()
                m.close()
                return True
            except:
                return False

        @staticmethod
        def __checkGraphviz():
            " Checks if the graphviz available "

            if 'win' in sys.platform.lower():
                return os.system( 'which dot > /NUL 2>&1' ) == 0
            return os.system( 'which dot > /dev/null 2>&1' ) == 0

        @staticmethod
        def __checkPylint():
            " Checks if pylint is available "

            if 'win' in sys.platform.lower():
                return os.system( 'which pylint > /NUL 2>&1' ) == 0
            return os.system( 'which pylint > /dev/null 2>&1' ) == 0


    def __init__( self ):
        if GlobalData._iInstance is None:
            GlobalData._iInstance = GlobalData.Singleton()
        self.__dict__[ '_GlobalData__iInstance' ] = GlobalData._iInstance
        return

    def __getattr__( self, aAttr ):
        return getattr( self._iInstance, aAttr )

    def __setattr__( self, aAttr, aValue ):
        setattr( self._iInstance, aAttr, aValue )
        return

