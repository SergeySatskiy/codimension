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

""" global data singleton """

import os, sys
import rope.base.project
from project            import CodimensionProject
from briefmodinfocache  import BriefModuleInfoCache
from runparamscache     import RunParametersCache
from settings           import ropePreferences, settingsDir
from PyQt4.QtCore       import QDir
from compatibility      import relpath


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
            self.briefModinfoCache = BriefModuleInfoCache()
            self.runParamsCache = RunParametersCache()
            if os.path.isfile( settingsDir + "runparamscache" ):
                self.runParamsCache.deserialize( settingsDir + \
                                                 "runparamscache" )

            self.fileAvailable = self.__checkFile()
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
                project = rope.base.project.Project( os.path.dirname(fileName),
                                                     None, None,
                                                     **ropePreferences )
                project.validate( project.root )
                return project

            # Unsaved buffer, make an assumption that it is in home directory
            project = rope.base.project.Project( str( QDir.homePath() ),
                                                 None, None,
                                                 **ropePreferences )
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
                   not fileName.endswith( ".py3" ):
                    return
            self.project.validateRopeProject( fileName )
            return

        def getProjectImportDirs( self ):
            " Provides a list of the project import dirs if so "
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
            if not scriptName.endswith( ".py" ) and \
               not scriptName.endswith( ".py3" ):
                return False
            return True

        @staticmethod
        def __checkFile():
            " Checks if the file utility available "

            if 'win' in sys.platform.lower():
                return os.system( 'which file > /NUL 2>&1' ) == 0
            return os.system( 'which file > /dev/null 2>&1' ) == 0

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

