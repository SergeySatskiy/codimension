# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2020 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Dependency diagram virtual canvas"""

from ui.qt import QColor, QPen, QBrush
from flowui.cellelement import CellElement
from flowui.auxitems import VSpacerCell, Rectangle, VacantCell
from flowui.scopeitems import ScopeHSideEdge
from .depsitems import SelfModule

class DepsVirtualCanvas:

    """Holds the dependencies diagram representation"""

    def __init__(self, settings, xAddr, yAddr, parent):
        self.kind = CellElement.VCANVAS
        self.cells = []
        self.canvas = parent

        self.settings = settings
        self.addr = [xAddr, yAddr]

        # Layout support
        self.__currentCF = None
        self.__currentScopeClass = None
        self.isNoScope = False

        self.width = 0
        self.height = 0
        self.minWidth = 0
        self.minHeight = 0

        # Painting support
        self.baseX = 0
        self.baseY = 0
        self.scopeRectangle = None

    def __allocateCell(self, row, column, needScopeEdge=True):
        """Allocates a cell as Vacant if it is not available yet.

        Can only allocate bottom and right growing cells.
        """
        lastIndex = len(self.cells) - 1
        while lastIndex < row:
            self.cells.append([])
            lastIndex += 1
            if needScopeEdge:
                if self.__currentScopeClass:
                    self.cells[lastIndex].append(
                        ScopeHSideEdge(self.__currentCF, self, 0, lastIndex))
        lastIndex = len(self.cells[row]) - 1
        while lastIndex < column:
            self.cells[row].append(VacantCell(None, self, lastIndex, row))
            lastIndex += 1

    def __allocateAndSet(self, row, column, what):
        """Allocates a cell and sets it to the given value"""
        self.__allocateCell(row, column)
        self.cells[row][column] = what

    def hasScope(self):
        """True if it has a scope"""
        try:
            return self.cells[0][0].scopedItem()
        except:
            return False

    def layoutTopLevel(self, fileName, depClasses):
        """Lays out the top level dependency diagram"""
        self.isNoScope = True
        vacantRow = 0

        # Avoid glueing to the top view edge
        self.__allocateAndSet(vacantRow, 1,
                              VSpacerCell(None, self, 1, vacantRow))
        vacantRow += 1

        needConnector = depClasses['totalCount'] > 0
        self.__allocateAndSet(vacantRow, 1,
                              SelfModule(fileName, needConnector, self, 1, vacantRow))

    def render(self):
        """Preforms rendering for all the cells"""
        self.height = 0

        maxRowIndex = len(self.cells) - 1
        index = 0
        while index <= maxRowIndex:
            row = self.cells[index]
            maxHeight = 0
            for cell in row:
                _, height = cell.render()
                maxHeight = max(maxHeight, height)
                if not cell.scopedItem():
                    if cell.isComment() or cell.isCMLDoc():
                        cell.adjustWidth()
            for cell in row:
                cell.height = maxHeight
                if cell.kind == CellElement.VCANVAS:
                    if not cell.hasScope():
                        cell.adjustLastCellHeight(maxHeight)
            self.height += maxHeight
            index += 1

        self.width = 0
        for row in self.cells:
            totalWidth = 0
            for cell in row:
                totalWidth += cell.width
            self.width = max(self.width, totalWidth)

        if self.hasScope():
            # Right hand side vertical part
            self.width += self.settings.scopeRectRadius + self.settings.hCellPadding

        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the diagram on the real canvas"""
        self.baseX = baseX
        self.baseY = baseY
        currentY = baseY
        for row in self.cells:
            if not row:
                continue
            height = row[0].height
            currentX = baseX
            for cell in row:
                if self.settings.debug:
                    if cell.kind == CellElement.VCANVAS:
                        rect = Rectangle(self, currentX + 1, currentY + 1,
                                         cell.width - 2, cell.height -2)
                        rect.pen = QPen(QColor(255, 0, 0, 255))
                        rect.brush = QBrush(QColor(255, 0, 0, 127))
                        rect.setToolTip('Canvas ' + str(cell.width) + 'x' +
                                        str(cell.height))
                        scene.addItem(rect)
                    else:
                        rect = Rectangle(self, currentX, currentY,
                                         cell.width, cell.height)
                        rect.pen = QPen(QColor(0, 255, 0, 255))
                        rect.brush = QBrush(QColor(0, 255, 0, 127))
                        rect.setToolTip('Item ' + str(cell) +
                                        ' ' + str(cell.kind))
                        scene.addItem(rect)
                cell.draw(scene, currentX, currentY)
                currentX += cell.width
            currentY += height

    def cleanup(self):
        """Cleans up the references etc"""
        self.canvas = None
        self.settings = None
        self.addr = None
        self.__currentCF = None
        self.scopeRectangle = None

        for row in self.cells:
            if row:
                for cell in row:
                    if isinstance(cell, DepsVirtualCanvas):
                        cell.cleanup()

