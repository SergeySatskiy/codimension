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
from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QPen, QBrush, QGraphicsRectItem, QGraphicsPathItem,
                          QGraphicsTextItem, QGraphicsItem, QPainterPath )


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


class ScopeCellElement( CellElement ):

    UNKNOWN = -1

    TOP_LEFT = 0
    LEFT = 1
    BOTTOM_LEFT = 2
    DECLARATION = 3
    SIDE_COMMENT = 4
    LEADING_COMMENT = 5
    DOCSTRING = 6
    TOP = 7
    BOTTOM = 8

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        self.subKind = self.UNKNOWN
        self.docstringText = None
        return

    def getDocstringText( self ):
        if self.docstringText is None:
            self.docstringText = self.ref.docstring.getDisplayValue()
        return self.docstringText

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
    ScopeCellElement.LEADING_COMMENT:   "LEADING_COMMENT",
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
        self.__textRect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint,
                                                          0, self.__getText() )

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
        self.__headerText = None
        return

    def __getHeaderText( self ):
        if self.__headerText is None:
            if self.ref.encodingLine:
                self.__headerText = "Encoding: " + self.ref.encodingLine.getDisplayValue()
            else:
                self.__headerText = "Encoding: not specified"
            if self.ref.bangLine:
                self.__headerText += "\nBang line: " + self.ref.bangLine.getDisplayValue()
            else:
                self.__headerText += "\nBang line: not specified"
        return self.__headerText

    def render( self ):
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception( "Unknown file scope element" )
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.minHeight = s.rectRadius
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.LEFT:
            self.minHeight = 0
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.BOTTOM_LEFT:
            self.minHeight = s.rectRadius
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.DECLARATION:
            rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                   self.__getHeaderText() )
            self.minHeight = rect.height() + 2 * s.vHeaderPadding
            self.minWidth = rect.width() + 2 * s.vHeaderPadding
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            raise Exception( "Side comment is not supported for a file scope" )
        elif self.subKind == ScopeCellElement.LEADING_COMMENT:
            raise Exception( "Leading comment is not supported for a file scope" )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                   self.getDocstringText() )
            self.minHeight = rect.height() + 2 * s.vHeaderPadding
            self.minWidth = rect.width() + 2 * s.vHeaderPadding
        elif self.subKind == ScopeCellElement.TOP:
            self.minHeight = s.rectRadius
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.BOTTOM:
            self.minHeight = s.rectRadius
            self.minWidth = 0
        else:
            raise Exception( "Unrecognized file scope element: " +
                             str( self.subKind ) )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        if self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception( "Unknown file scope element" )

        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            # Draw the scope rounded rectangle when we see the top left corner
            self.setRect( baseX, baseY, self.canvas.width, self.canvas.height )
            scene.addItem( self )
            self.canvas.scopeRectangle = self
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.setRect( baseX, baseY, self.width, self.height )
            scene.addItem( self )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.setRect( baseX, baseY, self.width, self.height )
            scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.subKind == ScopeCellElement.TOP_LEFT:
            brush = QBrush( s.fileScopeBGColor )
            painter.setBrush( brush )
            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawRoundedRect( self.baseX, self.baseY, self.canvas.width, self.canvas.height,
                                     s.rectRadius, s.rectRadius )
        elif self.subKind == ScopeCellElement.DECLARATION:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( self.baseX + s.hHeaderPadding,
                              self.baseY + s.vHeaderPadding,
                              int( self.rect().width() ) - 2 * s.hHeaderPadding,
                              int( self.rect().height() ) - 2 * s.vHeaderPadding,
                              Qt.AlignLeft,
                              self.__getHeaderText() )

            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( self.baseX - s.rectRadius, self.baseY + self.height,
                              self.baseX - s.rectRadius + self.canvas.width,
                              self.baseY + self.height )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( self.baseX + s.hHeaderPadding,
                              self.baseY + s.vHeaderPadding,
                              int( self.rect().width() ) - 2 * s.hHeaderPadding,
                              int( self.rect().height() ) - 2 * s.vHeaderPadding,
                              Qt.AlignLeft,
                              self.getDocstringText() )

            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( self.baseX - s.rectRadius, self.baseY + self.height,
                              self.baseX - s.rectRadius + self.canvas.width,
                              self.baseY + self.height )
        return



