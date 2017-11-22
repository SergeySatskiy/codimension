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
# The file was taken from eric 4/6 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Module implementing a debug client base class"""

import sys
import socket
import codeop
import codecs
import traceback
import os
import imp
import re
import signal
from PyQt5.QtNetwork import QTcpSocket, QAbstractSocket, QHostAddress
from protocol_cdm_dbg import (METHOD_PROC_ID_INFO, METHOD_PROLOGUE_CONTINUE,
                              METHOD_STDIN, VAR_TYPE_DISP_STRINGS,
                              METHOD_VARIABLES, METHOD_VARIABLE,
                              METHOD_THREAD_LIST, METHOD_THREAD_SET,
                              METHOD_FORK_TO,
                              METHOD_CONTINUE, METHOD_DEBUG_STARTUP,
                              METHOD_CALL_TRACE, METHOD_LINE,
                              METHOD_EXCEPTION, METHOD_STACK, METHOD_STEP_QUIT,
                              METHOD_STEP_OUT, METHOD_STEP_OVER, METHOD_STEP,
                              METHOD_MOVE_IP, METHOD_SET_BP,
                              METHOD_BP_CONDITION_ERROR, METHOD_BP_ENABLE,
                              METHOD_BP_IGNORE, METHOD_SET_WP,
                              METHOD_WP_CONDITION_ERROR, METHOD_WP_ENABLE,
                              METHOD_WP_IGNORE, METHOD_CLEAR_BP,
                              METHOD_CLEAR_WP, METHOD_SYNTAX_ERROR,
                              METHOD_SET_ENVIRONMENT, METHOD_EXECUTE_STATEMENT,
                              METHOD_SIGNAL, METHOD_SHUTDOWN,
                              METHOD_SET_FILTER, METHOD_EPILOGUE_EXIT_CODE,
                              METHOD_EPILOGUE_EXIT, SYNTAX_ERROR_AT_START,
                              STOPPED_BY_REQUEST, METHOD_EXEC_STATEMENT_ERROR,
                              METHOD_EXEC_STATEMENT_OUTPUT)
from base_cdm_dbg import setRecursionLimit
from asyncfile_cdm_dbg import AsyncFile
from outredir_cdm_dbg import OutStreamRedirector, OutStreamCollector
from bp_wp_cdm_dbg import Breakpoint, Watch
from cdm_dbg_utils import (sendJSONCommand, formatArgValues, getArgValues,
                           printerr, waitForIDEMessage,
                           getParsedJSONMessage)
from variables_cdm_dbg import getType, TOO_LARGE_ATTRIBUTE


# If set to true then the client prints debug messages on the original stderr
CLIENT_DEBUG = False

DEBUG_CLIENT_INSTANCE = None
VAR_TYPE_STRINGS = list(VAR_TYPE_DISP_STRINGS.keys())
DEBUG_CLIENT_ORIG_INPUT = None
DEBUG_CLIENT_ORIG_FORK = None
DEBUG_CLIENT_ORIG_CLOSE = None
DEBUG_CLIENT_ORIG_SET_RECURSION_LIMIT = None

WAIT_CONTINUE_TIMEOUT = 5       # in seconds
WAIT_EXIT_COMMAND_TIMEOUT = 5   # in seconds


def debugClientInput(prompt="", echo=True):
    """Replacement for the standard input builtin"""
    if DEBUG_CLIENT_INSTANCE is None or not DEBUG_CLIENT_INSTANCE.redirect:
        return DEBUG_CLIENT_ORIG_INPUT(prompt)
    return DEBUG_CLIENT_INSTANCE.input(prompt, echo)


# Use our own input().
try:
    DEBUG_CLIENT_ORIG_INPUT = __builtins__.__dict__['input']
    __builtins__.__dict__['input'] = debugClientInput
except (AttributeError, KeyError):
    import __main__
    DEBUG_CLIENT_ORIG_INPUT = __main__.__builtins__.__dict__['input']
    __main__.__builtins__.__dict__['input'] = debugClientInput


def debugClientFork():
    """Replacement for the standard os.fork()"""
    if DEBUG_CLIENT_INSTANCE is None:
        return DEBUG_CLIENT_ORIG_FORK()
    return DEBUG_CLIENT_INSTANCE.fork()


# use our own fork().
if 'fork' in dir(os):
    DEBUG_CLIENT_ORIG_FORK = os.fork
    os.fork = debugClientFork


def debugClientClose(filedesc):
    """Replacement for the standard os.close(fd)"""
    if DEBUG_CLIENT_INSTANCE is None:
        return DEBUG_CLIENT_ORIG_CLOSE(filedesc)
    return DEBUG_CLIENT_INSTANCE.close(filedesc)


# use our own close()
if 'close' in dir(os):
    DEBUG_CLIENT_ORIG_CLOSE = os.close
    os.close = debugClientClose


def debugClientSetRecursionLimit(limit):
    """Replacement for the standard sys.setrecursionlimit(limit)"""
    rlimit = max(limit, 64)
    setRecursionLimit(rlimit)
    DEBUG_CLIENT_ORIG_SET_RECURSION_LIMIT(rlimit + 64)


# use our own setrecursionlimit().
if 'setrecursionlimit' in dir(sys):
    DEBUG_CLIENT_ORIG_SET_RECURSION_LIMIT = sys.setrecursionlimit
    sys.setrecursionlimit = debugClientSetRecursionLimit
    debugClientSetRecursionLimit(sys.getrecursionlimit())


