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

# pylint: disable=C0305

from ui.qt import QPainterPath
from .cml import CMLdoc


def distance(val, begin, end):
    """Provides a distance between the absPos and an item"""
    if val >= begin and val <= end:
        return 0
    return min(abs(val - begin), abs(val - end))


def getCommentBoxPath(settings, baseX, baseY, width, height):
    """Provides the comment box path"""
    return getNoCellCommentBoxPath(baseX + settings.hCellPadding,
                                   baseY + settings.vCellPadding,
                                   width - 2 * settings.hCellPadding,
                                   height - 2 * settings.vCellPadding,
                                   settings.commentCorner)


def getNoCellCommentBoxPath(xPos, yPos, width, height, corner):
    """Provides the path for exactly specified rectangle"""
    path = QPainterPath()
    path.moveTo(xPos, yPos)
    path.lineTo(xPos + width - corner, yPos)
    path.lineTo(xPos + width, yPos + corner)
    path.lineTo(xPos + width, yPos + height)
    path.lineTo(xPos, yPos + height)
    path.lineTo(xPos, yPos)

    # -1 is to avoid sharp corners of the lines
    path.moveTo(xPos + width - corner, yPos + 1)
    path.lineTo(xPos + width - corner, yPos + corner)
    path.lineTo(xPos + width - 1, yPos + corner)
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


def getDoclinkIconAndTooltip(cmlRef, hidden=False):
    """Provides the icon file name and a tooltip for a doc item"""
    if cmlRef.link is not None and cmlRef.anchor is not None:
        pixmap = 'docanchor.svg'
        tooltip = 'Jump to the documentation'
    elif cmlRef.link is not None:
        pixmap = 'doclink.svg'
        tooltip = 'Jump to the documentation'
    else:
        pixmap = 'anchor.svg'
        tooltip = 'Documentation anchor'

    if hidden:
        pixmap = 'hidden' + pixmap
        if cmlRef.title:
            tooltip = cmlRef.title
    return pixmap, tooltip

