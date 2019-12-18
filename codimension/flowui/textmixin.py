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

"""Text mixin for the graphics items"""

# pylint: disable=C0305

from .cml import CMLVersion, CMLrt


class TextMixin:

    """Text mixin to support text displayed by the item and a tooltip"""

    def __init__(self, ref):
        self.text = None
        self.replaceText = None
        self.textRect = None
        self.tooltip = None

        self.__retrieveReplacementText(ref)

    def __retrieveReplacementText(self, ref):
        """Provides the replacement text if so from the CML comment"""
        try:
            rt = CMLVersion.find(self.ref.leadingCMLComments, CMLrt)
            if rt:
                self.replaceText = rt.getText()
        except AttributeError:
            pass

    def setupText(self, graphicsItem, customText=None):
        """Prepares the text and its rectangle; sets tooltip if needed"""
        self.text = customText

