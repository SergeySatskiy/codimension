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

"""
CML utilities
"""

from PyQt4.QtGui import QColor




class CMLCommentBase:
    " Base class for all the CML comments "

    def __init__( self ):
        return

    @staticmethod
    def isValid( cmlComment ):
        " Tells is the comment is a valid one "
        return False

    @staticmethod
    def match( cmlComments ):
        " Provides an instance of the comment in the container of comments "
        return None

    @staticmethod
    def description():
        " Provides the CML comment description "
        return ""

    @staticmethod
    def generate( pos = 1 ):
        " Generates the appropriate CML comment line "
        return ""



class CMLsw( CMLCommentBase ):
    " Covers the 'if' statement CML SW (switch branches) comments "

    CODE = "sw"

    def __init__( self ):
        CMLCommentBase.__init__( self )
        return

    @staticmethod
    def isValid( cmlComment ):
        return cmlComment.recordType == CMLsw.CODE and \
               CMLVersion.isValid( cmlComment )

    @staticmethod
    def match( cmlComments ):
        for cmlComment in cmlComments:
            if CMLsw.isValid( cmlComment ):
                return cmlComment
        return None

    @staticmethod
    def description():
        " Provides the CML comment description "
        return "The '" + CMLsw.CODE + \
               "' comment is used for 'if' and 'elif' statements " \
               "to switch default branch location i.e. to have the 'No' branch at the right.\n" \
               "Supported properties: none\n\n" \
               "Example:\n" \
               "# cml 1 " + CMLsw.CODE

    @staticmethod
    def generate( pos = 1 ):
        " Generates a complete line to be inserted "
        return " " * (pos -1) + "# cml 1 sw"



class CMLcc( CMLCommentBase ):
    " Covers 'Custom Colors' spec for most of the items "

    CODE = "cc"

    def __init__( self ):
        CMLCommentBase.__init__( self )
        return

    @staticmethod
    def isValid( cmlComment ):
        # test the properties too
        return cmlComment.recordType == CMLcc.CODE and \
               CMLVersion.isValid( cmlComment )

    @staticmethod
    def match( cmlComments ):
        for cmlComment in cmlComments:
            if CMLcc.isValid( cmlComment ):
                return cmlComment
        return None

    @staticmethod
    def description():
        " Provides the CML comment description "
        return "The '" + CMLcc.CODE + \
               "' comment is used for custom colors of most of " \
               "the graphics items.\n" \
               "Supported properties:\n" \
               "- 'background': background color for the item\n" \
               "- 'foreground': foreground color for the item\n" \
               "Color spec formats:\n" \
               "- '#hhhhhh': hexadecimal RGB\n" \
               "- '#hhhhhhhh': hexadecimal RGB + alpha\n" \
               "- 'ddd,ddd,ddd': decimal RGB\n" \
               "- 'ddd,ddd,ddd,ddd': decimal RGB + alpha\n\n" \
               "Example:\n" \
               "# cml 1 " + CMLcc.CODE + " backgound=#f6f4e4 foreground=#000000"

    @staticmethod
    def generate( backgound, foreground, pos = 1 ):
        " Generates a complete line to be inserted "
        res = " " * (pos -1) + "# cml 1 cc"
        if backgound is not None:
            bg = background.name()
            bgalpha = backgound.alpha()
            if bgalpha != 255:
                bg += hex( bgalpha )[ 2: ]
            res += " background=" + bg
        if foreground is not None:
            fg = foreground.name()
            fgalpha = foreground.alpha()
            if fgalpha != 255:
                fg += hex( fgalpha )[ 2: ]
            res += " foreground=" + fg

        return res

    @staticmethod
    def getColors( cmlComment ):
        fg = None
        bg = None
        if "background" in cmlComment.properties:
            bg = CMLcc.readColor( cmlComment.properties[ "background" ] )
        if "foreground" in cmlComment.properties:
            fg = CMLcc.readColor( cmlComment.properties[ "foreground" ] )
        return bg, fg

    @staticmethod
    def readColor( color ):
        """ Four variations are supported:
            #hhhhhh             hexadecimal rgb
            #hhhhhhhh           hexadecimal rgb and alpha
            ddd,ddd,ddd         decimal rgb
            ddd,ddd,ddd,ddd     decimal rgb and alpha
        """
        if color.startswith( '#' ):
            color = color[ 1: ]
            length = len( color )
            if length not in [ 6, 8 ]:
                raise Exception( "Invalid hexadecimal color format: #" + color )

            try:
                # The most common case
                r = int( color[ 0:2 ], 16 )
                CMLcc.checkColorRange( r )
                g = int( color[ 2:4 ], 16 )
                CMLcc.checkColorRange( g )
                b = int( color[ 4:6 ], 16 )
                CMLcc.checkColorRange( b )

                if length == 6:
                    return QColor( r, g, b )
                a = int( color[ 6:8 ], 16 )
                CMLcc.checkColorRange( a )
                return QColor( r, g, b, a )
            except:
                raise Exception( "Invalid hexadecimal color format: #" + color )

        parts = color.split( ',' )
        length = len( parts )
        if length not in [ 3, 4 ]:
            raise Exception( "Invalid decimal color format: " + color )

        try:
            r = int( parts[ 0 ].strip() )
            CMLcc.checkColorRange( r )
            g = int( parts[ 1 ].strip() )
            CMLcc.checkColorRange( g )
            b = int( parts[ 2 ].strip() )
            CMLcc.checkColorRange( b )

            if length == 4:
                a = int( parts[ 3 ].strip() )
                CMLcc.checkColorRange( a )
        except:
            raise Exception( "Invalid decimal color format: " + color )

        if length == 3:
            return QColor( r, g, b )
        return QColor( r, g, b, a )

    @staticmethod
    def checkColorRange( value ):
        if value < 0 or value > 255:
            raise Exception( "Invalid color value" )



class CMLVersion:
    " Describes the current CML version "

    VERSION = 1     # Current CML version
    COMMENT_TYPES = { CMLsw.CODE: CMLsw,
                      CMLcc.CODE: CMLcc }

    def __init__( self ):
        return

    @staticmethod
    def isValid( cmlComment ):
        return cmlComment.version <= CMLVersion.VERSION

    @staticmethod
    def getType( cmlComment ):
        " Provides the supported type of the comment; None otherwise "
        try:
            return CMLVersion.COMMENT_TYPES[ cmlComment.recordType ]
        except KeyError:
            return None



