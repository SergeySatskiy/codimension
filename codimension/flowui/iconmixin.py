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

"""Icon mixin for the graphics items"""

# pylint: disable=C0305

from .auxitems import SVGItem

class IconMixin:

    """Icon (svg) mixin for items like import"""

    def __init__(self, canvas, fName, tooltip=None):
        if fName is None:
            # Needed for the scope items. Not all kinds of them would need
            # an icon for the comment
            return

        self.__iconHeight = None
        self.iconItem = SVGItem(canvas, fName, self)
        self.iconItem.setIconHeight(self.__getIconHeight(canvas.settings))
        if tooltip:
            self.iconItem.setToolTip(tooltip)

    def __getIconHeight(self, settings):
        """Provides the icon height"""
        if self.__iconHeight is None:
            self.__iconHeight = \
                settings.monoFontMetrics.boundingRect('W').height() * 0.8
        return self.__iconHeight

