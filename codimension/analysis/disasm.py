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


# The objects which have already been disassembled
DIS_OBJECTS = set()

DIS_PATTERN = 'Disassembly of <code object '
DIS_PATTERN_LEN = len(DIS_PATTERN)
def updateDisassembledNames(disassembly):
    for line in disassembly.splitlines():
        if line.startswith(DIS_PATTERN):
            name = line[DIS_PATTERN_LEN:].split()[0]
            DIS_OBJECTS.add(name)


def recursiveDisassembly(codeObject, name=None):
    """Disassemble recursively"""
    if name is None:
        what = 'module'
    else:
        if name in DIS_OBJECTS:
            return ''
        what = name

    disassembly = getCodeDisassembly(codeObject)
    updateDisassembledNames(disassembly)

    res = '\n\nDisassembly of ' + what + ':\n' + disassembly
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
    props = [('Python version', platform.python_version()),
             ('Python interpreter path', sys.executable)]

    pycFile = open(pycPath, 'rb')

    magic = pycFile.read(4)
    timestamp = pycFile.read(4)

    if sys.version_info.major == 3 and sys.version_info.minor >= 3:
        size = pycFile.read(4)
        size = struct.unpack('I', size)[0]
        # Strange: the size is decoded as abnormally large and I don't
        # know why. So suppress it.
        # props.append(('Code size', str(size)))

    if sys.version_info.major == 3 and sys.version_info.minor >= 7:
        flags = pycFile.read(4)
        flags = struct.unpack('I', flags)[0]
        # The flags do not seem to be of a much interest
        # Suppress them
        # props.append(('Flags', hex(flags)))

    code = marshal.load(pycFile)
    magic = binascii.hexlify(magic).decode('utf-8')
    timestamp = time.asctime(
        time.localtime(struct.unpack('I', timestamp)[0]))

    # In terpreter magic is not really interesting because the version
    # and path are already provided. So suppress them
    # props.append(('Interpreter magic', magic))
    # props.append(('Interpreter timestamp', timestamp))

    bufferSpec = ''
    if forBuffer:
        bufferSpec = ' (unsaved buffer)'
    props.append(('Python module', pyPath + bufferSpec))
    props.append(('Optimization', optToString(optimization)))

    DIS_OBJECTS.clear()
    disassembly = recursiveDisassembly(code)
    DIS_OBJECTS.clear()

    return props, disassembly


def _stringify(props, disassembly):
    """Combines the properties and disassembly into one string"""
    result = '-' * 80
    for item in props:
        result += '\n' + item[0] + ': ' + item[1]
    result += '\n' + '-' * 80
    result += disassembly
    return result


def _getFileDisassembled(path, optimization):
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
        props, disassembly = getCompiledfileDisassembled(tempPycFile, path,
                                                         optimization)
    except:
        safeUnlink(tempPycFile)
        raise

    safeUnlink(tempPycFile)
    return props, disassembly


def getFileDisassembled(path, optimization, stringify=True):
    """Dsassembles a file"""
    props, disassembly = _getFileDisassembled(path, optimization)
    if stringify:
        return _stringify(props, disassembly)
    return props, disassembly


def _getBufferDisassembled(content, encoding, path, optimization):
    """Disassembles a memory buffer"""
    tempSrcFile = makeTempFile(suffix='.py')
    tempPycFile = makeTempFile(suffix='.pyc')

    try:
        saveToFile(tempSrcFile, content, allowException=True, enc=encoding)
        py_compile.compile(tempSrcFile, tempPycFile, path,
                           doraise=True, optimize=optimization)
    except Exception:
        safeUnlink(tempSrcFile)
        safeUnlink(tempPycFile)
        raise

    try:
        props, disassembly = getCompiledfileDisassembled(tempPycFile, path,
                                                         optimization, True)
    except:
        safeUnlink(tempSrcFile)
        safeUnlink(tempPycFile)
        raise

    safeUnlink(tempSrcFile)
    safeUnlink(tempPycFile)
    if path:
        return props, disassembly.replace('file "' + path + '",',
                                          'unsaved buffer "' + path + '",')
    return props, disassembly


def getBufferDisassembled(content, encoding, path, optimization, stringify=True):
    """Disassembles a memory buffer"""
    props, disassembly = _getBufferDisassembled(content, encoding,
                                                path, optimization)
    if stringify:
        return _stringify(props, disassembly)
    return props, disassembly



def getCompiledfileBinary(pycPath, pyPath, optimization, forBuffer=False):
    """Reads the .pyc file and provides the plain text disassembly"""
    props = [('Python version', platform.python_version()),
             ('Python interpreter path', sys.executable)]

    pycFile = open(pycPath, 'rb')
    content = pycFile.read()
    shift = 0

    magic = content[shift:shift + 4]
    shift += 4
    timestamp = content[shift:shift + 4]
    shift += 4

    if sys.version_info.major == 3 and sys.version_info.minor >= 3:
        size = content[shift:shift + 4]
        shift += 4
        size = struct.unpack('I', size)[0]
        # Strange: the size is decoded as abnormally large and I don't
        # know why. So suppress it.
        # props.append(('Code size', str(size)))

    if sys.version_info.major == 3 and sys.version_info.minor >= 7:
        flags = content[shift:shift + 4]
        shift += 4
        flags = struct.unpack('I', flags)[0]
        # The flags do not seem to be of a much interest
        # Suppress them
        # props.append(('Flags', hex(flags)))

    magic = binascii.hexlify(magic).decode('utf-8')
    timestamp = time.asctime(
        time.localtime(struct.unpack('I', timestamp)[0]))

    # Interpreter magic is not really interesting because the version
    # and path are already provided. So suppress them
    # props.append(('Interpreter magic', magic))
    # props.append(('Interpreter timestamp', timestamp))

    bufferSpec = ''
    if forBuffer:
        bufferSpec = ' (unsaved buffer)'
    props.append(('Python module', pyPath + bufferSpec))
    props.append(('Optimization', optToString(optimization)))

    return props, content


def getFileBinary(path, optimization):
    """Provides the binary pyc content"""
    if not os.path.exists(path):
        raise Exception("Cannot find " + path + " to provide binary")
    if not os.access(path, os.R_OK):
        raise Exception("No read permissions for " + path)

    tempPycFile = makeTempFile(suffix='.pyc')
    try:
        py_compile.compile(path, tempPycFile,
                           doraise=True, optimize=optimization)
    except Exception as exc:
        safeUnlink(tempPycFile)
        raise Exception("Cannot provide binary for file " +
                        path + ': ' + str(exc))

    try:
        props, content = getCompiledfileBinary(tempPycFile, path, optimization)
    except:
        safeUnlink(tempPycFile)
        raise

    safeUnlink(tempPycFile)
    return props, content



def getBufferBinary(content, encoding, path, optimization):
    """Provides the binary pyc content"""
    tempSrcFile = makeTempFile(suffix='.py')
    tempPycFile = makeTempFile(suffix='.pyc')

    try:
        saveToFile(tempSrcFile, content, allowException=True, enc=encoding)
        py_compile.compile(tempSrcFile, tempPycFile, path,
                           doraise=True, optimize=optimization)
    except Exception:
        safeUnlink(tempSrcFile)
        safeUnlink(tempPycFile)
        raise

    try:
        props, content = getCompiledfileBinary(tempPycFile, path,
                                               optimization, True)
    except:
        safeUnlink(tempSrcFile)
        safeUnlink(tempPycFile)
        raise

    safeUnlink(tempSrcFile)
    safeUnlink(tempPycFile)
    return props, content

