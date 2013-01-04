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

" Unit tests for the python control flow parser "

import unittest
import os.path
import sys
from cdmcfparser import ( getControlFlowFromMemory,
                          getControlFlowFromFile, getVersion )



def files_equal( name1, name2 ):
    " Compares two files. Returns True if their content matches "

    if not os.path.exists( name1 ):
        print >> sys.stderr, "Cannot open " + name1
        return False

    if not os.path.exists( name2 ):
        print >> sys.stderr, "Cannot open " + name2
        return False

    file1 = open( name1 )
    file2 = open( name2 )
    content1 = file1.read()
    content2 = file2.read()
    file1.close()
    file2.close()
    return content1.strip() == content2.strip()


class CDMControlFlowParserTest( unittest.TestCase ):
    " Unit test class "

    def setUp( self ):
        " Initialisation "

        self.dir = "unittest" + os.path.sep
        if not os.path.isdir( self.dir ):
            raise Exception( "Cannot find directory with tests. " \
                             "Expected here: " + self.dir )
        return

    def meat( self, pythonFile, errorMsg ):
        " The test process meat "

        controlFlow = getControlFlowFromFile( pythonFile )
        self.failUnless( controlFlow.isOK == True )

        f = open( pythonFile )
        content = f.read()
        f.close()

        controlFlow = getControlFlowFromMemory( content )
        self.failUnless( controlFlow.isOK == True )

        outFileName = pythonFile.replace( ".py", ".out" )
        outFile = open( outFileName, "w" )
        outFile.write( str( controlFlow ) )
        outFile.close()

        okFileName = pythonFile.replace( ".py", ".ok" )
        self.failUnless( files_equal( outFileName, okFileName ),
                         errorMsg )
        return

    def test_empty( self ):
        " Test empty file "
        self.meat( self.dir + "empty.py",
                   "empty file test failed" )
        return

#    def test_import( self ):
#        " Tests imports "
#        self.meat( self.dir + "import.py",
#                   "import test failed" )
#        return

#    def test_coding1( self ):
#        " Test coding 1"
#        self.meat( self.dir + "coding1.py",
#                   "error retrieving coding" )
#        return

#    def test_coding2( self ):
#        " Test coding 2"
#        self.meat( self.dir + "coding2.py",
#                   "error retrieving coding" )
#        return

#    def test_coding3( self ):
#        " Test coding 3"
#        self.meat( self.dir + "coding3.py",
#                   "error retrieving coding" )
#        return

#    def test_function_definitions( self ):
#        " Test function definitions"
#        self.meat( self.dir + "func_defs.py",
#                   "function definition test failed" )
#        return

#    def test_nested_func_definitions( self ):
#        " Test nested functions definitions "
#        self.meat( self.dir + "nested_funcs.py",
#                   "nested functions definitions test failed" )
#        return

#    def test_globals( self ):
#        " Test global variables "
#        self.meat( self.dir + "globals.py",
#                   "global variables test failed" )
#        return

#    def test_class_definitions( self ):
#        " Test class definitions "
#        self.meat( self.dir + "class_defs.py",
#                   "class definitions test failed" )
#        return

#    def test_nested_classes( self ):
#        " Test nested classes "
#        self.meat( self.dir + "nested_classes.py",
#                   "nested classes test failed" )
#        return

#    def test_docstrings( self ):
#        " Test docstrings "
#        self.meat( self.dir + "docstring.py",
#                   "docstring test failed" )
#        return

#    def test_decorators( self ):
#        " Test decorators "
#        self.meat( self.dir + "decorators.py",
#                   "decorators test failed" )
#        return

#    def test_static_members( self ):
#        " Test class static members "
#        self.meat( self.dir + "static_members.py",
#                   "class static members test failed" )
#        return

#    def test_class_members( self ):
#        " Test class members "
#        self.meat( self.dir + "class_members.py",
#                   "class members test failed" )
#        return

#    def test_errors( self ):
#        " Test errors "

#        pythonFile = self.dir + "errors.py"
#        info = getControlFlowFromFile( pythonFile )
#        self.failUnless( info.isOK != True )

#        outFileName = pythonFile.replace( ".py", ".out" )
#        outFile = open( outFileName, "w" )
#        outFile.write( info.niceStringify() )
#        for item in info.errors:
#            outFile.write( "\n" + item )
#        outFile.close()

#        okFileName = pythonFile.replace( ".py", ".ok" )
#        self.failUnless( files_equal( outFileName, okFileName ),
#                         "errors test failed" )
#        return

#    def test_wrong_indent( self ):
#        " Test wrong indent "

#        pythonFile = self.dir + "wrong_indent.py"
#        info = getControlFlowFromFile( pythonFile )
#        self.failUnless( info.isOK != True )

#        outFileName = pythonFile.replace( ".py", ".out" )
#        outFile = open( outFileName, "w" )
#        outFile.write( info.niceStringify() )
#        for item in info.errors:
#            outFile.write( "\n" + item )
#        outFile.close()

#        okFileName = pythonFile.replace( ".py", ".ok" )
#        self.failUnless( files_equal( outFileName, okFileName ),
#                         "wrong indent test failed" )
#        return

#    def test_one_comment( self ):
#        " Test for a file which consists of a single comment line "

#        self.meat( self.dir + "one_comment.py",
#                   "one comment line test failed" )
#        return

#    def test_comments_only( self ):
#        " Test for a file with no other lines except of comments "

#        self.meat( self.dir + "commentsonly.py",
#                   "comments only with no other empty lines test failed" )

#    def test_noendofline( self ):
#        " Test for a file which has no EOL at the end "

#        self.meat( self.dir + "noendofline.py",
#                   "No end of line at the end of the file test failed" )

#    def test_empty_brackets( self ):
#        " Test for empty brackets "

#        self.meat( self.dir + "empty_brackets.py",
#                   "empty brackets test failed" )
#        return


# Run the unit tests
if __name__ == '__main__':
    print "Testing control flow parser version: " + getVersion()
    unittest.main()

