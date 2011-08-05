#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010 - 2011 Sergey Satskiy <sergey.satskiy@gmail.com>
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

" import utility functions "


import os, os.path
from utils.fileutils    import detectFileType, PythonFileType, Python3FileType
from cdmbriefparser     import getBriefModuleInfoFromMemory
from PyQt4.QtGui        import QApplication
from utils.globals      import GlobalData


def getImportsList( fileContent ):
    " Parses a python file and provides a list imports in it "

    result = []
    info = getBriefModuleInfoFromMemory( str( fileContent ) )
    for importObj in info.imports:
        if importObj.name not in result:
            result.append( importObj.name )
    return result


def getImportsInLine( fileContent, lineNumber ):
    " Provides a list of imports in in the given import line "

    result = []
    info = getBriefModuleInfoFromMemory( str( fileContent ) )
    for importObj in info.imports:
        if importObj.line == lineNumber:
            if importObj.name not in result:
                result.append( importObj.name )
    return result


def __scanDir( prefix, path, infoLabel = None ):
    " Recursive scan for modules "

    if infoLabel is not None:
        infoLabel.setText( "Scanning " + path + "..." )
        QApplication.processEvents()

    result = []
    for item in os.listdir( path ):
        if item in [ ".svn", ".cvs" ]:
            continue
        if os.path.isdir( path + item ):
            result += __scanDir( prefix + item + ".",
                                 path + item + os.path.sep,
                                 infoLabel )
            continue

        fileType = detectFileType( path + item )
        if fileType not in [ PythonFileType, Python3FileType ]:
            continue
        if item.startswith( '__init__.' ):
            if prefix != "":
                result.append( prefix[ : -1 ] )
            continue

        nameParts = item.split( '.' )
        result.append( prefix + nameParts[ 0 ] )

    return result


def buildDirModules( path, infoLabel = None ):
    " Provides a list of modules how they can appear in the import statements "
    abspath = os.path.abspath( path )
    if not os.path.exists( abspath ):
        raise Exception( "Cannot build list of modules for not " \
                         "existed dir (" + path + ")" )
    if not os.path.isdir( abspath ):
        raise Exception( "Cannot build list of modules. The path " + path + \
                         " is not a directory." )
    if not abspath.endswith( os.path.sep ):
        abspath += os.path.sep
    return __scanDir( "", abspath, infoLabel )


def __checkImport( path, importStr ):
    " Tests one dir "
    if not path.endswith( os.path.sep ):
        path += os.path.sep

    path += importStr
    if os.path.exists( path + ".py" ):
        return path + ".py"
    if os.path.exists( path + ".py3" ):
        return path + ".py3"

    path += os.path.sep + "__init__.py"
    if os.path.exists( path ):
        return path
    if os.path.exists( path + "3" ):
        return path + "3"

    return ""


def resolveImport( basePath, importString ):
    " Resolves a single import "
    importString = importString.replace( '.', os.path.sep )
    if basePath != '':
        path = __checkImport( basePath, importString )
        if path != "":
            return path

    # Could not find at hand, try the project dirs as a base
    dirs = GlobalData().project.getProjectDirs()
    for basePath in dirs:
        path = __checkImport( basePath, importString )
        if path != "":
            return path

    return ""

