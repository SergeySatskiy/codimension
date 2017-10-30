# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""File outline browser and its model"""

from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from autocomplete.bufferutils import getItemForDisplayPath
from .qt import QPalette, QTreeView
from .browsermodelbase import BrowserModelBase
from .filesbrowserbase import FilesBrowser
from .viewitems import (DirectoryItemType, SysPathItemType, GlobalsItemType,
                        ImportsItemType, FunctionsItemType, ClassesItemType,
                        StaticAttributesItemType, InstanceAttributesItemType,
                        CodingItemType, ImportItemType, FunctionItemType,
                        ClassItemType, DecoratorItemType, AttributeItemType,
                        GlobalItemType, ImportWhatItemType, TreeViewCodingItem,
                        TreeViewGlobalsItem, TreeViewImportsItem,
                        TreeViewFunctionsItem, TreeViewClassesItem)


class OutlineBrowserModel(BrowserModelBase):

    """Class implementing the file outline browser model"""

    def __init__(self, shortName, info, parent=None):
        BrowserModelBase.__init__(self, shortName, parent)
        self.populateModel(info)
        self.setTooltips(Settings()['outlineTooltips'])

    def populateModel(self, info):
        """Populates the browser model"""
        self.clear()
        if info.encoding is not None:
            self.addItem(TreeViewCodingItem(self.rootItem, info.encoding))
        if info.imports:
            self.addItem(TreeViewImportsItem(self.rootItem, info))
        if info.globals:
            self.addItem(TreeViewGlobalsItem(self.rootItem, info))
        if info.functions:
            self.addItem(TreeViewFunctionsItem(self.rootItem, info))
        if info.classes:
            self.addItem(TreeViewClassesItem(self.rootItem, info))


