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

# pylint: disable=C0305
# pylint: disable=R0902
# pylint: disable=R0903

# The recommended way to use custom settings is to derive from
# CFlowSettings and change the required options in a new class __init__.
# Then to create an instance of the custom settings class and use it
# accordingly.


from math import ceil
from ui.qt import QFontMetrics
from utils.globals import GlobalData
from utils.colorfont import getZoomedCFMonoFont, getZoomedCFBadgeFont
from utils.settings import Settings

NEED_NORMALIZE = ('ifWidth', 'commentCorner', 'hCellPadding',
                  'vCellPadding', 'hTextPadding', 'vTextPadding',
                  'hHeaderPadding', 'vHeaderPadding', 'vSpacer',
                  'mainLine', 'decorMainLine', 'minWidth', 'returnRectRadius',
                  'hDocLinkPadding', 'vDocLinkPadding', 'hHiddenExceptPadding',
                  'vHiddenExceptPadding', 'vHiddenCommentPadding',
                  'hHiddenCommentPadding', 'badgeHSpacing', 'badgeVSpacing',
                  'scopeRectRadius', 'badgeRadius',
                  'badgePixmapSpacing', 'badgeToBadgeHSpacing',
                  'badgeToScopeVPadding', 'badgeGroupSpacing',
                  'openGroupVSpacer', 'openGroupHSpacer',
                  'collapsedGroupXShift', 'collapsedGroupYShift',
                  'emptyGroupXShift', 'emptyGroupYShift', 'breakHPadding',
                  'breakVPadding', 'breakRectRadius', 'continueHPadding',
                  'continueVPadding', 'continueRectRadius',
                  'hiddenCommentRectRadius', 'hiddenExceptRectRadius',
                  'ifSideCommentVShift', 'decorRectRadius',
                  'loopHeaderPadding')

class CFlowSettings:

    """Holds the control flow rendering and drawing settings"""

    def __init__(self, paintDevice, params):
        self.__paintDevice = paintDevice
        self.__params = params

        # Used to generate each item unique sequential ID
        self.itemID = 0

        self.__noZoomFontMetrics = QFontMetrics(self.__params['cfMonoFont'],
                                                self.__paintDevice)
        self.coefficient = 1.0

        for key, value in params.items():
            setattr(self, key, value)

        # Some display related settings are coming from the IDE wide settings
        settings = Settings()
        setattr(self, 'hidedocstrings', settings['hidedocstrings'])
        setattr(self, 'hidecomments', settings['hidecomments'])
        setattr(self, 'hideexcepts', settings['hideexcepts'])
        setattr(self, 'hidedecors', settings['hidedecors'])

        # Dynamic settings for the smart zoom feature
        setattr(self, 'noContent', False)
        setattr(self, 'noComment', False)
        setattr(self, 'noDocstring', False)
        setattr(self, 'noBlock', False)
        setattr(self, 'noImport', False)
        setattr(self, 'noBreak', False)
        setattr(self, 'noContinue', False)
        setattr(self, 'noReturn', False)
        setattr(self, 'noRaise', False)
        setattr(self, 'noAssert', False)
        setattr(self, 'noSysExit', False)
        setattr(self, 'noDecor', False)
        setattr(self, 'noFor', False)
        setattr(self, 'noWhile', False)
        setattr(self, 'noWith', False)
        setattr(self, 'noTry', False)
        setattr(self, 'noIf', False)
        setattr(self, 'noGroup', False)

        self.onFlowZoomChanged()

    def __getNormalized(self, value):
        """Normalize a defalt value to the current zoom"""
        return ceil(float(self.__params[value]) * self.coefficient)

    def onFlowZoomChanged(self):
        """Triggered when a flow zoom is changed"""
        self.monoFont = getZoomedCFMonoFont()
        self.monoFontMetrics = QFontMetrics(self.monoFont,
                                            self.__paintDevice)
        self.badgeFont = getZoomedCFBadgeFont()
        self.badgeFontMetrics = QFontMetrics(self.badgeFont,
                                             self.__paintDevice)

        # Recalculate various paddings. If they are not recalculated then the
        # badges may overlap the text and even boxes
        newHeight = self.monoFontMetrics.boundingRect('W').height()
        noZoomHeight = self.__noZoomFontMetrics.boundingRect('W').height()
        self.coefficient = float(newHeight) / float(noZoomHeight)

        for paramName in NEED_NORMALIZE:
            setattr(self, paramName, self.__getNormalized(paramName))


def getCflowSettings(paintDevice):
    """Provides the control flow settings"""
    return CFlowSettings(paintDevice, GlobalData().skin.cflowSettings)

