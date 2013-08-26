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

" Version control system plugin interface "


from cdmpluginbase import CDMPluginBase


class VersionControlSystemInterface( CDMPluginBase ):
    """ Version control system plugin interface """

    # Standard indicators
    VCS_NOT_WORKING_COPY = 0    # The directory is not a VCS checkout.
    VCS_LOCAL_ONLY = 1          # The directory is a VCS checkout
                                #   while an item is not.
    VCS_UPTODATE = 2            # The item is the same as in the repository.
    VCS_LOCAL_MODIFIED = 3      # The item is locally modified.
    VCS_REMOTE_MODIFIED = 4     # The item is updated in the repository.
    VCS_CONFLICT = 5            # The item is updated both locally
                                #   and in the repository.
    VCS_UNKNOWN = 6             # The item status is unknown, e.g. due to
                                #   repository communication errors.

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

    @staticmethod
    def getVCSName():
        """ Should provide the specific version control name, e.g. SVN """
        raise Exception( "getVCSName() must be overridden" )

    def activate( self, ideSettings, ideGlobalData ):
        """ The plugin may override the method to do specific
            plugin activation handling.

            ideSettings - reference to the IDE Settings singleton
                          see codimension/src/utils/settings.py
            ideGlobalData - reference to the IDE global settings
                            see codimension/src/utils/globals.py

            Note: if overridden then call the base class activate() first.
                  Plugin specific activation handling should follow it.
        """
        CDMPluginBase.activate( self, ideSettings, ideGlobalData )
        return

    def deactivate( self ):
        """ The plugin may override the method to do specific
            plugin deactivation handling.

            Note: if overridden then first do the plugin specific deactivation
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
                - Plugin manager (fixed item)
                - Separator (visible if at lease one plugin provided its main menu)
                - <Plugin #1 name> (this is the parentMenu passed)
                ...
            If no items were populated by the plugin then there will be no
            <Plugin #N name> menu item shown.
            Codimension will remove the populated menu when a plugin is disabled.
        """
        return

    def populateFileContextMenu( self, parentMenu ):
        """ The file context menu shown in the project viewer window will have
            an item with a plugin name and subitems which are populated here.
            If no items were populated then the plugin menu item will not be
            shown.
            When a callback is called the parentMenu data will be set to the
            absolute path of the selected item. So the plugin will be able
            to retrieve the selected path as follows:
            # In this method
            self.fileParentMenu = parentMenu
            ...
            # In a menu item handler
            path = str( self.fileParentMenu.menuAction().data().toString() )

            Codimension will remove the populated menu when a plugin is disabled.
        """
        return

    def populateDirectoryContextMenu( self, parentMenu ):
        """ The directory context menu shown in the project viewer window will have
            an item with a plugin name and subitems which are populated here.
            If no items were populated then the plugin menu item will not be
            shown.
            When a callback is called the parentMenu data will be set to the
            absolute path of the selected item. So the plugin will be able
            to retrieve the selected path as follows:
            # In this method
            self.dirParentMenu = parentMenu
            ...
            # In a menu item handler
            path = str( self.dirParentMenu.menuAction().data().toString() )

            Codimension will remove the populated menu when a plugin is disabled.
        """
        return

    def populateBufferContextMenu( self, parentMenu ):
        """ The buffer context menu shown for the current edited/viewed file
            will have an item with a plugin name and subitems which are populated here.
            If no items were populated then the plugin menu item will not be
            shown.
            Codimension will remove the populated menu when a plugin is disabled.
            Note: when a buffer context menu is selected by the user it always
                  refers to the current widget. To get access to the current
                  editing widget the plugin can use:
                  self.ide.currentEditorWidget
                  The widget could be of different types and some circumstances should
                  be considered, e.g.:
                  - it could be a new file which has not been saved yet
                  - it could be modified
                  - it could be that the disk file has already been deleted
                  - etc.
                  Having the current widget reference the plugin is able to retrieve
                  the information it needs.
        """
        return

    def getCustomIndicators( self ):
        """ A plugin can provide a list of its custom indicators.
            Each indicator is a tuple:
            (id, what, foreground, background, defaultTooltip)
            id - integer value which must be >= 64. 0 - 63 are reserved for standard
                 indicators
            what - string or QPixmap. If it is a pixmap it should be 16x16, if larger
                   then the pixmap will be scaled.
                   If it is a string then it must be no longer than 2 characters. The
                   extra characters will be stripped.
            foreground - QColor or None. It is taken into consideration only if the
                         second value in the tuple is a string. The color will be
                         used for the text font.
            background - QColor or None. It is taken into consideration only if the
                         second value in the tuple is a string. The color will be used
                         to fill the indicator background.
            defaultTooltip - string or None. If provided and the getStatus(...)
                             call did not provide a message then this one is
                             displayed
        """
        return []


    # flag argement values for the getStatus() method
    REQUEST_ITEM_ONLY = 0
    REQUEST_DIRECTORY = 1
    REQUEST_RECURSIVE = 2

    def getStatus( self, path, flag ):
        """ A plugin should provide VCS statuses for the items.
            path - absolute path (string)
            flag - tells what is requested. It is one of the following:
              - REQUEST_ITEM_ONLY => the status of the path is requested
              - REQUEST_DIRECTORY => the path is a directory and the status of
                                     each item in the directory is requested
              - REQUEST_RECURSIVE => the path is a directory and the status of
                                     each item recursively is requested

            Return value:
              list of tuples for each reported item
              (rest-of-item-path, status, message) where
                  - rest-of-item-path => the received path + this value
                                         must make the full item path
                  - status => integer, whether a standard VCS_... constant or
                              a custom indicator identifier
                  - message => message if so (string) or None. If a message
                               is supplied then it will appear as a tooltip
                               over the item indicator

            ATTENTION: no IDE functions must be called from this method. This
                       method is running in a separate thread and updating UI from
                       non-UI thread can cause the IDE crash.
        """
        raise Exception( "getStatus() must be overridden" )

