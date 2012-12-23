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
        " Serializes the object "
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

        if self.bangLine is not None:
            self.bangLine.serialize()
        if self.encodingLine is not None:
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


#
# Codimension recognizes three types of comments:
# - standalone comments
# - leading comments
# - side comment
# In all cases a comment consists of one or more comment lines
#


class CommentLine( Fragment ):
    " Represents a single comment line "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getDisplayValue( self, buf = None ):
        " Provides the comment line content without trailing spaces "
        return self.getContent( buf ).strip()

    def __str__( self ):
        " Converts to a string "
        return "Comment line: " + Fragment.__str__( self )



# Strictly speaking there is no need to derive from Fragment because
# a comment consists of a set of lines which are fragments themseves.
# It is however suits well for the leading and standalone comments so
# it was decided to have this derivation.
class Comment( Fragment ):
    " Represents a one or many lines comment "

    def __init__( self ):
        Fragment.__init__( self )
        self.commentLines = []      # CommentLine instances
        return

    def getDisplayValue( self, buf = None ):
        " Provides the comment without trailing spaces "
        if not self.commentLines:
            return ""

        beginPositions = set( [ line.beginPos for line in self.commentLines ] )
        sameShift = ( len( beginPositions ) == 1 )
        minShift = min( beginPositions )

        visibleLines = []
        currentLine = self.commentLines[ 0 ].beginLine - 1
        for line in self.commentLines:
            if line.beginLine - currentLine > 1:
                # Insert empty lines
                for count in xrange( 1, line.beginLine - currentLine ):
                    visibleLines.append( "" )
            if sameShift:
                visibleLines.append( line.getContent( buf ).strip() )
            else:
                if line.beginPos > minShift:
                    visibleLines.append( ( line.beginPos - minShift ) * " " + \
                                         line.getContent( buf ).strip() )
                else:
                    visibleLines.append( line.getContent( buf ).strip() )

        return "\n".join( visibleLines )

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        for line in self.commentLines:
            line.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Comment: " + Fragment.__str__( self ) + "\n" + \
               "\n".join( [ str( line ) for line in self.commentLines ] )


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


class Decorator( Fragment ):
    " Represents a single decorator "

    def __init__( self ):
        Fragment.__init__( self )

        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.name = None            # Fragment for a name
        self.arguments = None       # Fragment for arguments:
                                    # Starting from '(', ending with ')'
        return

    def __str__( self ):
        " Converts to a string "
        return "Decorator: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Name: " + str( self.name ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Arguments: " + str( self.arguments )

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        self.name.serialize()
        if self.arguments is not None:
            self.arguments.serialize()
        return


class CodeBlock( Fragment ):
    " Represents a code block "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment
        self.body = None            # Fragment for the body
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        self.body.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Code block: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Body: " + str( self.body )


class Function( Fragment ):
    " Represents a single function "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.decorators = []        # Instances of Decorator
        self.sideComment = None     # Fragment for the side comment

        self.name = None            # Fragment for the function name
        self.arguments = None       # Fragment for the function arguments:
                                    # Starting from '(', ending with ')'
        self.docstring = None       # Docstring fragment

        self.body = []              # Fragment for the body
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        for decor in self.decorators:
            decor.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        self.name.serialize()
        if self.arguments is not None:
            self.arguments.serialize()
        if self.docstring is not None:
            self.docstring.serialize()
        for item in self.body:
            item.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        if self.decorators:
            decorPart = "\n" + \
                        "\n".join( [ str( decor ) \
                                     for decor in self.decorators ] )
        else:
            decorPart = "None"

        return "Function: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Decorators: " + decorPart + "\n" \
               "Name: " + str( self.name ) + "\n" \
               "Arguments: " + str( self.arguments ) + "\n" \
               "Docstring: " + str( self.docstring ) + "\n" \
               "Body:\n" + \
               "\n".join( [ str( item ) for item in self.body ] )



class Class( Fragment ):
    " Represents a single class "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.decorators = []        # Instances of Decorator
        self.sideComment = None     # Fragment for the side comment

        self.name = None            # Fragment for the function name
        self.baseClasses = []       # Fragments for base classes names

        self.docstring = None       # Docstring fragment
        self.body = []              # Fragment for the body
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        for decor in self.decorators:
            decor.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        self.name.serialize()
        for baseClass in self.baseClasses:
            baseClass.serialize()
        if self.docstring is not None:
            self.docstring.serialize()
        for item in self.body:
            item.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        if self.decorators:
            decorPart = "\n" + \
                        "\n".join( [ str( decor ) \
                                     for decor in self.decorators ] )
        else:
            decorPart = "None"

        if self.baseClasses:
            baseClassPart = "\n" + \
                        "\n".join( [ str( baseClass ) \
                                     for baseClass in self.baseClasses ] )
        else:
            baseClassPart = "None"

        return "Class: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Decorators: " + decorPart + "\n" + \
               "Base classes: " + baseClassPart + "\n" \
               "Name: " + str( self.name ) + "\n" \
               "Docstring: " + str( self.docstring ) + "\n" \
               "Body:\n" + \
               "\n".join( [ str( item ) for item in self.body ] )



class Break( Fragment ):
    " Represents a single break statement "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Break: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment )


class Continue( Fragment ):
    " Represents a single continue statement "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Continue: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment )


class Return( Fragment ):
    " Represents a single return statement "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.value = None           # Fragment for the value
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        if self.value is not None:
            self.value.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Return: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Value: " + str( self.value )


class Raise( Fragment ):
    " Represents a single raise statement "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.value = None           # Fragment for the value
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        if self.value is not None:
            self.value.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Raise: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Value: " + str( self.value )



class Assert( Fragment ):
    " Represents a single assert statement "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.test = None            # Fragment for the test expression
        self.message = None         # Fragment for the message
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        if self.test is not None:
            self.test.serialize()
        if self.message is not None:
            self.message.serialize()
        return

    def __str__( self ):
        " Converts to a string "
        return "Assert: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Test: " + str( self.test ) + "\n" \
               "Message: " + str( self.message )


class While( Fragment ):
    " Represents a single while loop "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.condition = None       # Fragment for the condition
        self.body = []
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        if self.condition is not None:
            self.condition.serialize()
        for item in self.body:
            item.serialize()
        return

    def __str__( self ):
        " Converts to a string "

        return "While: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "condition: " + str( self.condition ) + "\n" \
               "Body:\n" + \
               "\n".join( [ str( item ) for item in self.body ] )


#
# NOTE: The For instances must not be instantiated for list comprehensions
#
class For( Fragment ):
    " Represents a single for loop "

    def __init__( self ):
        Fragment.__init__( self )
        self.leadingComment = None  # Fragment for the leading comment
        self.sideComment = None     # Fragment for the side comment

        self.iteration = None       # Fragment for the iteration
        self.body = []
        return

    def serialize( self ):
        " Serializes the object "
        Fragment.serialize( self )
        if self.leadingComment is not None:
            self.leadingComment.serialize()
        if self.sideComment is not None:
            self.sideComment.serialize()
        if self.iteration is not None:
            self.iteration.serialize()
        for item in self.body:
            item.serialize()
        return

    def __str__( self ):
        " Converts to a string "

        return "While: " + Fragment.__str__( self ) + "\n" \
               "Leading comment: " + str( self.leadingComment ) + "\n" \
               "Side comment: " + str( self.sideComment ) + "\n" \
               "Iteration: " + str( self.iteration ) + "\n" \
               "Body:\n" + \
               "\n".join( [ str( item ) for item in self.body ] )


