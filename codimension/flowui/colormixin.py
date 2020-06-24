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

# pylint: disable=C0305

from .cml import CMLVersion, CMLcc

# There are a few options of how the colors could be specified:
# - the item may have a leading CML cc comment
# - a scope item has a docstring which in turn has a leading CML cc comment
#   a docstring color spec does not support a border color because the scope
#   border is used for the dividing line
# - group items have the color spec in their CML ref
# - doc items have the color spec in their CML ref

class ColorMixin:

    """Color mixin to support bg, fg and border color"""

    def __init__(self, ref, defaultBG, defaultFG, defaultBorder,
                 isDocstring=False, colorSpec=None):
        self.bgColor = defaultBG
        self.fgColor = defaultFG
        self.borderColor = defaultBorder

        if colorSpec is not None:
            # the case for groups and docs
            self.__getFromColorSpec(colorSpec)
        elif isDocstring:
            # special case for docstrings
            self.__getFromDocstring(ref)
        else:
            # all the other items
            self.__getCustomColors(ref)

    def getColors(self):
        """Provides the item colors"""
        return self.bgColor, self.fgColor, self.borderColor

    @staticmethod
    def isDark(red, green, blue):
        """True if the color is dark"""
        yiq = ((red * 299) + (green * 587) + (blue * 114)) / 1000
        return yiq < 128

    def __getFromColorSpec(self, colorSpec):
        """Updates the colors from the given colorspec"""
        if colorSpec.bgColor:
            self.bgColor = colorSpec.bgColor
        if colorSpec.fgColor:
            self.fgColor = colorSpec.fgColor
        if colorSpec.border:
            self.borderColor = colorSpec.border

    def __getFromDocstring(self, ref):
        """Updates the colors for the docstrings"""
        leadingCML = ref.docstring.leadingCMLComments
        if leadingCML:
            colorSpec = CMLVersion.find(leadingCML, CMLcc)
            if colorSpec:
                # NOTE: no border color support for the docstrings full
                #       text in the scope however used for a hidden (badge)
                #       kind of docstring
                self.__getFromColorSpec(colorSpec)

    def __getCustomColors(self, ref):
        """Provides the colors to be used for an item"""
        leadingCML = ref.leadingCMLComments
        if leadingCML:
            colorSpec = CMLVersion.find(leadingCML, CMLcc)
            if colorSpec:
                self.__getFromColorSpec(colorSpec)

