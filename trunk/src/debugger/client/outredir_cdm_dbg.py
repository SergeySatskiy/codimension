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


"""
Redirectors for stdout/stderr streams
"""

import socket

MAX_TRIES = 5


class OutStreamRedirector( object ):
    " Wraps a socket object with a file interface "

    maxbuffersize = 1024 * 1024 * 4

    def __init__( self, sock ):
        self.closed = False
        self.sock = sock
        self.sock.setsockopt( socket.IPPROTO_TCP, socket.TCP_NODELAY, True )
        return

    def close( self, closeit = False ):
        " Closes the file. closeit != 0 => debugger requested it "
        if closeit and not self.closed:
            self.flush()
            self.sock.close()
            self.closed = True
        return

    def flush( self ):
        " Does nothing because there is no buffering "
        return

    def isatty( self ):
        " Indicates whether a tty interface is supported "
        return 0

    def fileno( self ):
        " Provides the file number "
        try:
            return self.sock.fileno()
        except socket.error:
            return -1

    def read_p( self, size = -1 ):
        " Read is not supported "
        raise IOError, '[Errno 9] Bad file descriptor'

    def read( self, size = -1 ):
        " Read is not supported "
        raise IOError, '[Errno 9] Bad file descriptor'

    def readline_p( self, size = -1 ):
        " Read is not supported "
        raise IOError, '[Errno 9] Bad file descriptor'

    def readlines( self, sizehint = -1 ):
        " Read is not supported "
        raise IOError, '[Errno 9] Bad file descriptor'

    def readline( self, sizehint = -1 ):
        " Read is not supported "
        raise IOError, '[Errno 9] Bad file descriptor'

    def seek( self, offset, whence = 0 ):
        " Seek is not supported "
        raise IOError, '[Errno 29] Illegal seek'

    def tell( self ):
        " Tell is not supported "
        raise IOError, '[Errno 29] Illegal seek'

    def truncate( self, size = -1 ):
        " Truncates is not supported "
        raise IOError, '[Errno 29] Illegal seek'

    def write( self, data ):
        " Writes a string to the file "

        try:
            data = data.encode( 'utf8' )
        except ( UnicodeEncodeError, UnicodeDecodeError ):
            pass

        tries = MAX_TRIES
        while tries > 0:
            try :
                self.sock.sendall( data )
                return
            except socket.error:
                tries -= 1
                continue

        raise socket.error( "Too many attempts to send data" )

    def writelines( self, lines ):
        " Writes a list of strings to the file "
        map( self.write, lines )
        return

