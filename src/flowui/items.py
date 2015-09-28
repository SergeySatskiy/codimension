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
                          QPainterPath, QPainter, QColor, QGraphicsItem,
                          QStyleOptionGraphicsItem, QStyle )
from PyQt4.QtSvg import QGraphicsSvgItem
import os.path



TOP_Z = 100.0

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


class BadgeItem( QGraphicsRectItem ):
    " Serves the scope badges "

    def __init__( self, ref, text ):
        QGraphicsRectItem.__init__( self )
        self.ref = ref
        self.__text = text

        self.__textRect = ref.canvas.settings.badgeFontMetrics.boundingRect(
                                                0, 0,  maxint, maxint, 0, text )
        self.__hSpacing = 2
        self.__vSpacing = 1
        self.__radius = 2

        self.__width = self.__textRect.width() + 2 * self.__hSpacing
        self.__height = self.__textRect.height() + 2 * self.__vSpacing

        self.__bgColor = ref.canvas.settings.badgeBGColor
        self.__fgColor = ref.canvas.settings.badgeFGColor
        self.__frameColor = ref.canvas.settings.badgeLineColor
        self.__font = ref.canvas.settings.badgeFont
        self.__needRect = True
        return

    def setBGColor( self, bgColor ):
        self.__bgColor = bgColor
    def setFGColor( self, fgColor ):
        self.__fgColor = fgColor
    def setFrameColor( self, frameColor ):
        self.__frameColor = framecolor
    def setNeedRectangle( self, value ):
        self.__needRect = value
    def setFont( self, font ):
        self.__font = font
    def width( self ):
        return self.__width
    def height( self ):
        return self.__height
    def text( self ):
        return self.__text
    def moveTo( self, x, y ):
        # This is a mistery. I do not understand why I need to divide by 2.0
        # however this works. I tried various combinations of initialization,
        # setting the position and mapping. Nothing works but ../2.0. Sick!
        self.setPos( float(x)/2.0, float(y)/2.0 )
        self.setRect( float(x)/2.0, float(y)/2.0, self.__width, self.__height )
    def withinHeader( self ):
        if self.ref.kind in [ self.ref.ELSE_SCOPE,
                              self.ref.FINALLY_SCOPE,
                              self.ref.TRY_SCOPE ]:
            return True
        if self.ref.kind == self.ref.EXCEPT_SCOPE:
            return self.ref.ref.clause is None
        return False

    def paint( self, painter, option, widget ):
        " Paints the scope item "
        s = self.ref.canvas.settings

        if self.__needRect:
            pen = QPen( self.__frameColor )
            pen.setWidth( s.badgeLineWidth )
            painter.setPen( pen )
            brush = QBrush( self.__bgColor )
            painter.setBrush( brush )
            painter.drawRoundedRect( self.x(), self.y(),
                                     self.__width, self.__height,
                                     self.__radius, self.__radius )

        pen = QPen( self.__fgColor )
        painter.setPen( pen )
        painter.setFont( self.__font )
        painter.drawText( self.x() + self.__hSpacing, self.y() + self.__vSpacing,
                          self.__textRect.width(),
                          self.__textRect.height(),
                          Qt.AlignLeft, self.__text )
        return


