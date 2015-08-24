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

" Various items used to represent a control flow on a virtual canvas "

from sys import maxint
from math import sqrt
from PyQt4.QtCore import Qt, QPointF
from PyQt4.QtGui import ( QPen, QBrush, QGraphicsRectItem, QGraphicsPathItem,
                          QPainterPath, QPainter, QColor )
from PyQt4.QtSvg import QGraphicsSvgItem
import os.path


def getDarkerColor( color ):
    r = color.red() - 40
    g = color.green() - 40
    b = color.blue() - 40
    return QColor( max( r, 0 ), max( g, 0 ), max( b, 0 ), color.alpha() )



class SVGItem( QGraphicsSvgItem ):
    " Wrapper for an SVG items on the control flow "

    def __init__( self, fName ):
        QGraphicsSvgItem.__init__( self, self.__getPath( fName ) )
        self.__scale = 0
        return

    def __getPath( self, fName ):
        " Tries to resolve the given file name "
        try:
            from utils.pixmapcache import PixmapCache
            path = PixmapCache().getSearchPath() + fName
            if os.path.exists( path ):
                return path
        except:
            pass

        if os.path.exists( fName ):
            return fName
        return ""

    def setHeight( self, height ):
        " Scales the svg item to the required height "
        rectHeight = float( self.boundingRect().height() )
        if rectHeight != 0.0:
            self.__scale = float( height ) / rectHeight
            self.setScale( self.__scale )
        return

    def setWidth( self, width ):
        " Scales the svg item to the required width "
        rectWidth = float( self.boundingRect().width() )
        if rectWidth != 0.0:
            self.__scale = float( width ) / rectWidth
            self.setScale( self.__scale )
        return

    def height( self ):
        return self.boundingRect().height() * self.__scale

    def width( self ):
        return self.boundingRect().width() * self.__scale


class CellElement:
    " Base class for all the elements which could be found on the canvas "

    UNKNOWN = -1

    VCANVAS = 0

    VACANT = 1
    H_SPACER = 2
    V_SPACER = 3

    NO_SCOPE = 99
    FILE_SCOPE = 100
    FUNC_SCOPE = 101
    CLASS_SCOPE = 102
    FOR_SCOPE = 103
    WHILE_SCOPE = 104
    TRY_SCOPE = 105
    WITH_SCOPE = 106
    DECOR_SCOPE = 107
    ELSE_SCOPE = 108
    EXCEPT_SCOPE = 109
    FINALLY_SCOPE = 110

    CODE_BLOCK = 200
    BREAK = 201
    CONTINUE = 202
    RETURN = 203
    RAISE = 204
    ASSERT = 205
    SYSEXIT = 206
    IMPORT = 207
    IF = 208
    LEADING_COMMENT = 209
    INDEPENDENT_COMMENT = 210
    SIDE_COMMENT = 211

    CONNECTOR = 300

    def __init__( self, ref, canvas, x, y ):
        self.kind = self.UNKNOWN
        self.ref = ref              # reference to the control flow object
        self.addr = [ x, y ]        # indexes in the current canvas
        self.canvas = canvas        # reference to the canvas

        self.tailComment = False

        # Filled when rendering is called
        self.width = None
        self.height = None
        self.minWidth = None
        self.minHeight = None

        # Filled when draw is called
        self.baseX = None
        self.baseY = None

        # Badge painting support
        self._badgeRect = None
        self._badgeText = None
        return

    def __str__( self ):
        return kindToString( self.kind ) + \
               "[" + str( self.width ) + ":" + str( self.height ) + "]"

    def render( self ):
        " Renders the graphics considering settings "
        raise Exception( "render() is not implemented for " +
                         kindToString( self.kind ) )

    def draw( self, scene, baseX, baseY ):
        """
        Draws the element on the real canvas
        in the given rect respecting settings
        """
        raise Exception( "draw() is not implemented for " +
                         kindToString( self.kind ) )

    def getBoundingRect( self, text ):
        " Provides the bounding rectangle for a monospaced font "
        return self.canvas.settings.monoFontMetrics.boundingRect(
                                        0, 0,  maxint, maxint, 0, text )

    def getBadgeBoundingRect( self, text ):
        " Provides the bounding rectangle for a badge text "
        return self.canvas.settings.badgeFontMetrics.boundingRect(
                                        0, 0,  maxint, maxint, 0, text )

    def getTooltip( self ):
        s = self.canvas.settings
        parts = []
        canvas = self.canvas
        while canvas is not None:
            parts.insert( 0, canvas.getScopeName() )
            canvas = canvas.canvas
        if s.debug:
            return "::".join( parts ) + "<br>Size: " + str( self.width ) + "x" + str( self.height ) + \
               " (" + str( self.minWidth ) + "x" + str( self.minHeight ) + ")" + \
               " Row: " + str( self.addr[1] ) + " Column: " + str( self.addr[0] )
        return "::".join( parts )

    def getCanvasTooltip( self ):
        s = self.canvas.settings
        parts = []
        canvas = self.canvas
        while canvas is not None:
            parts.insert( 0, canvas.getScopeName() )
            canvas = canvas.canvas
        if s.debug:
            return "::".join(parts ) + "<br>Size: " + str( self.canvas.width ) + "x" + \
                   str( self.canvas.height ) + \
                   " (" + str( self.canvas.minWidth ) + "x" + \
                   str( self.canvas.minHeight ) + ")"
        return "::".join( parts )

    def _paintBadge( self, painter, option, widget, startX = None,
                                                    startY = None,
                                                    needRect = True ):
        " Paints a badge for a scope "
        s = self.canvas.settings
        height = self._badgeRect.height() + 2
        width = self._badgeRect.width() + 4
        pen = QPen( s.badgeLineColor )
        pen.setWidth( s.badgeLineWidth )
        painter.setPen( pen )

        if startX is None:
            startX = self.baseX + s.rectRadius + s.hScopeSpacing
        if startY is None:
            startY = self.baseY - height / 2 + s.vScopeSpacing
        if needRect:
            brush = QBrush( s.badgeBGColor )
            painter.setBrush( brush )
            painter.drawRoundedRect( startX, startY,
                                     width, height, 2, 2 )
        pen.setColor( s.badgeFGColor )
        painter.setPen( pen )
        painter.setFont( s.badgeFont )
        painter.drawText( startX + 2, startY + 1,
                          width - 2, height - 2,
                          Qt.AlignLeft, self._badgeText )
        return




