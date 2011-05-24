#! /usr/bin/env python
""" PyMetrics - Complexity Measurements for Python code.

    Orignally based on grop.py by Jurgen Hermann.
    Modified by Reg. Charney to do Python complexity measurements.
    
    Copyright (c) 2001 by Jurgen Hermann <jh@web.de>
    Copyright (c) 2007 by Reg. Charney <charney@charneyday.com>

    All rights reserved, see LICENSE for details.
    
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    $Id$
"""
__revision__ = "$Id$"
__author__ = 'Reg. Charney <charney-at-charneyday.com>'

# Imports
import sys
import string
from processargs import ProcessArgs, ProcessArgsError
import token
import sqltokenout
import sqldataout
import csvout
from lexer import Lexer
from compute import ComputeMetrics
from globals import *

PYTHON_VERSION = sys.version[:3]

#############################################################################
### Main script for PyMetrics utility.
#############################################################################

def __importMetricModules( includeMetrics ):
    """ Import the modules specified in the parameter list.
    
    includeMetrics is a list of (metricModuleName, metricClassName) 
    pairs. This function defines a dictionary containing only valid 
    module/class names. When an error is found, the invalid 
    module/class pair is removed from the included list of metrics.
    """
    i = 0
    metricModules = {}
    if PYTHON_VERSION < '2.5':
      pfx = '' # this fix is for Python 2.4
    else:
      pfx = 'PyMetrics.'
    for m,n in includeMetrics:
        try:
            mm = pfx + m
            if PYTHON_VERSION < '2.5':
              mod = __import__( mm, globals(), locals(), [m] )
            else:
              mod = __import__( mm, fromlist=[m] )
            metricModules[m] = mod
            i += 1
        except ImportError:
            sys.stderr.write( "Unable to import metric module %s -- ignored.\n\n" % mm )
            # remove the erroneous metric module/class tuple
            del includeMetrics[i]
            
    return metricModules

def __instantiateMetric( metricModules, context, runMetrics, metrics, pa ):
    """ Instantiate all user specified metric classes.
    
    The code works by finding the desired metric class in a metric module and 
    instantiating the class. It does this by assuming that the metric
    class is in the dictionary of the metric module.
    """
    metricInstance = {}
    inclIndx = -1
    for m,n in pa.includeMetrics:
        inclIndx += 1
        try:
          metricInstance[m] = None        # default value if metric class does not exist.
          metricInstance[m] = metricModules[m].__dict__[n]( context, runMetrics, metrics, pa )
        except KeyError:
          sys.stderr.write( "Module %s does not contain metric class %s -- metric %s ignored.\n\n" % (m,n,m) )
          del( metricInstance[m] )
          del( pa.includeMetrics[inclIndx] )
        
    return metricInstance
            
def __stats( so, m, inFileName, label, *args ):
    """ Print line of statistics."""
    result = string.join(map(str, args), '')
    print "%11s    %s" % (result, label)
    so and so.write( m, inFileName, label, result )
        
def __printSummary( so, context, runMetrics, metrics, pa ):
    """ Print basic summary information."""
    # the following loop is a very, very ugly hack to distinguish between
    # tokens as they appear in the source; semantically generated tokens,
    # like DOCSTRING; and NONTOKENs, like numComments
    
    keys = []
    for k in metrics.keys():
        if str( k ).isdigit():
            keys.append( (token.tok_name[k],k,metrics[k]) )
        elif len( str( k ).split() ) > 1:
            keys.append( (k,SEMTOKEN,metrics[k]) )        
        else:
            keys.append( (k,NONTOKEN,metrics[k]) )
    keys.sort()
    
    inFileName = context['inFile']
    if pa.genKwCntSw:
        hdr = "Counts of Token Types in module %s" % context['inFile']
        print
        print hdr
        print "-"*len(hdr)
        print
        for k,t,v in keys:
            if (pa.zeroSw or v):
                if t != NONTOKEN:
                    __stats( so, 'basic', inFileName, k, v )
        print

    if pa.genBasicSw:
        __displayBasicMetrics( keys, pa, so, inFileName )

def __displayBasicMetrics( keys, pa, so, inFileName ):
    """ Display the Basic metrics that PyMetrics computes."""
    hdr = "Basic Metrics for module %s" % inFileName
    print
    print hdr
    print "-"*len( hdr )
    print
    for k,t,v in keys:
        if t==NONTOKEN:
            if pa.zeroSw or not v in ([],{},(),0,0.00):
                __stats( so, 'basic', inFileName, k, v )
    print
    
