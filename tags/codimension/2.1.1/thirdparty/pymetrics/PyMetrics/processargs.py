""" Process command line arguments.

Usage:

>>> pa = ProcessArgs( 'file1.py', 'file2.py', '/home/files/file3.py' )
>>> pa = ProcessArgs( "inFile1.py", sqlFileName='sqlF1.sql', genCsvSw=False,genKwCntSw=True )
>>> pa = ProcessArgs()  #doctest +NORMALIZE_WHITESPACE +ELLIPSIS
python PyMetrics [ options ] pgm1.py [ pgm2.py ... ]
<BLANKLINE>
Complexity metrics are computed for the Python input files
pgm1.py, pgm2.py, etc. At least one file name is required,
else this message appears.
<BLANKLINE>
Three types of output can be produced:
<BLANKLINE>
* Standard output for a quick summary of the main metrics.
* A text file containing SQL commands necessary to build a SQL table
        in the database of your choice.
* A text file containing Comma-Separated Values (CSV) formatted data
        necessary to load into most spreadsheet programs.
        PLEASE NOTE: multi-line literals have the new-line character
        replaced with the character "\\n" in the output text.
<BLANKLINE>
Capitalized options negate the default option.
<BLANKLINE>
options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -s SQLFILENAME, --sql=SQLFILENAME
                        name of output SQL command file. (Default is
                        metricData.sql)
  -t SQLTOKENTABLENAME, --tokentable=SQLTOKENTABLENAME
                        name of output SQL token table. (Default is
                        metricTokens)
  -m SQLMETRICSTABLENAME, --metricstable=SQLMETRICSTABLENAME
                        name of output SQL metrics table. (Default is
                        metricData)
  -c CSVFILENAME, --csv=CSVFILENAME
                        name of output CSV data file. (Default is
                        metricData.csv)
  -f INFILELIST, --files=INFILELIST
                        File containing list of path names to modules for
                        analysis.
  -i INCLUDEMETRICSSTR, --include=INCLUDEMETRICSSTR
                        list of metrics to include in run. This is a comma
                        separated list of metric module names with no
                        whitespace. Optionally, you can specify the class name
                        of the metric by following the module name with a
                        colon (:) and the metric class name. (Default metrics
                        are 'simple:SimpleMetric,mccabe:McCabeMetric,
                        sloc:SLOCMetric'. Default metric class name for metric 
                        module 'wxYz' is 'WxYzMetric' when only module name
                        given -- note capitalized metric class name.)
  -l LIBNAME, --library=LIBNAME
                        user-defined name applied to collection of modules
                        (Default is '')
  -e, --exists          assume SQL tables exist and does not generate creation
                        code. Using this option sets option -N. (Default is
                        False)
  -N, --noold           create new command output files and tables after
                        deleting old results, if any. Ignored if -e is set.
                        (Default is False)
  -B, --nobasic         suppress production of Basic metrics (Default is
                        False)
  -S, --nosql           suppress production of output SQL command text file.
                        (Default is False)
  -C, --nocsv           suppress production of CSV output text file. (Default
                        is False)
  -H, --noheadings      suppress heading line in csv file. (Default is False)
  -k, --kwcnt           generate keyword counts. (Default is False)
  -K, --nokwcnt         suppress keyword counts. (Default is True)
  -q, --quiet           suppress normal summary output to stdout. (Default is
                        False)
  -z, --zero            display zero or empty values in output to stdout.
                        (Default is to suppress zero/empty output)
  -v, --verbose         Produce verbose output - more -v's produce more
                        output. (Default is no verbose output to stdout)
  -d, --debug           Provide debug output, not usually generated - internal
                        use only
<BLANKLINE>
No program file names given.
<BLANKLINE>

    $Id: processargs.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import sys
from optparse import OptionParser, BadOptionError
from doctestsw import *

usageStr = """python PyMetrics [ options ] pgm1.py [ pgm2.py ... ]

Complexity metrics are computed for the Python input files
pgm1.py, pgm2.py, etc. At least one file name is required,
else this message appears.

Three types of output can be produced:

* Standard output for a quick summary of the main metrics.
* A text file containing SQL commands necessary to build a SQL table
        in the database of your choice.
* A text file containing Comma-Separated Values (CSV) formatted data
        necessary to load into most spreadsheet programs.
        PLEASE NOTE: multi-line literals have the new-line character
        replaced with the character "\\n" in the output text.

