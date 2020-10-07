# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2020  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""AST representation"""

import ast
import logging
from ui.qt import (QTreeWidget, QTreeWidgetItem, QAbstractItemView,
                   QHeaderView, pyqtSignal)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.astutils import parseSourceToAST


class ASTView(QTreeWidget):

    sigGotoLine = pyqtSignal(int, int)

    def __init__(self, navBar, parent):
        QTreeWidget.__init__(self, parent)
        self.__navBar = navBar

        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setSortingEnabled(False)
        self.setItemDelegate(NoOutlineHeightDelegate(4))
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setExpandsOnDoubleClick(False)

        self.__headerItem = QTreeWidgetItem(['Node', 'Position / items'])
        self.setHeaderItem(self.__headerItem)

        self.itemSelectionChanged.connect(self.__selectionChanged)
        self.itemActivated.connect(self.__activated)

    def populateAST(self, source, filename):
        """Populates the AST tree"""
        self.__navBar.clearWarnings()
        hScroll = self.horizontalScrollBar().value()
        vScroll = self.verticalScrollBar().value()
        try:
            tree = parseSourceToAST(source, filename)
            self.__parentStack = [None]

            self.clear()
            self.addNodeRecursive(tree)

            self.header().resizeSections(QHeaderView.ResizeToContents)
            self.__navBar.updateInfoIcon(self.__navBar.STATE_OK_UTD)

            self.horizontalScrollBar().setValue(hScroll)
            self.verticalScrollBar().setValue(vScroll)
        except Exception as exc:
            self.__navBar.updateInfoIcon(self.__navBar.STATE_BROKEN_UTD)
            self.__navBar.setErrors(
                'Parse source to AST error:\n' + str(exc))

    def addNodeRecursive(self, node, prefix=None):
        nodeName = node.__class__.__name__
        if prefix is not None:
            nodeName = prefix + nodeName
        treeNode = QTreeWidgetItem([nodeName, self.__getNodePosition(node)])
        if self.__parentStack[-1] is None:
            self.addTopLevelItem(treeNode)
        else:
            self.__parentStack[-1].addChild(treeNode)

        for fieldName in node._fields:
            fieldValue = getattr(node, fieldName)
            if isinstance(fieldValue, ast.AST):
                if fieldValue._fields:
                    self.__parentStack.append(treeNode)
                    self.addNodeRecursive(fieldValue, fieldName + ': ')
                    self.__parentStack.pop(-1)
                else:
                    treeNode.addChild(
                        QTreeWidgetItem(
                            [fieldName + ': ' + fieldValue.__class__.__name__,
                             self.__getNodePosition(fieldValue)]))
            elif self.__isScalar(fieldValue):
                treeNode.addChild(
                    QTreeWidgetItem([fieldName + ': ' + repr(fieldValue), '']))
            elif isinstance(fieldValue, list):
                listLength = len(fieldValue)
                txt = str(listLength) + ' item'
                if listLength != 1:
                    txt += 's'
                listNode = QTreeWidgetItem([fieldName + ': [...]', txt])
                treeNode.addChild(listNode)
                self.expandItem(listNode)
                self.__parentStack.append(listNode)
                for index, listItem in enumerate(fieldValue):
                    prefix = '[' + str(index) + ']: '
                    if self.__isScalar(listItem):
                        treeNode.addChild(
                            QTreeWidgetItem([prefix + repr(listItem), '']))
                    else:
                        self.addNodeRecursive(listItem, prefix)
                self.__parentStack.pop(-1)
            else:
                logging.error('AST node is not recognized. Skipping...')
        self.expandItem(treeNode)

    @staticmethod
    def __getNodePosition(astNode):
        pos = ''
        if hasattr(astNode, 'lineno'):
            pos = str(astNode.lineno)
            if hasattr(astNode, 'col_offset'):
                pos += ':' + str(astNode.col_offset)
        if hasattr(astNode, 'end_lineno'):
            pos += ' - ' + str(astNode.end_lineno)
            if hasattr(astNode, 'end_col_offset'):
                pos += ':' + str(astNode.end_col_offset)
        return pos

    @staticmethod
    def __isScalar(val):
        if isinstance(val, str):
            return True
        if isinstance(val, int):
            return True
        if isinstance(val, float):
            return True
        if isinstance(val, bytes):
            return True
        if val is None:
            return True

    def __selectionChanged(self):
        """Handles an AST item selection"""
        selected = list(self.selectedItems())
        self.__navBar.setSelectionLabel(len(selected), None)
        if selected:
            if len(selected) == 1:
                current = selected[0]
                path = self.__getPathElement(current)
                while current.parent() is not None:
                    current = current.parent()
                    path = self.__getPathElement(current) + u' \u2192 ' + path
                self.__navBar.setPath(path)
            else:
                self.__navBar.setPath('')
        else:
            self.__navBar.setPath('')

    @staticmethod
    def __getPathElement(node):
        text = node.text(0)
        if text.startswith('['):
            # List item, the actual purpose follows the index
            return text
        # Regular node, after ':' there might be its type
        return text.split(':')[0]

    @staticmethod
    def __getLinePos(node):
        while node is not None:
            text = node.text(1)
            if text:
                if not 'item' in text:
                    firstRegion = text.split('-')[0].strip()
                    try:
                        parts = firstRegion.split(':')
                        line = int(parts[0])
                        pos = 0
                        if len(parts) == 2:
                            pos = int(parts[1])
                        return line, pos
                    except:
                        pass
            node = node.parent()
        # Not found, e.g. it is a module
        return 1, 0

    def __activated(self, item, _):
        """Handles the double click (or Enter) on an AST item"""
        line, pos = self.__getLinePos(item)
        self.sigGotoLine.emit(line, pos + 1)