class ScopeConnector( QGraphicsPathItem ):

    def __init__( self, settings, x1, y1, x2, y2 ):
        QGraphicsPathItem.__init__( self )
        self.__settings = settings

        path = QPainterPath()
        path.moveTo( x1, y1 )
        path.lineTo( x2, y2 )
        self.setPath( path )
        return

    def paint( self, painter, option, widget ):
        pen = QPen( self.__settings.lineColor )
        pen.setWidth( self.__settings.lineWidth )
        self.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )
        return


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
        self._editor = None

        self.tailComment = False

        # Filled when rendering is called
        self.width = None
        self.height = None
        self.minWidth = None
        self.minHeight = None

        # Filled when draw is called
        self.baseX = None
        self.baseY = None
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
        path = " :: ".join( parts )
        if not path:
            path = " ::"
        if s.debug:
            return path + "<br>Size: " + str( self.canvas.width ) + "x" + \
                   str( self.canvas.height ) + \
                   " (" + str( self.canvas.minWidth ) + "x" + \
                   str( self.canvas.minHeight ) + ")"
        return path

    def setEditor( self, editor ):
        """ Provides the editor counterpart
            The default implementation is to ignore it """
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
        self._badgeItem = None
        self.__navBarUpdate = None
        self._connector = None
        return

    def _getHeaderText( self ):
        if self._headerText is None:
            self._headerText = self.ref.getDisplayValue()
        return self._headerText

    def getDocstringText( self ):
        if self.docstringText is None:
            self.docstringText = self.ref.docstring.getDisplayValue()
        return self.docstringText

    def _render( self ):
        " Provides rendering for the scope elements "
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = s.rectRadius + s.hCellPadding
        elif self.subKind == ScopeCellElement.LEFT:
            self.minHeight = 0
            self.minWidth = s.rectRadius + s.hCellPadding
        elif self.subKind == ScopeCellElement.BOTTOM_LEFT:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = s.rectRadius + s.hCellPadding
        elif self.subKind == ScopeCellElement.TOP:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.BOTTOM:
            self.minHeight = s.rectRadius + s.vCellPadding
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.DECLARATION:
            # The declaration location uses a bit of the top cell space
            # to make the view more compact
            badgeItem = self.canvas.cells[ self.addr[ 1 ] - 1 ][ self.addr[ 0 ] - 1]._badgeItem

            self._headerRect = self.getBoundingRect( self._getHeaderText() )
            self.minHeight = self._headerRect.height() + \
                             2 * s.vHeaderPadding - s.rectRadius
            w = self._headerRect.width()
            if badgeItem:
                w = max( w, badgeItem.width() )
            self.minWidth = w + s.hHeaderPadding - s.rectRadius
            if badgeItem:
                if badgeItem.withinHeader():
                    self.minWidth = badgeItem.width() + \
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

    def __afterTry( self ):
        row = self.canvas.addr[ 1 ] - 1
        column = self.canvas.addr[ 0 ]
        cells = self.canvas.canvas.cells
        while row >= 0:
            try:
                if cells[ row ][ column ].kind == CellElement.CONNECTOR:
                    row -= 1
                    continue
                if cells[ row ][ column ].kind == CellElement.VCANVAS:
                    return cells[ row ][ column ].cells[ 0 ][ 0 ].kind == CellElement.TRY_SCOPE
            except:
                return False
        return False

    def __needConnector( self ):
        if self.kind in [ CellElement.FOR_SCOPE, CellElement.DECOR_SCOPE,
                          CellElement.WHILE_SCOPE, CellElement.FUNC_SCOPE,
                          CellElement.CLASS_SCOPE, CellElement.WITH_SCOPE,
                          CellElement.FINALLY_SCOPE, CellElement.TRY_SCOPE ]:
            return True
        if self.kind == CellElement.ELSE_SCOPE:
            return self.__afterTry()

    def _draw( self, scene, baseX, baseY ):
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            # Draw connector if needed
            if self.__needConnector() and self._connector is None:
                self._connector = ScopeConnector( s, baseX + s.mainLine, baseY,
                                                  baseX + s.mainLine,
                                                  baseY + self.canvas.height )
                scene.addItem( self._connector )

            # Draw the scope rounded rectangle when we see the top left corner
            self.setRect( baseX + s.hCellPadding,
                          baseY + s.vCellPadding,
                          self.canvas.minWidth - 2 * s.hCellPadding,
                          self.canvas.minHeight - 2 * s.vCellPadding )
            scene.addItem( self )
            self.canvas.scopeRectangle = self
            if self._badgeItem:
                if self._badgeItem.withinHeader():
                    headerHeight = self.canvas.cells[ self.addr[ 1 ] + 1 ][ self.addr[ 0 ] ].height
                    fullHeight = headerHeight + s.rectRadius
                    self._badgeItem.moveTo( baseX + s.hCellPadding + s.rectRadius,
                                            baseY + s.vCellPadding + fullHeight / 2 - self._badgeItem.height() / 2 )
                else:
                    self._badgeItem.moveTo( baseX + s.hCellPadding + s.rectRadius,
                                            baseY + s.vCellPadding - self._badgeItem.height() / 2 )
                scene.addItem( self._badgeItem )
            if hasattr( scene.parent(), "updateNavigationToolbar" ):
                self.__navBarUpdate = scene.parent().updateNavigationToolbar
                self.setAcceptHoverEvents( True )
        elif self.subKind == ScopeCellElement.DECLARATION:
            yShift = 0
            if hasattr( self.ref, "sideComment" ):
                yShift = s.vTextPadding
            self.setRect( baseX - s.rectRadius,
                          baseY - s.rectRadius + s.vHeaderPadding + yShift,
                          self.canvas.width,
                          self.height + (s.rectRadius - s.vHeaderPadding) )
            scene.addItem( self )
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            self.setRect( self.canvas.baseX + self.canvas.width - self.width,
                          baseY - s.rectRadius + s.vHeaderPadding,
                          self.width + s.rectRadius - s.hHeaderPadding,
                          self._sideCommentRect.height() + 2 * s.vTextPadding )
            scene.addItem( self )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.setRect( baseX - s.rectRadius,
                          baseY + s.vHeaderPadding,
                          self.canvas.width, self.height - s.vHeaderPadding )
            scene.addItem( self )
        return

    def _paint( self, painter, option, widget ):
        " Draws the function scope element "
        s = self.canvas.settings

        if self.subKind == ScopeCellElement.TOP_LEFT:
            pen = QPen( getDarkerColor( painter.brush().color() ) )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                     self.baseY + s.vCellPadding,
                                     self.canvas.minWidth - 2 * s.hCellPadding,
                                     self.canvas.minHeight - 2 * s.vCellPadding,
                                     s.rectRadius, s.rectRadius )

        elif self.subKind == ScopeCellElement.DECLARATION:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            canvasLeft = self.baseX - s.rectRadius
            canvasTop = self.baseY - s.rectRadius
            textHeight = self._headerRect.height()
            yShift = 0
            if hasattr( self.ref, "sideComment" ):
                yShift = s.vTextPadding
            painter.drawText( canvasLeft + s.hHeaderPadding,
                              canvasTop + s.vHeaderPadding + yShift,
                              self._headerRect.width(), textHeight,
                              Qt.AlignLeft, self._getHeaderText() )

            pen = QPen( getDarkerColor( painter.brush().color() ) )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( canvasLeft,
                              self.baseY + self.height,
                              canvasLeft + self.canvas.minWidth - 2 * s.hCellPadding,
                              self.baseY + self.height )

        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            canvasTop = self.baseY - s.rectRadius
            # s.vHeaderPadding below is used intentionally: to have the same
            # spacing on top, bottom and right for the comment box
            movedBaseX = self.canvas.baseX + self.canvas.width - self.width - s.rectRadius - s.vHeaderPadding
            path = getNoCellCommentBoxPath( movedBaseX + s.hHeaderPadding,
                                            canvasTop + s.vHeaderPadding,
                                            self._sideCommentRect.width() + 2 * s.hTextPadding,
                                            self._sideCommentRect.height() + 2 * s.vTextPadding,
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
                              self._sideCommentRect.width(),
                              self._sideCommentRect.height(),
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
                              canvasLeft + self.canvas.minWidth - 2 * s.hCellPadding,
                              self.baseY + self.height )
        return

    def hoverEnterEvent( self, event ):
        if self.__navBarUpdate:
            self.__navBarUpdate( self.getCanvasTooltip() )
        return

    def hoverLeaveEvent( self, event ):
