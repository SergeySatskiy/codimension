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


""" Python lexer implementation """

import re

from PyQt4.Qsci     import QsciLexerPython
from lexer          import Lexer


# Python built in functions as of 2.7.3
# http://docs.python.org/library/functions.html
BUILTIN_FUNCS = "abs divmod input open staticmethod " \
                "all enumerate int ord str " \
                "any eval isinstance pow sum " \
                "basestring execfile issubclass print super " \
                "bin file iter property tuple " \
                "bool filter len range type " \
                "bytearray float list raw_input unichr " \
                "callable format locals reduce unicode " \
                "chr frozenset long reload vars " \
                "classmethod getattr map repr xrange " \
                "cmp globals max reversed zip " \
                "compile hasattr memoryview round __import__ " \
                "complex hash min set apply " \
                "delattr help next setattr buffer " \
                "dict hex object slice coerce " \
                "dir id oct sorted intern"
BOOLEANS = "True False"
BUILTIN_EXCEPTIONS = "BaseException Exception ArithmeticError " \
                     "LookupError EnvironmentError " \
                     "AssertionError AttributeError EOFError " \
                     "FloatingPointError GeneratorExit " \
                     "IOError ImportError IndentationError " \
                     "IndexError KeyError KeyboardInterrupt " \
                     "MemoryError NameError NotImplementedError " \
                     "OSError OverflowError ReferenceError " \
                     "RuntimeError StopIteration SyntaxError " \
                     "SystemError SystemExit TabError TypeError " \
                     "UnboundLocalError UnicodeError UnicodeEncodeError " \
                     "UnicodeDecodeError UnicodeTranslateError " \
                     "ValueError WindowsError ZeroDivisionError " \
                     "Warning UserWarning DeprecationWarning " \
                     "SyntaxWarning RuntimeWarning FutureWarning"
TREAT_AS_KEYWORDS = BUILTIN_FUNCS + " " + BOOLEANS + " " + BUILTIN_EXCEPTIONS + " nonlocal"



class LexerPython( QsciLexerPython, Lexer ):
    """ Adds lexer dependant methods to the QScintilla's version """

    def __init__( self, parent = None ):

        QsciLexerPython.__init__( self, parent )
        Lexer.__init__( self )

        self.commentString = "#"
        return

    def initProperties( self ):
        """ Initializes the lexer properties """

        self.setIndentationWarning( QsciLexerPython.Inconsistent )
        self.setFoldComments( 1 )
        self.setFoldQuotes( 1 )
        # self.setAutoIndentStyle( QsciScintilla.AiMaintain )

        try:
            self.setV2UnicodeAllowed( 1 )
            self.setV3BinaryOctalAllowed( 1 )
            self.setV3BytesAllowed( 1 )
        except AttributeError:
            pass
        return

    def getIndentationDifference( self, line, editor ):
        """ Determines the difference for the new indentation """

        indent_width = 4

        lead_spaces = editor.indentation(line)

        pline = line - 1
        while pline >= 0 and \
              re.match( '^\s*(#.*)?$', unicode( editor.text( pline ) ) ):
            pline -= 1

        if pline < 0:
            last = 0
        else:
            previous_lead_spaces = editor.indentation( pline )
            # trailing spaces
            m = re.search( ':\s*(#.*)?$', unicode( editor.text( pline ) ) )
            last = previous_lead_spaces
            if m:
                last += indent_width
            else:
                # special cases, like pass (unindent) or return (also unindent)
                match = re.search( '(pass\s*(#.*)?$)|(^[^#]return)',
                                   unicode( editor.text( pline ) ) )
                if match:
                    last -= indent_width

        if lead_spaces % indent_width != 0 or lead_spaces == 0 or \
           self.lastIndented != line:
            indentDifference = last - lead_spaces
        else:
            indentDifference = -indent_width
        return indentDifference

    def autoCompletionWordSeparators( self ):
        """ Provides the list of separators for autocompletion """

        return [ '.' ]

    def isCommentStyle( self, style ):
        """ Checks if a style is a comment one """

        return style in [ QsciLexerPython.Comment,
                          QsciLexerPython.CommentBlock ]

    def isStringStyle( self, style ):
        """ Checks if a style is a string one """

        return style in [ QsciLexerPython.DoubleQuotedString,
                          QsciLexerPython.SingleQuotedString,
                          QsciLexerPython.TripleDoubleQuotedString,
                          QsciLexerPython.TripleSingleQuotedString,
                          QsciLexerPython.UnclosedString ]

    def keywords( self, setNumber ):
        " Adds True and False into the list of keywords "
        standardSet = QsciLexerPython.keywords( self, setNumber )
        if standardSet is None:
            return standardSet

        return str( standardSet ) + " " + TREAT_AS_KEYWORDS

