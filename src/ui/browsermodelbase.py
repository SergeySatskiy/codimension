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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Common functionality of various browser models"""

import sys
import os
import logging
from utils.fileutils import isPythonFile, isPythonMime
from utils.globals import GlobalData
from utils.pixmapcache import getIcon
from .qt import Qt, QAbstractItemModel, QModelIndex, QApplication, QCursor
from .viewitems import (TreeViewItem, TreeViewDirectoryItem, TreeViewFileItem,
                        TreeViewGlobalsItem, TreeViewImportsItem,
                        TreeViewFunctionsItem, TreeViewClassesItem,
                        TreeViewStaticAttributesItem, GlobalsItemType,
                        TreeViewInstanceAttributesItem, FileItemType,
                        TreeViewCodingItem, TreeViewImportItem,
                        TreeViewFunctionItem, TreeViewClassItem,
                        TreeViewDecoratorItem, TreeViewAttributeItem,
                        TreeViewGlobalItem, TreeViewWhatItem,
                        DirectoryItemType, SysPathItemType,
                        ImportsItemType, FunctionsItemType,
                        ClassesItemType, StaticAttributesItemType,
                        InstanceAttributesItemType, DecoratorItemType,
                        FunctionItemType, ClassItemType, ImportItemType)


class BrowserModelBase(QAbstractItemModel):

    """Class implementing the file system browser model"""

    def __init__(self, headerData, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.rootItem = TreeViewItem(None, headerData)
        self.globalData = GlobalData()
        self.projectTopLevelDirs = []
        self.showTooltips = True

    def setTooltips(self, switchOn):
        """Sets the tooltip mode: to show or not to show them"""
        self.showTooltips = switchOn

    def columnCount(self, parent=QModelIndex()):
        """Provides the number of columns"""
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self.rootItem.columnCount()

    def updateRootData(self, column, value):
        """Updates the root entry, i.e. header"""
        self.rootItem.setData(column, value)
        self.headerDataChanged.emit(Qt.Horizontal, column, column)

    def data(self, index, role):
        """Provides data of an item"""
        if not index.isValid():
            return None

        column = index.column()
        if role == Qt.DisplayRole:
            item = index.internalPointer()
            if column < item.columnCount():
                return item.data(column)
            if column == item.columnCount() and \
               column < self.columnCount(self.parent(index)):
                # This is for the case when an item under a multi-column
                # parent doesn't have a value for all the columns
                return ""
        elif role == Qt.DecorationRole:
            if column == 0:
                return index.internalPointer().getIcon()
        elif role == Qt.ToolTipRole:
            item = index.internalPointer()
            if column == 1 and item.path is not None:
                return item.path
            if self.showTooltips and column == 0 and item.toolTip != "":
                return item.toolTip
        return None

    def flags(self, index):
        """Provides the item flags"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Provides the header data"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= self.rootItem.columnCount():
                return ""
            return self.rootItem.data(section)
        return None

    def index(self, row, column, parent=QModelIndex()):
        """Creates an index"""
        # The model/view framework considers negative values out-of-bounds,
        # however in python they work when indexing into lists. So make sure
        # we return an invalid index for out-of-bounds row/col
        if row < 0 or column < 0 or \
           row >= self.rowCount(parent) or \
           column >= self.columnCount(parent):
            return QModelIndex()

        if parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self.rootItem

        try:
            if not parentItem.populated:
                self.populateItem(parentItem)
            childItem = parentItem.child(row)
        except IndexError:
            return QModelIndex()

        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def buildIndex(self, rowPath):
        """Builds index for the path (path is like [1, 2, 1, 16])"""
        result = QModelIndex()
        for row in rowPath:
            result = self.index(row, 0, result)
        return result

    def parent(self, index):
        """Provides the index of the parent object"""
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()
        return self.createIndex(parentItem.row(), 0, parentItem)

    def totalRowCount(self):
        """Provides the total number of rows"""
        return self.rootItem.childCount()

    def rowCount(self, parent=QModelIndex()):
        """Provides the number of rows"""
        # Only the first column should have children
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return self.rootItem.childCount()

        parentItem = parent.internalPointer()
        if not parentItem.populated:    # lazy population
            self.populateItem(parentItem)
        return parentItem.childCount()

    def hasChildren(self, parent=QModelIndex()):
        """Returns True if the parent has children"""
        # Only the first column should have children
        if parent.column() > 0:
            return False
        if not parent.isValid():
            return self.rootItem.childCount() > 0

        if parent.internalPointer().lazyPopulation:
            return True
        return parent.internalPointer().childCount() > 0

    def clear(self):
        """Clears the model"""
        self.beginResetModel()
        self.rootItem.removeChildren()
        self.endResetModel()

    def item(self, index):
        """Provides a reference to an item"""
        if not index.isValid():
            return None
        return index.internalPointer()

    @staticmethod
    def _addItem(itm, parentItem):
        """Adds an item"""
        parentItem.appendChild(itm)

    def addItem(self, itm, parent=QModelIndex()):
        """Adds an item"""
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        cnt = parentItem.childCount()
        self.beginInsertRows(parent, cnt, cnt)
        self._addItem(itm, parentItem)
        self.endInsertRows()

    def populateItem(self, parentItem, repopulate=False):
        """Populates an item's subtree"""
        if parentItem.itemType == DirectoryItemType:
            self.populateDirectoryItem(parentItem, repopulate)
        elif parentItem.itemType == SysPathItemType:
            self.populateSysPathItem(parentItem, repopulate)
        elif parentItem.itemType == FileItemType:
            self.populateFileItem(parentItem, repopulate)
        elif parentItem.itemType == GlobalsItemType:
            self.populateGlobalsItem(parentItem, repopulate)
        elif parentItem.itemType == ImportsItemType:
            self.populateImportsItem(parentItem, repopulate)
        elif parentItem.itemType == FunctionsItemType:
            self.populateFunctionsItem(parentItem, repopulate)
        elif parentItem.itemType == ClassesItemType:
            self.populateClassesItem(parentItem, repopulate)
        elif parentItem.itemType == ClassItemType:
            self.populateClassItem(parentItem, repopulate)
        elif parentItem.itemType == StaticAttributesItemType:
            self.populateStaticAttributesItem(parentItem, repopulate)
        elif parentItem.itemType == InstanceAttributesItemType:
            self.populateInstanceAttributesItem(parentItem, repopulate)
        elif parentItem.itemType == FunctionItemType:
            self.populateFunctionItem(parentItem, repopulate)
        elif parentItem.itemType == ImportItemType:
            self.populateImportItem(parentItem, repopulate)
        parentItem.populated = True

    def populateDirectoryItem(self, parentItem, repopulate=False):
        """Populates a directory item's subtree"""
        path = parentItem.getPath()
        if not os.path.exists(path):
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            items = os.listdir(path)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            logging.error("Cannot populate directory. " + str(exc))
            return

        excludes = ['.svn', '.cvs', '.hg', '.git']
        items = [itm for itm in items if itm not in excludes]
        if parentItem.needVCSStatus:
            # That's the project browser. Filter out what not needed.
            excludeFunctor = GlobalData().project.shouldExclude
            items = [itm for itm in items if not excludeFunctor(itm)]

        pathsToRequest = []
        if items:
            infoSrc = self.globalData.briefModinfoCache

            if repopulate:
                self.beginInsertRows(self.createIndex(parentItem.row(),
                                                      0, parentItem),
                                     0, len(items) - 1)
            path = os.path.realpath(path) + os.path.sep
            for item in items:
                fullPath = path + item
                if os.path.isdir(fullPath):
                    node = TreeViewDirectoryItem(parentItem, fullPath, False)
                    if parentItem.needVCSStatus:
                        pathsToRequest.append(fullPath + os.path.sep)
                else:
                    node = TreeViewFileItem(parentItem, fullPath)
                    if parentItem.needVCSStatus:
                        pathsToRequest.append(fullPath)
                    if isPythonMime(node.fileType):
                        modInfo = infoSrc.get(fullPath)
                        node.toolTip = ""
                        if modInfo.docstring is not None:
                            node.toolTip = modInfo.docstring.text

                        if modInfo.isOK == False:
                            # Substitute icon and change the tooltip
                            node.icon = getIcon('filepythonbroken.png')
                            if node.toolTip != "":
                                node.toolTip += "\n\n"
                            node.toolTip += "Parsing errors:\n" + \
                                            "\n".join(modInfo.lexerErrors + \
                                                      modInfo.errors)
                            node.parsingErrors = True

                        if modInfo.encoding is None and \
                           not modInfo.imports and \
                           not modInfo.globals and \
                           not modInfo.functions and \
                           not modInfo.classes:
                            node.populated = True
                            node.lazyPopulation = False

                node.needVCSStatus = parentItem.needVCSStatus
                self._addItem(node, parentItem)

            if repopulate:
                self.endInsertRows()

        parentItem.populated = True

        # Request statuses of the populated items. The request must be sent
        # after the items are added, otherwise the status received by the model
        # before the items are populated thus not updated properly.
        for path in pathsToRequest:
            GlobalData().mainWindow.vcsManager.requestStatus(path)
        QApplication.restoreOverrideCursor()

    def populateSysPathItem(self, parentItem, repopulate=False):
        """Populates the sys.path item's subtree"""
        if sys.path:
            if repopulate:
                self.beginInsertRows(self.createIndex(parentItem.row(),
                                                      0, parentItem),
                                     0, len(sys.path) - 1)
            for path in sys.path:
                if path == '':
                    path = os.getcwd()

                if os.path.isdir(path):
                    node = TreeViewDirectoryItem(parentItem, path)
                    self._addItem(node, parentItem)
            if repopulate:
                self.endInsertRows()

        parentItem.populated = True

    def populateFileItem(self, parentItem, repopulate=False):
        """Populate a file item's subtree"""
        path = parentItem.getPath()
        if not isPythonFile(path):
            return

        parentItem.populated = True
        modInfo = self.globalData.briefModinfoCache.get(path)

        # Count the number of rows to insert
        count = 0
        if modInfo.encoding is not None:
            count += 1
        if modInfo.imports:
            count += 1
        if modInfo.globals:
            count += 1
        if modInfo.functions:
            count += 1
        if modInfo.classes:
            count += 1

        if count == 0:
            return

        # Insert rows
        if repopulate:
            self.beginInsertRows(self.createIndex(parentItem.row(),
                                                  0, parentItem),
                                 0, count - 1)
        if modInfo.encoding is not None:
            node = TreeViewCodingItem(parentItem, modInfo.encoding)
            self._addItem(node, parentItem)

        if modInfo.imports:
            node = TreeViewImportsItem(parentItem, modInfo)
            self._addItem(node, parentItem)

        if modInfo.globals:
            node = TreeViewGlobalsItem(parentItem, modInfo)
            self._addItem(node, parentItem)

        if modInfo.functions:
            node = TreeViewFunctionsItem(parentItem, modInfo)
            self._addItem(node, parentItem)

        if modInfo.classes:
            node = TreeViewClassesItem(parentItem, modInfo)
            self._addItem(node, parentItem)

        if repopulate:
            self.endInsertRows()

    def __populateList(self, parentItem, items, itemClass, repopulate=False):
        """Helper for populating lists"""
        parentItem.populated = True

        if repopulate:
            self.beginInsertRows(
                self.createIndex(parentItem.row(), 0, parentItem),
                0, len(items) - 1)
        for item in items:
            treeItem = itemClass(parentItem, item)
            if parentItem.columnCount() > 1:
                # Find out a parent with path set
                path = self.findParentPath(parentItem)
                treeItem.appendData([os.path.basename(path), item.line])
                treeItem.setPath(path)
            self._addItem(treeItem, parentItem)

        if repopulate:
            self.endInsertRows()

    @staticmethod
    def findParentPath(item):
        """Provides the nearest parent path"""
        while item.path is None:
            item = item.parentItem
        return item.path

    def populateGlobalsItem(self, parentItem, repopulate=False):
        """Populates the globals item"""
        self.__populateList(parentItem, parentItem.sourceObj.globals,
                            TreeViewGlobalItem, repopulate)

    def populateImportsItem(self, parentItem, repopulate=False):
        """Populates the imports item"""
        self.__populateList(parentItem, parentItem.sourceObj.imports,
                            TreeViewImportItem, repopulate)

    def populateFunctionsItem(self, parentItem, repopulate=False):
        """Populates functions item"""
        self.__populateList(parentItem, parentItem.sourceObj.functions,
                            TreeViewFunctionItem, repopulate)

    def populateClassesItem(self, parentItem, repopulate=False):
        """Populate classes item"""
        self.__populateList(parentItem, parentItem.sourceObj.classes,
                            TreeViewClassItem, repopulate)

    def populateClassItem(self, parentItem, repopulate):
        """Populates a class item"""
        parentItem.populated = True

        # Count the number of items
        count = len(parentItem.sourceObj.decorators) + \
                len(parentItem.sourceObj.functions)

        if parentItem.sourceObj.classes:
            count += 1
        if parentItem.sourceObj.classAttributes:
            count += 1
        if parentItem.sourceObj.instanceAttributes:
            count += 1

        if count == 0:
            return

        # Insert rows
        if repopulate:
            self.beginInsertRows(
                self.createIndex(parentItem.row(), 0, parentItem),
                0, count - 1)
        for item in parentItem.sourceObj.decorators:
            node = TreeViewDecoratorItem(parentItem, item)
            if parentItem.columnCount() > 1:
                node.appendData([parentItem.data(1), item.line])
                node.setPath(self.findParentPath(parentItem))
            self._addItem(node, parentItem)

        for item in parentItem.sourceObj.functions:
            node = TreeViewFunctionItem(parentItem, item)
            if parentItem.columnCount() > 1:
                node.appendData([parentItem.data(1), item.line])
                node.setPath(self.findParentPath(parentItem))
            self._addItem(node, parentItem)

        if parentItem.sourceObj.classes:
            node = TreeViewClassesItem(parentItem, parentItem.sourceObj)
            if parentItem.columnCount() > 1:
                node.appendData(["", ""])
            self._addItem(node, parentItem)

        if parentItem.sourceObj.classAttributes:
            node = TreeViewStaticAttributesItem(parentItem)
            if parentItem.columnCount() > 1:
                node.appendData(["", ""])
            self._addItem(node, parentItem)

        if parentItem.sourceObj.instanceAttributes:
            node = TreeViewInstanceAttributesItem(parentItem)
            if parentItem.columnCount() > 1:
                node.appendData(["", ""])
            self._addItem(node, parentItem)

        if repopulate:
            self.endInsertRows()

    def populateFunctionItem(self, parentItem, repopulate):
        """Populates a function item"""
        parentItem.populated = True

        # Count the number of items
        count = len(parentItem.sourceObj.decorators)

        if parentItem.sourceObj.functions:
            count += 1
        if parentItem.sourceObj.classes:
            count += 1

        if count == 0:
            return

        # Insert rows
        if repopulate:
            self.beginInsertRows(
                self.createIndex(parentItem.row(), 0, parentItem),
                0, count - 1)

        for item in parentItem.sourceObj.decorators:
            node = TreeViewDecoratorItem(parentItem, item)
            if parentItem.columnCount() > 1:
                node.appendData([parentItem.data(1), item.line])
                node.setPath(self.findParentPath(parentItem))
            self._addItem(node, parentItem)

        if parentItem.sourceObj.functions:
            node = TreeViewFunctionsItem(parentItem, parentItem.sourceObj)
            if parentItem.columnCount() > 1:
                node.appendData(["", ""])
            self._addItem(node, parentItem)

        if parentItem.sourceObj.classes:
            node = TreeViewClassesItem(parentItem, parentItem.sourceObj)
            if parentItem.columnCount() > 1:
                node.appendData(["", ""])
            self._addItem(node, parentItem)

        if repopulate:
            self.endInsertRows()

    def populateStaticAttributesItem(self, parentItem, repopulate):
        """Populates a static attributes item"""
        self.__populateList(parentItem,
                            parentItem.parentItem.sourceObj.classAttributes,
                            TreeViewAttributeItem, repopulate)

    def populateInstanceAttributesItem(self, parentItem, repopulate):
        """Populates an instance attributes item"""
        self.__populateList(parentItem,
                            parentItem.parentItem.sourceObj.instanceAttributes,
                            TreeViewAttributeItem, repopulate)

    def populateImportItem(self, parentItem, repopulate):
        """Populate an import item"""
        self.__populateList(parentItem, parentItem.sourceObj.what,
                            TreeViewWhatItem, repopulate)

    def signalItemUpdated(self, treeItem):
        """Emits a signal that an item is updated"""
        index = self.buildIndex(treeItem.getRowPath())
        self.dataChanged.emit(index, index)

    def removeTreeItem(self, treeItem):
        """Removes the given item"""
        index = self.buildIndex(treeItem.getRowPath())
        self.beginRemoveRows(index.parent(), index.row(), index.row())
        treeItem.parentItem.removeChild(treeItem)
        self.endRemoveRows()

    def addTreeItem(self, treeItem, newItem):
        """Adds the given item"""
        parentIndex = self.buildIndex(treeItem.getRowPath())
        self.addItem(newItem, parentIndex)

    def updateSingleClassItem(self, treeItem, classObj):
        """Updates single class item"""
        if not treeItem.populated:
            return

        # There might be decorators, classes, methods, static attributes and
        # instance attributes
        existingDecors = []
        existingMethods = []
        hadStaticAttributes = False
        hadInstanceAttributes = False
        hadClasses = False
        itemsToRemove = []
        for classChildItem in treeItem.childItems:
            if classChildItem.itemType == DecoratorItemType:
                name = classChildItem.sourceObj.name
                found = False
                for decor in classObj.decorators:
                    if decor.name == name:
                        found = True
                        existingDecors.append(name)
                        if cmpDecoratorDisplayName(classChildItem.sourceObj,
                                                   decor):
                            classChildItem.updateData(decor)
                            classChildItem.setData(2, decor.line)
                        else:
                            # Appearence changed
                            classChildItem.updateData(decor)
                            classChildItem.setData(2, decor.line)
                            self.signalItemUpdated(classChildItem)
                        break
                if not found:
                    itemsToRemove.append(classChildItem)
                continue
            elif classChildItem.itemType == ClassesItemType:
                hadClasses = True
                if not classObj.classes:
                    itemsToRemove.append(classChildItem)
                else:
                    classChildItem.updateData(classObj)
                    self.updateClassesItem(classChildItem,
                                           classObj.classes)
                continue
            elif classChildItem.itemType == FunctionItemType:
                name = classChildItem.sourceObj.name
                found = False
                for method in classObj.functions:
                    if method.name == name:
                        found = True
                        existingMethods.append(name)
                        if cmpFunctionDisplayName(classChildItem.sourceObj,
                                                  method):
                            classChildItem.updateData(method)
                            classChildItem.setData(2, method.line)
                        else:
                            # Appearence changed
                            classChildItem.updateData(method)
                            classChildItem.setData(2, method.line)
                            self.signalItemUpdated(classChildItem)
                        self.updateSingleFuncItem(classChildItem,
                                                  method)
                        break
                if not found:
                    itemsToRemove.append(classChildItem)
                continue
            elif classChildItem.itemType == StaticAttributesItemType:
                hadStaticAttributes = True
                if not classObj.classAttributes:
                    itemsToRemove.append(classChildItem)
                else:
                    self.updateAttrItem(classChildItem,
                                        classObj.classAttributes)
                continue
            elif classChildItem.itemType == InstanceAttributesItemType:
                hadInstanceAttributes = True
                if not classObj.instanceAttributes:
                    itemsToRemove.append(classChildItem)
                else:
                    self.updateAttrItem(classChildItem,
                                        classObj.instanceAttributes)
                continue

        for item in itemsToRemove:
            self.removeTreeItem(item)

        # Add those which have been introduced
        for decor in classObj.decorators:
            if decor.name not in existingDecors:
                newItem = TreeViewDecoratorItem(treeItem, decor)
                if treeItem.columnCount() > 1:
                    newItem.appendData([treeItem.data(1), decor.line])
                    newItem.setPath(self.findParentPath(treeItem))
                self.addTreeItem(treeItem, newItem)
        for method in classObj.functions:
            if method.name not in existingMethods:
                newItem = TreeViewFunctionItem(treeItem, method)
                if treeItem.columnCount() > 1:
                    newItem.appendData([treeItem.data(1), method.line])
                    newItem.setPath(self.findParentPath(treeItem))
                self.addTreeItem(treeItem, newItem)

        if not hadClasses and classObj.classes:
            newItem = TreeViewClassesItem(treeItem, classObj)
            if treeItem.columnCount() > 1:
                newItem.appendData(["", ""])
            self.addTreeItem(treeItem, newItem)
        if not hadStaticAttributes and \
           classObj.classAttributes:
            newItem = TreeViewStaticAttributesItem(treeItem)
            if treeItem.columnCount() > 1:
                newItem.appendData(["", ""])
            self.addTreeItem(treeItem, newItem)
        if not hadInstanceAttributes and \
           classObj.instanceAttributes:
            newItem = TreeViewInstanceAttributesItem(treeItem)
            if treeItem.columnCount() > 1:
                newItem.appendData(["", ""])
            self.addTreeItem(treeItem, newItem)

    def updateSingleFuncItem(self, treeItem, funcObj):
        """Updates single function item"""
        if not treeItem.populated:
            return

        # It may have decor, classes and other functions
        existingDecors = []
        hadFunctions = False
        hadClasses = False
        itemsToRemove = []
        for funcChildItem in treeItem.childItems:
            if funcChildItem.itemType == DecoratorItemType:
                name = funcChildItem.sourceObj.name
                found = False
                for decor in funcObj.decorators:
                    if decor.name == name:
                        found = True
                        existingDecors.append(name)
                        if cmpDecoratorDisplayName(funcChildItem.sourceObj,
                                                   decor):
                            funcChildItem.updateData(decor)
                            funcChildItem.setData(2, decor.line)
                        else:
                            # Appearence changed
                            funcChildItem.updateData(decor)
                            funcChildItem.setData(2, decor.line)
                            self.signalItemUpdated(funcChildItem)
                        break
                if not found:
                    itemsToRemove.append(funcChildItem)
                continue
            elif funcChildItem.itemType == FunctionsItemType:
                hadFunctions = True
                if not funcObj.functions:
                    itemsToRemove.append(funcChildItem)
                else:
                    funcChildItem.updateData(funcObj)
                    self.updateFunctionsItem(funcChildItem,
                                             funcObj.functions)
                continue
            elif funcChildItem.itemType == ClassesItemType:
                hadClasses = True
                if not funcObj.classes:
                    itemsToRemove.append(funcChildItem)
                else:
                    funcChildItem.updateData(funcObj)
                    self.updateClassesItem(funcChildItem,
                                           funcObj.classes)
                continue

        for item in itemsToRemove:
            self.removeTreeItem(item)

        # Add those which have been introduced
        for decor in funcObj.decorators:
            if decor.name not in existingDecors:
                newItem = TreeViewDecoratorItem(treeItem, decor)
                if treeItem.columnCount() > 1:
                    newItem.appendData([treeItem.data(1), decor.line])
                    newItem.setPath(self.findParentPath(treeItem))
                self.addTreeItem(treeItem, newItem)

        if not hadFunctions and funcObj.functions:
            newItem = TreeViewFunctionsItem(treeItem, funcObj)
            if treeItem.columnCount() > 1:
                newItem.appendData(["", ""])
            self.addTreeItem(treeItem, newItem)
        if not hadClasses and funcObj.classes:
            newItem = TreeViewClassesItem(treeItem, funcObj)
            if treeItem.columnCount() > 1:
                newItem.appendData(["", ""])
            self.addTreeItem(treeItem, newItem)

    def updateClassesItem(self, treeItem, classesObj):
        """Updates classes item"""
        if not treeItem.populated:
            return

        existingClasses = []
        itemsToRemove = []
        for classItem in treeItem.childItems:
            name = classItem.sourceObj.name
            found = False
            for cls in classesObj:
                if cls.name == name:
                    found = True
                    existingClasses.append(name)
                    if cmpClassDisplayName(classItem.sourceObj, cls):
                        classItem.updateData(cls)
                        classItem.setData(2, cls.line)
                    else:
                        # Appearence changed
                        classItem.updateData(cls)
                        classItem.setData(2, cls.line)
                        self.signalItemUpdated(classItem)
                    self.updateSingleClassItem(classItem, cls)
                    break
            if not found:
                itemsToRemove.append(classItem)

        for item in itemsToRemove:
            self.removeTreeItem(item)

        # Add those which have been introduced
        for cls in classesObj:
            if cls.name not in existingClasses:
                newItem = TreeViewClassItem(treeItem, cls)
                if treeItem.columnCount() > 1:
                    newItem.appendData([treeItem.data(1), cls.line])
                    newItem.setPath(self.findParentPath(treeItem))
                self.addTreeItem(treeItem, newItem)

    def updateFunctionsItem(self, treeItem, functionsObj):
        """Updates functions item"""
        if not treeItem.populated:
            return

        existingFunctions = []
        itemsToRemove = []
        for functionItem in treeItem.childItems:
            name = functionItem.sourceObj.name
            found = False
            for func in functionsObj:
                if func.name == name:
                    found = True
                    existingFunctions.append(name)
                    if cmpFunctionDisplayName(functionItem.sourceObj,
                                              func):
                        functionItem.updateData(func)
                        functionItem.setData(2, func.line)
                    else:
                        # Appearence changed
                        functionItem.updateData(func)
                        functionItem.setData(2, func.line)
                        self.signalItemUpdated(functionItem)
                    self.updateSingleFuncItem(functionItem, func)
                    break
            if not found:
                itemsToRemove.append(functionItem)

        for item in itemsToRemove:
            self.removeTreeItem(item)

        # Add those which have been introduced
        for func in functionsObj:
            if func.name not in existingFunctions:
                newItem = TreeViewFunctionItem(treeItem, func)
                if treeItem.columnCount() > 1:
                    newItem.appendData([treeItem.data(1), func.line])
                    newItem.setPath(self.findParentPath(treeItem))
                self.addTreeItem(treeItem, newItem)

    def updateAttrItem(self, treeItem, attributesObj):
        """Updates attributes item"""
        if not treeItem.populated:
            return

        existingAttributes = []
        itemsToRemove = []
        for attrItem in treeItem.childItems:
            name = attrItem.data(0)
            found = False
            for attr in attributesObj:
                if attr.name == name:
                    found = True
                    existingAttributes.append(name)
                    attrItem.updateData(attr)
                    attrItem.setData(2, attr.line)
                    # There is no need to send a signal to update the item
                    # because the only name is displayed and it's not
                    # changed.
                    # self.signalItemUpdated( attrItem )
                    break
            if not found:
                itemsToRemove.append(attrItem)

        for item in itemsToRemove:
            self.removeTreeItem(item)

        for attr in attributesObj:
            if attr.name not in existingAttributes:
                newItem = TreeViewAttributeItem(treeItem, attr)
                if treeItem.columnCount() > 1:
                    newItem.appendData([treeItem.data(1), attr.line])
                    newItem.setPath(self.findParentPath(treeItem))
                self.addTreeItem(treeItem, newItem)


def cmpDocstringDisplayName(lhs, rhs):
    """Returns True if the display names are the same"""
    if lhs is None and rhs is None:
        return True
    if lhs is None or rhs is None:
        return False
    return lhs.text == rhs.text


def cmpFunctionDisplayName(lhs, rhs):
    """Returns True if the functions display names are the same"""
    if lhs.name != rhs.name:
        return False
    if lhs.arguments != rhs.arguments:
        return False
    return cmpDocstringDisplayName(lhs.docstring, rhs.docstring)


def cmpDecoratorDisplayName(lhs, rhs):
    """Returns True if the decorators display names are the same"""
    if lhs.name != rhs.name:
        return False
    if lhs.arguments != rhs.arguments:
        return False
    return True


def cmpClassDisplayName(lhs, rhs):
    """Returns True if the classes display names are the same"""
    if lhs.name != rhs.name:
        return False
    if lhs.base != rhs.base:
        return False
    return cmpDocstringDisplayName(lhs.docstring, rhs.docstring)
