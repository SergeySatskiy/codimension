#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# Some code was taken from here and adopted for codimension:
# http://code.google.com/p/spyderlib/source/browse/spyderlib/utils/codeanalysis.py
#
# $Id$
#


""" Utilities to extract various TODO items from files/code """


import re


TODO_PATTERN = r"(^|#)[ ]*(TODO|FIXME|XXX|HINT|TIP)( |:|$)([^#]*)"


def findTodoItemsInBuffer( sourceCode ):
    " Find tasks in source code (TODO, FIXME, XXX, ...) "

    results = []
    for line, text in enumerate( sourceCode.splitlines(), 1 ):
        for todo in re.findall( TODO_PATTERN, text ):
            results.append( ( todo[ -1 ].strip().capitalize(), line ) )
    return results


def findTodoItemsInFile( fName ):
    " Find tasks in a file (TODO, FIXME, XXX, ...) "
    f = open( fName )
    content = f.read()
    f.close()

    return findTodoItemsInBuffer( content )


def findTodoItemsInDir( dirName ):
    " Find tasks in files in the given dir (TODO, FIXME, XXX, ...) "



def findTodoItems( where ):
    " Detects what is it and provides tasks accordingly "

    # where could be: buffer, file, directory, list of files/dirs