class OutlineBrowser(FilesBrowser):

    """File outline browser"""

    def __init__(self, uuid, shortName, info, parent=None):
        FilesBrowser.__init__(self, OutlineBrowserModel(shortName, info),
                              False, parent)

        self.__bufferUUID = uuid
        self.__bufferBroken = False

        self.header().setAutoFillBackground(True)
        self.__origHeaderBackground = self.__getOriginalHeaderBackground()
        self.__brokenHeaderBackground = self.__getBrokenHeaderBackground()
        self.setHeaderHighlight(False)

        self.setWindowTitle('File outline')
        self.setWindowIcon(getIcon('icon.png'))

    @staticmethod
    def __converttohex(value):
        """Converts to a 2 digits representation"""
        result = hex(value).replace("0x", "")
        if len(result) == 1:
            return "0" + result
        return result

    @staticmethod
    def __toCSSColor(rgba):
        """Converts the color to the CSS format"""
        return ''.join(['#',
                        OutlineBrowser.__converttohex(rgba[0]),
                        OutlineBrowser.__converttohex(rgba[1]),
                        OutlineBrowser.__converttohex(rgba[2])])

    def __getOriginalHeaderBackground(self):
        """Retrieves the original header color as a string useful for CSS"""
        headerPalette = self.header().palette()
        backgroundColor = headerPalette.color(QPalette.Background)
        return self.__toCSSColor(backgroundColor.getRgb())

    def __getBrokenHeaderBackground(self):
        """Returns the broken header bg color as a string useful for CSS"""
        return self.__toCSSColor(
            GlobalData().skin['outdatedOutlineColor'].getRgb())

    def setHeaderHighlight(self, switchOn):
        """Sets or removes the header highlight"""
        if switchOn:
            color = self.__brokenHeaderBackground
            self.__bufferBroken = True
        else:
            color = self.__origHeaderBackground
            self.__bufferBroken = False

        self.header().setStyleSheet(
            'QHeaderView[highlightHeader="true"] '
            '{ background-color: ' + color + ' }')
        self.header().setProperty("highlightHeader", True)
        self.header().style().unpolish(self.header())
        self.header().style().polish(self.header())

    def setTooltips(self, switchOn):
        """Sets the tooltip mode"""
        self.model().sourceModel().setTooltips(switchOn)

    def reload(self):
        """Reloads the filesystem view"""
        self.model().sourceModel().populateModel()
        self.model().beginResetModel()
        self.model().endResetModel()
        self.layoutDisplay()

    def mouseDoubleClickEvent(self, mouseEvent):
        """Reimplemented to disable expanding/collapsing of items when
           double-clicking. Instead the double-clicked entry is opened.
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

    def openItem(self, item):
        """Handles the case when an item is activated"""
        if item.itemType in [GlobalsItemType,
                             ImportsItemType, FunctionsItemType,
                             ClassesItemType, StaticAttributesItemType,
                             InstanceAttributesItemType]:
            return

        if item.itemType in [CodingItemType, ImportItemType, FunctionItemType,
                             ClassItemType, DecoratorItemType,
                             AttributeItemType, GlobalItemType,
                             ImportWhatItemType]:
            # Check if the used info has no errors
            if not self.__bufferBroken:
                GlobalData().mainWindow.gotoInBuffer(self.__bufferUUID,
                                                     item.sourceObj.line)
                return

            # The info has errors, try to reparse the current buffer and see
            # if an item has changed the position
            currentInfo = self.parent().getCurrentBufferInfo()
            displayPath = item.getDisplayDataPath()
            infoItem = getItemForDisplayPath(currentInfo, displayPath)
            if infoItem is None:
                # Not found, try luck with the old info
                GlobalData().mainWindow.gotoInBuffer(self.__bufferUUID,
                                                     item.sourceObj.line)
                return
            # Found in the new parsed info - use the new line
            GlobalData().mainWindow.gotoInBuffer(self.__bufferUUID,
                                                 infoItem.line)

    def __expandItem(self, item):
        """Expands the given item"""
        srcModel = self.model().sourceModel()
        index = srcModel.buildIndex(item.getRowPath())
        self.setExpanded(self.model().mapFromSource(index), True)

    def __selectItem(self, item):
        """Selects the item"""
        srcModel = self.model().sourceModel()
        index = srcModel.buildIndex(item.getRowPath())
        self.setCurrentIndex(self.model().mapFromSource(index))
        self.setFocus()

    @staticmethod
    def __importMatch(impObj, line):
        """Returns True if the importobject matches"""
        minLine = impObj.line
        maxLine = impObj.line
        for what in impObj.what:
            if what.line > maxLine:
                maxLine = what.line
        return line >= minLine and line <= maxLine

    @staticmethod
    def __funcMatch(funcObj, line):
        """Returns True if the function object matches"""
        minLine = funcObj.keywordLine
        maxLine = funcObj.colonLine
        for decor in funcObj.decorators:
            if decor.line < minLine:
                minLine = decor.line
        return line >= minLine and line <= maxLine

    @staticmethod
    def __classMatch(classObj, line):
        """Returns True if the class object matches"""
        minLine = classObj.keywordLine
        maxLine = classObj.colonLine
        for decor in classObj.decorators:
            if decor.line < minLine:
                minLine = decor.line
        return line >= minLine and line <= maxLine

    def highlightContextItem(self, context, line, info):
        """Highlights the context defined item"""
        srcModel = self.model().sourceModel()
        if context.length == 0:
            # It is a global context. Check if something matches
            # Encoding
            if info.encoding:
                if info.encoding.line == line:
                    for item in srcModel.rootItem.childItems:
                        if item.itemType == CodingItemType:
                            self.__selectItem(item)
                            return True
                    return False
            # Globals
            for glob in info.globals:
                if glob.line == line:
                    for item in srcModel.rootItem.childItems:
                        if item.itemType == GlobalsItemType:
                            self.__expandItem(item)
                            for item in item.childItems:
                                if item.sourceObj.line == line:
                                    self.__selectItem(item)
                                    return True
                    return False
            # Imports
            for imp in info.imports:
                if self.__importMatch(imp, line):
                    for item in srcModel.rootItem.childItems:
                        if item.itemType == ImportsItemType:
                            self.__expandItem(item)
                            for item in item.childItems:
                                if self.__importMatch(item.sourceObj, line):
                                    self.__selectItem(item)
                                    return True
                    return False

            # No match has been found in global context
            return False

        # This is something nested
        currentItem = srcModel.rootItem
        for level in context.levels:
            scopeType = level[1]
            scopeObj = level[0]
            if scopeType == context.FunctionScope:
                # Search for 'functions' item type and expand it
                if currentItem is not srcModel.rootItem:
                    self.__expandItem(currentItem)
                found = False
                for item in currentItem.childItems:
                    if item.itemType == FunctionsItemType:
                        self.__expandItem(item)
                        for item in item.childItems:
                            if self.__funcMatch(item.sourceObj, scopeObj.line):
                                self.__selectItem(item)
                                currentItem = item
                                found = True
                                break
                        if found:
                            break
                if found:
                    continue
                return False
            if scopeType == context.ClassScope:
                # Search for 'classes' item type and expand it
                if currentItem is not srcModel.rootItem:
                    self.__expandItem(currentItem)
                found = False
                for item in currentItem.childItems:
                    if item.itemType == ClassesItemType:
                        self.__expandItem(item)
                        for item in item.childItems:
                            if self.__classMatch(item.sourceObj,
                                                 scopeObj.line):
                                self.__selectItem(item)
                                currentItem = item
                                found = True
                                break
                        if found:
                            break
                if found:
                    continue
                return False
            if scopeType == context.ClassMethodScope:
                # Search for 'function' item type
                if currentItem is not srcModel.rootItem:
                    self.__expandItem(currentItem)
                found = False
                for item in item.childItems:
                    if item.itemType == FunctionItemType:
                        if self.__funcMatch(item.sourceObj, scopeObj.line):
                            self.__selectItem(item)
                            currentItem = item
                            found = True
                            break
                if found:
                    continue
                return False
        return True
