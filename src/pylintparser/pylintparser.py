#!/usr/bin/env python
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


" pylint output parser "


from subprocess import Popen, PIPE
import sys, os, os.path, tempfile, re
from optparse  import OptionParser
import logging


verbose = False


class ErrorMessage( object ):
    " Holds a single error message "

    def __init__( self, line, cwd ):

        self.__cwd = cwd
        if not self.__cwd.endswith( os.path.sep ):
            self.__cwd += os.path.sep
        self.fileName = ""
        self.lineNumber = -1
        self.messageID = ""
        self.objectName = ""    # could be empty
        self.message = ""

        self.__parse( line )
        return

    def __parse( self, line ):
        " parses the error message line "

        line = line.strip()
        parts = line.split( ':' )
        if len( parts ) < 3:
            raise Exception( "Unexpected pylint message format: " + line )

        reportFileName = parts[ 0 ].strip()
        if os.path.isabs( reportFileName ):
            self.fileName = reportFileName
        else:
            self.fileName = self.__cwd + reportFileName
        self.lineNumber = int( parts[ 1 ].strip() )

        msg = ":".join( parts[ 2: ] )   # The message without the
                                        # file name and line number
        msg = msg.strip()
        parts = msg.split( ']' )
        if len( parts ) < 2 or not parts[ 0 ].startswith( '[' ):
            raise Exception( "Unexpected pylint message format: " + line )

        parts[ 0 ] = parts[ 0 ][ 1: ]   # Strip leading [
        msgParts = parts[ 0 ].split( ',' )
        self.messageID = msgParts[ 0 ]
        if len( msgParts ) == 2:
            self.objectName = msgParts[ 1 ].strip()

        self.message = "]".join( parts[ 1: ] ).strip()
        return

    def __str__( self ):
        " Converts the message to a string "
        return "[" + self.fileName + ":" + str( self.lineNumber ) + "][" + \
               self.messageID + "][" + self.objectName + "] " + self.message



class Table( object ):
    " Holds a single table from the pylint report "

    def __init__( self, section ):
        self.header = []
        self.body = []
        self.title = ""

        self.__parse( section )
        return

    def __parse( self, section ):
        " Parses one section with a table inside "
        self.title = section[ 0 ].strip()
        if len( section ) < 8:
            raise Exception( "Unexpected length of a " \
                             "table section (" + self.title + ")" )
        if not section[ 1 ].startswith( "------" ):
            raise Exception( "Unexpected format of a " \
                             "table section (" + self.title + ")" )

        for index in range( 2, len( section ) ):
            if section[ index ].startswith( '|' ):
                values = self.__getValues( section[ index ] )
                if len( self.header ) == 0:
                    self.header = values
                else:
                    self.body.append( values )
        return

    @staticmethod
    def __getValues( line ):
        " Extracts a table row values from the line "
        line = line.strip()
        line = line[ 1:-1 ]
        parts = line.split( '|' )
        for index in range( len( parts ) ):
            parts[ index ] = parts[ index ].strip()
        return parts

    def __str__( self ):
        " Converts a table to a string "
        bodyPart = ""
        for row in self.body:
            bodyPart += "\nBody: " + " | ".join( row )

        return "Title: " + self.title + "\n" \
               "Header: " + " | ".join( self.header ) + \
               bodyPart



