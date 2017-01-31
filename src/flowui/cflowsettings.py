# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""The settings used for rendering and drawing"""

# The recommended way to use custom settings is to derive from
# CFlowSettings and change the required options in a new class __init__.
# Then to create an instance of the custom settings class and use it
# accordingly.


from ui.qt import QColor, QFont, QFontMetrics
from utils.globals import GlobalData


class CFlowSettings:

    """Holds the control flow rendering and drawing settings"""

    def __init__(self, paintDevice, params):
        # Visibility of the virtual cells (dotted outline)
        self.__paintDevice = paintDevice

        for key, value in params.items():
            setattr(self, key, value)

        self.monoFontMetrics = QFontMetrics(params['monoFont'], paintDevice)
        self.badgeFontMetrics = QFontMetrics(params['badgeFont'], paintDevice)

    def setMonoFont(self, font):
        """Sets the mono font"""
        self.monoFont = font
        self.monoFontMetrics = QFontMetrics(self.monoFont,
                                            self.__paintDevice)

    def setBadgeFont(self, font):
        """Sets the badge font"""
        self.badgeFont = font
        self.badgeFontMetrics = QFontMetrics(self.badgeFont,
                                             self.__paintDevice)


def getCflowSettings(paintDevice):
    return CFlowSettings(paintDevice, GlobalData().skin.cflowSettings)
