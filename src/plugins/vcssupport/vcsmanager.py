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
from utils.globals import GlobalData
from indicator import VCSIndicator
from utils.project import CodimensionProject
from PyQt4.QtCore import QObject, SIGNAL
from vcspluginthread import VCSPluginThread


class VCSPluginDescriptor:
    " Holds information about a single active plugin "

    def __init__( self, plugin ):
        self.plugin = plugin
        self.thread = None                  # VCSPluginThread
        self.indicators = None              # ID -> VCSIndicator

        self.__getPluginIndicators()
        self.thread = VCSPluginThread( plugin )
        self.thread.start()
        return

    def stopThread( self ):
        " Stops the plugin thread synchronously "
        self.thread.stop()  # Sends request
        self.thread.wait()  # Joins the thread
        return

    def requestStatus( self, path, urgent = False ):
        " Requests the item status asynchronously "
        self.thread.addRequest( path, urgent )
        return

    def __getPluginIndicators( self ):
        " Retrieves indicators from the plugin "
        return



class VCSManager( QObject ):
    " Manages the VCS plugins "

    def __init__( self ):
        QObject.__init__( self )

        self.dirCache = VCSStatusCache()    # Path -> VCSStatus
        self.fileCache = VCSStatusCache()   # Path -> VCSStatus
        self.activePlugins = {}             # Plugin ID -> VCSPluginDescriptor
        self.systemIndicators = {}          # ID -> VCSIndicator

        self.__firstFreeIndex = 0

        self.__readSettingsIndicators()

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( GlobalData().pluginManager, SIGNAL( 'PluginActivated' ),
                      self.__onPluginActivated )

        # Plugin deactivation must be done via dismissPlugin(...)
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

    def __onPluginActivated( self, plugin ):
        " Triggered when a plugin is activated "
        if plugin.categoryName != "VersionControlSystemInterface":
            return

        newPluginIndex = self.__getNewPluginIndex()
        self.activePlugins[ newPluginIndex ] = VCSPluginDescriptor( plugin )
        return


    def __populateProjectDirectories( self ):
        " Populates the project directories in the dirCache "
        pass

    def __onProjectChanged( self, what ):
        " Triggered when a project has changed "
        if what == CodimensionProject.CompleteProject:
            pass



    def dismissAllPlugins( self ):
        " Stops all the plugin threads "
        for identifier, descriptor in self.activePlugins.iteritems():
            descriptor.stopThread()
        return

    def dismissPlugin( self, plugin ):
        " Stops the plugin thread and cleans the plugin data "
        pass

    def requestStatus( self, path ):
        " Provides the path status asynchronously via sending a signal"
        pass

    def setLocallyModified( self, path ):
        " Sets the item status as locally modified "
        pass

