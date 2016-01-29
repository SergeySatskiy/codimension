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

""" Sets up and handles the flow UI context menus """


from PyQt4.QtGui import QMenu, QAction
from flowui.items import IfCell
from utils.pixmapcache import getIcon


class CFSceneContextMenuMixin:
    " Encapsulates the context menu handling "

    def __init__( self ):
        self.individualMenus = {}

        self.individualCommonMenu = QMenu()
        self.individualCommonMenu.addAction(
            getIcon( "customcolors.png" ), "Custom colors...",
            self.onCustomColors )
        self.individualCommonMenu.addAction(
            getIcon( "replacetitle.png" ), "Replace title...",
            self.onReplaceTitle )
        self.individualCommonMenu.addSeparator()
        self.individualCommonMenu.addAction(
            getIcon( "trash.png" ), "Delete...", self.onDelete )

        ifContextMenu = QMenu()
        ifContextMenu.addAction(
            getIcon( "switchbranches.png") , "Switch branch layout",
            self.onSwitchIfBranch )

        self.individualMenus[ IfCell ] = ifContextMenu


        self.groupMenu = QMenu()
        self.groupMenu.addAction(
            getIcon( "cfgroup.png" ), "Group...",
            self.onGroup )
        self.groupMenu.addAction(
            getIcon( "customcolors.png" ), "Custom colors...",
            self.onCustomColors )
        self.groupMenu.addSeparator()
        self.groupMenu.addAction(
            getIcon( "trash.png" ), "Delete...", self.onDelete )

        return

    def onContextMenu( self, event ):
        " Triggered when a context menu should be shown "
        selectedItems = self.selectedItems()
        selectionCount = len( selectedItems )
        if selectionCount == 0:
            return

        if selectionCount == 1:
            self.__buildIndividualMenu( selectedItems[ 0 ] )
        else:
            self.__buildGroupMenu( selectedItems )
        self.menu.popup( event.screenPos() )
        return

    def __buildIndividualMenu( self, item ):
        " Builds a context menu for the given item "
        self.menu = QMenu()
        if type( item ) in self.individualMenus:
            individualPart = self.individualMenus[ type( item ) ]
            self.menu.addActions( individualPart.actions() )
            self.menu.addSeparator()
        self.menu.addActions( self.individualCommonMenu.actions() )

        # Note: if certain items need to be disabled then it should be done
        #       here

        return

    def __buildGroupMenu(  self, items ):
        " Builds a context menu for the group of items "
        self.menu = QMenu()
        self.menu.addActions( self.groupMenu.actions() )

        # Note: if certain items need to be disabled then it should be done
        #       here

        return

    def onSwitchIfBranch( self ):
        " If primitive should switch the branches "
        print "Switch if branch"

    def onCustomColors( self ):
        " Custom background and foreground colors "
        print "Custom colors"

    def onReplaceTitle( self ):
        " Replace the code with a title "
        print "Replace title"

    def onDelete( self ):
        " Delete the item "
        print "Delete"

    def onGroup( self ):
        " Groups items into a single one "
        print "Group"


