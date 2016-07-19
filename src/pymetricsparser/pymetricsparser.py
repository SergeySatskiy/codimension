#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010 - 2011  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" pymetrics output parser "

from subprocess import Popen, PIPE
import sys, os, os.path, tempfile
from optparse  import OptionParser
from distutils.spawn import find_executable


verbose = False


class BasicMetrics( object ):
    " Holds basic metrics "

    metricsOfInterest = { 'blockDepth'                 :
                                'Block depth',
                          'maxBlockDepth'              :
                                'Max block depth',
                          'numBlocks'                  :
                                'Number of blocks',
                          'numCharacters'              :
                                'Number of characters',
                          'numClassDocStrings'         :
                                'Number of class doc strings',
                          'numClasses'                 :
                                'Number of classes',
                          'numComments'                :
                                'Number of comments',
                          'numCommentsInline'          :
                                'Number of comments in line',
                          'numDocStrings'              :
                                'Number of doc strings',
                          'numFcnDocStrings'           :
                                'Number of function doc strings',
                          'numFunctions'               :
                                'Number of functions',
                          'numKeywords'                :
                                'Number of keywords',
                          'numLines'                   :
                                'Number of lines',
                          'numModuleDocStrings'        :
                                'Number of module doc strings',
                          'numMultipleExitFcns'        :
                                'Number of multiple exit functions',
                          'numSrcLines'                :
                                'Number of source lines',
                          'numTokens'                  :
                                'Number of tokens',
                          '%ClassesHavingDocStrings'   :
                                '% of classes which have doc strings',
                          '%Comments'                  :
                                '% of comments',
                          '%CommentsInline'            :
                                '% of comments in line',
                          '%FunctionsHavingDocStrings' :
                                '% of functions which have doc strings' }

    def __init__( self ):

        # string key -> int value
        self.metrics = {}
        return

    def parseSection( self, section ):
        " Parses the basic metrics section "

        for line in section:
            line = line.strip()

            if line == "":
                continue

            parts = line.split()
            key = parts[ len( parts ) - 1 ]

            if key in self.metricsOfInterest:
                self.metrics[ key ] = parts[ 0 ]
                if verbose:
                    print "Adding basic metric: " + key + " -> " + parts[ 0 ]

        return

    def __str__( self ):
        " Converts to string "
        if len( self.metrics ) == 0:
            return "No Basic metrics found"
        string = "Basic metrics:\n"
        for item in self.metrics:
            string += item + " -> " + str( self.metrics[ item ] ) + "\n"
        return string



class McCabeMetrics( object ):
    " Holds McCabe metrics "

    def __init__( self ):

        # object name -> int value
        self.metrics = {}
        return

    def parseSection( self, section ):
        " Parses the McCabe metrics section "

        for line in section:
            line = line.strip()

            if line == "":
                continue

            parts = line.split()
            self.metrics[ parts[ 1 ] ] = int( parts[ 0 ] )
            if verbose:
                print "Adding McCabe metric: " + \
                      parts[ 1 ] + " -> " + parts[ 0 ]

        return

    def __str__( self ):
        " Converts to string "
        if len( self.metrics ) == 0:
            return "No McCabe metrics found"
        string = "MCCabe complexity:"
        for item in self.metrics:
            string += item + " -> " + str( self.metrics[ item ] ) + "\n"
        return string


class COCOMO2Metrics( object ):
    " Holds COCOMO 2 metrics "

    def __init__( self ):

        self.value = 0
        return

    def parseSection( self, section ):
        " Parses the COCOMO 2 metrics section "

        for line in section:
            line = line.strip()

            if line == "":
                continue

            self.value = int( line.split()[ 0 ] )
            if verbose:
                print "COCOMO 2: " + str( self.value )
            break

        return

    def __str__( self ):
        " Converts to string "
        return "COCOMO 2 metrics: " + str( self.value )


class Metric( object ):
    " Holds a single file metrics "

    def __init__( self ):
        self.messages = []
        self.basicMetrics = BasicMetrics()
        self.mcCabeMetrics = McCabeMetrics()
        self.cocomo2Metrics = COCOMO2Metrics()
        return

    def __str__( self ):
        " Converts to string "
        messagesPart = ""
        if len( self.messages ) == 0:
            messagesPart = "No messages found"
        else:
            messagesPart = "Messages:" + "\n" + \
                           "\n".join( self.messages ) + "\n"
        return messagesPart + "\n" + str( self.basicMetrics ) + "\n" + \
               str( self.mcCabeMetrics ) + "\n" + \
               str( self.cocomo2Metrics )


