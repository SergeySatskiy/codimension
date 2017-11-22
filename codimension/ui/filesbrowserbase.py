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

"""Base and auxiliary classes for FS and project browsers"""

import os.path
import logging
from utils.globals import GlobalData
from utils.pixmapcache import getIcon
from utils.fileutils import isPythonMime, isCDMProjectMime, getFileProperties
from utils.project import getProjectFileTooltip
from .qt import (Qt, QModelIndex, QSortFilterProxyModel, QAbstractItemView,
                 QApplication, QTreeView, pyqtSignal)
from .viewitems import (DirectoryItemType, SysPathItemType, GlobalsItemType,
                        ImportsItemType, FunctionsItemType, ClassesItemType,
                        StaticAttributesItemType, InstanceAttributesItemType,
                        CodingItemType, ImportItemType, FileItemType,
                        FunctionItemType, ClassItemType, DecoratorItemType,
                        AttributeItemType, GlobalItemType, ImportWhatItemType,
                        TreeViewDirectoryItem, TreeViewFileItem,
                        TreeViewCodingItem, TreeViewGlobalsItem,
                        TreeViewGlobalItem, TreeViewImportsItem,
                        TreeViewImportItem, TreeViewWhatItem,
                        TreeViewFunctionsItem, TreeViewClassesItem)
from .itemdelegates import NoOutlineHeightDelegate
from .parsererrors import ParserErrorsDialog
from .findinfiles import FindInFilesDialog


