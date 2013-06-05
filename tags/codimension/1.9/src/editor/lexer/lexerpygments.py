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


""" Custom lexer implementation using pygments """


from pygments.token      import Token
from pygments.lexers     import find_lexer_class, get_lexer_for_filename
from pygments.util       import ClassNotFound

from PyQt4.QtCore        import QString
from PyQt4.QtGui         import QColor, QFont
from lexercontainer      import LexerContainer


PYGMENTS_DEFAULT, \
PYGMENTS_COMMENT, \
PYGMENTS_PREPROCESSOR, \
PYGMENTS_KEYWORD, \
PYGMENTS_PSEUDOKEYWORD, \
PYGMENTS_TYPEKEYWORD, \
PYGMENTS_OPERATOR, \
PYGMENTS_WORD, \
PYGMENTS_BUILTIN, \
PYGMENTS_FUNCTION, \
PYGMENTS_CLASS, \
PYGMENTS_NAMESPACE, \
PYGMENTS_EXCEPTION, \
PYGMENTS_VARIABLE, \
PYGMENTS_CONSTANT, \
PYGMENTS_LABEL, \
PYGMENTS_ENTITY, \
PYGMENTS_ATTRIBUTE, \
PYGMENTS_TAG, \
PYGMENTS_DECORATOR, \
PYGMENTS_STRING, \
PYGMENTS_DOCSTRING, \
PYGMENTS_SCALAR, \
PYGMENTS_ESCAPE, \
PYGMENTS_REGEX, \
PYGMENTS_SYMBOL, \
PYGMENTS_OTHER, \
PYGMENTS_NUMBER, \
PYGMENTS_HEADING, \
PYGMENTS_SUBHEADING, \
PYGMENTS_DELETED, \
PYGMENTS_INSERTED           = range(32)
# 32 to 39 are reserved for QScintilla internal styles
PYGMENTS_GENERIC_ERROR, \
PYGMENTS_EMPHASIZE, \
PYGMENTS_STRONG, \
PYGMENTS_PROMPT, \
PYGMENTS_OUTPUT, \
PYGMENTS_TRACEBACK, \
PYGMENTS_ERROR              = range(40, 47)

#-----------------------------------------------------------------------------#

TOKEN_MAP = {
    Token.Comment:                   PYGMENTS_COMMENT,
    Token.Comment.Preproc:           PYGMENTS_PREPROCESSOR,

    Token.Keyword:                   PYGMENTS_KEYWORD,
    Token.Keyword.Pseudo:            PYGMENTS_PSEUDOKEYWORD,
    Token.Keyword.Type:              PYGMENTS_TYPEKEYWORD,

    Token.Operator:                  PYGMENTS_OPERATOR,
    Token.Operator.Word:             PYGMENTS_WORD,

    Token.Name.Builtin:              PYGMENTS_BUILTIN,
    Token.Name.Function:             PYGMENTS_FUNCTION,
    Token.Name.Class:                PYGMENTS_CLASS,
    Token.Name.Namespace:            PYGMENTS_NAMESPACE,
    Token.Name.Exception:            PYGMENTS_EXCEPTION,
    Token.Name.Variable:             PYGMENTS_VARIABLE,
    Token.Name.Constant:             PYGMENTS_CONSTANT,
    Token.Name.Label:                PYGMENTS_LABEL,
    Token.Name.Entity:               PYGMENTS_ENTITY,
    Token.Name.Attribute:            PYGMENTS_ATTRIBUTE,
    Token.Name.Tag:                  PYGMENTS_TAG,
    Token.Name.Decorator:            PYGMENTS_DECORATOR,

    Token.String:                    PYGMENTS_STRING,
    Token.String.Doc:                PYGMENTS_DOCSTRING,
    Token.String.Interpol:           PYGMENTS_SCALAR,
    Token.String.Escape:             PYGMENTS_ESCAPE,
    Token.String.Regex:              PYGMENTS_REGEX,
    Token.String.Symbol:             PYGMENTS_SYMBOL,
    Token.String.Other:              PYGMENTS_OTHER,
    Token.Number:                    PYGMENTS_NUMBER,

    Token.Generic.Heading:           PYGMENTS_HEADING,
    Token.Generic.Subheading:        PYGMENTS_SUBHEADING,
    Token.Generic.Deleted:           PYGMENTS_DELETED,
    Token.Generic.Inserted:          PYGMENTS_INSERTED,
    Token.Generic.Error:             PYGMENTS_GENERIC_ERROR,
    Token.Generic.Emph:              PYGMENTS_EMPHASIZE,
    Token.Generic.Strong:            PYGMENTS_STRONG,
    Token.Generic.Prompt:            PYGMENTS_PROMPT,
    Token.Generic.Output:            PYGMENTS_OUTPUT,
    Token.Generic.Traceback:         PYGMENTS_TRACEBACK,

    Token.Error:                     PYGMENTS_ERROR,
}

#-----------------------------------------------------------------------------#


