# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Various items used to represent a control flow on a virtual canvas "

class CellElement:
    " Base class for all the elements which could be found on the canvas "

    UNKNOWN = -1

    VACANT = 0
    H_SPACER = 1
    V_SPACER = 2

    NO_SCOPE = 99
    FILE_SCOPE = 100
    FUNC_SCOPE = 101
    CLASS_SCOPE = 102
    FOR_SCOPE = 103
    WHILE_SCOPE = 104
    TRY_SCOPE = 105
    WITH_SCOPE = 106
    DECOR_SCOPE = 107
    ELSE_SCOPE = 108
    EXCEPT_SCOPE = 109
    FINALLY_SCOPE = 110

    CODE_BLOCK = 200
    BREAK = 201
    CONTINUE = 202
    RETURN = 203
    RAISE = 204
    ASSERT = 205
    SYSEXIT = 206
    IMPORT = 207
    COMMENT = 208

    CONNECTOR = 300

    def __init__( self ):
        self.kind = self.UNKNOWN
        self.reference = None   # reference to the control flow object

        # Filled when rendering is called
        self.width = None
        self.height = None
        return

    def __str__( self ):
        return kindToString( self.kind ) + \
               "[" + str( self.width ) + ":" + str( self.height ) + "]"

    def render( self, settings ):
        " Renders the graphics considering settings "
        raise Exception( "render() is not implemented for " +
                         kindToString( self.kind ) )

    def getConnections( self ):
        " Provides the connection points the element uses "
        # Connections are described as a list of single letter strings
        # Each letter represents a cell edge: N, S, W, E
        raise Exception( "getConnections() is not implemented for " +
                         kindToString( self.kind ) )

    def draw( self, rect, scene, settings ):
        """
        Draws the element on the real canvas
        in the given rect respecting settings
        """
        raise Exception( "draw() is not implemented for " +
                         kindToString( self.kind ) )


class ScopeCellElement( CellElement ):

    UNKNOWN = -1

    TOP_LEFT = 0
    LEFT = 1
    BOTTOM_LEFT = 2
    DECLARATION = 3
    SIDE_COMMENT = 4
    LEADING_COMMENT = 5
    DOCSTRING = 6
    TOP = 7
    BOTTOM = 8

    def __init__( self ):
        CellElement.__init__( self )
        self.subKind = self.UNKNOWN
        return

    def __str__( self ):
        return CellElement.__str__( self ) + \
               "(" + scopeCellElementToString( self.subKind ) + ")"


__kindToString = {
    CellElement.UNKNOWN:            "UNKNOWN",
    CellElement.VACANT:             "VACANT",
    CellElement.H_SPACER:           "H_SPACER",
    CellElement.V_SPACER:           "V_SPACER",
    CellElement.FILE_SCOPE:         "FILE_SCOPE",
    CellElement.FUNC_SCOPE:         "FUNC_SCOPE",
    CellElement.CLASS_SCOPE:        "CLASS_SCOPE",
    CellElement.CODE_BLOCK:         "CODE_BLOCK",
    CellElement.BREAK:              "BREAK",
    CellElement.CONTINUE:           "CONTINUE",
    CellElement.RETURN:             "RETURN",
    CellElement.RAISE:              "RAISE",
    CellElement.ASSERT:             "ASSERT",
    CellElement.SYSEXIT:            "SYSEXIT",
    CellElement.IMPORT:             "IMPORT",
    CellElement.COMMENT:            "COMMENT",
    CellElement.CONNECTOR:          "CONNECTOR",
}


def kindToString( kind ):
    " Provides a string representation of a element kind "
    return __kindToString[ kind ]


_scopeCellElementToString = {
    ScopeCellElement.UNKNOWN:           "UNKNOWN",
    ScopeCellElement.TOP_LEFT:          "TOP_LEFT",
    ScopeCellElement.LEFT:              "LEFT",
    ScopeCellElement.BOTTOM_LEFT:       "BOTTOM_LEFT",
    ScopeCellElement.DECLARATION:       "DECLARATION",
    ScopeCellElement.SIDE_COMMENT:      "SIDE_COMMENT",
    ScopeCellElement.LEADING_COMMENT:   "LEADING_COMMENT",
    ScopeCellElement.DOCSTRING:         "DOCSTRING",
    ScopeCellElement.TOP:               "TOP",
    ScopeCellElement.BOTTOM:            "BOTTOM"
}

def scopeCellElementToString( kind ):
    " Provides a string representation of a element kind "
    return _scopeCellElementToString[ kind ]




class VacantCell( CellElement ):
    " Represents a vacant cell which can be later used for some other element "

    def __init__( self ):
        CellElement.__init__( self )
        self.kind = CellElement.VACANT
        return

    def render( self, settings ):
        self.width = 0
        self.height = 0
        return (self.width, self.height)

    def getConnections( self ):
        return []

    def draw( self, rect, scene, settings ):
        return



class CodeBlockCell( CellElement ):
    " Represents a single code block "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.CODE_BLOCK
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class FileScopeCell( ScopeCellElement ):
    " Represents a file scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.FILE_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class FunctionScopeCell( ScopeCellElement ):
    " Represents a function scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.FUNC_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ClassScopeCell( ScopeCellElement ):
    " Represents a class scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.CLASS_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ForScopeCell( ScopeCellElement ):
    " Represents a for-loop scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.FOR_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class WhileScopeCell( ScopeCellElement ):
    " Represents a while-loop scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.WHILE_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class TryScopeCell( ScopeCellElement ):
    " Represents a try-except scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.TRY_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class WithScopeCell( ScopeCellElement ):
    " Represents a with scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.WITH_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class DecoratorScopeCell( ScopeCellElement ):
    " Represents a decorator scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.DECOR_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ElseScopeCell( ScopeCellElement ):
    " Represents an else scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.ELSE_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ExceptScopeCell( ScopeCellElement ):
    " Represents an except scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.EXCEPT_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class FinallyScopeCell( ScopeCellElement ):
    " Represents a finally scope element "

    def __init__( self, ref, kind ):
        CellElement.__init__( self )
        self.kind = CellElement.FINALLY_SCOPE
        self.reference = ref
        self.subKind = kind
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class BreakCell( CellElement ):
    " Represents a single break statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.BREAK
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ContinueCell( CellElement ):
    " Represents a single continue statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.CONTINUE
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ReturnCell( CellElement ):
    " Represents a single return statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.RETURN
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class RaiseCell( CellElement ):
    " Represents a single raise statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.RAISE
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class AssertCell( CellElement ):
    " Represents a single assert statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.ASSERT
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class SysexitCell( CellElement ):
    " Represents a single sys.exit(...) statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.SYSEXIT
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ImportCell( CellElement ):
    " Represents a single import statement "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.IMPORT
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class CommentCell( CellElement ):
    " Represents a single independent comment "

    def __init__( self, ref ):
        CellElement.__init__( self )
        self.kind = CellElement.COMMENT
        self.reference = ref
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )



class ConnectorCell( CellElement ):
    " Represents a single connector cell "

    NORTH = 0
    SOUTH = 1
    WEST = 2
    EAST = 3
    CENTER = 4

    def __init__( self, connections ):
        """ Connections are supposed to be a list of tuples e.g
            [ (NORTH, SOUTH), (EAST, CENTER) ] """
        CellElement.__init__( self )
        self.kind = CellElement.CONNECTOR
        self.reference = None
        self.connections = connections
        return

    def render( self, settings ):
        raise Exception( "Not implemented yet" )

    def draw( self, rect, scene, settings ):
        raise Exception( "Not implemented yet" )