class Similarity( object ):
    " Holds information about found similarity "

    def __init__( self, section, filesList ):
        self.files = []
        self.fragment = []

        self.__parse( section, filesList )
        return

    def __parse( self, section, filesList ):
        " Parses a single similarity section "
        if len( section ) < 3:
            raise Exception( "Unexpected length of a " \
                             "similarity section" )
        parts = section[ 0 ].split()
        numberOfFiles = int( parts[ len( parts ) - 2 ] )
        index = 0
        while index < numberOfFiles:
            self.files.append( self.__getFileInfo( section[ index + 1 ],
                                                   filesList ) )
            index += 1

        self.fragment = section[ 1 + numberOfFiles : ]

        # Remove trailing space lines
        while self.fragment[ len( self.fragment ) - 1 ].strip() == "":
            del self.fragment[ len( self.fragment ) - 1 ]
        return

    @staticmethod
    def __getFileInfo( line, filesList ):
        " Extracts one file info "
        line = line.strip()
        if not line.startswith( "==" ):
            raise Exception( "Unexpected format of a " \
                             "similarity section (" + line + ")" )
        line = line[ 2: ]
        parts = line.split( ':' )
        if len( parts ) != 2:
            raise Exception( "Unexpected format of a " \
                             "similarity section (" + line + ")" )

        # pylint makes a mistake for 1 line (at least version 0.22.0)
        parts[ 1 ] = int( parts[ 1 ] ) + 1

        # Guess file name - pylint gives the module names but not file names
        cwd = os.getcwd()
        if not cwd.endswith( os.path.sep ):
            cwd += os.path.sep
        parts[ 0 ] = parts[ 0 ].replace( '.', os.path.sep )
        candidate = cwd + parts[ 0 ] + ".py"
        if os.path.exists( candidate ):
            parts[ 0 ] = candidate
        else:
            candidate = cwd + parts[ 0 ] + ".py3"
            if os.path.exists( candidate ):
                parts[ 0 ] = candidate
            else:
                parts[ 0 ] = Similarity.__findFileName( parts[ 0 ], filesList )
        return parts

    @staticmethod
    def __findFileName( moduleName, filesList ):
        """ Makes the last try to find the file name for similarities.
            It looks through the list of files and tries .py and .py3
            files. If there are more than one or many it throws
            an exception """
        candidates = []
        match1 = os.path.sep + moduleName + ".py"
        match2 = os.path.sep + moduleName + ".py3"
        for fName in filesList:
            if fName.endswith( match1 ):
                candidates.append( fName )
                continue
            if fName.endswith( match2 ):
                candidates.append( fName )

        length = len( candidates )
        if length == 0:
            raise Exception( "Cannot guess file name for pylint " \
                             "similarity (module " + moduleName + \
                             "). No candidates found." )
        if length > 1:
            raise Exception( "Cannot guess file name for pylint " \
                             "similarity (module " + moduleName + \
                             "). There are many candidates: " + \
                             ", ".join( candidates ) + ". You may " \
                             "want to rename them to make names unique." )
        return candidates[ 0 ]

    def __str__( self ):
        " Converts a similarity to a string "
        filesPart = "Similarity: ["
        for index in range( len( self.files ) ):
            filesPart += self.files[ index ][ 0 ] + ':' + \
                         str( self.files[ index ][ 1 ] )
            if index < len( self.files ) - 1:
                filesPart += ", "
        filesPart += "]"
        codePart = "\n".join( self.fragment )
        return filesPart + "\n" + codePart



class Dependencies( object ):
    " Holds information about dependencies "

    def __init__( self, section ):
        pass