class FilesBrowserSortFilterProxyModel(QSortFilterProxyModel):

    """Files (filesystem and project) browser sort filter proxy model.

    It allows filtering basing on top level items.
    """

    def __init__(self, isProjectFilter, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.__sortColumn = None    # Avoid pylint complains
        self.__sortOrder = None     # Avoid pylint complains
        self.__shouldFilter = isProjectFilter

    def sort(self, column, order):
        """Sorts the items"""
        self.__sortColumn = column
        self.__sortOrder = order
        QSortFilterProxyModel.sort(self, column, order)

    def lessThan(self, left, right):
        """Sorts the displayed items"""
        lhs = left.model() and left.model().item(left) or None
        rhs = right.model() and right.model().item(right) or None

        if lhs and rhs:
            return lhs.lessThan(rhs, self.__sortColumn, self.__sortOrder)
        return False

    def item(self, index):
        """Provides a reference to the item"""
        if not index.isValid():
            return None

        sourceIndex = self.mapToSource(index)
        return self.sourceModel().item(sourceIndex)

    def hasChildren(self, parent=QModelIndex()):
        """Checks the presence of the child items"""
        sourceIndex = self.mapToSource(parent)
        return self.sourceModel().hasChildren(sourceIndex)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """Filters rows"""
        if not self.__shouldFilter:
            return True     # Show everything

        # Filter using the loaded project filter
        if not sourceParent.isValid():
            return True

        item = sourceParent.internalPointer().child(sourceRow)
        return not GlobalData().project.shouldExclude(item.data(0))


class FilesBrowser(QTreeView):

    """Common functionality of the FS and project browsers"""

    sigFirstSelectedItem = pyqtSignal(QModelIndex)

    def __init__(self, sourceModel, isProjectFilter, parent=None):
        QTreeView.__init__(self, parent)

        self.__model = sourceModel
        self.__sortModel = FilesBrowserSortFilterProxyModel(isProjectFilter)
        self.__sortModel.setSourceModel(self.__model)
        self.setModel(self.__sortModel)

        self.activated.connect(self.openSelectedItem)
        self.expanded.connect(self._resizeColumns)
        self.collapsed.connect(self._resizeColumns)

        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setItemDelegate(NoOutlineHeightDelegate(4))

        header = self.header()
        header.setSortIndicator(0, Qt.AscendingOrder)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)

        self.setSortingEnabled(True)

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.header().setStretchLastSection(True)
        self.layoutDisplay()

        self.__debugMode = False

    def layoutDisplay(self):
        """Performs the layout operation"""
        self._resizeColumns(QModelIndex())
        self._resort()

    def _resizeColumns(self, index):
        """Resizes the view when items get expanded or collapsed"""
        del index   # unused argument
        # rowCount = self.model().rowCount()
        self.header().setStretchLastSection(True)

        width = max(100, self.sizeHintForColumn(0))
        self.header().resizeSection(0, width)

    def _resort(self):
        """Re-sorts the tree"""
        self.model().sort(self.header().sortIndicatorSection(),
                          self.header().sortIndicatorOrder())

    def mouseDoubleClickEvent(self, mouseEvent):
        """Reimplemented to disable expanding/collapsing of items on dbl click.

        Instead the double-clicked entry is opened.
        """
        index = self.indexAt(mouseEvent.pos())
        if not index.isValid():
            return

        item = self.model().item(index)
        if item.itemType in [GlobalsItemType,
                             ImportsItemType, FunctionsItemType,
                             ClassesItemType, StaticAttributesItemType,
                             InstanceAttributesItemType,
                             DirectoryItemType, SysPathItemType]:
            QTreeView.mouseDoubleClickEvent(self, mouseEvent)
        else:
            self.openItem(item)

    def openSelectedItem(self):
        """Triggers when an item is clicked or double clicked"""
        item = self.model().item(self.currentIndex())
        self.openItem(item)

    def highlightItem(self, path):
        """Highlights an item which matches the given path"""
        # Find the top level item first
        startItem = None
        srcModel = self.model().sourceModel()
        for treeItem in srcModel.rootItem.childItems:
            itemPath = treeItem.getPath()
            if itemPath != "" and path.startswith(itemPath):
                startItem = treeItem
                break
        if startItem is None:
            return False

        if not os.path.exists(path):
            return False

        # Here: the start item has been found and the file exists for sure
        index = srcModel.buildIndex(startItem.getRowPath())
        self.setExpanded(self.model().mapFromSource(index), True)

        parts = path[len(itemPath):].split(os.path.sep)
        dirs = parts[:-1]
        fName = parts[-1]

        for dirName in dirs:
            # find the dirName in the item and make it the current item
            found = False
            for treeItem in startItem.childItems:
                if str(treeItem.data(0)) == dirName:
                    startItem = treeItem
                    found = True
                    # Need to expand regardless it is populated or not because
                    # a dir could be populated but not expanded.
                    index = srcModel.buildIndex(startItem.getRowPath())
                    self.setExpanded(self.model().mapFromSource(index), True)
                    break
            if found:
                continue
            return False

        # Here: all the dirs have been found and they are expanded
        if fName == '':
            # It was a directory item, so there is no need to highlight,
            # it was just expanding dirs request.
            return False

        for treeItem in startItem.childItems:
            if str(treeItem.data(0)) == fName:
                # Found the item to highlight
                index = srcModel.buildIndex(treeItem.getRowPath())
                self.setCurrentIndex(self.model().mapFromSource(index))
                self.setFocus()
                return True

        return False

    def getExpanded(self):
        """Provides a list of paths which are currently expanded"""
        expandedPaths = []
        srcModel = self.model().sourceModel()
        self.__getExpanded(srcModel, srcModel.rootItem, expandedPaths)
        expandedPaths.sort()
        return expandedPaths

    def __getExpanded(self, srcModel, item, paths):
        """Provides a list of the expanded dirs in the files tree"""
        for treeItem in item.childItems:
            if treeItem.itemType not in [DirectoryItemType, SysPathItemType]:
                continue
            index = srcModel.buildIndex(treeItem.getRowPath())
            if self.isExpanded(self.model().mapFromSource(index)):
                paths.append(treeItem.getPath())
                self.__getExpanded(srcModel, treeItem, paths)

    @staticmethod
    def openItem(item):
        """Handles the case when an item is activated"""
        if item.itemType in [GlobalsItemType,
                             ImportsItemType, FunctionsItemType,
                             ClassesItemType, StaticAttributesItemType,
                             InstanceAttributesItemType,
                             DirectoryItemType, SysPathItemType]:
            return

        if item.itemType == FileItemType:
            if item.fileType is None:
                return
            if 'broken-symlink' in item.fileType:
                return

            itemPath = item.getPath()
            if not os.path.exists(itemPath):
                logging.error("Cannot open " + itemPath)
                return

            if os.path.islink(itemPath):
                # Convert it to the real path and the decide what to do
                itemPath = os.path.realpath(itemPath)
                # The type may differ...
                itemMime, _, _ = getFileProperties(itemPath)
            else:
                # The intermediate directory could be a link, so use the real
                # path
                itemPath = os.path.realpath(itemPath)
                itemMime = item.fileType

            GlobalData().mainWindow.openFileByType(itemMime, itemPath, -1)
            return

        if item.itemType in [CodingItemType, ImportItemType, FunctionItemType,
                             ClassItemType, DecoratorItemType,
                             AttributeItemType, GlobalItemType,
                             ImportWhatItemType]:
            GlobalData().mainWindow.openFile(os.path.realpath(item.getPath()),
                                             item.sourceObj.line)

    def copyToClipboard(self):
        """Copies the path to the file where the element is to the clipboard"""
        item = self.model().item(self.currentIndex())
        path = item.getPath()
        QApplication.clipboard().setText(path)

    @staticmethod
    def showParsingErrors(path):
        """Fires the show errors dialog window"""
        try:
            dialog = ParserErrorsDialog(path)
            dialog.exec_()
        except Exception as ex:
            logging.error(str(ex))

    def findInDirectory(self):
        """Find in directory popup menu handler"""
        index = self.currentIndex()
        searchDir = self.model().item(index).getPath()

        dlg = FindInFilesDialog(FindInFilesDialog.IN_DIRECTORY, "", searchDir)
        dlg.exec_()
        if dlg.searchResults:
            GlobalData().mainWindow.displayFindInFiles(dlg.searchRegexp,
                                                       dlg.searchResults)

    def selectionChanged(self, selected, deselected):
        """Triggered when the selection changed"""
        QTreeView.selectionChanged(self, selected, deselected)
        indexesList = selected.indexes()
        if indexesList:
            self.sigFirstSelectedItem.emit(indexesList[0])
        else:
            self.sigFirstSelectedItem.emit(QModelIndex())

    def _onFSChanged(self, items):
        """Triggered when the project files set has been changed"""
        itemsToDel = []
        itemsToAdd = []
        for item in items:
            item = str(item)
            if item.startswith('-'):
                itemsToDel.append(item[1:])
            else:
                itemsToAdd.append(item[1:])
        itemsToDel.sort()
        itemsToAdd.sort()

        # It is important that items are deleted first and then new are added!
        for item in itemsToDel:
            dirname, basename = self._splitPath(item)

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self._delFromTree(treeItem, dirname, basename)

        for item in itemsToAdd:
            dirname, basename = self._splitPath(item)

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__addToTree(treeItem, item, dirname, basename)

        self.layoutDisplay()

    def __addToTree(self, treeItem, item, dirname, basename):
        """Recursive function which adds an item to the displayed tree"""
        # treeItem is always of the directory type
        if not treeItem.populated:
            return

        srcModel = self.model().sourceModel()
        treePath = treeItem.getPath()
        if treePath != "":
            # Guard for the sys.path item
            treePath = os.path.realpath(treePath) + os.path.sep
        if treePath == dirname:
            # Need to add an item but only if there is no this item already!
            foundInChildren = False
            for i in treeItem.childItems:
                if basename == i.data(0):
                    foundInChildren = True
                    break

            if not foundInChildren:
                if item.endswith(os.path.sep):
                    newItem = TreeViewDirectoryItem(
                        treeItem, treeItem.getPath() + basename, False)
                else:
                    newItem = TreeViewFileItem(treeItem,
                                               treeItem.getPath() + basename)
                parentIndex = srcModel.buildIndex(treeItem.getRowPath())
                srcModel.addItem(newItem, parentIndex)

        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                self.__addToTree(i, item, dirname, basename)
            elif i.isLink:
                # Check if it was a broken link to the newly appeared item
                if os.path.realpath(i.getPath()) == dirname + basename:
                    # Update the link status
                    i.updateLinkStatus(i.getPath())
                    self._signalItemUpdated(i)

    def _delFromTree(self, treeItem, dirname, basename):
        """Recursive function which deletes an item from the displayed tree"""
        # treeItem is always of the directory type
        srcModel = self.model().sourceModel()

        d_dirname, d_basename = self._splitPath(treeItem.getPath())
        if d_dirname == dirname and d_basename == basename:
            index = srcModel.buildIndex(treeItem.getRowPath())
            srcModel.beginRemoveRows(index.parent(), index.row(), index.row())
            treeItem.parentItem.removeChild(treeItem)
            srcModel.endRemoveRows()
            return

        if treeItem.isLink:
            # Link to a directory
            if os.path.realpath(treeItem.getPath()) == dirname + basename:
                # Broken link now
                treeItem.updateStatus()
                self._signalItemUpdated(treeItem)
                return

        # Walk the directory items
        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                # directory
                self._delFromTree(i, dirname, basename)
            else:
                # file
                if i.isLink:
                    l_dirname, l_basename = self._splitPath(i.getPath())
                    if dirname == l_dirname and basename == l_basename:
                        index = srcModel.buildIndex(i.getRowPath())
                        srcModel.beginRemoveRows(index.parent(),
                                                 index.row(), index.row())
                        i.parentItem.removeChild(i)
                        srcModel.endRemoveRows()
                    elif os.path.realpath(i.getPath()) == dirname + basename:
                        i.updateLinkStatus(i.getPath())
                        self._signalItemUpdated(i)
                else:
                    # Regular final file
                    if os.path.realpath(i.getPath()) == dirname + basename:
                        index = srcModel.buildIndex(i.getRowPath())
                        srcModel.beginRemoveRows(index.parent(),
                                                 index.row(), index.row())
                        i.parentItem.removeChild(i)
                        srcModel.endRemoveRows()

    @staticmethod
    def _splitPath(path):
        """Provides the dirname and the base name"""
        if path.endswith(os.path.sep):
            # directory
            dirname = os.path.realpath(os.path.dirname(path[:-1])) + \
                      os.path.sep
            basename = os.path.basename(path[:-1])
        else:
            dirname = os.path.realpath(os.path.dirname(path)) + os.path.sep
            basename = os.path.basename(path)
        return dirname, basename

    def onFileUpdated(self, fileName, uuid):
        """Triggered when the file is updated"""
        del uuid    # unused argument
        mime, icon, _ = getFileProperties(fileName)
        if isPythonMime(mime):
            path = os.path.realpath(fileName)
            info = GlobalData().briefModinfoCache.get(path)
            if info.isOK:
                icon = getIcon('filepython.png')
            else:
                icon = getIcon('filepythonbroken.png')

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__walkTreeAndUpdate(treeItem, path, mime, icon, info)
        elif isCDMProjectMime(mime):
            path = os.path.realpath(fileName)
            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__walkTreeAndUpdate(treeItem, path, mime, None, None)
        elif fileName.endswith(".cgi"):
            path = os.path.realpath(fileName)

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__walkTreeAndUpdate(treeItem, path, mime, icon, None)

    def _signalItemUpdated(self, treeItem):
        """Emits a signal that an item is updated"""
        srcModel = self.model().sourceModel()
        index = srcModel.buildIndex(treeItem.getRowPath())
        srcModel.dataChanged.emit(index, index)

    def __removeTreeItem(self, treeItem):
        """Removes the given item"""
        srcModel = self.model().sourceModel()
        index = srcModel.buildIndex(treeItem.getRowPath())
        srcModel.beginRemoveRows(index.parent(), index.row(), index.row())
        treeItem.parentItem.removeChild(treeItem)
        srcModel.endRemoveRows()

    def __addTreeItem(self, treeItem, newItem):
        """Adds the given item"""
        srcModel = self.model().sourceModel()
        parentIndex = srcModel.buildIndex(treeItem.getRowPath())
        srcModel.addItem(newItem, parentIndex)
        self._resort()

    def __walkTreeAndUpdate(self, treeItem, path, mime, icon, info):
        """Recursively walks the tree items and updates the icon"""
        if treeItem.itemType in [DirectoryItemType, SysPathItemType]:
            for i in treeItem.childItems:
                if i.itemType in [DirectoryItemType,
                                  SysPathItemType, FileItemType]:
                    self.__walkTreeAndUpdate(i, path, mime, icon, info)

        if treeItem.itemType == FileItemType:
            if path == os.path.realpath(treeItem.getPath()):
                if isPythonMime(mime):
                    # Update icon
                    treeItem.setIcon(icon)
                    if info.docstring is None:
                        treeItem.toolTip = ""
                    else:
                        treeItem.toolTip = info.docstring.text
                    treeItem.parsingErrors = not info.isOK

                    self._signalItemUpdated(treeItem)

                    # Update content if populated
                    self.updateFileItem(treeItem, info)
                elif isCDMProjectMime(mime):
                    # Tooltip update only
                    treeItem.toolTip = getProjectFileTooltip(path)
                    self._signalItemUpdated(treeItem)
                elif path.endswith(".cgi"):
                    # It can only happened when python CGI is not a python any
                    # more. So display it a a general file.
                    # The case when a cgi became a python file is covered in
                    # the first branch of this if statement.
                    treeItem.setIcon(icon)
                    treeItem.toolTip = ""
                    self._signalItemUpdated(treeItem)

                    # Remove child items if so
                    while treeItem.childItems:
                        self.__removeTreeItem(treeItem.childItems[0])

    def updateFileItem(self, treeItem, info):
        """Updates the file item recursively"""
        hadCoding = False
        hadGlobals = False
        hadImports = False
        hadFunctions = False
        hadClasses = False
        itemsToRemove = []
        for fileChildItem in treeItem.childItems:
            if fileChildItem.itemType == CodingItemType:
                hadCoding = True
                if info.encoding is None:
                    itemsToRemove.append(fileChildItem)
                else:
                    fileChildItem.updateData(info.encoding)
                    self._signalItemUpdated(fileChildItem)
                continue
            elif fileChildItem.itemType == GlobalsItemType:
                hadGlobals = True
                if info.globals:
                    fileChildItem.updateData(info)
                    self.__updateGlobalsItem(fileChildItem, info.globals)
                else:
                    itemsToRemove.append(fileChildItem)
                continue
            elif fileChildItem.itemType == ImportsItemType:
                hadImports = True
                if info.imports:
                    fileChildItem.updateData(info)
                    self.__updateImportsItem(fileChildItem, info.imports)
                else:
                    itemsToRemove.append(fileChildItem)
                continue
            elif fileChildItem.itemType == FunctionsItemType:
                hadFunctions = True
                if info.functions:
                    fileChildItem.updateData(info)
                    self.model().sourceModel().updateFunctionsItem(
                        fileChildItem, info.functions)
                    self._resort()
                else:
                    itemsToRemove.append(fileChildItem)
                continue
            elif fileChildItem.itemType == ClassesItemType:
                hadClasses = True
                if info.classes:
                    fileChildItem.updateData(info)
                    self.model().sourceModel().updateClassesItem(fileChildItem,
                                                                 info.classes)
                    self._resort()
                else:
                    itemsToRemove.append(fileChildItem)
                continue

        for item in itemsToRemove:
            self.__removeTreeItem(item)

        if not hadCoding and treeItem.populated and \
           info.encoding is not None:
            # Coding item appeared, so we need to add it
            newItem = TreeViewCodingItem(treeItem, info.encoding)
            self.__addTreeItem(treeItem, newItem)

        if not hadGlobals and treeItem.populated and info.globals:
            # Globals item appeared, so we need to add it
            newItem = TreeViewGlobalsItem(treeItem, info)
            self.__addTreeItem(treeItem, newItem)

        if not hadImports and treeItem.populated and info.imports:
            # Imports item appeared, so we need to add it
            newItem = TreeViewImportsItem(treeItem, info)
            self.__addTreeItem(treeItem, newItem)

        if not hadFunctions and treeItem.populated and info.functions:
            # Functions item appeared, so we need to add it
            newItem = TreeViewFunctionsItem(treeItem, info)
            self.__addTreeItem(treeItem, newItem)

        if not hadClasses and treeItem.populated and info.classes:
            # Classes item appeared, so we need to add it
            newItem = TreeViewClassesItem(treeItem, info)
            self.__addTreeItem(treeItem, newItem)

    def __updateGlobalsItem(self, treeItem, globalsObj):
        """Updates globals item"""
        if not treeItem.populated:
            return

        existingGlobals = []
        itemsToRemove = []
        for globalItem in treeItem.childItems:
            name = globalItem.data(0)
            found = False
            for glob in globalsObj:
                if glob.name == name:
                    found = True
                    existingGlobals.append(name)
                    globalItem.updateData(glob)
                    # No need to send the update signal because the name is
                    # still the same
                    break
            if not found:
                # Disappeared item
                itemsToRemove.append(globalItem)

        for item in itemsToRemove:
            self.__removeTreeItem(item)

        # Add those which have been introduced
        for glob in globalsObj:
            if glob.name not in existingGlobals:
                newItem = TreeViewGlobalItem(treeItem, glob)
                self.__addTreeItem(treeItem, newItem)

    def __updateImportsItem(self, treeItem, importsObj):
        """Updates imports item"""
        if not treeItem.populated:
            return

        # Need to update item by item. There could be 2 import items with
        # the same name, so this stuff of a copied list.
        importsCopy = list(importsObj)
        itemsToRemove = []
        for importItem in treeItem.childItems:
            name = importItem.data(0)
            found = False
            for index in range(len(importsCopy)):
                if importsCopy[index].getDisplayName() == name:
                    found = True
                    importItem.updateData(importsCopy[index])
                    # No need to send the update signal because the name is
                    # still the same, but need to update the importwhat items
                    # if so
                    self.__updateSingleImportItem(importItem,
                                                  importsCopy[index])
                    del importsCopy[index]
                    break
            if not found:
                # Disappeared item
                itemsToRemove.append(importItem)

        for item in itemsToRemove:
            self.__removeTreeItem(item)

        # Add those which have been introduced
        for item in importsCopy:
            newItem = TreeViewImportItem(treeItem, item)
            self.__addTreeItem(treeItem, newItem)

    def __updateSingleImportItem(self, treeItem, importObject):
        """Updates single import item, i.e. importWhat"""
        if not treeItem.populated:
            return
        importWhatCopy = list(importObject.what)
        itemsToRemove = []
        for importWhatItem in treeItem.childItems:
            name = importWhatItem.data(0)
            found = False
            for index in range(len(importWhatCopy)):
                if importWhatCopy[index].getDisplayName() == name:
                    found = True
                    importWhatItem.updateData(importWhatCopy[index])
                    # No need to send the update signal because the name is
                    # still the same
                    del importWhatCopy[index]
                    break
            if not found:
                # Disappeared item
                itemsToRemove.append(importWhatItem)

        for item in itemsToRemove:
            self.__removeTreeItem(item)

        # Add those which have been introduced
        for item in importWhatCopy:
            newItem = TreeViewWhatItem(treeItem, item)
            self.__addTreeItem(treeItem, newItem)

    def onDebugMode(self, newState):
        """Memorizes the current debug state"""
        self.__debugMode = newState
