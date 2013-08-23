#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id: tidysettings.py 620 2012-06-08 03:11:30Z sergey.satskiy@gmail.com $
#

" PythonTidy tunable parameters "

from utils.settings import Settings

# The list of tuples: (name, description, type, default value)
# Supported types: int
#                  string
#                  bool

TIDY_SETTINGS = { \
    'COL_LIMIT' :
    ( 'Width of output lines in characters',
      'int', Settings().editorEdge ),
      'ASSIGNMENT' :
    ( 'How the assignment operator should appear',
      'string', ' = ' ),
      'FUNCTION_PARAM_ASSIGNMENT' :
    ( 'How function-parameter assignment should appear',
      'string', '=' ),
      'DICT_COLON' :
    ( 'This separates dictionary keys from values',
      'string', ': ' ),
      'SLICE_COLON' :
    ( 'This separates the start:end indices of slices',
      'string', ':' ),
      'COMMENT_PREFIX' :
    ( 'This is the sentinel that marks the beginning of a commentary string',
      'string', '# ' ),
      'SHEBANG' :
    ( 'One line comment naming the Python interpreter to Unix shells',
      'string', '#!/usr/bin/python' ),
      'CODING' :
    ( 'The output character encoding (codec)',
      'string', 'utf-8' ),
      'CODING_SPEC' :
    ( 'Source file encoding comment',
      'string', '# -*- coding: utf-8 -*-' ),
      'BOILERPLATE' :
    ( 'Standard code block inserted after the module doc string on output',
      'string', '' ),
      'BLANK_LINE' :
    ( 'How a blank line should appear (up to the newline character)',
      'string', '' ),
      'KEEP_BLANK_LINES' :
    ( 'Preserve one blank where blank(s) are encountered',
      'bool', True ),
      'ADD_BLANK_LINES_AROUND_COMMENTS' :
    ( 'Set off comment blocks with blanks',
      'bool', True ),
      'MAX_SEPS_FUNC_DEF' :
    ( 'Split lines containing longer function definitions',
      'int', 3 ),
      'MAX_SEPS_FUNC_REF' :
    ( 'Split lines containing longer function calls',
      'int', 5 ),
      'MAX_SEPS_SERIES' :
    ( 'Split lines containing longer lists or tuples',
      'int', 5 ),
      'MAX_SEPS_DICT' :
    ( 'Split lines containing longer dictionary definitions',
      'int', 3 ),
      'MAX_LINES_BEFORE_SPLIT_LIT' :
    ( 'Split string literals containing more newline characters',
      'int', 2 ),
      'LEFT_MARGIN' :
    ( 'How the left margin should appear',
      'string', '' ),
      'LEFTJUST_DOC_STRINGS' :
    ( 'Left justify doc strings',
      'bool', False ),
      'WRAP_DOC_STRINGS' :
    ( 'Wrap long doc strings',
      'bool', False ),
      'DOUBLE_QUOTED_STRINGS' :
    ( 'Use quotes instead of apostrophes for string literals',
      'bool', False ),
      'SINGLE_QUOTED_STRINGS' :
    ( 'Use apostrophes instead of quotes for string literals',
      'bool', False ),
      'RECODE_STRINGS' :
    ( "Try to decode strings",
      'bool', False ),
      'OVERRIDE_NEWLINE' :
    ( "How the newline sequence should appear.\n" \
      "Normally, the first thing that looks like a newline " \
      "sequence on input is captured and used at the end of every " \
      "line of output.  If this is not satisfactory, the desired " \
      "output newline sequence may be specified here.",
      "string", None ),
      'CAN_SPLIT_STRINGS' :
    ( 'Split longer strings',
      'bool', False ),
      'DOC_TAB_REPLACEMENT' :
    ( 'This literal replaces tab characters in doc strings and comments',
      'string', '    ' ),
      'KEEP_UNASSIGNED_CONSTANTS' :
    ( "Preserve unassigned constants so that code to be tidied\n" \
      "may contain blocks of commented-out lines that have been no-op'ed\n" \
      "with leading and trailing triple quotes. Python scripts may declare\n" \
      "constants without assigning them to a variables, but PythonTidy\n" \
      "considers this wasteful and normally elides them.",
      'bool', False ),
      'PARENTHESIZE_TUPLE_DISPLAY' :
    ( "Omit parentheses around tuples, which are superfluous\n" \
      "after all. Normal PythonTidy behavior will be still to include them\n" \
      "as a sort of tuple display analogous to list displays, dict\n" \
      "displays, and yet-to-come set displays.",
      'bool', True ),
      'JAVA_STYLE_LIST_DEDENT' :
    ( "When PythonTidy splits longer lines, the statement normally is\n" \
      "closed before the margin is restored. The closing bracket, brace,\n" \
      "or parenthesis is placed at the current indent level. This looks\n" \
      "ugly to \"C\" programmers. If this option is checked, the closing\n" \
      "bracket, brace, or parenthesis is brought back left to the indent\n" \
      "level of the enclosing statement.",
      'bool', False ),
      'INDENTATION' :
    ( 'String used to indent lines',
      'string', '    ' ),
      'FUNCTION_PARAM_SEP' :
    ( 'How function parameters are separated',
      'string', ', ' ),
      'LIST_SEP' :
    (  'How list items are separated',
      'string', ', ' ),
      'SUBSCRIPT_SEP' :
    ( 'How subscripts are separated',
      'string', ', ' )
    }

