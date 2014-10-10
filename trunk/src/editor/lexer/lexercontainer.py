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


""" Base class for custom lexers """


from PyQt4.Qsci     import QsciLexer
from lexer          import Lexer


class LexerContainer( QsciLexer, Lexer ):
    " Base class for custom lexers "

    def __init__( self, parent = None ):

        QsciLexer.__init__( self, parent )
        Lexer.__init__( self )

        self.editor = parent
        return

    def language( self ):
        " Provides the lexer language "
        return "Container"

    def lexer( self ):
        " Provides the lexer type "

        if hasattr( self, 'lexerId' ):
            return None
        return "container"

    def description( self, style ):
        " Provides the descriptions of the lexer supported styles "
        return ""

    def styleBitsNeeded( self ):
        " Provides the number of style bits needed by the lexer "
        return 5

    def styleText( self, start, end ):
        " Perform the styling "

        self.editor.startStyling( start, 0x1f )
        self.editor.setStyling( end - start + 1, 0 )
        return

