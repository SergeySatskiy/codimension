# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Sets up and handles the flow UI context menus"""


from ui.qt import QMenu
from flowui.items import CellElement, IfCell
from utils.pixmapcache import getIcon


class CFSceneContextMenuMixin:

    """Encapsulates the context menu handling"""

    def __init__(self):
        self.menu = None
        self.individualMenus = {}

        # Scene menu preparation
        self.sceneMenu = QMenu()
        self.sceneMenu.addAction(getIcon('filesvg.png'), 'Save as SVG...',
                                 self.parent().onSaveAsSVG)
        self.sceneMenu.addAction(getIcon('filepdf.png'), 'Save as PDF...',
                                 self.parent().onSaveAsPDF)
        self.sceneMenu.addAction(getIcon('filepixmap.png'), 'Save as PNG...',
                                 self.parent().onSaveAsPNG)
        self.sceneMenu.addSeparator()
        self.sceneMenu.addAction(getIcon('copymenu.png'), 'Copy to clipboard',
                                 self.parent().copyToClipboard)

        # Common menu for all the individually selected items
        self.commonMenu = QMenu()
        # self.commonMenu.addAction(
        #    getIcon("cutmenu.png"), "Cut (Ctrl+X)", self.onCut)
        # self.commonMenu.addAction(
        #    getIcon("copymenu.png"), "Copy (Ctrl+C)", self.onCopy)
        # self.commonMenu.addSeparator()
        # self.commonMenu.addAction(
        #    getIcon("trash.png"), "Delete (Del)", self.onDelete)

        # Non-comment common menu for the individually selected items
        self.nonCommentCommonMenu = QMenu()
        # self.nonCommentCommonMenu.addAction(
        #    getIcon("customcolors.png"), "Custom colors...",
        #    self.onCustomColors)
        # self.nonCommentCommonMenu.addAction(
        #    getIcon("replacetitle.png"), "Replace text...",
        #    self.onReplaceText)

        # Individual items specific menu: begin
        ifContextMenu = QMenu()
        ifContextMenu.addAction(
            getIcon("switchbranches.png"), "Switch branch layout",
            self.onSwitchIfBranch)

        self.individualMenus[IfCell] = ifContextMenu
        # Individual items specific menu: end

        # Menu for a group of selected items
        self.groupMenu = QMenu()
        # self.groupMenu.addAction(
        #    getIcon( "cfgroup.png" ), "Group...",
        #    self.onGroup )
        # self.groupMenu.addAction(
        #    getIcon( "customcolors.png" ), "Custom colors...",
        #    self.onCustomColors )
        # self.groupMenu.addSeparator()
        # self.groupMenu.addAction(
        #    getIcon( "trash.png" ), "Delete (Del)", self.onDelete )

    def onContextMenu(self, event):
        """Triggered when a context menu should be shown"""
        selectedItems = self.selectedItems()
        selectionCount = len(selectedItems)
        if selectionCount == 0:
            self.sceneMenu.popup(event.screenPos())
            return

        if selectionCount == 1:
            self.__buildIndividualMenu(selectedItems[0])
        else:
            self.__buildGroupMenu(selectedItems)
        self.menu.popup(event.screenPos())

    def __buildIndividualMenu(self, item):
        """Builds a context menu for the given item"""
        self.menu = QMenu()
        if type(item) in self.individualMenus:
            individualPart = self.individualMenus[type(item)]
            self.menu.addActions(individualPart.actions())
            self.menu.addSeparator()
        if not item.isComment():
            self.menu.addActions(self.nonCommentCommonMenu.actions())
            self.menu.addSeparator()
        self.menu.addActions(self.commonMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here

    def __buildGroupMenu(self, items):
        """Builds a context menu for the group of items"""
        self.menu = QMenu()
        self.menu.addActions(self.groupMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here

    def onSwitchIfBranch(self):
        """If primitive should switch the branches"""
        selectedItems = self.selectedItems()
        for item in selectedItems:
            if item.kind == CellElement.IF:
                item.switchBranches()

    def onCustomColors(self):
        """Custom background and foreground colors"""
        print("Custom colors")

    def onReplaceText(self):
        """Replace the code with a title"""
        print("Replace title")

    def onDelete(self):
        """Delete the item"""
        print("Delete")

    def onGroup(self):
        """Groups items into a single one"""
        print("Group")

    def onCopy(self):
        """Copying..."""
        print("Copy")

    def onCut(self):
        """Cutting..."""
        print("Cut")
