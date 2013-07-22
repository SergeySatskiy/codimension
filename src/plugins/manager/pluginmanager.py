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

import logging
from yapsy.PluginManager import PluginManager
from utils.settings import settingsDir, Settings

# List of the supported plugin categories, i.e. base class names
CATEGORIES = [ "VersionControlSystemInterface" ]



class CDMPluginManager( PluginManager ):
    " Implements the codimension plugin manager "

    NO_CONFLICT = 0
    SYSTEM_USER_CONFLICT = 1                # Same name plugin in system and user locations
    INCOMPATIBLE_IDE_VERSION_CONFLICT = 2   # Plugin required incompatible version
    VERSION_CONFLICT = 3                    # Newer version of the same name plugin
    ACTIVATE_CONFLICT = 4                   # Exception on activation
    BAD_BASE_CLASS = 5                      # Does not derive from any supported interface
    BAD_ACTIVATION = 6                      # The plugin raised exception during activation
    BAD_INTERFACE = 7                       # Exception on basic methods
    USER_DISABLED = 8

    def __init__( self ):
        PluginManager.__init__( self, None,
                                [ settingsDir + "plugins",
                                  "/usr/share/codimension-plugins" ],
                                "cdmp" )

        self.inactivePlugins = {}   # Categorized inactive plugins
        self.activePlugins = {}     # Categorized active plugins
        self.unknownPlugins = []    # Unknown plugins
        return

    def load( self ):
        " Loads the found plugins "
        # Now, let's check the plugins. They must be of known category.
        collectedPlugins = self.__collect()
        self.__applyDisabledPlugins( collectedPlugins )

        self.__checkIDECompatibility( collectedPlugins )
        self.__sysVsUserConflicts( collectedPlugins )
        self.__categoryConflicts( collectedPlugins )
        self.__activatePlugins( collectedPlugins )

        self.__saveDisabledPlugins()
        return

    def __collect( self ):
        " Checks that the plugins belong to what is known "
        self.locatePlugins()
        self.collectPlugins()

        collectedPlugins = {}
        for plugin in self.getAllPlugins():
            recognised = False
            baseClasses = getBaseClassNames( plugin.plugin_object )
            for category in CATEGORIES:
                if category in baseClasses:
                    # OK, this plugin base has been recognised
                    recognised = True
                    newPlugin = CDMPluginInfo( plugin )
                    if collectedPlugins.has_key( category ):
                        collectedPlugins[ category ].append( newPlugin )
                    else:
                        collectedPlugins[ category ] = [ newPlugin ]
                    break

            if not recognised:
                logging.warning( "Plugin of an unknown category is found at: " +
                                 plugin.path + ". The plugin is disabled." )
                newPlugin = CDMPluginInfo( plugin )
                newPlugin.conflictType = CDMPluginManager.BAD_BASE_CLASS
                newPlugin.conflictMessage = "The plugin does not derive any " \
                                            "known plugin category interface"
                self.unknownPlugins.append( newPlugin )

        return collectedPlugins

    def __activatePlugins( self, collectedPlugins ):
        " Activating the plugins "
        from utils.globals import GlobalData

        for category in collectedPlugins:
            for plugin in collectedPlugins[ category ]:
                try:
                    plugin.getObject().activate( Settings(), GlobalData() )
                    if category in self.activePlugins:
                        self.activePlugins[ category ].append( plugin )
                    else:
                        self.activePlugins[ category ] = [ plugin ]
                except Exception as excpt:
                    logging.error( "Error activating plugin at " +
                                   plugin.getPath() +
                                   ". The plugin disabled. Error message: \n" +
                                   str( excpt ) )
                    plugin.conflictType = CDMPluginManager.BAD_ACTIVATION
                    plugin.conflictMessage = "Error activating the plugin"
                    if category in self.inactivePlugins:
                        self.inactivePlugins[ category ].append( plugin )
                    else:
                        self.inactivePlugins[ category ] = [ plugin ]
        return


    def __checkIDECompatibility( self, collectedPlugins ):
        " Checks that the plugins can be used with the current IDE "
        from utils.globals import GlobalData

        toBeRemoved = []
        for category in collectedPlugins:
            for plugin in collectedPlugins[ category ]:
                try:
                    if not plugin.getObject().isIDEVersionCompatible(
                                GlobalData().version ):
                        # The plugin is incompatible. Disable it
                        logging.warning( "Plugin of an incompatible version "
                                         "is found at: " + plugin.getPath() +
                                         ". The plugin is disabled." )
                        plugin.conflictType = CDMPluginManager.INCOMPATIBLE_IDE_VERSION_CONFLICT
                        plugin.conflictMessage = "The IDE version does not meet " \
                                                 "the plugin requirements."
                        self.unknownPlugins.append( plugin )
                        toBeRemoved.append( plugin.getPath() )
                except Exception as excpt:
                    # Could not successfully call the interface method
                    logging.error( "Error checking IDE version compatibility of plugin at " +
                                   plugin.getPath() +
                                   ". The plugin disabled. Error message: \n" +
                                   str( excpt ) )
                    plugin.conflictType = CDMPluginManager.BAD_INTERFACE
                    plugin.conflictMessage = "Error checking IDE version compatibility"
                    if category in self.inactivePlugins:
                        self.inactivePlugins[ category ].append( plugin )
                    else:
                        self.inactivePlugins[ category ] = [ plugin ]
                    toBeRemoved.append( plugin.getPath() )

        for path in toBeRemoved:
            for category in collectedPlugins:
                for plugin in collectedPlugins[ category ]:
                    if plugin.getPath() == path:
                        collectedPlugins.remove( plugin )
                        break

        return

    def __applyDisabledPlugins( self, collectedPlugins ):
        """ Takes the disabled plugins from settings and marks
            collected plugins accordingly """
        for disabledPlugin in Settings().disabledPlugins:
            # Parse the record
            try:
                conflictType, \
                path, \
                conflictMessage = CDMPluginInfo.parseDisabledLine( disabledPlugin )
            except Exception as excpt:
                logging.warning( str( excpt ) )
                continue

            found = False
            for category in collectedPlugins:
                for plugin in collectedPlugins[ category ]:
                    if plugin.getPath() == path:
                        found = True
                        plugin.conflictType = conflictType
                        plugin.conflictMessage = conflictMessage
                        if self.inactivePlugins.has_key( category ):
                            self.inactivePlugins[ category ].append( plugin )
                        else:
                            self.inactivePlugins[ category ] = [ plugin ]
                        collectedPlugins[ category ].remove( plugin )
                        break
                if found:
                    break

            if not found:
                # Second try - search through the unknown plugins
                for plugin in self.unknownPlugins:
                    if plugin.getPath() == path:
                        found = True
                        plugin.conflictType = conflictType
                        plugin.conflictMessage = conflictMessage
                        break

            if not found:
                logging.warning( "The disabled plugin at " + path +
                                 " has not been found. The information that "
                                 " the plugin is disabled will be deleted." )

        return

    def __sysVsUserConflicts( self, collectedPlugins ):
        " Checks for the system vs user plugin conflicts "
        return

    def __categoryConflicts( self, collectPlugins ):
        " Checks for version conflicts within the category "
        return

    def __saveDisabledPlugins( self ):
        """ Saves the disabled plugins info into the settings """
        value = []
        for category in self.inactivePlugins:
            for plugin in self.inactivePlugins[ category ]:
                line = plugin.getDisabledLine()
                if line is not None:
                    value.append( line )
        for plugin in self.unknownPlugins:
            line = plugin.getDisabledLine()
            if line is not None:
                value.append( line )
        Settings().disabledPlugins = value
        return