class ScopeCellElement( CellElement ):

    UNKNOWN = -1

    TOP_LEFT = 0
    LEFT = 1
    BOTTOM_LEFT = 2
    DECLARATION = 3
    SIDE_COMMENT = 4
    DOCSTRING = 5
    TOP = 6
    BOTTOM = 7

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        self.subKind = self.UNKNOWN
        self.docstringText = None
        self._headerText = None
        self._headerRect = None
        self._sideComment = None
        self._sideCommentRect = None
        return

    def _getHeaderText( self ):
        if self._headerText is None:
            self._headerText = self.ref.getDisplayValue()
        return self._headerText

    def getDocstringText( self ):
        if self.docstringText is None:
            self.docstringText = self.ref.docstring.getDisplayValue()
        return self.docstringText

    def _render( self, badgeText = None ):
        " Provides rendering for the scope elements "
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.minHeight = s.rectRadius + s.vScopeSpacing
            self.minWidth = s.rectRadius + s. hScopeSpacing
            if badgeText:
                self._badgeText = badgeText
                self._badgeRect = self.getBadgeBoundingRect( badgeText )
        elif self.subKind == ScopeCellElement.LEFT:
            self.minHeight = 0
            self.minWidth = s.rectRadius + s.hScopeSpacing
        elif self.subKind == ScopeCellElement.BOTTOM_LEFT:
            self.minHeight = s.rectRadius + s.vScopeSpacing
            self.minWidth = s.rectRadius + s.hScopeSpacing
        elif self.subKind == ScopeCellElement.TOP:
            self.minHeight = s.rectRadius + s.vScopeSpacing
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.BOTTOM:
            self.minHeight = s.rectRadius + s.vScopeSpacing
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.DECLARATION:
            # The declaration location uses a bit of the top cell space
            # to make the view more compact
            self._headerRect = self.getBoundingRect( self._getHeaderText() )
            self.minHeight = self._headerRect.height() + \
                             2 * s.vHeaderPadding - s.rectRadius
            self.minWidth = self._headerRect.width() + \
                            s.hHeaderPadding - s.rectRadius
            if hasattr( self.ref, "sideComment" ):
                if self.ref.sideComment:
                    self.minHeight += 2 * s.vTextPadding
                    self.minWidth += s.hCellPadding
                else:
                    self.minHeight += s.vTextPadding
                    self.minWidth += s.hHeaderPadding
            else:
                self.minWidth += s.hHeaderPadding
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            self._sideCommentRect = self.getBoundingRect( self._getSideComment() )
            self.minHeight = self._sideCommentRect.height() + \
                             2 * (s.vHeaderPadding + s.vTextPadding) - \
                             s.rectRadius
            self.minWidth = s.hCellPadding + s.hTextPadding + \
                            self._sideCommentRect.width() + s.hTextPadding + \
                            s.hHeaderPadding - s.rectRadius
        elif self.subKind == ScopeCellElement.DOCSTRING:
            rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                   self.getDocstringText() )
            self.minHeight = rect.height() + 2 * s.vHeaderPadding
            self.minWidth = rect.width() + 2 * (s.hHeaderPadding - s.rectRadius)
        elif self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception( "Unknown scope element" )
        else:
            raise Exception( "Unrecognized scope element: " +
                             str( self.subKind ) )
        return

    def _draw( self, scene, baseX, baseY ):
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            # Draw the scope rounded rectangle when we see the top left corner
            vAdjust = 0
            if self._badgeRect:
                vAdjust = self._badgeRect.height() / 2 + 1 - s.vScopeSpacing
            self.setRect( baseX, baseY - vAdjust,
                          self.canvas.width, self.canvas.height + vAdjust )
            self.setToolTip( self.getCanvasTooltip() )
            scene.addItem( self )
            self.canvas.scopeRectangle = self
        elif self.subKind == ScopeCellElement.DECLARATION:
            yShift = 0
            if hasattr( self.ref, "sideComment" ):
                yShift = s.vTextPadding
            self.setRect( baseX - s.rectRadius,
                          baseY - s.rectRadius + s.vHeaderPadding + yShift,
                          self.canvas.width,
                          self.height + (s.rectRadius - s.vHeaderPadding) )
            self.setToolTip( self.getTooltip() )
            scene.addItem( self )
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            self.setRect( self.canvas.baseX + self.canvas.width - self.width,
                          baseY - s.rectRadius + s.vHeaderPadding,
                          self.width + s.rectRadius - s.hHeaderPadding,
                          self._sideCommentRect.height() + 2 * s.vTextPadding )
            self.setToolTip( self.getTooltip() )
            scene.addItem( self )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.setRect( baseX - s.rectRadius,
                          baseY + s.vHeaderPadding,
                          self.canvas.width, self.height - s.vHeaderPadding )
            self.setToolTip( self.getTooltip() )
            scene.addItem( self )
        return

    def _paint( self, painter, option, widget ):
        " Draws the function scope element "
        s = self.canvas.settings

        if self.subKind == ScopeCellElement.TOP_LEFT:
            pen = QPen( getDarkerColor( painter.brush().color() ) )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawRoundedRect( self.baseX + s.hScopeSpacing,
                                     self.baseY + s.vScopeSpacing,
                                     self.canvas.width - 2 * s.hScopeSpacing,
                                     self.canvas.height - 2 * s.vScopeSpacing,
                                     s.rectRadius, s.rectRadius )
            if self._badgeText:
                self._paintBadge( painter, option, widget )

            if self.kind in [ CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE ]:
                # Draw the 'break' badge
                oldBadgeText = self._badgeText
                oldBadgeRect = self._badgeRect
                self._badgeText = 'break'
                self._badgeRect = self.getBadgeBoundingRect( self._badgeText )
                self._paintBadge( painter, option, widget,
                                  self.baseX + self.canvas.width / 2 -
                                  self._badgeRect.width() / 2,
                                  self.baseY + self.canvas.height -
                                  self._badgeRect.height() - 2 * s.vScopeSpacing, True )
                self._badgeText = oldBadgeText
                self._badgeRect = oldBadgeRect

        elif self.subKind == ScopeCellElement.DECLARATION:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            yShift = 0
            if hasattr( self.ref, "sideComment" ):
                yShift = s.vTextPadding
            canvasLeft = self.baseX - s.rectRadius
            canvasTop = self.baseY - s.rectRadius
            painter.drawText( canvasLeft + s.hHeaderPadding + s.hScopeSpacing,
                              canvasTop + s.vHeaderPadding + yShift + s.vScopeSpacing,
                              int( self._headerRect.width() ),
                              int( self._headerRect.height() ),
                              Qt.AlignLeft, self._getHeaderText() )

            pen = QPen( getDarkerColor( painter.brush().color() ) )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( canvasLeft,
                              self.baseY + self.height,
                              canvasLeft + self.canvas.width - 2 * s.hScopeSpacing,
                              self.baseY + self.height )
            if self.kind in [ CellElement.FOR_SCOPE, CellElement.WHILE_SCOPE ]:
                # Draw the 'continue' badge
                oldBadgeText = self._badgeText
                oldBadgeRect = self._badgeRect
                self._badgeText = 'continue'
                self._badgeRect = self.getBadgeBoundingRect( self._badgeText )
                self._paintBadge( painter, option, widget,
                                  self.baseX - s.rectRadius +
                                  self.canvas.width / 2 - self._badgeRect.width() / 2,
                                  self.baseY + self.height, True )
                self._badgeText = oldBadgeText
                self._badgeRect = oldBadgeRect

        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            canvasTop = self.baseY - s.rectRadius
            movedBaseX = self.canvas.baseX + self.canvas.width - self.width + s.hScopeSpacing
            path = getNoCellCommentBoxPath( movedBaseX + s.hHeaderPadding,
                                            canvasTop + s.vHeaderPadding,
                                            int( self._sideCommentRect.width() ) + 2 * s.hTextPadding,
                                            int( self._sideCommentRect.height() ) + 2 * s.vTextPadding,
                                            s.commentCorner )
            brush = QBrush( s.commentBGColor )
            painter.setBrush( brush )
            pen = QPen( s.commentLineColor )
            pen.setWidth( s.commentLineWidth )
            painter.setPen( pen )
            painter.drawPath( path )

            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( movedBaseX + s.hHeaderPadding + s.hTextPadding,
                              canvasTop + s.vHeaderPadding + s.vTextPadding,
                              int( self._sideCommentRect.width() ),
                              int( self._sideCommentRect.height() ),
                              Qt.AlignLeft, self._getSideComment() )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            canvasLeft = self.baseX - s.rectRadius
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( canvasLeft + s.hHeaderPadding,
                              self.baseY + s.vHeaderPadding,
                              self.canvas.width - 2 * s.hHeaderPadding,
                              self.height - 2 * s.vHeaderPadding,
                              Qt.AlignLeft, self.getDocstringText() )

            pen = QPen( s.lineColor )
            pen = QPen( getDarkerColor( painter.brush().color() ) )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( canvasLeft, self.baseY + self.height,
                              canvasLeft + self.canvas.width - 2 * s.hScopeSpacing,
                              self.baseY + self.height )
        return


    def __str__( self ):
        return CellElement.__str__( self ) + \
               "(" + scopeCellElementToString( self.subKind ) + ")"