def main():
    """ Main routine for PyMetrics."""
    # process command line args
    try:
        pa = ProcessArgs()
    except ProcessArgsError, e:
        sys.stderr.writelines( str(e) )
        return
      
    if pa.genNewSw:
        __deleteOldOutputFiles( pa )
        
    so, od = __genNewSqlCmdFiles( pa )
    co = __genNewCsvFile( pa )
    
    # import all the needed metric modules
    metricModules = __importMetricModules( pa.includeMetrics )

    runMetrics = {} # metrics for whole run
    metrics = {}    # metrics for this module
    context = {}    # context in which token was used
    
    # main loop - where all the work is done
    for inFileName in pa.inFileNames:

        metrics.clear()
        context.clear()
        context['inFile'] = inFileName
        
        # instantiate all the desired metric classes
        metricInstance = __instantiateMetric( metricModules, context, runMetrics, metrics, pa )
        
        cm = ComputeMetrics( metricInstance, context, runMetrics, metrics, pa, so, co )
    
        # define lexographical scanner to use for this run
        # later, this may vary with file and language.
        lex = Lexer()
        
        if not pa.quietSw:
            print "=== File: %s ===" % inFileName

        try:
            lex.parse( inFileName ) # parse input file
            
            metrics["numCharacters"] = len(lex.srcLines)
            metrics["numLines"] = lex.lineCount                  # lines of code
        
            metrics = cm( lex )
            
            # if printing desired, output summary and desired metrics
            # also, note that this preserves the order of the metrics desired
            if not pa.quietSw:
                __printSummary( od, context, runMetrics, metrics, pa )
                for m,n in pa.includeMetrics:
                    if metricInstance[m]:
                        result = metricInstance[m].display()
                        if metrics.has_key(m):
                            metrics[m].append( result )
                        else:
                            metrics[m] = result
                        for r in result.keys():
                            od and od.write( m, inFileName, r, result[r] )
        except IOError, e:
            sys.stderr.writelines( str(e) + " -- Skipping input file.\n\n")
            
    co and co.close()
    
    result = {}
    if len( pa.inFileNames ) > 0:
      for m,n in pa.includeMetrics:
          if metricInstance[m]:
              result = metricInstance[m].processRun( None )
              if result:
                  for r in result.keys():
                      od and od.write( m, None, r, result[r] )
    od and od.close()
    
    if not pa.quietSw:
        n = len( pa.inFileNames )
        print
        print "*** Processed %s module%s in run ***" % (n,(n>1) and 's' or '')

def __genNewCsvFile( pa ):
    """ Determine output CSV data file, if any, 
    and check it can be created."""
    co = None
    try:
        if pa.genCsvSw:
            co = csvout.CsvOut( pa.csvFileName, genHdrSw=pa.genHdrSw, genNewSw=pa.genNewSw )
    except StandardError, e:
        # this should not occur - it should be handled in processArgs.
        sys.stderr.writelines( str(e) + " -- No CSV file will be generated\n\n" )
        pa.genCsvSw = False
    
    return co

def __genNewSqlCmdFiles( pa ):
    """ determine output SQL tokens command file, if any, 
    and check it can be created ."""
    so = None
    co = None
    od = None
    fd = None
    
    try:
        if pa.genSqlSw:
            if pa.sqlFileName:
                fd = open( pa.sqlFileName, 'a' )
            else:
                fd = sys.stdout
            so = sqltokenout.SqlTokenOut( fd, pa.libName, pa.sqlFileName, pa.sqlTokenTableName, pa.genNewSw, pa.genExistsSw )
            od = sqldataout.SqlDataOut( fd, pa.libName, pa.sqlFileName, pa.sqlMetricsTableName, pa.genNewSw, pa.genExistsSw )
    except StandardError, e:
        # this should not occur - it should be handled in processArgs.
        sys.stderr.writelines( str(e) + " -- No SQL command file will be generated\n\n" )
        pa.genSqlSw = False
        so and so.close()
        od and od.close()
        so = None
        od = None
        
    return so, od

def __deleteOldOutputFiles( pa ):
    """ Generate new output files by ensuring old files deleted."""
    import os
    try:
        if pa.genSqlSw and os.path.exists( pa.sqlFileName ):
            os.remove( pa.sqlFileName )
    except IOError, e:
        sys.stderr.writelines( str(e) )
        pa.genSqlSw = False
        
    try:
        if pa.genCsvSw and os.path.exists( pa.csvFileName ):
            os.remove( pa.csvFileName )
    except IOError, e:
        sys.stderr.writelines( str(e) )
        pa.genCsvSw = False
    return

if __name__ == "__main__":
    main()
    sys.exit(0)
