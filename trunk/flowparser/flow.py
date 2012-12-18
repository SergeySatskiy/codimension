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
import sys


CODING_REGEXP = re.compile( r'''coding[:=]\s*([-\w_.]+)''' )

#
# The Fragment class is a basic building block for anything found
# in a python code.
#

class Fragment:
    " Represents a single text fragment of a python file"

    def __init__( self ):

        # Minimal necessary information.
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
        # the editor buffer directly.
        self.beginLine = None   # 1-based line number
        self.beginPos = None    # 1-based position number in the line
        self.endLine = None     # 1-based line number
        self.endPos = None      # 1-based position number in the line

        # Serialization support
        self.serialized = False # True if has been serialized
        return

    def isSerialized( self ):
        " True if the object has already been serialized "
        return self.serialized

    def serialize( self ):
        " Serializes the object basing on the buffer parsed "
        self.serialized = True
        return

    def getContent( self, buf = None ):
        " Provides the content of the fragment "
        if buf is None and not self.serialized:
            raise Exception( "Cannot get content of not serialized " \
                             "fragment without its buffer" )

        if self.serialized:
            # Find the global scope parent
            current = self
            while current.parent is not None:
                current = current.parent
            return current.content[ self.begin : self.end + 1 ]

        # Non-serialized
        return buf[ self.begin : self.end + 1 ]

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
        if forBegin:
            return self.beginLine
        return self.endLine

    def getPos( self, forBegin = True ):
        " Provides the position in the specified end line "
        if forBegin:
            return self.beginPos
        return self.endPos

    def getAbsoluteBegin( self ):
        """ Provides 0-based position starting from
            the beginning of the input stream """
        return self.begin

    def getAbsoluteEnd( self ):
        """ Provides 0-based position starting from
            the beginning of the input stream """
        return self.end

    def __str__( self ):
        " Converts to a string "
        return "Fragment[" + str( self.begin ) + ":" + str( self.end ) + \
               "] (" + str( self.beginLine ) + "," + str( self.beginPos ) + \
               ") (" + str( self.endLine ) + "," + str( self.endPos ) + ")"


class ControlFlow( Fragment ):
    " Represents one python file content "

    def __init__( self ):
        Fragment.__init__( self )
        self.parent = None          # The only object which has to have it None

        self.bangLine = None        # Bang line Fragment
        self.encodingLine = None    # Encoding line Fragment

        self.body = []              # List of global scope fragments. It could be:
                                    # Docstring, Comment, CodeBlock,
                                    # Function, Class
                                    # For, While, Try, With, Assert, If, Pass,
                                    # Raise, Return etc.

        # Additional field to support serialization
        self.content = None     # Not None when the ControlFlow is serialized
        return

    def serialize( self, buf ):
        " Serializes the object basing on the buffer parsed "

        self.content = buf

        self.bangLine.serialize()
        self.encodingLine.serialize()
        for item in self.body:
            item.serialize()
        return

    def __str__( self ):
        " Converts to string "
        return "Bang: " + str( self.bangLine ) + "\n" \
               "Encoding: " + str( self.encodingLine ) + "\n" \
               "Body:\n" + "\n".join( [ str( item ) for item in self.body ] )


class BangLine( Fragment ):
    " Represents a line with the bang notation "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayValue( self, buf = None ):
        " Provides the actual bang line "
        content = self.getContent( buf )
        return content.replace( "#!", "", 1 ).strip()

    def __str__( self ):
        " Converts to a string "
        return "Bang line: " + Fragment.__str__( self )


class EncodingLine( Fragment ):
    " Represents a line with the file encoding "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayValue( self, buf = None ):
        " Provides the encoding "
        match = CODING_REGEXP.search( self.getContent( buf ) )
        if match:
            return match.group( 1 ).lower()
        raise Exception( "Inconsistency: no encoding " \
                         "found in th encoding line" )

    def __str__( self ):
        " Converts to a string "
        return "Encoding line: " + Fragment.__str__( self )


class Comment( Fragment ):
    " Represents a one or many lines comment "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayValue( self, buf = None ):
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

    def __str__( self ):
        " Converts to a string "
        return "Comment: " + Fragment.__str__( self )


class Docstring( Fragment ):
    " Represents a docstring "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayValue( self, buf = None ):
        " Provides the docstring without syntactic sugar "

        rawContent = self.getContent( buf )

        # First, strip quotes
        stripCount = 1
        if rawContent.startswith( '"""' ) or rawContent.startswith( "'''" ):
            stripCount = 3
        return self.trimDocstring( rawContent[ stripCount : -stripCount ] )

    @staticmethod
    def trimDocstring( docstring ):
        " Taken from http://www.python.org/dev/peps/pep-0257/ "

        if not docstring:
            return ''

        # Convert tabs to spaces (following the normal Python rules)
        # and split into a list of lines:
        lines = docstring.expandtabs().splitlines()

        # Determine minimum indentation (first line doesn't count):
        indent = sys.maxint
        for line in lines[ 1: ]:
            stripped = line.lstrip()
            if stripped:
                indent = min( indent, len( line ) - len( stripped ) )

        # Remove indentation (first line is special):
        trimmed = [ lines[ 0 ].strip() ]
        if indent < sys.maxint:
            for line in lines[ 1: ]:
                trimmed.append( line[ indent: ].rstrip() )

        # Strip off trailing and leading blank lines:
        while trimmed and not trimmed[ -1 ]:
            trimmed.pop()
        while trimmed and not trimmed[ 0 ]:
            trimmed.pop( 0 )

        # Return a single string:
        return '\n'.join( trimmed )

    def __str__( self ):
        " Converts to a string "
        return "Docstring: " + Fragment.__str__( self )


class Argument( Fragment ):
    " Represents a single argument for anything which may have it "

    def __init__( self ):
        Fragment.__init__( self )

        self.nameComment = None     # Fragment for a name comment
        self.name = None            # Fragment for the name

        self.defaultValComment = None   # Fragment for a default value comment
        self.defaultVal = None          # Fragment or Call for a default value
        return

    def __str__( self ):
        " Converts to a string "
        return "Argument: " + Fragment.__str__( self ) + "\n" \
               "  Name comment: " + str( self.nameComment ) + "\n" \
               "  Name: " + str( self.name ) + "\n" \
               "  Default value comment: " + str( self.defaultValComment ) + "\n" \
               "  Default value: " + str( self.defaultVal )



class Call( Fragment ):
    " Represent a single function call "

    def __init__( self ):
        Fragment.__init__( self )

        self.leadingComment = None  # Comment fragment
        self.sideComment = None     # Comment fragment

        self.name = None            # Name fragment
        self.arguments = []         # Arguments instances
        return





class Decorator( Fragment ):
    " Represents a single decorator "

    def __init__( self ):
        Fragment.__init__( self )

        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.name = None            # Fragment for a name
        self.arguments = []         # Arguments instances
        return

    def __str__( self ):
        " Converts to a string "
        result = "Decorator: " + Fragment.__str__( self ) + "\n" \
                 "  Leading comment: " + str( self.leadingComment ) + "\n" \
                 "  Name: " + str( self.name ) + "\n" \
                 "  Side comment: " + str( self.sideComment )
        for argument in self.arguments:
            result += "\n  Argument: " + str( argument )
        return result



class CodeBlock( Fragment ):
    " Represents a code block "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None
        self.body = []                  # Pairs (Fragment, Comment)
        return


