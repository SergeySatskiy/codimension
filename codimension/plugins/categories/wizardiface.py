# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Wizard plugin interface"""

from .cdmpluginbase import CDMPluginBase


class WizardInterface(CDMPluginBase):

    """Wizard plugin interface"""

    def __init__(self):
        """The plugin class is instantiated with no arguments.

        Instantiating is done regardless wheather a plugin is
        enabled or disabled. So it is recommended to have the
        resource allocation in the activate(...) method and
        deallocation of them in the deactivate(...) method.
        """
        CDMPluginBase.__init__(self)

    # Member functions below could or should be implemented by a plugin.
    # See docstrings for the detailed description.

    @staticmethod
    def isIDEVersionCompatible(ideVersion):
        """Codimension makes this call before activating a plugin.

        The passed ideVersion is a string representing
        the current IDE version.
        True should be returned if the plugin is compatible with the IDE.
        """
        raise Exception("isIDEVersionCompatible() must be overridden")

    def activate(self, ideSettings, ideGlobalData):
        """Can be may overriden to do specific plugin activation handling.

        ideSettings - reference to the IDE Settings singleton
                      see codimension/src/utils/settings.py
        ideGlobalData - reference to the IDE global settings
                        see codimension/src/utils/globals.py

        Note: if overridden then call the base class activate() first.
              Plugin specific activation handling should follow it.
        """
        CDMPluginBase.activate(self, ideSettings, ideGlobalData)

    def deactivate(self):
        """Can be overriden to do specific plugin deactivation handling.

        Note: if overridden then first do the plugin specific deactivation
              handling and then call the base class deactivate()
        """
        CDMPluginBase.deactivate(self)

    def getConfigFunction(self):
        """Provides the config function.

        The plugin can provide a function which will be called when the
        user requests plugin configuring.
        If a plugin does not require any config parameters then None
        should be returned.
        By default no configuring is required.
        """
        return CDMPluginBase.getConfigFunction(self)

    def populateMainMenu(self, parentMenu):
        """Called to populate the main menu.

        The main menu looks as follows:
        Plugins
            - Plugin manager (fixed item)
            - Separator (visible if at lease one plugin provided its
              main menu)
            - <Plugin #1 name> (this is the parentMenu passed)
            ...
        If no items were populated by the plugin then there will be no
        <Plugin #N name> menu item shown.
        Codimension will remove the populated menu when
        a plugin is disabled.
        """
        pass

    def populateFileContextMenu(self, parentMenu):
        """Called to populate the file menu.

        The file context menu shown in the project viewer window will have
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

        Codimension will remove the populated menu when
        a plugin is disabled.
        """
        pass

    def populateDirectoryContextMenu(self, parentMenu):
        """Called to populate the directory menu.

        The directory context menu shown in the project viewer window
        will have an item with a plugin name and subitems which are
        populated here.
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

        Codimension will remove the populated menu when
        a plugin is disabled.
        """
        pass

    def populateBufferContextMenu(self, parentMenu):
        """Called to populate the editing buffer menu.

        The buffer context menu shown for the current edited/viewed file
        will have an item with a plugin name and subitems which are
        populated here.
        If no items were populated then the plugin menu item will not be
        shown.
        Codimension will remove the populated menu when
        a plugin is disabled.
        Note: when a buffer context menu is selected by the user it always
              refers to the current widget. To get access to the current
              editing widget the plugin can use:
              self.ide.currentEditorWidget
              The widget could be of different types and some circumstances
              should be considered, e.g.:
              - it could be a new file which has not been saved yet
              - it could be modified
              - it could be that the disk file has already been deleted
              - etc.
              Having the current widget reference the plugin is able to
              retrieve the information it needs."""
        pass
