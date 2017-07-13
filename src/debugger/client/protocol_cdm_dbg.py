#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

# The address used for debugger/client communications.
DEBUG_ADDRESS = '127.0.0.1'

METHOD_CLIENT_OUTPUT = 'ClientOutput'
METHOD_REQUEST_INPUT = 'RequestInput'
METHOD_REQUEST_VARIABLES = 'RequestVariables'
METHOD_REQUEST_VARIABLE = 'RequestVariable'
METHOD_REQUEST_THREAD_LIST = 'RequestThreadList'
METHOD_REQUEST_THREAD_SET = 'RequestThreadSet'
METHOD_RESPONSE_THREAD_SET = 'ResponseThreadSet'
METHOD_RESPONSE_THREAD_LIST = 'ResponseThreadList'
METHOD_RESPONSE_STACK = 'ResponseStack'
METHOD_REQUEST_BANNER = 'RequestBanner'
METHOD_RESPONSE_BANNER = 'ResponseBanner'
METHOD_REQUEST_SET_FILTER = 'RequestSetFilter'
METHOD_REQUEST_CALL_TRACE = 'RequestCallTrace'
METHOD_REQUEST_ENVIRONMENT = 'RequestEnvironment'
METHOD_REQUEST_LOAD = 'RequestLoad'
METHOD_REQUEST_RUN = 'RequestRun'
METHOD_EXECUTE_STATEMENT = 'ExecuteStatement'
METHOD_RESPONSE_CONTINUE = 'ResponseContinue'
METHOD_RESPONSE_OK = 'ResponseOK'
METHOD_REQUEST_STEP = 'RequestStep'
METHOD_REQUEST_STEP_OVER = 'RequestStepOver'
METHOD_REQUEST_STEP_OUT = 'RequestStepOut'
METHOD_REQUEST_STEP_QUIT = 'RequestStepQuit'
METHOD_REQUEST_MOVE_IP = 'RequestMoveIP'
METHOD_REQUEST_CONTINUE = 'RequestContinue'
METHOD_USER_INPUT = 'UserInput'
METHOD_REQUEST_BREAKPOINT = 'RequestBreakpoint'
METHOD_RESPONSE_BP_CONDITION_ERROR = 'ResponseBPConditionError'
METHOD_REQUEST_BP_ENABLE = 'RequestBreakpointEnable'
METHOD_REQUEST_BP_IGNORE = 'RequestBreakpointIgnore'
METHOD_REQUEST_WATCH = 'RequestWatch'
METHOD_RESPONSE_WATCH_CONDITION_ERROR = 'ResponseWatchConditionError'
METHOD_REQUEST_WATCH_ENABLE = 'RequestWatchEnable'
METHOD_REQUEST_WATCH_IGNORE = 'RequestWatchIgnore'
METHOD_REQUEST_SHUTDOWN = 'RequestShutdown'
METHOD_RESPONSE_FORK_TO = 'ResponseForkTo'
METHOD_RESPONSE_CLEAR_BP = 'ResponseClearBreakpoint'
METHOD_RESPONSE_CLEAR_WATCH = 'ResponseClearWatch'
METHOD_RESPONSE_LINE = 'ResponseLine'
METHOD_CALL_TRACE = 'CallTrace'
METHOD_RESPONSE_EXCEPTION = 'ResponseException'
METHOD_RESPONSE_SYNTAX = 'ResponseSyntax'
METHOD_PASSIVE_STARTUP = 'PassiveStartup'
METHOD_RESPONSE_SIGNAL = 'ResponseSignal'
METHOD_RESPONSE_EXIT = 'ResponseExit'
METHOD_RESPONSE_VARIABLES = 'ResponseVariables'
METHOD_RESPONSE_VARIABLE = 'ResponseVariable'
METHOD_REQUEST_FORK_TO = 'RequestForkTo'

METHOD_STDOUT = 'ClientStdout'
METHOD_STDERR = 'ClientStderr'


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
