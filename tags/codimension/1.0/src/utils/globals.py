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
from project            import CodimensionProject
from briefmodinfocache  import BriefModuleInfoCache


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

            self.fileAvailable = self.__checkFile()
            self.doxygenAvailable = self.__checkDoxygen()
            self.pylintAvailable = self.__checkPylint()
            self.graphvizAvailable = self.__checkGraphviz()
            return

        @staticmethod
        def __checkFile():
            " Checks if the file utility available "

            if 'win' in sys.platform.lower():
                return os.system( 'which file > /NUL 2>&1' ) == 0
            return os.system( 'which file > /dev/null 2>&1' ) == 0

        @staticmethod
        def __checkDoxygen():
            " Checks if the doxygen available "

            if 'win' in sys.platform.lower():
                return os.system( 'which doxygen > /NUL 2>&1' ) == 0
            return os.system( 'which doxygen > /dev/null 2>&1' ) == 0

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

