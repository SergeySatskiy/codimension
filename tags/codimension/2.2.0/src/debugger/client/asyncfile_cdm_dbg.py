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

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an asynchronous
file like socket interface for the debugger.
"""

import socket

from protocol_cdm_dbg import EOT


def AsyncPendingWrite( fileObj ):
    """
    Checks for data to be written

    @param fileObj The file object to be checked (file)
    @return Flag indicating if there is data wating (int)
    """

    try:
        pending = fileObj.pendingWrite()
    except:
        pending = 0
    return pending


class AsyncFile( object ):
    " Wrapps a socket object with a file interface "

    maxtries = 10
    maxbuffersize = 1024 * 1024 * 4

    def __init__( self, sock, mode, name ):
        """
        @param sock the socket object being wrapped
        @param mode mode of this file (string)
        @param name name of this file (string)
        """

        # Initialise the attributes.
        self.closed = 0
        self.sock = sock
        self.mode = mode
        self.name = name
        self.nWriteErrors = 0

        self.wpending = u''
        return

    def __checkMode( self, mode ):
        """
        Checks the mode

        This method checks, if an operation is permitted according to
        the mode of the file. If it is not, an IOError is raised.

        @param mode the mode to be checked (string)
        """

        if mode != self.mode:
            raise IOError, '[Errno 9] Bad file descriptor'
        return

    def __nWrite( self, n ):
        """
        Writes a specific number of pending bytes

        @param n the number of bytes to be written (int)
        """

        if n:
            try :
                buf = "%s%s" % ( self.wpending[ : n ], EOT )
                try:
                    buf = buf.encode( 'utf8' )
                except ( UnicodeEncodeError, UnicodeDecodeError ):
                    pass
                self.sock.sendall( buf )
                self.wpending = self.wpending[ n : ]
                self.nWriteErrors = 0
            except socket.error:
                self.nWriteErrors += 1
                if self.nWriteErrors > self.maxtries:
                    self.wpending = u'' # delete all output
        return

    def pendingWrite( self ):
        """
        Returns the number of bytes waiting to be written

        @return the number of bytes to be written (int)
        """

        return self.wpending.rfind( '\n' ) + 1

    def close( self, closeit = 0 ):
        """
        Closes the file

        @param closeit flag to indicate a close ordered by
                       the debugger code (boolean)
        """

        if closeit and not self.closed:
            self.flush()
            self.sock.close()
            self.closed = 1
        return

    def flush( self ):
        " Writes all pending bytes "

        self.__nWrite( len( self.wpending ) )
        return

    def isatty( self ):
        """
        Indicates whether a tty interface is supported.

        @return always false
        """
        return 0

    def fileno( self ):
        """
        Public method returning the file number.

        @return file number (int)
        """
        try:
            return self.sock.fileno()
        except socket.error:
            return -1

    def read_p( self, size = -1 ):
        """
        Reads bytes from this file

        @param size maximum number of bytes to be read (int)
        @return the bytes read (any)
        """
        self.__checkMode( 'r' )

        if size < 0:
            size = 20000

        return self.sock.recv(size).decode( 'utf8' )

    def read( self, size = -1 ):
        """
        Reads bytes from this file

        @param size maximum number of bytes to be read (int)
        @return the bytes read (any)
        """
        self.__checkMode( 'r' )

        buf = raw_input()
        if size >= 0:
            buf = buf[ : size ]
        return buf

    def readline_p( self, size = -1 ):
        """
        Reads a line from this file.

        <b>Note</b>: This method will not block and may return
        only a part of a line if that is all that is available.

        @param size maximum number of bytes to be read (int)
        @return one line of text up to size bytes (string)
        """
        self.__checkMode( 'r' )

        if size < 0:
            size = 20000

        # The integration of the debugger client event loop and the connection
        # to the debugger relies on the two lines of the debugger command being
        # delivered as two separate events.  Therefore we make sure we only
        # read a line at a time.
        line = self.sock.recv( size, socket.MSG_PEEK )

        eol = line.find( '\n' )

        if eol >= 0:
            size = eol + 1
        else:
            size = len( line )

        # Now we know how big the line is, read it for real.
        return self.sock.recv( size ).decode( 'utf8' )

    def readlines( self, sizehint = -1 ):
        """
        Reads all lines from this file.

        @param sizehint hint of the numbers of bytes to be read (int)
        @return list of lines read (list of strings)
        """
        self.__checkMode( 'r' )

        lines = []
        room = sizehint

        line = self.readline_p( room )
        linelen = len( line )

        while linelen > 0:
            lines.append( line )

            if sizehint >= 0:
                room = room - linelen

                if room <= 0:
                    break

            line = self.readline_p( room )
            linelen = len( line )

        return lines

    def readline( self, sizehint = -1 ):
        """
        Reads one line from this file.

        @param sizehint hint of the numbers of bytes to be read (int)
        @return one line read (string)
        """
        self.__checkMode( 'r' )

        line = raw_input() + '\n'
        if sizehint >= 0:
            line = line[ : sizehint ]
        return line

    def seek( self, offset, whence = 0 ):
        """
        Moves the filepointer

        @exception IOError This method is not supported and always raises an
        IOError.
        """
        raise IOError, '[Errno 29] Illegal seek'

    def tell( self ):
        """
        Provides the filepointer position

        @exception IOError This method is not supported and always raises an
        IOError.
        """
        raise IOError, '[Errno 29] Illegal seek'

    def truncate( self, size = -1 ):
        """
        Truncates the file

        @exception IOError This method is not supported and always raises an
        IOError.
        """
        raise IOError, '[Errno 29] Illegal seek'

    def write( self, s ):
        """
        Writes a string to the file

        @param s bytes to be written (string)
        """

        self.__checkMode( 'w' )
        tries = 0
        if not self.wpending:
            self.wpending = s
        elif type( self.wpending ) != type( s ) or \
             len( self.wpending ) + len( s ) > self.maxbuffersize:
            # flush wpending so that different string types
            # are not concatenated
            while self.wpending:
                # if we have a persistent error in sending the data,
                # an exception will be raised in __nWrite
                self.flush()
                tries += 1
                if tries > self.maxtries:
                    raise socket.error( "Too many attempts to send data" )
            self.wpending = s
        else:
            self.wpending += s
        self.__nWrite( self.pendingWrite() )
        return

    def writelines( self, lines ):
        """
        Writes a list of strings to the file.

        @param lines the list to be written (list of string)
        """
        map( self.write, lines )
        return
