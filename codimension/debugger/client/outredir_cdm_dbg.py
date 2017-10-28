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

"""Redirectors for stdout/stderr streams"""

# pylint: disable=no-self-use, unused-argument

from protocol_cdm_dbg import METHOD_STDOUT, METHOD_STDERR
from cdm_dbg_utils import sendJSONCommand


class OutStreamRedirector():

    """Wraps a socket object with a file interface"""

    def __init__(self, sock, isStdout, procid):
        self.closed = False
        self.sock = sock
        self.isStdout = isStdout
        self.procid = procid

    def close(self, closeit=False):
        """Closes the file. closeit != 0 => debugger requested it"""
        if closeit and not self.closed:
            self.sock.close()
            self.closed = True

    def flush(self):
        """Does nothing because there is no buffering"""
        pass

    def isatty(self):
        """Indicates whether a tty interface is supported"""
        return False

    def fileno(self):
        """Provides the file number"""
        try:
            return self.sock.socketDescriptor()
        except Exception as exc:
            return -1

    def read_p(self, size=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def read(self, size=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def readline_p(self, size=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def readlines(self, sizehint=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def readline(self, sizehint=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def seekable(self):
        """Checks if the stream is seekable"""
        return False

    def seek(self, offset, whence=0):
        """Seek is not supported"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def tell(self):
        """Tell is not supported"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def truncate(self, size=-1):
        """Truncates is not supported"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def write(self, data):
        """Writes a string to the file"""
        method = METHOD_STDERR
        if self.isStdout:
            method = METHOD_STDOUT
        sendJSONCommand(self.sock, method, self.procid, {'text': data})

    def writelines(self, lines):
        """Writes a list of strings to the file"""
        self.write(''.join(lines))


# The OutStreamCollector is used in case of the Exec() request.
# The Exec() supposes that there could be both stdout and stderr
# printouts. They need to be collected as a combined output and sent back to
# the IDE. So an instance of the OutStreamCollector is used to temporary
# substitute the sys.stdout and sys.stderr.
class OutStreamCollector():

    """Collects output with a file interface"""

    def __init__(self):
        self.buf = ""

    def close(self):
        """Closes the file"""
        pass

    def flush(self):
        """Does nothing because there is no buffering"""
        pass

    def isatty(self):
        """Indicates whether a tty interface is supported"""
        return False

    def fileno(self):
        """Provides the file number"""
        return -1

    def readable(self):
        """Checks if the stream is readable"""
        return False

    def read_p(self, size=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def read(self, size=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def readline_p(self, size=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def readlines(self, sizehint=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def readline(self, sizehint=-1):
        """Read is not supported"""
        raise IOError((9, '[Errno 9] Bad file descriptor'))

    def seekable(self):
        """Checks if the stream is seekable"""
        return False

    def seek(self, offset, whence=0):
        """Seek is not supported"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def tell(self):
        """Tell is not supported"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def truncate(self, size=-1):
        """Truncates is not supported"""
        raise IOError((29, '[Errno 29] Illegal seek'))

    def writable(self):
        """Check if a stream is writable"""
        return True

    def write(self, data):
        """Writes a string to the file"""
        self.buf += data

    def writelines(self, lines):
        """Writes a list of strings to the file"""
        self.write(''.join(lines))
