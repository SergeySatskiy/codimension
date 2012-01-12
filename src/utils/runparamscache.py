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


""" codimension run parameters cache """

import cPickle
from run import RunParameters


class RunParametersCache( object ):
    """ Provides the run parameters cache """

    def __init__( self ):

        # path -> RunParameters, see run.py
        # The path can be relative or absolute:
        # relative for project files, absolute for non-project ones
        self.__cache = {}
        return

    def get( self, path ):
        """ Provides the required parameters object """
        try:
            return self.__cache[ path ]
        except KeyError:
            return RunParameters()

    def add( self, path, params ):
        " Adds run params into cache if needed "
        if params.isDefault():
            if not self.__cache.has_key( path ):
                return
            self.remove( path )
            return
        # Non-default, so need to insert
        self.__cache[ path ] = params
        return

    def remove( self, path ):
        " Removes one item from the map "
        try:
            del self.__cache[ path ]
        except KeyError:
            return

    def serialize( self, path ):
        " Saves the cache into the given file "
        ouf = open( path, "wb" )
        cPickle.dump( self.__cache, ouf, 1 )
        ouf.close()
        return

    def deserialize( self, path ):
        " Loads the cache from the given file "
        inf = open( path, "rb" )
        self.__cache = cPickle.load( inf )
        inf.close()
        return