class Pylint( object ):
    " Holds a pylint report "

    Unknown         = -1
    Message         = 0
    MessageSimilar  = 1
    SectionStart    = 2

    def __init__( self ):

        self.retCode = -1
        self.errorMessages = []
        self.tables = []
        self.similarities = []
        self.dependencies = None
        self.statementsAnalysed = 0
        self.score = 0.0
        self.previousScore = 0.0

        self.__currentSection = []
        self.__messageRegexp = \
            re.compile( "^\S+:\d+:\s*\[\S+.*\]\s*\S*" )
        self.__similarRegexp = \
            re.compile( "^\S+:\d+:\s*\[\S+.*\]\s*Similar lines in" )

        return

    def analyzeFile( self, path, pylintrc = "",
                     importDirs = [], workingDir = "" ):
        " run pylint for a certain file or files list "

        self.retCode = -1
        self.errorMessages = []
        self.tables = []
        self.similarities = []
        self.dependencies = None
        self.statementsAnalysed = 0
        self.score = 0.0
        self.previousScore = 0.0

        self.__currentSection = []

        if pylintrc != "" and not os.path.exists( pylintrc ):
            # This is a buffer with an rc content
            tempDirName = tempfile.mkdtemp()
            if not tempDirName.endswith( os.path.sep ):
                tempDirName += os.path.sep
            tempFileName = tempDirName + "temp_pylint.rc"

            temporaryStorage = open( tempFileName, "w" )
            temporaryStorage.write( str( pylintrc ) )
            temporaryStorage.close()

        if type( path ) == type( "a" ):
            path = path.split()

        # Run pylint with a parseable output and with messages types
        try:

            rcArg = []
            if pylintrc:
                if os.path.exists( pylintrc ):
                    rcArg = [ "--rcfile=" + pylintrc ]
                else:
                    rcArg = [ "--rcfile=" + tempFileName ]

            initHook = [ "--init-hook" ]
            if importDirs:
                code = "import sys"
                for dirName in importDirs:
                    code += ";sys.path.insert(0,'" + dirName + "')"

            # Dirty hack to support CGI files pylinting
            if code:
                code += ";\n"
            code += "try: from logilab.common import modutils;" \
                    "modutils.PY_SOURCE_EXTS=('py','cgi');\nexcept: pass"

            initHook.append( code )

            skipTillRecognised = False
            for line in self.__run( [ 'pylint', '-f', 'parseable',
                                      '-i', 'y'] +
                                    initHook + rcArg +
                                    path, workingDir ).split( '\n' ):
                if skipTillRecognised:
                    lineType, shouldSkip = self.__detectLineType( line )
                    if lineType == self.Unknown:
                        continue
                    skipTillRecognised = shouldSkip
                else:
                    lineType, skipTillRecognised = self.__detectLineType( line )

                if verbose:
                    print str( lineType ) + " -> " + line
                if lineType == self.Message:
                    self.errorMessages.append( ErrorMessage( line,
                                                             workingDir ) )
                    continue

                if lineType == self.Unknown:
                    self.__currentSection.append( line )
                    continue

                # Here: beginning of a section or beginning of a similarity
                # message
                self.__parseCurrentSection( path )
                self.__currentSection.append( line )

            # Final section parsing
            self.__parseCurrentSection( path )

        except Exception, exc:
            if pylintrc != "" and not os.path.exists( pylintrc ):
                os.unlink( tempFileName )
                os.rmdir( tempDirName )
            raise

        if pylintrc != "" and not os.path.exists( pylintrc ):
            os.unlink( tempFileName )
            os.rmdir( tempDirName )
        return

    def analyzeBuffer( self, content, pylintrc = "",
                       importDirs = [], workingDir = "" ):
        " run pylint for a memory buffer "

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

        # Run pylint
        try:
            self.analyzeFile( tempFileName, pylintrc, importDirs, workingDir )
        except Exception, exc:
            os.unlink( tempFileName )
            os.rmdir( tempDirName )
            raise

        # Remove the temporary dir and file
        os.unlink( tempFileName )
        os.rmdir( tempDirName )
        return

    def __run( self, commandArgs, workingDir ):
        " Runs the given command and reads the output "

        errTmp = tempfile.mkstemp()
        errStream = os.fdopen( errTmp[ 0 ] )
        process = Popen( commandArgs, stdin = PIPE,
                         stdout = PIPE, stderr = errStream,
                         cwd = workingDir )
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
        # pylint may return any value as its return code however in case of
        # crash it returns 1 and its trace is in stderr
        if process.returncode == 1:
            if "Traceback" in err:
                raise Exception( "pylint crash:\n" + err )
        return processStdout

    def __detectLineType( self, line ):
        """ Provides the pylint output line type and a flag
            if some lines should be skipped  """

        # Some error messages are multiline:
        # ... Comma not followed by a space
        # ... Operator not followed by a space
        # ... Operator not preceded by a space

        line = line.strip()
        if line in [ 'Global evaluation', 'Messages',
                     '% errors / warnings by module',
                     'Messages by category',
                     'Duplication', 'External dependencies',
                     'Statistics by type', 'Raw metrics',
                     'Report' ]:
            return self.SectionStart, False

        if self.__similarRegexp.match( line ):
            return self.MessageSimilar, False

        if self.__messageRegexp.match( line ):
            if "Comma not followed by a space" in line or \
               "Operator not followed by a space" in line or \
               "Operator not preceded by a space" in line:
                return self.Message, True
            return self.Message, False

        return self.Unknown, False

    def __parseCurrentSection( self, filesList ):
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
        if firstLine == 'Global evaluation':
            self.__parseGlobalEvaluation()
        elif firstLine in [ 'Messages',
                            '% errors / warnings by module',
                            'Messages by category',
                            'Duplication',
                            'Statistics by type',
                            'Raw metrics' ]:
            self.tables.append( Table( self.__currentSection ) )
        elif firstLine == 'External dependencies':
            self.dependencies = Dependencies( self.__currentSection )
        elif firstLine == 'Report':
            self.__parseReport()
        elif self.__similarRegexp.match( firstLine ):
            try:
                self.similarities.append(
                        Similarity( self.__currentSection, filesList ) )
            except Exception, exc:
                logging.error( str( exc ) )
                logging.error( "Skipping this similarity" )
        else:
            raise Exception( "unknown pylint output section: '" + \
                             firstLine + "'" )
        self.__currentSection = []
        return

    def __parseGlobalEvaluation( self ):
        " Parses the global evaluation "
        if len( self.__currentSection ) < 3:
            raise Exception( "Unexpected length of the " \
                             "global evaluation section" )
        if not self.__currentSection[ 1 ].startswith( '-------' ):
            raise Exception( "Unexpected format of the " \
                             "global evaluation section" )

        # Your code has been rated at 4.17/10
        # Your code has been rated at 9.45/10 (previous run: 9.46/10)
        line = self.__currentSection[ 2 ].replace( \
            "Your code has been rated at", "" ).strip()
        parts = line.split( '/' )
        if len( parts ) < 2:
            raise Exception( "Unexpected format of the " \
                             "global evaluation section" )
        self.score = float( parts[ 0 ] )
        if len( parts ) == 3:
            line = parts[ 1 ].replace( "10 (previous run:", "" ).strip()
            self.previousScore = float( line )
        return

    def __parseReport( self ):
        " Parses the report "
        if len( self.__currentSection ) < 3:
            raise Exception( "Unexpected length of the " \
                             "report section" )
        if not self.__currentSection[ 1 ].startswith( '=====' ):
            raise Exception( "Unexpected format of the " \
                             "report section" )

        # 4304 statements analysed.
        parts = self.__currentSection[ 2 ].split()
        if len( parts ) < 1:
            raise Exception( "Unexpected format of the " \
                             "report section" )
        self.statementsAnalysed = int( parts[ 0 ] )
        return

