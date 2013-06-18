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
from PyQt4.QtCore       import QString, QRegExp
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


def getContext( editor, info = None, readOnly = False ):
    """ Detects the context where the text cursor is.
        readOnly == True is used when a context is detected for search
        purposes like jumping to the beginning of the current scope.
        The difference is how empty lines are treated. If readOnly is set
        then empty lines are skipped backward and the last non empty
        line is used to detect the context. """

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
    if readOnly == True:
        while line >= 0:
            text = editor.text( line )
            trimmedText = text.trimmed()
            if trimmedText != "":
                pos = len( text )
                break
            line -= 1
        if line < 0:
            line = 0
            pos = 0

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
            if txt[ col ] != '\\':
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

        txt = str( editor.text( line ) )
        if txt[ col ] != '.':
            return obj, prefix

        line, col = _skipSpacesBack( editor, line, col )
        if line < 0 or col < 0:
            return obj, prefix

        part = str( editor.getWord( line, col + 1, 1, True ) )
        if part == "":
            txt = str( editor.text( line ) )
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

    # If a cursor is in a middle of the word then the current word is not what
    # you need.
    currentWord = str( editor.getCurrentWord() ).strip()
    result.discard( currentWord )
    return result


def isStringLiteral( editor, pos = None ):
    """ Returns True if the position is inside a string literal.
        It is supposed that the file type is Python """
    if pos is None:
        pos = editor.currentPosition()
    return editor.styleAt( pos ) in \
                    [ QsciLexerPython.TripleDoubleQuotedString,
                      QsciLexerPython.TripleSingleQuotedString,
                      QsciLexerPython.DoubleQuotedString,
                      QsciLexerPython.SingleQuotedString,
                      QsciLexerPython.UnclosedString ]


def isRemarkLine( editor, pos = None):
    """ Returns True if the position is inside a remark.
        It is supposed that the file type is Python """
    if pos is None:
        pos = editor.currentPosition()
    return editor.styleAt( pos ) in \
                    [ QsciLexerPython.Comment,
                      QsciLexerPython.CommentBlock ]


def isImportLine( editor, pos = None ):
    """ Returns True if the current line is a part of an import line.
        It is supposed that the file type is Python """
    if pos is None:
        pos = editor.currentPosition()
    if isStringLiteral( editor, pos ):
        return False, -1

    line, index = editor.lineIndexFromPosition( pos )
    # Find the beginning of the line
    while True:
        if line == 0:
            break
        prevLine = editor.text( line - 1 ).trimmed()
        if not prevLine.endsWith( '\\' ) and not prevLine.endsWith( ',' ):
            break
        line -= 1

    text = editor.text( line ).trimmed()
    if text.startsWith( "import " ) or text.startsWith( "from " ) or \
       text.startsWith( "import\\" ) or text.startsWith( "from\\" ):
        if not isStringLiteral( editor,
                                editor.positionFromLineIndex( line, 0 ) ):
            return True, line
    return False, -1

def getWordAtPosition( editor, position, direction = 0,
                       useWordChars = True, addChars = "" ):
    " Provides a word at position "
    wordLine, pos = editor.lineIndexFromPosition( position )
    return editor.getWord( wordLine, pos, direction, useWordChars, addChars )

