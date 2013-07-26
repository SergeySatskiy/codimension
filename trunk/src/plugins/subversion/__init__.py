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

" Codimension SVN plugin implementation "


from plugins.categories.vcsiface import VersionControlSystemInterface



class SubversionPlugin( VersionControlSystemInterface ):
    """ Codimension subversion plugin """

    def __init__( self ):
        VersionControlSystemInterface.__init__( self )
        print "Instantiated"
        return

    @staticmethod
    def isIDEVersionCompatible( ideVersion ):
        """ Codimension makes this call before activating a plugin.
            The passed ideVersion is a string representing
            the current IDE version.
            True should be returned if the plugin is compatible with the IDE.
        """
        return True

    @staticmethod
    def getVCSName():
        """ Should provide the specific version control name, e.g. SVN """
        return "SVN"

    def activate( self, ideSettings, ideGlobalData ):
        """ The plugin may override the method to do specific
            plugin activation handling.

            ideSettings - reference to the IDE Settings singleton
                          see codimension/src/utils/settings.py
            ideGlobalData - reference to the IDE global settings
                            see codimension/src/utils/globals.py

            Note: if overriden do not forget to call the
                  base class activate() """
        VersionControlSystemInterface.activate( self, ideSettings,
                                                      ideGlobalData )
        print "Activated"
        return

    def deactivate( self ):
        """ The plugin may override the method to do specific
            plugin deactivation handling.
            Note: if overriden do not forget to call the
                  base class deactivate() """
        VersionControlSystemInterface.deactivate( self )
        print "Deactivated"
        return

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

    def isUnderVCS( self, path ):
        """ 'path' is an absolute path to a directory or to a file.
            Return value must be True if the given path is under the
            revision control system type, or False otherwise. """
        raise Exception( "isUnderVCS() must be overridden" )

    def isChangedLocally( self, path, recursively = False ):
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

    def isChangedRemotely( self, path, recursively = False ):
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

    def getInfo( self, path, recursively = False ):
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


