#
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
# $Id$
#

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#


" Module implementing the lexer base class "


class Lexer( object ):
    "  The lexer mixin class "

    def __init__( self ):

        self.commentString = ''
        self.streamCommentString = { 'start' : '',
                                     'end'   : '' }
        self.boxCommentString = { 'start'  : '',
                                  'middle' : '',
                                  'end'    : '' }

        # last indented line wrapper
        self.lastIndented = -1
        self.lastIndentedIndex = -1

        # always keep tabs (for languages where tabs are esential)
        self._alwaysKeepTabs = False
        return

    def initProperties( self ):
        """ Initializes the properties """

        # default implementation is a do nothing
        return

    def commentStr( self ):
        """ Provides the comment string """

        return self.commentString

    def canBlockComment( self ):
        """ Determines if the lexer language supports a block comment """

        return self.commentString != ""

    def streamCommentStr( self ):
        """ Provides the stream comment strings """

        return self.streamCommentString

    def canStreamComment( self ):
        """ Determines if the lexer language supports a stream comment """

        return (self.streamCommentString[ 'start' ] != "") and \
               (self.streamCommentString[ 'end' ] != "")

    def boxCommentStr( self ):
        """ Provides the box comment strings """

        return self.boxCommentString

    def canBoxComment( self ):
        """ Determines if the lexer language supports a box comment """

        return (self.boxCommentString[ 'start' ] != "") and \
               (self.boxCommentString[ 'middle' ] != "") and \
               (self.boxCommentString[ 'end' ] != "")

    def alwaysKeepTabs( self ):
        """ Checks if tab conversion is allowed """

        return self._alwaysKeepTabs

    def hasSmartIndent( self ):
        """ Indicates if the lexer can do smart indentation """

        return hasattr( self, 'getIndentationDifference' )

    def smartIndentLine( self, editor ):
        """ Handles smart indentation for a line """

        cline, cindex = editor.getCursorPosition()

        # get leading spaces
        lead_spaces = editor.indentation( cline )

        # get the indentation difference
        indentDifference = self.getIndentationDifference( cline, editor )

        if indentDifference != 0:
            editor.setIndentation( cline, lead_spaces + indentDifference )
            editor.setCursorPosition( cline, cindex + indentDifference )

        self.lastIndented = cline
        return

    def smartIndentSelection( self, editor ):
        """ Handles smart indentation for a selection of lines """

        if not editor.hasSelectedText():
            return

        # get the selection
        lineFrom, indexFrom, lineTo, indexTo = editor.getSelection()
        if lineFrom != self.lastIndented:
            self.lastIndentedIndex = indexFrom

        if indexTo == 0:
            endLine = lineTo - 1
        else:
            endLine = lineTo

        # get the indentation difference
        indentDifference = self.getIndentationDifference( lineFrom, editor )

        editor.beginUndoAction()
        # iterate over the lines
        for line in range( lineFrom, endLine + 1 ):
            editor.setIndentation( line,
                                   editor.indentation( line ) + \
                                       indentDifference )
        editor.endUndoAction()

        if self.lastIndentedIndex != 0:
            indexStart = indexFrom + indentDifference
        else:
            indexStart = 0

        if indexStart < 0:
            indexStart = 0
        indexEnd = indexTo != 0 and (indexTo + indentDifference) or 0
        if indexEnd < 0:
            indexEnd = 0
        editor.setSelection( lineFrom, indexStart, lineTo, indexEnd )

        self.lastIndented = lineFrom
        return

    def autoCompletionWordSeparators( self ):
        """ Provides the list of separators for autocompletion """

        return []

    def isCommentStyle( self, style ):
        """ Checks if a style is a comment style """

        return True

    def isStringStyle( self, style ):
        """ Checks if a style is a string style """

        return True

