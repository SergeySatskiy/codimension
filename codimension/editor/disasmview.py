# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2020 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Disassembly view"""

from ui.qt import (QTreeWidget, QTreeWidgetItem, QAbstractItemView,
                   QHeaderView, pyqtSignal, QWidget, QSizePolicy,
                   QVBoxLayout, Qt)
from ui.itemdelegates import NoOutlineHeightDelegate
from ui.labels import HeaderLabel
from utils.settings import Settings
from analysis.disasm import getFileDisassembled, getBufferDisassembled


# https://stackoverflow.com/questions/12673074/how-should-i-understand-the-output-of-dis-dis
# The output of the disassembly basically looks like that (3.6 and up):
# (1)|(2)|(3)|(4)|          (5)         |(6)|  (7)
# ---|---|---|---|----------------------|---|-------
#   2|   |   |  0|LOAD_FAST             |  0|(num)
#    |-->|   |  2|LOAD_CONST            |  1|(42)
#    |   |   |  4|COMPARE_OP            |  2|(==)
#    |   |   |  6|POP_JUMP_IF_FALSE     | 12|
#    |   |   |   |                      |   |
#   3|   |   |  8|LOAD_CONST            |  2|(True)
#    |   |   | 10|RETURN_VALUE          |   |
#    |   |   |   |                      |   |
#   4|   |>> | 12|LOAD_CONST            |  3|(False)
#    |   |   | 14|RETURN_VALUE          |   |
#
# (1) The corresponding line number in the source code
# (2) Optionally indicates the current instruction executed (when the bytecode
#     comes from a frame object for example)
# (3) A label which denotes a possible JUMP from an earlier instruction to
#     this one
# (4) The address in the bytecode which corresponds to the byte index (those
#     are multiples of 2 because Python 3.6 use 2 bytes for each instruction,
#     while it could vary in previous versions)
# (5) The instruction name (also called opname), each one is briefly explained
#     in the dis module and their implementation can be found in ceval.c
#     (the core loop of CPython)
# (6) The argument (if any) of the instruction which is used internally by
#     Python to fetch some constants or variables, manage the stack, jump to a
#     specific instruction, etc.
# (7) The human-friendly interpretation of the instruction argument


