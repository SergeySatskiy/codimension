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
from math import sqrt, atan2, pi, cos, sin
from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QPen, QBrush, QGraphicsRectItem, QGraphicsPathItem,
                          QGraphicsTextItem, QGraphicsItem, QPainterPath,
                          QColor, QPainter )


class CellElement:
    " Base class for all the elements which could be found on the canvas "

    UNKNOWN = -1

    VACANT = 0
    H_SPACER = 1
    V_SPACER = 2

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
        return "Size: " + str( self.width ) + "x" + str( self.height ) + \
               " (" + str( self.minWidth ) + "x" + str( self.minHeight ) + ")"

    def getCanvasTooltip( self ):
        return "Size: " + str( self.canvas.width ) + "x" + str( self.canvas.height ) + \
               " (" + str( self.canvas.minWidth ) + "x" + str( self.canvas.minHeight ) + ")"

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
            startX = self.baseX + s.rectRadius
        if startY is None:
            startY = self.baseY - height / 2
        if needRect:
            brush = QBrush( s.badgeBGColor )
            painter.setBrush( brush )
            painter.drawRoundedRect( startX, startY,
                                     width, height, 2, 2 )
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
            self.minHeight = s.rectRadius
            self.minWidth = s.rectRadius
            if badgeText:
                self._badgeText = badgeText
                self._badgeRect = self.getBadgeBoundingRect( badgeText )
        elif self.subKind == ScopeCellElement.LEFT:
            self.minHeight = 0
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.BOTTOM_LEFT:
            self.minHeight = s.rectRadius
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.TOP:
            self.minHeight = s.rectRadius
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.BOTTOM:
            self.minHeight = s.rectRadius
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.DECLARATION:
            # The declaration location uses a bit of the top cell space
            # to make the view more compact
            self._headerRect = self.getBoundingRect( self._getHeaderText() )
            self.minHeight = self._headerRect.height() + 2 * s.vHeaderPadding - s.rectRadius
            self.minWidth = self._headerRect.width() + s.hHeaderPadding - s.rectRadius
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
                vAdjust = self._badgeRect.height() / 2 + 1
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
            self.setRect( baseX,
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
            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawRoundedRect( self.baseX, self.baseY,
                                     self.canvas.width, self.canvas.height,
                                     s.rectRadius, s.rectRadius )
            if self._badgeText:
                self._paintBadge( painter, option, widget )
        elif self.subKind == ScopeCellElement.DECLARATION:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            yShift = 0
            if hasattr( self.ref, "sideComment" ):
                yShift = s.vTextPadding
            canvasLeft = self.baseX - s.rectRadius
            canvasTop = self.baseY - s.rectRadius
            painter.drawText( canvasLeft + s.hHeaderPadding,
                              canvasTop + s.vHeaderPadding + yShift,
                              int( self._headerRect.width() ),
                              int( self._headerRect.height() ),
                              Qt.AlignLeft, self._getHeaderText() )

            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( canvasLeft, self.baseY + self.height,
                              canvasLeft + self.canvas.width,
                              self.baseY + self.height )
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            canvasTop = self.baseY - s.rectRadius
            path = getNoCellCommentBoxPath( self.baseX + s.hCellPadding,
                                            canvasTop + s.vHeaderPadding,
                                            int( self._sideCommentRect.width() ) + 2 * s.hTextPadding,
                                            int( self._sideCommentRect.height() ) + 2 * s.vTextPadding,
                                            s.commentCorner )
            # Add vertcal separation line
            path.moveTo( self.baseX, canvasTop + s.vHeaderPadding )
            path.lineTo( self.baseX, canvasTop + s.vHeaderPadding +
                                     int( self._sideCommentRect.height() ) +
                                     2 * s.vTextPadding )
            brush = QBrush( s.commentBGColor )
            painter.setBrush( brush )
            pen = QPen( s.commentLineColor )
            pen.setWidth( s.commentLineWidth )
            painter.setPen( pen )
            painter.drawPath( path )

            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
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
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( canvasLeft, self.baseY + self.height,
                              canvasLeft + self.canvas.width,
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
        self.minWidth = self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
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
        painter.drawRect( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.width - 2 * s.hCellPadding,
                          self.height - 2 * s.vCellPadding )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + (self.width - 2 * s.hCellPadding - self.__textRect.width()) / 2,
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        if self.subKind == ScopeCellElement.TOP_LEFT:
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
        s = self.canvas.settings
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
        s = self.canvas.settings
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
        self.minWidth = self.__textRect.width() + 2 * (s.hCellPadding + s.hTextPadding)
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
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
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.width - 2 * s.hCellPadding,
                                 self.height - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )

        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + (self.width - 2 * s.hCellPadding - self.__textRect.width()) / 2,
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
        self.__arrowWidth = None
        self.__arrowHeight = None
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
        singleCharRect = s.monoFontMetrics.tightBoundingRect( 'W' )
        self.__arrowHeight = singleCharRect.height()
        self.__arrowWidth = self.__arrowHeight

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding + \
                        2 * s.returnRectRadius + self.__arrowWidth
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
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
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height / 2 )
        painter.drawRoundedRect( self.baseX + s.hCellPadding,
                                 self.baseY + s.vCellPadding,
                                 self.width - 2 * s.hCellPadding,
                                 self.height - 2 * s.vCellPadding,
                                 s.returnRectRadius, s.returnRectRadius )
        painter.drawLine( self.baseX + s.hCellPadding + s.returnRectRadius + self.__arrowWidth + s.hTextPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + s.returnRectRadius + self.__arrowWidth + s.hTextPadding,
                          self.baseY + self.height - s.vCellPadding )

        # Draw the arrow
        beginX = self.baseX + s.hCellPadding + s.returnRectRadius
        beginY = self.baseY + self.height / 2 + self.__arrowHeight / 2
        endX = beginX + self.__arrowWidth
        endY = beginY - self.__arrowHeight
        painter.drawLine( beginX, beginY, endX, endY )

        angle = atan2( beginY - endY, beginX - endX )
        cosy = cos( angle )
        siny = sin( angle )
        painter.setRenderHints( QPainter.Antialiasing )
        painter.drawLine( endX, endY,
                          endX + int( s.arrowLength * cosy - ( s.arrowLength / 2.0 * siny ) ),
                          endY + int( s.arrowLength * siny + ( s.arrowLength / 2.0 * cosy ) ) )
        painter.drawLine( endX, endY,
                          endX + int( s.arrowLength * cosy + s.arrowLength / 2.0 * siny ),
                          endY - int( s.arrowLength / 2.0 * cosy - s.arrowLength * siny ) )


        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( endX + 2 * s.hTextPadding,
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
        self.minWidth = rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding + \
                        self.__diamondDiagonal
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
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
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )

        dHalf = int( self.__diamondDiagonal / 2.0 )
        dx1 = self.baseX + s.hCellPadding
        dy1 = self.baseY + int( self.height / 2 )
        dx2 = dx1 + dHalf
        dy2 = dy1 - dHalf
        dx3 = dx1 + 2 * dHalf
        dy3 = dy1
        dx4 = dx2
        dy4 = dy2 + 2 * dHalf
        painter.drawLine( dx1, dy1, dx2, dy2 )
        painter.drawLine( dx2, dy2, dx3, dy3 )
        painter.drawLine( dx3, dy3, dx4, dy4 )
        painter.drawLine( dx4, dy4, dx1, dy1 )

        painter.drawRect( dx3 + 1, self.baseY + s.vCellPadding,
                          self.width - 2 * s.hCellPadding - self.__diamondDiagonal,
                          self.height - 2 * s.vCellPadding )

        # Draw the arrow
