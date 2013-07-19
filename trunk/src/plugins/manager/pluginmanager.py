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
    POOR_IMPLEMENTATION_CONFLICT = 2        # Bad plugin interface
    INCOMPATIBLE_IDE_VERSION_CONFLICT = 3   # Plugin required incompatible version
    VERSION_CONFLICT = 4                    # Newer version of the same name plugin
    ACTIVATE_CONFLICT = 5                   # Exception on activation
    BAD_BASE_CLASS = 6                      # Does not derive from any supported interface

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
        self.locatePlugins()
        self.collectPlugins()

        print "All plugins"
        for plugin in self.getAllPlugins():
            print "Plugin: " + plugin.name + " Version: " + str( plugin.version )

        # Now, let's check the plugins. They must be of known category.
        # Put all the collected to inactive list first
        for plugin in self.getAllPlugins():
            recognised = False
            baseClasses = getBaseClassNames( plugin.plugin_object )
            for category in CATEGORIES:
                if category in baseClasses:
                    # OK, this plugin base has been recognised
                    recognised = True
                    newPlugin = CDMPluginInfo( plugin )
                    if self.inactivePlugins.has_key( category ):
                        self.inactivePlugins[ category ] = [ newPlugin ]
                    else:
                        self.inactivePlugins[ category ].append( newPlugin )
                    break

            if not recognised:
                logging.warning( "Plugin of an unknown category is found at: " +
                                 plugin.path + ". The plugin is ignored." )
                newPlugin = CDMPluginInfo( plugin )
                newPlugin.conflictType = CDMPluginManager.BAD_BASE_CLASS
                newPlugin.conflictMessage = "The plugin does not derive any " \
                                            "known plugin category interface"
                self.unknownPlugins.append( newPlugin )

        # Check settings for the disabled plugins






        # Update settings with the disabled plugins


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

