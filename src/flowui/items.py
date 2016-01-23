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

" Various items used to represent a control flow on a virtual canvas "

from sys import maxint
from math import sqrt
import os.path
from PyQt4.QtCore import Qt, QPointF
from PyQt4.QtGui import ( QPen, QBrush, QGraphicsRectItem, QGraphicsPathItem,
                          QPainterPath, QPainter, QColor, QGraphicsItem,
                          QStyleOptionGraphicsItem, QStyle, QFont,
                          QGraphicsSimpleTextItem )
from PyQt4.QtSvg import QGraphicsSvgItem
from auxitems import SVGItem, Connector, Text



def getDarkerColor( color ):
    r = color.red() - 40
    g = color.green() - 40
    b = color.blue() - 40
    return QColor( max( r, 0 ), max( g, 0 ), max( b, 0 ), color.alpha() )



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
    ABOVE_COMMENT = 212

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
            if canvas.isNoScope == False:
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

    def scopedItem( self ):
        return False

    def isProxyItem( self ):
        return False

    def getProxiedItem( self ):
        return None



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
    CellElement.ABOVE_COMMENT:          "ABOVE_COMMENT",
    CellElement.CONNECTOR:              "CONNECTOR",
}


def kindToString( kind ):
    " Provides a string representation of a element kind "
    return __kindToString[ kind ]




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
        self.connector = None

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

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine,
                                    baseY + self.height )
        scene.addItem( self.connector )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = s.selectPenWidth - 1
        self.setRect( baseX + s.hCellPadding - penWidth,
                      baseY + s.vCellPadding - penWidth,
                      self.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                      self.minHeight - 2 * s.vCellPadding + 2 * penWidth )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        rectWidth = self.minWidth - 2 * s.hCellPadding
        rectHeight = self.minHeight - 2 * s.vCellPadding

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.boxBGColor ) )
            painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )
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
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.body.getLineRange()
        return "Code block at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )



class BreakCell( CellElement, QGraphicsRectItem ):
    " Represents a single break statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.BREAK
        self.__textRect = None
        self.__vSpacing = 0
        self.__hSpacing = 4
        self.connector = None

        # Cache for the size
        x1 = None
        y1 = None
        w = None
        h = None

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( "break" )
        self.minHeight = self.__textRect.height() + 2 * (self.__vSpacing + s.vCellPadding)
        self.minWidth = self.__textRect.width() + 2 * (self.__hSpacing + s.hCellPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize( self ):
        s = self.canvas.settings
        self.x1 = self.baseX + s.hCellPadding
        self.y1 = self.baseY + s.vCellPadding
        self.w = 2 * self.__hSpacing + self.__textRect.width()
        self.h = 2 * self.__vSpacing + self.__textRect.height()
        return

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + s.vCellPadding )
        scene.addItem( self.connector )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = s.selectPenWidth - 1
        self.__calculateSize()
        self.setRect( self.x1 - penWidth, self.y1 - penWidth,
                      self.w + 2 * penWidth, self.h + 2 * penWidth )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the break statement "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.breakBGColor ) )
            painter.setPen( pen )

        brush = QBrush( s.breakBGColor )
        painter.setBrush( brush )

        painter.drawRoundedRect( self.x1, self.y1, self.w, self.h, 2, 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.x1 + self.__hSpacing, self.y1 + self.__vSpacing,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, "break" )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.body.getLineRange()
        return "Break at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )


