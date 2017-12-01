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


from ui.qt import QMenu, QApplication
from flowui.items import CellElement, IfCell
from flowui.cml import CMLVersion, CMLsw, CMLcc, CMLrt
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
        self.__ccAction = self.commonMenu.addAction(
            getIcon("customcolors.png"), "Custom colors...",
            self.onCustomColors)
        self.__rtAction = self.commonMenu.addAction(
            getIcon("replacetitle.png"), "Replace text...",
            self.onReplaceText)
        self.commonMenu.addSeparator()
        self.__removeCCAction = self.commonMenu.addAction(
            getIcon('trash.png'), 'Remove custom colors',
            self.onRemoveCustomColors)
        self.__removeRTAction = self.commonMenu.addAction(
            getIcon('trash.png'), 'Remove replacement text',
            self.onRemoveReplacementText)
        self.commonMenu.addSeparator()
        self.__cutAction = self.commonMenu.addAction(
            getIcon("cutmenu.png"), "Cut", self.onCut)
        self.__copyAction = self.commonMenu.addAction(
            getIcon("copymenu.png"), "Copy", self.onCopy)
        self.commonMenu.addSeparator()
        self.commonMenu.addAction(
            getIcon("trash.png"), "Delete", self.onDelete)

        # Individual items specific menu: begin
        ifContextMenu = QMenu()
        ifContextMenu.addAction(
            getIcon("switchbranches.png"), "Switch branch layout",
            self.onSwitchIfBranch)

        self.individualMenus[IfCell] = ifContextMenu
        # Individual items specific menu: end

        # Menu for a group of selected items
        self.groupMenu = QMenu()
        self.__groupAction = self.groupMenu.addAction(
            getIcon("cfgroup.png"), "Group...",
            self.onGroup)

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
        self.menu.addActions(self.commonMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here
        self.__disableMenuItems()

    def __buildGroupMenu(self, items):
        """Builds a context menu for the group of items"""
        self.menu = QMenu()
        if type(items[0]) in self.individualMenus:
            if self.areSelectedOfTypes([[items[0].kind, items[0].subKind]]):
                individualPart = self.individualMenus[type(items[0])]
                self.menu.addActions(individualPart.actions())
                self.menu.addSeparator()
        self.menu.addActions(self.commonMenu.actions())
        self.menu.addSeparator()
        self.menu.addActions(self.groupMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here
        self.__groupAction.setEnabled(False)
        self.__disableMenuItems()

    def __disableMenuItems(self):
        """Disables the common menu items as needed"""
        hasComment = self.isCommentInSelection()
        hasDocstring = self.isDocstringInSelection()
        count = len(self.selectedItems())

        self.__ccAction.setEnabled(not hasComment)
        self.__rtAction.setEnabled(not hasComment and not hasDocstring)
        self.__removeCCAction.setEnabled(
            self.countItemsWithCML(CMLcc) == count)
        self.__removeRTAction.setEnabled(
            self.countItemsWithCML(CMLrt) == count)
        self.__cutAction.setEnabled(count == 1)
        self.__copyAction.setEnabled(count == 1)

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
        editor = self.selectedItems()[0].getEditor()
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
        QApplication.processEvents()
        self.parent().redrawNow()

    def onCustomColors(self):
        """Custom background and foreground colors"""
        if not self.__actionPrerequisites():
            return

        bgcolor, fgcolor, bordercolor = self.selectedItems()[0].getColors()
        dlg = CustomColorsDialog(bgcolor, fgcolor, bordercolor, self.parent())
        if dlg.exec_():
            bgcolor = dlg.backgroundColor()
            fgcolor = dlg.foregroundColor()
            bordercolor = dlg.borderColor()

            editor = self.selectedItems()[0].getEditor()
            with editor:
                for item in self.sortSelectedReverse():
                    if item.isDocstring():
                        cmlComment = CMLVersion.find(
                            item.ref.docstring.leadingCMLComments,
                            CMLcc)
                    else:
                        cmlComment = CMLVersion.find(
                            item.ref.leadingCMLComments, CMLcc)
                    if cmlComment is not None:
                        # Existed, so remove the old one first
                        lineNo = cmlComment.ref.beginLine
                        cmlComment.removeFromText(editor)
                    else:
                        lineNo = item.getFirstLine()

                    line = CMLcc.generate(bgcolor, fgcolor, bordercolor,
                                          item.ref.body.beginPos)
                    editor.insertLines(line, lineNo)
            QApplication.processEvents()
            self.parent().redrawNow()

    def onReplaceText(self):
        """Replace the code with a title"""
        if not self.__actionPrerequisites():
            return

        dlg = ReplaceTextDialog(self.parent())

        # If it was one item selection and there was a previous text then
        # set it for editing
        if len(self.selectedItems()) == 1:
            cmlComment = CMLVersion.find(
                self.selectedItems()[0].ref.leadingCMLComments, CMLrt)
            if cmlComment is not None:
                dlg.setText(cmlComment.getText())

        if dlg.exec_():
            replacementText = dlg.text()
            editor = self.selectedItems()[0].getEditor()
            with editor:
                for item in self.sortSelectedReverse():
                    cmlComment = CMLVersion.find(
                        item.ref.leadingCMLComments, CMLrt)
                    if cmlComment is not None:
                        # Existed, so remove the old one first
                        lineNo = cmlComment.ref.beginLine
                        cmlComment.removeFromText(editor)
                    else:
                        lineNo = item.getFirstLine()

                    line = CMLrt.generate(replacementText,
                                          item.ref.body.beginPos)
                    editor.insertLines(line, lineNo)
            QApplication.processEvents()
            self.parent().redrawNow()

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

    def onRemoveCustomColors(self):
        """Removing the previously set custom colors"""
        if not self.__actionPrerequisites():
            return

        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                if item.isDocstring():
                    cmlComment = CMLVersion.find(
                        item.ref.docstring.leadingCMLComments, CMLcc)
                else:
                    cmlComment = CMLVersion.find(
                        item.ref.leadingCMLComments, CMLcc)
                if cmlComment is not None:
                    cmlComment.removeFromText(editor)
        QApplication.processEvents()
        self.parent().redrawNow()

    def onRemoveReplacementText(self):
        """Removing replacement text"""
        if not self.__actionPrerequisites():
            return

        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                cmlComment = CMLVersion.find(item.ref.leadingCMLComments,
                                             CMLrt)
                if cmlComment is not None:
                    cmlComment.removeFromText(editor)
        QApplication.processEvents()
        self.parent().redrawNow()

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

    def isDocstringInSelection(self):
        """True if a docstring item in the selection"""
        for item in self.selectedItems():
            if item.isDocstring():
                return True
        return False

    def isCommentInSelection(self):
        """True if a comment item in the selection"""
        for item in self.selectedItems():
            if item.isComment():
                return True
        return False

    def countItemsWithCML(self, cmlType):
        """Counts items with have a certain type of a CML comment"""
        count = 0
        for item in self.selectedItems():
            if item.isComment():
                continue
            if item.isDocstring():
                # Side comments for docstrings? Nonesense! So they are ignored
                # even if they are collected
                if CMLVersion.find(item.ref.docstring.leadingCMLComments,
                                   cmlType) is not None:
                    count += 1
                continue

            if hasattr(item.ref, 'leadingCMLComments'):
                if CMLVersion.find(item.ref.leadingCMLComments,
                                   cmlType) is not None:
                    count += 1
                    continue
            if hasattr(item.ref, 'sideCMLComments'):
                if CMLVersion.find(item.ref.sideCMLComments,
                                   cmlType) is not None:
                    count += 1
        return count

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
