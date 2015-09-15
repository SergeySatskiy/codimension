# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

" The settings used for rendering and drawing "


# The recommended way to use custom settings is to derive from
# CFlowSettings and change the required options in a new class __init__.
# Then to create an instance of the custom settings class and use it
# accordingly.


from PyQt4.QtGui import QColor, QFont, QFontMetrics


def buildFont( fontAsString ):
    " Converts a string into QFont object "
    fontAsString = fontAsString.strip()
    font = QFont()
    font.fromString( fontAsString )
    return font


class CFlowSettings:
    " Holds the control flow rendering and drawing settings "

    def __init__( self, paintDevice ):

        # Visibility of the virtual cells (dotted outline)
        self.debug = False
        self.__paintDevice = paintDevice

        self.monoFont = buildFont( "Ubuntu mono,12,-1,5,50,0,0,0,0,0" )
        self.monoFontMetrics = QFontMetrics( self.monoFont, paintDevice )
        self.badgeFont = buildFont( "Ubuntu mono,9,-1,5,50,0,0,0,0,0" )
        self.badgeFontMetrics = QFontMetrics( self.badgeFont, paintDevice )

        self.hCellPadding = 10      # in pixels (left and right)
        self.vCellPadding = 6       # in pixels (top and bottom)
        self.hTextPadding = 5       # in pixels (left and right)
        self.vTextPadding = 5       # in pixels (top and bottom)

        self.hHeaderPadding = 5     # Scope header (file, decor, loops etc) paddings
        self.vHeaderPadding = 5

        self.vSpacer = 10

        self.rectRadius = 6         # Rounded rectangles radius
        self.returnRectRadius = 16  # Rounded rectangles radius
        self.minWidth = 100
        self.ifWidth = 10           # One if wing width
        self.commentCorner = 6      # Top right comment corner
        self.hScopeSpacing = 2
        self.vScopeSpacing = 2

        self.lineWidth = 1          # used for connections and box edges
        self.lineColor = QColor( 16, 16, 16, 255 )

        # Code blocks and other statements
        self.boxBGColor = QColor( 250, 250, 250, 255 )
        self.boxFGColor = QColor( 0, 0, 0, 255 )

        # Badges
        self.badgeBGColor = QColor( 230, 230, 230, 255 )
        self.badgeFGColor = QColor( 0, 0, 0, 255 )
        self.badgeLineWidth = 1
        self.badgeLineColor = QColor( 0, 0, 0, 255 )

        # Labels
        self.labelBGColor = QColor( 230, 230, 230, 255 )
        self.labelFGColor = QColor( 0, 0, 0, 255 )
        self.labelLineWidth = 1
        self.labelLineColor = QColor( 0, 0, 0, 255 )

        # Comments: leading, side & independent
        self.commentBGColor = QColor( 255, 255, 153, 255 )
        self.commentFGColor = QColor( 0, 0, 0, 255 )
        self.commentLineColor = QColor( 102, 102, 61, 255 )
        self.commentLineWidth = 1
        self.mainLine = 50

        self.fileScopeBGColor = QColor( 255, 255, 230, 255 )
        self.funcScopeBGColor = QColor( 230, 230, 255, 255 )
        self.decorScopeBGColor = QColor( 230, 255, 255, 255 )
        self.classScopeBGColor = QColor( 230, 255, 230, 255 )
        self.forScopeBGColor = QColor( 187, 222, 251, 255 )
        self.whileScopeBGColor = QColor( 187, 222, 251, 255 )
        self.elseScopeBGColor = QColor( 209, 196, 233, 255 )
        self.withScopeBGColor = QColor( 255, 255, 255, 255 )
        self.tryScopeBGColor = QColor( 255, 255, 255, 255 )
        self.exceptScopeBGColor = QColor( 255, 255, 255, 255 )
        self.finallyScopeBGColor = QColor( 192, 192, 192, 255 )
        self.breakBGColor = QColor( 144, 202, 249, 255 )
        self.continueBGColor = QColor( 144, 202, 249, 255 )
        self.ifBGColor = QColor( 255, 229, 127, 255 )
        return

    def setMonoFont( self, font ):
        " Sets the mono font "
        self.monoFont = font
        self.monoFontMetrics = QFontMetrics( self.monoFont,
                                             self.__paintDevice )
        return

    def setBadgeFont( self, font ):
        " Sets the badge font "
        self.badgeFont = font
        self.badgeFontMetrics = QFontMetrics( self.badgeFont,
                                              self.__paintDevice )
        return

def getDefaultCflowSettings( paintDevice ):
    return CFlowSettings( paintDevice )

