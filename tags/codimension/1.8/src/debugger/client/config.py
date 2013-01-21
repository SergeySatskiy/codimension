#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#



"""
Module defining type strings for the different Python types.
"""

ConfigVarTypeStrings = [ '__', 'NoneType', 'type',
        'bool', 'int', 'long', 'float', 'complex',
        'str', 'unicode', 'tuple', 'list',
        'dict', 'dict-proxy', 'set', 'file', 'xrange',
        'slice', 'buffer', 'class', 'instance',
        'instance method', 'property', 'generator',
        'function', 'builtin_function_or_method', 'code', 'module',
        'ellipsis', 'traceback', 'frame', 'other' ]