class ContinueCell( CellElement, QGraphicsRectItem ):
    " Represents a single continue statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.CONTINUE
        self.__textRect = None
        self.__vSpacing = 0
        self.__hSpacing = 4
        self.connector = None

        # Cache for the size
        x1 = None
        y1 = None
        w = None
        h = None

        # To make double click delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, True )
        return

    def render( self ):
        s = self.canvas.settings
        self.__textRect = self.getBoundingRect( "continue" )
        self.minHeight = self.__textRect.height() + 2 * (self.__vSpacing + s.vCellPadding)
        self.minWidth = self.__textRect.width() + 2 * (self.__hSpacing + s.hCellPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def __calculateSize( self ):
        s = self.canvas.settings
        self.x1 = self.baseX + s.hCellPadding
        self.y1 = self.baseY + s.vCellPadding
        self.w = 2 * self.__hSpacing + self.__textRect.width()
        self.h = 2 * self.__vSpacing + self.__textRect.height()
        return

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + s.vCellPadding )
        scene.addItem( self.connector )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = s.selectPenWidth - 1
        self.__calculateSize()
        self.setRect( self.x1 - penWidth, self.y1 - penWidth,
                      self.w + 2 * penWidth, self.h + 2 * penWidth )

        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the break statement "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.continueBGColor ) )
            painter.setPen( pen )

        brush = QBrush( s.continueBGColor )
        painter.setBrush( brush )

        painter.drawRoundedRect( self.x1, self.y1, self.w, self.h, 2, 2 )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.x1 + self.__hSpacing, self.y1 + self.__vSpacing,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, "continue" )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.body.getLineRange()
        return "Continue at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )


class ReturnCell( CellElement, QGraphicsRectItem ):
    " Represents a single return statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.RETURN
        self.__text = None
        self.__textRect = None
        self.__arrowWidth = 16
        self.connector = None

        self.arrowItem = SVGItem( "return.svgz", self )
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

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + s.vCellPadding )


        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = s.selectPenWidth - 1
        self.setRect( baseX + s.hCellPadding - penWidth,
                      baseY + s.vCellPadding - penWidth,
                      self.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                      self.minHeight - 2 * s.vCellPadding + 2 * penWidth )

        self.arrowItem.setPos( baseX + s.hCellPadding + s.hTextPadding,
                               baseY + self.minHeight/2 - self.arrowItem.height()/2 )

        scene.addItem( self.connector )
        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.boxBGColor ) )
            painter.setPen( pen )

        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )
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
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        beginLine = self.ref.body.beginLine
        if self.ref.value is not None:
            endLine = self.ref.value.endLine
        else:
            endLine = self.ref.body.endLine
        return "Return at lines " + str( beginLine ) + "-" + str( endLine )



class RaiseCell( CellElement, QGraphicsRectItem ):
    " Represents a single raise statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.RAISE
        self.__text = None
        self.__textRect = None
        self.__arrowWidth = 16

        self.arrowItem = SVGItem( "raise.svg", self )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "raise" )
        self.connector = None

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

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + s.vCellPadding )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = s.selectPenWidth - 1
        self.setRect( baseX + s.hCellPadding - penWidth,
                      baseY + s.vCellPadding - penWidth,
                      self.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                      self.minHeight - 2 * s.vCellPadding + 2 * penWidth )

        self.arrowItem.setPos( baseX + s.hCellPadding + s.hTextPadding,
                               baseY + self.minHeight/2 - self.arrowItem.height()/2 )

        scene.addItem( self.connector )
        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.boxBGColor ) )
            painter.setPen( pen )

        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )
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
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        beginLine = self.ref.body.beginLine
        if self.ref.value is not None:
            endLine = self.ref.value.endLine
        else:
            endLine = self.ref.body.endLine
        return "Raise at lines " + str( beginLine ) + "-" + str( endLine )




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
        self.connector = None

        self.arrowItem = SVGItem( "assert.svg", self )
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

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + self.height )
        scene.addItem( self.connector )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = s.selectPenWidth - 1
        self.setRect( baseX + s.hCellPadding - penWidth,
                      baseY + s.vCellPadding - penWidth,
                      self.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                      self.minHeight - 2 * s.vCellPadding + 2 * penWidth )

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

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( selectPen )
        else:
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

        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )
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
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        beginLine = self.ref.body.beginLine
        if self.ref.message is not None:
            endLine = self.ref.message.endLine
        elif self.ref.test is not None:
            endLine = self.ref.test.endLine
        else:
            endLine = self.ref.body.endLine
        return "Assert at lines " + str( beginLine ) + "-" + str( endLine )



