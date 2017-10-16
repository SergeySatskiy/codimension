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

"""Find name feature implementation"""


from cdmpyparser import getBriefModuleInfoFromMemory
from utils.globals import GlobalData
from utils.pixmapcache import getIcon
from utils.settings import Settings
from utils.fileutils import isPythonFile
from utils.diskvaluesrelay import getFindNameHistory, setFindNameHistory
from .qt import (Qt, QAbstractItemModel, QRegExp, QModelIndex,
                 QTreeView, QAbstractItemView, QDialog, QVBoxLayout, QCursor,
                 QComboBox, QSizePolicy, QSortFilterProxyModel, QApplication)
from .combobox import EnterSensitiveComboBox
from .itemdelegates import NoOutlineHeightDelegate


class NameItem():

    """Names list item"""

    def __init__(self, parent, icon, name, fileName, line, tooltip):
        self.parentItem = parent
        self.icon = icon

        self.childItems = []
        self.childItemsSize = 0

        # Item data is below
        self.name = name
        self.tooltip = ""
        if parent is not None:
            if tooltip == "":
                self.tooltip = fileName + ":" + str(line)
            else:
                self.tooltip = tooltip + "\n\n" + fileName + ":" + str(line)

    @staticmethod
    def columnCount():
        """Provides the number of columns"""
        return 1

    def data(self, column):
        """Provides a value for the column"""
        if column == 0:
            return self.name
        return ''

    def appendChild(self, child):
        """Appends a child item"""
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

    def parent(self):
        """Provides a reference to the parent item"""
        return self.parentItem

    # Arguments: other, column, order
    def lessThan(self, other, column, _):
        """Check, if the item is less than another"""
        if column == 0:
            return self.name < other.name
        return False


class FindNameModel(QAbstractItemModel):

    """Find name data model implementation"""

    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.rootItem = NameItem(None, None, "Name", "", "", "")
        self.count = 0
        self.showTooltips = Settings()['findNameTooltips']
        self.__populateModel()

    def __populateModel(self):
        """Populates the list names model"""
        self.clear()

        # If a project is loaded then take the project
        # If not - the opened files
        if GlobalData().project.isLoaded():
            self.__populateFromProject()
        else:
            self.__populateFromOpened()

    def __populateFromProject(self):
        """Populates find name dialog from the project files"""
        mainWindow = GlobalData().mainWindow
        for fname in GlobalData().project.filesList:
            if isPythonFile(fname):
                widget = mainWindow.getWidgetForFileName(fname)
                if widget is None:
                    info = GlobalData().briefModinfoCache.get(fname)
                else:
                    info = getBriefModuleInfoFromMemory(
                        widget.getEditor().text)
                self.__populateInfo(info, fname)

    def __populateInfo(self, info, fname):
        """Populates parsed info from a python file"""
        for item in info.globals:
            newItem = NameItem(self.rootItem, getIcon('globalvar.png'),
                               item.name, fname, item.line, "")
            self.rootItem.appendChild(newItem)
            self.count += 1

        for klass in info.classes:
            self.__polulateClass(klass, "", fname)
        for func in info.functions:
            self.__populateFunction(func, "", fname)

    def __polulateClass(self, klass, prefix, fname):
        """Recursively populates the given class"""
        if klass.isPrivate():
            icon = getIcon('class_private.png')
        elif klass.isProtected():
            icon = getIcon('class_protected.png')
        else:
            icon = getIcon('class.png')

        tooltip = ""
        if self.showTooltips and klass.docstring is not None:
            tooltip = klass.docstring.text

        classItem = NameItem(self.rootItem, icon, prefix + klass.name,
                             fname, klass.line, tooltip)
        self.rootItem.appendChild(classItem)
        self.count += 1

        for item in klass.classAttributes:
            newItem = NameItem(self.rootItem, getIcon('attributes.png'),
                               prefix + item.name, fname, item.line, "")
            self.rootItem.appendChild(newItem)
            self.count += 1

        for item in klass.instanceAttributes:
            newItem = NameItem(self.rootItem, getIcon('attributes.png'),
                               prefix + item.name, fname, item.line, "")
            self.rootItem.appendChild(newItem)
            self.count += 1

        for item in klass.functions:
            self.__populateFunction(item, prefix + klass.name + ".", fname)
        for item in klass.classes:
            self.__polulateClass(item, prefix + klass.name + ".", fname)

    def __populateFunction(self, func, prefix, fname):
        """Recursively populates the given function"""
        tooltip = ""
        if self.showTooltips and func.docstring is not None:
            tooltip = func.docstring.text

        funcItem = NameItem(self.rootItem, getIcon('method.png'),
                            prefix + func.name, fname, func.line, tooltip)
        self.rootItem.appendChild(funcItem)
        self.count += 1

        for item in func.functions:
            self.__populateFunction(item, prefix + func.name + ".", fname)
        for item in func.classes:
            self.__polulateClass(item, prefix + func.name + ".", fname)

    def __populateFromOpened(self):
        """Populates the name dialog from the opened files"""
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        for record in editorsManager.getTextEditors():
            # uuid = record[0]
            fname = record[1]
            widget = record[2]
            if isPythonFile(fname):
                content = widget.getEditor().text()
                info = getBriefModuleInfoFromMemory(content)
                self.__populateInfo(info, fname)

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


