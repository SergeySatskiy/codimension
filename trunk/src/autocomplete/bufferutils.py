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

" Various editor buffer related utilities "


from PyQt4.Qsci         import QsciLexerPython
from PyQt4.QtCore       import QString, QRegExp, Qt
from cdmbriefparser     import getBriefModuleInfoFromMemory


class TextCursorContext:
    " Holds the text cursor context for a python file "

    GlobalScope      = 1
    FunctionScope    = 2
    ClassScope       = 3
    ClassMethodScope = 4

    def __init__( self ):
        self.levels = []    # Each item is [infoObj, scope type]
        self.length = 0
        return

    def addFunction( self, infoObj ):
        " Adds nested function "
        if self.length == 0:
            self.levels.append( [ infoObj, self.FunctionScope ] )
        else:
            if self.levels[ self.length - 1 ][ 1 ] == self.ClassScope:
                self.levels.append( [ infoObj, self.ClassMethodScope ] )
            else:
                self.levels.append( [ infoObj, self.FunctionScope ] )
        self.length += 1
        return

    def getScope( self ):
        " Provides the deepest scope type "
        if self.length == 0:
            return self.GlobalScope
        return self.levels[ self.length - 1 ][ 1 ]

    def getInfoObj( self ):
        " Provides the deepest info object "
        if self.length == 0:
            return None
        return self.levels[ self.length - 1 ][ 0 ]

    def addClass( self, infoObj ):
        " Adds nested class "
        self.levels.append( [ infoObj, self.ClassScope ] )
        self.length += 1
        return

    def __scopeToString( self, scope ):
        " Converts scope constant to a string "
        if scope == self.GlobalScope:
            return "GlobalScope"
        if scope == self.FunctionScope:
            return "FunctionScope"
        if scope == self.ClassScope:
            return "ClassScope"
        if scope == self.ClassMethodScope:
            return "ClassMethodScope"
        return "UnknownScope"

    def __str__( self ):
        " Converts context to a string representation "
        retval = ""
        if self.length == 0:
            retval = "GlobalScope"

        first = True
        for level in self.levels:
            if first:
                first = False
            else:
                retval += " -> "
            retval += self.__scopeToString( level[ 1 ] ) + \
                      ":" + level[ 0 ].name + ":" + str( level[ 0 ].line )
        return retval

    def getLastScopeLine( self ):
        " Provides the last scope line "
        if self.length == 0:
            raise Exception( "No scopes found" )
        return self.levels[ self.length - 1 ][ 0 ].line

    def stripLevels( self, nonSpacePos ):
        " Strips the levels depending on the position "
        maxLevels = int( nonSpacePos / 4 )
        if maxLevels < self.length:
            self.levels = self.levels[ : maxLevels ]
            self.length = maxLevels
        return


def _IdentifyScope( infoObject, context, cursorLine ):
    " Searches for the hierarchy "

    # Find the closest global level class definition
    nearestClassLine = -1
    nearestClassInfo = None
    for klass in infoObject.classes:
        if klass.line > nearestClassLine and \
           klass.line < cursorLine:
            nearestClassLine = klass.line
            nearestClassInfo = klass

    # Find the closest global level function definition
    nearestFuncLine = -1
    nearestFuncInfo = None
    for func in infoObject.functions:
        if func.line > nearestClassLine and \
           func.line > nearestFuncLine and \
           func.line <= cursorLine:
            nearestFuncLine = func.line
            nearestFuncInfo = func

    if nearestClassLine == -1 and nearestFuncLine == -1:
        # No definitions before the line
        return

    # Check nested objects
    if nearestClassLine > nearestFuncLine:
        context.addClass( nearestClassInfo )
        _IdentifyScope( nearestClassInfo, context, cursorLine )
    else:
        context.addFunction( nearestFuncInfo )
        _IdentifyScope( nearestFuncInfo, context, cursorLine )
    return


def _getFirstNonSpacePos( text ):
    " Provides the index of the first non-space character in the given line "
    for pos in xrange( len( text ) ):
        if text[ pos ] not in [ ' ', '\n', '\r' ]:
            return pos
    return -1


def _endsWithTripleQuotedString( editor, line, pos ):
    " True if the position is a triple quoted string literal "
    editorPos = editor.positionFromLineIndex( line, pos )
    return editor.styleAt( editorPos ) in \
                        [ QsciLexerPython.TripleDoubleQuotedString,
                          QsciLexerPython.TripleSingleQuotedString ]


