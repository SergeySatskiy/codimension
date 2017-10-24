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

"""Collection of items which may appear in various tree views:
   - project view
   - filesystem view
   - classes view
   - functions view
"""

import os
import os.path
from utils.pixmapcache import getIcon
from utils.fileutils import getFileProperties, isPythonMime, isCDMProjectMime
from utils.project import getProjectFileTooltip
from .qt import Qt


NoItemType = -1

DirectoryItemType = 1
SysPathItemType = 2
FileItemType = 3
GlobalsItemType = 4
ImportsItemType = 5
FunctionsItemType = 6
ClassesItemType = 7
StaticAttributesItemType = 8
InstanceAttributesItemType = 9

CodingItemType = 20
ImportItemType = 21
ImportWhatItemType = 22
FunctionItemType = 23
ClassItemType = 24
DecoratorItemType = 25
AttributeItemType = 26
GlobalItemType = 27

EMPTY_ICON = getIcon('empty.png')


class TreeViewItem():

    """Common data structures for tree views items"""

    def __init__(self, parent, data):

        self.childItems = []
        self.childItemsSize = 0

        if isinstance(data, list):
            self.itemData = data
            self.itemDataSize = len(self.itemData)
        else:
            self.itemData = [data]
            self.itemDataSize = 1

        self.isLink = False
        self.parentItem = parent
        self.itemType = NoItemType
        self.icon = EMPTY_ICON
        self.populated = True
        self.lazyPopulation = False
        self.toolTip = ""
        self.path = None
        self.needVCSStatus = False

        self.vcsStatus = None   # VCSStatus instance, if present

    def isRoot(self):
        """True if it is the root item"""
        return self.parentItem is None

    def appendData(self, data):
        """Adds more data to the item"""
        if isinstance(data, list):
            self.itemData += data
            self.itemDataSize = len(self.itemData)
        else:
            self.itemData.append(data)
            self.itemDataSize += 1

    def setPath(self, path):
        """Sets the item path"""
        self.path = path

    def appendChild(self, child):
        """Adds a child to the item"""
        self.childItems.append(child)
        self.childItemsSize += 1
        self.populated = True

    def removeChild(self, child):
        """Removes the child"""
        self.childItems.remove(child)
        self.childItemsSize -= 1

    def removeChildren(self):
        """Removes all children"""
        self.childItems = []
        self.childItemsSize = 0

    def child(self, row):
        """Provides the child"""
        return self.childItems[row]

    def children(self):
        """Provides all the child items"""
        return self.childItems[:]

    def childCount(self):
        """Provides the number of child items"""
        # Optimization against len(self.childItems)
        return self.childItemsSize

    def columnCount(self):
        """Provides the number of available data items"""
        # Optimization against len(self.itemData)
        return self.itemDataSize

    def data(self, column):
        """Provides item data"""
        try:
            return self.itemData[column]
        except IndexError:
            return ''

    def setData(self, column, value):
        """Sets the new data"""
        try:
            self.itemData[column] = value
        except:
            pass

    def parent(self):
        """Provides the reference to the parent item"""
        return self.parentItem

    def row(self):
        """Provides the row number of this item"""
        return self.parentItem.childItems.index(self)

    def type(self):
        """Provides the item type"""
        return self.itemType

    def getIcon(self):
        """Provides the items icon"""
        return self.icon

    def setIcon(self, icon):
        """Sets the icon"""
        self.icon = icon

    def lessThan(self, other, column, order):
        """Check, if the item is less than another"""
        try:
            return self.itemData[column] < other.itemData[column]
        except IndexError:
            return False

    def getPath(self):
        """Provides the file name or dir name depending on the item type"""
        if self.itemType in [SysPathItemType, NoItemType]:
            return ''

        current = self

        # The item could be used for G/F/C viewers where the file name is
        # available in the second column
        if self.path:
            return self.path
        if self.itemDataSize >= 2:
            return self.itemData[1]

        # Memorize if it is a directory item
        isDir = current.itemType == DirectoryItemType

        # skip till file or directory items
        while True:
            if current.itemType == NoItemType:
                raise Exception("Internal error of getting tree view "
                                "item path. Please inform the developers.")
            if current.itemType in [FileItemType, DirectoryItemType,
                                    SysPathItemType]:
                break
            current = current.parentItem

        path = current.itemData[0]
        while current.parentItem.itemType != NoItemType and \
              current.parentItem.itemType != SysPathItemType:
            current = current.parentItem
            path = os.path.sep + path
            if current.itemData[0] != os.path.sep:    # root item
                path = current.itemData[0] + path

        path = os.path.normpath(path)
        if isDir:
            if not path.endswith(os.path.sep):
                path += os.path.sep
        return path

    def getRealPath(self):

        """Provides the file name or dir name depending on the item type.
           All the links except of the item itself are resolved.
        """
        if self.itemType in [SysPathItemType, NoItemType]:
            return ''

        current = self

        # The item could be used for G/F/C viewers where the file name is
        # available in the second column
        if self.path:
            return self.path
        if self.itemDataSize >= 2:
            return self.itemData[1]

        # Memorize if it is a directory item
        isDir = self.itemType == DirectoryItemType

        # skip till file or directory items
        while True:
            if current.itemType == NoItemType:
                raise Exception("Internal error of getting tree view "
                                "item path. Please inform the developers.")
            if current.itemType in [FileItemType, DirectoryItemType,
                                    SysPathItemType]:
                break
            current = current.parentItem

        hasLinks = False
        path = current.itemData[0]
        while current.parentItem.itemType != NoItemType and \
              current.parentItem.itemType != SysPathItemType:
            current = current.parentItem
            if current.itemType == DirectoryItemType:
                if current.isLink:
                    hasLinks = True
            path = os.path.sep + path
            if current.itemData[0] != os.path.sep:    # root item
                path = current.itemData[0] + path

        if hasLinks:
            if self.isLink:
                path = os.path.realpath(os.path.dirname(path)) + \
                       os.path.sep + self.itemData[0]
            else:
                path = os.path.realpath(path)

        path = os.path.normpath(path)
        if isDir:
            if not path.endswith(os.path.sep):
                path += os.path.sep
        return path

    def getQualifiedName(self):
        """Provides the qualified item name"""
        current = self
        name = ""
        while current is not None:
            if current.itemType in [FunctionItemType, ClassItemType]:
                namePart = current.data(0).split("(")[0]
                if name != "":
                    name = namePart + "." + name
                else:
                    name = namePart
            current = current.parentItem
        return name

    def getRowPath(self):
        """Provides the row path"""
        rowPath = []
        child = self
        current = self.parentItem
        while not current is None:
            for index in range(0, len(current.childItems)):
                if current.childItems[index] == child:
                    rowPath = [index] + rowPath
                    child = current
                    current = child.parentItem
                    break
        return rowPath

    def getDisplayDataPath(self):
        """Provides the diplayed path for the item"""
        result = []
        current = self
        while current.parentItem is not None:
            result.insert(0, (current.itemType, current.data(0)))
            current = current.parentItem
        return result


