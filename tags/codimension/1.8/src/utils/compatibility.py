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

" Compatibility routines, e.g. os.path.relpath() is not in python 2.5 "

import os.path

# The implementation is taken from the python distribution
# I need it because the relpath() appears in python 2.6 while
# python 2.5 is still in wide usage
def relpath( path, start = os.path.curdir ):
    """ Return a relative version of a path """
    if not path:
        raise ValueError( "no path specified" )
    start_list = os.path.abspath( start ).split( os.path.sep )
    path_list = os.path.abspath( path ).split( os.path.sep )
    # Work out how much of the filepath is shared by start and path.
    i = len( os.path.commonprefix( [ start_list, path_list ] ) )
    rel_list = [ os.path.pardir ] * ( len( start_list ) - i ) + path_list[ i: ]
    if not rel_list:
        return os.path.curdir
    return os.path.join( *rel_list )