def getContext( editor, info = None ):
    " Detects the context where the text cursor is "

    # It is expected that this is a python editor.
    # If non-python editor is given, then a global context is provided

    context = TextCursorContext()

    lexer = editor.lexer()
    if lexer is None or not isinstance( lexer, QsciLexerPython ):
        return context


    # It's not the first position, so the parsed module info is required
    if info is None:
        info = getBriefModuleInfoFromMemory( str( editor.text() ) )

    line, pos = editor.getCursorPosition()
    _IdentifyScope( info, context, line )

    if context.length == 0:
        return context

    continueLine = False
    currentLine = context.getLastScopeLine() + 1
    for currentLine in xrange( context.getLastScopeLine(),
                               editor.lines() ):
        if currentLine == line:
            break

        text = editor.text( currentLine )
        trimmedText = text.trimmed()
        if continueLine == False:
            if trimmedText == "" or trimmedText.startsWith( "#" ):
                continue

            # Here: there must be characters in the line
            nonSpacePos = _getFirstNonSpacePos( text )
            context.stripLevels( nonSpacePos )
            if context.length == 0:
                return context

        if trimmedText.endsWith( "," ) or trimmedText.endsWith( '\\' ) or \
           _endsWithTripleQuotedString( editor, currentLine, len( text ) - 1 ):
            continueLine = True
        else:
            continueLine = False

    if continueLine:
        context.stripLevels( nonSpacePos )
    else:
        nonSpacePos = _getFirstNonSpacePos( editor.text( line ) )
        if nonSpacePos == -1:
            context.stripLevels( pos )
        else:
            context.stripLevels( min( pos, nonSpacePos ) )
    return context


def _skipSpacesBack( editor, line, col ):
    " Skips spaces backward and returns position of the non-space symbol "
    txt = editor.text( line )
    while True:
        col -= 1
        if col < 0:
            line -= 1
            if line < 0:
                return -1, -1   # Reached the beginning of the doc
            txt = editor.text( line )
            col = len( txt ) - 2    # \r or \n at the end
            if not txt[ col ] == '\\':
                return -1, -1   # Reached the beginning of the line
            col -= 1
        if txt[ col ] in [ ' ', '\t' ]:
            continue
        break
    return line, col


def getPrefixAndObject( editor ):
    """ Provides a prefix to search for and
        the object the prefix used with if so.
        E.g. self.bla would return 'bla' as prefix and 'self' as object
             a.b.bla would return 'bla' and 'a.b' """

    # Get the word to the left
    line, col = editor.getCursorPosition()
    prefix = str( editor.getWord( line, col, 1, True ) )

    # Search for object
    obj = ""
    col -= len( prefix )

    while True:
        line, col = _skipSpacesBack( editor, line, col )
        if line < 0 or col < 0:
            return obj, prefix

        txt = editor.text( line )
        if txt[ col ] != '.':
            return obj, prefix

        line, col = _skipSpacesBack( editor, line, col )
        if line < 0 or col < 0:
            return obj, prefix

        part = str( editor.getWord( line, col + 1, 1, True ) )
        if part == "":
            txt = editor.text( line )
            if txt[ col ] in [ ")", "]", "}", "'", '"' ]:
                if obj != "":
                    obj = "." + obj
                obj = txt[ col ] + obj
            return obj, prefix

        if obj != "":
            obj = "." + obj
        obj = part + obj
        col = col - len( part ) + 1


def getEditorTags( editor, exclude = "", excludePythonKeywords = False ):
    """ Builds a list of the tags in the editor.
        The current line could be excluded.
        The only tags are included which start with prefix """

    excludeSet = set()
    if exclude != "":
        excludeSet.add( exclude )
    if excludePythonKeywords:
        # Note: 2 characters words will be filtered unconditionally
        excludeSet.update( [ "try", "for", "and", "not" ] )

    wordRegexp = QRegExp( "\\W+" )

    result = set()
    for line in xrange( editor.lines() ):
        words = editor.text( line ).split( wordRegexp, QString.SkipEmptyParts )
        for word in words:
            word = str( word )
            if len( word ) > 2:
                if word not in excludeSet:
                    result.add( word )

    return result

