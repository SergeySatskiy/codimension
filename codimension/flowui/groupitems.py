# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Virtual canvas items to handle groups (opened/collapsed)"""


from .items import CellElement


class EmptyGroup(CellElement):

    """Represents an empty group"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.EMPTY_GROUP

    def render(self):
        """Renders the cell"""

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""


class OpenedGroupBegin(CellElement):

    """Represents beginning af a group which can be collapsed"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.OPENED_GROUP_BEGIN

    def render(self):
        """Renders the cell"""
        self.width = 0
        self.height = self.canvas.settings.vSpacer
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        # There is no need to draw anything. The cell just reserves some
        # vertical space for better appearance
        self.baseX = baseX
        self.baseY = baseY


class OpenedGroupEnd(CellElement):

    """Represents the end af a group which can be collapsed"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.OPENED_GROUP_END

    def render(self):
        """Renders the cell"""
        self.width = 0
        self.height = self.canvas.settings.vSpacer
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
        # There is no need to draw anything. The cell just reserves some
        # vertical space for better appearance
        self.baseX = baseX
        self.baseY = baseY


class CollapsedGroup(CellElement):

    """Represents a collupsed group"""

    def __init__(self, ref, canvas, x, y):
        CellElement.__init__(self, ref, canvas, x, y)
        self.kind = CellElement.COLLAPSED_GROUP

    def render(self):
        """Renders the cell"""

    def draw(self, scene, baseX, baseY):
        """Draws the cell"""
