# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2019  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Color mixin for the graphics items"""

from .cml import CMLVersion, CMLcc


class ColorMixin:

    """Color mixin to support bg, fg and border color"""

    def __init__(self, ref, defaultBG, defaultFG, defaultBorder,
                 isDocstring=False):
        self.bgColor = defaultBG
        self.fgColor = defaultFG
        self.borderColor = defaultBorder
        self.__getCustomColors(ref, isDocstring)

    def getColors(self):
        """Provides the item colors"""
        return self.bgColor, self.fgColor, self.borderColor

    def __getCustomColors(self, ref, isDocstring):
        """Provides the colors to be used for an item"""
        leadingCML = ref.leadingCMLComments
        if isDocstring:
            leadingCML = ref.docstring.leadingCMLComments

        # fg and bg are supported by all the items
        # (except comments)
        if leadingCML:
            colorSpec = CMLVersion.find(leadingCML, CMLcc)
            if colorSpec:
                if colorSpec.bgColor:
                    self.bgColor = colorSpec.bgColor
                if colorSpec.fgColor:
                    self.fgColor = colorSpec.fgColor

        # The border color is NOT supported by docstrings
        if ref.leadingCMLComments:
            colorSpec = CMLVersion.find(ref.leadingCMLComments, CMLcc)
            if colorSpec:
                if colorSpec.border:
                    self.borderColor = colorSpec.border

