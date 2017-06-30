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
# The file was taken from eric 4/eric 6 and adopted for codimension.
# Original copyright:
# Copyright (c) 2015 - 2016 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Various debug utilities
"""

import json

def prepareJSONMessage(method, params):
    """Prepares a JSON message to be send"""
    msg = json.dumps(
        {'jsonrpc': '2.0',
         'method': method,
         'params': params}) + '\n'
    return msg.encode('utf8', 'backslashreplace')


def parseJSONMessage(jsonStr):
    """Parses a JSON message"""
    cmdDictionary = json.loads(jsonStr.strip())
    return cmdDictionary['method'], cmdDictionary['params']
