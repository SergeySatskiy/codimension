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
import sys
from collections import namedtuple
from inspect import iscode, isframe
from dis import COMPILER_FLAG_NAMES
from PyQt5.QtNetwork import QAbstractSocket


MAX_TRIES = 3


# Create constants for the compiler flags in Include/code.h
mod_dict = globals()
for flagName, value in COMPILER_FLAG_NAMES.items():
    mod_dict['CO_' + value] = flagName

ArgInfo = namedtuple('ArgInfo', 'args varargs keywords locals')


def printerr(s):
    """debugging the debug client printout"""
    sys.__stderr__.write('{0!s}\n'.format(s))
    sys.__stderr__.flush()


def prepareJSONMessage(method, procuuid, params):
    """Prepares a JSON message to be send"""
    msg = json.dumps(
        {'jsonrpc': '2.0',
         'method': method,
         'procuuid': procuuid,
         'params': params}) + '\n'
    return msg.encode('utf8', 'backslashreplace')


def parseJSONMessage(jsonStr):
    """Parses a JSON message"""
    cmdDictionary = json.loads(jsonStr.strip())
    return cmdDictionary['method'], cmdDictionary['procuuid'], \
        cmdDictionary['params']


def sendJSONCommand(clientSocket, method, procuuid, params):
    """Prepares a message and sends it"""
    cmd = prepareJSONMessage(method, procuuid, params)
    if not clientSocket:
        raise Exception('Cannot send a command to a counterpart: '
                        'no connection established. Command: ' + str(cmd))

    lastSocketError = None
    tries = MAX_TRIES
    while tries > 0:
        try:
            clientSocket.write(cmd)
            clientSocket.flush()
            return
        except Exception as exc:
            tries -= 1
            lastSocketError = str(exc)
            continue
    msg = 'Too many attempts to send data'
    if lastSocketError:
        msg += ': ' + lastSocketError
    raise Exception(msg)


def waitForIDEMessage(clientSocket, msgType, timeout):
    """Waits for a certain message from the IDE"""
    if clientSocket.waitForReadyRead(timeout * 1000):
        jsonStr = bytes(clientSocket.readLine()).decode()
        try:
            method, _, params = parseJSONMessage(jsonStr)
            if method != msgType:
                raise Exception('Unexpected message from IDE. Expected: ' +
                                msgType + '. Received: ' + str(method))
            return params
        except (TypeError, ValueError) as exc:
            raise Exception('Error parsing IDE message: ' + str(exc))

    if clientSocket.state() != QAbstractSocket.ConnectedState:
        # the socket has disconnected which most probably means
        # the IDE crashed
        sys.exit(1)

    raise Exception('Timeout waiting an IDE message ' + msgType)


def getParsedJSONMessage(clientSocket):
    """Provides a parsed message"""
    jsonStr = bytes(clientSocket.readLine()).decode('utf-8')
    try:
        method, procuuid, params = parseJSONMessage(jsonStr)
        return method, procuuid, params, jsonStr
    except Exception as exc:
        raise Exception('Error parsing JSON message: ' + str(exc) +
                        '\nIncoming message: ' + str(jsonStr))


def getArgValues(frame):
    """Provides information about arguments passed into a particular frame"""
    if not isframe(frame):
        raise TypeError('{0!r} is not a frame object'.format(frame))

    args, varargs, kwonlyargs, varkw = _getfullargs(frame.f_code)
    return ArgInfo(args + kwonlyargs, varargs, varkw, frame.f_locals)


def _getfullargs(co):
    """Provides information about the arguments accepted by a code object"""
    if not iscode(co):
        raise TypeError('{0!r} is not a code object'.format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])
    kwonlyargs = list(names[nargs:nargs + nkwargs])

    nargs += nkwargs
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return args, varargs, kwonlyargs, varkw


def formatArgValues(args, varargs, varkw, localsDict,
                    formatarg=str,
                    formatvarargs=lambda name: '*' + name,
                    formatvarkw=lambda name: '**' + name,
                    formatvalue=lambda value: '=' + repr(value)):
    """Formats an argument spec from the 4 values returned by getArgValues"""
    specs = []
    for i in range(len(args)):
        name = args[i]
        specs.append(formatarg(name) + formatvalue(localsDict[name]))
    if varargs:
        specs.append(formatvarargs(varargs) + formatvalue(localsDict[varargs]))
    if varkw:
        specs.append(formatvarkw(varkw) + formatvalue(localsDict[varkw]))
    argvalues = '(' + ', '.join(specs) + ')'
    if '__return__' in localsDict:
        argvalues += " -> " + formatvalue(localsDict['__return__'])
    return argvalues
