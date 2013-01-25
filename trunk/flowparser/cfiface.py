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
                   Fragment, Comment, FragmentWithComments, Docstring )
from cml import CMLRecord


class ControlFlowParserIFace:
    " Class with a set of callbacks to glue the control flow parser "

    def __init__( self, controlFlowInstance ):

        # Reference to the object where all the collected info is stored
        self.cf = controlFlowInstance
        self.__fragments = []
        self.__objectsStack = []
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
                           beginLine, beginPos, endLine, endPos ):
        " Called when bang line is found "
        bangLine = BangLine( begin, end, beginLine, beginPos,
                                         endLine, endPos )

        # Parent is the global scope
        bangLine.parent = self.cf

        self.cf.bangLine = bangLine
        return

    def _onEncodingLine( self, begin, end,
                               beginLine, beginPos, endLine, endPos ):
        " Called when encoding line is found "
        encodingLine = EncodingLine( begin, end, beginLine, beginPos,
                                                 endLine, endPos )

        # Parent is the global scope
        encodingLine.parent = self.cf

        self.cf.encodingLine = encodingLine
        return

    def _onFragment( self, begin, end,
                           beginLine, beginPos, endLine, endPos ):
        " Generic fragment. The exact fragment type is unknown yet "
        self.__fragments.append( Fragment( begin, end, beginLine, beginPos,
                                           endLine, endPos ) )
        return

    def _onStandaloneCommentFinished( self ):
        " Standalone comment finished "
        comment = Comment()
        self.__wrapFragments( comment, self.__fragments )
        comment.parts = self.__fragments
        self.__fragments = []

        # Insert the comment at the proper location
        self.__insertStandaloneComment( comment, self.cf, self.cf.body, False )
        return

    def _onCMLCommentFinished( self ):
        " CML Record finished "
        cml = CMLRecord()
        self.__wrapFragments( cml, self.__fragments )
        cml.parts = self.__fragments
        self.__fragments = []

        # Insert the comment at the proper location
        self.__insertStandaloneComment( cml, self.cf, self.cf.body, True )
        return

    def __wrapFragments( self, obj, parts ):
        " Sets the wrapping object properties "
        for part in parts:
            part.parent = obj

        obj.begin = parts[ 0 ].begin
        obj.end = parts[ -1 ].end
        obj.beginLine = parts[ 0 ].beginLine
        obj.beginPos = parts[ 0 ].beginPos
        obj.endLine = parts[ -1 ].endLine
        obj.endPos = parts[ -1 ].endPos
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
        return
        raise Exception( "Not implemented yet" )

    def _onDocstringFinished( self ):
        " Called when a docstring is finished "
        docstring = Docstring()
        self.__wrapFragments( docstring, self.__fragments )
        docstring.parts = self.__fragments
        self.__fragments = []

        # Insert into the proper object
        if not self.__objectsStack:
            docstring.parent = self.cf
            self.cf.docstring = docstring
            return

        index = len( self.__objectsStack ) - 1
        docstring.parent = self.__objectsStack[ index ]
        self.__objectsStack[ index ].docstring = docstring
        return


