#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Sends a short message to the specified port.

Usually used to signal that a program has finished
"""

import socket
import sys
import os
from os.path import basename
import errno
import time
from signal import SIGTERM, SIGINT, SIGHUP, SIGKILL

FEEDBACK_PREFIX = "cdmfeedback"


def sendFeedbackMessage(localPort, parts):
    """Sends the 'done <exit code>' message to localhost:port"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = ' '.join([FEEDBACK_PREFIX] + parts)
    sock.sendto(msg.encode('utf-8'), ('127.0.0.1', localPort))


def decodeMessage(msg):
    """Validates the message and extract parts from it"""
    parts = msg.decode('utf-8').split()
    if len(parts) < 1:
        raise Exception("Invalid message length - no prefix")
    if parts[0] != FEEDBACK_PREFIX:
        raise Exception("Invalid message prefix")
    return parts[1:]


def isProcessAlive(pid):
    """Returns True is the process is still alive"""
    try:
        # Signal 0 means no sending a signal but check preconditions
        os.kill(pid, 0)
    except OSError as excpt:
        if excpt.errno == errno.ESRCH:
            return False
        if excpt.errno == errno.EPERM:
            return True
        raise
    return True


def killProcess(pid):
    """Tries to kill the given process"""
    for signal in (SIGTERM, SIGINT, SIGHUP):
        if not isProcessAlive(pid):
            return

        try:
            os.kill(pid, signal)
        except OSError as excpt:
            if excpt.errno == errno.ESRCH:
                return  # Already dead
            raise
        time.sleep(0.5)

    # Could not kill gracefully, try harder
    startTime = time.time()
    while True:
        if not isProcessAlive(pid):
            return

        if time.time() - startTime >= 15:
            raise Exception("Cannot kill process (pid: " + str(pid) + ")")

        try:
            os.kill(pid, SIGKILL)
        except OSError as excpt:
            if excpt.errno == errno.ESRCH:
                return  # Already dead
            raise
        time.sleep(0.1)
    return


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Incorrect number of arguments", file=sys.stderr)
        print("Usage: " + basename(sys.argv[0]) + " <port> [...]",
              file=sys.stderr)
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except:
        print("Cannot get port number", file=sys.stderr)
        sys.exit(2)

    try:
        sendFeedbackMessage(port, sys.argv[2:])
    except Exception as exc:
        print("Cannot send feedback message: " + str(exc), file=sys.stderr)
        sys.exit(3)

    sys.exit(0)
