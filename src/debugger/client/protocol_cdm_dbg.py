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

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Module defining the debug protocol tokens"""

# Distinctive return codes
KILLED = -100000
DISCONNECTED = -200000
FAILED_TO_START = -300000
SYNTAX_ERROR_AT_START = -400000
STOPPED_BY_REQUEST = -500000
UNHANDLED_EXCEPTION = -600000

METHOD_STDOUT = 'Stdout'
METHOD_STDERR = 'Stderr'
METHOD_STDIN = 'Stdin'

METHOD_CLIENT_OUTPUT = 'ClientOutput'
METHOD_THREAD_LIST = 'ThreadList'                       # to/from IDE
METHOD_THREAD_SET = 'ThreadSet'                         # to/from IDE
METHOD_VARIABLES = 'Variables'                          # to/from IDE
METHOD_VARIABLE = 'Variable'                            # to/from IDE
METHOD_FORK_TO = 'ForkTo'                               # to/from IDE
METHOD_CALL_TRACE = 'CallTrace'                         # to/from IDE

METHOD_DEBUG_STARTUP = 'DebugStartup'                   # to IDE
METHOD_LINE = 'Line'                                    # to IDE
METHOD_EXCEPTION = 'Exception'                          # to IDE
METHOD_STACK = 'Stack'                                  # to IDE
METHOD_BP_CONDITION_ERROR = 'BPConditionError'          # to IDE
METHOD_WP_CONDITION_ERROR = 'WPConditionError'          # to IDE
METHOD_CLEAR_BP = 'ClearBreakpoint'                     # to IDE
METHOD_CLEAR_WP = 'ClearWatchpoint'                     # to IDE
METHOD_SYNTAX_ERROR = 'SyntaxError'                     # to IDE
METHOD_SIGNAL = 'Signal'                                # to IDE
METHOD_EXEC_STATEMENT_ERROR = 'ExecStatementError'      # to IDE
METHOD_EXEC_STATEMENT_OUTPUT = 'ExecStatementOutput'    # to IDE

METHOD_CONTINUE = 'Continue'                            # from IDE
METHOD_STEP_QUIT = 'StepQuit'                           # from IDE
METHOD_STEP_OUT = 'StepOut'                             # from IDE
METHOD_STEP_OVER = 'StepOver'                           # from IDE
METHOD_STEP = 'Step'                                    # from IDE
METHOD_MOVE_IP = 'MoveIP'                               # from IDE
METHOD_SET_BP = 'SetBreakpoint'                         # from IDE
METHOD_BP_ENABLE = 'EnableBreakpoint'                   # from IDE
METHOD_BP_IGNORE = 'IgnoreBreakpoint'                   # from IDE
METHOD_SET_WP = 'SetWatchpoint'                         # from IDE
METHOD_WP_ENABLE = 'EnableWatchpoint'                   # from IDE
METHOD_WP_IGNORE = 'IgnoreWatchpoint'                   # from IDE
METHOD_SET_ENVIRONMENT = 'SetEnvironment'               # from IDE
METHOD_EXECUTE_STATEMENT = 'ExecuteStatement'           # from IDE
METHOD_SHUTDOWN = 'Shutdown'                            # from IDE
METHOD_SET_FILTER = 'SetFilter'                         # from IDE

METHOD_PROC_ID_INFO = 'ProcIDInfo'
METHOD_PROLOGUE_CONTINUE = 'PrologueContinue'
METHOD_EPILOGUE_EXIT = 'EpilogueExit'
METHOD_EPILOGUE_EXIT_CODE = 'EpilogueExitCode'

VAR_TYPE_DISP_STRINGS = {
    '__': 'Hidden Attributes',
    'NoneType': 'None',
    'type': 'Type',
    'bool': 'Boolean',
    'int': 'Integer',
    'long': 'Long Integer',
    'float': 'Float',
    'complex': 'Complex',
    'str': 'String',
    'unicode': 'Unicode String',
    'tuple': 'Tuple',
    'list': 'List/Array',
    'dict': 'Dictionary/Hash/Map',
    'dict-proxy': 'Dictionary Proxy',
    'set': 'Set',
    'frozenset': 'Frozen Set',
    'file': 'File',
    'xrange': 'X Range',
    'slice': 'Slice',
    'buffer': 'Buffer',
    'class': 'Class',
    'instance': 'Class Instance',
    'method': 'Class Method',
    'property': 'Class Property',
    'generator': 'Generator',
    'function': 'Function',
    'builtin_function_or_method': 'Builtin Function',
    'code': 'Code',
    'module': 'Module',
    'ellipsis': 'Ellipsis',
    'traceback': 'Traceback',
    'frame': 'Frame',
    'other': 'Other'}
