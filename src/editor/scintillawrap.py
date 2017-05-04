# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" QsciScintilla wrapper """

import re
from PyQt4.QtGui import QApplication, QPalette
from PyQt4.Qsci import QsciScintilla



class ScintillaWrapper( QsciScintilla ):
    """ QsciScintilla wrapper implementation """

    def __init__( self, parent = None ):
        QsciScintilla.__init__( self, parent )

        self.SendScintilla( self.SCI_SETLAYOUTCACHE, self.SC_CACHE_DOCUMENT )

        self.zoom = 0
        self._charWidth = -1
        self._lineHeight = -1

        self.__targetSearchFlags = 0
        self.__targetSearchExpr = ""
        self.__targetSearchStart = 0
        self.__targetSearchEnd = -1
        self.__targetSearchActive = False
        return

    def linesOnScreen( self ):
        """ Provides the number of the visible lines """
        return self.SendScintilla( self.SCI_LINESONSCREEN )

    def lineAt( self, pos ):
        """ Calculates the line at a position. pos is int or QPoint.
            Returns -1 if there is no line at pos """
        if type( pos ) == int:
            scipos = pos
        else:
            scipos = self.SendScintilla( self.SCI_POSITIONFROMPOINT,
                                         pos.x(), pos.y() )
        line = self.SendScintilla( self.SCI_LINEFROMPOSITION, scipos )

        # Zero based, so >=
        if line >= self.lines():
            return -1
        return line

    def getEndPosition( self ):
        " Provides the end position "
        line = self.lines() - 1
        return ( line, len( self.text( line ) ) )

    def getCurrentPixelPosition( self ):
        " Provides the current text cursor position in points "
        pos = self.SendScintilla( self.SCI_GETCURRENTPOS )
        xPos = self.SendScintilla( self.SCI_POINTXFROMPOSITION, 0, pos )
        yPos = self.SendScintilla( self.SCI_POINTYFROMPOSITION, 0, pos )
        return xPos, yPos

    def setCurrentPosition( self, pos ):
        " Sets the current position "
        self.SendScintilla( self.SCI_SETCURRENTPOS, pos )
        return

    def styleAt( self, pos ):
        """ Provides the style at the pos """
        return self.SendScintilla( self.SCI_GETSTYLEAT, pos )

    def currentStyle( self ):
        """ Provides the style at the current cursor position """
        return self.styleAt( self.currentPosition() )

    def stringAt( self, pos, length ):
        """ Provides a string starting at position 'pos' with
            the length of 'length' bytes (not characters!).
            It respects multibyte characters """
        lastPos = pos + length
        result = u""
        while pos < lastPos:
            decodedChar, utf8Len = self.__decodeMultibyteCharacter( pos )
            pos += utf8Len
            result += decodedChar
        return result

    def __decodeMultibyteCharacter( self, pos ):
        " Provides decoded character if needed and the lenght "
        character = self.rawCharAt( pos )
        if character and ord( character ) > 127 and self.isUtf8():
            if ( ord( character[0] ) & 0xF0 ) == 0xF0:
                utf8Len = 4
            elif ( ord( character[0] ) & 0xE0 ) == 0xE0:
                utf8Len = 3
            elif ( ord( character[0] ) & 0xC0 ) == 0xC0:
                utf8Len = 2
            else:
                return character, 1
            while len( character ) < utf8Len:
                pos += 1
                character += self.rawCharAt( pos )
            return character.decode( 'utf8' ), utf8Len
        return character, 1

    def charAt( self, pos ):
        """ Provides the character at the pos in the text
            observing multibyte characters """
        decodedChar, utf8Len = self.__decodeMultibyteCharacter( pos )
        return decodedChar

    def rawCharAt( self, pos ):
        """ Provides the raw character at the pos in the text """
        character = self.SendScintilla( self.SCI_GETCHARAT, pos )
        if character == 0:
            return ""
        if character < 0:
            return chr( character + 256 )
        return chr( character )

    def setIndentationGuideView( self, view ):
        """ Sets the view of the indentation guides """
        self.SendScintilla( self.SCI_SETINDENTATIONGUIDES, view )
        return

    def indentationGuideView( self ):
        """ Provides the indentation guide view """
        return self.SendScintilla( self.SCI_GETINDENTATIONGUIDES )

    # methods below are missing from QScintilla

    def editorCommand( self, cmd ):
        """ Executes a simple editor command """
        self.SendScintilla( cmd )
        return

    def scrollVertical( self, lines ):
        """ Scroll the text area the given lines up or down """
        self.SendScintilla( self.SCI_LINESCROLL, 0, lines )
        return

    def duplicateLine( self ):
        " Duplicates the current line "
        if not self.isReadOnly():
            self.SendScintilla( self.SCI_LINEDUPLICATE )
        return

    def deleteBack( self ):
        """ Deletes the character to the left of the cursor """
        self.SendScintilla( self.SCI_DELETEBACK )
        return

    def delete( self ):
        """ Deletes the character to the right of the cursor """
        self.SendScintilla( self.SCI_CLEAR )
        return

    def deleteLineRight( self ):
        """ Deletes the line to the right of the cursor """
        self.SendScintilla( self.SCI_DELLINERIGHT )
        return

    def getHScrollOffset( self ):
        " Provides the current horizontal offset "
        return self.SendScintilla( self.SCI_GETXOFFSET )

        # methods to perform searches in target range

    def positionFromPoint( self, point ):
        """ Calculates the scintilla position from a point in the window """
        return self.SendScintilla( self.SCI_POSITIONFROMPOINTCLOSE,
                                   point.x(), point.y() )

    def positionBefore( self, pos ):
        """ Provides the position before the given position taking into account
            multibyte characters """
        return self.SendScintilla( self.SCI_POSITIONBEFORE, pos )

    def positionAfter( self, pos ):
        """ Provides the position after the given position taking into account
            multibyte characters """
        return self.SendScintilla( self.SCI_POSITIONAFTER, pos )

    def positionFromLineIndex( self, line, index ):
        """ Converts line and index to an absolute position """
        pos = self.SendScintilla( self.SCI_POSITIONFROMLINE, line )

        # Allow for multi-byte characters
        for i in xrange( index ):
            pos = self.positionAfter( pos )
        return pos

    def lineIndexFromPosition( self, pos ):
        """ Converts an absolute position to line and index """
        lin = self.SendScintilla( self.SCI_LINEFROMPOSITION, pos )
        linpos = self.SendScintilla( self.SCI_POSITIONFROMLINE, lin )
        index = 0

        # Allow for multi-byte characters
        while linpos < pos:
            new_linpos = self.positionAfter( linpos )

            # If the position hasn't moved then we must be at the end
            # of the text (which implies that the position passed was
            # beyond the end of the text)
            if new_linpos == linpos:
                break

            linpos = new_linpos
            index += 1

        return lin, index

    def lineEndPosition( self, line ):
        """ Determines the line end position of the given line """
        return self.SendScintilla( self.SCI_GETLINEENDPOSITION, line )

    # indicator handling methods

    def __checkIndicator( self, indicator ):
        """ Checks the indicator value """
        if indicator < self.INDIC_CONTAINER or \
           indicator > self.INDIC_MAX:
            raise ValueError( "indicator number out of range" )
        return

    def indicatorDefine( self, indicator, style, color ):
        """ Defines the indicator appearance """
        self.__checkIndicator( indicator )

        if style < self.INDIC_PLAIN or style > self.INDIC_ROUNDBOX:
            raise ValueError( "style out of range" )

        self.SendScintilla( self.SCI_INDICSETSTYLE, indicator, style )
        self.SendScintilla( self.SCI_INDICSETFORE, indicator, color )
        return

    def setCurrentIndicator( self, indicator ):
        " Sets the current indicator "
        self.__checkIndicator( indicator )
        self.SendScintilla( self.SCI_SETINDICATORCURRENT, indicator)
        return

    def getCurrentIndicator( self ):
        " Provides the current indicator "
        return self.SendScintilla( self.SCI_GETINDICATORCURRENT )

    def setIndicatorRange( self, indicator, spos, length ):
        " Sets the indicator for the given range "
        self.setCurrentIndicator( indicator )
        self.SendScintilla( self.SCI_INDICATORFILLRANGE, spos, length )
        return

    def setIndicator( self, indicator, sline, sindex, eline, eindex ):
        """ Sets the indicator for the given range """
        spos = self.positionFromLineIndex( sline, sindex )
        epos = self.positionFromLineIndex( eline, eindex )
        self.setIndicatorRange( indicator, spos, epos - spos )
        return

    def clearIndicatorRange( self, indicator, spos, length ):
        """ Clears the indicator for the given range """
        self.setCurrentIndicator( indicator )
        self.SendScintilla( self.SCI_INDICATORCLEARRANGE, spos, length )
        return

    def clearIndicator( self, indicator, sline, sindex, eline, eindex ):
        """ Clears the indicator for the given range """
        spos = self.positionFromLineIndex( sline, sindex )
        epos = self.positionFromLineIndex( eline, eindex )
        self.clearIndicatorRange( indicator, spos, epos - spos )
        return

    def clearAllIndicators( self, indicator ):
        " Clears all occurrences of an indicator "
        self.clearIndicatorRange( indicator, 0, self.length() )
        return

    def hasIndicator( self, indicator, pos ):
        """ Tests for the existence of the indicator """
        return self.SendScintilla( self.SCI_INDICATORVALUEAT, indicator, pos )

    # interface methods to the standard keyboard command set

    def clearKeys( self ):
        """ Clears the key commands """
        # call into the QsciCommandSet
        self.standardCommands().clearKeys()
        return

    def clearAlternateKeys( self ):
        """ Clears the alternate key commands """
        # call into the QsciCommandSet
        self.standardCommands().clearAlternateKeys()
        return

    def setCurrentLineHighlight( self, isHighlighted, color ):
        " Sets the current line highlight "
        self.SendScintilla( self.SCI_SETCARETLINEVISIBLE, isHighlighted )
        if isHighlighted:
            self.SendScintilla( self.SCI_SETCARETLINEBACK, color )
        return

    def expandTabs( self, spaces ):
        " Expands tabs "
        searchRE = r"\t"

        line, pos = self.getCursorPosition()
        replace = spaces * " "
        found = self.findFirstTarget( searchRE, True, False, False, 0, 0 )
        self.beginUndoAction()
        while found:
            self.replaceTarget( replace )
            found = self.findNextTarget()
        self.endUndoAction()
        self.setCursorPosition( line, pos )
        return

    def getTextAtPos( self, line, col, length ):
        " Provides the text of the given length under the cursor "
        text = self.text( line )
        return text[ col : col + length ]

    def selectParagraphUp( self ):
        " Selects the paragraph up "
        self.SendScintilla( self.SCI_PARAUPEXTEND )
        return

    def selectParagraphDown( self ):
        " Selects the paragraph down "
        self.SendScintilla( self.SCI_PARADOWNEXTEND )
        return

    def dedentLine( self ):
        " Dedent the current line "
        self.SendScintilla( self.SCI_BACKTAB )
        return

    def selectTillDisplayEnd( self ):
        " Selects from the current position till the displayed end of line "
        self.SendScintilla( self.SCI_LINEENDDISPLAYEXTEND )
        return

    def moveToLineEnd( self ):
        " Moves the cursor to the displayed end of line "
        self.SendScintilla( self.SCI_LINEENDDISPLAY )
        return

    def selectTillLineBegin( self, firstNonSpace ):
        " Selects till the beginning of the line "
        if firstNonSpace:
            self.SendScintilla( self.SCI_VCHOMEEXTEND )
        else:
            self.SendScintilla( self.SCI_HOMEDISPLAYEXTEND )
        return

    def getSelectionStart( self ):
        " Provides the selection start "
        return self.SendScintilla( self.SCI_GETSELECTIONSTART )

    def getSelectionEnd( self ):
        " Provides the selection end "
        return self.SendScintilla( self.SCI_GETSELECTIONEND )
