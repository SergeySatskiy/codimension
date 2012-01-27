""" SqlDataOut - class to produce SQL data command file output.

    $Id$
"""
__revision__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import sys
import time
import token
import tokenize
import utils

import sqltemplate

class InvalidTableNameError( Exception ): 
    """ Used to indicate that the SQL table name is invalid."""
    pass

class SqlDataOut( object ):
    """ Class used to generate a command file suitable for runnning against
    any SQL dbms."""
    def __init__( self, 
                  fd, 
                  libName, 
                  fileName, 
                  tableName, 
                  genNewSw=False, 
                  genExistsSw=False ):
        """ Initialize instance of SqlDataOut."""
        if tableName == '':
            raise InvalidTableNameError( tableName )
        if not fd:
            raise IOError( "Output file does not yet exist" )
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.libName = libName
        self.fileName = fileName
        self.tableName = tableName
        self.quotedFileName = '"'+self.fileName+'"'
        self.IDDateTime = '"'+timestamp+'"'
        self.toknum = 0
        self.fd = fd
        
        if not genExistsSw:
            self.writeHdr( genNewSw, tableName )
        
    def writeHdr( self, genNewSw, tableName ):
        """ Write header information for creating SQL command file."""
        if genNewSw:
            import re
            r = re.compile( '\w+' )
            if r.match( tableName ):
                self.fd.write( 
                  sqltemplate.dataHdr % 
                  (tableName, tableName, tableName, tableName) 
                  )
            else:
                raise AttributeError( 'Invalid table name' )
        
    def write( self, metricName, srcFileName, varName, value ):
        """ Generate the Sql INSERT line into the sql command file."""
        sArgs = ','.join( (
            self.IDDateTime,
            '0',
            '"'+str( self.libName )+'"',
            '"'+str( metricName )+'"',
            '"'+str( srcFileName )+'"',
            '"'+str( varName )+'"',
            '"'+str( value )+'"'
            ) )
        sOut = sqltemplate.dataInsert % (self.tableName, sArgs)
        self.fd and self.fd.write( sOut )

    def close( self ):
        """ Close file, if it is opened."""
        self.fd and self.fd.close()
        self.fd = None