Capitalized options negate the default option.
"""

class PyMetricsOptionParser( OptionParser ):
  """ Subclass OptionParser so I can override default error handler."""
  def __init__( self, *args, **kwds ):
    """ Just call super class's __init__ since we aren't making changes here."""
    OptionParser.__init__( self, *args, **kwds )
    
  def error( self, msg ):
    """ Explicitly raise BadOptionError so calling program can handle it."""
    raise BadOptionError( msg )
    
class ProcessArgsError( Exception ): pass

class ProcessArgs( object ):
    """ Process command line arguments."""
    def __init__( self,
                  *pArgs,
                  **pKwds
                ):
        """ Initial processing of arguments."""

        # precedence for defaults, parameters, and command line arguments/keywords
        # is:
        #
        #   command line parameters/keywords take precedence over
        #   parameters used to instantiate ProcessArgs that takes precedence over
        #   default values for keywords.
        #
        # This implies we set completed options with defaults first
        # then override completed options with parameters
        # then override completed options with command line args/keywords
        #

        # default values for possible parameters
        libName = ''
        sqlFileName = "metricData.sql"
        sqlTokenTableName = "metricTokens"
        sqlMetricsTableName = "metricData"
        csvFileName = "metricData.csv"
        inFileList = None
        includeMetricsStr = 'simple:SimpleMetric,mccabe:McCabeMetric,sloc:SLOCMetric'
        excludeMetricsStr = None
        debugSw = False
        debugSw = False
        quietSw = False
        zeroSw = False
        genBasicSw = True
        genKwCntSw = False
        genSqlSw = True
        genCsvSw = True
        genHdrSw = True
        genAppendSw = True
        genNewSw = False
        genExistsSw = False
        verbose = 0

        self.__dict__.update( locals() )
        del( self.__dict__['self'] )  # remove recursive self from self.__dict__
        self.__dict__.update( pKwds )
        del( self.__dict__['pKwds'] ) # remove redundant pKwds in self.__dict__

        # set up option parser
        parser = PyMetricsOptionParser( '', version="%prog 0.8.1" )
        parser.add_option("-s", "--sql", 
                          dest="sqlFileName",
                          default=self.sqlFileName,
                          help="name of output SQL command file. (Default is %s)" % self.sqlFileName )
        parser.add_option("-t", "--tokentable", 
                          dest="sqlTokenTableName",
                          default=self.sqlTokenTableName,
                          help="name of output SQL token table. (Default is %s)" % self.sqlTokenTableName )
        parser.add_option("-m", "--metricstable", 
                          dest="sqlMetricsTableName",
                          default=self.sqlMetricsTableName,
                          help="name of output SQL metrics table. (Default is %s)" % self.sqlMetricsTableName )
        parser.add_option("-c", "--csv", 
                          dest="csvFileName",
                          default=self.csvFileName,
                          help="name of output CSV data file. (Default is %s)" % self.csvFileName )
        parser.add_option("-f", "--files", 
                          dest="inFileList",
                          default=self.inFileList,
                          help="File containing list of path names to modules for analysis." )
        parser.add_option("-i", "--include", 
                          dest="includeMetricsStr",
                          default=self.includeMetricsStr,
                          help="list of metrics to include in run. This is a comma separated list of metric module names with no whitespace. Optionally, you can specify the class name of the metric by following the module name with a colon (:) and the metric class name. (Default metrics are 'simple:SimpleMetric,mccabe:McCabeMetric,sloc:SLOCMetric'. Default metric class name for metric module 'wxYz' is 'WxYzMetric' when only module name given -- note capitalized metric class name.)" )
        parser.add_option("-l", "--library", 
                          dest="libName",
                          default=self.libName,
                          help="user-defined name applied to collection of modules (Default is '')" )
        parser.add_option("-e", "--exists",
                          action="store_true", 
                          dest="genExistsSw", 
                          default=self.genExistsSw,
                          help="assume SQL tables exist and does not generate creation code. Using this option sets option -N. (Default is %s)" % (self.genExistsSw) )
        parser.add_option("-N", "--noold",
                          action="store_true", 
                          dest="genNewSw", 
                          default=self.genNewSw,
                          help="create new command output files and tables after deleting old results, if any. Ignored if -e is set. (Default is %s)" % (self.genNewSw) )
        parser.add_option("-B", "--nobasic",
                          action="store_false", 
                          dest="genBasicSw", 
                          default=self.genBasicSw,
                          help="suppress production of Basic metrics (Default is %s)" % (not self.genBasicSw) )
        parser.add_option("-S", "--nosql",
                          action="store_false", 
                          dest="genSqlSw", 
                          default=self.genSqlSw,
                          help="suppress production of output SQL command text file. (Default is %s)" % (not self.genSqlSw) )
        parser.add_option("-C", "--nocsv",
                          action="store_false", 
                          dest="genCsvSw", 
                          default=self.genCsvSw,
                          help="suppress production of CSV output text file. (Default is %s)" % (not self.genCsvSw) )
        parser.add_option("-H", "--noheadings",
                          action="store_false", 
                          dest="genHdrSw", 
                          default=self.genHdrSw,
                          help="suppress heading line in csv file. (Default is %s)" % (not self.genHdrSw) )
        parser.add_option("-k", "--kwcnt",
                          action="store_true", 
                          dest="genKwCntSw", 
                          default=self.genKwCntSw,
                          help="generate keyword counts. (Default is %s)" % (self.genKwCntSw,) )
        parser.add_option("-K", "--nokwcnt",
                          action="store_false", 
                          dest="genKwCntSw", 
                          default=self.genKwCntSw,
                          help="suppress keyword counts. (Default is %s)" % (not self.genKwCntSw) )
        parser.add_option("-q", "--quiet",
                          action="store_true", 
                          dest="quietSw", 
                          default=self.quietSw,
                          help="suppress normal summary output to stdout. (Default is %s)" % (self.quietSw) )
        parser.add_option("-z", "--zero",
                          action="store_true", 
                          dest="zeroSw", 
                          default=self.zeroSw,
                          help="display zero or empty values in output to stdout. (Default is to suppress zero/empty output)" )
        parser.add_option("-v", "--verbose",
                          action="count", 
                          dest="verbose", 
                          default=self.verbose,
                          help="Produce verbose output - more -v's produce more output. (Default is no verbose output to stdout)")
        parser.add_option("-d", "--debug",
                          action="store_true", 
                          dest="debugSw", 
                          default=self.debugSw,
                          help="Provide debug output, not usually generated - internal use only")

        # parse the command line/arguments for this instance
        try:
            (options, args) = parser.parse_args()
        except BadOptionError, e:
            sys.stderr.writelines( "\nBadOptionError: %s\n" % str( e ) )
            sys.stderr.writelines( "\nThe valid options are:\n\n" )
            sys.stderr.writelines( parser.format_help() )
            sys.exit( 1 )

        # augment parameter values from instantiation with 
        #   command line values.
        # the command line parameter values take precidence 
        #   over values in program.

        args.extend( pArgs )

        # convert command line arguments into instance values
        self.__dict__.update( options.__dict__ )

        if self.inFileList:
            try:
                inF = open( self.inFileList )
                files = inF.read().split()
                inF.close()
                args.extend( files )
            except IOError, e:
                raise ProcessArgsError( e )

        self.inFileNames = args

        self.includeMetrics = self.processIncludeMetrics( self.includeMetricsStr )

        if len( args ) < 1:
            print usageStr
            print parser.format_help()
            e = "No program file names given.\n"
            # because of what I believe to be a bug in the doctest module,
            # which makes it mishandle exceptions, I have 'faked' the handling
            # of raising an exception and just return
            if doctestSw:
              print e
              return
            else:
              raise ProcessArgsError( e )

        so = None
        if self.genSqlSw and self.sqlFileName:
            # Try opening command file for input. If OK, then file exists.
            # Else, the commamd file does not exist to create SQL table and
            # this portion of the command file must be generated as if new
            # table was to be created.
            # 
            # NOTE: This assumption can be dangerous. If the table does exist
            # but the command file is out of sync with the table, then a valid
            # table can be deleted and recreated, thus losing the old data.
            # The workaround for this is to examine the SQL database for the 
            # table and only create the table, if needed.
            try:
                if self.sqlFileName:
                    self.so = open( self.sqlFileName, "r" )
                    self.so.close()
            except IOError:
                self.genNewSw = True
            
            try:
                mode = "a"
                if self.genNewSw:
                    mode = "w"
                so = open( self.sqlFileName, mode )    # check to see that we can write file
                so.close()
            except IOError, e:
                sys.stderr.writelines( str(e) + " -- No SQL command file will be generated\n" )
                self.genSqlSw = False
                so = None

        co = None
        if self.genCsvSw and self.csvFileName:
            try:
                mode = "a"
                if self.genNewSw:
                    mode = "w"
                co = open( self.csvFileName, mode )    # check we will be able to write file
                co.close()
            except IOError, e:
                sys.stderr.writelines( str(e) + " -- No CSV output file will be generated\n" )
                self.genCsvSw = False
                co = None
                
        if self.genExistsSw:
            # Assuming that table already exists, means concatenating 
            # data is not needed - we only want new data in SQL command file.
            self.genNewSw = True

    def conflictHandler( self, *args, **kwds ):
        print "args=%s" % args
        print "kwds=%s" % kwds

    def processIncludeMetrics( self, includeMetricsStr ):
        includeMetrics = []
        try:
            metricList = includeMetricsStr.split( ',' )
            for a in metricList:
                s = a.split( ':' )
                if len( s ) == 2:    # both metric class and module name given
                    includeMetrics.append( s )
                elif len( s ) == 1:
                    # only the module name given. Generate default metric
                    # class name by capitalizing first letter of module
                    # name and appending "Metric" so the default metric
                    # class name for module wxYz is WxYzMetric.
                    if s[0]:
                        defName = s[0][0].upper() + s[0][1:] + 'Metric'
                        includeMetrics.append( (s[0], defName) )
                    else:
                        raise ProcessArgsError("Missing metric module name")
                else:
                    raise ProcessArgsError("Malformed items in includeMetric string")
        except AttributeError, e:
            e = ( "Invalid list of metric names: %s" % 
                includeMetricsStr )
            raise ProcessArgsError( e )
        return includeMetrics

def testpa( pa ):
    """ Test of ProcessArgs.

    Usage:

    >>> pa=ProcessArgs('inFile.py')
    >>> testpa(pa)  #doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    Arguments processed:
      sqlFileName=metricData.sql
      sqlTokenTableName=metricTokens
      sqlMetricsTableName=metricData
      csvFileName=metricData.csv
      Include Metric Modules=simple:SimpleMetric,mccabe:McCabeMetric
      quietSw=False
      genCsvSw=True
      genHdrSw=True
      genKwCntSw=False
      verbose=...
    Metrics to be used are:
      Module simple contains metric class SimpleMetric
      Module mccabe contains metric class McCabeMetric
    Input files:
      inFile.py
    >>>
    """
    print """