class TreeViewDirectoryItem(TreeViewItem):

    """Directory item"""

    def __init__(self, parent, dinfo, full=True):

        self._dirName = os.path.abspath(str(dinfo))

        if full:
            dname = self._dirName
        else:
            dname = os.path.basename(self._dirName)

        TreeViewItem.__init__(self, parent, dname)

        self.itemType = DirectoryItemType

        self.icon = None
        self.populated = False
        self.lazyPopulation = True
        self.isLink = False
        self.updateStatus()

    def updateStatus(self):
        """Updates internal fields"""
        if os.path.exists(self._dirName):
            self.icon = getIcon('dirclosed.png')
            self.populated = False
            self.lazyPopulation = True

            if os.path.islink(self._dirName):
                self.isLink = True
                linkTo = os.readlink(self._dirName)
                realpath = os.path.realpath(self._dirName)
                self.toolTip = "-> " + linkTo + "  (" + realpath + ")"
                self.icon = getIcon('dirlink.png')
        else:
            self.icon = getIcon('dirbroken.png')
            self.populated = True
            self.lazyPopulation = False

            self.childItems = []
            self.childItemsSize = 0

    def lessThan(self, other, column, order):
        """Checks if the item is less than another"""
        if other.itemType == FileItemType:
            return order == Qt.AscendingOrder
        return TreeViewItem.lessThan(self, other, column, order)