class SysexitCell( CellElement, QGraphicsRectItem ):
    " Represents a single sys.exit(...) statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.SYSEXIT
        self.__text = None
        self.__textRect = None
        self.__xWidth = 16
        self.connector = None

        self.xItem = SVGItem( "sysexit.svgz", self )
        self.xItem.setWidth( self.__xWidth )
        self.xItem.setToolTip( "sys.exit()" )

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
                             s.returnRectRadius + 2 * s.hTextPadding + self.__xWidth,
                             s.minWidth )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + s.vCellPadding )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen with must be considered too.
        penWidth = s.selectPenWidth - 1
        self.setRect( baseX + s.hCellPadding - penWidth,
                      baseY + s.vCellPadding - penWidth,
                      self.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                      self.minHeight - 2 * s.vCellPadding + 2 * penWidth )

        self.xItem.setPos( baseX + s.hCellPadding + s.hTextPadding,
                           baseY + self.minHeight/2 - self.xItem.height()/2 )

        scene.addItem( self.connector )
        scene.addItem( self )
        scene.addItem( self.xItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.boxBGColor ) )
            painter.setPen( pen )

        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.minWidth - 2 * s.hCellPadding,
                                 self.minHeight - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.__xWidth + 2 * s.hTextPadding,
                                 self.minHeight - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        availWidth = self.minWidth - 2 * s.hCellPadding - self.__xWidth - 2 * s.hTextPadding - s.hTextPadding - s.returnRectRadius
        textShift = (availWidth - self.__textRect.width()) / 2
        painter.drawText( self.baseX + s.hCellPadding + self.__xWidth + 3 * s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.body.getLineRange()
        return "Sys.exit() at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )



class ImportCell( CellElement, QGraphicsRectItem ):
    " Represents a single import statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.IMPORT
        self.__text = None
        self.__arrowWidth = 16
        self.__textRect = None
        self.arrowItem = SVGItem( "import.svgz", self )
        self.arrowItem.setWidth( self.__arrowWidth )
        self.arrowItem.setToolTip( "import" )
        self.connector = None

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

        # Add the connector as a separate scene item to make the selection
        # working properly
        s = self.canvas.settings
        self.connector = Connector( s, baseX + s.mainLine, baseY,
                                    baseX + s.mainLine, baseY + self.height )
        scene.addItem( self.connector )

        # Setting the rectangle is important for the selection and for
        # redrawing. Thus the selection pen must be considered too.
        penWidth = s.selectPenWidth - 1
        self.setRect( baseX + s.hCellPadding - penWidth,
                      baseY + s.vCellPadding - penWidth,
                      self.minWidth - 2 * s.hCellPadding + 2 * penWidth,
                      self.minHeight - 2 * s.vCellPadding + 2 * penWidth )

        self.arrowItem.setPos( baseX + s.hCellPadding + s.hTextPadding,
                               baseY + self.minHeight/2 - self.arrowItem.height()/2 )
        scene.addItem( self )
        scene.addItem( self.arrowItem )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.boxBGColor ) )
            painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )
        painter.drawRect( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.minWidth - 2 * s.hCellPadding,
                          self.minHeight - 2 * s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding + self.__arrowWidth + 2 * s.hTextPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + self.__arrowWidth + 2 * s.hTextPadding,
                          self.baseY + self.minHeight - s.vCellPadding )

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
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.body.getLineRange()
        return "Import at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )



