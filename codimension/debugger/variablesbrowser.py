# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""The debugger namespace viewer implementation"""


from ui.qt import (Qt, QRegExp, QAbstractItemView, QHeaderView, QTreeWidget)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.settings import Settings
from .variableitems import (VariableItem, SpecialVariableItem,
                            ArrayElementVariableItem,
                            SpecialArrayElementVariableItem,
                            INDICATORS)
from .varfilters import VARIABLE_FILTERS
from .viewvariable import ViewVariableDialog
from .client.protocol_cdm_dbg import VAR_TYPE_DISP_STRINGS


INDICATOR_PATTERN = "|".join([QRegExp.escape(indicator)
                              for indicator in INDICATORS])
RX_CLASS = QRegExp('<.*(instance|object) at 0x.*>')
RX_CLASS2 = QRegExp('class .*')
RX_CLASS3 = QRegExp('<class .* at 0x.*>')
DVAR_RX_CLASS1 = QRegExp(
    r'<.*(instance|object) at 0x.*>({0})'.format(INDICATOR_PATTERN))
DVAR_RX_CLASS2 = QRegExp(
    r'<class .* at 0x.*>({0})'.format(INDICATOR_PATTERN))
DVAR_RX_ARRAY_ELEMENT = QRegExp(r'^\d+$')
DVAR_RX_SPECIAL_ARRAY_ELEMENT = QRegExp(
    r'^\d+({0})$'.format(INDICATOR_PATTERN))
RX_NONPRINTABLE = QRegExp(r"""(\\x\d\d)+""")

TYPE_TO_INDICATORS = {
    # Python types
    'list': '[]',
    'tuple': '()',
    'dict': '{:}',
    'set': '{}',
    'frozenset': '{}'}