#        if self.__navBarUpdate:
#            self.__navBarUpdate( "" )
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

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
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
        self.setZValue( TOP_Z )
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
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )

        rectWidth = self.minWidth - 2 * s.hCellPadding
        rectHeight = self.minHeight - 2 * s.vCellPadding
        painter.drawRect( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          rectWidth, rectHeight )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )

        textWidth = self.__textRect.width() + 2 * s.hTextPadding
        textShift = (rectWidth - textWidth) / 2
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "def" )
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "class" )
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "for" )
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "while" )
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
            self._headerText = ""
        return self._headerText

    def render( self ):
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "try" )
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "with" )
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "@" )
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
        self.after = self
        return

    def _getSideComment( self ):
        if self._sideComment is None:
            self._sideComment = self.ref.sideComment.getDisplayValue()
        return self._sideComment

    def _getHeaderText( self ):
        if self._headerText is None:
            self._headerText = ""
        return self._headerText

    def render( self ):
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "else" )
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "except" )
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
            self._headerText = ""
        return self._headerText

    def render( self ):
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self._badgeItem = BadgeItem( self, "finally" )
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
        self.__vSpacing = 0
        self.__hSpacing = 4

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( "break" )
        self.minHeight = self.__textRect.height() + 2 * self.__vSpacing + s.vCellPadding
        self.minWidth = self.__textRect.width() + 2 * (self.__hSpacing + s.hCellPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
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
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + s.vCellPadding )

        pen = QPen( getDarkerColor( s.breakBGColor ) )
        painter.setPen( pen )

        x1 = self.baseX + s.hCellPadding
        y1 = self.baseY + s.vCellPadding
        w = 2 * self.__hSpacing + self.__textRect.width()
        h = 2 * self.__vSpacing + self.__textRect.height()

        painter.drawRoundedRect( x1, y1, w, h, 2, 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( x1 + self.__hSpacing, y1 + self.__vSpacing,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, "break" )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return


class ContinueCell( CellElement, QGraphicsRectItem ):
    " Represents a single continue statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.CONTINUE
        self.__textRect = None
        self.__vSpacing = 0
        self.__hSpacing = 4

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( "continue" )
        self.minHeight = self.__textRect.height() + 2 * self.__vSpacing + s.vCellPadding
        self.minWidth = self.__textRect.width() + 2 * (self.__hSpacing + s.hCellPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
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
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + s.vCellPadding )

        pen = QPen( getDarkerColor( s.continueBGColor ) )
        painter.setPen( pen )

        x1 = self.baseX + s.hCellPadding
        y1 = self.baseY + s.vCellPadding
        w = 2 * self.__hSpacing + self.__textRect.width()
        h = 2 * self.__vSpacing + self.__textRect.height()

        painter.drawRoundedRect( x1, y1, w, h, 2, 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( x1 + self.__hSpacing, y1 + self.__vSpacing,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, "continue" )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return


class ReturnCell( CellElement, QGraphicsRectItem ):
    " Represents a single return statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.RETURN
        self.__text = None
        self.__textRect = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem( "return.svgz" )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "return" )

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
            if not self.__text:
                self.__text = "None"
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * (s.vCellPadding + s.vTextPadding)
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + s.hTextPadding +
                             s.returnRectRadius + 2 * s.hTextPadding + self.__arrowWidth,
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
                               baseY + self.minHeight/2 - self.arrowItem.height()/2 )

        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + s.vCellPadding )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.minWidth - 2 * s.hCellPadding,
                                 self.minHeight - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.__arrowWidth + 2 * s.hTextPadding,
                                 self.minHeight - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )

        availWidth = self.minWidth - 2 * s.hCellPadding - self.__arrowWidth - 2 * s.hTextPadding - s.hTextPadding - s.returnRectRadius
        textShift = (availWidth - self.__textRect.width()) / 2
        painter.drawText( self.baseX + s.hCellPadding + self.__arrowWidth + 3 * s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return


class RaiseCell( CellElement, QGraphicsRectItem ):
    " Represents a single raise statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.RAISE
        self.__text = None
        self.__textRect = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem( "raise.svg" )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "raise" )

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * (s.vCellPadding + s.vTextPadding)
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + s.hTextPadding +
                             s.returnRectRadius + 2 * s.hTextPadding + self.__arrowWidth,
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
                               baseY + self.minHeight/2 - self.arrowItem.height()/2 )

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
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + s.vCellPadding )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.minWidth - 2 * s.hCellPadding,
                                 self.minHeight - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.__arrowWidth + 2 * s.hTextPadding,
                                 self.minHeight - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        availWidth = self.minWidth - 2 * s.hCellPadding - self.__arrowWidth - 2 * s.hTextPadding - s.hTextPadding - s.returnRectRadius
        textShift = (availWidth - self.__textRect.width()) / 2
        painter.drawText( self.baseX + s.hCellPadding + self.__arrowWidth + 3 * s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return




class AssertCell( CellElement, QGraphicsRectItem ):
    " Represents a single assert statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.ASSERT
        self.__text = None
        self.__textRect = None
        self.__diamondDiagonal = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem( "assert.svg" )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "assert" )

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                                          0, self.__getText() )

        # for an arrow box
        singleCharRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                                         0, "W" )
        self.__diamondDiagonal = singleCharRect.height() + 2 * s.vTextPadding

        self.minHeight = self.__textRect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding +
                             self.__diamondDiagonal, s.minWidth )
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
                               baseY + self.minHeight/2 - self.arrowItem.height()/2 )

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
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )

        dHalf = int( self.__diamondDiagonal / 2.0 )
        dx1 = self.baseX + s.hCellPadding
        dy1 = self.baseY + int( self.minHeight / 2 )
        dx2 = dx1 + dHalf
        dy2 = dy1 - dHalf
        dx3 = dx1 + 2 * dHalf
        dy3 = dy1
        dx4 = dx2
        dy4 = dy2 + 2 * dHalf

        painter.drawPolygon( QPointF(dx1, dy1), QPointF(dx2, dy2),
                             QPointF(dx3, dy3), QPointF(dx4, dy4) )

        painter.drawRect( dx3 + 1, self.baseY + s.vCellPadding,
                          self.minWidth - 2 * s.hCellPadding - self.__diamondDiagonal,
                          self.minHeight - 2 * s.vCellPadding )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        availWidth = self.minWidth - 2 * s.hCellPadding - self.__diamondDiagonal
        textWidth = self.__textRect.width() + 2 * s.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText( dx3 + s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
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

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
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
        self.arrowItem.setPos( baseX + s.hCellPadding + s.hTextPadding,
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
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + self.height )

        pen = QPen( getDarkerColor( s.boxBGColor ) )
        painter.setPen( pen )
        painter.drawRect( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.minWidth - 2 * s.hCellPadding,
                          self.height - 2 * s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding + self.__arrowWidth + 2 * s.hTextPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + self.__arrowWidth + 2 * s.hTextPadding,
                          self.baseY + self.height - s.vCellPadding )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        textRectWidth = self.minWidth - 2 * s.hCellPadding - 4 * s.hTextPadding - self.__arrowWidth
        textShift = ( textRectWidth - self.__textRect.width() ) / 2
        painter.drawText( self.baseX + s.hCellPadding + self.__arrowWidth + 3 * s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft,
                          self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return



class IfCell( CellElement, QGraphicsRectItem ):
    " Represents a single if statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.IF
        self.__text = None
        self.__textRect = None

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                          self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding + 2 * s.ifWidth,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setRect( baseX, baseY, self.width, self.height )
        self.setZValue( TOP_Z )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        painter.setPen( pen )
        brush = QBrush( s.ifBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.drawLine( self.baseX + s.mainLine, self.baseY,
                          self.baseX + s.mainLine, self.baseY + self.height )

        # Draw the main element
        pen = QPen( getDarkerColor( s.ifBGColor ) )
        painter.setPen( pen )

        x1 = self.baseX + s.hCellPadding
        y1 = self.baseY + self.minHeight / 2
        x2 = self.baseX + s.hCellPadding + s.ifWidth
        y2 = self.baseY + s.vCellPadding
        x3 = self.baseX + self.minWidth - s.hCellPadding - s.ifWidth
        y3 = y2
        x4 = x3 + s.ifWidth
        y4 = y1
        x5 = x3
        y5 = self.baseY + (self.minHeight - s.vCellPadding)
        x6 = x2
        y6 = y5
        painter.drawPolygon( QPointF(x1, y1), QPointF(x2, y2),
                             QPointF(x3, y3), QPointF(x4, y4),
                             QPointF(x5, y5), QPointF(x6, y6) )

        # Draw the 'false' connector
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        painter.setPen( pen )
        painter.drawLine( x4, y4, self.baseX + self.width, y4 )
        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        availWidth = x3 - x2
        textWidth = self.__textRect.width() + 2 * s.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText( x2 + s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )

        # Draw the 'n' badge
        pen = QPen( s.lineColor )
        pen.setWidth( 1 )
        painter.setPen( pen )
        painter.setFont( s.badgeFont )
        badgeRect = s.badgeFontMetrics.boundingRect( 0, 0,  maxint, maxint,
                                                     0, 'N' )
        painter.drawText( x4 + 2, y4 - badgeRect.height() - 2,
                          badgeRect.width(), badgeRect.height(),
                          Qt.AlignLeft, 'N' )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.body.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
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
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.INDEPENDENT_COMMENT
        self.__text = None
        self.__textRect = None
        self.leadingForElse = False
        self.sideForElse = False

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
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
        self.minWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def adjustWidth( self ):
        """ Used during rendering to adjust the width of the cell.
            The comment now can take some space on the left and the left hand
            side cell has to be rendered already.
            The width of this cell will take whatever is needed considering
            the comment shift to the left
        """
        s = self.canvas.settings
        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        spareWidth = cellToTheLeft.width - s.mainLine
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth
        return

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setZValue( TOP_Z )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the independent comment "
        s = self.canvas.settings

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        leftEdge = cellToTheLeft.baseX + s.mainLine
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        path = getCommentBoxPath( s, leftEdge, self.baseY, boxWidth, self.minHeight )
        path.moveTo( leftEdge + s.hCellPadding,
                     self.baseY + self.minHeight / 2 )
        if self.leadingForElse:
            path.lineTo( cellToTheLeft.baseX + s.mainLine,
                         self.baseY + self.minHeight / 2 )
#            path.moveTo( self.baseX, self.baseY + self.minHeight / 2 )
#            path.lineTo( cellToTheLeft.baseX + s.mainLine,
#                         self.baseY + self.minHeight )
        else:
            path.lineTo( cellToTheLeft.baseX + s.mainLine,
                         self.baseY + self.minHeight / 2 )

        self.setPath( path )

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )
        self.setPen( pen )

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem( option )
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint( self, painter, itemOption, widget )

        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( leftEdge + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return



class LeadingCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single leading comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.LEADING_COMMENT
        self.__text = None
        self.__textRect = None

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = self.ref.leadingComment.getDisplayValue()
        return self.__text

    def render( self ):
        s = self.canvas.settings
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                          self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def adjustWidth( self ):
        """ Used during rendering to adjust the width of the cell.
            The comment now can take some space on the left and the left hand
            side cell has to be rendered already.
            The width of this cell will take whatever is needed considering
            the comment shift to the left
        """
        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # Not implemented yet
            return

        # Here: there is a connector on the left so we can move the comment
        #       safely
        s = self.canvas.settings
        spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth + s.hCellPadding
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth
        return

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setZValue( TOP_Z )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the leading comment "
        s = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # not implemented yet
            leftEdge = self.baseX
        else:
            leftEdge = cellToTheLeft.baseX + s.mainLine
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )

        path = getCommentBoxPath( s, leftEdge, baseY, boxWidth, self.minHeight )
        path.moveTo( leftEdge + s.hCellPadding,
                     baseY + self.minHeight / 2 )
        path.lineTo( leftEdge + s.hCellPadding / 2,
                     baseY + self.minHeight / 2 )
        # The moveTo() below is required to suppress painting the surface
        path.moveTo( leftEdge + s.hCellPadding / 2,
                     baseY + self.minHeight / 2 )
        path.lineTo( leftEdge,
                     baseY + self.minHeight + s.vCellPadding )
        self.setPath( path )


        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )
        self.setPen( pen )

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem( option )
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint( self, painter, itemOption, widget )

        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( leftEdge + s.hCellPadding + s.hTextPadding,
                          baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.leadingComment.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
        return



class SideCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single side comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.SIDE_COMMENT
        self.__text = None
        self.__textRect = None

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
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
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                          self.__getText() )

        self.minHeight = self.__textRect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = max( self.__textRect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def adjustWidth( self ):
        """ Used during rendering to adjust the width of the cell.
            The comment now can take some space on the left and the left hand
            side cell has to be rendered already.
            The width of this cell will take whatever is needed considering
            the comment shift to the left
        """
        s = self.canvas.settings
        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        if cellToTheLeft.kind == CellElement.CONNECTOR:
            spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth + s.hCellPadding
        else:
            spareWidth = cellToTheLeft.width - cellToTheLeft.minWidth
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        if spareWidth >= boxWidth:
            self.minWidth = 0
        else:
            self.minWidth = boxWidth - spareWidth
        self.width = self.minWidth
        return

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.setZValue( TOP_Z )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the side comment "
        s = self.canvas.settings

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
        if self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ].kind == CellElement.CONNECTOR:
            # 'if' or 'elif' side comment
            leftEdge = cellToTheLeft.baseX + s.mainLine
            path = getCommentBoxPath( s, leftEdge, self.baseY, boxWidth, self.minHeight )

            width = 0
            index = self.addr[ 0 ] - 1
            while self.canvas.cells[ self.addr[ 1 ] ][ index ].kind == CellElement.CONNECTOR:
                width += self.canvas.cells[ self.addr[ 1 ] ][ index ].width
                index -= 1

            # The first non-connector cell must be the 'if' cell
            ifCell = self.canvas.cells[ self.addr[ 1 ] ][ index ]

            path.moveTo( leftEdge + s.hCellPadding,
                         self.baseY + ifCell.minHeight / 2 + 6 )
            path.lineTo( ifCell.baseX + ifCell.minWidth - s.hCellPadding,
                         self.baseY + ifCell.minHeight / 2 + 6 )
        else:
            # Regular box
            leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
            path = getCommentBoxPath( s, leftEdge, self.baseY, boxWidth, self.minHeight )

            h = min( self.minHeight / 2, cellToTheLeft.minHeight / 2 )
            path.moveTo( leftEdge + s.hCellPadding, self.baseY + h )
            path.lineTo( cellToTheLeft.baseX + cellToTheLeft.minWidth - s.hCellPadding,
                         self.baseY + h )

        self.setPath( path )

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )
        self.setPen( pen )

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem( option )
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected
        QGraphicsPathItem.paint( self, painter, itemOption, widget )

        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( leftEdge + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft,
                          self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        line = self.ref.sideComment.beginLine
        if self._editor:
            self._editor.gotoLine( line )
            self._editor.setFocus()
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
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.CONNECTOR
        self.connections = connections
        return

    def __hasVertical( self ):
        for conn in self.connections:
            if self.NORTH in conn or self.SOUTH in conn:
                return True
        return False

    def __hasHorizontal( self ):
        for conn in self.connections:
            if self.EAST in conn or self.WEST in conn:
                return True
        return False

    def render( self ):
        s = self.canvas.settings

        if self.__hasVertical():
            self.minWidth = s.mainLine + s.hCellPadding
        else:
            self.minWidth = 0

        if self.__hasHorizontal():
            self.minHeight = 2 * s.vCellPadding
        else:
            self.minHeight = 0

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __getY( self ):
        row = self.addr[ 1 ]
        column = self.addr[ 0 ]
        cells = self.canvas.cells
        for index in xrange( column - 1, -1, -1 ):
            kind = cells[ row ][ index ].kind
            if kind in [ CellElement.VACANT, CellElement.H_SPACER,
                         CellElement.V_SPACER ]:
                continue
            if kind in [ CellElement.FILE_SCOPE, CellElement.FUNC_SCOPE,
                         CellElement.CLASS_SCOPE, CellElement.FOR_SCOPE,
                         CellElement.WHILE_SCOPE, CellElement.TRY_SCOPE,
                         CellElement.WITH_SCOPE, CellElement.DECOR_SCOPE,
                         CellElement.ELSE_SCOPE, CellElement.EXCEPT_SCOPE,
                         CellElement.FINALLY_SCOPE ]:
                break
            if kind != CellElement.CONNECTOR:
                return cells[ row ][ index ].minHeight / 2
        return self.height / 2

    def __getXY( self, location ):
        s = self.canvas.settings
        if location == self.NORTH:
            return self.baseX + s.mainLine, self.baseY
        if location == self.SOUTH:
            return self.baseX + s.mainLine, self.baseY + self.height
        if location == self.WEST:
            return self.baseX, self.baseY + self.__getY()
        if location == self.EAST:
            return self.baseX + self.width, self.baseY + self.__getY()
        # It is CENTER
        return self.baseX + s.mainLine, self.baseY + self.__getY()

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

