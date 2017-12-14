# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Various routines used in other places"""

from ui.qt import QPainterPath, QColor


def getBorderColor(color):
    """Creates a darker version of the color"""
    red = color.red()
    green = color.green()
    blue = color.blue()

    delta = 60
    if isDark(red, green, blue):
        # Need lighter color
        return QColor(min(red + delta, 255),
                      min(green + delta, 255),
                      min(blue + delta, 255), color.alpha())
    # Need darker color
    return QColor(max(red - delta, 0),
                  max(green - delta, 0),
                  max(blue - delta, 0), color.alpha())


def isDark(red, green, blue):
    """True if the color is dark"""
    yiq = ((red * 299) + (green * 587) + (blue * 114)) / 1000
    return yiq < 128


def distance(val, begin, end):
    """Provides a distance between the absPos and an item"""
    if val >= begin and val <= end:
        return 0
    return min(abs(val - begin), abs(val - end))


def getCommentBoxPath(settings, baseX, baseY, width, height,
                      enforceHidden=False):
    """Provides the comomment box path"""
    if settings.hidecomments or enforceHidden:
        return getHiddenCommentPath(baseX + settings.hCellPadding,
                                    baseY + settings.vCellPadding,
                                    width - 2 * settings.hCellPadding,
                                    height - 2 * settings.vCellPadding)
    return getNoCellCommentBoxPath(baseX + settings.hCellPadding,
                                   baseY + settings.vCellPadding,
                                   width - 2 * settings.hCellPadding,
                                   height - 2 * settings.vCellPadding,
                                   settings.commentCorner)


def getNoCellCommentBoxPath(x, y, width, height, corner):
    """Provides the path for exactly specified rectangle"""
    path = QPainterPath()
    path.moveTo(x, y)
    path.lineTo(x + width - corner, y)
    path.lineTo(x + width, y + corner)
    path.lineTo(x + width, y + height)
    path.lineTo(x, y + height)
    path.lineTo(x, y)

    # -1 is to avoid sharp corners of the lines
    path.moveTo(x + width - corner, y + 1)
    path.lineTo(x + width - corner, y + corner)
    path.lineTo(x + width - 1, y + corner)
    return path


def getHiddenCommentPath(x, y, width, height):
    """Provides the path for the hidden comment"""
    path = QPainterPath()
    path.moveTo(x, y)
    path.addRoundedRect(x, y, width, height, 3, 3)
    return path