def isOnSomeImport( editor ):
    """ Returns 3 values:
        bool   - this is an import line
        bool   - a list of modules should be provided
        string - module name from which an object is to be imported
    """
    # There are two case:
    # import BLA1, BLA2 as WHATEVER2, BLA3
    # from BLA import X, Y as y, Z
    isImport, line = isImportLine( editor )
    if isImport == False:
        return False, False, ""

    charsToSkip = [ ' ', '\\', '\r', '\n', '\t' ]

    text = editor.text( line ).trimmed()
    if text.startsWith( "import" ):
        currentWord = editor.getCurrentWord()
        if currentWord in [ "import", "as" ]:
            # It is an import line, but no need to complete
            return True, False, ""
        # Search for the first non space character before the current word
        position = editor.positionBefore( editor.currentPosition() )
        while editor.charAt( position ) not in charsToSkip:
            position = editor.positionBefore( position )
        while editor.charAt( position ) in charsToSkip:
            position = editor.positionBefore( position )
        if editor.charAt( position ) in [ ',', '(' ]:
            # It's an import line and need to complete
            return True, True, ""

        if getWordAtPosition( editor, position ) == "import":
            # It's an import line and need to complete
            return True, True, ""
        # It;s an import line but no need to complete
        return True, False, ""

    # Here: this is the from x import bla as ... statement
    currentWord = editor.getCurrentWord()
    if currentWord in [ "from", "import", "as" ]:
        return True, False, ""
    # Search for the first non space character before the current word
    position = editor.positionBefore( editor.currentPosition() )
    while editor.charAt( position ) not in charsToSkip:
        position = editor.positionBefore( position )
    while editor.charAt( position ) in charsToSkip:
        position = editor.positionBefore( position )

    previousWord = getWordAtPosition( editor, position )
    if previousWord == "as":
        # Nothing should be completed
        return True, False, ""
    if previousWord == "from":
        # Completing a module
        return True, True, ""
    if previousWord == "import" or editor.charAt( position ) in [ ',', '(' ]:
        # Need to complete an imported object
        position = editor.positionFromLineIndex( line, 0 )
        while editor.charAt( position ) in [ ' ', '\t' ]:
            position = editor.positionAfter()
        # Expected 'from' at this position
        if getWordAtPosition( editor, position ) != 'from':
            return True, False, ""
        # Next is a module name
        position += len( 'from' )
        while editor.charAt( position ) in charsToSkip:
            position = editor.positionAfter()
        moduleName = getWordAtPosition( editor, position, 0, True, "." )
        if moduleName == "":
            return True, False, ""
        # Sanity check - there is 'import' after that
        position += len( moduleName )
        while editor.charAt( position ) in charsToSkip:
            position = editor.positionAfter()
        if getWordAtPosition( editor, position ) != 'import':
            return True, False, ""
        # Finally, this is a completion for an imported object
        return True, True, moduleName

    return True, False, ""


def getCallPositionAndCommas( editor ):
    """ It is going to be used for calltips. It provides a tuple - position
        of where the function name is (or None if not found) and the number
        of commas at the current level of nesting (used to highlight the
        current parameter in a calltip """
    commas = 0
    level = 0

    pos = editor.currentPosition()
    startLine, _ = editor.lineIndexFromPosition( pos )
    while pos > 0:
        if isStringLiteral( editor, pos ):
            pos = editor.positionBefore( pos )
            continue
        ch = editor.charAt( pos )
        if ch == ')':
            level += 1
        elif ch == ',':
            if level == 0:
                commas += 1
        elif ch == '(':
            if level == 0:
                break
            level -= 1
        elif ch in [ '\n', '\r' ]:
            # It makes sense to check if it is a time to stop searching
            curLine, _ = editor.lineIndexFromPosition( pos )
            if curLine < startLine:
                lineContent = editor.text( curLine + 1 ).trimmed()
                if lineContent.startsWith( "def " ) or \
                   lineContent.startsWith( "class " ) or \
                   lineContent.startsWith( "def\\" ) or \
                   lineContent.startsWith( "class\\" ):
                    # It does not make sense to search beyond a class or
                    # a function definition
                    return None, 0
        pos = editor.positionBefore( pos )

    if pos <= 0:
        # pos points to '(' or 0. Even if '(' is at position 0,
        # there is nothing to provide calltip for
        return None, 0

    # Now, find out where the first non-space character is to get the object
    # name position.
    pos = editor.positionBefore( pos )
    while pos > 0:
        ch = editor.charAt( pos )
        if ch in [ ' ', '\t', '\r', '\n', '\\' ]:
            pos = editor.positionBefore( pos )
            continue
        if ch.isalnum():
            return pos, commas
        return None, 0
    return None, 0
