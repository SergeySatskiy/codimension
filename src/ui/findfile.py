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

"""Find file feature implementation"""

import os
import os.path
from cdmpyparser import getBriefModuleInfoFromMemory
from utils.globals import GlobalData
from utils.fileutils import getFileProperties, isPythonMime
from utils.settings import Settings
from utils.diskvaluesrelay import getFindFileHistory, setFindFileHistory
from .qt import (Qt, QAbstractItemModel, QRegExp, QModelIndex,
                 QTreeView, QAbstractItemView, QDialog, QVBoxLayout,
                 QCursor, QSizePolicy, QHeaderView, QComboBox,
                 QSortFilterProxyModel, QApplication)
from .itemdelegates import NoOutlineHeightDelegate
from .combobox import EnterSensitiveComboBox


class FileItemRoot():

    """Files list root item"""

    def __init__(self, values):
        self.itemData = values
        self.childItems = []
        self.childItemsSize = 0

    def columnCount(self):
        """Provides the number of columns"""
        return len(self.itemData)

    def data(self, column):
        """Provides a value of the given column"""
        try:
            return self.itemData[column]
        except:
            return ''

    def appendChild(self, child):
        """Add a child item"""
        self.childItems.append(child)
        self.childItemsSize += 1

    def childCount(self):
        """Provides the number of children"""
        return self.childItemsSize

    def removeChildren(self):
        """Removes all the children"""
        self.childItems = []
        self.childItemsSize = 0

    def child(self, row):
        """Provides a reference to a child"""
        return self.childItems[row]

    @staticmethod
    def parent():
        """Provides a reference to the parent item"""
        return None

    # Arguments: other, column, order
    def lessThan(self, other, column, _):
        """Check, if the item is less than another"""
        try:
            self.itemData[column] < other.itemData[column]
        except:
            return False


class FileItem():

    """Files list item"""

    def __init__(self, parent, icon, fullname, tooltip):
        self.parentItem = parent
        self.icon = icon

        # Item data is below
        self.basename = os.path.basename(fullname)
        self.dirname = os.path.dirname(fullname) + os.path.sep
        self.tooltip = tooltip

    @staticmethod
    def columnCount():
        """Provides the number of columns"""
        return 2    # Base name and full path

    def data(self, column):
        """Provides a value for the column"""
        if column == 0:
            return self.basename
        if column == 1:
            return self.dirname + self.basename
        return ""

    @staticmethod
    def childCount():
        """Provides the number of children"""
        return 0

    def parent(self):
        """Provides a reference to the parent item"""
        return self.parentItem

    # Arguments: other, column, order
    def lessThan(self, other, column, _):
        """Check, if the item is less than another"""
        if column == 0:
            return self.basename < other.basename
        return self.dirname + self.basename < other.dirname + other.basename