__kindToString = {
    CellElement.UNKNOWN:                "UNKNOWN",
    CellElement.VACANT:                 "VACANT",
    CellElement.H_SPACER:               "H_SPACER",
    CellElement.V_SPACER:               "V_SPACER",
    CellElement.FILE_SCOPE:             "FILE_SCOPE",
    CellElement.FUNC_SCOPE:             "FUNC_SCOPE",
    CellElement.CLASS_SCOPE:            "CLASS_SCOPE",
    CellElement.DECOR_SCOPE:            "DECOR_SCOPE",
    CellElement.FOR_SCOPE:              "FOR_SCOPE",
    CellElement.WHILE_SCOPE:            "WHILE_SCOPE",
    CellElement.ELSE_SCOPE:             "ELSE_SCOPE",
    CellElement.WITH_SCOPE:             "WITH_SCOPE",
    CellElement.TRY_SCOPE:              "TRY_SCOPE",
    CellElement.EXCEPT_SCOPE:           "EXCEPT_SCOPE",
    CellElement.FINALLY_SCOPE:          "FINALLY_SCOPE",
    CellElement.CODE_BLOCK:             "CODE_BLOCK",
    CellElement.BREAK:                  "BREAK",
    CellElement.CONTINUE:               "CONTINUE",
    CellElement.RETURN:                 "RETURN",
    CellElement.RAISE:                  "RAISE",
    CellElement.ASSERT:                 "ASSERT",
    CellElement.SYSEXIT:                "SYSEXIT",
    CellElement.IMPORT:                 "IMPORT",
    CellElement.IF:                     "IF",
    CellElement.LEADING_COMMENT:        "LEADING_COMMENT",
    CellElement.INDEPENDENT_COMMENT:    "INDEPENDENT_COMMENT",
    CellElement.SIDE_COMMENT:           "SIDE_COMMENT",
    CellElement.CONNECTOR:              "CONNECTOR",
}


