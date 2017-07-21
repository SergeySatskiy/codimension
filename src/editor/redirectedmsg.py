# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Redirected IO console messages implementation"""

from datetime import datetime
from utils.settings import Settings


def printableTimestamp(tstamp):
    """Provides a printable timestamp"""
    millisecond = str(int(round(tstamp.microsecond / 1000.0)))
    while len(millisecond) != 3:
        millisecond = "0" + millisecond
    return tstamp.strftime("%H:%M:%S.") + millisecond


def getNowTimestamp():
    """Provides the now() timestamp as a string"""
    return printableTimestamp(datetime.now())


class IOConsoleMsg():

    """Holds a single message"""

    __slots__ = ["msgType", "msgText", "timestamp"]

    IDE_MESSAGE = 0
    STDOUT_MESSAGE = 1
    STDERR_MESSAGE = 2
    STDIN_MESSAGE = 3

    def __init__(self, msgType, msgText):
        self.msgType = msgType
        self.msgText = msgText
        self.timestamp = datetime.now()

    def getTimestamp(self):
        """Provides the timestamp as a string"""
        return printableTimestamp(self.timestamp)


class IOConsoleMessages:

    """Holds a list of messages"""

    def __init__(self):
        self.msgs = []
        self.size = 0

    def append(self, msg):
        """Appends the message to the list. Returns True if it was trimmed"""
        self.msgs.append(msg)
        self.size += 1

        if self.size <= Settings()['ioconsolemaxmsgs']:
            return False

        removeCount = Settings()['ioconsoledelchunk']
        self.msgs = self.msgs[removeCount:]
        self.size -= removeCount
        return True

    def clear(self):
        """Clears all the messages"""
        self.msgs = []
        self.size = 0

    def renderWithTimestamps(self):
        """Provides the 'copy with timestamps' content"""
        buf = []
        outputIndex = -1

        streamPlaceholder = "   "
        timestampPlaceholder = " " * 12
        emptyPrefix = streamPlaceholder + " " + timestampPlaceholder

        for msg in self.msgs:
            if msg.msgType == IOConsoleMsg.IDE_MESSAGE:
                txt = msg.msgText.strip()
                parts = txt.splitlines()
                if parts:
                    buf.append("ide " + msg.getTimestamp() + " " + parts[0])
                    for part in parts[1:]:
                        buf.append(emptyPrefix + " " + part)
                outputIndex = -1
                continue

            if msg.msgType not in [IOConsoleMsg.STDOUT_MESSAGE,
                                   IOConsoleMsg.STDERR_MESSAGE,
                                   IOConsoleMsg.STDIN_MESSAGE]:
                raise Exception("Unexpected message IO console type: " +
                                str(msg.msgType))

            if msg.msgType == IOConsoleMsg.STDOUT_MESSAGE:
                stream = "out"
            elif msg.msgType == IOConsoleMsg.STDERR_MESSAGE:
                stream = "err"
            else:
                stream = " in"

            parts = msg.msgText.splitlines()
            if parts:
                if outputIndex == -1:
                    buf.append(stream + " " + msg.getTimestamp() +
                               " " + parts[0])
                    outputIndex = len(buf) - 1
                else:
                    spaces = len(buf[outputIndex]) - len(emptyPrefix) - 1
                    buf[outputIndex] += parts[0]
                    buf.append(stream + " " + msg.getTimestamp() +
                               " " + " " * spaces + "^")

                parts = parts[1:]
                if parts:
                    for part in parts:
                        buf.append(stream + " " + msg.getTimestamp() +
                                   " " + part)
                    outputIndex = len(buf) - 1

            if msg.msgText.endswith('\n') or msg.msgText.endswith('\r'):
                outputIndex = -1

        return "\n".join(buf)