class FindFileModel(QAbstractItemModel):

    """Find file data model implementation"""

    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.rootItem = FileItemRoot(["File name", "Full path"])
        self.count = 0
        self.__populateModel()

    def __populateModel(self):
        """Populates the list names model"""
        self.clear()

        # If a project is loaded then take the project
        # If not - take opened files
        if GlobalData().project.isLoaded():
            self.__populateFromProject()
        else:
            self.__populateFromOpened()

    def __populateFromProject(self):
        """Populates find name dialog from the project files"""
        mainWindow = GlobalData().mainWindow
        showTooltips = Settings()['findFileTooltips']
        for fname in GlobalData().project.filesList:
            if fname.endswith(os.path.sep):
                continue
            mime, icon, _ = getFileProperties(fname)
            tooltip = ""
            if showTooltips and isPythonMime(mime):
                widget = mainWindow.getWidgetForFileName(fname)
                if widget is None:
                    info = GlobalData().briefModinfoCache.get(fname)
                else:
                    content = widget.getEditor().text
                    info = getBriefModuleInfoFromMemory(content)
                if info.docstring is not None:
                    tooltip = info.docstring.text
            newItem = FileItem(self.rootItem, icon, fname, tooltip)
            self.rootItem.appendChild(newItem)
            self.count += 1

    def __populateFromOpened(self):
        """Populates the name dialog from the opened files"""
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        showTooltips = Settings()['findFileTooltips']
        for record in editorsManager.getTextEditors():
            # uuid = record[0]
            fname = record[1]
            widget = record[2]
            mime, icon, _ = getFileProperties(fname)
            tooltip = ""
            if showTooltips and isPythonMime(mime):
                content = widget.getEditor().text
                info = getBriefModuleInfoFromMemory(content)
                if info.docstring is not None:
                    tooltip = info.docstring.text
            newItem = FileItem(self.rootItem, icon, fname, tooltip)
            self.rootItem.appendChild(newItem)
            self.count += 1

    def columnCount(self, parent=QModelIndex()):
        """Provides the number of columns"""
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self.rootItem.columnCount()

    def rowCount(self, parent=QModelIndex()):
        """Provides the number of rows"""
        # Only the first column should have children
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return self.rootItem.childCount()

        parentItem = parent.internalPointer()
        return parentItem.childCount()

    def data(self, index, role):
        """Provides data of an item"""
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            item = index.internalPointer()
            if index.column() < item.columnCount():
                return item.data(index.column())
            elif index.column() == item.columnCount() and \
                index.column() < self.columnCount(self.parent(index)):
                # This is for the case when an item under a multi-column
                # parent doesn't have a value for all the columns
                return ""
        elif role == Qt.DecorationRole:
            if index.column() == 0:
                return index.internalPointer().icon
        elif role == Qt.ToolTipRole:
            item = index.internalPointer()
            if item.tooltip != "":
                return item.tooltip
        return None

    @staticmethod
    def flags(index):
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

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        try:
            childItem = parentItem.child(row)
        except IndexError:
            childItem = None
            return QModelIndex()

        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def parent(self, index):
        """Provides the index of the parent object"""
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def hasChildren(self, parent=QModelIndex()):
        """Checks for the presence of child items"""
        # Only the first column should have children
        if parent.column() > 0:
            return False

        if not parent.isValid():
            return self.rootItem.childCount() > 0
        return parent.internalPointer().childCount() > 0

    def clear(self):
        """Clears the model"""
        self.beginResetModel()
        self.rootItem.removeChildren()
        self.endResetModel()

    @staticmethod
    def item(index):
        """Provides a reference to an item"""
        if not index.isValid():
            return None
        return index.internalPointer()


class FindFileSortFilterProxyModel(QSortFilterProxyModel):

    """Find file dialog sort filter proxy model"""

    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.__sortColumn = None    # Avoid pylint complains
        self.__sortOrder = None     # Avoid pylint complains

        self.__filters = []
        self.__filtersCount = 0
        self.__sourceModelRoot = None

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

    def setFilter(self, text):
        """Sets the new filters"""
        self.__filters = []
        self.__filtersCount = 0
        self.__sourceModelRoot = None
        for part in str(text).strip().split():
            regexp = QRegExp(part, Qt.CaseInsensitive, QRegExp.RegExp2)
            self.__filters.append(regexp)
            self.__filtersCount += 1
        self.__sourceModelRoot = self.sourceModel().rootItem

    # Arguments: sourceRow, sourceParent
    def filterAcceptsRow(self, sourceRow, _):
        """Filters rows"""
        if self.__filtersCount == 0 or self.__sourceModelRoot is None:
            return True     # No filters

        nameToMatch = self.__sourceModelRoot.child(sourceRow).basename
        for regexp in self.__filters:
            if regexp.indexIn(nameToMatch) == -1:
                return False
        return True