def kindToString( kind ):
    " Provides a string representation of a element kind "
    return __kindToString[ kind ]


_scopeCellElementToString = {
    ScopeCellElement.UNKNOWN:           "UNKNOWN",
    ScopeCellElement.TOP_LEFT:          "TOP_LEFT",
    ScopeCellElement.LEFT:              "LEFT",
    ScopeCellElement.BOTTOM_LEFT:       "BOTTOM_LEFT",
    ScopeCellElement.DECLARATION:       "DECLARATION",
    ScopeCellElement.SIDE_COMMENT:      "SIDE_COMMENT",
    ScopeCellElement.DOCSTRING:         "DOCSTRING",
    ScopeCellElement.TOP:               "TOP",
    ScopeCellElement.BOTTOM:            "BOTTOM"
}

def scopeCellElementToString( kind ):
    " Provides a string representation of a element kind "
    return _scopeCellElementToString[ kind ]




class VacantCell( CellElement ):
    " Represents a vacant cell which can be later used for some other element "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        self.kind = CellElement.VACANT
        return

    def render( self ):
        self.width = 0
        self.height = 0
        self.minWidth = 0
        self.minHeight = 0
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        return


class VSpacerCell( CellElement ):
    " Represents a vertical spacer cell "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        self.kind = CellElement.V_SPACER
        return

    def render( self ):
        self.width = 0
        self.height = self.canvas.settings.vSpacer
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        # There is no need to draw anything. The cell just reserves some
        # vertical space for better appearance
        self.baseX = baseX
        self.baseY = baseY
        return


class HSpacerCell( CellElement ):
    " Represents a horizontal spacer cell "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        self.kind = CellElement.H_SPACER
        return

    def render( self ):
        self.width = self.canvas.settings.hSpacer
        self.height = 0
        self.minWidth = self.width
        self.minHeight = self.height
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        # There is no need to draw anything. The cell just reserves some
        # horizontal space for better appearance
        self.baseX = baseX
        self.baseY = baseY
        return


class CodeBlockCell( CellElement, QGraphicsRectItem ):
    " Represents a single code block "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.CODE_BLOCK
        self.__text = None
        self.__textRect = None
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * (s.vCellPadding + s.vTextPadding)
        self.minWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        brush = QBrush( s.boxBGColor )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.setBrush( brush )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        if s.stretchBlocks:
            painter.drawRect( self.baseX + s.hCellPadding,
                              self.baseY + s.vCellPadding,
                              self.width - 2 * s.hCellPadding,
                              self.height - 2 * s.vCellPadding )
        else:
            painter.drawRect( self.baseX + s.hCellPadding + (self.width - self.minWidth) / 2,
                              self.baseY + s.vCellPadding,
                              self.minWidth - 2 * s.hCellPadding,
                              self.height - 2 * s.vCellPadding )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding +
                          (self.width - 2 * s.hCellPadding - self.__textRect.width()) / 2,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return



class FileScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a file scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.FILE_SCOPE
        self.subKind = kind
        return

    def _getHeaderText( self ):
        if self._headerText is None:
            if self.ref.encodingLine:
                self._headerText = "Encoding: " + \
                                   self.ref.encodingLine.getDisplayValue()
            else:
                self._headerText = "Encoding: not specified"
            if self.ref.bangLine:
                self._headerText += "\nBang line: " + \
                                    self.ref.bangLine.getDisplayValue()
            else:
                self._headerText += "\nBang line: not specified"
        return self._headerText

    def render( self ):
        self._render()
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the file scope element "
        brush = QBrush( self.canvas.settings.fileScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class FunctionScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a function scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.FUNC_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.name.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            # The comment may stop before the end of the arguments list
            linesAfter = self.ref.arguments.endLine - \
                         self.ref.sideComment.endLine
            if linesAfter > 0:
                self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "def" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the function scope element "
        brush = QBrush( self.canvas.settings.funcScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class ClassScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a class scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.CLASS_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the class
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.name.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            if self.ref.baseClasses is None:
                lastLine = self.ref.name.endLine
            else:
                lastLine = self.ref.baseClasses.endLine
            # The comment may stop before the end of the arguments list
            linesAfter = lastLine - self.ref.sideComment.endLine
            if linesAfter > 0:
                self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "class" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the class scope element "
        brush = QBrush( self.canvas.settings.classScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class ForScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a for-loop scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.FOR_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.iteration.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            # The comment may stop before the end of the arguments list
            linesAfter = self.ref.iteration.endLine - \
                         self.ref.sideComment.endLine
            if linesAfter > 0:
                self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "for" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the for-loop scope element "
        brush = QBrush( self.canvas.settings.forScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return



class WhileScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a while-loop scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.WHILE_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.condition.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            # The comment may stop before the end of the arguments list
            linesAfter = self.ref.condition.endLine - \
                         self.ref.sideComment.endLine
            if linesAfter > 0:
                self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "while" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the while-loop scope element "
        brush = QBrush( self.canvas.settings.whileScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return



class TryScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a try-except scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.TRY_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
        return self._sideComment

    def _getHeaderText( self ):
        if self._headerText is None:
            self._headerText = "try"
        return self._headerText

    def render( self ):
        self._render( "try" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the try scope element "
        brush = QBrush( self.canvas.settings.tryScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return



class WithScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a with scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.WITH_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.items.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            # The comment may stop before the end of the arguments list
            linesAfter = self.ref.items.endLine - \
                         self.ref.sideComment.endLine
            if linesAfter > 0:
                self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "with" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the with scope element "
        brush = QBrush( self.canvas.settings.withScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class DecoratorScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a decorator scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.DECOR_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the function
            linesBefore = self.ref.sideComment.beginLine - \
                          self.ref.name.beginLine
            self._sideComment = '\n' * linesBefore + \
                                self.ref.sideComment.getDisplayValue()
            if self.ref.arguments is None:
                lastLine = self.ref.name.endLine
            else:
                lastLine = self.ref.arguments.endLine
            # The comment may stop before the end of the arguments list
            linesAfter = lastLine - self.ref.sideComment.endLine
            if linesAfter > 0:
                self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "@" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return
        if self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception( "Unknown decorator scope element" )

    def paint( self, painter, option, widget ):
        " Draws the decorator scope element "
        brush = QBrush( self.canvas.settings.decorScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class ElseScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents an else scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.ELSE_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
        return self._sideComment

    def _getHeaderText( self ):
        if self._headerText is None:
            self._headerText = "else"
        return self._headerText

    def render( self ):
        self._render( "else" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the else scope element "
        brush = QBrush( self.canvas.settings.elseScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class ExceptScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents an except scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.EXCEPT_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            # The comment may start not at the first line of the except
            if self.ref.clause is None:
                self._sideComment = self.ref.sideComment.getDisplayValue()
            else:
                linesBefore = self.ref.sideComment.beginLine - \
                              self.ref.clause.beginLine
                self._sideComment = '\n' * linesBefore + \
                                    self.ref.sideComment.getDisplayValue()
                lastLine = self.ref.clause.endLine
                # The comment may stop before the end of the arguments list
                linesAfter = lastLine - self.ref.sideComment.endLine
                if linesAfter > 0:
                    self._sideComment += '\n' * linesAfter
        return self._sideComment

    def render( self ):
        self._render( "except" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the except scope element "
        brush = QBrush( self.canvas.settings.exceptScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return


class FinallyScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a finally scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.FINALLY_SCOPE
        self.subKind = kind
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
        return self._sideComment

    def _getHeaderText( self ):
        if self._headerText is None:
            self._headerText = "finally"
        return self._headerText

    def render( self ):
        self._render( "finally" )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self._draw( scene, baseX, baseY )
        return

    def paint( self, painter, option, widget ):
        " Draws the finally scope element "
        brush = QBrush( self.canvas.settings.finallyScopeBGColor )
        painter.setBrush( brush )
        self._paint( painter, option, widget )
        return





class BreakCell( CellElement, QGraphicsRectItem ):
    " Represents a single break statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.BREAK
        self.__textRect = None
        self.__radius = None
        return

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( "b" )
        self.__radius = int( sqrt( self.__textRect.width() ** 2 +
                                   self.__textRect.height() ** 2 ) / 2 ) + 1
        self.minHeight = 2 * (self.__radius + s.vCellPadding)
        self.minWidth = 2 * (self.__radius + s.hCellPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
        self.setToolTip( self.getTooltip() + " radius: " + str( self.__radius ) )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the break statement "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        brush = QBrush( s.breakBGColor )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.setBrush( brush )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height / 2 )
        painter.drawEllipse( self.baseX + self.width / 2 - self.__radius,
                             self.baseY + self.height / 2 - self.__radius,
                             self.__radius * 2, self.__radius * 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + (self.width - self.__textRect.width()) / 2,
                          self.baseY + (self.height - self.__textRect.height()) / 2,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignCenter, "b" )
        return


class ContinueCell( CellElement, QGraphicsRectItem ):
    " Represents a single continue statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.CONTINUE
        self.__textRect = None
        self.__radius = None
        return

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( "c" )
        self.__radius = int( sqrt( self.__textRect.width() ** 2 +
                                   self.__textRect.height() ** 2 ) / 2 ) + 1
        self.minHeight = 2 * (self.__radius + s.vCellPadding)
        self.minWidth = 2 * (self.__radius + s.hCellPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
        self.setToolTip( self.getTooltip() + " radius: " + str( self.__radius ) )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the break statement "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        brush = QBrush( s.continueBGColor )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.setBrush( brush )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height / 2 )
        painter.drawEllipse( self.baseX + self.width / 2 - self.__radius,
                             self.baseY + self.height / 2 - self.__radius,
                             self.__radius * 2, self.__radius * 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + (self.width - self.__textRect.width()) / 2,
                          self.baseY + (self.height - self.__textRect.height()) / 2,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignCenter, "c" )
        return



class ReturnCell( CellElement, QGraphicsRectItem ):
    " Represents a single return statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.RETURN
        self.__text = None
        self.__textRect = None
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * (s.vCellPadding + s.vTextPadding)
        self.minWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                             s.minWidth )

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        brush = QBrush( s.returnBGColor )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.setBrush( brush )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height / 2 )

        pen = QPen( getDarkerColor( s.returnBGColor ) )
        painter.setPen( pen )
        if s.stretchBlocks:
            painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                     self.baseY + s.vCellPadding,
                                     self.width - 2 * s.hCellPadding,
                                     self.height - 2 * s.vCellPadding,
                                     s.returnRectRadius, s.returnRectRadius )
        else:
            painter.drawRoundedRect( self.baseX + s.hCellPadding + (self.width - self.minWidth) / 2,
                                     self.baseY + s.vCellPadding,
                                     self.minWidth - 2 * s.hCellPadding,
                                     self.height - 2 * s.vCellPadding,
                                     s.returnRectRadius, s.returnRectRadius )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding +
                          (self.width - 2 * s.hCellPadding - self.__textRect.width()) / 2,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return


class RaiseCell( CellElement, QGraphicsRectItem ):
    " Represents a single raise statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.RAISE
        self.__text = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem( "raise.svg" )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "raise" )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                               0, self.__getText() )

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding +
                             2 * s.hTextPadding + self.__arrowWidth,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )

        s = self.canvas.settings
        self.arrowItem.setPos( baseX + s.hCellPadding + s.hTextPadding,
                               baseY + self.height/2 - self.arrowItem.height()/2 )

        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height / 2 )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.width - 2 * s.hCellPadding,
                                 self.height - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.__arrowWidth + 2 * s.hTextPadding,
                                self.height - 2 * s.vCellPadding,
                                s.returnRectRadius, s.returnRectRadius )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + self.__arrowWidth + 3 * s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * (s.hTextPadding + s.hCellPadding) - self.__arrowWidth,
                          int( self.rect().height() ) - 2 * (s.vTextPadding + s.vCellPadding),
                          Qt.AlignLeft,
                          self.__getText() )
        return




class AssertCell( CellElement, QGraphicsRectItem ):
    " Represents a single assert statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.ASSERT
        self.__text = None
        self.__diamondDiagonal = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem( "assert.svg" )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "assert" )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                               0, self.__getText() )

        # for an arrow box
        singleCharRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                                         0, "W" )
        self.__diamondDiagonal = singleCharRect.height() + 2 * s.vTextPadding

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding + \
                             self.__diamondDiagonal,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )

        s = self.canvas.settings
        self.arrowItem.setPos( baseX + self.__diamondDiagonal / 2 + s.hCellPadding -
                               self.arrowItem.width() / 2,
                               baseY + self.height/2 - self.arrowItem.height()/2 )

        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )

        dHalf = int( self.__diamondDiagonal / 2.0 )
        dx1 = self.baseX + s.hCellPadding
        dy1 = self.baseY + int( self.height / 2 )
        dx2 = dx1 + dHalf
        dy2 = dy1 - dHalf
        dx3 = dx1 + 2 * dHalf
        dy3 = dy1
        dx4 = dx2
        dy4 = dy2 + 2 * dHalf

        painter.drawPolygon( QPointF(dx1, dy1), QPointF(dx2, dy2),
                             QPointF(dx3, dy3), QPointF(dx4, dy4) )

        painter.drawRect( dx3 + 1, self.baseY + s.vCellPadding,
                          self.width - 2 * s.hCellPadding - self.__diamondDiagonal,
                          self.height - 2 * s.vCellPadding )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( dx3 + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * (s.hTextPadding + s.hCellPadding) - self.__diamondDiagonal,
                          int( self.rect().height() ) - 2 * (s.vTextPadding + s.vCellPadding),
                          Qt.AlignLeft,
                          self.__getText() )
        return




class SysexitCell( CellElement ):
    " Represents a single sys.exit(...) statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.SYSEXIT
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ImportCell( CellElement, QGraphicsRectItem ):
    " Represents a single import statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.IMPORT
        self.__text = None
        self.__arrowWidth = 16
        self.__textRect = None
        self.arrowItem = SVGItem( "import.svgz" )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "import" )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                               0, self.__getText() )
        self.minHeight = self.__textRect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding +
                             self.__arrowWidth + 2 * s.hTextPadding,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )

        s = self.canvas.settings
        if s.stretchBlocks:
            hShift = 0
        else:
            hShift = (self.width - self.minWidth) / 2
        self.arrowItem.setPos( baseX + s.hCellPadding + s.hTextPadding + hShift,
                               baseY + self.height/2 - self.arrowItem.height()/2 )
        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        if s.stretchBlocks:
            hShift = 0
            width = self.width
        else:
            hShift = (self.width - self.minWidth) / 2
            width = self.minWidth
        painter.drawRect( self.baseX + s.hCellPadding + hShift,
                          self.baseY + s.vCellPadding,
                          width - 2 * s.hCellPadding,
                          self.height - 2 * s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding + self.__arrowWidth + 2 * s.hTextPadding + hShift,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + self.__arrowWidth + 2 * s.hTextPadding + hShift,
                          self.baseY + self.height - s.vCellPadding )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        textRectWidth = width - 2 * s.hCellPadding - 4 * s.hTextPadding - self.__arrowWidth
        textShift = ( textRectWidth - self.__textRect.width() ) / 2
        painter.drawText( self.baseX + s.hCellPadding + self.__arrowWidth + 3 * s.hTextPadding + hShift + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft,
                          self.__getText() )
        return