class VariablesBrowser(QTreeWidget):

    """Variables browser implementation"""

    def __init__(self, debugger, parent=None):
        QTreeWidget.__init__(self, parent)

        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setItemDelegate(NoOutlineHeightDelegate(4))

        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.setHeaderLabels(["Name", "Value", "Type"])
        header = self.header()
        header.setSortIndicator(0, Qt.AscendingOrder)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.setStretchLastSection(True)

        self.itemExpanded.connect(self.__expandItemSignal)
        self.itemCollapsed.connect(self.collapseItem)

        self.resortEnabled = True
        self.openItems = []
        self.framenr = 0
        self.__debugger = debugger

        # Ugly filtering support
        self.__filterIsSet = False

        self.setSortingEnabled(True)

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        """ Disables horizontal scrolling when a row is clicked.

        Found here: http://qt-project.org/faq/answer/
                           how_can_i_disable_autoscroll_when
                           _selecting_a_partially_displayed_column_in
        """
        oldValue = self.horizontalScrollBar().value()
        QTreeWidget.scrollTo(self, index, hint)
        self.horizontalScrollBar().setValue(oldValue)

    def __findItem(self, slist, column, node=None):
        """Searches for an item.

        It is used to find a specific item in column,
        that is a child of node. If node is None, a child of the
        QTreeWidget is searched.
        """
        if node is None:
            count = self.topLevelItemCount()
        else:
            count = node.childCount()

        if column == 0:
            searchStr = VariableItem.extractId(slist[0])[0]
        else:
            searchStr = slist[0]

        for index in range(count):
            if node is None:
                item = self.topLevelItem(index)
            else:
                item = node.child(index)

            if item.text(column) == searchStr:
                if len(slist) > 1:
                    item = self.__findItem(slist[1:], column, item)
                return item
        return None

    def __clearScopeVariables(self, areGlobals):
        """Removes those variables which belong to the specified frame"""
        count = self.topLevelItemCount()
        for index in range(count - 1, -1, -1):
            item = self.topLevelItem(index)
            if item.isGlobal() == areGlobals:
                self.takeTopLevelItem(index)

    def showVariables(self, areGlobals, vlist, frmnr):
        """Shows variables list"""
        self.current = self.currentItem()
        if self.current:
            self.curpathlist = self.__buildTreePath(self.current)
        self.__clearScopeVariables(areGlobals)
        self.__scrollToItem = None
        self.framenr = frmnr

        if len(vlist):
            self.resortEnabled = False
            self.setSortingEnabled(False)
            for (var, vtype, value) in vlist:
                item = self.__addItem(None, areGlobals, vtype, var, value)
                item.setHidden(not self.__variableToShow(item.getName(),
                                                         item.isGlobal(),
                                                         item.getType()))

            # reexpand tree
            openItems = sorted(self.openItems[:])
            self.openItems = []
            for itemPath in openItems:
                itm = self.__findItem(itemPath, 0)
                if itm is not None:
                    self.expandItem(itm)
                else:
                    self.openItems.append(itemPath)

            if self.current:
                citm = self.__findItem(self.curpathlist, 0)
                if citm:
                    self.setCurrentItem(citm)
                    citm.setSelected(True)
                    self.scrollToItem(citm, QAbstractItemView.PositionAtTop)
                    self.current = None

            self.__resizeSections()

            self.resortEnabled = True
            self.setSortingEnabled(True)
            self.__resort()

    def __resizeSections(self):
        """Resizes the variable sections"""
        if self.topLevelItemCount() == 0:
            return

        header = self.header()
        nameSectionSize = header.sectionSize(0)
        header.resizeSections(QHeaderView.ResizeToContents)
        if header.sectionSize(0) < nameSectionSize:
            header.resizeSection(0, nameSectionSize)

    def showVariable(self, isGlobal, vlist):
        """Shows variables in a list"""
        # vlist the list of subitems to be displayed. The first element gives
        # the path of the parent variable. Each other listentry is a tuple of
        # three values:
        #   the variable name (string)
        #   the variables type (string)
        #   the variables value (string)

        resortEnabled = self.resortEnabled
        self.resortEnabled = False
        self.setSortingEnabled(False)

        if self.current is None:
            self.current = self.currentItem()
            if self.current:
                self.curpathlist = self.__buildTreePath(self.current)

        if vlist:
            item = self.__findItem(vlist[0], 0)
            for var, vtype, value in vlist[1:]:
                newItem = self.__addItem(item, isGlobal, vtype, var, value)
                newItem.setHidden(not self.__variableToShow(newItem.getName(),
                                                            newItem.isGlobal(),
                                                            newItem.getType()))

        # reexpand tree
        openItems = sorted(self.openItems[:])
        self.openItems = []
        for itemPath in openItems:
            item = self.__findItem(itemPath, 0)
            if item is not None and not item.isExpanded():
                if item.populated:
                    self.blockSignals(True)
                    item.setExpanded(True)
                    self.blockSignals(False)
                else:
                    self.expandItem(item)
        self.openItems = openItems[:]

        if self.current:
            citm = self.__findItem(self.curpathlist, 0)
            if citm:
                self.setCurrentItem(citm)
                citm.setSelected(True)
                if self.__scrollToItem:
                    self.scrollToItem(self.__scrollToItem,
                                      QAbstractItemView.PositionAtTop)
                else:
                    self.scrollToItem(citm, QAbstractItemView.PositionAtTop)
                self.current = None
        elif self.__scrollToItem:
            self.scrollToItem(self.__scrollToItem,
                              QAbstractItemView.PositionAtTop)

        self.__resizeSections()

        self.resortEnabled = resortEnabled
        if self.resortEnabled:
            self.setSortingEnabled(True)
        self.__resort()

    def __generateItem(self, parentItem, isGlobal,
                       varName, varValue, varType, isSpecial=False):
        """Generates an appropriate variable item"""
        if isSpecial:
            if DVAR_RX_CLASS1.exactMatch(varName) or \
               DVAR_RX_CLASS2.exactMatch(varName):
                isSpecial = False

        if RX_CLASS2.exactMatch(varType):
            return SpecialVariableItem(parentItem, self.__debugger, isGlobal,
                                       varName, varValue, varType[7:-1],
                                       self.framenr)

        elif varType != "void *" and \
             (RX_CLASS.exactMatch(varValue) or
              RX_CLASS3.exactMatch(varValue) or
              isSpecial):
            if DVAR_RX_SPECIAL_ARRAY_ELEMENT.exactMatch(varName):
                return SpecialArrayElementVariableItem(parentItem,
                                                       self.__debugger,
                                                       isGlobal,
                                                       varName, varValue,
                                                       varType,
                                                       self.framenr)
            return SpecialVariableItem(parentItem, self.__debugger, isGlobal,
                                       varName, varValue, varType,
                                       self.framenr)
        elif varType in ["numpy.ndarray", "django.MultiValueDict",
                         "array.array"]:
            return SpecialVariableItem(parentItem, self.__debugger, isGlobal,
                                       varName, "{0} items".format(varValue),
                                       varType, self.framenr)
        else:
            if DVAR_RX_ARRAY_ELEMENT.exactMatch(varName):
                return ArrayElementVariableItem(parentItem, isGlobal,
                                                varName, varValue, varType)
            return VariableItem(parentItem, isGlobal,
                                varName, varValue, varType)

        print("WARNING: Reached the end without forming a variable!")

    def __getDisplayType(self, varType):
        """Provides a variable type for display purpose"""
        try:
            dvtype = VAR_TYPE_DISP_STRINGS[varType]
        except KeyError:
            if varType == 'classobj':
                dvtype = VAR_TYPE_DISP_STRINGS['instance']
            else:
                dvtype = varType
        return dvtype

    def __addItem(self, parentItem, isGlobal, varType, varName, varValue):
        """Adds a new item to the children of the parentItem"""
        if parentItem is None:
            parentItem = self

        try:
            varName = '{0}{1}'.format(varName, TYPE_TO_INDICATORS[varType])
        except KeyError:
            pass

        displayType = self.__getDisplayType(varType)
        if varType in ['list', 'tuple', 'dict', 'set', 'frozenset']:
            return self.__generateItem(parentItem, isGlobal,
                                       varName, str(varValue) + " item(s)",
                                       displayType,
                                       True)
        if varType in ['unicode', 'str']:
            if RX_NONPRINTABLE.indexIn(varValue) != -1:
                stringValue = varValue
            else:
                try:
                    stringValue = eval(varValue)
                    displayType += " (chars: " + str(len(stringValue)) + ")"
                except:
                    stringValue = varValue
            return self.__generateItem(parentItem, isGlobal,
                                       varName, stringValue,
                                       displayType)

        return self.__generateItem(parentItem, isGlobal,
                                   varName, varValue, displayType)

    def mouseDoubleClickEvent(self, mouseEvent):
        """Handles the mouse double click event"""
        item = self.itemAt(mouseEvent.pos())
        if item is None:
            return

        childCount = item.childCount()
        if childCount == 0:
            # Show the dialog
            dlg = ViewVariableDialog(self.__getQualifiedName(item),
                                     item.getType(), item.getValue(),
                                     item.isGlobal())
            dlg.exec_()
        else:
            QTreeWidget.mouseDoubleClickEvent(self, mouseEvent)

    def __getQualifiedName(self, item):
        """Provides a fully qualified name"""
        name = item.getName()
        if name[-2:] in ['[]', '{}', '()']:
            name = name[:-2]

        par = item.parent()
        nlist = [name]
        # build up the fully qualified name
        while par is not None:
            pname = par.getName()
            if pname[-2:] in ['[]', '{}', '()']:
                if nlist[0].endswith("."):
                    nlist[0] = '[%s].' % nlist[0][:-1]
                else:
                    nlist[0] = '[%s]' % nlist[0]
                nlist.insert(0, pname[:-2])
            else:
                nlist.insert(0, '%s.' % pname)
            par = par.parent()

        name = ''.join(nlist)
        return name

    def __buildTreePath(self, item):
        """Builds up a path from the top to the given item"""
        name = item.text(0)
        pathList = [name]

        parent = item.parent()
        # build up a path from the top to the item
        while parent is not None:
            parentVariableName = parent.text(0)
            pathList.insert(0, parentVariableName)
            parent = parent.parent()

        return pathList[:]

    def __expandItemSignal(self, parentItem):
        """Handles the expanded signal"""
        self.expandItem(parentItem)
        self.__scrollToItem = parentItem

    def expandItem(self, parentItem):
        """Handles the expanded signal"""
        pathList = self.__buildTreePath(parentItem)
        self.openItems.append(pathList)
        if parentItem.populated:
            return

        try:
            parentItem.expand()
            self.__resort()
        except AttributeError:
            QTreeWidget.expandItem(self, parentItem)

    def collapseItem(self, parentItem):
        """Handles the collapsed signal"""
        pathList = self.__buildTreePath(parentItem)
        self.openItems.remove(pathList)

        try:
            parentItem.collapse()
        except AttributeError:
            QTreeWidget.collapseItem(self, parentItem)

    def __resort(self):
        """Resorts the tree"""
        if self.resortEnabled:
            self.sortItems(self.sortColumn(),
                           self.header().sortIndicatorOrder())

    def getShownAndTotalCounts(self):
        """Provides the total number of variables and currently shown"""
        total = self.topLevelItemCount()
        shownCount = 0
        for index in range(total):
            if not self.topLevelItem(index).isHidden():
                shownCount += 1
        return shownCount, total

    def clear(self):
        """Resets everything"""
        self.resortEnabled = True
        self.openItems = []
        self.framenr = 0

        QTreeWidget.clear(self)

    def filterChanged(self):
        """Sets the new filter"""
        self.__filterIsSet = False
        for _, settingName, _ in VARIABLE_FILTERS:
            if not Settings()[settingName]:
                self.__filterIsSet = True
                break
        self.__applyFilters()

    def __applyFilters(self):
        """Re-applies the filters to the list"""
        resortEnabled = self.resortEnabled
        self.resortEnabled = False
        self.setSortingEnabled(False)

        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            toShow = self.__variableToShow(item.getName(),
                                           item.isGlobal(),
                                           item.getType())
            item.setHidden(not toShow)
            if toShow:
                self.__applyFiltersRecursively(item)

        self.__resizeSections()
        self.resortEnabled = resortEnabled
        if self.resortEnabled:
            self.setSortingEnabled(True)
        self.__resort()

    def __applyFiltersRecursively(self, item):
        """Applies the filter recursively to all the children of the item"""
        for index in range(item.childCount()):
            childItem = item.child(index)
            if not hasattr(childItem, "getName"):
                continue
            toShow = self.__variableToShow(childItem.getName(),
                                           childItem.isGlobal(),
                                           childItem.getType())
            childItem.setHidden(not toShow)
            if toShow:
                self.__applyFiltersRecursively(childItem)

    def __variableToShow(self, varName, isGlobal, varType):
        """Checks if the given item should be shown"""
        if not self.__filterIsSet:
            return True

        # Strip indicators from the name
        varName = str(varName)
        if varName.endswith("]") or \
           varName.endswith("}") or \
           varName.endswith(")"):
            varName = varName[:-2]   # Strip display purpose decor if so

        settings = Settings()
        for _, settingName, matchFunction in VARIABLE_FILTERS:
            if settings[settingName] is False:
                if matchFunction(isGlobal, varName, varType):
                    return False
        return True
