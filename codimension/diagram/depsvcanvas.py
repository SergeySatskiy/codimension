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

from .auxitems import VSpacerCell

class DepsVirtualCanvas:

    """Holds the dependencies diagram representation"""

    def __init__(self, settings, xAddr, yAddr, parent):
        self.kind = CellElement.VCANVAS
        self.cells = []
        self.canvas = parent

        self.settings = settings
        self.addr = [xAddr, yAddr]

        self.isNoScope = False

        self.width = 0
        self.height = 0
        self.minWidth = 0
        self.minHeight = 0

        # Painting support
        self.baseX = 0
        self.baseY = 0
        self.scopeRectangle = None

    def __allocateAndSet(self, row, column, what):
        """Allocates a cell and sets it to the given value"""
        self.__allocateCell(row, column)
        self.cells[row][column] = what

    def layoutTopLevel(self, fileName, depClasses):
        """Lays out the top level dependency diagram"""
        self.isNoScope = True
        vacantRow = 0

        # Avoid glueing to the top view edge
        self.__allocateAndSet(vacantRow, 1,
                              VSpacerCell(None, self, 1, vacantRow))
        vacantRow += 1

        

