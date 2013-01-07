# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""
Definition of an interface class for the control flow C parser
"""

from flow import ( BangLine, EncodingLine, Fragment,
                   CommentLine, Comment )
from cml import CMLRecord


class ControlFlowParserIFace:
    " Class with a set of callbacks to glue the control flow parser "

    def __init__( self, controlFlowInstance ):

        # Reference to the object where all the collected info is stored
        self.cf = controlFlowInstance
        self.comments = []
        return

    def _onError( self, message ):
        " Reports parsing error "
        self.cf.isOK = False
        if message.strip():
            self.cf.errors.append( message )
        return

    def _onLexerError( self, message ):
        " Reports lexer error "
        self.cf.isOK = False
        if message.strip():
            self.cf.lexerErrors.append( message )
        return

    def _onBangLine( self, begin, end,
                           beginLine, beginPos,
                           endLine, endPos ):
        " Called when bang line is found "
        bangLine = BangLine()
        bangLine.begin = begin
        bangLine.end = end

        # Parent is the global scope
        bangLine.parent = self.cf

        bangLine.beginLine = beginLine
        bangLine.beginPos = beginPos
        bangLine.endLine = endLine
        bangLine.endPos = endPos

        self.cf.bangLine = bangLine
        return

    def _onEncodingLine( self, begin, end,
                               beginLine, beginPos,
                               endLine, endPos ):
        " Called when encoding line is found "
        encodingLine = EncodingLine()
        encodingLine.begin = begin
        encodingLine.end = end

        # Parent is the global scope
        encodingLine.parent = self.cf

        encodingLine.beginLine = beginLine
        encodingLine.beginPos = beginPos
        encodingLine.endLine = endLine
        encodingLine.endPos = endPos

        self.cf.encodingLine = encodingLine
        return

    def _onCommentFragment( self, begin, end,
                                  beginLine, beginPos,
                                  endLine, endPos ):
        " Generic comment fragment. The exact comment type is unknown yet "
        commentLine = CommentLine()
        commentLine.begin = begin
        commentLine.end = end
        commentLine.beginLine = beginLine
        commentLine.beginPos = beginPos
        commentLine.endLine = endLine
        commentLine.endPos = endPos

        self.comments.append( commentLine )
        return

    def _onStandaloneCommentFinished( self ):
        " Standalone comment finished "
        comment = Comment()
        comment.commentLines = self.comments
        self.comments = []

        # Update parent for all members
        for line in comment.commentLines:
            line.parent = comment

        # Update the whole fragment properties
        comment.begin = comment.commentLines[ 0 ].begin
        comment.end = comment.commentLines[ -1 ].end
        comment.beginLine = comment.commentLines[ 0 ].beginLine
        comment.beginPos = comment.commentLines[ 0 ].beginPos
        comment.endLine = comment.commentLines[ -1 ].endLine
        comment.endPos = comment.commentLines[ -1 ].endPos

        # Insert the comment at the proper location
        # TODO
        return

    def _onSideCommentFinished( self ):
        pass

    def _onCMLCommentFinished( self ):
        pass


