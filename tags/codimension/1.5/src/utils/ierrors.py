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

import sys, compiler


def getFileErrors( sourceCode ):
    " Checks the given buffer and returns a list of errors "

    try:
        tree = compiler.parse( sourceCode + "\n" )
    except (SyntaxError, IndentationError), excpt:
        message = excpt.args[ 0 ]
        value = sys.exc_info()[ 1 ]
        try:
            lineno, _offset, _text = value[ 1 ][ 1: ]
        except IndexError:
            # Compilation error
            return []
        return [ [ message, lineno, True ] ]
    except:
        return []

    try:
        import pyflakes.checker, pyflakes.messages
    except:
        return []

    # Pyflakes was imported successfully
    result = []
    warnings = pyflakes.checker.Checker( tree, "" )
    warnings.messages.sort( lambda a, b: cmp( a.lineno, b.lineno ) )

    errorMessages = ( pyflakes.messages.UndefinedName,
                      pyflakes.messages.UndefinedExport,
                      pyflakes.messages.UndefinedLocal,
                      pyflakes.messages.DuplicateArgument,
                      pyflakes.messages.LateFutureImport )
    lines = sourceCode.splitlines()
    for warning in warnings.messages:
        if 'pyflakes:ignore' not in lines[ warning.lineno - 1 ]:
            result.append( ( warning.message % warning.message_args,
                             warning.lineno,
                             isinstance( warning, errorMessages ) ) )
    return result

