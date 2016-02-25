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
        return "CML comment 'sw'; used for 'if' and 'elif' statements " \
               "to switch default branch location."

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
        return "CML comment 'sw'; used for 'if' and 'elif' statements " \
               "to switch default branch location."

    @staticmethod
    def generate( pos = 1 ):
        " Generates a complete line to be inserted "
        return " " * (pos -1) + "# cml 1 sw"






class CMLVersion:
    " Describes the current CML version "

    VERSION = 1     # Current CML version
    COMMENT_TYPES = { CMLsw.CODE: CMLsw }

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