class TreeViewSysPathItem(TreeViewItem):

    """sys.path files item"""

    def __init__(self, parent):

        TreeViewItem.__init__(self, parent, "sys.path")

        self.itemType = SysPathItemType
        self.icon = getIcon('filepython.png')
        self.populated = False
        self.lazyPopulation = True
        self.isLink = False


class TreeViewFileItem(TreeViewItem):

    """file item"""

    def __init__(self, parent, path):
        path = str(path)
        TreeViewItem.__init__(self, parent, os.path.basename(path))
        self.itemType = FileItemType
        self.parsingErrors = False  # Used for python files only
        self.isLink = False

        self.fileType, self.icon, _ = getFileProperties(path)
        if self.fileType is None:
            if self.icon is None:
                self.icon = getIcon('filemisc.png')
            return

        if 'broken-symlink' in self.fileType:
            self.isLink = True
            self.toolTip = self.__brokenLinkTooltip(path)
            return

        if os.path.islink(path):
            self.isLink = True
            self.toolTip = self.__linkTooltip(path)
            self.icon = getIcon('filelink.png')
            self.fileType, _, _ = getFileProperties(os.path.realpath(path))
            return

        # Fine corrections for some file types
        if isPythonMime(self.fileType):
            self.populated = False
            self.lazyPopulation = True
            return

        if isCDMProjectMime(self.fileType):
            # Get the project properties
            try:
                self.toolTip = getProjectFileTooltip(path)
            except:
                # cannot get project properties
                self.toolTip = 'Broken project file'
            return

    def lessThan(self, other, column, order):
        """Checks if the item is less than another"""
        if other.itemType != FileItemType:
            return order == Qt.DescendingOrder

        sinit = self.data(0).startswith('__init__.py')
        oinit = other.data(0).startswith('__init__.py')
        if sinit and not oinit:
            return order == Qt.AscendingOrder
        if not sinit and oinit:
            return order == Qt.DescendingOrder
        return TreeViewItem.lessThan(self, other, column, order)

    def updateLinkStatus(self, path):
        """Called to update the status to/from broken link"""
        if not self.isLink:
            return

        self.fileType, self.icon, _ = getFileProperties(path)
        if 'broken-symlink' in self.fileType:
            self.toolTip = self.__brokenLinkTooltip(path)
            return

        self.toolTip = self.__linkTooltip(path)
        self.icon = getIcon('filelink.png')
        self.fileType, _, _ = getFileProperties(os.path.realpath(path))

    @staticmethod
    def __brokenLinkTooltip(path):
        """Provides the broken link tooltip"""
        linkTo = os.readlink(path)
        realpath = os.path.realpath(path)
        return "Broken symlink -> " + linkTo + " (" + realpath + ")"

    @staticmethod
    def __linkTooltip(path):
        """Provides the link tooltip"""
        linkTo = os.readlink(path)
        realpath = os.path.realpath(path)
        return "-> " + linkTo + "  (" + realpath + ")"


