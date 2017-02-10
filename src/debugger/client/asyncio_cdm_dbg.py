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
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a base class of an asynchronous interface for the debugger
"""


class AsyncIO(object):

    """Class implementing asynchronous reading and writing"""

    def __init__(self):
        # There is no connection yet
        self.disconnect()

    def disconnect(self) :
        """Disconnects any current connection"""
        self.readfd = None
        self.writefd = None

    def setDescriptors(self, rfd, wfd):
        """Sets the descriptors for the connection

        @param rfd file descriptor of the input file (int)
        @param wfd file descriptor of the output file (int)
        """
        self.rbuf = ''
        self.readfd = rfd

        self.wbuf = ''
        self.writefd = wfd

    def readReady(self, fd):
        """Called when there is data ready to be read

        @param fd file descriptor of the file that has data to be read (int)
        """
        try:
            got = self.readfd.readline_p()
        except:
            return

        if not got:
            self.sessionClose()
            return

        self.rbuf = self.rbuf + got

        # Call handleLine for the line if it is complete.
        eol = self.rbuf.find('\n')

        while eol >= 0:
            s = self.rbuf[:eol + 1]
            self.rbuf = self.rbuf[eol + 1:]
            self.handleLine(s)
            eol = self.rbuf.find('\n')

    def writeReady(self, fd):
        """Called when we are ready to write data

        @param fd file descriptor of the file that
                  has data to be written (int)
        """
        self.writefd.write(self.wbuf)
        self.writefd.flush()
        self.wbuf = ''

    def write(self, data):
        """Writes a string

        @param s the data to be written (string)
        """
        self.wbuf = self.wbuf + data
