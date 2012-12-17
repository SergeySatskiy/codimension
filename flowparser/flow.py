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


"""
The file contains data types to represent losslessly a python file
content for the further displaying it as graphics
"""

import re



CODING_REGEXP = re.compile( r'''coding[:=]\s*([-\w_.]+)''' )

#
# The Fragment class is a basic building block for anything found
# in a python code.
#

class Fragment:
    " Represents a single text fragment of a python file"

    def __init__( self ):

        # Minimal necessary information.
        # Position 0 depends on the fragment scope.
        # The global scope fragments have it as the input stream beginning.
        # Nested fragments have it as the beginning of their parent.
        self.begin = None       # Absolute position of the first fragment
                                # character. 0-based
                                # It must never be None.
        self.end = None         # Absolute position of the last fragment
                                # character. 0-based
                                # It must never be None.

        self.parent = None      # Reference to the parent fragment. The only
                                # case when it is None is for the global
                                # scope fragments.

        # Excessive members for convenience. This makes it easier to work with
        # the editor buffer directly. The line numbers start different for
        # global scope fragments and for nested fragments similar to the start
        # and begin positions.
        self.beginLine = None   # 1-based line number
        self.beginPos = None    # 1-based position number in the line
        self.endLine = None     # 1-based line number
        self.endPos = None      # 1-based position number in the line

        # Serialization support
        self.serialized = False # True if has been serialized
        self.content = None     # Must be not None only for the global scope
                                # objects and is filled when serialized.
                                # The nested objects refer to their top level
                                # parent for the content.
        return

    def isSerialized( self ):
        " True if the object has already been serialized "
        return self.serialized

    def serialize( self, buf ):
        " Serializes the object basing on the buffer parsed "
        if self.serialized:
            return

        self.serialized = True
        if self.parent is not None:
            return

        self.content = buf[ self.begin : self.end + 1 ]
        return

    def getContent( self, buf = None ):
        " Provides the content of the fragment "
        if buf is None and not self.serialized:
            raise Exception( "Cannot get content of not serialized " \
                             "fragment without its buffer" )

        if self.serialized:
            if self.parent is None:
                return self.content

            # Find the global scope parent
            current = self
            while current.parent is not None:
                current = current.parent
            buf = current.content
            beginInBuf = self.getAbsoluteBegin() - current.begin
            endInBug = self.getAbsoluteEnd() - current.begin
            return buf[ beginInBuf : endInBug + 1 ]

        # Non-serialized
        return buf[ self.getAbsoluteBegin() : self.getAbsoluteEnd() + 1 ]

    def getLineContent( self, buf = None ):
        """ Provides a content with complete lines
            including leading spaces if so """
        leadingSpaces = " " * (self.beginPos - 1)
        return leadingSpaces + self.getContent( buf )

    def getLineAndPos( self, forBegin = True ):
        " Provides the actual line and pos for the specified end "
        return self.getLine( forBegin ), self.getPos( forBegin )

    def getLine( self, forBegin = True ):
        " Provides the actual line for the specified end "
        current = self
        if forBegin:
            result = self.beginLine
        else:
            result = self.endLine

        while current.parent is not None:
            current = current.parent
            result += current.beginLine - 1
        return result

    def getPos( self, forBegin = True ):
        " Provides the position in the specified end line "
        if forBegin:
            return self.beginPos
        return self.endPos

    def getAbsoluteBegin( self ):
        """ Provides 0-based position starting from
            the beginning of the input stream """
        result = self.begin
        current = self
        while current.parent is not None:
            current = current.parent
            result += current.begin
        return result

    def getAbsoluteEnd( self ):
        """ Provides 0-based position starting from
            the beginning of the input stream """
        if self.parent is None:
            return self.end

        return self.getAbsoluteBegin() + self.end

    def __str__( self ):
        " Converts to a string "


class ControlFlow:
    " Represents one python file content "

    def __init__( self ):
        self.bangLine = None        # Bang line fragment
        self.encodingLine = None    # Encoding line fragment

        self.body = []              # List of global scope fragments

    def serialize( self, buf ):
        " Serializes the object basing on the buffer parsed "
        self.bang.serialize( buf )
        self.encoding.serialize( buf )
        for item in self.body:
            item.serialize( buf )
        return


class BangLine( Fragment ):
    " Represents a line with the bang notation "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayString( self, buf = None ):
        " Provides the actual bang line "
        content = self.getContent( buf )
        return content.replace( "#!", "", 1 ).strip()


class EncodingLine( Fragment ):
    " Represents a line with the file encoding "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayString( self, buf = None ):
        " Provides the encoding "
        match = CODING_REGEXP.search( self.getContent( buf ) )
        if match:
            return match.group( 1 ).lower()
        raise Exception( "Inconsistency: no encoding " \
                         "found in th encoding line" )


class Comment( Fragment ):
    " Represents a one or many lines comment "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayString( self, buf = None ):
        " Provides the comment without the syntactic shugar "
        content = [ line.strip()[ 1: ] for line \
                    in self.getContent( buf ).split( '\n' ) ]

        # Identify the number of leading spaces after the 'hash' character
        # common for all the lines
        leadingCharCounts = []
        for line in content:
            count = 0
            for char in line:
                if char == " ":
                    count += 1
                else:
                    break
            if count != 0:
                leadingCharCounts.append( count )

        if leadingCharCounts:
            spacesToStrip = min( leadingCharCounts )
            content = [ line[ spacesToStrip : ] for line in content ]
        return '\n'.join( content )



