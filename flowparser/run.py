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

import sys      # side comment: line 1
                #               line 2
from cdmcf import getControlFlowFromFile, VERSION

if len( sys.argv ) != 2:
    print >> sys.stderr, "Single file name is expected"
    sys.exit( 1 )

print "Running control flow parser version: " + VERSION

controlFlow = getControlFlowFromFile( sys.argv[ 1 ] )
print controlFlow
sys.exit( 0 )

