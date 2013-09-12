#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

"""
VCS plugin support: manager to keep track of the VCS plugins and file status
"""

from statuscache import VCSStatusCache
from utils.settings import Settings
from indicator import VCSIndicator


class VCSPluginDescriptor:
    " Holds information about a single active plugin "

    def __init__( self ):
        self.pluginName = None
        self.thread = None                  # VCS plugin service thread
        self.indicators = None              # ID -> VCSIndicator
        return



class VCSManager:
    " Manages the VCS plugins "

    def __init__( self ):
        self.dirCache = VCSStatusCache()    # Path -> VCSStatus
        self.fileCache = VCSStatusCache()   # Path -> VCSStatus
        self.activePlugins = {}             # Plugin ID -> VCSPluginDescriptor
        self.systemIndicators = {}          # ID -> VCSIndicator

        self.__firstFreeIndex = 0

        self.__readSettingsIndicators()
        return

    def __getNewPluginIndex( self ):
        " Provides a new plugin index "
        index = self.__firstFreeIndex
        self.__firstFreeIndex += 1
        return index

    def __readSettingsIndicators( self ):
        " Reads the system indicators "
        for indicLine in Settings().vcsindicators:
            indicator = VCSIndicator( indicLine )
            self.systemIndicators[ indicator.identifier ] = indicator
        return

