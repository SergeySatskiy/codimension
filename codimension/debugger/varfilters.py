# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Variable filters"""

# A set of functions to filter variables in the debugger.
# Each function should return True if the variable matches the filter.
# The filtration is done on the IDE side.
# Both name and type are strings


def filterLocalVariables(isGlobal, varName, varType):
    """Filters out the local variables"""
    del varName     # unused argument
    del varType     # unused argument
    return not isGlobal


def filterGlobalVariables(isGlobal, varName, varType):
    """Filters out the global variables"""
    del varName     # unused argument
    del varType     # unused argument
    return isGlobal


def filterHiddenAttributes(isGlobal, varName, varType):
    """Filters out the hidden attributes"""
    del isGlobal    # unused argument
    del varType     # unused argument
    return varName.startswith('__') and varName.endswith('__')


def filterTypes(isGlobal, varName, varType):
    """Filters out types"""
    del isGlobal    # unused argument
    del varName     # unused argument
    return varType.lower() == 'type'


def filterClassMethods(isGlobal, varName, varType):
    """Filters out methods"""
    del isGlobal    # unused argument
    del varName     # unused argument
    return varType.lower() == 'class method'


def filterFunctions(isGlobal, varName, varType):
    """Filters out functions"""
    del isGlobal    # unused argument
    del varName     # unused argument
    return varType.lower() == 'function'


def filterBuiltinFunctions(isGlobal, varName, varType):
    """Filters out builtin functions"""
    del isGlobal    # unused argument
    del varName     # unused argument
    return varType.lower() in ['method-wrapper', 'builtin function']


def filterModules(isGlobal, varName, varType):
    """Filters out modules"""
    del isGlobal    # unused argument
    del varName     # unused argument
    return varType.lower() == 'module'


def filterNones(isGlobal, varName, varType):
    """Filters out None-type variables"""
    del isGlobal    # unused argument
    del varName     # unused argument
    return varType.lower() == 'none'



VARIABLE_FILTERS = [
    ['Local Variables', 'dbgfltlocal', filterLocalVariables],
    ['Global Variables', 'dbgfltglobal', filterGlobalVariables],
    ['Hidden Attributes', 'dbgflthidden', filterHiddenAttributes],
    ['Types', 'dbgflttype', filterTypes],
    ['Class Methods', 'dbgfltmethod', filterClassMethods],
    ['Functions', 'dbgfltfunc', filterFunctions],
    ['Builtin Functions', 'dbgfltbuiltin', filterBuiltinFunctions],
    ['Modules', 'dbgfltmodule', filterModules],
    ['No Types', 'dbgfltnotype', filterNones]]