class IfCell( CellElement, QGraphicsRectItem ):
    " Represents a single if statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.IF
        self.__text = None
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                               self.__getText() )

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding + 2 * s.ifWidth
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        path = QPainterPath()
        path.moveTo( self.baseX + s.hCellPadding,
                     self.baseY + self.height / 2 )
        path.lineTo( self.baseX + s.hCellPadding + s.ifWidth,
                     self.baseY + s.vCellPadding )
        path.lineTo( self.baseX + (self.width - s.hCellPadding - s.ifWidth),
                     self.baseY + s.vCellPadding )
        path.lineTo( self.baseX + (self.width - s.hCellPadding),
                     self.baseY + self.height / 2 )
        path.lineTo( self.baseX + (self.width - s.hCellPadding - s.ifWidth),
                     self.baseY + (self.height - s.vCellPadding) )
        path.lineTo( self.baseX + s.hCellPadding + s.ifWidth,
                     self.baseY + (self.height - s.vCellPadding) )
        path.lineTo( self.baseX + s.hCellPadding,
                     self.baseY + self.height / 2 )

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )


        # Draw the connector as a single line under the rectangle
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        painter.drawPath( path )
        painter.drawLine( self.baseX + (self.width - s.hCellPadding),
                          self.baseY + self.height / 2,
                          self.baseX + self.width,
                          self.baseY + self.height / 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.ifWidth + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * s.ifWidth - 2 * s.hTextPadding,
                          int( self.rect().height() ) - 2 * s.vTextPadding,
                          Qt.AlignLeft,
                          self.__getText() )

        # Draw the 'n' badge
        self._badgeText = 'N'
        self._badgeRect = self.getBadgeBoundingRect( self._badgeText )
        self._paintBadge( painter, option, widget,
                          self.baseX + self.width - self._badgeRect.width() - 7,
                          self.baseY + self.height / 2 - self._badgeRect.height() - 3,
                          False )
        return



