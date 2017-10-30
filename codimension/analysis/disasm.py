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

"""Disassembling files and buffers"""

import sys
import dis
import os
import os.path
import py_compile
import marshal
import platform
import binascii
import struct
import time
from types import CodeType
from io import StringIO
from utils.fileutils import makeTempFile, saveToFile


OPT_NO_OPTIMIZATION = 0
OPT_OPTIMIZE_ASSERT = 1
OPT_OPTIMIZE_DOCSTRINGS = 2

_CONVERSION = {OPT_NO_OPTIMIZATION: 'no optimization',
               OPT_OPTIMIZE_ASSERT: 'assert optimization',
               OPT_OPTIMIZE_DOCSTRINGS: 'assert + docstring optimization'}

def optToString(optimization):
    """Converts optimization into a string"""
    try:
        return _CONVERSION[optimization]
    except KeyError:
        return 'unknown optimization'


def safeUnlink(path):
    """No exception unlink"""
    try:
        os.unlink(path)
    except:
        pass


def getCodeDisassembly(code):
    """Provides disassembly of a code object"""
    fileLikeObject = StringIO()
    dis.dis(code, file=fileLikeObject)
    fileLikeObject.seek(0)
    return fileLikeObject.read()


def recursiveDisassembly(codeObject, name=None):
    what = 'module' if name is None else name
    res = '\n\nDisassembly of ' + what + ':\n' + getCodeDisassembly(codeObject)
    for item in codeObject.co_consts:
        if type(item) == CodeType:
            itemName = item.co_name
            if name:
                itemName = name + '.' + itemName
            res += recursiveDisassembly(item, itemName)
    return res


# The idea is taken from here:
# https://stackoverflow.com/questions/11141387/given-a-python-pyc-file-is-there-a-tool-that-let-me-view-the-bytecode
# https://stackoverflow.com/questions/32562163/how-can-i-understand-a-pyc-file-content
def getCompiledfileDisassembled(pycPath, pyPath, optimization,
                                forBuffer=False):
    """Reads the .pyc file and provides the plain text disassembly"""
    pycFile = open(pycPath, 'rb')

    magic = pycFile.read(4)
    timestamp = pycFile.read(4)

    size = None
    if sys.version_info.major == 3 and sys.version_info.minor >= 3:
        size = pycFile.read(4)
        size = struct.unpack('I', size)[0]

    code = marshal.load(pycFile)
    magic = binascii.hexlify(magic).decode('utf-8')
    timestamp = time.asctime(
        time.localtime(struct.unpack('I', b'D\xa5\xc2X')[0]))

    bufferSpec = ''
    if forBuffer:
        bufferSpec = ' (unsaved buffer)'
    return '\n'.join(
        ['-' * 80,
         'Python version: ' + platform.python_version(),
         'Python interpreter path: ' + sys.executable,
         'Interpreter magic: ' + magic,
         'Interpreter timestamp: ' + timestamp,
         'Python module: ' + pyPath + bufferSpec,
         'Optimization: ' + optToString(optimization),
         'Code size: ' + str(size),
         '-' * 80,
         recursiveDisassembly(code)])


def getFileDisassembled(path, optimization):
    """Dsassembles a file"""
    if not os.path.exists(path):
        raise Exception("Cannot find " + path + " to disassemble")
    if not os.access(path, os.R_OK):
        raise Exception("No read permissions for " + path)

    tempPycFile = makeTempFile(suffix='.pyc')
    try:
        py_compile.compile(path, tempPycFile,
                           doraise=True, optimize=optimization)
    except Exception as exc:
        safeUnlink(tempPycFile)
        raise Exception("Cannot disassemble file " + path + ': ' + str(exc))

    try:
        result = getCompiledfileDisassembled(tempPycFile, path, optimization)
    except:
        safeUnlink(tempPycFile)
        raise

    safeUnlink(tempPycFile)
    return result


def getBufferDisassembled(content, encoding, path, optimization):
    """Disassembles a memory buffer"""
    tempSrcFile = makeTempFile(suffix='.py')
    tempPycFile = makeTempFile(suffix='.pyc')

    try:
        saveToFile(tempSrcFile, content, allowException=True, enc=encoding)
        py_compile.compile(tempSrcFile, tempPycFile, path,
                           doraise=True, optimize=optimization)
    except Exception as exc:
        safeUnlink(tempSrcFile)
        safeUnlink(tempPycFile)
        raise

    try:
        result = getCompiledfileDisassembled(tempPycFile, path,
                                             optimization, True)
    except:
        safeUnlink(tempSrcFile)
        safeUnlink(tempPycFile)
        raise

    safeUnlink(tempSrcFile)
    safeUnlink(tempPycFile)
    if path:
        return result.replace('file "' + path + '",',
                              'unsaved buffer "' + path + '",')
    return result
