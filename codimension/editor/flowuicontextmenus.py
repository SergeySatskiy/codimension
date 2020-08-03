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


import os.path
import uuid
import logging
from ui.qt import QMenu, QApplication
from flowui.cellelement import CellElement
from flowui.items import IfCell
from flowui.scopeitems import ScopeCellElement
from flowui.groupitems import OpenedGroupBegin, CollapsedGroup, EmptyGroup
from flowui.docitems import IndependentDocCell, LeadingDocCell, AboveDocCell
from flowui.cml import CMLVersion, CMLsw, CMLcc, CMLrt, CMLgb, CMLge, CMLdoc
from utils.pixmapcache import getIcon
from utils.diskvaluesrelay import addCollapsedGroup, removeCollapsedGroup
from utils.settings import Settings
from utils.globals import GlobalData
from utils.misc import preResolveLinkPath, getDefaultFileDoc
from .flowuireplacetextdlg import ReplaceTextDialog
from .customcolordlg import CustomColorsDialog
from .flowuidoceditdlg import DocLinkAnchorDialog


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
        self.__ccSubmenuAction = self.commonMenu.addMenu(
            self.__initCustomColorsContextMenu())
        self.__rtSubmenuAction = self.commonMenu.addMenu(
            self.__initReplaceTextContextMenu())
        self.__docSubmenuAction = self.commonMenu.addMenu(
            self.__initDocContextMenu())
        self.__groupAction = self.commonMenu.addAction(
            getIcon("cfgroup.png"), "Group...", self.onGroup)

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

        self.individualMenus[IfCell] = ifContextMenu
        self.individualMenus[OpenedGroupBegin] = self.__initOpenGroupContextMenu()
        self.individualMenus[CollapsedGroup] = self.__initCloseGroupContextMenu()
        self.individualMenus[EmptyGroup] = self.__initEmptyGroupContextMenu()

        # Individual items specific menu: end

        # Menu for a group of selected items
        self.groupMenu = QMenu()

    def __initOpenGroupContextMenu(self):
        """Creates the open group context menu"""
        ogMenu = QMenu()
        ogMenu.addAction(getIcon("collapse.png"), "Collapse", self.onGroupCollapse)
        ogMenu.addAction(getIcon("replacetitle.png"), "Edit title...", self.onGroupEditTitle)
        ogMenu.addAction(getIcon("ungroup.png"), "Ungroup", self.onGroupUngroup)
        return ogMenu

    def __initCloseGroupContextMenu(self):
        """Creates the closed group context menu"""
        cgMenu = QMenu()
        cgMenu.addAction(getIcon("expand.png"), "Expand", self.onGroupExpand)
        cgMenu.addAction(getIcon("replacetitle.png"), "Edit title...", self.onGroupEditTitle)
        cgMenu.addAction(getIcon("ungroup.png"), "Ungroup", self.onGroupUngroup)
        return cgMenu

    def __initEmptyGroupContextMenu(self):
        """Creates the empty group context menu"""
        egMenu = QMenu()
        egMenu.addAction(getIcon("replacetitle.png"), "Edit title...", self.onGroupEditTitle)
        egMenu.addAction(getIcon("ungroup.png"), "Ungroup", self.onGroupUngroup)
        return egMenu

    def __initCustomColorsContextMenu(self):
        """Create the custom colors submenu"""
        self.__customColorsSubmenu = QMenu('Custom colors')
        self.__customColorsSubmenu.setIcon(getIcon('customcolorsmenu.png'))
        self.__ccAction = self.__customColorsSubmenu.addAction(
            getIcon("customcolors.png"), "Custom colors...",
            self.onCustomColors)
        self.__customColorsSubmenu.addSeparator()
        self.__removeCCAction = self.__customColorsSubmenu.addAction(
            getIcon('trash.png'), 'Remove custom colors',
            self.onRemoveCustomColors)
        return self.__customColorsSubmenu

    def __initReplaceTextContextMenu(self):
        """Create the Replace text submenu"""
        self.__replaceTextSubmenu = QMenu('Replace text')
        self.__replaceTextSubmenu.setIcon(getIcon('replacetextmenu.png'))
        self.__rtAction = self.__replaceTextSubmenu.addAction(
            getIcon("replacetitle.png"), "Replace text...",
            self.onReplaceText)
        self.__replaceTextSubmenu.addSeparator()
        self.__removeRTAction = self.__replaceTextSubmenu.addAction(
            getIcon('trash.png'), 'Remove replacement text',
            self.onRemoveReplacementText)
        return self.__replaceTextSubmenu

    def __initDocContextMenu(self):
        """Create the Documentation submenu"""
        self.__docSubmenu = QMenu('Documentation')
        self.__docSubmenu.setIcon(getIcon('markdown.png'))
        self.__editDocAction = self.__docSubmenu.addAction(
            getIcon('replacetitle.png'), 'Add/edit doc link/anchor...',
            self.onEditDoc)
        self.__autoDocActon = self.__docSubmenu.addAction(
            getIcon('createdoc.png'),
            'Create doc file, add link and open for editing',
            self.onAutoAddDoc)
        self.__docSubmenu.addSeparator()
        self.__removeDocAction = self.__docSubmenu.addAction(
            getIcon('trash.png'), 'Remove doc link/anchor',
            self.onRemoveDoc)
        return self.__docSubmenu

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

    def __destroyDynamicMenu(self):
        """Properly cleans up the menu memory"""
        if self.menu is not None:
            self.menu.deleteLater()
            self.menu = None

    def __buildIndividualMenu(self, item):
        """Builds a context menu for the given item"""
        self.__destroyDynamicMenu()
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
        self.__destroyDynamicMenu()
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
        totalComments = self.countComments()
        hasComment = totalComments > 0
        hasDocstring = self.isDocstringInSelection()
        hasMinimizedExcepts = self.isInSelected([(CellElement.SCOPE_EXCEPT_BADGE,
                                                  None)])
        # Doc links are considered comments as well
        totalDocLinks = self.countInSelected([(CellElement.INDEPENDENT_DOC, None),
                                              (CellElement.LEADING_DOC, None),
                                              (CellElement.ABOVE_DOC, None)])
        totalNonDocComments = totalComments - totalDocLinks

        totalGroups = sum(self.countGroups())
        count = len(self.selectedItems())
        totalCCGroups = sum(self.countGroupsWithCustomColors())
        totalCCDocs = self.countDocWithCustomColors()
        minimizedCount = self.countMinimizedItems()

        self.__ccAction.setEnabled(totalNonDocComments == 0 and
                                   not hasMinimizedExcepts)
        self.__removeCCAction.setEnabled(
            self.countItemsWithCML(CMLcc) + totalCCGroups + totalCCDocs == count)
        self.__customColorsSubmenu.setEnabled(self.__ccAction.isEnabled() or
                                              self.__removeCCAction.isEnabled())

        self.__rtAction.setEnabled(not hasComment and
                                   not hasDocstring and
                                   not hasMinimizedExcepts and
                                   totalDocLinks == 0 and
                                   totalGroups == 0)
        self.__removeRTAction.setEnabled(
            self.countItemsWithCML(CMLrt) == count)
        self.__replaceTextSubmenu.setEnabled(self.__rtAction.isEnabled() or
                                             self.__removeRTAction.isEnabled())

        self.__groupAction.setEnabled(self.__canBeGrouped())

        itemsWithDocCML = self.countItemsWithCML(CMLdoc)
        self.__removeDocAction.setEnabled(
            totalDocLinks + itemsWithDocCML == count)
        if count != 1 or totalNonDocComments != 0 or hasDocstring or \
                totalGroups != 0 or minimizedCount > 0:
            self.__editDocAction.setEnabled(False)
            self.__autoDocActon.setEnabled(False)
        else:
            self.__editDocAction.setEnabled(True)
            fileName = None
            editor = self.selectedItems()[0].getEditor()
            if editor:
                fileName = editor._parent.getFileName()
            self.__autoDocActon.setEnabled(
                fileName is not None and totalDocLinks + itemsWithDocCML == 0)
        self.__docSubmenu.setEnabled(self.__removeDocAction.isEnabled() or
                                     self.__editDocAction.isEnabled() or
                                     self.__autoDocActon.isEnabled())

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
        dlg = CustomColorsDialog(bgcolor, fgcolor, bordercolor, self.parent())
        if dlg.exec_():
            bgcolor = dlg.backgroundColor()
            fgcolor = dlg.foregroundColor()
            bordercolor = dlg.borderColor()

            editor = self.selectedItems()[0].getEditor()
            with editor:
                # Add colors is done via delete/insert for the Doc and group
                # items. So it is safer to do first because the cc comment may be
                # in a set of selected which is inserted before the doc cml and
                # thus breaks the line numbering
                for item in self.selectedItems():
                    if item.isCMLDoc():
                        # The doc always exists so just add/change the colors
                        item.cmlRef.updateCustomColors(editor, bgcolor,
                                                       fgcolor, bordercolor)
                        continue
                    if item.isGroupItem():
                        # The group always exists so just add/change the colors
                        item.groupBeginCMLRef.updateCustomColors(editor,
                                                                 bgcolor,
                                                                 fgcolor,
                                                                 bordercolor)

                for item in self.sortSelectedReverse():
                    if item.isCMLDoc() or item.isGroupItem():
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
        previousText = None
        if len(self.selectedItems()) == 1:
            previousText = ''
            cmlComment = CMLVersion.find(
                self.selectedItems()[0].ref.leadingCMLComments, CMLrt)
            if cmlComment is not None:
                previousText = cmlComment.getText()
                dlg.setText(previousText)

        if dlg.exec_():
            replacementText = dlg.text()
            if previousText == replacementText:
                return

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
            # Remove colors is done via delete/insert for the Doc and group
            # items. So it is safer to do first because the cc comment may be
            # in a set of selected which is inserted before the doc cml and
            # thus breaks the line numbering
            for item in self.selectedItems():
                # The doc always exists
                if item.isCMLDoc():
                    item.cmlRef.removeCustomColors(editor)
                    continue
                # The group always exists
                if item.isGroupItem():
                    item.groupBeginCMLRef.removeCustomColors(editor)

            # Now handle the rest of items
            for item in self.sortSelectedReverse():
                if item.isCMLDoc() or item.isGroupItem():
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
        if self.__actionPrerequisites():
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

    def __createDocFile(self, link, fromFile):
        """Creates the doc file if needed"""
        fName, _, errMsg = preResolveLinkPath(link, fromFile, True)
        if errMsg:
            logging.error(errMsg)
            return None

        if os.path.exists(fName):
            return fName

        try:
            os.makedirs(os.path.dirname(fName), exist_ok=True)
            with open(fName, 'w') as f:
                pass
        except Exception as exc:
            logging.error('Error creating the documentation file ' +
                          fName + ': ' + str(exc))
            return None
        return fName

    def onEditDoc(self):
        """Editing the CML doc comment"""
        if not self.__actionPrerequisites():
            return

        selectedItem = self.selectedItems()[0]  # Exactly one is selected
        editor = selectedItem.getEditor()
        fileName = editor._parent.getFileName()
        if not fileName:
            fileName = editor._parent.getShortName()

        # It could be a CML doc or an item which has a CML doc
        if selectedItem.isComment():
            cmlRef = selectedItem.cmlRef
        else:
            # If not found then it means the doc link needs to be created
            cmlRef = self.__findCMLinItem(selectedItem, CMLdoc)

        dlg = DocLinkAnchorDialog('Add' if cmlRef is None else 'Edit',
                                  cmlRef, fileName, self.parent())
        if dlg.exec_():
            link = dlg.linkEdit.text().strip()
            anchor = dlg.anchorEdit.text().strip()
            title = dlg.title()
            needToCreate = dlg.needToCreate()

            # First create a file if asked
            if needToCreate:
                docFileName = self.__createDocFile(link, fileName)
                if not docFileName:
                    return

            selection = self.serializeSelection()
            with editor:
                # Now insert a new cml comment or update existing
                if cmlRef:
                    # It is editing, the comment exists
                    lineNo = cmlRef.ref.beginLine
                    pos = cmlRef.ref.beginPos
                    cmlRef.removeFromText(editor)
                    bgColor = cmlRef.bgColor
                    fgColor = cmlRef.fgColor
                    border = cmlRef.border
                else:
                    # It is a new doc link
                    lineNo = selectedItem.getFirstLine()
                    pos = selectedItem.ref.body.beginPos
                    bgColor = None
                    fgColor = None
                    border = None

                line = CMLdoc.generate(link, anchor, title,
                                       bgColor, fgColor, border, pos)
                editor.insertLines(line, lineNo)

            QApplication.processEvents()
            self.parent().redrawNow()
            self.restoreSelectionByID(selection)

    @staticmethod
    def __getAutoDocFileName(fileName):
        """Forms the auto doc file name"""
        # Markdown is used as a default documentation format
        fBaseName = os.path.basename(fileName)
        if '.' in fBaseName:
            fileExtension = fBaseName.split('.')[-1]
            fBaseName = fBaseName[:-len(fileExtension)] + 'md'
        else:
            fBaseName += '.md'

        project = GlobalData().project
        if project.isProjectFile(fileName):
            projectDir = project.getProjectDir()
            relativePath = fileName[len(projectDir):]
            projectName = project.getProjectName()
            if relativePath.startswith(projectName):
                relativePath = relativePath.replace(projectName, '', 1)
            return os.path.normpath(
                os.path.sep.join([projectDir + 'doc',
                                  os.path.dirname(relativePath),
                                  fBaseName]))
        return os.path.normpath(
            os.path.sep.join([os.path.dirname(fileName),
                              'doc',
                               fBaseName]))

    def onAutoAddDoc(self):
        """Create a doc file, add a link and open for editing"""
        if not self.__actionPrerequisites():
            return

        selectedItem = self.selectedItems()[0]  # Exactly one is selected
        editor = selectedItem.getEditor()
        fileName = editor._parent.getFileName()
        if not fileName:
            logging.error('Save file before invoking auto doc')
            return

        needContent = False
        newAnchor = 'doc' + str(uuid.uuid4().fields[-1])[-6:]

        docFileName = self.__getAutoDocFileName(fileName)
        if not os.path.exists(docFileName):
            # Create file and populate with the default content
            try:
                os.makedirs(os.path.dirname(docFileName), exist_ok=True)
                with open(docFileName, 'w') as f:
                    pass
            except Exception as exc:
                logging.error('Error creating the documentation file ' +
                              docFileName + ': ' + str(exc))
                return
            needContent = True

        project = GlobalData().project
        if project.isProjectFile(docFileName):
            linkFromFile = project.getRelativePath(docFileName)
            if project.isProjectFile(fileName):
                linkFromDoc = project.getRelativePath(fileName)
            else:
                linkFromDoc = os.path.relpath(fileName,
                                              os.path.dirname(docFileName))
        else:
            linkFromFile = os.path.relpath(docFileName,
                                           os.path.dirname(fileName))
            linkFromDoc = os.path.relpath(fileName,
                                          os.path.dirname(docFileName))


        # Insert a doc link
        with editor:
            if self.__isModuleSelected():
                lineNo = 1
                if selectedItem.ref.encodingLine:
                    lineNo += 1
                if selectedItem.ref.bangLine:
                    lineNo += 1
            else:
                lineNo = selectedItem.getFirstLine()
            line = CMLdoc.generate(linkFromFile, newAnchor, 'See documentation',
                                   None, None, None,
                                   selectedItem.ref.body.beginPos)
            editor.insertLines(line, lineNo)

            QApplication.processEvents()
            self.parent().redrawNow()

        # Open the file
        if GlobalData().mainWindow.openFile(docFileName, -1):
            if needContent:
                widget = GlobalData().mainWindow.em.getWidgetForFileName(docFileName)
                editor = widget.getEditor()
                editor.text = getDefaultFileDoc(linkFromDoc, newAnchor)
                editor.document().setModified(False)

    def onRemoveDoc(self):
        """Removing the CML doc comment"""
        if not self.__actionPrerequisites():
            return

        editor = self.selectedItems()[0].getEditor()
        with editor:
            for item in self.sortSelectedReverse():
                cmlComment = CMLVersion.find(item.ref.leadingCMLComments,
                                             CMLdoc)
                if cmlComment is not None:
                    cmlComment.removeFromText(editor)
        QApplication.processEvents()
        self.parent().redrawNow()

    def countInSelected(self, matchList):
        """Counts the number of matching items in selection"""
        # match is a list of pairs [kind, subKind]
        #   None would mean 'match any'
        count = 0
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
                    count += 1
        return count

    def isInSelected(self, matchList):
        """Checks if any if the match list items is in the selection"""
        return self.countInSelected(matchList) > 0

    def isDocstringInSelection(self):
        """True if a docstring item in the selection"""
        for item in self.selectedItems():
            if item.isDocstring():
                return True
        return False

    def countComments(self):
        """Count comments in selection"""
        count = 0
        for item in self.selectedItems():
            if item.isComment():
                count += 1
        return count

    def isCommentInSelection(self):
        """True if a comment item in the selection"""
        return self.countComments() > 0

    def countItemsWithCML(self, cmlType):
        """Counts items with have a certain type of a CML comment"""
        count = 0
        for item in self.selectedItems():
            if self.__findCMLinItem(item, cmlType) is not None:
                count += 1
        return count

    def __findCMLinItem(self, item, cmlType):
        """Finds a related CML item"""
        if item.isComment():
            # Doc links are comments so they are skipped here
            return None
        if item.isDocstring():
            # Side comments for docstrings? Nonesense! So they are ignored
            # even if they are collected
            if item.kind == CellElement.SCOPE_DOCSTRING_BADGE:
                docstr = item.ref.ref.docstring
            else:
                docstr = item.ref.docstring
            cml = CMLVersion.find(docstr.leadingCMLComments, cmlType)
            if cml is not None:
                return cml

        if hasattr(item.ref, 'leadingCMLComments'):
            cml = CMLVersion.find(item.ref.leadingCMLComments, cmlType)
            if cml is not None:
                return cml
        if hasattr(item.ref, 'sideCMLComments'):
            cml = CMLVersion.find(item.ref.sideCMLComments, cmlType)
            if cml is not None:
                return cml
        return None

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

    def countDocWithCustomColors(self):
        count = 0
        for item in self.selectedItems():
            if item.isCMLDoc():
                if item.cmlRef.bgColor is not None or \
                   item.cmlRef.fgColor is not None or \
                   item.cmlRef.border is not None:
                    count += 1
        return count

    def countMinimizedItems(self):
        count = 0
        for item in self.selectedItems():
            if item.isMinimizedItem():
                count += 1
        return count

    def sortSelectedReverse(self):
        """Sorts the selected items in reverse order"""
        result = []
        for item in self.selectedItems():
            for index in range(len(result)):
                if self.itemAbsPosLess(result[index], item):
                    result.insert(index, item)
                    break
            else:
                result.append(item)
        return result

    @staticmethod
    def itemAbsPosLess(lhs, rhs):
        lhsBegin, lhsEnd = lhs.getAbsPosRange()
        rhsBegin, rhsEnd = rhs.getAbsPosRange()

        if lhsBegin < rhsBegin:
            return True
        if lhsBegin == rhsBegin:
            return lhsEnd < rhsEnd
        return False

    def sortSelected(self, selected):
        """Sorts the selected items in direct order"""
        result = []
        for item in selected:
            for index in range(len(result)):
                if self.itemAbsPosLess(item, result[index]):
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
        if self.__areAllSelectedDependentComments():
            return False
        if self.__areScopeDocstringSelected():
            return False
        if self.__isModuleSelected():
            return False
        if self.__areHangingDependentSelected():
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

    def __areAllSelectedDependentComments(self):
        """True if all selected items are comments"""
        for item in self.selectedItems():
            if item.kind not in [CellElement.SIDE_COMMENT,
                                 CellElement.LEADING_COMMENT,
                                 CellElement.ABOVE_COMMENT,
                                 CellElement.LEADING_DOC,
                                 CellElement.ABOVE_DOC]:
                return False
        return True

    def __areScopeDocstringSelected(self):
        for item in self.selectedItems():
            if item.scopedItem():
                if item.subKind in [ScopeCellElement.DOCSTRING]:
                    return True
        return False

    def __isModuleSelected(self):
        """True if the whole module is selected"""
        for item in self.selectedItems():
            if item.kind == CellElement.FILE_SCOPE:
                return True
        return False

    def __areHangingDependentSelected(self):
        """True if e.g. a comment or doc is selected but the item is not"""
        scopeBadges = (CellElement.SCOPE_EXCEPT_BADGE,
                       CellElement.SCOPE_DOCSTRING_BADGE,
                       CellElement.SCOPE_COMMENT_BADGE,
                       CellElement.SCOPE_DECORATOR_BADGE,
                       CellElement.SCOPE_DOCLINK_BADGE)
        docAndComments = (CellElement.LEADING_COMMENT,
                          CellElement.SIDE_COMMENT,
                          CellElement.ABOVE_COMMENT,
                          CellElement.LEADING_DOC,
                          CellElement.ABOVE_DOC)
        for item in self.selectedItems():
            if item.kind in scopeBadges:
                if not item.ref.isSelected():
                    return True
            elif item.kind in docAndComments:
                for relatedItem in self.findItemsForRef(item.ref):
                    if relatedItem.kind in scopeBadges:
                        continue
                    if relatedItem.kind in docAndComments:
                        continue
                    if not relatedItem.isSelected():
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
            elif item.kind in [CellElement.FUNC_SCOPE,
                               CellElement.CLASS_SCOPE]:
                if item.ref.decorators:
                    s = item.canvas.settings
                    if not s.noDecor and not s.hidedecors:
                        # Full decorators are drawn
                        for decor in item.ref.decorators:
                            for relatedItem in self.findItemsForRef(decor):
                                if relatedItem not in selected:
                                    return True
            elif item.kind in [CellElement.DECORATOR]:
                if not item.scopeItem.isSelected():
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
                        if tryItem.kind == CellElement.SCOPE_EXCEPT_BADGE:
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
            elif item.kind == CellElement.SCOPE_EXCEPT_BADGE:
                # here: no except blocks on the diagram, they are collapsed
                tryItems = self.findItemsForRef(item.ref.ref)
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
            if not item.isComment() and not item.isCMLDoc() and not self.isOpenGroupItem(item):
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

        if first.kind == CellElement.OPENED_GROUP_BEGIN:
            firstLine = first.groupBeginCMLRef.ref.parts[0].beginLine
            pos = first.groupBeginCMLRef.ref.parts[0].beginPos
        else:
            firstLine = first.getLineRange()[0]
            if first.kind in [CellElement.SCOPE_DOCSTRING_BADGE,
                              CellElement.SCOPE_COMMENT_BADGE,
                              CellElement.SCOPE_EXCEPT_BADGE,
                              CellElement.SCOPE_DECORATOR_BADGE,
                              CellElement.SCOPE_DOCLINK_BADGE]:
                pos = first.beginPos
            else:
                pos = first.ref.beginPos

        lastLine = -1
        for item in selected:
            if item.scopedItem():
                lastLine = max(lastLine, item.ref.endLine)
            elif item.kind == CellElement.OPENED_GROUP_BEGIN:
                lastLine = max(lastLine,
                               item.groupEndCMLRef.ref.parts[-1].endLine)
            else:
                lastLine = max(lastLine, item.getLineRange()[1])

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
                    if not isinstance(item, CellElement):
                        continue
                    if item.isProxyItem():
                        continue
                    if item.scopedItem():
                        if item.subKind not in [ScopeCellElement.TOP_LEFT,
                                                ScopeCellElement.DOCSTRING]:
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
            if not isinstance(item, CellElement):
                continue
            if item.isProxyItem():
                continue
            if item.scopedItem():
                if item.subKind not in [ScopeCellElement.TOP_LEFT,
                                        ScopeCellElement.DOCSTRING]:
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
                elif item.kind in [CellElement.INDEPENDENT_DOC,
                                   CellElement.LEADING_DOC,
                                   CellElement.ABOVE_DOC]:
                    branchId = item.cmlRef.ref.getParentIfID()
                elif item.kind in [CellElement.SCOPE_DOCSTRING_BADGE,
                                   CellElement.SCOPE_COMMENT_BADGE,
                                   CellElement.SCOPE_EXCEPT_BADGE,
                                   CellElement.SCOPE_DECORATOR_BADGE,
                                   CellElement.SCOPE_DOCLINK_BADGE,
                                   CellElement.INDEPENDENT_MINIMIZED_DOC]:
                    branchId = item.ref.ref.getParentIfID()
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

    def terminateMenus(self):
        """Called when a tab is closed"""
        self.sceneMenu.deleteLater()
        self.commonMenu.deleteLater()
        self.groupMenu.deleteLater()
        self.__destroyDynamicMenu()

        for menu in self.individualMenus.values():
            menu.deleteLater()