class TreeViewGlobalsItem(TreeViewItem):

    """Globals item"""

    def __init__(self, parent, infoObj):
        TreeViewItem.__init__(self, parent, "Globals")

        self.sourceObj = infoObj
        self.itemType = GlobalsItemType
        self.icon = getIcon('globalvar.png')
        self.populated = False
        self.lazyPopulation = True

    def updateData(self, infoObj):
        """Updates data model source"""
        self.sourceObj = infoObj


class TreeViewImportsItem(TreeViewItem):

    """Imports item"""

    def __init__(self, parent, infoObj):

        TreeViewItem.__init__(self, parent, "Imports")

        self.sourceObj = infoObj
        self.itemType = ImportsItemType
        self.icon = getIcon('imports.png')
        self.populated = False
        self.lazyPopulation = True

    def updateData(self, infoObj):
        """Updates data model source"""
        self.sourceObj = infoObj


class TreeViewFunctionsItem(TreeViewItem):

    """Functions item"""

    def __init__(self, parent, infoObj):
        TreeViewItem.__init__(self, parent, "Functions")

        self.sourceObj = infoObj
        self.itemType = FunctionsItemType
        self.icon = getIcon('method.png')
        self.populated = False
        self.lazyPopulation = True

    def updateData(self, infoObj):
        """Updates data model source"""
        self.sourceObj = infoObj


class TreeViewClassesItem(TreeViewItem):

    """Classes item"""

    def __init__(self, parent, infoObj):
        TreeViewItem.__init__(self, parent, "Classes")

        self.sourceObj = infoObj
        self.itemType = ClassesItemType
        self.icon = getIcon('class.png')
        self.populated = False
        self.lazyPopulation = True

    def updateData(self, infoObj):
        """Updates data model source"""
        self.sourceObj = infoObj


class TreeViewStaticAttributesItem(TreeViewItem):

    """Static attributes item"""

    def __init__(self, parent):
        TreeViewItem.__init__(self, parent, "Static attributes")

        self.itemType = StaticAttributesItemType
        self.icon = getIcon('attributes.png')
        self.populated = False
        self.lazyPopulation = True


class TreeViewInstanceAttributesItem(TreeViewItem):

    """Instance attributes item"""

    def __init__(self, parent):

        TreeViewItem.__init__(self, parent, "Instance attributes")

        self.itemType = InstanceAttributesItemType
        self.icon = getIcon('attributes.png')
        self.populated = False
        self.lazyPopulation = True


class TreeViewCodingItem(TreeViewItem):

    """coding item"""

    def __init__(self, parent, encodingObj):
        TreeViewItem.__init__(self, parent, encodingObj.name)

        self.sourceObj = encodingObj
        self.itemType = CodingItemType
        self.icon = getIcon('textencoding.png')

    def updateData(self, encodingObj):
        """Updates data model source"""
        self.sourceObj = encodingObj
        self.setData(0, encodingObj.name)


class TreeViewImportItem(TreeViewItem):

    """Single import item"""

    def __init__(self, parent, importObj):
        TreeViewItem.__init__(self, parent, importObj.getDisplayName())

        self.sourceObj = importObj
        self.itemType = ImportItemType
        self.icon = getIcon('imports.png')

        self.populated = False
        self.lazyPopulation = True

    def updateData(self, importObj):
        """Updates data model source"""
        self.sourceObj = importObj
        self.setData(0, importObj.getDisplayName())


class TreeViewWhatItem(TreeViewItem):

    """Single what imported item"""

    def __init__(self, parent, whatObj):
        TreeViewItem.__init__(self, parent, whatObj.getDisplayName())

        self.sourceObj = whatObj
        self.itemType = ImportWhatItemType
        self.icon = getIcon('importwhat.png')

    def updateData(self, whatObj):
        """Updates data model source"""
        self.sourceObj = whatObj
        self.setData(0, whatObj.getDisplayName())


