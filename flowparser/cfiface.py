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

from flow import ( BangLine, EncodingLine,
                   CommentLine, Comment, FragmentWithComments )
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
        comment.body = self.comments
        self.comments = []

        # Update parent for all members
        for line in comment.body:
            line.parent = comment

        # Update the whole fragment properties
        comment.begin = comment.body[ 0 ].begin
        comment.end = comment.body[ -1 ].end
        comment.beginLine = comment.body[ 0 ].beginLine
        comment.beginPos = comment.body[ 0 ].beginPos
        comment.endLine = comment.body[ -1 ].endLine
        comment.endPos = comment.body[ -1 ].endPos

        # Insert the comment at the proper location
        self.__insertStandaloneComment( comment, self.cf, self.cf.body, False )
        return

    def _onCMLCommentFinished( self ):
        " CML Record finished "
        cml = CMLRecord()
        cml.body = self.comments
        self.comments = []

        # Update parent for all members
        for line in cml.body:
            line.parent = cml

        # Update the whole fragment properties
        cml.begin = cml.body[ 0 ].begin
        cml.end = cml.body[ -1 ].end
        cml.beginLine = cml.body[ 0 ].beginLine
        cml.beginPos = cml.body[ 0 ].beginPos
        cml.endLine = cml.body[ -1 ].endLine
        cml.endPos = cml.body[ -1 ].endPos

        # Insert the comment at the proper location
        self.__insertStandaloneComment( cml, self.cf, self.cf.body, True )
        return

    def __insertStandaloneComment( self, obj, parent, body, isCML ):
        " Inserts the fragment into the proper position in the control flow "
        line = obj.beginLine
        index = -1
        for item in body:
            index += 1
            lineRange = item.getLineRange()
            if line >= lineRange[ 0 ] and line <= lineRange[ 1 ]:
                self.__insertStandaloneComment( obj, item, item.body, isCML )
                return
            if lineRange[ 0 ] > line:
                if obj.endLine + 1 != lineRange[ 0 ] or isCML or \
                   not isinstance( item, FragmentWithComments ):
                    # Insert as standalone
                    obj.parent = parent
                    body.insert( index, obj )
                    return
                else:
                    # Insert as leading comment
                    obj.parent = item
                    item.leadingComment = obj
                    return

        # Not found in the list, so append to the end
        obj.parent = parent
        body.append( obj )
        return

    def _onSideCommentFinished( self ):
        pass


