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

"""Process related utility functions"""

import os
import errno
import time
from signal import SIGTERM, SIGINT, SIGHUP, SIGKILL


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
