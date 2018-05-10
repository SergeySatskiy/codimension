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
from flowui.scopeitems import ScopeCellElement
from flowui.groupitems import OpenedGroupBegin, CollapsedGroup, EmptyGroup
from flowui.cml import CMLVersion, CMLsw, CMLcc, CMLrt, CMLgb, CMLge
from utils.pixmapcache import getIcon
from utils.diskvaluesrelay import addCollapsedGroup, removeCollapsedGroup
from utils.settings import Settings
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
        self.sceneMenu.addAction(getIcon('copymenu.png'),
                                 'Copy image to clipboard',
                                 self.parent().copyToClipboard)

        # Common menu for all the individually selected items
        self.commonMenu = QMenu()
        self.__ccAction = self.commonMenu.addAction(
            getIcon("customcolors.png"), "Custom colors...",
            self.onCustomColors)
        self.__rtAction = self.commonMenu.addAction(
            getIcon("replacetitle.png"), "Replace text...",
            self.onReplaceText)
        self.__groupAction = self.commonMenu.addAction(
            getIcon("cfgroup.png"), "Group...",
            self.onGroup)
        self.commonMenu.addSeparator()
        self.__removeCCAction = self.commonMenu.addAction(
            getIcon('trash.png'), 'Remove custom colors',
            self.onRemoveCustomColors)
        self.__removeRTAction = self.commonMenu.addAction(
            getIcon('trash.png'), 'Remove replacement text',
            self.onRemoveReplacementText)
        #self.commonMenu.addSeparator()
        #self.__cutAction = self.commonMenu.addAction(
        #    getIcon("cutmenu.png"), "Cut (specific for graphics pane)",
        #    self.onCut)
        #self.__copyAction = self.commonMenu.addAction(
        #    getIcon("copymenu.png"), "Copy (specific for graphics pane)",
        #    self.onCopy)
        #self.commonMenu.addSeparator()
        #self.commonMenu.addAction(
        #    getIcon("trash.png"), "Delete", self.onDelete)

        # Individual items specific menu: begin
        ifContextMenu = QMenu()
        ifContextMenu.addAction(
            getIcon("switchbranches.png"), "Switch branch layout",
            self.onSwitchIfBranch)

        openGroupContextMenu = QMenu()
        openGroupContextMenu.addAction(
            getIcon("collapse.png"), "Collapse",
            self.onGroupCollapse)
        openGroupContextMenu.addAction(
            getIcon("replacetitle.png"), "Edit title...",
            self.onGroupEditTitle)
        openGroupContextMenu.addAction(
            getIcon("ungroup.png"), "Ungroup",
            self.onGroupUngroup)

        closeGroupContextMenu = QMenu()
        closeGroupContextMenu.addAction(
            getIcon("expand.png"), "Expand",
            self.onGroupExpand)
        closeGroupContextMenu.addAction(
            getIcon("replacetitle.png"), "Edit title...",
            self.onGroupEditTitle)
        closeGroupContextMenu.addAction(
            getIcon("ungroup.png"), "Ungroup",
            self.onGroupUngroup)

        emptyGroupContextMenu = QMenu()
        emptyGroupContextMenu.addAction(
            getIcon("replacetitle.png"), "Edit title...",
            self.onGroupEditTitle)
        emptyGroupContextMenu.addAction(
            getIcon("ungroup.png"), "Ungroup",
            self.onGroupUngroup)

        self.individualMenus[IfCell] = ifContextMenu
        self.individualMenus[OpenedGroupBegin] = openGroupContextMenu
        self.individualMenus[CollapsedGroup] = closeGroupContextMenu
        self.individualMenus[EmptyGroup] = emptyGroupContextMenu
        # Individual items specific menu: end

        # Menu for a group of selected items
        self.groupMenu = QMenu()

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
        if not self.groupMenu.isEmpty():
            self.menu.addSeparator()
            self.menu.addActions(self.groupMenu.actions())

        # Note: if certain items need to be disabled then it should be done
        #       here
        self.__disableMenuItems()

    def __disableMenuItems(self):
        """Disables the common menu items as needed"""
        hasComment = self.isCommentInSelection()
        hasDocstring = self.isDocstringInSelection()
        hasMinimizedExcepts = self.isInSelected([(CellElement.EXCEPT_MINIMIZED,
                                                  None)])
        totalGroups = sum(self.countGroups())
        count = len(self.selectedItems())

        self.__ccAction.setEnabled(not hasComment and not hasMinimizedExcepts)
        self.__rtAction.setEnabled(not hasComment and
                                   not hasDocstring and
                                   not hasMinimizedExcepts and
                                   totalGroups == 0)

        totalCCGroups = sum(self.countGroupsWithCustomColors())
        self.__removeCCAction.setEnabled(
            self.countItemsWithCML(CMLcc) + totalCCGroups == count)
        self.__removeRTAction.setEnabled(
            self.countItemsWithCML(CMLrt) == count)
        self.__groupAction.setEnabled(self.__canBeGrouped())
        #self.__cutAction.setEnabled(count == 1)
        #self.__copyAction.setEnabled(count == 1)

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

        # Memorize the current selection
        selection = self.serializeSelection()

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
        self.restoreSelectionByID(selection)

    def onCustomColors(self):
        """Custom background and foreground colors"""
        if not self.__actionPrerequisites():
            return

        # Memorize the current selection
        selection = self.serializeSelection()

        bgcolor, fgcolor, bordercolor = self.selectedItems()[0].getColors()
        hasDocstring = self.isDocstringInSelection()
        dlg = CustomColorsDialog(bgcolor, fgcolor,
                                 None if hasDocstring else bordercolor,
                                 self.parent())
        if dlg.exec_():
            bgcolor = dlg.backgroundColor()
            fgcolor = dlg.foregroundColor()
            bordercolor = dlg.borderColor()

            editor = self.selectedItems()[0].getEditor()
            with editor:
                for item in self.sortSelectedReverse():
                    if item.kind in [CellElement.OPENED_GROUP_BEGIN,
                                     CellElement.COLLAPSED_GROUP,
                                     CellElement.EMPTY_GROUP]:
                        # The group always exists so just add/change the colors
                        item.groupBeginCMLRef.updateCustomColors(editor,
                                                                 bgcolor,
                                                                 fgcolor,
                                                                 bordercolor)
                        continue
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

                    pos = item.ref.body.beginPos
                    if item.isDocstring():
                        pos = item.ref.docstring.beginPos
                    line = CMLcc.generate(bgcolor, fgcolor, bordercolor, pos)
                    editor.insertLines(line, lineNo)
            QApplication.processEvents()
            self.parent().redrawNow()
            self.restoreSelectionByID(selection)

    def onReplaceText(self):
        """Replace the code with a title"""
        if not self.__actionPrerequisites():
            return

        # Memorize the current selection
        selection = self.serializeSelection()

        dlg = ReplaceTextDialog('Replace text', 'Item caption:', self.parent())

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
            self.restoreSelectionByID(selection)

    def onGroupCollapse(self):
        """Collapses the selected group"""
        if not self.__actionPrerequisites():
            return

        # The selected items need to be sorted in the reverse line no oreder
        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                if item.kind == CellElement.OPENED_GROUP_BEGIN:
                    fileName = editor._parent.getFileName()
                    if not fileName:
                        fileName = editor._parent.getShortName()
                    addCollapsedGroup(fileName, item.getGroupId())

        QApplication.processEvents()
        self.parent().redrawNow()

    def onGroupExpand(self):
        """Expands the selected group"""
        if not self.__actionPrerequisites():
            return

        # The selected items need to be sorted in the reverse line no oreder
        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                if item.kind == CellElement.COLLAPSED_GROUP:
                    fileName = editor._parent.getFileName()
                    if not fileName:
                        fileName = editor._parent.getShortName()
                    removeCollapsedGroup(fileName, item.getGroupId())

        QApplication.processEvents()
        self.parent().redrawNow()

    def onGroupEditTitle(self):
        """Edit (or view) the group title"""
        if not self.__actionPrerequisites():
            return

        # Memorize the current selection
        selection = self.serializeSelection()

        dlg = ReplaceTextDialog('Group title', 'Group title:', self.parent())

        # If it was one item selection and there was a previous text then
        # set it for editing
        if len(self.selectedItems()) == 1:
            title = self.selectedItems()[0].getTitle()
            if title:
                dlg.setText(title)

        if dlg.exec_():
            newTitle = dlg.text()
            editor = self.selectedItems()[0].getEditor()
            with editor:
                for item in self.sortSelectedReverse():
                    item.groupBeginCMLRef.updateTitle(editor, newTitle)
            QApplication.processEvents()
            self.parent().redrawNow()
            self.restoreSelectionByID(selection)

    def onGroupUngroup(self):
        """Ungroups the items"""
        if not self.__actionPrerequisites():
            return

        # Memorize the current selection
        selection = self.serializeSelection()

        # The selected items need to be sorted in the reverse line no oreder
        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                item.groupEndCMLRef.removeFromText(editor)
                item.groupBeginCMLRef.removeFromText(editor)
        QApplication.processEvents()
        self.parent().redrawNow()
        self.restoreSelectionByTooltip(selection)

    def onDelete(self):
        """Delete the item"""
        print("Delete")

    def onGroup(self):
        """Groups items into a single one"""
        dlg = ReplaceTextDialog('Group title', 'Group title:', self.parent())

        if dlg.exec_():
            groupTitle = dlg.text()
            selected = self.__extendSelectionForGrouping()
            selected = self.sortSelected(selected)
            editor = selected[0].getEditor()

            firstLine, lastLine, pos = self.__getLineRange(selected)

            groupid = self.parent().generateNewGroupId()
            beginComment = CMLgb.generate(groupid, groupTitle,
                                          None, None, None, pos)
            endComment = CMLge.generate(groupid, pos)

            with editor:
                editor.insertLines(endComment, lastLine + 1)
                editor.insertLines(beginComment, firstLine)

            # Redraw the group collapsed
            fileName = editor._parent.getFileName()
            if not fileName:
                fileName = editor._parent.getShortName()
            addCollapsedGroup(fileName, groupid)

            QApplication.processEvents()
            self.parent().redrawNow()

    def onCopy(self):
        """Copying..."""
        selectedItems = self.selectedItems()
        if selectedItems:
            if len(selectedItems) > 1:
                print('Copying multiple items has not been implemented yet')
                return
            selectedItems[0].copyToClipboard()

    def onCut(self):
        """Cutting..."""
        print("Cut")

    def onRemoveCustomColors(self):
        """Removing the previously set custom colors"""
        if not self.__actionPrerequisites():
            return

        # Memorize the current selection
        selection = self.serializeSelection()

        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                if item.kind in [CellElement.OPENED_GROUP_BEGIN,
                                 CellElement.COLLAPSED_GROUP,
                                 CellElement.EMPTY_GROUP]:
                    item.groupBeginCMLRef.removeCustomColors(editor)
                    continue
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
        self.restoreSelectionByID(selection)

    def onRemoveReplacementText(self):
        """Removing replacement text"""
        if not self.__actionPrerequisites():
            return

        # Memorize the current selection
        selection = self.serializeSelection()

        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                cmlComment = CMLVersion.find(item.ref.leadingCMLComments,
                                             CMLrt)
                if cmlComment is not None:
                    cmlComment.removeFromText(editor)
        QApplication.processEvents()
        self.parent().redrawNow()
        self.restoreSelectionByID(selection)

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

    def countGroups(self):
        """Counts empty, close and open groups"""
        emptyCount = 0
        closeCount = 0
        openCount = 0
        for item in self.selectedItems():
            if item.kind == CellElement.EMPTY_GROUP:
                emptyCount += 1
            elif item.kind == CellElement.COLLAPSED_GROUP:
                closeCount += 1
            elif item.kind == CellElement.OPENED_GROUP_BEGIN:
                openCount += 1
        return emptyCount, closeCount, openCount

    def countGroupsWithCustomColors(self):
        """Counts the groups with any color defined"""
        emptyCount = 0
        closeCount = 0
        openCount = 0
        for item in self.selectedItems():
            if item.kind in [CellElement.EMPTY_GROUP,
                             CellElement.COLLAPSED_GROUP,
                             CellElement.OPENED_GROUP_BEGIN]:
                if item.groupBeginCMLRef.bgColor is not None or \
                   item.groupBeginCMLRef.fgColor is not None or \
                   item.groupBeginCMLRef.border is not None:
                    if item.kind == CellElement.EMPTY_GROUP:
                        emptyCount += 1
                    elif item.kind == CellElement.COLLAPSED_GROUP:
                        closeCount += 1
                    else:
                        openCount += 1
        return emptyCount, closeCount, openCount

    def sortSelectedReverse(self):
        """Sorts the selected items in reverse order"""
        result = []
        for item in self.selectedItems():
            itemBegin = item.getAbsPosRange()[0]
            for index in range(len(result)):
                if itemBegin > result[index].getAbsPosRange()[0]:
                    result.insert(index, item)
                    break
            else:
                result.append(item)
        return result

    def sortSelected(self, selected):
        """Sorts the selected items in direct order"""
        result = []
        for item in selected:
            itemBegin = item.getAbsPosRange()[0]
            for index in range(len(result)):
                if itemBegin < result[index].getAbsPosRange()[0]:
                    result.insert(index, item)
                    break
            else:
                result.append(item)
        return result

    def __canBeGrouped(self):
        """True if the selected items can be grouped"""
        # Cannot import it at the top...
        from .flowuiwidget import SMART_ZOOM_ALL, SMART_ZOOM_NO_CONTENT

        if Settings()['smartZoom'] not in [SMART_ZOOM_ALL,
                                           SMART_ZOOM_NO_CONTENT]:
            return False
        if self.__areAllSelectedComments():
            return False
        if self.__areScopeDocstringOrCommentSelected():
            return False
        if self.__isModuleSelected():
            return False

        # Extend the selection with all the selected items comments
        selected = self.__extendSelectionForGrouping()

        if self.__areLoneCommentsSelected(selected):
            return False

        if self.__areIncompleteScopeSelected(selected):
            return False

        scopeCoveredRegions = self.__getSelectedScopeRegions(selected)

        # The __areIfFullySelected() also updates the regions with
        # fully selected if regions
        if not self.__areIfFullySelected(selected, scopeCoveredRegions):
            return False

        selected = self.sortSelected(selected)
        begin = selected[0].getAbsPosRange()[0]
        end = selected[-1].getAbsPosRange()[1]

        if not self.__isSelectionContinuous(selected, scopeCoveredRegions,
                                            begin, end):
            return False

        if self.__moreThanOneIfBranchSelected(selected, scopeCoveredRegions):
            return False
        return True

    def __areAllSelectedComments(self):
        """True if all selected items are comments"""
        for item in self.selectedItems():
            if not item.isComment():
                return False
        return True

    def __areScopeDocstringOrCommentSelected(self):
        for item in self.selectedItems():
            if item.scopedItem():
                if item.subKind in [ScopeCellElement.SIDE_COMMENT,
                                    ScopeCellElement.DOCSTRING]:
                    return True
        return False

    def __isModuleSelected(self):
        """True if the whole module is selected"""
        for item in self.selectedItems():
            if item.kind == CellElement.FILE_SCOPE:
                return True
        return False

    def __areIncompleteScopeSelected(self, selected):
        """True if an incomplete scope selected"""
        for item in selected:
            if item.kind in [CellElement.FOR_SCOPE,
                             CellElement.WHILE_SCOPE]:
                if item.ref.elsePart:
                    for relatedItem in self.findItemsForRef(item.ref.elsePart):
                        if relatedItem not in selected:
                            return True
            elif item.kind in [CellElement.TRY_SCOPE]:
                # It could be that the exception blocks are hidden, so there
                # will be exactly one more item instead of many and that item
                # will have a ref which matches the try scope.
                exceptPartCount = 0
                for exceptPart in item.ref.exceptParts:
                    for relatedItem in self.findItemsForRef(exceptPart):
                        exceptPartCount += 1
                        if relatedItem not in selected:
                            return True
                if exceptPartCount == 0:
                    # here: no except blocks on the diagram, they are collapsed
                    tryItems = self.findItemsForRef(item.ref)
                    for tryItem in tryItems:
                        if tryItem.kind == CellElement.EXCEPT_MINIMIZED:
                            if not tryItem.isSelected():
                                return True
                            break
                    else:
                        # The minimized except is not selected
                        return True
                if item.ref.elsePart:
                    for relatedItem in self.findItemsForRef(item.ref.elsePart):
                        if relatedItem not in selected:
                            return True
                if item.ref.finallyPart:
                    for relatedItem in self.findItemsForRef(item.ref.finallyPart):
                        if relatedItem not in selected:
                            return True
            elif item.kind in [CellElement.ELSE_SCOPE,
                               CellElement.EXCEPT_SCOPE,
                               CellElement.FINALLY_SCOPE]:
                for relatedItem in self.findItemsForRef(item.leaderRef):
                    if relatedItem not in selected:
                        return True
            elif item.kind == CellElement.EXCEPT_MINIMIZED:
                # here: no except blocks on the diagram, they are collapsed
                tryItems = self.findItemsForRef(item.ref)
                for tryItem in tryItems:
                    if tryItem.kind == CellElement.TRY_SCOPE:
                        if tryItem.subKind == ScopeCellElement.TOP_LEFT:
                            if not tryItem.isSelected():
                                return True
                            break
                else:
                    # The try is not selected
                    return True
        return False

    def __extendSelectionForGrouping(self):
        """Extends the selection with the leading and side comments"""
        boundComments = []
        selected = self.selectedItems()
        for item in selected:
            if not item.isComment() and not self.isOpenGroupItem(item):
                for relatedItem in self.findItemsForRef(item.ref):
                    if relatedItem not in selected:
                        boundComments.append(relatedItem)
        return selected + boundComments

    def __areLoneCommentsSelected(self, selected):
        """True if there are comments selected which have no main item selected"""
        for item in selected:
            if item.isComment():
                if item.kind in [CellElement.SIDE_COMMENT,
                                 CellElement.LEADING_COMMENT,
                                 CellElement.ABOVE_COMMENT]:
                    for relatedItem in self.findItemsForRef(item.ref):
                        if relatedItem not in selected:
                            return True
        return False

    def __getLineRange(self, selected):
        first = selected[0]
        last = selected[-1]

        if first.kind == CellElement.OPENED_GROUP_BEGIN:
            firstLine = first.groupBeginCMLRef.ref.parts[0].beginLine
            pos = first.groupBeginCMLRef.ref.parts[0].beginPos
        else:
            firstLine = first.getLineRange()[0]
            pos = first.ref.beginPos

        if last.scopedItem():
            lastLine = last.ref.endLine
        elif last.kind == CellElement.OPENED_GROUP_BEGIN:
            lastLine = last.groupEndCMLRef.ref.parts[-1].endLine
        else:
            lastLine = last.getLineRange()[1]
        return firstLine, lastLine, pos

    def __getSelectedScopeRegions(self, selected):
        """Provides the regions of the selected scope items"""
        coveredRegions = []
        for item in selected:
            if item.scopedItem():
                if item.subKind in [ScopeCellElement.TOP_LEFT]:
                    if item.ref.leadingComment:
                        coveredRegions.append((item.ref.leadingComment.begin,
                                               item.ref.end))
                    else:
                        coveredRegions.append((item.ref.begin, item.ref.end))
            elif item.kind == CellElement.OPENED_GROUP_BEGIN:
                coveredRegions.append(item.getAbsPosRange())
        return coveredRegions

    def __areIfFullySelected(self, selected, regions):
        """Checks if selected IFs are fully selected"""
        for item in selected:
            if item.kind == CellElement.IF:
                ifBegin = item.ref.begin
                ifEnd = item.ref.end
                for item in self.items():
                    if item.isProxyItem():
                        continue
                    if item.scopedItem():
                        if item.subKind not in [ScopeCellElement.TOP_LEFT,
                                                ScopeCellElement.DOCSTRING,
                                                ScopeCellElement.SIDE_COMMENT]:
                            continue
                    if item in selected:
                        continue
                    itemRange = item.getAbsPosRange()
                    if self.isInRegion(itemRange[0], itemRange[1], regions):
                        continue
                    if itemRange[0] > ifBegin and itemRange[0] < ifEnd:
                        return False
                    if itemRange[1] > ifBegin and itemRange[1] < ifEnd:
                        return False
                regions.append([ifBegin, ifEnd])
        return True

    @staticmethod
    def isInRegion(start, finish, regions):
        for region in regions:
            if start >= region[0] and finish <= region[1]:
                return True
        return False

    def __isSelectionContinuous(self, selected, regions, begin, end):
        """Checks if the selection is continuous"""
        for item in self.items():
            if item.isProxyItem():
                continue
            if item.scopedItem():
                if item.subKind not in [ScopeCellElement.TOP_LEFT,
                                        ScopeCellElement.DOCSTRING,
                                        ScopeCellElement.SIDE_COMMENT]:
                    continue
            if item in selected:
                continue
            itemRange = item.getAbsPosRange()
            if self.isInRegion(itemRange[0], itemRange[1], regions):
                continue

            # It is important to keep < and > instead of <= and >=
            # This is because the scopes start with the first statement
            if itemRange[0] > begin and itemRange[0] < end:
                return False
            if itemRange[1] > begin and itemRange[1] < end:
                return False
        return True

    def __moreThanOneIfBranchSelected(self, selected, regions):
        """Checks that the continuous selected items belong to more than one
        not selected IF statements
        """
        ifRef = None
        for item in selected:
            if item.kind != CellElement.IF:
                itemRange = item.getAbsPosRange()
                if item.kind != CellElement.OPENED_GROUP_BEGIN:
                    if self.isInRegion(itemRange[0], itemRange[1], regions):
                        # Here: an item is in a selected scope item, in a selected
                        #       open group or in a fully selected if
                        continue
                # Test if an item belongs to an if statement branch
                if item.kind in [CellElement.OPENED_GROUP_BEGIN,
                                 CellElement.EMPTY_GROUP,
                                 CellElement.COLLAPSED_GROUP]:
                    branchId = item.groupBeginCMLRef.ref.getParentIfID()
                else:
                    branchId = item.ref.getParentIfID()
                if branchId is not None:
                    if ifRef is None:
                        ifRef = branchId
                    else:
                        if branchId != ifRef:
                            # Selected items belong to more than one branch
                            return True
        return False
