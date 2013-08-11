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
                - Plugin manager (fixed item)
                - Separator (visible if at lease one plugin provided its main menu)
                - <Plugin #1 name> (this is the parentMenu passed)
                ...
            If no items were populated by the plugin then there will be no
            <Plugin #N name> menu item shown.
            Codimension will remove the populated menu when a plugin is disabled.
        """
        raise Exception( "populateMainMenu() must be overridden" )

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
        raise Exception( "populateFileContextMenu() must be overridden" )

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
        raise Exception( "populateDirectoryContextMenu() must be overridden" )

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
                  the infirmation it needs.
        """
        raise Exception( "populateBufferContextMenu() must be overridden" )

    def isUnderVCS( self, path ):
        """ 'path' is an absolute path to a directory or to a file.
            Return value must be True if the given path is under the
            revision control system type, or False otherwise. """
        raise Exception( "isUnderVCS() must be overridden" )

    def isChangedLocally( self, path, recursive = False ):
        """ 'path' is an absolute path to a directory or to a file.
            If the path is a directory then the 'recursive' argument
            could be set to True. If the path is a file then the
            'recursive' argument should be ignored.

            The expected return value is a list of tuples:
            [ (relpath, bool), (relpath, bool)... ]
            where relpath is a relative path to the item (empty string for a file)
            and bool is True if the item changed locally
        """
        raise Exception( "isChangedLocally() must be overridden" )

    def isChangedRemotely( self, path, recursive = False ):
        """ 'path' is an absolute path to a directory or to a file.
            If the path is a directory then the 'recursive' argument
            could be set to True. If the path is a file then the
            'recursive' argument should be ignored.

            The expected return value is a list of tuples:
            [ (relpath, bool), (relpath, bool)... ]
            where relpath is a relative path to the item (empty string for a file)
            and bool is True if the item changed in the repository
        """
        raise Exception( "isChangedRemotely() must be overridden" )

    def getInfo( self, path, recursive = False ):
        """ 'path' is an absolute path to a directory or to a file.
            If the path is a directory then the 'recursive' argument
            could be set to True. If the path is a file then the
            'recursive' argument should be ignored.

            The expected return value is a list of tuples:
            [ (relpath, string), (relpath, string)... ]
            where relpath is a relative path to the item (empty string for a file)
            and string is the textual description of what the VCS can tell about
            the item.
        """
        raise Exception( "getInfo() must be overridden" )

    def getRepositoryVersion( self, path, revision = None ):
        """ Should provide the content of the file at path from the VCS.
            If revision is not specified then it must be the latest version """
        raise Exception( "getRepositoryVersion() must be overridden" )