# The script execution entry point
if __name__ == "__main__":

    parser = OptionParser(
    """
    %prog  <file name> [more files]
    Parses the pylint output
    """ )

    parser.add_option( "-v", "--verbose",
                       action="store_true", dest="verbose", default=False,
                       help="be verbose (default: False)" )

    options, args = parser.parse_args()

    if len( args ) < 1:
        print >> sys.stderr, "One or more arguments are expected"
        sys.exit( 1 )

    verbose = options.verbose

    lint = Pylint()
    lint.analyzeFile( args[ 0: ] )

    print "Collected information:"
    print "Ret code: " + str( lint.retCode )
    print "Statements analysed: " + str( lint.statementsAnalysed )
    print "Score: " + str( lint.score )
    print "Previous score: " + str( lint.previousScore )

    if len( lint.errorMessages ) == 0:
        print "No error messages found"
    else:
        print "Found " + str( len( lint.errorMessages ) ) + " error messages:"
        for item in lint.errorMessages:
            print item

    if len( lint.tables ) == 0:
        print "No tables found"
    else:
        print "Found " + str( len( lint.tables ) ) + " tables:"
        for item in lint.tables:
            print item

    if len( lint.similarities ) == 0:
        print "No similarities found"
    else:
        print "Found " + str( len( lint.similarities ) ) + " similarities:"
        for item in lint.similarities:
            print item

    sys.exit( 0 )

