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

from ui.qt import QPainterPath
from .cml import CMLdoc


def distance(val, begin, end):
    """Provides a distance between the absPos and an item"""
    if val >= begin and val <= end:
        return 0
    return min(abs(val - begin), abs(val - end))


def getCommentBoxPath(settings, baseX, baseY, width, height,
                      enforceHidden=False):
    """Provides the comment box path"""
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


def getCMLComment(cmlComments, code):
    """CML comment or None"""
    for cmlComment in cmlComments:
        if hasattr(cmlComment, 'CODE'):
            if cmlComment.CODE == code:
                return cmlComment
    return None


def getDocComment(cmlComments):
    """CML doc comment reference or None"""
    return getCMLComment(cmlComments, CMLdoc.CODE)

