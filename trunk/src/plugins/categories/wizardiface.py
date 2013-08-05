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

" Wizard plugin interface "


from cdmpluginbase import CDMPluginBase

class WizardInterface( CDMPluginBase ):
    """ Wizard plugin interface """

    def __init__( self ):
        """ The plugin class is instantiated with no arguments.
            Instantiating is done regardless wheather a plugin is
            enabled or disabled. So it is recommended to have the
            resource allocation in the activate(...) method and
            deallocation of them in the deactivate(...) method.
        """
        CDMPluginBase.__init__( self )
        return


    # Member functions below could or should be implemented by a plugin.
    # See docstrings for the detailed description.

    @staticmethod
    def isIDEVersionCompatible( ideVersion ):
        """ Codimension makes this call before activating a plugin.
            The passed ideVersion is a string representing
            the current IDE version.
            True should be returned if the plugin is compatible with the IDE.
        """
        raise Exception( "isIDEVersionCompatible() must be overridden" )

    def activate( self, ideSettings, ideGlobalData ):
        """ The plugin may override the method to do specific
            plugin activation handling.

            ideSettings - reference to the IDE Settings singleton
                          see codimension/src/utils/settings.py
            ideGlobalData - reference to the IDE global settings
                            see codimension/src/utils/globals.py

            Note: if overriden then call the base class activate() first.
                  Plugin specific activation handling should follow it.
        """
        CDMPluginBase.activate( self, ideSettings, ideGlobalData )
        return

    def deactivate( self ):
        """ The plugin may override the method to do specific
            plugin deactivation handling.

            Note: if overriden then first do the plugin specific deactivation
                  handling and then call the base class deactivate()
        """
        CDMPluginBase.deactivate( self )
        return

    def getConfigFunction( self ):
        """ The plugin can provide a function which will be called when the
            user requests plugin configuring.
            If a plugin does not require any config parameters then None
            should be returned.
            By default no configuring is required.
        """
        return CDMPluginBase.getConfigFunction( self )

    def populateMainMenu( self, parentMenu ):
        """ The main menu looks as follows:
            Plugins
                - Mange plugins (fixed item)
                - Separator (fixed item)
                - <Plugin #1 name> (this is the parentMenu passed)
                ...
            If no items were populated by the plugin then there will be no
            <Plugin #N name> menu item shown.
            It is suggested to insert plugin configuration item here if so.
        """
        raise Exception( "populateMainMenu() must be overridden" )

    def populateFileContextMenu( self, parentMenu ):
        """ The file context menu shown in the project viewer window will have
            an item with a plugin name and subitems which are populated here.
            If no items were populated then the plugin menu item will not be
            shown.
            When a callback is called the corresponding menu item will have
            attached data with an absolute path to the item.
        """
        raise Exception( "populateFileContextMenu() must be overridden" )

    def populateDirectoryContextMenu( self, parentMenu ):
        """ The directory context menu shown in the project viewer window will have
            an item with a plugin name and subitems which are populated here.
            If no items were populated then the plugin menu item will not be
            shown.
            When a callback is called the corresponding menu item will have
            attached data with an absolute path to the directory.
        """
        raise Exception( "populateDirectoryContextMenu() must be overridden" )

    def populateBufferContextMenu( self, parentMenu ):
        """ The buffer context menu shown for the current edited/viewed file
            will have an item with a plugin name and subitems which are populated here.
            If no items were populated then the plugin menu item will not be
            shown.
            When a callback is called the corresponding menu item will have
            attached data with the buffer UUID.
        """
        raise Exception( "populateBufferContextMenu() must be overridden" )