class IfCell( CellElement, QGraphicsRectItem ):
    " Represents a single if statement "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.IF
        self.__text = None
        self.__textRect = None
        self.vConnector = None
        self.hConnector = None
        self.rightLabel = None

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

    def __calcPolygon( self ):
        s = self.canvas.settings

        self.x1 = self.baseX + s.hCellPadding
        self.y1 = self.baseY + self.minHeight / 2
        self.x2 = self.baseX + s.hCellPadding + s.ifWidth
        self.y2 = self.baseY + s.vCellPadding
        self.x3 = self.baseX + self.minWidth - s.hCellPadding - s.ifWidth
        self.y3 = self.y2
        self.x4 = self.x3 + s.ifWidth
        self.y4 = self.y1
        self.x5 = self.x3
        self.y5 = self.baseY + (self.minHeight - s.vCellPadding)
        self.x6 = self.x2
        self.y6 = self.y5
        return

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY

        self.__calcPolygon()

        # Add the connectors as separate scene items to make the selection
        # working properly
        s = self.canvas.settings
        self.vConnector = Connector( s, baseX + s.mainLine, baseY,
                                     baseX + s.mainLine,
                                     baseY + self.height )
        scene.addItem( self.vConnector )

        self.hConnector = Connector( s, self.x4, self.y4,
                                     self.baseX + self.width,
                                     self.y4 )
        scene.addItem( self.hConnector )

        self.rightLabel = Text( s, "N" )
        self.rightLabel.setPos( self.x4 + 2,
                                self.y4 - self.rightLabel.boundingRect().height() - 2 )
        scene.addItem( self.rightLabel )

        penWidth = s.selectPenWidth - 1
        self.setRect( self.x1 - penWidth, self.y2 - penWidth,
                      self.x4 - self.x1 + 2 * penWidth,
                      self.y6 - self.y2 + 2 * penWidth )
        scene.addItem( self )
        return


    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( selectPen )
        else:
            pen = QPen( getDarkerColor( s.ifBGColor ) )
            pen.setJoinStyle( Qt.RoundJoin )
            painter.setPen( pen )

        brush = QBrush( s.ifBGColor )
        painter.setBrush( brush )
        painter.drawPolygon( QPointF(self.x1, self.y1), QPointF(self.x2, self.y2),
                             QPointF(self.x3, self.y3), QPointF(self.x4, self.y4),
                             QPointF(self.x5, self.y5), QPointF(self.x6, self.y6) )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setPen( pen )
        painter.setFont( s.monoFont )
        availWidth = self.x3 - self.x2
        textWidth = self.__textRect.width() + 2 * s.hTextPadding
        textShift = (availWidth - textWidth) / 2
        painter.drawText( self.x2 + s.hTextPadding + textShift,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.body.beginLine,
                                   self.ref.body.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.body.getLineRange()
        return "If at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )


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
    path.lineTo( x + width, y + corner )
    path.lineTo( x + width,  y + height )
    path.lineTo( x, y + height )
    path.lineTo( x, y )

    # -1 is to avoid sharp corners of the lines
    path.moveTo( x + width - corner, y + 1 )
    path.lineTo( x + width - corner, y + corner )
    path.lineTo( x + width - 1, y + corner )
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
        self.__leftEdge = None
        self.connector = None

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
        spareWidth = cellToTheLeft.width - s.mainLine - s.hCellPadding
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
        self.__setupPath()
        scene.addItem( self.connector )
        scene.addItem( self )
        return

    def __setupPath( self ):
        " Sets the path for painting "
        s = self.canvas.settings

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        self.__leftEdge = cellToTheLeft.baseX + s.mainLine + s.hCellPadding
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        path = getCommentBoxPath( s, self.__leftEdge, self.baseY, boxWidth, self.minHeight )
        self.setPath( path )

        # May be later the connector will look different for two cases below
        if self.leadingForElse:
            self.connector = Connector( s, self.__leftEdge + s.hCellPadding,
                                        self.baseY + self.minHeight / 2,
                                        cellToTheLeft.baseX + s.mainLine,
                                        self.baseY + self.minHeight / 2 )
        else:
            self.connector = Connector( s, self.__leftEdge + s.hCellPadding,
                                        self.baseY + self.minHeight / 2,
                                        cellToTheLeft.baseX + s.mainLine,
                                        self.baseY + self.minHeight / 2 )
        self.connector.penColor = s.commentLineColor
        self.connector.penWidth = s.commentLineWidth
        return

    def paint( self, painter, option, widget ):
        " Draws the independent comment "
        s = self.canvas.settings

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            self.setPen( selectPen )
        else:
            pen = QPen( s.commentLineColor )
            pen.setWidth( s.commentLineWidth )
            pen.setJoinStyle( Qt.RoundJoin )
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
        painter.drawText( self.__leftEdge + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.beginLine,
                                   self.ref.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.getLineRange()
        return "Independent comment at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )


class LeadingCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single leading comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.LEADING_COMMENT
        self.__text = None
        self.__textRect = None
        self.__leftEdge = None
        self.connector = None

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
        self.__setupPath()
        scene.addItem( self.connector )
        scene.addItem( self )
        return

    def __setupPath( self ):
        " Sets the comment path "
        s = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        if cellToTheLeft.kind != CellElement.CONNECTOR:
            # not implemented yet
            self.__leftEdge = self.baseX
        else:
            self.__leftEdge = cellToTheLeft.baseX + s.mainLine + s.hCellPadding
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )

        path = getCommentBoxPath( s, self.__leftEdge, baseY, boxWidth, self.minHeight )
        self.setPath( path )

        self.connector = Connector( s, 0, 0, 0, 0 )
        connectorPath = QPainterPath()
        connectorPath.moveTo( self.__leftEdge + s.hCellPadding,
                              baseY + self.minHeight / 2 )
        connectorPath.lineTo( self.__leftEdge,
                              baseY + self.minHeight / 2 )
        connectorPath.lineTo( self.__leftEdge - s.hCellPadding,
                              baseY + self.minHeight + s.vCellPadding )
        self.connector.setPath( connectorPath )
        self.connector.penColor = s.commentLineColor
        self.connector.penWidth = s.commentLineWidth
        return

    def paint( self, painter, option, widget ):
        " Draws the leading comment "
        s = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            self.setPen( selectPen )
        else:
            pen = QPen( s.commentLineColor )
            pen.setWidth( s.commentLineWidth )
            pen.setJoinStyle( Qt.RoundJoin )
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
        painter.drawText( self.__leftEdge + s.hCellPadding + s.hTextPadding,
                          baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.leadingComment.beginLine,
                                   self.ref.leadingComment.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.leadingComment.getLineRange()
        return "Leading comment at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )


class SideCommentCell( CellElement, QGraphicsPathItem ):
    " Represents a single side comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.SIDE_COMMENT
        self.__text = None
        self.__textRect = None
        self.__leftEdge = None
        self.connector = None

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
        self.__setupPath()
        scene.addItem( self.connector )
        scene.addItem( self )
        return

    def __setupPath( self ):
        " Sets the comment path "
        s = self.canvas.settings

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )
        self.__leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
        if self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ].kind == CellElement.CONNECTOR:
            # 'if' or 'elif' side comment
            self.__leftEdge = cellToTheLeft.baseX + s.mainLine + s.hCellPadding
            path = getCommentBoxPath( s, self.__leftEdge, self.baseY, boxWidth, self.minHeight )

            width = 0
            index = self.addr[ 0 ] - 1
            while self.canvas.cells[ self.addr[ 1 ] ][ index ].kind == CellElement.CONNECTOR:
                width += self.canvas.cells[ self.addr[ 1 ] ][ index ].width
                index -= 1

            # The first non-connector cell must be the 'if' cell
            ifCell = self.canvas.cells[ self.addr[ 1 ] ][ index ]

            self.connector = Connector( s,
                                        self.__leftEdge + s.hCellPadding,
                                        self.baseY + ifCell.minHeight / 2 + 6,
                                        ifCell.baseX + ifCell.minWidth - s.hCellPadding,
                                        self.baseY + ifCell.minHeight / 2 + 6 )
        else:
            # Regular box
            self.__leftEdge = cellToTheLeft.baseX + cellToTheLeft.minWidth
            path = getCommentBoxPath( s, self.__leftEdge, self.baseY, boxWidth, self.minHeight )

            h = min( self.minHeight / 2, cellToTheLeft.minHeight / 2 )

            self.connector = Connector( s,
                                        self.__leftEdge + s.hCellPadding,
                                        self.baseY + h,
                                        cellToTheLeft.baseX + cellToTheLeft.minWidth - s.hCellPadding,
                                        self.baseY + h )

        self.connector.penColor = s.commentLineColor
        self.connector.penWidth = s.commentLineWidth

        self.setPath( path )
        return

    def paint( self, painter, option, widget ):
        " Draws the side comment "
        s = self.canvas.settings

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            self.setPen( selectPen )
        else:
            pen = QPen( s.commentLineColor )
            pen.setWidth( s.commentLineWidth )
            pen.setJoinStyle( Qt.RoundJoin )
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
        painter.drawText( self.__leftEdge + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.sideComment.beginLine,
                                   self.ref.sideComment.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.sideComment.getLineRange()
        return "Side comment at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )



class AboveCommentCell( CellElement, QGraphicsPathItem ):
    """ Represents a single leading comment which is above a certain block, namely
        try/except or for/else or while/else
        i.e. those which are scopes located in a single row """

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsPathItem.__init__( self )
        self.kind = CellElement.ABOVE_COMMENT
        self.__text = None
        self.__textRect = None
        self.__leftEdge = None
        self.needConnector = False
        self.connector = None
        self.commentConnector = None

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

        self.minHeight = self.__textRect.height() + 2 * (s.vCellPadding + s.vTextPadding)
        # Width of the comment box itself
        self.minWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                             s.minWidth )
        # Add the connector space
        self.minWidth += s.mainLine + s.hCellPadding

        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        self.__setupPath()

        if self.needConnector:
            s = self.canvas.settings
            self.connector = Connector( s, baseX + s.mainLine, baseY,
                                        baseX + s.mainLine,
                                        baseY + self.height )
            scene.addItem( self.connector )

        scene.addItem( self.commentConnector )
        scene.addItem( self )
        return

    def __setupPath( self ):
        " Sets the comment path "
        s = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        self.__leftEdge = self.baseX + s.mainLine + s.hCellPadding
        boxWidth = max( self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding),
                        s.minWidth )

        path = getCommentBoxPath( s, self.__leftEdge, baseY, boxWidth, self.minHeight )
        self.setPath( path )

        self.commentConnector = Connector( s, 0, 0, 0, 0 )
        connectorPath = QPainterPath()
        connectorPath.moveTo( self.__leftEdge + s.hCellPadding,
                              baseY + self.minHeight / 2 )
        connectorPath.lineTo( self.__leftEdge,
                              baseY + self.minHeight / 2 )
        connectorPath.lineTo( self.__leftEdge - s.hCellPadding,
                              baseY + self.minHeight + s.vCellPadding )
        self.commentConnector.setPath( connectorPath )
        self.commentConnector.penColor = s.commentLineColor
        self.commentConnector.penWidth = s.commentLineWidth
        return

    def paint( self, painter, option, widget ):
        " Draws the leading comment "
        s = self.canvas.settings

        # Bottom adjustment
        yShift = self.height - self.minHeight
        baseY = self.baseY + yShift

        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )
        if self.isSelected():
            selectPen = QPen( s.selectColor )
            selectPen.setWidth( s.selectPenWidth )
            selectPen.setJoinStyle( Qt.RoundJoin )
            self.setPen( selectPen )
        else:
            pen = QPen( s.commentLineColor )
            pen.setWidth( s.commentLineWidth )
            pen.setJoinStyle( Qt.RoundJoin )
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
        painter.drawText( self.__leftEdge + s.hCellPadding + s.hTextPadding,
                          baseY + s.vCellPadding + s.vTextPadding,
                          self.__textRect.width(), self.__textRect.height(),
                          Qt.AlignLeft, self.__getText() )
        return

    def setEditor( self, editor ):
        " Provides the editor counterpart "
        self._editor = editor

    def mouseDoubleClickEvent( self, event ):
        " Jump to the appropriate line in the text editor "
        if self._editor:
            self._editor.gotoLine( self.ref.leadingComment.beginLine,
                                   self.ref.leadingComment.beginPos )
            self._editor.setFocus()
        return

    def getSelectTooltip( self ):
        lineRange = self.ref.leadingComment.getLineRange()
        return "Leading comment at lines " + str( lineRange[0] ) + "-" + str( lineRange[1] )



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
        pen.setJoinStyle( Qt.RoundJoin )
        self.setPen( pen )
        painter.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )
        return

