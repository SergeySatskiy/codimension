""" SqlTokenOut - class to produce SQL Token command file output.

    $Id: sqltokenout.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__revision__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import sys
import time
import token
import tokenize
from utils import *

import string
import sqltemplate

class InvalidTableNameError( Exception ): pass

class SqlTokenOut( object ):
    """ Class used to generate a command file suitable for runnning against
    any SQL dbms."""
    def __init__( self, fd, libName, fileName, tableName, genNewSw=False, genExistsSw=False ):
        if tableName == '':
            raise InvalidTableNameError( tableName )
            
        self.libName = libName
        self.fileName = fileName
        self.tableName = tableName
        self.quotedFileName = '"'+self.fileName+'"'
        self.IDDateTime = '"'+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())+'"'
        self.toknum = 0
        self.fd = fd
        
        if not genExistsSw:
            self.writeHdr( genNewSw, tableName )
        
    def writeHdr( self, genNewSw, tableName ):
        """ Write header information for creating SQL command file."""
        if genNewSw:
            self.fd.write( sqltemplate.tokenHdr % (tableName,tableName,tableName,tableName) )
        
    def write( self, context, tok, fqnFunction, fqnClass ):
        """ Generate the Sql INSERT line into the sql command file."""
        self.toknum += 1
        txt = tok.text
        tt = tok.type
        tn = token.tok_name[tt]
        
        if tt == token.NEWLINE or tt == tokenize.NL:
            txt = r'\n'
        sn = self.__formSemanticName(tok)
        sArgs = self.__formArgString(context, tok, tn, sn, txt, fqnFunction, fqnClass)
        sOut = sqltemplate.tokenInsert % (self.tableName, sArgs)
        self.fd.write( sOut )

    def __formSemanticName(self, tok):
        """ Form semantic name by decoding semtype."""
        sn = ''
        if tok.semtype:
            sn = token.tok_name[tok.semtype]
        return sn

    def __formArgString(self, context, tok, tn, sn, txt, fqnFunction, fqnClass):
        """ Generate arguments string for use in write method."""
        sArgs = ','.join( (
            self.IDDateTime,
            str( self.toknum ),
            '"'+str( self.libName )+'"',
            '"'+str( context['inFile'] )+'"',
            str( tok.row ),
            str( tok.col ),
            '"'+tn+'"',
            '"'+sn+'"',
            str( len( txt ) ),
            sqlQ( txt ),
            '"'+str( toTypeName( context, fqnFunction ) )+'"',
            '"'+str( toTypeName( context, fqnClass ) )+'"',
            str( context['blockNum'] ),
            str( context['blockDepth'] ),
            str( context['fcnDepth'] ),
            str( context['classDepth'] ),
            str( context['parenDepth'] ),
            str( context['bracketDepth'] ),
            str( context['braceDepth'] )
            ) )
        return sArgs

    def close( self ):
        """ Close file, if it is opened."""
        self.fd and self.fd.close()
        self.fd = None
      
