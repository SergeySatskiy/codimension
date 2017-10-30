# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# The file was taken from eric 6 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2017 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing the multithreaded version of the debug client
"""

import sys
import traceback
import time
from base_cdm_dbg import DebugBase
from clientbase_cdm_dbg import DebugClientBase
from threadextension_cdm_dbg import ThreadExtension


CLIENT_DEBUG = True


class DebugClient(DebugClientBase, DebugBase, ThreadExtension):

    """
    Class implementing the client side of the debugger
    """

    def __init__(self):
        DebugClientBase.__init__(self)
        DebugBase.__init__(self, self)
        ThreadExtension.__init__(self)


# We are normally called by the debugger to execute directly.

if __name__ == '__main__':
    debugClient = DebugClient()
    try:
        debugClient.main()
    except Exception as exc:
        if CLIENT_DEBUG:
            print(traceback.format_exc(), file=sys.__stderr__)
            if sys.__stderr__ != sys.stderr:
                print(traceback.format_exc(), file=sys.stderr)
            # The delay is for a socket data
            time.sleep(4)