#        beginX = self.baseX + s.hCellPadding + s.returnRectRadius
#        beginY = self.baseY + self.height / 2 + self.__arrowHeight / 2
#        endX = beginX + self.__arrowWidth
#        endY = beginY - self.__arrowHeight
#        painter.drawLine( beginX, beginY, endX, endY )

#        angle = atan2( beginY - endY, beginX - endX )
#        cosy = cos( angle )
#        siny = sin( angle )
#        painter.setRenderHints( QPainter.Antialiasing )
#        painter.drawLine( endX, endY,
#                          endX + int( s.arrowLength * cosy - ( s.arrowLength / 2.0 * siny ) ),
#                          endY + int( s.arrowLength * siny + ( s.arrowLength / 2.0 * cosy ) ) )
#        painter.drawLine( endX, endY,
#                          endX + int( s.arrowLength * cosy + s.arrowLength / 2.0 * siny ),
#                          endY - int( s.arrowLength / 2.0 * cosy - s.arrowLength * siny ) )


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
        self.__arrowWidth = None
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
                                                         0, 'ww' )
        self.__arrowWidth = singleCharRect.width() + 2 * s.hTextPadding

        self.minHeight = rect.height() + 2 * s.vCellPadding + 2 * s.vTextPadding
        self.minWidth = rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding + \
                        self.__arrowWidth
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
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
        painter.setPen( pen )
        brush = QBrush( s.boxBGColor )
        painter.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )
        painter.drawRect( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.width - 2 * s.hCellPadding,
                          self.height - 2 * s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding + self.__arrowWidth,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + self.__arrowWidth,
                          self.baseY + self.height - s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + self.height / 2,
                          self.baseX + s.hCellPadding + self.__arrowWidth - s.hTextPadding,
                          self.baseY + self.height / 2 )
        painter.drawLine( self.baseX + s.hCellPadding + self.__arrowWidth - s.hTextPadding,
                          self.baseY + self.height / 2,
                          self.baseX + s.hCellPadding + self.__arrowWidth - s.hTextPadding - s.arrowLength,
                          self.baseY + self.height / 2 - s.arrowWidth )
        painter.drawLine( self.baseX + s.hCellPadding + self.__arrowWidth - s.hTextPadding,
                          self.baseY + self.height / 2,
                          self.baseX + s.hCellPadding + self.__arrowWidth - s.hTextPadding - s.arrowLength,
                          self.baseY + self.height / 2 + s.arrowWidth )


        # Draw the text in the rectangle
        pen = QPen( s.boxFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + self.__arrowWidth + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * s.hTextPadding,
                          int( self.rect().height() ) - 2 * s.vTextPadding,
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
        s = self.canvas.settings
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

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        path = getCommentBoxPath( s, self.baseX, self.baseY, self.width, self.height )
        path.moveTo( self.baseX + s.hCellPadding,
                     self.baseY + self.height / 2 )
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
        " Draws the leading comment "
        s = self.canvas.settings

        cellToTheLeft = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ]
        path = getCommentBoxPath( s, self.baseX, self.baseY, self.width, self.height )
        path.moveTo( self.baseX + s.hCellPadding,
                     self.baseY + self.height / 2 )
        path.lineTo( self.baseX - cellToTheLeft.width / 4,
                     self.baseY + self.height / 2 )
        # The moveTo() below is required to suppress painting the surface
        path.moveTo( self.baseX - cellToTheLeft.width / 4,
                     self.baseY + self.height / 2 )
        path.lineTo( self.baseX - cellToTheLeft.width / 3,
                     self.baseY + self.height + s.vCellPadding )
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
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          self.width - 2 * (s.hCellPadding + s.hTextPadding),
                          self.height - 2 * (s.vCellPadding + s.vTextPadding),
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

        path = getCommentBoxPath( s, self.baseX, self.baseY, self.width, self.height )
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
        s = self.canvas.settings

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


