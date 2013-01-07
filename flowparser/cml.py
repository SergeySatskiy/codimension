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
The file contains data types to represent CML (Codimension Markup Language)
statements
"""

import uuid
from flow import Fragment


class CMLVersion:
    " Holds information about the latest supported version "

    version = "1.0"     # Current CML version

    def __init__( self ):
        pass

    @staticmethod
    def isSupported( otherVersion ):
        " Returns True if supported "
        try:
            # The other version comes as string
            value = float( otherVersion )
            return value <= float( CMLVersion.version )
        except:
            return False

    def __str__( self ):
        " Converts to string "
        return "Current CML version: " + self.version



class RecordType:
    " Holds information about record types "

    independentRecord = "I"
    scopeRecord = "S"

    def __init__( self ):
        pass

    @staticmethod
    def isSupported( otherType ):
        " Returns True if it is supported "
        return otherType in [ RecordType.independentRecord,
                              RecordType.scopeRecord ]


class RecordSubType:
    " Holds information about supported record subtypes "

    scopeBegin = "SB"
    scopeEnd = "SE"
    continuation = "C"

    def __init__( self ):
        pass

    @staticmethod
    def isSupported( otherSubtype ):
        " Returns True if it is supported "
        return otherSubtype in [ RecordSubType.scopeBegin,
                                 RecordSubType.scopeEnd,
                                 RecordSubType.continuation ]



class CMLRecord( Fragment ):
    " Represents a single (one or many lines) CML record "

    def __init__( self ):
        Fragment.__init__( self )
        return

    def getVersion( self, buf = None ):
        " Provides the record version or throws an exception "
        contentParts = self.getContent( buf ).split()
        # The version is the third field
        if len( contentParts ) < 3:
            raise Exception( "Unexpected CML record format" )

        try:
            return float( contentParts[ 2 ] )
        except:
            raise Exception( "Unexpected CML record version format" )

    def getType( self, buf = None ):
        " Provides the record type or throws an exception "
        contentParts = self.getContent( buf ).split()
        # The type must be fourth field
        if len( contentParts ) < 4:
            raise Exception( "Unexpected CML record format" )

        return contentParts[ 3 ]

    def getSubType( self, buf = None ):
        " Provides the record subtype or throws an exception "
        contentParts = self.getContent( buf ).split()
        # The subtype must be the fifth field
        if len( contentParts ) < 5:
            raise Exception( "Unexpected CML record format" )

        return contentParts[ 4 ]

    def getUUID( self, buf = None ):
        " Provides the record UUID or throws an exception "
        # UUID might be there but might be not
        contentParts = self.getContent( buf ).split()
        if len( contentParts ) < 6:
            raise Exception( " The record does not have UUID" )
        return contentParts[ 5 ]

    def __str__( self ):
        " Converts to string "
        return "CML record: " + Fragment.__str__( self )



# Utility functions to construct various records

def generateScopeBlock( text ):
    " Generates scope record begin and end records "

    recordBegin = []
    recordUUID = str( uuid.uuid1() )

    textParts = text.split( '\n' )
    recordBegin.append( "# cml 1.0 S SB " + recordUUID + " " + textParts[ 0 ] )
    for part in textParts[ 1: ]:
        recordBegin.append( "# cml 1.0 C " + part )

    recordEnd = "# cml 1.0 S SE " + recordUUID
    return recordBegin, recordEnd

