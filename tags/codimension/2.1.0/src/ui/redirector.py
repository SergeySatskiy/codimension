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
# $Id: redirector.py 17 2011-01-16 21:23:13Z sergey.satskiy@gmail.com $
#

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" Helper redirector class """

from PyQt4.QtCore import QObject, SIGNAL



class Redirector( QObject ):
    """ Helper class used to redirect stdout and stderr to the log window """

    def __init__( self, isStdout ):
        QObject.__init__( self )
        self.isStdout = isStdout
        self.buffer = ''
        return

    def __del__( self ):
        self.flush()
        return

    def __nWrite( self, nBytes ):
        """ Writes n bytes of data """

        if nBytes > 0:
            line = self.buffer[ :nBytes ]
            if self.isStdout:
                self.emit( SIGNAL('appendToStdout'), line )
            else:
                self.emit( SIGNAL('appendToStderr'), line )
            self.buffer = self.buffer[ nBytes: ]
        return

    def __bytesToWrite( self ):
        """ Provides the number of characters to write """

        return self.buffer.rfind( '\n' ) + 1

    def flush( self ):
        """ Flushes the buffered data """

        self.__nWrite( len( self.buffer ) )
        return

    def write( self, message ):
        """ Writes the given data """

        while message.endswith( '\n' ):
            message = message[ :-1 ]
        if self.isStdout:
            self.emit( SIGNAL('appendToStdout'), message )
        else:
            self.emit( SIGNAL('appendToStderr'), message )
#        self.buffer = self.buffer + unicode( message )
#        self.__nWrite( self.__bytesToWrite() )
#        return

