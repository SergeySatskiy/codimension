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

" Speed test for the codimension brief parser "

import os, os.path, sys
import datetime
import pyclbr
from cdmcfparser import getControlFlowFromFile, getVersion


def collectFiles( path, files ):
    " Collects python files "
    if not path.endswith( os.path.sep ):
        path += os.path.sep
    for item in os.listdir( path ):
        if os.path.isdir( path + item ):
            collectFiles( path + item, files )
        if item.endswith( ".py" ):
            if item.startswith( "__" ):
                continue
            files.append( os.path.abspath( path + item ) )
            continue
    return


def cdmcfparserTest( files ):
    " Loop for the codimension parser "
    count = 0
    for item in files:
        #print "Processing " + item + " ..."
        tempObj = getControlFlowFromFile( item )
        count += 1
    print "cdmcfparser: processed " + str(count) + " file(s)"
    return


print "Speed test measures the time required for " \
      "cdmcfparser to parse python files."
print "Parser version: " + getVersion()


pythonFiles = []
if len( sys.argv ) > 1:
    # File names are expected
    for fname in sys.argv[ 1: ]:
        if not os.path.exists( fname ):
            print "Cannot find file specified: '" + fname + "'"
            sys.exit( 1 )
        pythonFiles.append( os.path.abspath( fname ) )
    print "Files to test: " + str(len(pythonFiles))
else:
    print "Collecting a list of python classes..."
    startDir = os.path.sep + "usr" + os.path.sep + "lib64" + os.path.sep + \
               "python2.7" + os.path.sep
    if not os.path.exists( startDir ):
        startDir = os.path.sep + "usr" + os.path.sep + "lib" + os.path.sep + \
                   "python2.7" + os.path.sep
    collectFiles( startDir, pythonFiles )
    print "Collected " + str(len(pythonFiles)) + " files from " + startDir


# timing for cdmcfparser
start = datetime.datetime.now()
cdmcfparserTest( pythonFiles )
end = datetime.datetime.now()

print "cdmcfparser timing:"
print "Start: " + str( start )
print "End:   " + str( end )
print "Delta: " + str( end - start )