Arguments processed:
\tsqlFileName=%s
\tsqlTokenTableName=%s
\tsqlMetricsTableName=%s
\tcsvFileName=%s
\tinclude Metric Modules=%s
\tquietSw=%s
\tgenNewSw=%s
\tgenExistsSw=%s
\tgenSqlSw=%s
\tgenCsvSw=%s
\tgenHdrSw=%s
\tgenKwCntSw=%s
\tverbose=%s""" % (
        pa.sqlFileName,
        pa.sqlTokenTableName,
        pa.sqlMetricsTableName,
        pa.csvFileName,
        pa.includeMetricsStr,
        pa.quietSw,
        pa.genNewSw,
        pa.genExistsSw,
        pa.genSqlSw,
        pa.genCsvSw,
        pa.genHdrSw,
        pa.genKwCntSw,
        pa.verbose)
    print "Metrics to be used are:"
    for m,n in pa.includeMetrics:
        print "\tModule %s contains metric class %s" % (m,n)
    if pa.inFileNames:
        print "Input files:"
        for f in pa.inFileNames:
            print "\t%s" % f

if __name__ == "__main__":

    # ignore doctestsw.doctestSw if this is run as a standalone
    # module. Instead, look at the first argument on the command
    # line. If it is "doctest", set doctestSw = True and delete
    # the parameter "doctest" from sys.argv, thus leaving things
    # as _normal_.
    if len(sys.argv) > 1 and sys.argv[1] == 'doctest':
      doctestSw = True
      sys.argv[1:] = sys.argv[2:]
      import doctest
      doctest.testmod( sys.modules[__name__] )
      sys.exit( 0 )

    print "=== ProcessArgs: %s ===" % ("'file1.py', 'file2.py', '/home/files/file3.py'",)
    try:
      pa = ProcessArgs( 'file1.py', 'file2.py', '/home/files/file3.py' )
      testpa( pa )
    except ProcessArgsError, e:
      sys.stderr.writelines( str( e ) )
    print
    print "=== ProcessArgs: %s ===" % ("inFile1.py, sqlFileName='sqlF1.sql', genCsvSw=False,genKwCntSw=True",)
    try:
      pa = ProcessArgs( "inFile1.py", sqlFileName='sqlF1.sql', genCsvSw=False,genKwCntSw=True )
      testpa( pa )
    except ProcessArgsError, e:
      sys.stderr.writelines( str( e ) )
    print
    print "=== ProcessArgs: %s ===" % ("No arguments",)
    try:
      pa = ProcessArgs()
      testpa( pa )
    except ProcessArgsError, e:
      sys.stderr.writelines( str( e ) )
    print
    sys.exit( 0 )

