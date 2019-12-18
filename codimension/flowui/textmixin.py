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

from html import escape
from .cml import CMLVersion, CMLrt
from .cellelement import CellElement


class TextMixin:

    """Text mixin to support text displayed by the item and a tooltip"""

    def __init__(self):
        self.text = None            # Text to display; it may be:
                                    # - text from the code
                                    # - replacement text if so
                                    # - nothing if suppressed
        self.textRect = None

    @staticmethod
    def getReplacementText(ref):
        """Provides the replacement text if so from the CML comment"""
        try:
            rtComment = CMLVersion.find(ref.leadingCMLComments, CMLrt)
            if rtComment:
                return rtComment.getText()
        except AttributeError:
            # The leadingCMLComments attribute may be not available
            return None
        return None

    @staticmethod
    def __getDisplayText(graphicsItem, customText):
        """Provides the display text"""
        if customText is None:
            return graphicsItem.ref.getDisplayValue()
        return customText

    @staticmethod
    def __shouldHideText(graphicsItem):
        """True if the text should be hidden"""
        settings = graphicsItem.canvas.settings
        if settings.hidecomments:
            if graphicsItem.isComment() or graphicsItem.isCMLDoc():
                return True

        if settings.noContent:
            if graphicsItem.kind not in [CellElement.CLASS_SCOPE,
                                         CellElement.FUNC_SCOPE]:
                return True

        return False

    def setupText(self, graphicsItem, customText=None, customReplacement=None):
        """Prepares the text and its rectangle; sets tooltip if needed"""
        if customReplacement is None:
            replacement = TextMixin.getReplacementText(graphicsItem.ref)
        else:
            replacement = customReplacement

        if TextMixin.__shouldHideText(graphicsItem):
            # The content needs to be suppressed
            tooltip = '<pre>' + \
                      TextMixin.__getDisplayText(graphicsItem, customText) + \
                      '</pre>'

            if replacement:
                tooltip += '<hr>Replacement text:<pre>' + \
                    escape(replacement) + '</pre>'
            graphicsItem.setToolTip(tooltip)

            self.text = ''
        else:
            # No suppression; something needs to be shown
            self.text = TextMixin.__getDisplayText(graphicsItem, customText)
            if replacement:
                graphicsItem.setToolTip('<pre>' + escape(self.text) + '</pre>')
                self.text = replacement
        self.textRect = graphicsItem.getBoundingRect(self.text)

