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


from distutils.core import setup, Extension

setup( name = 'cdmpyparser',
       version = '0.0.1',
       py_modules  = [ 'cdmbriefparser.py' ],
       ext_modules = [ Extension( '_cdmpyparser',
                                  [ 'cdmpyparser.c',
                                    'lexerutils.c',
                                    'pythonbriefLexer.c',
                                    'pythonbriefParser.c' ],
                                  extra_compile_args = [ '-Wno-unused', '-fomit-frame-pointer',
                                                         '-I../thirdparty/libantlr3c-3.2',
                                                         '-I../thirdparty/libantlr3c-3.2/include',
                                                         '-ffast-math' ],
                                  extra_link_args = [ '../thirdparty/libantlr3c-3.2/.libs/libantlr3c.a' ]
                                ) ] )