class FindNameSortFilterProxyModel(QSortFilterProxyModel):

    """Find name dialog sort filter proxy model"""

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

        nameToMatch = self.__sourceModelRoot.child(sourceRow).name
        for regexp in self.__filters:
            if regexp.indexIn(nameToMatch) == -1:
                return False
        return True


class NamesBrowser(QTreeView):

    """List of names widget implementation"""

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)

        self.__parentDialog = parent
        self.__model = FindNameModel()
        self.__sortModel = FindNameSortFilterProxyModel()
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
        infoLine = item.tooltip.split('\n')[-1]
        parts = infoLine.split(':')
        line = int(parts[-1])
        fname = ':'.join(parts[:-1])

        GlobalData().mainWindow.openFile(fname, line)
        self.__parentDialog.onClose()

    def getTotal(self):
        """Provides the total number of items"""
        return self.model().sourceModel().count

    def getVisible(self):
        """Provides the number of visible items"""
        return self.model().rowCount()

    def setFilter(self, text):
        """Called when the filter has been changed"""
        # Notify the filtering model of the new filters
        self.model().setFilter(text)

        # This is to trigger filtering - ugly but I don't know how else
        self.model().setFilterRegExp("")


class FindNameDialog(QDialog):

    """Find name dialog implementation"""

    def __init__(self, what="", parent=None):
        QDialog.__init__(self, parent)

        self.__namesBrowser = None
        self.findCombo = None
        self.__projectLoaded = GlobalData().project.isLoaded()

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.__createLayout()
        self.findCombo.setFocus()
        QApplication.restoreOverrideCursor()

        # Set the window title and restore the previous searches
        self.__findNameHistory = getFindNameHistory()
        self.findCombo.addItems(self.__findNameHistory)
        self.findCombo.setEditText(what)

        self.findCombo.editTextChanged.connect(self.__filterChanged)

        self.__highlightFirst()
        self.__updateTitle()

    def __highlightFirst(self):
        """Sets the selection to the first item in the files list"""
        if self.__namesBrowser.getVisible() == 0:
            return
        self.__namesBrowser.clearSelection()

        first = self.__namesBrowser.model().index(0, 0, QModelIndex())
        self.__namesBrowser.setCurrentIndex(first)
        self.__namesBrowser.scrollTo(first)

    def __updateTitle(self):
        """Updates the window title"""
        title = "Find name in the "
        if self.__projectLoaded:
            title += "project: "
        else:
            title += "opened files: "
        title += str(self.__namesBrowser.getVisible()) + " of " + \
                 str(self.__namesBrowser.getTotal())
        self.setWindowTitle(title)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(600, 300)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        self.__namesBrowser = NamesBrowser(self)
        verticalLayout.addWidget(self.__namesBrowser)

        self.findCombo = EnterSensitiveComboBox(self)
        self.__tuneCombo(self.findCombo)
        self.findCombo.lineEdit().setToolTip("Regular expression "
                                             "to search for")
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
        self.__namesBrowser.setFilter(text)
        self.__highlightFirst()
        self.__updateTitle()

    def onClose(self):
        """Called when an item has been selected"""
        # Save the current filter if needed
        filterText = self.findCombo.currentText().strip()
        if filterText != "":
            if filterText in self.__findNameHistory:
                self.__findNameHistory.remove(filterText)
            self.__findNameHistory.insert(0, filterText)
            if len(self.__findNameHistory) > 32:
                self.__findNameHistory = self.__findNameHistory[:32]
            setFindNameHistory(self.__findNameHistory)
        self.close()

    def __enterInFilter(self):
        """Handles ENTER and RETURN keys in the find combo"""
        if self.__namesBrowser.getVisible() != 0:
            self.__namesBrowser.openCurrentItem()
