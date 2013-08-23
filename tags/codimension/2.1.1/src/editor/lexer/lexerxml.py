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
# $Id: lexerxml.py 18 2011-01-16 21:24:10Z sergey.satskiy@gmail.com $
#

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#


""" XML lexer implementation """

from PyQt4.Qsci     import QsciLexerXML
from PyQt4.QtCore   import QString
from lexer          import Lexer


class LexerXML(QsciLexerXML, Lexer):
    """ Adds lexer dependant methods to the QScintilla's version """

    def __init__( self, parent = None ):

        QsciLexerXML.__init__( self, parent )
        Lexer.__init__( self )

        self.streamCommentString = { 'start' : QString( '<!-- ' ),
                                     'end'   : QString( ' -->' ) }
        return

    def initProperties( self ):
        """ Initializes the lexer properties """

        self.setFoldPreprocessor( 0 )
        self.setCaseSensitiveTags( 0 )
        self.setFoldCompact( 1 )
        try:
            self.setFoldScriptComments( 0 )
            self.setFoldScriptHeredocs( 0 )
            self.setScriptsStyled( 1 )
        except AttributeError:
            pass
        return

    def isCommentStyle( self, style ):
        """ Checks if a style is a comment one """

        return style in [ QsciLexerXML.HTMLComment,
                          QsciLexerXML.ASPXCComment,
                          QsciLexerXML.SGMLComment,
                          QsciLexerXML.SGMLParameterComment,
                          QsciLexerXML.JavaScriptComment,
                          QsciLexerXML.JavaScriptCommentDoc,
                          QsciLexerXML.JavaScriptCommentLine,
                          QsciLexerXML.ASPJavaScriptComment,
                          QsciLexerXML.ASPJavaScriptCommentDoc,
                          QsciLexerXML.ASPJavaScriptCommentLine,
                          QsciLexerXML.VBScriptComment,
                          QsciLexerXML.ASPVBScriptComment,
                          QsciLexerXML.PythonComment,
                          QsciLexerXML.ASPPythonComment,
                          QsciLexerXML.PHPComment ]

    def isStringStyle( self, style ):
        """ Checks if a style is a string one """

        return style in [ QsciLexerXML.HTMLDoubleQuotedString,
                          QsciLexerXML.HTMLSingleQuotedString,
                          QsciLexerXML.SGMLDoubleQuotedString,
                          QsciLexerXML.SGMLSingleQuotedString,
                          QsciLexerXML.JavaScriptDoubleQuotedString,
                          QsciLexerXML.JavaScriptSingleQuotedString,
                          QsciLexerXML.JavaScriptUnclosedString,
                          QsciLexerXML.ASPJavaScriptDoubleQuotedString,
                          QsciLexerXML.ASPJavaScriptSingleQuotedString,
                          QsciLexerXML.ASPJavaScriptUnclosedString,
                          QsciLexerXML.VBScriptString,
                          QsciLexerXML.VBScriptUnclosedString,
                          QsciLexerXML.ASPVBScriptString,
                          QsciLexerXML.ASPVBScriptUnclosedString,
                          QsciLexerXML.PythonDoubleQuotedString,
                          QsciLexerXML.PythonSingleQuotedString,
                          QsciLexerXML.PythonTripleDoubleQuotedString,
                          QsciLexerXML.PythonTripleSingleQuotedString,
                          QsciLexerXML.ASPPythonDoubleQuotedString,
                          QsciLexerXML.ASPPythonSingleQuotedString,
                          QsciLexerXML.ASPPythonTripleDoubleQuotedString,
                          QsciLexerXML.ASPPythonTripleSingleQuotedString,
                          QsciLexerXML.PHPDoubleQuotedString,
                          QsciLexerXML.PHPSingleQuotedString ]

