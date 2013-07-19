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

from yapsy.PluginManager import PluginManager
#VersionControlSystemInterface


class CodimensionPluginManager( PluginManager ):
    " Implements the codimension plugin manager "
    def __init__( self ):
        PluginManager.__init__( self, None,
                                [ "/home/swift/codimension/src/plugins" ],
                                "cdmp" )
        return

    def load( self ):
        " Loads the found plugins "
        self.locatePlugins()
        self.collectPlugins()
        print "All plugins"
        for plugin in self.getAllPlugins():
            print "Plugin: " + plugin.name + " Version: " + str( plugin.version )
            for item in plugin.plugin_object.__class__.__bases__:
                print "  Base: " + item.__name__

        return

