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
        self.debug = True
        self.__paintDevice = paintDevice

        self.monoFont = buildFont( "Ubuntu mono,12,-1,5,50,0,0,0,0,0" )
        self.otherFont = buildFont( "Times,12,-1,5,50,0,0,0,0,0" )

        self.monoFontMetrics = QFontMetrics( self.monoFont, paintDevice )
        self.otherFontMetrics = QFontMetrics( self.otherFont, paintDevice )

        self.hCellPadding = 15      # in pixels (left and right)
        self.vCellPadding = 15      # in pixels (top and bottom)
        self.hTextPadding = 5       # in pixels (left and right)
        self.vTextPadding = 5       # in pixels (top and bottom)

        self.hHeaderPadding = 5     # Scope header (file, decor, loops etc) paddings
        self.vHeaderPadding = 5

        self.vSpacer = 10

        self.rectRadius = 10        # Rounded rectangles radius
        self.arrowLength = 3        # Length of an arrow
        self.arrowWidth = 2         # One wing width

        self.lineWidth = 2          # used for connections and box edges
        self.lineColor = QColor( 0, 0, 0, 255 )

        # Code blocks and other statements
        self.boxBGColor = QColor( 216, 216, 207, 255 )
        self.boxFGColor = QColor( 0, 0, 0, 255 )

        # Comments: leading, side & independent
        self.commentBGColor = QColor( 216, 216, 207, 255 )
        self.commentFGColor = QColor( 90, 90, 88, 255 )
        self.commentLineColor = QColor( 255, 0, 0, 255 )
        self.commentLineWidth = 1

        self.fileScopeBGColor = QColor( 255, 255, 230, 255 )
        return

    def setMonoFont( self, font ):
        " Sets the mono font "
        self.monoFont = font
        self.monoFontMetrics = QFontMetrics( self.monoFont,
                                             self.__paintDevice )
        return

    def setOtherFont( self, font ):
        " Sets the non-mono font "
        self.otherFont = font
        self.otherFontMetrics = QFontMetrics( self.otherFont,
                                              self.__paintDevice )
        return


def getDefaultCflowSettings( paintDevice ):
    return CFlowSettings( paintDevice )

