""" Parsing classes.

    $Id: lexer.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import sys
import string
import cStringIO
import mytoken
import keyword
from globals import *

class ParseError(Exception):
    pass

class Lexer:
    """ Parse python source."""
    def __init__( self ):
        self.prevToktype = None
        self.prevSemtype = None
        self.prevToktext = None

    def parse( self, inFileName ):
        """ Read and parse the source. """
        fd = open( inFileName )
        try:
            srcLines = fd.read()
            self.srcLines = string.expandtabs( srcLines )
        finally:
            fd.close()
        
        self.tokenlist = []

        self.__computeOffsets()
        self.__parseSource()

    def __parseSource(self):
        """ Parse the source in file."""
        self.pos = 0
        text = cStringIO.StringIO( self.srcLines )
        try:
            tokenize.tokenize( text.readline, self )
        except tokenize.TokenError, ex:
            msg = ex[0]
            line = ex[1][0]
            print line, self.srcLines[self.offset[line]:]
            raise ParseError("ERROR %s\nLine %d:%s" % (
                msg, line, self.srcLines[self.offset[line]:]))

    def __computeOffsets(self):
        """ Compute and store line offsets in self.offset. """
        self.offset = [0, 0]
        self.lineCount = 0
        pos = 0
        while pos < len( self.srcLines ):
            self.lineCount += 1
            pos = string.find( self.srcLines, '\n', pos ) + 1
            if not pos: break
            self.offset.append( pos )
        self.offset.append( len( self.srcLines ) )


    def __push(self, toktype, semtype, toktext, srow, scol, line):
        "Append given token to final list of tokens."

        self.tokenlist.append(mytoken.MyToken(type=toktype, semtype=semtype, text=toktext, row=srow, col=scol, line=line))
        if toktype in [NEWLINE,INDENT,DEDENT,EMPTY,ENDMARKER]:
            self.prevToktype = None
            self.prevSemtype = None
            self.prevToktext = None
        elif toktype != WS:
            self.prevToktype = toktype
            self.prevSemtype = semtype
            self.prevToktext = toktext


    def __call__(self, toktype, toktext, (srow,scol), (erow,ecol), line):
        """ MyToken handler."""
        semtype = None
        
        # calculate new positions
        oldpos = self.pos
        newpos = self.offset[srow] + scol
        self.pos = newpos + len(toktext)

        # check for extraneous '\r', usually produced in Windows and Mac systems
        if toktype == ERRORTOKEN:  # Python treats a '\r' as an error
            if toktext in ['\r']:
                toktext = ' '
                toktype = WS
            else:
                msg = "Invalid character %s in line %d column %d\n" % (str.__repr__(toktext), srow, scol+1)
                sys.stderr.writelines( msg )
                sys.stdout.writelines( msg )
                # next line is commented out so that invalid tokens are not output
                # self.__push(toktype, None, toktext, srow, scol, line)
                return
                    
        # handle newlines
        if toktype in [NEWLINE, EMPTY]:
            self.__push(toktype, None, '\n', srow, scol, line)
            return

        # send the original whitespace, if needed
        # this is really a reconstruction based on last
        # and current token positions and lengths.
        if newpos > oldpos:
            # srow scol is the starting position for the current 
            #    token that follows the whitespace.
            # srow sws is the computed starting position of the 
            #    whitespace
            sws = scol - ( newpos - oldpos )
            self.__push(WS, None, self.srcLines[oldpos:newpos], srow, sws, line)

        # skip tokens that indent/dedent
        if toktype in [INDENT, DEDENT]:
            self.pos = newpos
            self.__push(toktype, None, '', srow, scol, line)
            return

        # map token type to one of ours and set semantic type, if possible
        if token.LPAR <= toktype and toktype <= OP:
            toktype = OP
            if toktext == '@':
                semtype = DECORATOR
        elif toktype == NAME:
            if keyword.iskeyword(toktext) or toktext == "self":
                semtype = KEYWORD
            else:
                semtype = VARNAME
                if self.prevToktext == "def":
                    semtype = FCNNAME
                elif self.prevToktext == "class":
                    semtype = CLASSNAME

        # add token
        self.__push(toktype, semtype, toktext, srow, scol, line)