def getCommentBoxPath( settings, baseX, baseY, width, height ):
    " Provides the comomment box path "
    return getNoCellCommentBoxPath( baseX + settings.hCellPadding,
                                    baseY + settings.vCellPadding,
                                    width - 2 * settings.hCellPadding,
                                    height - 2 * settings.vCellPadding,
                                    settings.commentCorner )


def getNoCellCommentBoxPath( x, y, width, height, corner ):
    " Provides the path for exactly specified rectangle "
    path = QPainterPath()
    path.moveTo( x, y )
    path.lineTo( x + width - corner, y )
    path.lineTo( x + width - corner, y + corner )
    path.lineTo( x + width, y + corner )
    path.lineTo( x + width,  y + height )
    path.lineTo( x, y + height )
    path.lineTo( x, y )
    path.moveTo( x + width - corner, y )
    path.lineTo( x + width, y + corner )
    return path




class IndependentCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single independent comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.INDEPENDENT_COMMENT
        self.__text = None
        self.__textRect = None
        self.leadingForElse = False
        self.sideForElse = False
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                          self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * (s.vCellPadding + s.vTextPadding)
        self.minWidth = self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the independent comment "
        s = self.canvas.settings

        w = self.minWidth
        if s.stretchComments:
            w = self.width

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        path = getCommentBoxPath( s, self.baseX, self.baseY, w, self.height )
        path.moveTo( self.baseX + s.hCellPadding,
                     self.baseY + self.height / 2 )
        if self.leadingForElse:
            path.lineTo( self.baseX, self.baseY + self.height / 2 )
            path.moveTo( self.baseX, self.baseY + self.height / 2 )
            path.lineTo( self.baseX - cellToTheLeft.width / 2,
                         self.baseY + self.height )
        else:
            path.lineTo( self.baseX - cellToTheLeft.width / 2,
                         self.baseY + self.height / 2 )

        self.setPath( path )

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )
        self.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )

        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.width - 2 * (s.hCellPadding + s.hTextPadding),
                          self.height - 2 * (s.vCellPadding + s.vTextPadding),
                          Qt.AlignLeft | Qt.AlignVCenter,
                          self.__getText() )
        return



class LeadingCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single leading comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.LEADING_COMMENT
        self.__text = None
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.leadingComment.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                               self.__getText() )

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the leading comment "
        s = self.canvas.settings

        w = self.minWidth
        if s.stretchComments:
            w = self.width

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        path = getCommentBoxPath( s, self.baseX, baseY, w, self.minHeight )
        path.moveTo( self.baseX + s.hCellPadding,
                     baseY + self.minHeight / 2 )