class FunctionScopeCell( ScopeCellElement, QGraphicsRectItem ):
    " Represents a function scope element "

    def __init__( self, ref, canvas, x, y, kind ):
        ScopeCellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self )
        self.kind = CellElement.FUNC_SCOPE
        self.subKind = kind
        self.__headerText = None
        return

    def __getHeaderText( self ):
        if self.__headerText is None:
            self.__headerText = "TTTTTTT"
        return self.__headerText

    def render( self ):
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception( "Unknown file scope element" )
        if self.subKind == ScopeCellElement.TOP_LEFT:
            self.minHeight = s.rectRadius
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.LEFT:
            self.minHeight = 0
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.BOTTOM_LEFT:
            self.minHeight = s.rectRadius
            self.minWidth = s.rectRadius
        elif self.subKind == ScopeCellElement.DECLARATION:
            rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                   self.__getHeaderText() )
            self.minHeight = rect.height() + 2 * s.vHeaderPadding
            self.minWidth = rect.width() + 2 * s.vHeaderPadding
        elif self.subKind == ScopeCellElement.SIDE_COMMENT:
            raise Exception( "Side comment has not been implemented yet" )
        elif self.subKind == ScopeCellElement.LEADING_COMMENT:
            raise Exception( "Leading comment has not been implemented yet" )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            rect = s.monoFontMetrics.boundingRect( 0, 0, maxint, maxint, 0,
                                                   self.getDocstringText() )
            self.minHeight = rect.height() + 2 * s.vHeaderPadding
            self.minWidth = rect.width() + 2 * s.vHeaderPadding
        elif self.subKind == ScopeCellElement.TOP:
            self.minHeight = s.rectRadius
            self.minWidth = 0
        elif self.subKind == ScopeCellElement.BOTTOM:
            self.minHeight = s.rectRadius
            self.minWidth = 0
        else:
            raise Exception( "Unrecognized file scope element: " +
                             str( self.subKind ) )
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        if self.subKind == ScopeCellElement.UNKNOWN:
            raise Exception( "Unknown file scope element" )

        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
        if self.subKind == ScopeCellElement.TOP_LEFT:
            # Draw the scope rounded rectangle when we see the top left corner
            self.setRect( baseX, baseY, self.canvas.width, self.canvas.height )
            scene.addItem( self )
            self.canvas.scopeRectangle = self
        elif self.subKind == ScopeCellElement.DECLARATION:
            self.setRect( baseX, baseY, self.width, self.height )
            scene.addItem( self )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            self.setRect( baseX, baseY, self.width, self.height )
            scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        if self.subKind == ScopeCellElement.TOP_LEFT:
            brush = QBrush( s.funcScopeBGColor )
            painter.setBrush( brush )
            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawRoundedRect( self.baseX, self.baseY, self.canvas.width, self.canvas.height,
                                     s.rectRadius, s.rectRadius )
        elif self.subKind == ScopeCellElement.DECLARATION:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( self.baseX + s.hHeaderPadding,
                              self.baseY + s.vHeaderPadding,
                              int( self.rect().width() ) - 2 * s.hHeaderPadding,
                              int( self.rect().height() ) - 2 * s.vHeaderPadding,
                              Qt.AlignLeft,
                              self.__getHeaderText() )

            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( self.baseX - s.rectRadius, self.baseY + self.height,
                              self.baseX - s.rectRadius + self.canvas.width,
                              self.baseY + self.height )
        elif self.subKind == ScopeCellElement.DOCSTRING:
            pen = QPen( s.boxFGColor )
            painter.setFont( s.monoFont )
            painter.setPen( pen )
            painter.drawText( self.baseX + s.hHeaderPadding,
                              self.baseY + s.vHeaderPadding,
                              int( self.rect().width() ) - 2 * s.hHeaderPadding,
                              int( self.rect().height() ) - 2 * s.vHeaderPadding,
                              Qt.AlignLeft,
                              self.getDocstringText() )

            pen = QPen( s.lineColor )
            pen.setWidth( s.lineWidth )
            painter.setPen( pen )
            painter.drawLine( self.baseX - s.rectRadius, self.baseY + self.height,
                              self.baseX - s.rectRadius + self.canvas.width,
                              self.baseY + self.height )
        return



class ClassScopeCell( ScopeCellElement ):
    " Represents a class scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.CLASS_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ForScopeCell( ScopeCellElement ):
    " Represents a for-loop scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.FOR_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class WhileScopeCell( ScopeCellElement ):
    " Represents a while-loop scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.WHILE_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class TryScopeCell( ScopeCellElement ):
    " Represents a try-except scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.TRY_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class WithScopeCell( ScopeCellElement ):
    " Represents a with scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.WITH_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class DecoratorScopeCell( ScopeCellElement ):
    " Represents a decorator scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.DECOR_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ElseScopeCell( ScopeCellElement ):
    " Represents an else scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.ELSE_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ExceptScopeCell( ScopeCellElement ):
    " Represents an except scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.EXCEPT_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class FinallyScopeCell( ScopeCellElement ):
    " Represents a finally scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.FINALLY_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class BreakCell( CellElement ):
    " Represents a single break statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.BREAK
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ContinueCell( CellElement ):
    " Represents a single continue statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.CONTINUE
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ReturnCell( CellElement ):
    " Represents a single return statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.RETURN
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class RaiseCell( CellElement ):
    " Represents a single raise statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.RAISE
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class AssertCell( CellElement ):
    " Represents a single assert statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.ASSERT
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



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
                                                         0, 'w' )
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
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        # Set the colors and line width
        pen = QPen( s.lineColor )
        pen.setWidth( s.lineWidth )
        self.setPen( pen )
        brush = QBrush( s.boxBGColor )
        self.setBrush( brush )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + self.width / 2,
                          self.baseY,
                          self.baseX + self.width / 2,
                          self.baseY + self.height )
        QGraphicsRectItem.paint( self, painter, option, widget )
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
        return



