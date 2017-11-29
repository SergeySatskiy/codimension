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
from flowui.cml import CMLVersion, CMLsw, CMLcc
from utils.pixmapcache import getIcon
from .flowuireplacetextdlg import ReplaceTextDialog
from .customcolordlg import CustomColorsDialog


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
        self.nonCommentNonDocCommonMenu = QMenu()
        self.nonCommentNonDocCommonMenu.addAction(
            getIcon("customcolors.png"), "Custom colors...",
            self.onCustomColors)
        self.nonCommentNonDocCommonMenu.addAction(
            getIcon("replacetitle.png"), "Replace text...",
            self.onReplaceText)

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
        # self.groupMenu.addSeparator()
        self.groupMenu.addAction(
            getIcon("trash.png"), "Delete (Del)", self.onDelete)

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
        if not self.isDocOrCommentInSelection():
            self.menu.addActions(self.nonCommentNonDocCommonMenu.actions())
            self.menu.addSeparator()
        self.menu.addActions(self.commonMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here

    def __buildGroupMenu(self, items):
        """Builds a context menu for the group of items"""
        self.menu = QMenu()
        if type(items[0]) in self.individualMenus:
            if self.areSelectedOfTypes([[items[0].kind, items[0].subKind]]):
                individualPart = self.individualMenus[type(items[0])]
                self.menu.addActions(individualPart.actions())
                self.menu.addSeparator()
        if not self.isDocOrCommentInSelection():
            self.menu.addActions(self.nonCommentNonDocCommonMenu.actions())
            self.menu.addSeparator()
        self.menu.addActions(self.groupMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here

    def __actionPrerequisites(self):
        """True if an editor related action can be done"""
        selectedItems = self.selectedItems()
        if not selectedItems:
            return False
        editor = selectedItems[0].getEditor()
        if editor is None:
            return False
        return True

    def onSwitchIfBranch(self):
        """If primitive should switch the branches"""
        if not self.__actionPrerequisites():
            return

        # The selected items need to be sorted in the reverse line no oreder
        editor = selectedItems[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                if item.kind == CellElement.IF:
                    cmlComment = CMLVersion.find(item.ref.leadingCMLComments,
                                                 CMLsw)
                    if cmlComment is None:
                        # Did not exist, so needs to be generated
                        line = CMLsw.generate(item.ref.body.beginPos)
                        lineNo = item.getFirstLine()
                        editor.insertLines(line, lineNo)
                    else:
                        # Existed, so it just needs to be deleted
                        cmlComment.removeFromText(editor)

    def onCustomColors(self):
        """Custom background and foreground colors"""
        if not self.__actionPrerequisites():
            return

        bgcolor, fgcolor, bordercolor = self.selectedItems()[0].getColors()
        dlg = CustomColorsDialog(bgcolor, fgcolor, bordercolor, self.parent())
        bgcolor = dlg.backgroundColor()
        fgcolor = dlg.foregroundColor()
        bordercolor = dlg.borderColor()
        if dlg.exec_():
            editor = selectedItems[0].getEditor()
            with editor:
                for item in self.sortSelectedReverse():
                    cmlComment = CMLVersion.find(item.ref.leadingCMLComments,
                                                 CMLcc)
                    if cmlComment is not None:
                        # Existed, so remove the old one first
                        lineNo = cmlComment.ref.beginLine
                        cmlComment.removeFromText(editor)
                    else:
                        lineNo = item.getFirstLine()

                    line = CMLcc.generate(bgcolor, fgcolor, bordercolor,
                                          item.ref.body.beginPos)
                    editor.insertLines(line, lineNo)

    def onReplaceText(self):
        """Replace the code with a title"""
        if not self.__actionPrerequisites():
            return

        dlg = ReplaceTextDialog(self.parent())
        if dlg.exec_():
            replacementText = dlg.text()
            if replacementText:
                for item in self.selectedItems():
                    if not item.isComment():
                        item.replaceText(replacementText)

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

    def areSelectedOfTypes(self, matchList):
        """Checks if the selected items belong to the match"""
        # match is a list of pairs [kind, subKind]
        #   None would mean 'match any'
        selectedItems = self.selectedItems()
        if selectedItems:
            for selectedItem in selectedItems:
                for kind, subKind in matchList:
                    match = True
                    if kind is not None:
                        if kind != selectedItem.kind:
                            match = False
                    if subKind is not None:
                        if subKind != selectedItem.subKind:
                            match = False
                    if match:
                        break
                else:
                    return False
            return True
        return False

    def isInSelected(self, matchList):
        """Checks if any if the match list items is in the selection"""
        # match is a list of pairs [kind, subKind]
        #   None would mean 'match any'
        for selectedItem in self.selectedItems():
            for kind, subKind in matchList:
                match = True
                if kind is not None:
                    if kind != selectedItem.kind:
                        match = False
                if subKind is not None:
                    if subKind != selectedItem.subKind:
                        match = False
                if match:
                    return True
        return False

    def isDocOrCommentInSelection(self):
        """True if a docstring item or a comment item in the selection"""
        for item in self.selectedItems():
            if item.isComment() or item.isDocstring():
                return True
        return False

    def sortSelectedReverse(self):
        """Sorts the selected items in reverse order"""
        result = []
        for item in self.selectedItems():
            itemBegin = item.ref.body.begin
            for index in range(len(result)):
                if itemBegin > result[index].ref.body.begin:
                    result.insert(index, item)
                    break
            else:
                result.append(item)
        return result