class TreeViewFunctionItem(TreeViewItem):

    """Single function / class  method item"""

    def __init__(self, parent, functionObj):
        TreeViewItem.__init__(self, parent, functionObj.getDisplayName())

        self.sourceObj = functionObj
        self.itemType = FunctionItemType

        self.__updateTooltip()

        if functionObj.isPrivate():
            self.icon = getIcon('method_private.png')
        elif functionObj.isProtected():
            self.icon = getIcon('method_protected.png')
        else:
            self.icon = getIcon('method.png')

        self.populated = False
        self.lazyPopulation = True

    def updateData(self, functionObj):
        """Updates data model source"""
        self.sourceObj = functionObj
        self.setData(0, functionObj.getDisplayName())
        self.__updateTooltip()

    def __updateTooltip(self):
        """Sets the tooltip value"""
        self.toolTip = ""
        if self.sourceObj.docstring is not None:
            self.toolTip = self.sourceObj.docstring.text


class TreeViewClassItem(TreeViewItem):

    """Single class item"""

    def __init__(self, parent, classObj):
        TreeViewItem.__init__(self, parent, classObj.getDisplayName())

        self.sourceObj = classObj
        self.itemType = ClassItemType

        self.__updateTooltip()

        if classObj.isPrivate():
            self.icon = getIcon('class_private.png')
        elif classObj.isProtected():
            self.icon = getIcon('class_protected.png')
        else:
            self.icon = getIcon('class.png')

        # Decide if it should be expandable
        if classObj.decorators or \
           classObj.functions or \
           classObj.classes or \
           classObj.classAttributes or \
           classObj.instanceAttributes:
            self.populated = False
            self.lazyPopulation = True

    def updateData(self, classObj):
        """Updates data model source"""
        self.sourceObj = classObj
        self.setData(0, classObj.getDisplayName())
        self.__updateTooltip()

    def __updateTooltip(self):
        """Sets the tooltip value"""
        self.toolTip = ""
        if self.sourceObj.docstring is not None:
            self.toolTip = self.sourceObj.docstring.text


class TreeViewDecoratorItem(TreeViewItem):

    """Single decorator item"""

    def __init__(self, parent, decoratorObj):
        TreeViewItem.__init__(self, parent, decoratorObj.getDisplayName())

        self.sourceObj = decoratorObj
        self.itemType = DecoratorItemType
        self.icon = getIcon('decorator.png')

    def updateData(self, decoratorObj):
        """Updates data model source"""
        self.sourceObj = decoratorObj
        self.setData(0, decoratorObj.getDisplayName())


class TreeViewAttributeItem(TreeViewItem):

    """Single attribute item"""

    def __init__(self, parent, attributeObj):
        TreeViewItem.__init__(self, parent, attributeObj.name)

        self.sourceObj = attributeObj
        self.itemType = AttributeItemType
        self.__setIcon()

    def updateData(self, attributeObj):
        """Updates data model source"""
        self.sourceObj = attributeObj
        self.setData(0, attributeObj.name)
        self.__setIcon()

    def __setIcon(self):
        """Sets the icon depending on access type"""
        if self.sourceObj.isPrivate():
            self.icon = getIcon('attribute_private.png')
        elif self.sourceObj.isProtected():
            self.icon = getIcon('attribute_protected.png')
        else:
            self.icon = getIcon('attribute.png')


class TreeViewGlobalItem(TreeViewItem):

    """Single global var item"""

    def __init__(self, parent, globalObj):
        TreeViewItem.__init__(self, parent, globalObj.name)

        self.sourceObj = globalObj
        self.itemType = GlobalItemType
        self.__setIcon()

    def updateData(self, globalObj):
        """Updates data model source"""
        self.sourceObj = globalObj
        self.setData(0, globalObj.name)
        self.__setIcon()

    def __setIcon(self):
        """Sets the icon depending on access type"""
        if self.sourceObj.isPrivate():
            self.icon = getIcon('attribute_private.png')
        elif self.sourceObj.isProtected():
            self.icon = getIcon('attribute_protected.png')
        else:
            self.icon = getIcon('attribute.png')