class IndependentCommentCell( CellElement, QGraphicsRectItem ):
    " Represents a single independent comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.INDEPENDENT_COMMENT
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
        self.minWidth = rect.width() + 2 * s.hCellPadding + 2 * s.hTextPadding
        self.height = self.minHeight
        self.width = self.minWidth
        return (self.width, self.height)

    def draw( self, scene, baseX, baseY ):
        self.baseX = baseX
        self.baseY = baseY
        s = self.canvas.settings
        self.setRect( baseX + s.hCellPadding, baseY + s.vCellPadding,
                      self.width - 2 * s.hCellPadding,
                      self.height - 2 * s.vCellPadding )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        pen = QPen( s.commentBGColor )
        pen.setWidth( 0 )
        self.setPen( pen )
        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        painter.setPen( pen )
        QGraphicsRectItem.paint( self, painter, option, widget )


        # Set the colors and line width
        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ) )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ),
                          self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ) )
        painter.drawLine( self.baseX,
                          self.baseY + self.height / 2,
                          self.baseX + s.hCellPadding,
                          self.baseY + self.height / 2 )


        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * s.hTextPadding,
                          int( self.rect().height() ) - 2 * s.vTextPadding,
                          Qt.AlignLeft,
                          self.__getText() )
        return



class LeadingCommentCell( CellElement, QGraphicsRectItem ):
    " Represents a single leading comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
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
        s = self.canvas.settings
        self.setRect( baseX + s.hCellPadding, baseY + s.vCellPadding,
                      self.width - 2 * s.hCellPadding,
                      self.height - 2 * s.vCellPadding )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        pen = QPen( s.commentBGColor )
        pen.setWidth( 0 )
        self.setPen( pen )
        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        painter.setPen( pen )
        QGraphicsRectItem.paint( self, painter, option, widget )


        # Set the colors and line width
        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ) )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ),
                          self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ) )
        painter.drawLine( self.baseX,
                          self.baseY + self.height,
                          self.baseX + s.hCellPadding,
                          self.baseY + self.height / 2 )


        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * s.hTextPadding,
                          int( self.rect().height() ) - 2 * s.vTextPadding,
                          Qt.AlignLeft,
                          self.__getText() )
        return



class SideCommentCell( CellElement, QGraphicsRectItem ):
    " Represents a single side comment "

    def __init__( self, ref, canvas, x, y ):
        CellElement.__init__( self, ref, canvas, x, y )
        QGraphicsRectItem.__init__( self, canvas.scopeRectangle )
        self.kind = CellElement.SIDE_COMMENT
        self.__text = None
        return

    def __getText( self ):
        if self.__text is None:
            self.__text = ""
            if self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ].kind == CellElement.IMPORT:
                importRef = self.canvas.cells[ self.addr[ 1 ] ][ self.addr[ 0 ] - 1 ].ref
                if importRef.fromPart is not None:
                    self.__text = "\n"
                self.__text += '\n' * (self.ref.sideComment.beginLine - importRef.whatPart.beginLine ) + \
                               self.ref.sideComment.getDisplayValue()
            else:
                self.__text = '\n' * (self.ref.sideComment.beginLine - self.ref.body.beginLine ) + \
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
        s = self.canvas.settings
        self.setRect( baseX + s.hCellPadding, baseY + s.vCellPadding,
                      self.width - 2 * s.hCellPadding,
                      self.height - 2 * s.vCellPadding )
        scene.addItem( self )
        return

    def paint( self, painter, option, widget ):
        " Draws the code block "
        s = self.canvas.settings

        pen = QPen( s.commentBGColor )
        pen.setWidth( 0 )
        self.setPen( pen )
        brush = QBrush( s.commentBGColor )
        self.setBrush( brush )

        painter.setPen( pen )
        QGraphicsRectItem.paint( self, painter, option, widget )


        # Set the colors and line width
        pen = QPen( s.commentLineColor )
        pen.setWidth( s.commentLineWidth )

        # Draw the connector as a single line under the rectangle
        painter.setPen( pen )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ) )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding,
                          self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding )
        painter.drawLine( self.baseX + s.hCellPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ),
                          self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + int( self.rect().height() ) )
        painter.drawLine( self.baseX,
                          self.baseY + self.height / 2,
                          self.baseX + s.hCellPadding,
                          self.baseY + self.height / 2 )


        # Draw the text in the rectangle
        pen = QPen( s.commentFGColor )
        painter.setFont( s.monoFont )
        painter.setPen( pen )
        painter.drawText( self.baseX + s.hCellPadding + s.hTextPadding,
                          self.baseY + s.vCellPadding + s.vTextPadding,
                          int( self.rect().width() ) - 2 * s.hTextPadding,
                          int( self.rect().height() ) - 2 * s.vTextPadding,
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


