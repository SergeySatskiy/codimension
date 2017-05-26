#
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
from _ast import PyCF_ONLY_AST
from utils.run import checkOutput


DIS_MODULE_PATH = dis.__file__
PYTHON_INTERPRETER_PATH = sys.executable


def isFileSyntacticallyCorrect(path):
    """True if the file could be compiled"""
    try:
        py_compile.compile(path)
        return True
    except:
        return False

def isBufferSyntacticallyCorrect(content):
    """True if the buffer is syntactically correct"""
    try:
        compile(content, "<string>", "exec", PyCF_ONLY_AST)
        return True
    except:
        return False


def getFileDisassembled(path):
    """Dsassembles a file"""
    if not os.path.exists(path):
        raise Exception("Cannot find " + path + " to disassemble")
    if not os.access(path, os.R_OK):
        raise Exception("No read permissions for " + path)

    cmd = [PYTHON_INTERPRETER_PATH, DIS_MODULE_PATH, path]
    try:
        return checkOutput(cmd)
    except:
        if not isFileSyntacticallyCorrect(path):
            raise Exception("Cannot disassemble "
                            "syntactically incorrect file " + path)
    raise Exception("Could not get " + path + " disassembled")


def getBufferDisassembled(content):
    """Disassembles a memory buffer"""
    os.environ['CDM_DISASM_CONTENT'] = content
    cmd = 'echo $CDM_DISASM_CONTENT | ' + PYTHON_INTERPRETER_PATH
    cmd += ' ' + DIS_MODULE_PATH
    try:
        output = checkOutput(cmd, useShell=True)
        del os.environ['CDM_DISASM_CONTENT']
        return output
    except:
        del os.environ['CDM_DISASM_CONTENT']
        if isBufferSyntacticallyCorrect(content):
            raise Exception("Cannot disassemble "
                            "syntactically incorrect buffer")
    raise Exception("Could not get the buffer disassembled")
