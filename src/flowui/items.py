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

    FILE_HEADER = 100
    FUNC_HEADER = 101
    CLASS_HEADER = 102

    CODE_BLOCK = 200

    def __init__( self ):
        self.kind = self.UNKNOWN
        self.reference = None   # reference to the control flow object

        # Filled when rendering is called
        self.width = None
        self.height = None
        return

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

    def draw( self, rect, canvas, settings ):
        """
        Draws the element on the real canvas
        in the given rect respecting settings
        """
        raise Exception( "draw() is not implemented for " +
                         kindToString( self.kind ) )


__kindToString = {
    CellElement.UNKNOWN:            "UNKNOWN",
    CellElement.VACANT:             "VACANT",
    CellElement.H_SPACER:           "H_SPACER",
    CellElement.V_SPACER:           "V_SPACER",
    CellElement.FILE_HEADER:        "FILE_HEADER",
    CellElement.FUNC_HEADER:        "FUNC_HEADER",
    CellElement.CLASS_HEADER:       "CLASS_HEADER",
    CellElement.CODE_BLOCK:         "CODE_BLOCK",
}


def kindToString( kind ):
    " Provides a string representtion of a element kind "
    return __kindToString[ kind ]



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

    def draw( self, rect, canvas, settings ):
        return