class FilesBrowser(QTreeView):

    """List of files widget implementation"""

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)

        self.__parentDialog = parent
        self.__model = FindFileModel()
        self.__sortModel = FindFileSortFilterProxyModel()
        self.__sortModel.setDynamicSortFilter(True)
        self.__sortModel.setSourceModel(self.__model)
        self.setModel(self.__sortModel)
        self.selectedIndex = None

        self.activated.connect(self.openCurrentItem)

        self.setRootIsDecorated(False)
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

        self.layoutDisplay()

    def selectionChanged(self, selected, deselected):
        """Slot is called when the selection has been changed"""
        if selected.indexes():
            self.selectedIndex = selected.indexes()[0]
        else:
            self.selectedIndex = None
        QTreeView.selectionChanged(self, selected, deselected)

    def layoutDisplay(self):
        """Performs the layout operation"""
        self.header().resizeSections(QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(True)
        self._resort()

    def _resort(self):
        """Re-sorts the tree"""
        self.model().sort(self.header().sortIndicatorSection(),
                          self.header().sortIndicatorOrder())

    def openCurrentItem(self):
        """Triggers when an item is clicked or double clicked"""
        if self.selectedIndex is not None:
            item = self.model().item(self.selectedIndex)
            self.openItem(item)

    def openItem(self, item):
        """Handles the case when an item is activated"""
        path = item.dirname + item.basename
        GlobalData().mainWindow.detectTypeAndOpenFile(path)
        self.__parentDialog.onClose()

    def getTotal(self):
        """Provides the total number of items"""
        return self.model().sourceModel().count

    def getVisible(self):
        """Provides the number of currently visible items"""
        return self.model().rowCount()

    def setFilter(self, text):
        """Called when the filter has been changed"""
        # Notify the filtering model of the new filters
        self.model().setFilter(text)

        # This is to trigger filtering - ugly but I don't know how else
        self.model().setFilterRegExp("")


class FindFileDialog(QDialog):

    """Find file dialog implementation"""

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.__filesBrowser = None
        self.findCombo = None
        self.__projectLoaded = GlobalData().project.isLoaded()

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.__createLayout()
        self.findCombo.setFocus()
        QApplication.restoreOverrideCursor()

        # Set the window title and restore the previous searches
        self.__findFileHistory = getFindFileHistory()
        self.findCombo.addItems(self.__findFileHistory)
        self.findCombo.setEditText("")

        self.findCombo.editTextChanged.connect(self.__filterChanged)

        self.__highlightFirst()
        self.__updateTitle()

    def __highlightFirst(self):
        """Sets the selection to the first item in the files list"""
        if self.__filesBrowser.getVisible() == 0:
            return
        self.__filesBrowser.clearSelection()

        first = self.__filesBrowser.model().index(0, 0, QModelIndex())
        self.__filesBrowser.setCurrentIndex(first)
        self.__filesBrowser.scrollTo(first)

    def __updateTitle(self):
        """Updates the window title"""
        title = "Find file in the "
        if self.__projectLoaded:
            title += "project: "
        else:
            title += "opened files: "
        title += str(self.__filesBrowser.getVisible()) + " of " + \
            str(self.__filesBrowser.getTotal())
        self.setWindowTitle(title)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(600, 300)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        self.__filesBrowser = FilesBrowser(self)
        verticalLayout.addWidget(self.__filesBrowser)

        self.findCombo = EnterSensitiveComboBox(self)
        self.__tuneCombo(self.findCombo)
        self.findCombo.lineEdit().setToolTip(
            "Regular expression to search for")
        verticalLayout.addWidget(self.findCombo)
        self.findCombo.enterClicked.connect(self.__enterInFilter)

    @staticmethod
    def __tuneCombo(comboBox):
        """Sets the common settings for a combo box"""
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            comboBox.sizePolicy().hasHeightForWidth())
        comboBox.setSizePolicy(sizePolicy)
        comboBox.setEditable(True)
        comboBox.setInsertPolicy(QComboBox.InsertAtTop)
        comboBox.setCompleter(None)
        comboBox.setDuplicatesEnabled(False)

    def __filterChanged(self, text):
        """Triggers when the filter text changed"""
        self.__filesBrowser.setFilter(text)
        self.__highlightFirst()
        self.__updateTitle()

    def onClose(self):
        """Called when an item has been selected"""
        # Save the current filter if needed
        filterText = self.findCombo.currentText().strip()
        if filterText != "":
            if filterText in self.__findFileHistory:
                self.__findFileHistory.remove(filterText)
            self.__findFileHistory.insert(0, filterText)
            if len(self.__findFileHistory) > 32:
                self.__findFileHistory = self.__findFileHistory[:32]

            setFindFileHistory(self.__findFileHistory)
        self.close()

    def __enterInFilter(self):
        """Handles ENTER and RETURN keys in the find combo"""
        if self.__filesBrowser.getVisible() == 0:
            return
        self.__filesBrowser.openCurrentItem()
