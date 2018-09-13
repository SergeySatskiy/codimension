# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4/eric 6 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2016 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Implementation of an asynchronous file like socket interface for the debugger
"""

import socket
from cdm_dbg_utils import prepareJSONMessage
from protocol_cdm_dbg import METHOD_CLIENT_OUTPUT


class AsyncFile(object):

    """Wrapps a socket object with a file interface"""

    MAXTRIES = 10

    def __init__(self, sock, mode, name):
        self.closed = False
        self.sock = sock
        self.mode = mode
        self.name = name
        self.nWriteErrors = 0
        self.encoding = 'utf-8'
        self.errors = None
        self.newlines = None
        self.line_buffering = False

        self.wpending = []

    def __checkMode(self, mode):
        """Checks the mode"""
        if mode != self.mode:
            raise IOError((9, '[Errno 9] Bad file descriptor'))

    def pendingWrite(self):
        """Returns the number of strings waiting to be written"""
        return len(self.wpending)

    def close(self, closeit=False):
        """Closes the file"""
        if closeit and not self.closed:
            self.sock.close()
            self.closed = True

    def flush(self):
        """Writes all pending entries"""
        while self.wpending:
            try:
                buf = self.wpending.pop(0)
            except IndexError:
                break

            try:
                try:
                    buf = buf.encode('utf-8', 'backslashreplace')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
                self.sock.sendall(buf)
                self.nWriteErrors = 0
            except socket.error:
                self.nWriteErrors += 1
                if self.nWriteErrors > self.MAXTRIES:
                    self.wpending = []    # delete all output

    def isatty(self):
        """Indicates whether a tty interface is supported"""
        return False

    def fileno(self):
        """Provides the file number"""
        try:
            return self.sock.socketDescriptor()
        except Exception as exc:
            return -1

    def readable(self):
        """Checks if the stream is readable"""
        return self.mode == 'r'

    def read_p(self, size=-1):
        """Reads bytes from this file"""
        self.__checkMode('r')
        if size < 0:
            size = 20000
        return self.sock.recv(size).decode('utf8', 'backslashreplace')

    def read(self, size=-1):
        """Reads bytes from this file"""
        self.__checkMode('r')
        buf = input()
        if size >= 0:
            buf = buf[:size]
        return buf

    def readline_p(self, size=-1):
        """Reads a line from this file"""
        self.__checkMode('r')
        if size < 0:
            size = 20000

        # The integration of the debugger client event loop and the connection
        # to the debugger relies on the two lines of the debugger command being
        # delivered as two separate events. Therefore we make sure we only
        # read a line at a time.
        line = self.sock.recv(size, socket.MSG_PEEK)
        eol = line.find(b'\n')

        if eol >= 0:
            size = eol + 1
        else:
            size = len(line)

        # Now we know how big the line is, read it for real.
        return self.sock.recv(size).decode('utf8', 'backslashreplace')

    def readlines(self, sizehint=-1):
        """Reads all lines from this file"""
        self.__checkMode('r')

        lines = []
        room = sizehint

        line = self.readline_p(room)
        linelen = len(line)

        while linelen > 0:
            lines.append(line)

            if sizehint >= 0:
                room = room - linelen

                if room <= 0:
                    break

            line = self.readline_p(room)
            linelen = len(line)

        return lines

    def readline(self, sizehint=-1):
        """Reads one line from this file"""
        self.__checkMode('r')
        line = input() + '\n'
        if sizehint >= 0:
            line = line[:sizehint]
        return line

    def seekable(self):
        """Checks if the stream is seekable"""
        return False

    def seek(self, offset, whence=0):
        """Moves the filepointer"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def tell(self):
        """Provides the filepointer position"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def truncate(self, size=-1):
        """Truncates the file"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def writable(self):
        """Check if a stream is writable"""
        return self.mode == 'w'

    def write(self, s):
        """Writes a string to the file"""
        self.__checkMode('w')
        cmd = prepareJsonMessage(
            METHOD_CLIENT_OUTPUT, {"text": s})
        self.wpending.append(cmd)
        self.flush()

    def write_p(self, s):
        """Writes a json-rpc 2.0 coded string to the file"""
        self.__checkMode('w')
        self.wpending.append(s)
        self.flush()

    def writelines(self, lines):
        """Writes a list of strings to the file"""
        self.write("".join(lines))
