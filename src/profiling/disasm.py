#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Disassembling classes and functions "

import os.path
import sys
from utils.globals import GlobalData



def getDisassembled( path, name ):
    " Provides disassembler output for thr given name "

    if not os.path.exists( path ):
        raise Exception( "Cannot find file " + path )
    if not os.path.isfile( path ):
        raise Exception( "The path '" + path + "' does not point to a file" )
    if not path.endswith( '.py' ) and not path.endswith( '.py3' ):
        raise Exception( "Path must point to a python file" )

    project = GlobalData().project
    if project.isLoaded():
        pass
    else:
        # No project, just cd to the dir
        workingDir = os.path.dirname( path )
        moduleToImport = os.path.basename( path )
        if moduleToImport.endswith( ".py" ):
            moduleToImport = moduleToImport[ : -3 ]
        elif moduleToImport.endswith( ".py3" ):
            moduleToImport = moduleToImport[ : -3 ]

        srcCode = "import dis;" \
                  "import " + moduleToImport + ";" \
                  "dis.dis(" + name + ")"

        commandLine = "cd " + workingDir + ";" + \
                      sys.executable + " -c '" + srcCode + "'"




