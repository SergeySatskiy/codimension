""" CvsOut - class to produce CVS data output.

    $Id$
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import sys
import time
import token
import tokenize
from utils import *

class CsvOut( object ):
    """ Class used to generate a CSV data file suitable for input to spreadsheet program."""
    def __init__( self, fileName, genHdrSw=True, genNewSw=False ):
        """ Open output file and generate header line, if desired."""
        self.fileName = fileName
        self.quotedFileName = '"'+self.fileName+'"'
        self.IDDateTime = '"'+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())+'"'
        self.toknum = 0
        
        mode = "a"
        if genNewSw:
            mode = "w"
        try:
            if self.fileName:
                self.fd = open( fileName, mode )
            else:
                self.fd = sys.stdout
        except IOError:
            raise
            
        self.writeHdr( genNewSw, genHdrSw )
        
    def writeHdr( self, genNewSw, genHdrSw ):
        """ Write header information for CSV file."""
        if genNewSw and genHdrSw:
            fldNames = [
                '"IDDateTime"',
                '"tokNum"',
                '"inFile"',
                '"line"',
                '"col"',
                '"tokType"',
                '"semType"',
                '"tokLen"',
                '"token"',
                '"fqnFunction"',
                '"fqnClass"',
                '"blockNum"',
                '"blockDepth"',
                '"fcnDepth"',
                '"classDepth"',
                '"parenDepth"',
                '"bracketDepth"',
                '"braceDepth"'
            ]
            self.fd.write( ','.join( fldNames ) )
            self.fd.write( '\n' )
    
    def close( self ):
        """ Close output file if it is not stdout. """
        if self.fileName:
            self.fd.flush()
            self.fd.close()
    
    def write( self, context, tok, fqnFunction, fqnClass ):
        """ Generate the CSV data line."""
        self.toknum += 1
        txt = tok.text
        tt = tok.type
        tn = token.tok_name[tt]
        
        sn = ''
        if tok.semtype:
            sn = token.tok_name[tok.semtype]
        if tt == token.NEWLINE or tt == tokenize.NL:
            txt = r'\n'
        
        sArgs = ','.join( (
            self.IDDateTime,
            str( self.toknum ),
            '"'+str( context['inFile'] )+'"',
            str( tok.row ),
            str( tok.col ),
            '"'+tn+'"',
            '"'+sn+'"',
            str( len( txt ) ),
            csvQ( txt ),
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
        self.fd.write( sArgs )
        self.fd.write( '\n' )

    def close( self ):
        """ Close file, if it is opened."""
        self.fd and self.fd.close()
        self.fd = None
