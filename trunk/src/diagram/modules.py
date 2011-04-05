#
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


""" Utility functions for building modules lists """


import os, os.path
from utils.fileutils    import detectFileType, PythonFileType, Python3FileType
from PyQt4.QtGui        import QApplication


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