class DisassemblyTreeWidget(QTreeWidget):

    """Need only to generate sigEscapePressed signal"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)

        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setSortingEnabled(False)
        self.setItemDelegate(NoOutlineHeightDelegate(4))
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setExpandsOnDoubleClick(False)

        headerLabels = ["Line", "Jump", "Address", "Instruction",
                        "Argument", "Argument interpretation"]
        self.setHeaderLabels(headerLabels)

        headerItem = self.headerItem()
        headerItem.setToolTip(
            0, "The corresponding line number in the source code")
        headerItem.setToolTip(
            1, "A possible JUMP from an earlier instruction to this one")
        headerItem.setToolTip(
            2, "The address in the bytecode which corresponds to "
            "the byte index")
        headerItem.setToolTip(
            3, "The instruction name (also called opname)")
        headerItem.setToolTip(
            4, "The argument (if any) of the instruction which is used "
            "internally by Python to fetch some constants or variables, "
            "manage the stack, jump to a specific instruction, etc.")
        headerItem.setToolTip(
            5, "The human-friendly interpretation of the instruction argument")

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            self.sigEscapePressed.emit()
            event.accept()
        else:
            QTreeWidget.keyPressEvent(self, event)


class DisassemblyView(QWidget):

    sigGotoLine = pyqtSignal(int, int)
    sigEscapePressed = pyqtSignal()

    def __init__(self, navBar, parent):
        QWidget.__init__(self, parent)
        self.__navBar = navBar

        self.__table = DisassemblyTreeWidget(self)
        self.__table.sigEscapePressed.connect(self.__onEsc)
        self.__table.itemActivated.connect(self.__activated)
        self.__table.itemSelectionChanged.connect(self.__selectionChanged)

        self.__summary = HeaderLabel(parent=self)
        self.__summary.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Maximum)
        self.__summary.setMinimumWidth(10)
        self.__summary.setVisible(False)

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(self.__summary)
        vLayout.addWidget(self.__table)

        self.setLayout(vLayout)

    def serializeScrollAndSelection(self):
        """Memorizes the selection and expanded items"""
        # Scroll
        self.__hScroll = self.__table.horizontalScrollBar().value()
        self.__vScroll = self.__table.verticalScrollBar().value()

        # Collapsed
        self.__collapsed = []
        for index in range(self.__table.topLevelItemCount()):
            item = self.__table.topLevelItem(index)
            if not item.isExpanded():
                name = item.text(0)
                if '(' in name:
                    name = name.split('(')[0].strip()
                self.__collapsed.append(name)

        # Selection
        # - top level item
        # - non-top empty
        # - non-top something
        selected = self.__table.selectedItems()
        if len(selected) != 1:
            self.__selectedParent =None
            self.__selected = None
            self.__selectedIndex = None
        else:
            selected = selected[0]
            self.__selectedParent = selected.parent()
            if self.__selectedParent is None:
                # Top level selected
                self.__selected = selected.text(0)
                if '(' in self.__selected:
                    self.__selected = self.__selected.split('(')[0].strip()
                self.__selectedIndex = None
            else:
                # Non-top level
                self.__selectedIndex = self.__selectedParent.indexOfChild(
                    selected)
                self.__selectedParent = self.__selectedParent.text(0)
                if '(' in self.__selectedParent:
                    self.__selectedParent = self.__selectedParent.split('(')[0].strip()
                self.__selected = (selected.text(0), selected.text(1),
                                   selected.text(2), selected.text(3),
                                   selected.text(4), selected.text(5))

    def restoreScrollAndSelection(self):
        """Restores the selection and scroll position"""
        # Selection
        if (self.__selectedParent is not None or self.__selected is not None or
            self.__selectedIndex is not None):
            # Need to restore the selection
            if self.__selectedParent is None:
                # Top level was selected
                topItem = self.__findTopLevel(self.__selected)
                if topItem is not None:
                    topItem.setSelected(True)
            else:
                # Non-top item was selected
                topItem = self.__findTopLevel(self.__selectedParent)
                if topItem is not None:
                    maxIndex = topItem.childCount() - 1
                    if self.__selectedIndex <= maxIndex:
                        item = topItem.child(self.__selectedIndex)
                        if (item.text(0) == self.__selected[0] and
                            item.text(1) == self.__selected[1] and
                            item.text(2) == self.__selected[2] and
                            item.text(3) == self.__selected[3] and
                            item.text(4) == self.__selected[4] and
                            item.text(5) == self.__selected[5]):
                            item.setSelected(True)

        # Collapsed
        for index in range(self.__table.topLevelItemCount()):
            item = self.__table.topLevelItem(index)
            title = item.text(0)
            if '(' in title:
                title = title.split('(')[0].strip()
            if title in self.__collapsed:
                item.setExpanded(False)

        # Scroll
        self.__table.horizontalScrollBar().setValue(self.__hScroll)
        self.__table.verticalScrollBar().setValue(self.__vScroll)

    def __findTopLevel(self, name):
        """Provides a reference to the top level item if found"""
        for index in range(self.__table.topLevelItemCount()):
            item = self.__table.topLevelItem(index)
            title = item.text(0)
            if title == name:
                return item
            if title.startswith(name + ' ('):
                return item
        return None

    def populateDisassembly(self, source, encoding, filename):
        """Populates the disassembly tree"""
        self.__navBar.clearWarnings()
        self.serializeScrollAndSelection()
        try:
            optLevel = Settings()['disasmLevel']
            if source is None:
                props, disassembly = getFileDisassembled(
                    filename, optLevel, stringify=False)
            else:
                props, disassembly = getBufferDisassembled(
                    source, encoding, filename, optLevel, stringify=False)

            self.__table.clear()

            self.__setupLabel(props)
            self.__populate(disassembly)

            self.__table.header().resizeSections(QHeaderView.ResizeToContents)
            self.__navBar.updateInfoIcon(self.__navBar.STATE_OK_UTD)

            self. restoreScrollAndSelection()
        except Exception as exc:
            self.__navBar.updateInfoIcon(self.__navBar.STATE_BROKEN_UTD)
            self.__navBar.setErrors('Disassembling error:\n' + str(exc))

    def __setupLabel(self, props):
        """Updates the property label"""
        txt = ''
        for item in props:
            if txt:
                txt += '<br/>'
            txt += '<b>' + item[0] + ':</b> ' + item[1]
        self.__summary.setText(txt)
        self.__summary.setToolTip(txt)
        self.__summary.setVisible(True)

    def __populate(self, disassembly):
        """Populates disassembly"""
        currentTopLevel = None
        emptyCount = 0
        for line in disassembly.splitlines():
            if line.lower().startswith('disassembly of'):
                line = line.strip()
                emptyCount = 0

                # Two options:
                # Disassembly of <code object optToString at 0x7f63b7bf9920, file "...", line 45>:
                # Disassembly of optToString:

                if line.endswith(':'):
                    line = line[:-1]
                if '<' in line and '>' in line:
                    # First option
                    begin = line.find('code object ') + len('code object ')
                    end = line.find(' at 0x')
                    name = line[begin:end]
                    begin = line.find(', line ') + len(', line ')
                    lineNo = line[begin:-1]
                    currentTopLevel = QTreeWidgetItem([name + ' (' + lineNo + ')'])
                else:
                    # Second option
                    currentTopLevel = QTreeWidgetItem([line.split()[-1]])

                self.__table.addTopLevelItem(currentTopLevel)
                continue

            if currentTopLevel is None:
                continue

            if not line.strip():
                emptyCount += 1
                continue

            # Here: not an empty line and there is a parent
            # so parse and add as a child
            while emptyCount > 0:
                currentTopLevel.addChild(QTreeWidgetItem([]))
                emptyCount -= 1

            # Line numbers may occupy more than 3 positions so the first
            # part is taken with a good margin
            parts = line.split()
            if '>>' in parts:
                jump = '>>'
                parts.remove('>>')
            else:
                jump = ''

            if '-->' in parts:
                parts.remove('-->')

            if parts[0].isdigit() and parts[1].isdigit():
                # Line number and address
                lineNo = parts.pop(0)
            else:
                # Only adderess
                lineNo = ''
            address = parts.pop(0)
            instruction = parts.pop(0)

            if parts:
                argument = parts.pop(0)
            else:
                argument = ''
            if parts:
                interpretation = ' '.join(parts)
            else:
                interpretation = ''

            currentTopLevel.addChild(
                QTreeWidgetItem([lineNo, jump, address,
                                 instruction, argument, interpretation]))
            self.__table.expandItem(currentTopLevel)

    def __selectionChanged(self):
        """Handles an AST item selection"""
        selected = list(self.__table.selectedItems())
        self.__navBar.setSelectionLabel(len(selected), None)
        if selected:
            if len(selected) == 1:
                self.__navBar.setPath(self.__getPath(selected[0]))
                return
        self.__navBar.setPath('')

    @staticmethod
    def __getPath(node):
        if node.parent() is None:
            return node.text(0)
        instruction = node.text(3)
        if not instruction:
            instruction = '?'
        return node.parent().text(0) + u' \u2192 ' + instruction

    def __activated(self, item, _):
        """Handles the double click (or Enter) on an AST item"""
        if item.parent() is None:
            # Top level item
            title = item.text(0)
            if '(' in title:
                lineNo = title.split('(')[1]
                lineNo = lineNo.split(')')[0]
                if lineNo.isdigit():
                    self.sigGotoLine.emit(int(lineNo), 1)
                    return
            # Search in the children
            for index in range(item.childCount()):
                lineNo = item.child(index).text(0)
                if lineNo.isdigit():
                    self.sigGotoLine.emit(int(lineNo), 1)
                    return
            return

        parent = item.parent()
        itemIndex = parent.indexOfChild(item)
        for index in range(itemIndex, -1, -1):
            lineNo = parent.child(index).text(0)
            if lineNo.isdigit():
                self.sigGotoLine.emit(int(lineNo), 1)
                return

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

