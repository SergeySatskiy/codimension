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

"""Interactive errors report using pyflakes"""

import re
from _ast import PyCF_ONLY_AST
from pyflakes.checker import Checker
from radon.complexity import cc_visit_ast, sorted_results


# Returns a dictionary:
# {lineno1: [msg1, msg2, ...],
#  lineno2: [msg3, ...]}


IGNORE_REGEXP = re.compile(r'analysis:\s*(off|disable|ignore)', re.IGNORECASE)


def getBufferErrors(sourceCode):
    """Provides a list of warnings/errors for the given source code"""
    sourceCode += '\n'

    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(sourceCode, "<string>", "exec", PyCF_ONLY_AST)
    except SyntaxError as value:
        # If there's an encoding problem with the file, the text is None.
        if value.text is None:
            return {}, []
        return {value.lineno: [value.args[0]]}, []
    except (ValueError, TypeError) as value:
        # ValueError may happened in case of invalid \x escape character
        # E.g. http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674797
        # TypeError may happened in case of null characters in a file
        # E.g. http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674796
        msg = str(value)
        if msg == "":
            return {-1: ["Could not compile buffer: unknown error"]}, []
        return {-1: ["Could not compile buffer: " + msg]}, []

    # Okay, it's syntactically valid.  Now check it.
    check = Checker(tree, "<string>")
    results = {}
    lines = sourceCode.splitlines()
    for warning in check.messages:
        if isinstance(warning.lineno, int):
            lineno = warning.lineno
        else:
            # By some reasons I see ast NAME node here (pyflakes 0.7.3)
            lineno = warning.lineno.lineno
        if not IGNORE_REGEXP.search(lines[lineno - 1]):
            if lineno in results:
                results[lineno].append(warning.message % warning.message_args)
            else:
                results[lineno] = [warning.message % warning.message_args]

    # Radon: CC complexity as the second value
    return results, sorted_results(cc_visit_ast(tree))