class DebugClientBase(object):

    """Class implementing the client side of the debugger.

    It provides access to the Python interpeter from a debugger running in
    another process.

    The protocol between the debugger and the client is based on JSONRPC 2.0
    PDUs. Each one is sent on a single line, i.e. commands or responses are
    separated by a linefeed character.

    If the debugger closes the session there is no response from the client.
    The client may close the session at any time as a result of the script
    being debugged closing or crashing.

    Note: This class is meant to be subclassed by individual
    DebugClient classes. Do not instantiate it directly.
    """

    # keep these in sync with VariablesViewer.VariableItem.Indicators
    INDICATORS = ['()', '[]', '{:}', '{}']

    def __init__(self):
        self.breakpoints = {}
        self.redirect = True
        self.socket = None
        self.procuuid = None

        self.__messageHandlers = {}
        self.__initMessageHandlers()

        # special objects representing the main scripts thread and frame
        self.mainThread = self
        self.framenr = 0

        # The context to run the debugged program in.
        self.debugMod = imp.new_module('__main__')
        self.debugMod.__dict__['__builtins__'] = __builtins__

        # The list of complete lines to execute.
        self.buffer = ''

        # The list of regexp objects to filter variables against
        self.globalsFilterObjects = []
        self.localsFilterObjects = []

        self._fncache = {}
        self.dircache = []
        self.passive = False    # used to indicate the passive mode
        self.running = None
        self.test = None
        self.debugging = False
        self.userInput = None

        self.forkAuto = False
        self.forkChild = False

        self.readstream = None
        self.pollingDisabled = False

        self.callTraceEnabled = None

        self.compileCommand = codeop.CommandCompiler()

        self.__encoding = 'utf-8'
        self.eventExit = None
        self.__needEpilogue = True

    def __initMessageHandlers(self):
        """initializes a map for the message handlers"""
        self.__messageHandlers = {
            METHOD_VARIABLES: self.__handleVariables,
            METHOD_VARIABLE: self.__handleVariable,
            METHOD_THREAD_LIST: self.__handleThreadList,
            METHOD_FORK_TO: self.__handleForkTo,
            METHOD_SHUTDOWN: self.__handleShutdown,
            METHOD_WP_IGNORE: self.__handleWPIgnore,
            METHOD_WP_ENABLE: self.__handleWPEnable,
            METHOD_SET_WP: self.__handleSetWP,
            METHOD_BP_IGNORE: self.__handleBPIgnore,
            METHOD_BP_ENABLE: self.__handleBPEnable,
            METHOD_SET_BP: self.__handleSetBP,
            METHOD_STDIN: self.__handleStdin,
            METHOD_CONTINUE: self.__handleContinue,
            METHOD_MOVE_IP: self.__handleMoveIP,
            METHOD_STEP_QUIT: self.__handleStepQuit,
            METHOD_STEP_OUT: self.__handleStepOut,
            METHOD_STEP_OVER: self.__handleStepOver,
            METHOD_STEP: self.__handleStep,
            METHOD_EXECUTE_STATEMENT: self.__handleExecuteStatement,
            METHOD_SET_ENVIRONMENT: self.__handleSetEnvironment,
            METHOD_CALL_TRACE: self.__handleCallTrace,
            METHOD_SET_FILTER: self.__handleSetFilter,
            METHOD_THREAD_SET: self.__handleThreadSet}

    def input(self, prompt, echo):
        """input() using the event loop"""
        sendJSONCommand(self.socket, METHOD_STDIN,
                        self.procuuid, {'prompt': prompt, 'echo': echo})
        self.eventLoop(True)
        return self.userInput

    def sessionClose(self, terminate=True):
        """Closes the session with the debugger and optionally terminate"""
        try:
            self.set_quit()
        except:
            pass

        self.debugging = False

        # make sure we close down our end of the socket
        # might be overkill as normally stdin, stdout and stderr
        # SHOULD be closed on exit, but it does not hurt to do it here
        self.readstream.close(True)

        if terminate:
            # Ok, go away.
            sys.exit()

    def __compileFileSource(self, filename, mode='exec'):
        """Compiles source code read from a file"""
        with codecs.open(filename, encoding=self.__encoding) as fp:
            statement = fp.read()

        try:
            code = compile(statement + '\n', filename, mode)
        except SyntaxError:
            exctype, excval, exctb = sys.exc_info()
            try:
                message = str(excval)
                filename = excval.filename
                lineno = excval.lineno
                charno = excval.offset
                if charno is None:
                    charno = 0
            except (AttributeError, ValueError):
                message = ""
                filename = ""
                lineno = 0
                charno = 0

            self.sendSyntaxError(message, filename, lineno, charno)
            return None
        return code

    def handleJSONCommand(self):
        """Handle a command serialized as a JSON string"""
        method, procuuid, params, _ = getParsedJSONMessage(self.socket)
        if procuuid != self.procuuid:
            return

        if CLIENT_DEBUG:
            printerr("Method: " + method + " Params: " + repr(params))

        try:
            self.__messageHandlers[method](params)
        except KeyError:
            printerr('Unhandled message. Method: ' + method +
                     ' Params: ' + repr(params))

    def __handleThreadSet(self, params):
        """Handling METHOD_THREAD_SET"""
        if params['threadID'] in self.threads:
            self.setCurrentThread(params['threadID'])
            sendJSONCommand(self.socket, METHOD_THREAD_SET,
                            self.procuuid, None)
            stack = self.currentThread.getStack()
            sendJSONCommand(self.socket, METHOD_STACK,
                            self.procuuid, {'stack': stack})

    def __handleSetFilter(self, params):
        """Handling METHOD_SET_FILTER"""
        self.__generateFilterObjects(params['scope'], params['filter'])

    def __handleCallTrace(self, params):
        """Handling METHOD_CALL_TRACE"""
        self.setCallTrace(params['enable'])

    def __handleSetEnvironment(self, params):
        """Handling METHOD_SET_ENVIRONMENT"""
        for key, value in params['environment'].items():
            if key.endswith('+'):
                if key[:-1] in os.environ:
                    os.environ[key[:-1]] += value
                else:
                    os.environ[key[:-1]] = value
            else:
                os.environ[key] = value

    def __handleExecuteStatement(self, params):
        """Handling METHOD_EXECUTE_STATEMENT"""
        statement = params['statement']
        try:
            code = self.compileCommand(statement, self.readstream.name)
        except (OverflowError, SyntaxError, ValueError):
            # Report the exception
            sys.last_type, sys.last_value, sys.last_traceback = \
                sys.exc_info()
            sendJSONCommand(self.socket, METHOD_EXEC_STATEMENT_ERROR,
                            self.procuuid,
                            {'text': ''.join(traceback.format_exception_only(
                                sys.last_type, sys.last_value))})
            return

        if code is None:
            sendJSONCommand(self.socket, METHOD_EXEC_STATEMENT_ERROR,
                            self.procuuid,
                            {'text': 'Incomplete statement to execute'})
            return

        try:
            cf = self.currentThread.getCurrentFrame()
            # program has terminated
            if cf is None:
                self.running = None
                _globals = self.debugMod.__dict__
                _locals = _globals
            else:
                frmnr = self.framenr
                while cf is not None and frmnr > 0:
                    cf = cf.f_back
                    frmnr -= 1
                _globals = cf.f_globals
                _locals = self.currentThread.getFrameLocals(self.framenr)

            # Execute a statement using a collector to collect both
            # stdout and stderr. The combined output is sent to the IDE
            collector = OutStreamCollector()
            self.__execWithCollector(code, _globals, _locals, collector)
            self.currentThread.storeFrameLocals(self.framenr)

            sendJSONCommand(self.socket, METHOD_EXEC_STATEMENT_OUTPUT,
                            self.procuuid,
                            {'text': collector.buf})

        except SystemExit as exc:
            self.progTerminated(exc.code)
        except Exception:
            # Report the exception and the traceback
            tlist = []
            try:
                exc_type, exc_value, exc_tb = sys.exc_info()
                sys.last_type = exc_type
                sys.last_value = exc_value
                sys.last_traceback = exc_tb
                tblist = traceback.extract_tb(exc_tb)
                del tblist[:1]
                tlist = traceback.format_list(tblist)
                if tlist:
                    tlist.insert(0, 'Traceback (innermost last):\n')
                    tlist.extend(traceback.format_exception_only(
                        exc_type, exc_value))
            finally:
                tblist = exc_tb = None

            sendJSONCommand(self.socket, METHOD_EXEC_STATEMENT_ERROR,
                            self.procuuid, {'text': ''.join(tlist)})

    @staticmethod
    def __execWithCollector(code, globalVars, localVars, collector):
        """The actual execution with the output collected"""
        oldStreams = [None for _ in range(6)]
        if 'sys' in globalVars:
            oldStreams[0] = globalVars['sys'].stdout
            oldStreams[1] = globalVars['sys'].stderr
            globalVars['sys'].stdout = collector
            globalVars['sys'].stderr = collector
        if 'sys' in localVars:
            oldStreams[2] = localVars['sys'].stdout
            oldStreams[3] = localVars['sys'].stderr
            localVars['sys'].stdout = collector
            localVars['sys'].stderr = collector
        oldStreams[4] = sys.stdout
        oldStreams[5] = sys.stderr
        sys.stdout = collector
        sys.stderr = collector

        try:
            exec(code, globalVars, localVars)
        finally:
            if 'sys' in globalVars:
                globalVars['sys'].stdout = oldStreams[0]
                globalVars['sys'].stderr = oldStreams[1]
            if 'sys' in localVars:
                localVars['sys'].stdout = oldStreams[2]
                localVars['sys'].stderr = oldStreams[3]
            sys.stdout = oldStreams[4]
            sys.stderr = oldStreams[5]

    def __handleStep(self, _):
        """Handling METHOD_STEP"""
        self.currentThreadExec.step(True)
        self.eventExit = True

    def __handleStepOver(self, _):
        """Handling METHOD_STEP_OVER"""
        self.currentThreadExec.step(False)
        self.eventExit = True

    def __handleStepOut(self, _):
        """Handling METHOD_STEP_OUT"""
        self.currentThreadExec.stepOut()
        self.eventExit = True

    def __handleStepQuit(self, params):
        """Handling METHOD_STEP_QUIT"""
        if self.passive:
            if params:
                if 'exitCode' in params:
                    # The IDE requested to exit with a certain code
                    self.progTerminated(params['exitCode'])
                    return
            self.progTerminated(STOPPED_BY_REQUEST)
        else:
            self.set_quit()
            self.eventExit = True

    def __handleMoveIP(self, params):
        """Handling METHOD_MOVE_IP"""
        newLine = params['newLine']
        self.currentThreadExec.move_instruction_pointer(newLine)

    def __handleContinue(self, params):
        """Handling METHOD_CONTINUE"""
        self.currentThreadExec.go(params['special'])
        self.eventExit = True

    def __handleStdin(self, params):
        """Handling METHOD_STDIN"""
        # If we are handling raw mode input then break out of the current
        # event loop.
        self.userInput = params['input']
        self.eventExit = True

    def __handleSetBP(self, params):
        """Handling METHOD_SET_BP"""
        if params['setBreakpoint']:
            if params['condition'] in ['None', '']:
                cond = None
            elif params['condition'] is not None:
                try:
                    cond = compile(params['condition'], '<string>', 'eval')
                except SyntaxError:
                    sendJSONCommand(self.socket, METHOD_BP_CONDITION_ERROR,
                                    self.procuuid,
                                    {'filename': params['filename'],
                                     'line': params['line']})
                    return
            else:
                cond = None

            Breakpoint(params['filename'], params['line'],
                       params['temporary'], cond)
        else:
            Breakpoint.clear_break(params['filename'], params['line'])

    def __handleBPEnable(self, params):
        """Handling METHOD_BP_ENABLE"""
        bPoint = Breakpoint.get_break(params['filename'], params['line'])
        if bPoint is not None:
            if params['enable']:
                bPoint.enable()
            else:
                bPoint.disable()

    def __handleBPIgnore(self, params):
        """Handling METHOD_BP_IGNORE"""
        bPoint = Breakpoint.get_break(params['filename'], params['line'])
        if bPoint is not None:
            bPoint.ignore = params['count']

    def __handleSetWP(self, params):
        """Handling METHOD_SET_WP"""
        if params['setWatch']:
            if params['condition'].endswith(
                    ('??created??', '??changed??')):
                compiledCond, flag = params['condition'].split()
            else:
                compiledCond = params['condition']
                flag = ''

            try:
                compiledCond = compile(compiledCond, '<string>', 'eval')
            except SyntaxError:
                sendJSONCommand(self.socket, METHOD_WP_CONDITION_ERROR,
                                self.procuuid,
                                {'condition': params['condition']})
                return
            Watch(params['condition'], compiledCond, flag,
                  params['temporary'])
        else:
            Watch.clear_watch(params['condition'])

    def __handleWPEnable(self, params):
        """Handling METHOD_WP_ENABLE"""
        wPoint = Watch.get_watch(params['condition'])
        if wPoint is not None:
            if params['enable']:
                wPoint.enable()
            else:
                wPoint.disable()

    def __handleWPIgnore(self, params):
        """Handling METHOD_WP_IGNORE"""
        wPoint = Watch.get_watch(params['condition'])
        if wPoint is not None:
            wPoint.ignore = params['count']

    def __handleShutdown(self, _):
        """Handling METHOD_SHUTDOWN"""
        self.sessionClose()

    def __handleForkTo(self, params):
        """Handling METHOD_FORK_TO"""
        # this results from a separate event loop
        self.forkChild = (params['target'] == 'child')
        self.eventExit = True

    def __handleVariables(self, params):
        """Handling METHOD_VARIABLES"""
        self.__dumpVariables(params['frameNumber'], params['scope'],
                             params['filters'])

    def __handleVariable(self, params):
        """Handling METHOD_VARIABLE"""
        self.__dumpVariable(params['variable'], params['frameNumber'],
                            params['scope'], params['filters'])

    def __handleThreadList(self, _):
        """Handling METHOD_THREAD_LIST"""
        self.dumpThreadList()

    def setCallTrace(self, enabled):
        """Sets up the call trace"""
        if enabled:
            sys.setprofile(self.profile)
            self.callTraceEnabled = self.profile
        else:
            sys.setprofile(None)
            self.callTraceEnabled = None

    def sendClearTemporaryBreakpoint(self, filename, lineno):
        """Signals the deletion of a temporary breakpoint"""
        sendJSONCommand(self.socket, METHOD_CLEAR_BP,
                        self.procuuid, {'filename': filename, 'line': lineno})

    def sendClearTemporaryWatch(self, condition):
        """Signals the deletion of a temporary watch expression"""
        sendJSONCommand(self.socket, METHOD_CLEAR_WP,
                        self.procuuid, {'condition': condition})

    def sendResponseLine(self, stack):
        """Sends the current call stack"""
        sendJSONCommand(self.socket, METHOD_LINE,
                        self.procuuid, {'stack': stack})

    def sendCallTrace(self, event, fromInfo, toInfo):
        """Sends a call trace entry"""
        sendJSONCommand(self.socket, METHOD_CALL_TRACE,
                        self.procuuid,
                        {'event': event[0], 'from': fromInfo, 'to': toInfo})

    def sendException(self, exceptionType, exceptionMessage, stack):
        """Sends information for an exception"""
        sendJSONCommand(self.socket, METHOD_EXCEPTION,
                        self.procuuid,
                        {'type': exceptionType, 'message': exceptionMessage,
                         'stack': stack})

    def sendSyntaxError(self, message, filename, lineno, charno):
        """Sends information for a syntax error"""
        sendJSONCommand(self.socket, METHOD_SYNTAX_ERROR,
                        self.procuuid,
                        {'message': message, 'filename': filename,
                         'line': lineno, 'characternumber': charno})

    def sendPassiveStartup(self, filename, exceptions):
        """Sends indication that the debugee is entering event loop"""
        sendJSONCommand(self.socket, METHOD_DEBUG_STARTUP,
                        self.procuuid,
                        {'filename': filename, 'exceptions': exceptions})

    def readReady(self, stream):
        """Called when there is data ready to be read"""
        self.handleJSONCommand()

    def __interact(self):
        """Interacts with the debugger"""
        global DEBUG_CLIENT_INSTANCE

        DEBUG_CLIENT_INSTANCE = self
        self.__receiveBuffer = ''

        if not self.passive:
            # At this point simulate an event loop
            self.eventLoop()

    def eventLoop(self, disablePolling=False):
        """Implements our event loop"""
        self.eventExit = None
        self.pollingDisabled = disablePolling

        while self.eventExit is None:
            if self.socket.waitForReadyRead():
                while self.socket.canReadLine():
                    self.readReady(self.readstream)

        self.eventExit = None
        self.pollingDisabled = False

    def eventPoll(self):
        """Polls for events like 'set break point'"""
        if not self.pollingDisabled:
            # without
            # if self.socket.waitForReadyRead(0):
            # canReadLine() always returns False. I have no idea why.
            # An option with
            # if self.socket.bytesAvailable() > 0:
            # does not work either. So I use a 0 timeout to make it as quick as
            # possible
            if self.socket.waitForReadyRead(0):
                while self.socket.canReadLine():
                    self.readReady(self.readstream)

    def connect(self, remoteAddress, port):
        """Establishes a session with the debugger"""
        self.socket = QTcpSocket()
        if remoteAddress is None:
            self.socket.connectToHost(QHostAddress.LocalHost, port)
        else:
            self.socket.connectToHost(remoteAddress, port)
        if not self.socket.waitForConnected(1000):
            raise Exception('Cannot connect to the IDE')
        self.socket.setSocketOption(QAbstractSocket.KeepAliveOption, 1)
        self.socket.setSocketOption(QAbstractSocket.LowDelayOption, 1)
        self.socket.disconnected.connect(self.__onDisconnected)

    def __onDisconnected(self):
        """IDE dropped the socket"""
        sys.exit(0)

    def __setupStreams(self):
        """Sets up all the required streams"""
        self.readstream = AsyncFile(self.socket,
                                    sys.stdin.mode, sys.stdin.name)

        if self.redirect:
            sys.stdout = OutStreamRedirector(self.socket, True, self.procuuid)
            sys.stderr = OutStreamRedirector(self.socket, False, self.procuuid)
            sys.stdin = self.readstream

        # Attach to the main thread here
        self.attachThread(mainThread=True)

    def __unhandled_exception(self, exctype, excval, exctb):
        """Called to report an uncaught exception"""
        self.mainThread.user_exception((exctype, excval, exctb), True)

    def __interceptSignals(self):
        """Intercepts common signals"""
        for signum in [signal.SIGABRT,          # abnormal termination
                       signal.SIGFPE,           # floating point exception
                       signal.SIGILL,           # illegal instruction
                       signal.SIGSEGV]:         # segmentation violation
            signal.signal(signum, self.__signalHandler)

    def __signalHandler(self, signalNumber, stackFrame):
        """Handles signals"""
        if signalNumber == signal.SIGABRT:
            message = "Abnormal Termination"
        elif signalNumber == signal.SIGFPE:
            message = "Floating Point Exception"
        elif signalNumber == signal.SIGILL:
            message = "Illegal Instruction"
        elif signalNumber == signal.SIGSEGV:
            message = "Segmentation Violation"
        else:
            message = "Unknown Signal '{0}'".format(signalNumber)

        filename = self.absPath(stackFrame.f_code.co_filename)

        linenr = stackFrame.f_lineno
        ffunc = stackFrame.f_code.co_name

        if ffunc == '?':
            ffunc = ''

        if ffunc and not ffunc.startswith('<'):
            argInfo = getArgValues(stackFrame)
            try:
                fargs = formatArgValues(
                    argInfo.args, argInfo.varargs,
                    argInfo.keywords, argInfo.locals)
            except Exception:
                fargs = ''
        else:
            fargs = ''

        sendJSONCommand(self.socket, METHOD_SIGNAL,
                        self.procuuid,
                        {'message': message, 'filename': filename,
                         'linenumber': linenr, 'function': ffunc,
                         'arguments': fargs})

    def absPath(self, fileName):
        """Converts a filename to an absolute name"""
        if os.path.isabs(fileName):
            if sys.version_info[0] == 2:
                fileName = fileName.decode(sys.getfilesystemencoding())
            return fileName

        # Check the cache
        if fileName in self._fncache:
            return self._fncache[fileName]

        # Search sys.path
        for aPath in sys.path:
            afn = os.path.abspath(os.path.join(aPath, fileName))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                if sys.version_info[0] == 2:
                    afn = afn.decode(sys.getfilesystemencoding())

                self._fncache[fileName] = afn
                aDir = os.path.dirname(afn)
                if (aDir not in sys.path) and (aDir not in self.dircache):
                    self.dircache.append(aDir)
                return afn

        # Search the additional directory cache
        for aPath in self.dircache:
            afn = os.path.abspath(os.path.join(aPath, fileName))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                self._fncache[fileName] = afn
                return afn

        # Nothing found
        return fileName

    def getRunning(self):
        """True if the main script we are currently running"""
        return self.running

    def progTerminated(self, status, message=''):
        """Tells the debugger that the program has terminated"""
        if not self.__needEpilogue:
            return

        self.__needEpilogue = False

        if status is None:
            status = 0
        elif not isinstance(status, int):
            message = str(status)
            status = 1

        if self.running:
            self.set_quit()
            self.running = None

        sendJSONCommand(self.socket, METHOD_EPILOGUE_EXIT_CODE,
                        self.procuuid, {'exitCode': status,
                                        'message': message})
        waitForIDEMessage(self.socket, METHOD_EPILOGUE_EXIT,
                          WAIT_EXIT_COMMAND_TIMEOUT)
        # The final message exchange with the IDE has been completed
        # It is safe just to abort
        raise SystemExit

    def __dumpVariables(self, frmnr, scope, filterList):
        """Returns the variables of a frame to the debug server"""
        if self.currentThread is None:
            return

        frmnr += self.currentThread.skipFrames
        if scope == 0:
            self.framenr = frmnr

        f = self.currentThread.getCurrentFrame()

        while f is not None and frmnr > 0:
            f = f.f_back
            frmnr -= 1

        if f is None:
            if scope:
                varDict = self.debugMod.__dict__
            else:
                scope = -1
        elif scope:
            varDict = f.f_globals
        elif f.f_globals is f.f_locals:
            scope = -1
        else:
            varDict = f.f_locals

        varlist = []

        if scope != -1:
            keylist = varDict.keys()

            vlist = self.__formatVariablesList(
                keylist, varDict, scope, filterList)
            varlist.extend(vlist)

        sendJSONCommand(self.socket, METHOD_VARIABLES,
                        self.procuuid, {'scope': scope, 'variables': varlist})

    def __dumpVariable(self, var, frmnr, scope, filterList):
        """Returns the variables of a frame to the debug server"""
        if self.currentThread is None:
            return

        frmnr += self.currentThread.skipFrames
        f = self.currentThread.getCurrentFrame()

        while f is not None and frmnr > 0:
            f = f.f_back
            frmnr -= 1

        if f is None:
            if scope:
                varDict = self.debugMod.__dict__
            else:
                scope = -1
        elif scope:
            varDict = f.f_globals
        elif f.f_globals is f.f_locals:
            scope = -1
        else:
            varDict = f.f_locals

        varlist = []

        if scope != -1:
            variable = varDict
            for attribute in var:
                attribute = self.__extractIndicators(attribute)[0]
                typeObject, typeName, typeStr, resolver = getType(variable)
                if resolver:
                    variable = resolver.resolve(variable, attribute)
                    if variable is None:
                        break
                else:
                    break

            if variable is not None:
                typeObject, typeName, typeStr, resolver = getType(variable)
                if typeStr.startswith(('PyQt5.', 'PyQt4.')):
                    vlist = self.__formatQtVariable(variable, typeName)
                    varlist.extend(vlist)
                elif resolver:
                    varDict = resolver.getDictionary(variable)
                    vlist = self.__formatVariablesList(
                        list(varDict.keys()), varDict, scope, filterList)
                    varlist.extend(vlist)

        sendJSONCommand(self.socket, METHOD_VARIABLE,
                        self.procuuid,
                        {'scope': scope, 'variable': var,
                         'variables': varlist})

    def __extractIndicators(self, var):
        """Extracts the indicator string from a variable text"""
        for indicator in DebugClientBase.INDICATORS:
            if var.endswith(indicator):
                return var[:-len(indicator)], indicator
        return var, ""

    def __formatQtVariable(self, value, qttype):
        """Produces a formatted output of a simple Qt4/Qt5 type"""
        varlist = []
        if qttype == 'QChar':
            varlist.append(
                ('', 'QChar', '{0}'.format(chr(value.unicode()))))
            varlist.append(('', 'int', '{0:d}'.format(value.unicode())))
        elif qttype == 'QByteArray':
            varlist.append(
                ('bytes', 'QByteArray', '{0}'.format(bytes(value))[2:-1]))
            varlist.append(
                ('hex', 'QByteArray', '{0}'.format(value.toHex())[2:-1]))
            varlist.append(
                ('base64', 'QByteArray', '{0}'.format(value.toBase64())[2:-1]))
            varlist.append(('percent encoding', 'QByteArray',
                            '{0}'.format(value.toPercentEncoding())[2:-1]))
        elif qttype == 'QString':
            varlist.append(('', 'QString', '{0}'.format(value)))
        elif qttype == 'QStringList':
            for i in range(value.count()):
                varlist.append(
                    ('{0:d}'.format(i), 'QString', '{0}'.format(value[i])))
        elif qttype == 'QPoint':
            varlist.append(('x', 'int', '{0:d}'.format(value.x())))
            varlist.append(('y', 'int', '{0:d}'.format(value.y())))
        elif qttype == 'QPointF':
            varlist.append(('x', 'float', '{0:g}'.format(value.x())))
            varlist.append(('y', 'float', '{0:g}'.format(value.y())))
        elif qttype == 'QRect':
            varlist.append(('x', 'int', '{0:d}'.format(value.x())))
            varlist.append(('y', 'int', '{0:d}'.format(value.y())))
            varlist.append(('width', 'int', '{0:d}'.format(value.width())))
            varlist.append(('height', 'int', '{0:d}'.format(value.height())))
        elif qttype == 'QRectF':
            varlist.append(('x', 'float', '{0:g}'.format(value.x())))
            varlist.append(('y', 'float', '{0:g}'.format(value.y())))
            varlist.append(('width', 'float', '{0:g}'.format(value.width())))
            varlist.append(('height', 'float', '{0:g}'.format(value.height())))
        elif qttype == 'QSize':
            varlist.append(('width', 'int', '{0:d}'.format(value.width())))
            varlist.append(('height', 'int', '{0:d}'.format(value.height())))
        elif qttype == 'QSizeF':
            varlist.append(('width', 'float', '{0:g}'.format(value.width())))
            varlist.append(('height', 'float', '{0:g}'.format(value.height())))
        elif qttype == 'QColor':
            varlist.append(('name', 'str', '{0}'.format(value.name())))
            red, green, blue, alpha = value.getRgb()
            varlist.append(
                ('rgba', 'int',
                 '{0:d}, {1:d}, {2:d}, {3:d}'.format(red, green, blue, alpha)))
            hue, saturation, value, alpha = value.getHsv()
            varlist.append(
                ('hsva', 'int',
                 '{0:d}, {1:d}, {2:d}, {3:d}'.format(hue, saturation,
                                                     value, alpha)))
            cyan, magenta, yellow, black, alpha = value.getCmyk()
            varlist.append(
                ('cmyka', 'int',
                 '{0:d}, {1:d}, {2:d}, {3:d}, {4:d}'.format(cyan, magenta,
                                                            yellow, black,
                                                            alpha)))
        elif qttype == 'QDate':
            varlist.append(('', 'QDate', '{0}'.format(value.toString())))
        elif qttype == 'QTime':
            varlist.append(('', 'QTime', '{0}'.format(value.toString())))
        elif qttype == 'QDateTime':
            varlist.append(('', 'QDateTime', '{0}'.format(value.toString())))
        elif qttype == 'QDir':
            varlist.append(('path', 'str', '{0}'.format(value.path())))
            varlist.append(('absolutePath', 'str',
                            '{0}'.format(value.absolutePath())))
            varlist.append(('canonicalPath', 'str',
                            '{0}'.format(value.canonicalPath())))
        elif qttype == 'QFile':
            varlist.append(('fileName', 'str', '{0}'.format(value.fileName())))
        elif qttype == 'QFont':
            varlist.append(('family', 'str', '{0}'.format(value.family())))
            varlist.append(
                ('pointSize', 'int', '{0:d}'.format(value.pointSize())))
            varlist.append(('weight', 'int', '{0:d}'.format(value.weight())))
            varlist.append(('bold', 'bool', '{0}'.format(value.bold())))
            varlist.append(('italic', 'bool', '{0}'.format(value.italic())))
        elif qttype == 'QUrl':
            varlist.append(('url', 'str', '{0}'.format(value.toString())))
            varlist.append(('scheme', 'str', '{0}'.format(value.scheme())))
            varlist.append(('user', 'str', '{0}'.format(value.userName())))
            varlist.append(('password', 'str', '{0}'.format(value.password())))
            varlist.append(('host', 'str', '{0}'.format(value.host())))
            varlist.append(('port', 'int', '{0:d}'.format(value.port())))
            varlist.append(('path', 'str', '{0}'.format(value.path())))
        elif qttype == 'QModelIndex':
            varlist.append(('valid', 'bool', '{0}'.format(value.isValid())))
            if value.isValid():
                varlist.append(('row', 'int', '{0}'.format(value.row())))
                varlist.append(('column', 'int', '{0}'.format(value.column())))
                varlist.append(
                    ('internalId', 'int', '{0}'.format(value.internalId())))
                varlist.append(('internalPointer', 'void *',
                                '{0}'.format(value.internalPointer())))
        elif qttype == 'QRegExp':
            varlist.append(('pattern', 'str', '{0}'.format(value.pattern())))

        # GUI stuff
        elif qttype == 'QAction':
            varlist.append(('name', 'str', '{0}'.format(value.objectName())))
            varlist.append(('text', 'str', '{0}'.format(value.text())))
            varlist.append(
                ('icon text', 'str', '{0}'.format(value.iconText())))
            varlist.append(('tooltip', 'str', '{0}'.format(value.toolTip())))
            varlist.append(
                ('whatsthis', 'str', '{0}'.format(value.whatsThis())))
            varlist.append(
                ('shortcut', 'str',
                 '{0}'.format(value.shortcut().toString())))
        elif qttype == 'QKeySequence':
            varlist.append(('value', '', '{0}'.format(value.toString())))

        # XML stuff
        elif qttype == 'QDomAttr':
            varlist.append(('name', 'str', '{0}'.format(value.name())))
            varlist.append(('value', 'str', '{0}'.format(value.value())))
        elif qttype == 'QDomCharacterData':
            varlist.append(('data', 'str', '{0}'.format(value.data())))
        elif qttype == 'QDomComment':
            varlist.append(('data', 'str', '{0}'.format(value.data())))
        elif qttype == "QDomDocument":
            varlist.append(('text', 'str', '{0}'.format(value.toString())))
        elif qttype == 'QDomElement':
            varlist.append(('tagName', 'str', '{0}'.format(value.tagName())))
            varlist.append(('text', 'str', '{0}'.format(value.text())))
        elif qttype == 'QDomText':
            varlist.append(('data', 'str', '{0}'.format(value.data())))

        # Networking stuff
        elif qttype == 'QHostAddress':
            varlist.append(
                ('address', 'QHostAddress', '{0}'.format(value.toString())))

        return varlist

    def __formatVariablesList(self, keylist, dict_, scope, filterList=None,
                              formatSequences=False):
        """Produces a formated variables list"""
        filterList = [] if filterList is None else filterList[:]

        varlist = []
        if scope:
            patternFilterObjects = self.globalsFilterObjects
        else:
            patternFilterObjects = self.localsFilterObjects

        for key in keylist:
            # filter based on the filter pattern
            matched = False
            for pat in patternFilterObjects:
                if pat.match(str(key)):
                    matched = True
                    break
            if matched:
                continue

            # filter hidden attributes (filter #0)
            if 0 in filterList and str(key)[:2] == '__' and not (
                    key == "___len___" and
                    TOO_LARGE_ATTRIBUTE in keylist):
                continue

            # special handling for '__builtins__' (it's way too big)
            if key == '__builtins__':
                rvalue = '<module __builtin__ (built-in)>'
                valtype = 'module'
            else:
                value = dict_[key]
                valtypestr = str(type(value))[1:-1]
                _, valtype = valtypestr.split(' ', 1)
                valtype = valtype[1:-1]
                valtypename = type(value).__name__
                if valtype not in VAR_TYPE_STRINGS:
                    if valtype in ['numpy.ndarray', 'array.array']:
                        if VAR_TYPE_STRINGS.index('list') in filterList:
                            continue
                    elif valtypename == 'MultiValueDict':
                        if VAR_TYPE_STRINGS.index('dict') in filterList:
                            continue
                    elif valtype == 'sip.methoddescriptor':
                        if VAR_TYPE_STRINGS.index('method') in filterList:
                            continue
                    elif valtype == 'sip.enumtype':
                        if VAR_TYPE_STRINGS.index('class') in filterList:
                            continue
                    elif VAR_TYPE_STRINGS.index('instance') in filterList:
                        continue

                    if (not valtypestr.startswith('type ') and
                            valtypename not in
                            ['ndarray', 'MultiValueDict', 'array']):
                        valtype = valtypestr
                else:
                    try:
                        # Strip 'instance' to be equal with Python 3
                        if valtype == 'instancemethod':
                            valtype = 'method'

                        if VAR_TYPE_STRINGS.index(valtype) in filterList:
                            continue
                    except ValueError:
                        if valtype == 'classobj':
                            if VAR_TYPE_STRINGS.index(
                                    'instance') in filterList:
                                continue
                        elif valtype == 'sip.methoddescriptor':
                            if VAR_TYPE_STRINGS.index(
                                    'method') in filterList:
                                continue
                        elif valtype == 'sip.enumtype':
                            if VAR_TYPE_STRINGS.index('class') in \
                                    filterList:
                                continue
                        elif not valtype.startswith('PySide') and \
                            (VAR_TYPE_STRINGS.index('other') in
                             filterList):
                            continue

                try:
                    if valtype in ['list', 'tuple', 'dict', 'set',
                                   'frozenset', 'array.array']:
                        if valtype == 'dict':
                            rvalue = '{0:d}'.format(len(value.keys()))
                        else:
                            rvalue = '{0:d}'.format(len(value))
                    elif valtype == 'numpy.ndarray':
                        rvalue = '{0:d}'.format(value.size)
                    elif valtypename == 'MultiValueDict':
                        rvalue = '{0:d}'.format(len(value.keys()))
                        valtype = 'django.MultiValueDict'  # shortened type
                    else:
                        rvalue = repr(value)
                        if valtype.startswith('class') and \
                           rvalue[0] in ['{', '(', '[']:
                            rvalue = ''
                except Exception:
                    rvalue = ''

            if formatSequences:
                if str(key) == key:
                    key = "'{0!s}'".format(key)
                else:
                    key = str(key)
            varlist.append((key, valtype, rvalue))

        return varlist

    def __generateFilterObjects(self, scope, filterString):
        """Converts a filter string to a list of filter objects"""
        patternFilterObjects = []
        for pattern in filterString.split(';'):
            patternFilterObjects.append(re.compile('^{0}$'.format(pattern)))
        if scope:
            self.globalsFilterObjects = patternFilterObjects[:]
        else:
            self.localsFilterObjects = patternFilterObjects[:]

    def startProgInDebugger(self, progargs, host,
                            port, exceptions, tracePython,
                            enableCallTrace):
        """Starts the remote debugger"""
        remoteAddress = self.resolveHost(host)
        self.connect(remoteAddress, port)

        # Common part of running: the IDE waits for the client message
        sendJSONCommand(self.socket, METHOD_PROC_ID_INFO,
                        self.procuuid, None)
        waitForIDEMessage(self.socket, METHOD_PROLOGUE_CONTINUE,
                          WAIT_CONTINUE_TIMEOUT)

        self.__setupStreams()

        self._fncache = {}
        self.dircache = []
        sys.argv = progargs[:]
        sys.argv[0] = os.path.abspath(sys.argv[0])
        sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
        self.running = sys.argv[0]
        self.debugging = True

        self.passive = True
        self.sendPassiveStartup(self.running, exceptions)
        self.__interact()

        self.attachThread(mainThread=True)
        self.mainThread.tracePythonLibs(tracePython)

        # set the system exception handling function to ensure, that
        # we report on all unhandled exceptions
        sys.excepthook = self.__unhandled_exception
        self.__interceptSignals()

        # This will eventually enter a local event loop.
        # Note the use of backquotes to cause a repr of self.running. The
        # need for this is on Windows os where backslash is the path separator.
        # They will get inadvertantly stripped away during the eval causing
        # IOErrors if self.running is passed as a normal str.
        self.debugMod.__dict__['__file__'] = self.running
        sys.modules['__main__'] = self.debugMod

        code = self.__compileFileSource(self.running)
        if code:
            self.setCallTrace(enableCallTrace)
            res = self.mainThread.run(code, self.debugMod.__dict__, debug=True)
        else:
            res = SYNTAX_ERROR_AT_START
        self.progTerminated(res)

    @staticmethod
    def resolveHost(host):
        """Resolves a hostname to an IP address"""
        try:
            host, _ = host.split("@@")
            family = socket.AF_INET6
        except ValueError:
            # version = 'v4'
            family = socket.AF_INET
        return socket.getaddrinfo(host, None, family,
                                  socket.SOCK_STREAM)[0][4][0]

    def main(self):
        """
        Public method implementing the main method.
        """
        if '--' in sys.argv:
            args = sys.argv[1:]
            host = None
            port = None
            tracePython = False
            exceptions = True
            enableCallTrace = True
            while args[0]:
                if args[0] == '--host':
                    host = args[1]
                    del args[0]
                    del args[0]
                elif args[0] == '--port':
                    port = int(args[1])
                    del args[0]
                    del args[0]
                elif args[0] == '--trace-python':
                    tracePython = True
                    del args[0]
                elif args[0] == '--no-exc-report':
                    exceptions = False
                    del args[0]
                elif args[0] == '--no-redirect':
                    self.redirect = False
                    del args[0]
                elif args[0] == '--encoding':
                    self.__encoding = args[1]
                    del args[0]
                    del args[0]
                elif args[0] == '--fork-child':
                    self.forkAuto = True
                    self.forkChild = True
                    del args[0]
                elif args[0] == '--fork-parent':
                    self.forkAuto = True
                    self.forkChild = False
                    del args[0]
                elif args[0] == '--procuuid':
                    self.procuuid = args[1]
                    del args[0]
                    del args[0]
                elif args[0] == '--no-call-trace':
                    enableCallTrace = False
                    del args[0]
                elif args[0] == '--':
                    del args[0]
                    break
                else:   # unknown option
                    del args[0]
            if not args:
                print("No program given. Aborting...")
            elif port is None or host is None:
                print("Network address is not provided. Aborting...")
            else:
                self.startProgInDebugger(args, host, port,
                                         exceptions,
                                         tracePython,
                                         enableCallTrace)
        else:
            print("No script to debug. Aborting...")

    def fork(self):
        """fork routine deciding which branch to follow"""
        # It does not make sense to follow something which was run via the
        # subprocess module. The subprocess module uses fork() internally,
        # so let's analyze it and do auto follow parent even if it was not
        # required explicitly.
        isPopen = False
        stackFrames = traceback.extract_stack()
        for stackFrame in stackFrames:
            if stackFrame[2] == '_execute_child':
                if stackFrame[0].endswith(os.path.sep + 'subprocess.py'):
                    isPopen = True

        if not self.forkAuto and not isPopen:
            sendJSONCommand(self.socket, METHOD_FORK_TO,
                            self.procuuid, None)
            self.eventLoop(True)
        pid = DEBUG_CLIENT_ORIG_FORK()

        if isPopen:
            # Switch to following parent
            oldFollow = self.forkChild
            self.forkChild = False

        if pid == 0:
            # child
            if not self.forkChild:
                sys.settrace(None)
                sys.setprofile(None)
                self.sessionClose(False)
        else:
            # parent
            if self.forkChild:
                sys.settrace(None)
                sys.setprofile(None)
                self.sessionClose(False)

        if isPopen:
            # Switch to what it was before
            self.forkChild = oldFollow
        return pid

    def close(self, fdescriptor):
        """close method as a replacement for os.close().

        It prevents the debugger connections from being closed
        """
        if fdescriptor not in [self.readstream.fileno()]:
            DEBUG_CLIENT_ORIG_CLOSE(fdescriptor)

    @staticmethod
    def __getSysPath(firstEntry):
        """calculate a path list including the PYTHONPATH env variable"""
        sysPath = [path for path in
                   os.environ.get('PYTHONPATH', '').split(os.pathsep)
                   if path not in sys.path] + sys.path[:]
        if '' in sysPath:
            sysPath.remove('')
        sysPath.insert(0, firstEntry)
        sysPath.insert(0, '')
        return sysPath
