#
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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" encoding related functions """

import re
from types  import UnicodeType
from codecs import BOM_UTF8, BOM_UTF16, BOM_UTF32
import thirdparty.chardet as chardet
from PyQt4.QtCore import QString


coding_regexps = [
    (2, re.compile(r'''coding[:=]\s*([-\w_.]+)''')),
    (1, re.compile(r'''<\?xml.*\bencoding\s*=\s*['"]([-\w_.]+)['"]\?>''')),
                 ]
supportedCodecs = [ 'utf-8',
                    'iso8859-1',  'iso8859-15', 'iso8859-2',  'iso8859-3',
                    'iso8859-4',  'iso8859-5',  'iso8859-6',  'iso8859-7',
                    'iso8859-8',  'iso8859-9',  'iso8859-10', 'iso8859-11',
                    'iso8859-13', 'iso8859-14', 'iso8859-16', 'latin-1',
                    'koi8-r',     'koi8-u',     'utf-16',
                    'cp037',  'cp424',  'cp437',  'cp500',  'cp737', 'cp775',
                    'cp850',  'cp852',  'cp855',  'cp856',  'cp857', 'cp860',
                    'cp861',  'cp862',  'cp863',  'cp864',  'cp865', 'cp866',
                    'cp874',  'cp875',  'cp932',  'cp949',  'cp950', 'cp1006',
                    'cp1026', 'cp1140', 'cp1250', 'cp1251', 'cp1252',
                    'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257',
                    'cp1258',
                    'ascii' ]


class CodingError( Exception ):
    """ Exception for incorrect coding """

    def __init__( self, coding ):

        Exception.__init__( self )
        self.errorMessage = "The coding '" + coding + \
                            "' is wrong for the given text"
        return

    def __repr__(self):

        return unicode( self.errorMessage )

    def __str__(self):

        return str( self.errorMessage )


def get_coding( text ):
    """ Provides the coding of the text """

    lines = text.splitlines()
    for coding in coding_regexps:
        coding_re = coding[ 1 ]
        head = lines[ :coding[0] ]
        for line in head:
            match = coding_re.search( line )
            if match:
                return match.group( 1 ).lower()
    return None

def decode( text ):
    """ Decodes the text """

    try:
        if text.startswith( BOM_UTF8 ):
            # UTF-8 with BOM
            return unicode( text[ len(BOM_UTF8): ], 'utf-8' ), 'utf-8-bom'

        if text.startswith( BOM_UTF16 ):
            # UTF-16 with BOM
            return unicode( text[ len(BOM_UTF16): ], 'utf-16' ), 'utf-16'

        if text.startswith( BOM_UTF32 ):
            # UTF-32 with BOM
            return unicode( text[ len(BOM_UTF32): ], 'utf-32' ), 'utf-32'

        coding = get_coding( text )
        if coding:
            return unicode( text, coding ), coding

    except ( UnicodeError, LookupError ):
        pass

    guess = None
    # Try the universal character encoding detector
    try:
        guess = chardet.detect( text )
        if guess and guess[ 'confidence' ] > 0.95 \
                 and guess[ 'encoding' ] is not None:
            codec = guess[ 'encoding' ].lower()
            return unicode( text, codec ), '%s-guessed' % codec
    except ( UnicodeError, LookupError ):
        pass

    # Assume UTF-8
    try:
        return unicode( text, 'utf-8' ), 'utf-8-guessed'
    except ( UnicodeError, LookupError ):
        pass

    # Use the guessed one even if confifence level is low
    if guess and guess[ 'encoding' ] is not None:
        try:
            codec = guess[ 'encoding' ].lower()
            return unicode( text, codec ), '%s-guessed' % codec
        except ( UnicodeError, LookupError ):
            pass

    # Assume Latin-1
    return unicode( text, "latin-1" ), 'latin-1-guessed'

def encode( text, orig_coding ):
    """ Encodes the text """

    if orig_coding == 'utf-8-bom':
        return BOM_UTF8 + text.encode( "utf-8" ), 'utf-8-bom'

    # Try declared coding spec
    coding = get_coding( text )
    if coding:
        try:
            return text.encode( coding ), coding
        except ( UnicodeError, LookupError ):
            # Error: Declared encoding is incorrect
            raise CodingError( coding )

    if orig_coding and orig_coding.endswith( '-selected' ):
        coding = orig_coding.replace( "-selected", "" )
        try:
            return text.encode( coding ), coding
        except ( UnicodeError, LookupError ):
            pass
    if orig_coding and orig_coding.endswith( '-default' ):
        coding = orig_coding.replace( "-default", "" )
        try:
            return text.encode( coding ), coding
        except ( UnicodeError, LookupError ):
            pass
    if orig_coding and orig_coding.endswith( '-guessed' ):
        coding = orig_coding.replace( "-guessed", "" )
        try:
            return text.encode( coding ), coding
        except ( UnicodeError, LookupError ):
            pass

    # Try saving as ASCII
    try:
        return text.encode( 'ascii' ), 'ascii'
    except UnicodeError:
        pass

    # Save as UTF-8 without BOM
    return text.encode( 'utf-8' ), 'utf-8'

def toUnicode( inputStr ):
    """ Converts a string to unicode """

    if isinstance( inputStr, QString ):
        return inputStr

    if type( inputStr ) is type( u"" ):
        return inputStr

    for codec in supportedCodecs:
        try:
            return unicode( inputStr, codec )
        except UnicodeError:
            pass
        except TypeError:
            break

    # we didn't succeed
    return inputStr

_escape = re.compile( eval( r'u"[&<>\"\u0080-\uffff]"' ) )
_escape_map = { "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;" }

def escape_entities( matchObject, escape_map = None ):
    """ Encodes html entities """

    if escape_map is None:
        escape_map = _escape_map

    char = matchObject.group()
    text = escape_map.get( char )
    if text is None:
        text = "&#%d;" % ord( char )
    return text

def html_encode( text, pattern = _escape ):
    """ Encodes a text for html """

    if not text:
        return ""

    text = pattern.sub( escape_entities, text )
    return text.encode( "ascii" )

_uescape = re.compile( ur'[\u0080-\uffff]' )

def escape_uentities( matchObject ):
    """ Encodes html entities """

    char = matchObject.group()
    text = "&#%d;" % ord( char )
    return text

def html_uencode( text, pattern = _uescape ):
    """ Encodes a unicode text for html """

    if not text:
        return ""

    try:
        if type( text ) is not UnicodeType:
            text = unicode( text, "utf-8" )
    except (ValueError,  LookupError):
        pass
    text = pattern.sub( escape_uentities, text )
    return text.encode( "ascii" )

def convertLineEnds( text, eol ):
    """ Converts the end of line characters in text to the given eol """

    if eol == '\r\n':
        regexp = re.compile( r"(\r(?!\n)|(?<!\r)\n)" )
        return regexp.sub( lambda m, eol = '\r\n': eol, text )
    elif eol == '\n':
        regexp = re.compile( r"(\r\n|\r)" )
        return regexp.sub( lambda m, eol = '\n': eol, text )
    elif eol == '\r':
        regexp = re.compile( r"(\r\n|\n)" )
        return regexp.sub( lambda m, eol = '\r': eol, text )
    else:
        return text