class LexerPygments( LexerContainer ):
    """ Custom lexer implementation using pygments """

    def __init__( self, parent = None, name = "", fileName = "" ):

        LexerContainer.__init__( self, parent )

        self.__pygmentsName = name
        self.__fileName = fileName
        self.__lexerGuessed = False
        self.__language = "Guessed"

        self.descriptions = {
            PYGMENTS_DEFAULT       : "Default",
            PYGMENTS_COMMENT       : "Comment",
            PYGMENTS_PREPROCESSOR  : "Preprocessor",
            PYGMENTS_KEYWORD       : "Keyword",
            PYGMENTS_PSEUDOKEYWORD : "Pseudo Keyword",
            PYGMENTS_TYPEKEYWORD   : "Type Keyword",
            PYGMENTS_OPERATOR      : "Operator",
            PYGMENTS_WORD          : "Word",
            PYGMENTS_BUILTIN       : "Builtin",
            PYGMENTS_FUNCTION      : "Function or method name",
            PYGMENTS_CLASS         : "Class name",
            PYGMENTS_NAMESPACE     : "Namespace",
            PYGMENTS_EXCEPTION     : "Exception",
            PYGMENTS_VARIABLE      : "Identifier",
            PYGMENTS_CONSTANT      : "Constant",
            PYGMENTS_LABEL         : "Label",
            PYGMENTS_ENTITY        : "Entity",
            PYGMENTS_ATTRIBUTE     : "Attribute",
            PYGMENTS_TAG           : "Tag",
            PYGMENTS_DECORATOR     : "Decorator",
            PYGMENTS_STRING        : "String",
            PYGMENTS_DOCSTRING     : "Documentation string",
            PYGMENTS_SCALAR        : "Scalar",
            PYGMENTS_ESCAPE        : "Escape",
            PYGMENTS_REGEX         : "Regular expression",
            PYGMENTS_SYMBOL        : "Symbol",
            PYGMENTS_OTHER         : "Other string",
            PYGMENTS_NUMBER        : "Number",
            PYGMENTS_HEADING       : "Heading",
            PYGMENTS_SUBHEADING    : "Subheading",
            PYGMENTS_DELETED       : "Deleted",
            PYGMENTS_INSERTED      : "Inserted",
            PYGMENTS_GENERIC_ERROR : "Generic error",
            PYGMENTS_EMPHASIZE     : "Emphasized text",
            PYGMENTS_STRONG        : "Strong text",
            PYGMENTS_PROMPT        : "Prompt",
            PYGMENTS_OUTPUT        : "Output",
            PYGMENTS_TRACEBACK     : "Traceback",
            PYGMENTS_ERROR         : "Error",
        }

        self.defaultColors = {
            PYGMENTS_DEFAULT       : QColor("#000000"),
            PYGMENTS_COMMENT       : QColor("#408080"),
            PYGMENTS_PREPROCESSOR  : QColor("#BC7A00"),
            PYGMENTS_KEYWORD       : QColor("#008000"),
            PYGMENTS_PSEUDOKEYWORD : QColor("#008000"),
            PYGMENTS_TYPEKEYWORD   : QColor("#B00040"),
            PYGMENTS_OPERATOR      : QColor("#666666"),
            PYGMENTS_WORD          : QColor("#AA22FF"),
            PYGMENTS_BUILTIN       : QColor("#008000"),
            PYGMENTS_FUNCTION      : QColor("#0000FF"),
            PYGMENTS_CLASS         : QColor("#0000FF"),
            PYGMENTS_NAMESPACE     : QColor("#0000FF"),
            PYGMENTS_EXCEPTION     : QColor("#D2413A"),
            PYGMENTS_VARIABLE      : QColor("#19177C"),
            PYGMENTS_CONSTANT      : QColor("#880000"),
            PYGMENTS_LABEL         : QColor("#A0A000"),
            PYGMENTS_ENTITY        : QColor("#999999"),
            PYGMENTS_ATTRIBUTE     : QColor("#7D9029"),
            PYGMENTS_TAG           : QColor("#008000"),
            PYGMENTS_DECORATOR     : QColor("#AA22FF"),
            PYGMENTS_STRING        : QColor("#BA2121"),
            PYGMENTS_DOCSTRING     : QColor("#BA2121"),
            PYGMENTS_SCALAR        : QColor("#BB6688"),
            PYGMENTS_ESCAPE        : QColor("#BB6622"),
            PYGMENTS_REGEX         : QColor("#BB6688"),
            PYGMENTS_SYMBOL        : QColor("#19177C"),
            PYGMENTS_OTHER         : QColor("#008000"),
            PYGMENTS_NUMBER        : QColor("#666666"),
            PYGMENTS_HEADING       : QColor("#000080"),
            PYGMENTS_SUBHEADING    : QColor("#800080"),
            PYGMENTS_DELETED       : QColor("#A00000"),
            PYGMENTS_INSERTED      : QColor("#00A000"),
            PYGMENTS_GENERIC_ERROR : QColor("#FF0000"),
            PYGMENTS_PROMPT        : QColor("#000080"),
            PYGMENTS_OUTPUT        : QColor("#808080"),
            PYGMENTS_TRACEBACK     : QColor("#0040D0"),
        }

        self.defaultPapers = {
            PYGMENTS_ERROR         : QColor("#FF0000"),
        }

    def language( self ):
        """ Provides the language of the lexer """
        return self.__language

    def description( self, style ):
        """ Provides the descriptions of the styles supported by the lexer """
        try:
            return self.descriptions[ style ]
        except KeyError:
            return QString()

    def defaultColor( self, style ):
        """ Provides the default foreground color for a style """
        try:
            return self.defaultColors[ style ]
        except KeyError:
            return LexerContainer.defaultColor( self, style )

    def defaultPaper( self, style ):
        """ Provides the default paper for a style """
        try:
            return self.defaultPapers[ style ]
        except KeyError:
            return LexerContainer.defaultPaper( self, style )

    def defaultFont( self, style ):
        """ Provides the default font for a style """

        if style in [ PYGMENTS_COMMENT, PYGMENTS_PREPROCESSOR ]:
            f = QFont( "Monospace", 14 )
            if style == PYGMENTS_PREPROCESSOR:
                f.setItalic( True )
            return f

        if style in [ PYGMENTS_STRING ]:
            return QFont( "Monospace", 14 )

        if style in [ PYGMENTS_KEYWORD, PYGMENTS_OPERATOR,  PYGMENTS_WORD,
                      PYGMENTS_BUILTIN, PYGMENTS_ATTRIBUTE, PYGMENTS_FUNCTION,
                      PYGMENTS_CLASS,   PYGMENTS_NAMESPACE, PYGMENTS_EXCEPTION,
                      PYGMENTS_ENTITY,  PYGMENTS_TAG,       PYGMENTS_SCALAR,
                      PYGMENTS_ESCAPE,  PYGMENTS_HEADING,   PYGMENTS_SUBHEADING,
                      PYGMENTS_STRONG,  PYGMENTS_PROMPT ]:
            f = LexerContainer.defaultFont( self, style )
            f.setBold( True )
            return f

        if style in [ PYGMENTS_DOCSTRING, PYGMENTS_EMPHASIZE ]:
            f = LexerContainer.defaultFont( self, style )
            f.setItalic( True )
            return f

        return LexerContainer.defaultFont( self, style )

    def styleBitsNeeded( self ):
        """ Provides the number of style bits needed by the lexer """
        return 6

    def __guessLexer( self ):
        """ Guesses a pygments lexer """

        self.__lexerGuessed = True
        if self.__pygmentsName:
            lexerClass = find_lexer_class( self.__pygmentsName )
            if lexerClass is not None:
                self.__language = "Guessed: " + lexerClass.name
                return lexerClass()
        else:
            # Unfortunately, guessing a lexer by text lead to unpredictable
            # behaviour in some cases. E.g. national non-english characters
            # are mis-displayed or even core dump is generated. So the part
            # of guessing by text has been removed.
            if self.editor is not None:
                if self.__fileName != "":
                    filename = self.__fileName
                else:
                    filename = self.editor.getFileName()

                try:
                    lexerClass = get_lexer_for_filename( filename )
                    self.__language = "Guessed: " + lexerClass.name
                    return lexerClass
                except ClassNotFound:
                    pass

        # Last resort - text only
        lexerClass = find_lexer_class( "Text only" )
        if lexerClass is not None:
            self.__language = "Guessed: " + lexerClass.name
            return lexerClass()
        return None

    def canStyle( self ):
        """ Checks if the lexer is able to style the text """
        if self.editor is None:
            return True

        if self.__lexerGuessed == False:
            self.__lexer = self.__guessLexer()
        return self.__lexer is not None

    def name( self ):
        """ Provides the name of the pygments lexer """
        if self.__lexer is None:
            return ""
        return self.__lexer.name

    def styleText( self, start, end ):
        """ Performs the styling """

        text = unicode( self.editor.text() )[ :end + 1 ].encode( 'utf-8' )
        textLen = len( text )
        if self.__lexerGuessed == False:
            self.__lexer = self.__guessLexer()

        cpos = 0
        self.editor.startStyling( cpos, 0x3f )
        if self.__lexer is None:
            self.editor.setStyling( textLen, PYGMENTS_DEFAULT )
        else:
            eolLen = len( self.editor.getLineSeparator() )
            for token, txt in self.__lexer.get_tokens( text ):
                style = TOKEN_MAP.get( token, PYGMENTS_DEFAULT )

                tlen = len( txt )
                if eolLen > 1:
                    tlen += txt.count( '\n' )
                cpos += tlen
                if tlen and cpos < textLen:
                    self.editor.setStyling( tlen, style )
                else:
                    break
            self.editor.startStyling( cpos, 0x3f )
        return

    def isCommentStyle( self, style ):
        """ Checks if a style is a comment one """
        return style in [ PYGMENTS_COMMENT ]

    def isStringStyle( self, style ):
        """ Checks if a style is a string one """
        return style in [ PYGMENTS_STRING,     PYGMENTS_DOCSTRING,
                          PYGMENTS_OTHER,      PYGMENTS_HEADING,
                          PYGMENTS_SUBHEADING, PYGMENTS_EMPHASIZE,
                          PYGMENTS_STRONG ]