#        path.lineTo( self.baseX - cellToTheLeft.width / 4,
#                     baseY + self.minHeight / 2 )
        path.lineTo( self.baseX,
                     baseY + self.minHeight / 2 )
        # The moveTo() below is required to suppress painting the surface
#        path.moveTo( self.baseX - cellToTheLeft.width / 4,
#                     baseY + self.minHeight / 2 )
        path.moveTo( self.baseX,
                     baseY + self.minHeight / 2 )
#        path.lineTo( self.baseX - cellToTheLeft.width / 3,
#                     baseY + self.minHeight + s.vCellPadding )
        path.lineTo( self.baseX - s.rectRadius,
                     baseY + self.minHeight + s.vCellPadding )
        self.setPath( path )

        self.setToolTip( self.getTooltip() + " Cell to the left width: " + str(cellToTheLeft.width ) )

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )
        self.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )

        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
                          baseY + s.vCellPadding + s.vTextPadding,
                          self.width - 2 * (s.hCellPadding + s.hTextPadding),
                          self.minHeight - 2 * (s.vCellPadding + s.vTextPadding),
                          Qt.AlignLeft | Qt.AlignVCenter,
                          self.__getText() )
        return



class SideCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single side comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.SIDE_COMMENT
        self.__text = None
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = ""
            cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
            if cellToTheLeft.kind == CellElement.IMPORT:
                importRef = cellToTheLeft.ref
                if importRef.fromPart is not None:
                    self.__text = "\n"
                self.__text += '\n' * (self.ref.sideComment.beginLine - importRef.whatPart.beginLine) + \
                               self.ref.sideComment.getDisplayValue()
            else:
                self.__text = '\n' * (self.ref.sideComment.beginLine - self.ref.body.beginLine) + \
                              self.ref.sideComment.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                               self.__getText() )

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the side comment "
        s = self.canvas.settings

        w = self.minWidth
        if s.stretchComments:
            w = self.width

        path = getCommentBoxPath( s, self.baseX, self.baseY, w, self.height )
        if self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ].kind == CellElement.CONNECTOR:
            # 'if' or 'elif' side comment
            path.moveTo( self.baseX + s.hCellPadding,
                         self.baseY + self.height / 2 + 6 )
            width = 0
            index = self.addr[ 0 ] - 1
            while self.canvas.cells[ self.addr[ 1 ] ][ index ].kind == CellElement.CONNECTOR:
                width += self.canvas.cells[ self.addr[ 1 ] ][ index ].width
                index -= 1
            path.lineTo( self.baseX - s.hCellPadding - width,
                         self.baseY + self.height / 2 + 6 )
        else:
            # Regular box
            path.moveTo( self.baseX + s.hCellPadding,
                         self.baseY + self.height / 2 )
            path.lineTo( self.baseX - s.hCellPadding,
                         self.baseY + self.height / 2 )

        self.setPath( path )

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )
        self.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )

        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.width - 2 * (s.hCellPadding + s.hTextPadding),
                          self.height - 2 * (s.vCellPadding + s.vTextPadding),
                          Qt.AlignLeft,
                          self.__getText() )
        return



class ConnectorCell( CellElement, QGraphicsPathItem ):
    " Represents a single connector cell "

    NORTH = 0
    SOUTH = 1
    WEST = 2
    EAST = 3
    CENTER = 4

    def __init__( self, connections, canvas, x, y ):
        """ Connections are supposed to be a list of tuples e.g
            [ (NORTH, SOUTH), (EAST, CENTER) ] """
        CellElement.__init__( self, None, canvas, x, y )
        QGraphicsPathItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.CONNECTOR
        self.connections = connections
        return

    def render( self ):
        s = self.canvas.settings

        self.minHeight = 2 * s.vCellPadding
        self.minWidth = 2 * s.hCellPadding
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __getXY( self, location ):
        if location == self.NORTH:
            return self.baseX + self.width / 2, self.baseY
        if location == self.SOUTH:
            return self.baseX + self.width / 2, self.baseY + self.height
        if location == self.WEST:
            return self.baseX, self.baseY + self.height / 2
        if location == self.EAST:
            return self.baseX + self.width, self.baseY + self.height / 2
        # It is CENTER
        return self.baseX + self.width / 2, self.baseY + self.height / 2

    def __angled( self, begin, end ):
        if begin in [ self.NORTH, self.SOUTH ] and \
           end in [ self.WEST, self.EAST ]:
            return True
        return end in [ self.NORTH, self.SOUTH ] and \
               begin in [ self.WEST, self.EAST ]

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY

        path = QPainterPath()
        for connection in self.connections:
            startX, startY = self.__getXY( connection[ 0 ] )
            endX, endY = self.__getXY( connection[ 1 ] )
            if self.__angled( connection[ 0 ], connection[ 1 ] ):
                centerX, centerY = self.__getXY( self.CENTER )
                path.moveTo( startX, startY )
                path.lineTo( centerX, centerY )
                path.lineTo( endX, endY )
            else:
                path.moveTo( startX, startY )
                path.lineTo( endX, endY )
        self.setPath( path )

        self.setToolTip( self.getTooltip() )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        self.setPen( pen )
        painter.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )
        return