class CDMPluginInfo:
    " Holds info about a single plugin "

    def __init__( self, pluginInfo ):
        " The pluginInfo comes from yapsy "
        self.info = pluginInfo                              # yapsy.PluginInfo
        self.isUser = self.__isUserPlugin( self.info )      # True/False
        self.isEnabled = False                              # True/False
        self.conflictType = CDMPluginManager.NO_CONFLICT    # See CDMPluginManager constants
        self.conflictMessage = ""                           # One line message for UI/log
        return

    def __isUserPlugin( self, plugin ):
        " True if it is a user plugin "
        dir( plugin )
        type( plugin )
        print plugin.path
        return plugin.path.startswith( "settingsDir" )

    def getDisabledLine( self ):
        " Used for the setting file "
        if self.isEnabled is None or self.isEnabled == True:
            return None
        return str( self.conflictType ) + ":::" + \
               self.info.path + ":::" + \
               self.conflictMessage

    @staticmethod
    def parseDisabledLine( configLine ):
        " Parser the config line and returns a tuple "
        parts = configLine.split( ":::", 2 )
        if len( parts ) != 3:
            raise ValueError( "Incorrect disabled plugin description: " +
                              configLine )
        # (conflictType, path, conflictMessage)
        return ( parts[ 0 ], parts[ 1 ], parts[ 2 ] )

    def getObject( self ):
        " Provides a reference to the plugin object "
        return self.info.plugin_object

    def getPath( self ):
        " Provides the plugin path "
        return self.info.path

    def disable( self, conflictType = CDMPluginManager.NO_CONFLICT,
                       conflictMessage = "" ):
        " Disables the plugin "
        self.isEnabled = False
        self.conflictType = conflictType
        self.conflictMessage = ""

        if self.getObject().isActivated():
            self.getObject().deactivate()
        return

    def enable( self ):
        " Enables the plugin "
        self.isEnabled = True
        self.conflictType = CDMPluginManager.NO_CONFLICT
        self.conflictMessage = ""
        return


def getBaseClassNames( inst ):
    " Provides a list of base class names for the given instance "
    baseNames = []

    def baseClassNames( inst, names ):
        " Recursive retriever "
        if hasattr( inst, "__bases__" ):
            container = inst.__bases__
        else:
            container = inst.__class__.__bases__
        for base in container:
            names.append( base.__name__ )
            if base.__name__ != "object":
                baseClassNames( base, names )
        return

    baseClassNames( inst, baseNames )
    return baseNames



if __name__ == "__main__":
    class A1( ):
        def f():
            pass
    class A( A1 ):
        def f():
            pass
    class B:
        def f():
            pass
    class C( A, B ):
        def f():
            pass
    print getBaseClassNames( C() )

