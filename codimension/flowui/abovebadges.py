# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2020  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Various routines used in relation to above badges"""


class AboveBadgesDivider:

    """Divides the left hand side and the right hand side"""

    def __init__(self):
        self.width = 0


class AboveBadgesSpacer:

    """Provides a spacing between the badges"""

    def __init__(self, width):
        self.width = width


class AboveBadges:

    """Wrapper for the above badges container"""

    def __init__(self):
        self.__badges = []
        self.__normalized = False
        self.__height = None
        self.__width = None
        self.count = 0      # Badges count (not separators)

    @staticmethod
    def isBadge(badge):
        """True if it is a badge"""
        if isinstance(badge, AboveBadgesDivider):
            return False
        if isinstance(badge, AboveBadgesSpacer):
            return False
        return True

    def hasAny(self):
        """True if there are top badges"""
        for badge in self.__badges:
            if self.isBadge(badge):
                return True
        return False

    def append(self, item):
        """Appends an item to the badges list"""
        self.__badges.append(item)
        if self.isBadge(item):
            self.count += 1

    def __getitem__(self, key):
        """Provides certain badge"""
        return self.__badges[key]

    def __normalizeHeight(self):
        """Makes all the badges of the same height (max)"""
        if not self.__normalized:
            maxHeight = -1
            for badge in self.__badges:
                if self.isBadge(badge):
                    maxHeight = max(maxHeight, badge.height)
            for badge in self.__badges:
                if self.isBadge(badge):
                    badge.height = maxHeight
                    # make sure the badge is at least square
                    if badge.width < badge.height:
                        badge.width = badge.height
            self.__normalized = True

    @property
    def height(self):
        """Provides the normalized height of the badges row"""
        if self.__height is not None:
            return self.__height

        self.__normalizeHeight()
        self.__height = 0
        for badge in self.__badges:
            if self.isBadge(badge):
                self.__height = badge.height
                break
        return self.__height

    @property
    def width(self):
        """Provides the min width of the badges row"""
        if self.__width is not None:
            return self.__width

        self.__normalizeHeight()
        self.__width = 0
        for badge in self.__badges:
            self.__width += badge.width
        return self.__width

    def draw(self, scene, settings, baseX, baseY, minWidth):
        """Draws the badges row"""
        if self.count == 0:
            return

        self.__normalizeHeight()

        xPos = baseX + settings.hCellPadding
        yPos = baseY + settings.vCellPadding

        # Before a divider part
        dividerFound = False
        for badge in self.__badges:
            if isinstance(badge, AboveBadgesDivider):
                dividerFound = True
                break
            if not isinstance(badge, AboveBadgesSpacer):
                badge.moveTo(xPos, yPos)
                scene.addItem(badge)
                badge.draw(scene, xPos, yPos)
            xPos += badge.width

        if dividerFound:
            # After divider part
            xPos = baseX + minWidth - settings.hCellPadding
            for badge in reversed(self.__badges):
                if isinstance(badge, AboveBadgesDivider):
                    break
                xPos -= badge.width
                if not isinstance(badge, AboveBadgesSpacer):
                    badge.moveTo(xPos, yPos)
                    scene.addItem(badge)
                    badge.draw(scene, xPos, yPos)

    def raizeAllButFirst(self):
        """Sets the Z value for all badges except the first one"""
        for index, badge in enumerate(self.__badges):
            if index != 0:
                if self.isBadge(badge):
                    badge.setZValue(1)

