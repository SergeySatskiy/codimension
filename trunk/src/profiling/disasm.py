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
from utils.compatibility import relpath
from subprocess import Popen, PIPE



def _getCode( workingDir, moduleToImport, name, importDirs ):
    """ Cmd line to get disassemble """

    if moduleToImport.endswith( ".py" ):
        moduleToImport = moduleToImport[ : -3 ]
    elif moduleToImport.endswith( ".py3" ):
        moduleToImport = moduleToImport[ : -4 ]

    srcCode = ""
    if len( importDirs ) > 0:
        srcCode += "import sys;"
        for importPath in importDirs:
            srcCode += "sys.path.append( '" + importPath + "' );"

    srcCode += "import dis;" \
               "import " + moduleToImport + " as m;" \
               "dis.dis(" + "m." + name + ")"

    return "cd " + workingDir + ";" + \
           sys.executable + " -c '" + srcCode + "'"


def _getCodeForStandaloneScript( path, name, importDirs ):
    """ Provides a complete command line for two cases:
        - there were no project loaded
        - file does not belong to the project """

    workingDir = os.path.dirname( path )
    moduleToImport = os.path.basename( path )
    return _getCode( workingDir, moduleToImport, name, importDirs )


def _getCodeForNestedScript( projectTopDir, relativePath,
                             name, importDirs ):
    """ Provides a complete command line for a module which is in
        a nested directory starting from a project top dir.
        projectTopDir is like /a/b/c
        relativePath is like d/e/f.py """
    workingDir = projectTopDir
    moduleToImport = relativePath.replace( os.path.sep, '.' )
    return _getCode( workingDir, moduleToImport, name, importDirs )


def _checkInitPresence( startDir, dirs ):
    """ Checks that all pathes down have __init__ files.
        Returns True if so
        startDir is like /a/b/c
        dirs is like d/e/f """
    candidatePath = startDir + os.path.sep
    parts = dirs.split( os.path.sep )
    for part in parts:
        candidatePath += part + os.path.sep
        if os.path.exists( candidatePath + "__init__.py" ):
            continue
        if os.path.exists( candidatePath + "__init__.py3" ):
            continue
        return False
    return True


def runWithShell( commandLine ):
    " Runs something via a shell "
    process = Popen( commandLine, shell = True,
                     stdin = PIPE, stdout = PIPE, stderr = PIPE )
    process.stdin.close()
    processStdout = process.stdout.read()
    process.stdout.close()
    processStderr = process.stderr.read()
    process.stderr.close()
    process.wait()

    if process.returncode != 0:
        raise Exception( "Error executing command: '" + \
                         commandLine + "': " + processStderr )
    return processStdout



def getDisassembled( path, name ):
    " Provides disassembler output for thr given name "

    if not os.path.exists( path ):
        raise Exception( "Cannot find file " + path )
    if not os.path.isfile( path ):
        raise Exception( "The path '" + path + "' does not point to a file" )
    if not path.endswith( '.py' ) and not path.endswith( '.py3' ):
        raise Exception( "Path must point to a python file" )

    cmdLine2 = ""
    project = GlobalData().project
    if project.isProjectFile:
        # There are at least two options:
        # - to import starting from the project top level dir
        # - to import starting from the directory where the script is located
        # Let's try both of them
        projectTopDir = os.path.dirname( project.fileName )
        scriptDir = os.path.dirname( path )
        if projectTopDir == scriptDir:
            cmdLine = _getCodeForStandaloneScript( path, name,
                                                   project.importDirs )
        else:
            # Calculate the relative path
            # it will be like 'c/d/e/my.py'
            relativePath = relpath( path, projectTopDir )

            # Make sure there are __init__ files in all paths down
            if _checkInitPresence( projectTopDir,
                                   os.path.dirname( relativePath ) ) == False:
                # No init files in the structure, so there is no point to try
                # importing from the project top directory
                cmdLine = _getCodeForStandaloneScript( path,
                                                       name,
                                                       project.importDirs )
            else:
                # Need to try both options of importing
                # We may get luck succesfully loading it
                cmdLine = _getCodeForStandaloneScript( path,
                                                       name,
                                                       project.importDirs )

                cmdLine2 = _getCodeForNestedScript( projectTopDir,
                                                    relativePath,
                                                    name,
                                                    project.importDirs )
    else:
        cmdLine = _getCodeForStandaloneScript( path, name, project.importDirs )

    # cmdLine is formed in any case
    # cmdLine2 only if certain conditions are met
    try:
        return runWithShell( cmdLine )
    except:
        if cmdLine2 != "":
            try:
                return runWithShell( cmdLine2 )
            except:
                pass
    raise Exception( "Could not get '" + name + "' disassembled" )



