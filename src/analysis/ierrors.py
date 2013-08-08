#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Interactive errors report using pyflakes "

from _ast import PyCF_ONLY_AST
from thirdparty.pyflakes.checker import Checker


def getFileErrors( sourceCode ):
    " Provides a list of warnings/errors for the given source code "

    sourceCode += '\n'

    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile( sourceCode, "<string>", "exec", PyCF_ONLY_AST )
    except SyntaxError, value:
        # If there's an encoding problem with the file, the text is None.
        if value.text is None:
            return []
        return [ ( value.args[0], value.lineno ) ]
    except ( ValueError, TypeError ):
        # May happened in case of invalid \x escape character
        # E.g. http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674797
        # May happened in case of null characters in a file
        # E.g. http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674796
        return []

    # Okay, it's syntactically valid.  Now check it.
    w = Checker( tree, "<string>" )
    results = []
    lines = sourceCode.splitlines()
    for warning in w.messages:
        if type( warning.lineno ) == int:
            lineno = warning.lineno
        else:
            # By some reasons I see ast NAME node here (pyflakes 0.7.3)
            lineno = warning.lineno.lineno
        if 'analysis:ignore' not in lines[ lineno - 1 ]:
            results.append( ( warning.message % warning.message_args,
                              lineno ) )
    results.sort( key = lambda x: x[ 1 ] )
    return results