class PyMetrics( object ):
    " Holds a pymetrics report "

    Unknown      = -1
    FileStarted  = 0
    Message      = 1
    SectionStart = 2
    ReportEnd    = 3


    def __init__( self, pymetricsElf = "" ):

        if pymetricsElf == "":
            # Try to find in the PATH
            try:
                self.pymetricsElf = find_executable( "pymetrics" )
                if self.pymetricsElf:
                    self.__run( [ self.pymetricsElf ] )
                else:
                    raise Exception( "Not found" )
            except:
                raise Exception( "Cannot find pymetrics. "
                                 "Consider updating PATH." )
        else:
            self.pymetricsElf = os.path.abspath( pymetricsElf )
            if not os.path.exists( self.pymetricsElf ):
                raise Exception( "Cannot find pymetrics executable at " +
                                 self.pymetricsElf )
            if not os.path.isfile( self.pymetricsElf ):
                raise Exception( self.pymetricsElf +
                                 " is expected to be a file" )
            if not os.access( self.pymetricsElf, os.X_OK ):
                raise Exception( self.pymetricsElf +
                                 " does not have exec permissions" )

        # file name -> Metric
        self.report = {}
        self.retCode = -1

        self.__currentSection = []
        self.__metric = None
        return

    def getVersion( self ):
        " Provides the pymetrics version "
        try:
            for line in self.__run( [ self.pymetricsElf,
                                      '--version' ] ).split( '\n' ):
                line = line.strip()
                if line:
                    parts = line.split()
                    if len( parts ) == 2 and \
                       parts[ 0 ].startswith( 'pymetrics' ) and \
                       parts[ 1 ][ 0 ].isdigit():
                        return parts[ 1 ]
        except:
            pass
        return None

    def getPath( self ):
        return self.pymetricsElf

    def analyzeFile( self, path ):
        " run pymetrics for a certain file or files list "

        self.retCode = -1
        self.report = {}

        fileName = ""
        self.__metric = None
        self.__currentSection = []

        if type( path ) == type( "a" ):
            path = path.split()

        for line in self.__run( [ self.pymetricsElf, '-S', '-C', '-z' ] + \
                                path ).split( '\n' ):

            lineType = self.__detectLineType( line )

            if verbose:
                print str( lineType ) + " -> " + line

            if lineType == self.FileStarted:
                # === File: ...ion/src/ui/viewitems.py ===
                if fileName != "" and self.__metric is not None:
                    self.__parseCurrentSection()
                    self.report[ fileName ] = self.__metric

                self.__metric = Metric()
                parts = line.split()
                if len( parts ) != 4 or parts[ 0 ] != '===' or \
                   parts[ 1 ] != 'File:' or parts[ 3 ] != '===':
                    raise Exception( "Unknown file started line format: " + \
                                     line )
                fileName = parts[ 2 ]
                continue

            if lineType == self.ReportEnd:
                # *** Processed 1 module in run ***
                if not line.startswith( '***' ) or \
                   not line.endswith( '***' ):
                    raise Exception( "Unknown report end line format: " + line )
                if fileName != "" and self.__metric is not None:
                    self.__parseCurrentSection()
                    self.report[ fileName ] = self.__metric
                break

            if lineType == self.Message:
                # In file ...ion/src/ui/viewitems.py, function TreeView....
                # or
                # Module class_defs.py is missing a module doc string. Detected at line 1
                if line.startswith( 'In file ' ):
                    parts = line.split( ',' )
                    msg = ",".join( parts[ 1: ] )
                    self.__metric.messages.append( msg.strip() )
                elif line.startswith( 'Module ' ):
                    parts = line.split()
                    del parts[ 1 ]
                    self.__metric.messages.append( ' '.join( parts ) )
                continue

            if lineType == self.Unknown:
                self.__currentSection.append( line )
                continue

            # Here: beginning of a section
            self.__parseCurrentSection()
            self.__currentSection.append( line )
        return

    def analyzeBuffer( self, content ):
        " run pymetrics for a memory buffer "

        # Save the buffer to a temporary file
        tempDirName = tempfile.mkdtemp()
        if not tempDirName.endswith( os.path.sep ):
            tempDirName += os.path.sep
        tempFileName = tempDirName + "temp_buf_save.py"

        temporaryStorage = open( tempFileName, "w" )

        # str( content ) is required because
        # otherwise it is saved as 4 bytes encoded if taken from
        # QScintilla's buffer
        temporaryStorage.write( str( content ) )
        temporaryStorage.close()

        # Run pymetrics
        try:
            self.analyzeFile( tempFileName )
        except Exception:
            os.unlink( tempFileName )
            os.rmdir( tempDirName )
            raise

        # Remove the temporary dir and file
        os.unlink( tempFileName )
        os.rmdir( tempDirName )
        return

    def __run( self, commandArgs ):
        " Runs the given command and reads the output "

        errTmp = tempfile.mkstemp()
        errStream = os.fdopen( errTmp[ 0 ] )
        process = Popen( commandArgs, stdin = PIPE,
                         stdout = PIPE, stderr = errStream,
                         cwd = os.getcwd() )
        process.stdin.close()
        processStdout = process.stdout.read()
        process.stdout.close()
        errStream.seek( 0 )
        err = errStream.read()
        errStream.close()
        process.wait()
        try:
            os.unlink( errTmp[ 1 ] )
        except:
            pass

        self.retCode = process.returncode

        if process.returncode != 0:
            raise Exception( "Error pymetrics invocation: " + err )
        return processStdout

    def __detectLineType( self, line ):
        " Provides the pymetrics output line type "

        line = line.strip()
        if line.startswith( '===' ):
            return self.FileStarted

        if line.startswith( "Basic Metrics" ) or \
           line.startswith( "Functions DocString" ) or \
           line.startswith( "Classes DocString" ) or \
           line.startswith( "McCabe Complexity Metric" ) or \
           line.startswith( "COCOMO 2's SLOC Metric" ):
            return self.SectionStart

        if line.startswith( '***' ):
            return self.ReportEnd

        if line.startswith( 'In file ' ) or \
           line.startswith( 'Module ' ):
            return self.Message

        return self.Unknown

    def __parseCurrentSection( self ):
        " Parses one collected section "

        while len( self.__currentSection ) > 0 and \
              self.__currentSection[ 0 ].strip() == "":
            del self.__currentSection[ 0 ]

        if verbose:
            print " => Collected section:"
            for sectionLine in self.__currentSection:
                print " => " + sectionLine
            print " => End collected section"

        if len( self.__currentSection ) == 0:
            return

        firstLine = self.__currentSection[ 0 ].strip()

        # Strip the first line
        del self.__currentSection[ 0 ]
        # The next line must be -----------
        if len( self.__currentSection ) == 0 or \
           not self.__currentSection[ 0 ].startswith( '--------' ):
            raise Exception( "Unknown section format" )
        del self.__currentSection[ 0 ]

        if firstLine.startswith( 'Classes DocString' ) or \
           firstLine.startswith( 'Functions DocString' ):
            if verbose:
                print "Skipping section: " + firstLine
        elif firstLine.startswith( "Basic Metrics" ):
            self.__metric.basicMetrics.parseSection( self.__currentSection )
        elif firstLine.startswith( "McCabe Complexity Metric" ):
            self.__metric.mcCabeMetrics.parseSection( self.__currentSection )
        elif firstLine.startswith( "COCOMO 2's SLOC Metric" ):
            self.__metric.cocomo2Metrics.parseSection( self.__currentSection )
        else:
            # Unknown section, skip it
            if verbose:
                print "Skipping unknown section: " + firstLine

        self.__currentSection = []
        return


# The script execution entry point
if __name__ == "__main__":

    parser = OptionParser(
    """
    %prog  <file name> [more files]
    Parses the pymetrics output
    """ )

    parser.add_option( "-v", "--verbose",
                       action="store_true", dest="verbose", default=False,
                       help="be verbose (default: False)" )

    options, args = parser.parse_args()

    if len( args ) < 1:
        print >> sys.stderr, "One or more arguments are expected"
        sys.exit( 1 )

    verbose = options.verbose

    try:
        metrics = PyMetrics()
        metrics.analyzeFile( args[ 0: ] )

        # print results
        for filename in metrics.report:
            print "Metrics for file: " + filename
            print str( metrics.report[ filename ] )

    except Exception, excpt:
        print >> sys.stderr, str( excpt )
        sys.exit( 1 )

    sys.exit( 0 )

