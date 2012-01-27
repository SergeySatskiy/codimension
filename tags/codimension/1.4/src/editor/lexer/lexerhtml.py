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

""" HTML lexer implementation """


from PyQt4.Qsci     import QsciLexerHTML
from PyQt4.QtCore   import QString
from lexer          import Lexer


class LexerHTML( QsciLexerHTML, Lexer ):
    """ Adds lexer dependant methods to the QScintilla's version """

    def __init__( self, parent = None ):

        QsciLexerHTML.__init__( self, parent )
        Lexer.__init__( self )

        self.streamCommentString = { 'start' : QString('<!-- '),
                                     'end'   : QString(' -->') }
        return

    def initProperties( self ):
        """ Initializes the lexer properties """

        self.setFoldPreprocessor( 0 )
        self.setCaseSensitiveTags( 0 )
        self.setFoldCompact( 1)
        try:
            self.setFoldScriptComments( 0 )
            self.setFoldScriptHeredocs( 0 )
        except AttributeError:
            pass
        return

    def isCommentStyle( self, style ):
        """ Checks if a style is a comment one """

        return style in [ QsciLexerHTML.HTMLComment,
                          QsciLexerHTML.ASPXCComment,
                          QsciLexerHTML.SGMLComment,
                          QsciLexerHTML.SGMLParameterComment,
                          QsciLexerHTML.JavaScriptComment,
                          QsciLexerHTML.JavaScriptCommentDoc,
                          QsciLexerHTML.JavaScriptCommentLine,
                          QsciLexerHTML.ASPJavaScriptComment,
                          QsciLexerHTML.ASPJavaScriptCommentDoc,
                          QsciLexerHTML.ASPJavaScriptCommentLine,
                          QsciLexerHTML.VBScriptComment,
                          QsciLexerHTML.ASPVBScriptComment,
                          QsciLexerHTML.PythonComment,
                          QsciLexerHTML.ASPPythonComment,
                          QsciLexerHTML.PHPComment ]

    def isStringStyle( self, style ):
        """ Checks if a style is a string one """

        return style in [ QsciLexerHTML.HTMLDoubleQuotedString,
                          QsciLexerHTML.HTMLSingleQuotedString,
                          QsciLexerHTML.SGMLDoubleQuotedString,
                          QsciLexerHTML.SGMLSingleQuotedString,
                          QsciLexerHTML.JavaScriptDoubleQuotedString,
                          QsciLexerHTML.JavaScriptSingleQuotedString,
                          QsciLexerHTML.JavaScriptUnclosedString,
                          QsciLexerHTML.ASPJavaScriptDoubleQuotedString,
                          QsciLexerHTML.ASPJavaScriptSingleQuotedString,
                          QsciLexerHTML.ASPJavaScriptUnclosedString,
                          QsciLexerHTML.VBScriptString,
                          QsciLexerHTML.VBScriptUnclosedString,
                          QsciLexerHTML.ASPVBScriptString,
                          QsciLexerHTML.ASPVBScriptUnclosedString,
                          QsciLexerHTML.PythonDoubleQuotedString,
                          QsciLexerHTML.PythonSingleQuotedString,
                          QsciLexerHTML.PythonTripleDoubleQuotedString,
                          QsciLexerHTML.PythonTripleSingleQuotedString,
                          QsciLexerHTML.ASPPythonDoubleQuotedString,
                          QsciLexerHTML.ASPPythonSingleQuotedString,
                          QsciLexerHTML.ASPPythonTripleDoubleQuotedString,
                          QsciLexerHTML.ASPPythonTripleSingleQuotedString,
                          QsciLexerHTML.PHPDoubleQuotedString,
                          QsciLexerHTML.PHPSingleQuotedString ]

