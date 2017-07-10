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

"""Module implementing a debug client base class"""

import sys
import socket
import select
import codeop
import codecs
import traceback
import os
import time
import imp
import re
import signal
import atexit
import json

from .protocol_cdm_dbg import *
from .base_cdm_dbg import setRecursionLimit
from .asyncfile_cdm_dbg import AsyncFile, AsyncPendingWrite
from .outredir_cdm_dbg import OutStreamRedirector, OutStreamCollector
from .bp_wp_cdm_dbg import Breakpoint, Watch
from .cdm_dbg_utils import prepareJSONMessage


DEBUG_CLIENT_INSTANCE = None
VAR_TYPE_STRINGS = list(VAR_TYPE_DISP_STRINGS.keys())
DEBUG_CLIENT_ORIG_INPUT = None
DEBUG_CLIENT_ORIG_FORK = None
DEBUG_CLIENT_ORIG_CLOSE = None
DEBUG_CLIENT_ORIG_SET_RECURSION_LIMIT = None


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
        self.__receiveBuffer = ''

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

        self.forkAuto = False
        self.forkChild = False

        self.readstream = None
        self.writestream = None
        self.errorstream = None
        self.pollingDisabled = False

        self.callTraceEnabled = None

        self.variant = 'You should not see this'

        self.compileCommand = codeop.CommandCompiler()

        self.codingRegexp = re.compile(r"coding[:=]\s*([-\w_.]+)")
        self.defaultCoding = 'utf-8'
        self.__coding = self.defaultCoding
        self.noencoding = False

    def getCoding(self):
        """Provides the current coding"""
        return self.__coding

    def __setCoding(self, filename):
        """Sets the coding used by a python file"""
        if self.noencoding:
            self.__coding = sys.getdefaultencoding()
        else:
            default = 'utf-8'
            try:
                f = open(filename, 'rb')
                # read the first and second line
                text = f.readline()
                text = "{0}{1}".format(text, f.readline())
                f.close()
            except IOError:
                self.__coding = default
                return

            for line in text.splitlines():
                match = self.codingRegexp.search(line)
                if match:
                    self.__coding = match.group(1)
                    return
            self.__coding = default

    def input(self, prompt, echo):
        """input() using the event loop"""
        self.sendJSONCommand(
            METHOD_REQUEST_INPUT, {'prompt': prompt, 'echo': echo})
        self.eventLoop(True)
        return self.userInput

    def sessionClose(self, terminate=True):
        """Closes the session with the debugger and optionally terminate"""
        try:
            self.setQuit()
        except:
            pass

        self.debugging = False

        # make sure we close down our end of the socket
        # might be overkill as normally stdin, stdout and stderr
        # SHOULD be closed on exit, but it does not hurt to do it here
        self.readstream.close(True)
        self.writestream.close(True)
        self.errorstream.close(True)

        if terminate:
            # Ok, go away.
            sys.exit()

    def __compileFileSource(self, filename, mode='exec'):
        """Compiles source code read from a file"""
        with codecs.open(filename, encoding=self.__coding) as fp:
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

    def handleLine(self, line):
        """Handles the receipt of a complete line"""
        # Remove any newline
        if line[-1] == '\n':
            line = line[:-1]
        ## printerr(line)
        self.handleJSONCommand(line)

    def handleJSONCommand(self, jsonStr):
        """Handle a command serialized as a JSON string"""
        try:
            commandDict = json.loads(jsonStr.strip())
        except (TypeError, ValueError) as err:
            printerr(str(err))
            return

        method = commandDict['method']
        params = commandDict['params']

        if method == METHOD_REQUEST_VARIABLES:
            self.__dumpVariables(
                params['frameNumber'], params['scope'], params['filters'])

        elif method == METHOD_REQUEST_VARIABLE:
            self.__dumpVariable(
                params['variable'], params['frameNumber'],
                params['scope'], params['filters'])

        elif method == METHOD_REQUEST_THREAD_LIST:
            self.dumpThreadList()

        elif method == METHOD_REQUEST_THREAD_SET:
            if params['threadID'] in self.threads:
                self.setCurrentThread(params['threadID'])
                self.sendJSONCommand(METHOD_RESPONSE_THREAD_SET, {})
                stack = self.currentThread.getStack()
                self.sendJSONCommand(METHOD_RESPONSE_STACK, {'stack': stack})

        elif method == METHOD_REQUEST_BANNER:
            self.sendJSONCommand(
                METHOD_RESPONSE_BANNER,
                {'version': 'Python {0}'.format(sys.version),
                 'platform': socket.gethostname(),
                 'dbgclient': self.variant})

        elif method == METHOD_REQUEST_SET_FILTER:
            self.__generateFilterObjects(params['scope'], params['filter'])

        elif method == METHOD_REQUEST_CALL_TRACE:
            if params['enable']:
                callTraceEnabled = self.profile
            else:
                callTraceEnabled = None

            if self.debugging:
                sys.setprofile(callTraceEnabled)
            else:
                # remember for later
                self.callTraceEnabled = callTraceEnabled

        elif method == METHOD_REQUEST_ENVIRONMENT:
            for key, value in params['environment'].items():
                if key.endswith('+'):
                    if key[:-1] in os.environ:
                        os.environ[key[:-1]] += value
                    else:
                        os.environ[key[:-1]] = value
                else:
                    os.environ[key] = value

        elif method == METHOD_REQUEST_LOAD:
            self._fncache = {}
            self.dircache = []
            sys.argv = []
            self.__setCoding(params['filename'])
            sys.argv.append(params['filename'])
            sys.argv.extend(params['argv'])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params['workdir'] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params['workdir'])

            self.running = sys.argv[0]
            self.debugging = True

            self.forkAuto = params["autofork"]
            self.forkChild = params["forkChild"]

            self.threads.clear()
            self.attachThread(mainThread=True)

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            # clear all old breakpoints, they'll get set after we have
            # started
            Breakpoint.clear_all_breaks()
            Watch.clear_all_watches()

            self.mainThread.tracePythonLibs(params['traceInterpreter'])

            # This will eventually enter a local event loop.
            self.debugMod.__dict__['__file__'] = self.running
            sys.modules['__main__'] = self.debugMod
            code = self.__compileFileSource(self.running)
            if code:
                sys.setprofile(self.callTraceEnabled)
                self.mainThread.run(code, self.debugMod.__dict__, debug=True)

        elif method == METHOD_REQUEST_RUN:
            sys.argv = []
            self.__setCoding(params['filename'])
            sys.argv.append(params['filename'])
            sys.argv.extend(params['argv'])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params['workdir'] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params['workdir'])

            self.running = sys.argv[0]
            self.botframe = None

            self.forkAuto = params['autofork']
            self.forkChild = params['forkChild']

            self.threads.clear()
            self.attachThread(mainThread=True)

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            self.mainThread.tracePythonLibs(False)

            self.debugMod.__dict__['__file__'] = sys.argv[0]
            sys.modules['__main__'] = self.debugMod
            res = 0
            code = self.__compileFileSource(self.running)
            if code:
                self.mainThread.run(code, self.debugMod.__dict__, debug=False)

        elif method == METHOD_REQUEST_COVERAGE:
            from coverage import coverage
            sys.argv = []
            self.__setCoding(params['filename'])
            sys.argv.append(params['filename'])
            sys.argv.extend(params['argv'])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params['workdir'] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params['workdir'])

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            # generate a coverage object
            self.cover = coverage(
                auto_data=True,
                data_file="{0}.coverage".format(
                    os.path.splitext(sys.argv[0])[0]))

            if params['erase']:
                self.cover.erase()
            sys.modules['__main__'] = self.debugMod
            self.debugMod.__dict__['__file__'] = sys.argv[0]
            code = self.__compileFileSource(sys.argv[0])
            if code:
                self.running = sys.argv[0]
                self.cover.start()
                self.mainThread.run(code, self.debugMod.__dict__, debug=False)
                self.cover.stop()
                self.cover.save()

        elif method == METHOD_REQUEST_PROFILE:
            sys.setprofile(None)
            import PyProfile
            sys.argv = []
            self.__setCoding(params['filename'])
            sys.argv.append(params['filename'])
            sys.argv.extend(params['argv'])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params['workdir'] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            # generate a profile object
            self.prof = PyProfile.PyProfile(sys.argv[0])

            if params['erase']:
                self.prof.erase()
            self.debugMod.__dict__['__file__'] = sys.argv[0]
            sys.modules['__main__'] = self.debugMod
            script = ''
            with codecs.open(sys.argv[0], encoding=self.__coding) as fp:
                script = fp.read()
            if script and not script.endswith('\n'):
                script += '\n'

            if script:
                self.running = sys.argv[0]
                res = 0
                try:
                    self.prof.run(script)
                    atexit._run_exitfuncs()
                except SystemExit as exc:
                    res = exc.code
                    atexit._run_exitfuncs()
                except Exception:
                    excinfo = sys.exc_info()
                    self.__unhandled_exception(*excinfo)

                self.prof.save()
                self.progTerminated(res)

        elif method == METHOD_EXECUTE_STATEMENT:
            if self.buffer:
                self.buffer = self.buffer + '\n' + params['statement']
            else:
                self.buffer = params['statement']

            try:
                code = self.compile_command(self.buffer, self.readstream.name)
            except (OverflowError, SyntaxError, ValueError):
                # Report the exception
                sys.last_type, sys.last_value, sys.last_traceback = \
                    sys.exc_info()
                self.sendJSONCommand(
                    METHOD_CLIENT_OUTPUT,
                    {'text': ''.join(traceback.format_exception_only(
                        sys.last_type, sys.last_value))})
                self.buffer = ''
            else:
                if code is None:
                    self.sendJSONCommand(METHOD_RESPONSE_CONTINUE, {})
                    return
                else:
                    self.buffer = ''

                    try:
                        if self.running is None:
                            exec(code, self.debugMod.__dict__)
                        else:
                            if self.currentThread is None:
                                # program has terminated
                                self.running = None
                                _globals = self.debugMod.__dict__
                                _locals = _globals
                            else:
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
                                    _locals = \
                                        self.currentThread.getFrameLocals(
                                            self.framenr)
                            # reset sys.stdout to our redirector
                            # (unconditionally)
                            if 'sys' in _globals:
                                __stdout = _globals['sys'].stdout
                                _globals['sys'].stdout = self.writestream
                                exec(code, _globals, _locals)
                                _globals['sys'].stdout = __stdout
                            elif 'sys' in _locals:
                                __stdout = _locals['sys'].stdout
                                _locals['sys'].stdout = self.writestream
                                exec(code, _globals, _locals)
                                _locals['sys'].stdout = __stdout
                            else:
                                exec(code, _globals, _locals)

                            self.currentThread.storeFrameLocals(self.framenr)
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
                                tlist.insert(
                                    0, '"Traceback (innermost last):\n')
                                tlist.extend(traceback.format_exception_only(
                                    exc_type, exc_value))
                        finally:
                            tblist = exc_tb = None

                        self.sendJSONCommand(
                            METHOD_CLIENT_OUTPUT, {'text': ''.join(tlist)})

            self.sendJSONCommand(METHOD_RESPONSE_OK, {})

        elif method == METHOD_REQUEST_STEP:
            self.currentThreadExec.step(True)
            self.eventExit = True

        elif method == METHOD_REQUEST_STEP_OVER:
            self.currentThreadExec.step(False)
            self.eventExit = True

        elif method == METHOD_REQUEST_STEP_OUT:
            self.currentThreadExec.stepOut()
            self.eventExit = True

        elif method == METHOD_REQUEST_STEP_QUIT:
            if self.passive:
                self.progTerminated(42)
            else:
                self.setQuit()
                self.eventExit = True

        elif method == METHOD_REQUEST_MOVE_IP:
            newLine = params['newLine']
            self.currentThreadExec.move_instruction_pointer(newLine)

        elif method == METHOD_REQUEST_CONTINUE:
            self.currentThreadExec.go(params['special'])
            self.eventExit = True

        elif method == METHOD_USER_INPUT:
            # If we are handling raw mode input then break out of the current
            # event loop.
            self.userInput = params['input']
            self.eventExit = True

        elif method == METHOD_REQUEST_BREAKPOINT:
            if params['setBreakpoint']:
                if params['condition'] in ['None', '']:
                    cond = None
                elif params['condition'] is not None:
                    try:
                        cond = compile(params['condition'], '<string>', 'eval')
                    except SyntaxError:
                        self.sendJSONCommand(
                            METHOD_RESPONSE_BP_CONDITION_ERROR,
                            {'filename': params['filename'],
                             'line': params['line']})
                        return
                else:
                    cond = None

                Breakpoint(params['filename'], params['line'],
                           params['temporary'], cond)
            else:
                Breakpoint.clear_break(params['filename'], params['line'])

        elif method == METHOD_REQUEST_BP_ENABLE:
            bp = Breakpoint.get_break(params['filename'], params['line'])
            if bp is not None:
                if params['enable']:
                    bp.enable()
                else:
                    bp.disable()

        elif method == METHOD_REQUEST_BP_IGNORE:
            bp = Breakpoint.get_break(params['filename'], params['line'])
            if bp is not None:
                bp.ignore = params['count']

        elif method == METHOD_REQUEST_WATCH:
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
                    self.sendJSONCommand(
                        METHOD_RESPONSE_WATCH_CONDITION_ERROR,
                        {'condition': params['condition']})
                    return
                Watch(params['condition'], compiledCond, flag,
                      params['temporary'])
            else:
                Watch.clear_watch(params['condition'])

        elif method == METHOD_REQUEST_WATCH_ENABLE:
            wp = Watch.get_watch(params['condition'])
            if wp is not None:
                if params['enable']:
                    wp.enable()
                else:
                    wp.disable()

        elif method == METHOD_REQUEST_WATCH_IGNORE:
            wp = Watch.get_watch(params['condition'])
            if wp is not None:
                wp.ignore = params['count']

        elif method == METHOD_REQUEST_SHUTDOWN:
            self.sessionClose()

        elif method == METHOD_REQUEST_COMPLETION:
            self.__completionList(params['text'])

        elif method == METHOD_RESPONSE_FORK_TO:
            # this results from a separate event loop
            self.fork_child = (params['target'] == 'child')
            self.eventExit = True

    def sendJSONCommand(self, method, params):
        """Sends a single command or response to the IDE"""
        cmd = prepareJSONMessage(method, params)

        self.writestream.write_p(cmd)
        self.writestream.flush()

    def sendClearTemporaryBreakpoint(self, filename, lineno):
        """Signals the deletion of a temporary breakpoint"""
        self.sendJSONCommand(
            METHOD_RESPONSE_CLEAR_BP,
            {'filename': filename, 'line': lineno})

    def sendClearTemporaryWatch(self, condition):
        """Signals the deletion of a temporary watch expression"""
        self.sendJSONCommand(
            METHOD_RESPONSE_CLEAR_WATCH, {'condition': condition})

    def sendResponseLine(self, stack):
        """Sends the current call stack"""
        self.sendJSONCommand(
            METHOD_RESPONSE_LINE, {'stack': stack})

    def sendCallTrace(self, event, fromInfo, toInfo):
        """Sends a call trace entry"""
        self.sendJSONCommand(
            METHOD_CALL_TRACE,
            {'event': event[0], 'from': fromInfo, 'to': toInfo})

    def sendException(self, exceptionType, exceptionMessage, stack):
        """Sends information for an exception"""
        self.sendJSONCommand(
            METHOD_RESPONSE_EXCEPTION,
            {'type': exceptionType, 'message': exceptionMessage,
             'stack': stack})

    def sendSyntaxError(self, message, filename, lineno, charno):
        """Sends information for a syntax error"""
        self.sendJSONCommand(
            METHOD_RESPONSE_SYNTAX,
            {'message': message, 'filename': filename,
             'linenumber': lineno, 'characternumber': charno})

    def sendPassiveStartup(self, filename, exceptions):
        """Sends the passive start information"""
        self.sendJSONCommand(
            METHOD_PASSIVE_STARTUP,
            {'filename': filename, 'exceptions': exceptions})

    def readReady(self, stream):
        """Called when there is data ready to be read"""
        try:
            got = stream.readline_p()
        except Exception:
            return

        if len(got) == 0:
            self.sessionClose()
            return

        self.__receiveBuffer = self.__receiveBuffer + got

        # Call handleLine for the line if it is complete
        eol = self.__receiveBuffer.find('\n')
        while eol >= 0:
            line = self.__receiveBuffer[:eol + 1]
            self.__receiveBuffer = self.__receiveBuffer[eol + 1:]
            self.handleLine(line)
            eol = self.__receiveBuffer.find('\n')

    def writeReady(self, stream):
        """Called when we are ready to write data"""
        stream.write_p('')
        stream.flush()

    def __interact(self):
        """Interacts with the debugger"""
        global DebugClientInstance

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
            wrdy = []

            if self.writestream.nWriteErrors > self.writestream.maxtries:
                break

            if AsyncPendingWrite(self.writestream):
                wrdy.append(self.writestream)

            if AsyncPendingWrite(self.errorstream):
                wrdy.append(self.errorstream)

            try:
                rrdy, wrdy, xrdy = select.select([self.readstream], wrdy, [])
            except (select.error, KeyboardInterrupt, socket.error):
                # just carry on
                continue

            if self.readstream in rrdy:
                self.readReady(self.readstream)

            if self.writestream in wrdy:
                self.writeReady(self.writestream)

            if self.errorstream in wrdy:
                self.writeReady(self.errorstream)

        self.eventExit = None
        self.pollingDisabled = False

    def eventPoll(self):
        """Polls for events like 'set break point'"""
        if self.pollingDisabled:
            return

        wrdy = []
        if AsyncPendingWrite(self.writestream):
            wrdy.append(self.writestream)

        if AsyncPendingWrite(self.errorstream):
            wrdy.append(self.errorstream)

        # Immediate return if nothing is ready
        try:
            rrdy, wrdy, xrdy = select.select([self.readstream], wrdy, [], 0)
        except (select.error, KeyboardInterrupt, socket.error):
            return

        if self.readstream in rrdy:
            self.readReady(self.readstream)

        if self.writestream in wrdy:
            self.writeReady(self.writestream)

        if self.errorstream in wrdy:
            self.writeReady(self.errorstream)

    def connectDebugger(self, port, remoteAddress=None, redirect=True):
        """Establishes a session with the debugger"""
        if remoteAddress is None:
            remoteAddress = DEBUG_ADDRESS
        elif "@@i" in remoteAddress:
            remoteAddress = remoteAddress.split("@@i")[0]
        sock = socket.create_connection((remoteAddress, port))

        self.readstream = AsyncFile(sock, sys.stdin.mode, sys.stdin.name)
        self.writestream = AsyncFile(sock, sys.stdout.mode, sys.stdout.name)
        self.errorstream = AsyncFile(sock, sys.stderr.mode, sys.stderr.name)

        if redirect:
            sys.stdout = OutStreamRedirector(sock, True)
            sys.stderr = OutStreamRedirector(sock, False)
            sys.stdin = self.readstream
        self.redirect = redirect

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

        filename = self.absPath(stackFrame)

        linenr = stackFrame.f_lineno
        ffunc = stackFrame.f_code.co_name

        if ffunc == '?':
            ffunc = ''

        if ffunc and not ffunc.startswith('<'):
            argInfo = getargvalues(stackFrame)
            try:
                fargs = formatargvalues(
                    argInfo.args, argInfo.varargs,
                    argInfo.keywords, argInfo.locals)
            except Exception:
                fargs = ''
        else:
            fargs = ''

        self.sendJSONCommand(
            METHOD_RESPONSE_SIGNAL,
            {'message': message, 'filename': filename, 'linenumber': linenr,
             'function': ffunc, 'arguments': fargs})

    def absPath(self, fn):
        """Converts a filename to an absolute name"""
        if os.path.isabs(fn):
            if sys.version_info[0] == 2:
                fn = fn.decode(sys.getfilesystemencoding())

            return fn

        # Check the cache
        if fn in self._fncache:
            return self._fncache[fn]

        # Search sys.path
        for p in sys.path:
            afn = os.path.abspath(os.path.join(p, fn))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                if sys.version_info[0] == 2:
                    afn = afn.decode(sys.getfilesystemencoding())

                self._fncache[fn] = afn
                d = os.path.dirname(afn)
                if (d not in sys.path) and (d not in self.dircache):
                    self.dircache.append(d)
                return afn

        # Search the additional directory cache
        for p in self.dircache:
            afn = os.path.abspath(os.path.join(p, fn))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                self._fncache[fn] = afn
                return afn

        # Nothing found
        return fn

    def getRunning(self):
        """True if the main script we are currently running"""
        return self.running

    def progTerminated(self, status, message=''):
        """Tells the debugger that the program has terminated"""
        if status is None:
            status = 0
        elif not isinstance(status, int):
            message = str(status)
            status = 1

        if self.running:
            self.setQuit()
            self.running = None
            self.sendJsonCommand(
                METHOD_RESPONSE_EXIT, {'status': status, 'message': message})

        # reset coding
        self.__coding = self.defaultCoding

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

        self.sendJSONCommand(
            METHOD_RESPONSE_VARIABLES, {'scope': scope, 'variables': varlist})

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
                typeObject, typeName, typeStr, resolver = \
                    DebugVariables.getType(variable)
                if resolver:
                    variable = resolver.resolve(variable, attribute)
                    if variable is None:
                        break
                else:
                    break

            if variable is not None:
                typeObject, typeName, typeStr, resolver = \
                    DebugVariables.getType(variable)
                if typeStr.startswith(('PyQt5.', 'PyQt4.')):
                    vlist = self.__formatQtVariable(variable, typeName)
                    varlist.extend(vlist)
                elif resolver:
                    varDict = resolver.getDictionary(variable)
                    vlist = self.__formatVariablesList(
                        list(varDict.keys()), varDict, scope, filterList)
                    varlist.extend(vlist)

        self.sendJSONCommand(
            METHOD_RESPONSE_VARIABLE,
            {'scope': scope, 'variable': var, 'variables': varlist})

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
            r, g, b, a = value.getRgb()
            varlist.append(
                ('rgba', 'int',
                 '{0:d}, {1:d}, {2:d}, {3:d}'.format(r, g, b, a)))
            h, s, v, a = value.getHsv()
            varlist.append(
                ('hsva', 'int',
                 '{0:d}, {1:d}, {2:d}, {3:d}'.format(h, s, v, a)))
            c, m, y, k, a = value.getCmyk()
            varlist.append(
                ('cmyka', 'int',
                 '{0:d}, {1:d}, {2:d}, {3:d}, {4:d}'.format(c, m, y, k, a)))
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
                    DebugVariables.TooLargeAttribute in keylist):
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
                        elif valtype == sip.methoddescriptor:
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

    def __completionList(self, text):
        """Handles the request for a commandline completion list"""
        completerDelims = ' \t\n`~!@#$%^&*()-=+[{]}\\|;:\'",<>/?'

        completions = set()
        # find position of last delim character
        pos = -1
        while pos >= -len(text):
            if text[pos] in completerDelims:
                if pos == -1:
                    text = ''
                else:
                    text = text[pos + 1:]
                break
            pos -= 1

        # Get local and global completions
        try:
            localdict = self.currentThread.getFrameLocals(self.framenr)
            localCompleter = Completer(localdict).complete
            self.__getCompletionList(text, localCompleter, completions)
        except AttributeError:
            pass

        cf = self.currentThread.getCurrentFrame()
        frmnr = self.framenr
        while cf is not None and frmnr > 0:
            cf = cf.f_back
            frmnr -= 1

        if cf is None:
            globaldict = self.debugMod.__dict__
        else:
            globaldict = cf.f_globals

        globalCompleter = Completer(globaldict).complete
        self.__getCompletionList(text, globalCompleter, completions)

        self.sendJSONCommand(
            METHOD_RESPONSE_COMPLETION,
            {'completions': list(completions), 'text': text})

    def __getCompletionList(self, text, completer, completions):
        """Creates a completions list"""
        state = 0
        try:
            comp = completer(text, state)
        except Exception:
            comp = None
        while comp is not None:
            completions.add(comp)
            state += 1
            try:
                comp = completer(text, state)
            except Exception:
                comp = None

    def startProgInDebugger(self, progargs, wd, host,
                            port, exceptions=True, tracePython=False,
                            redirect=True):
        """Starts the remote debugger"""
        remoteAddress = self.__resolveHost(host)
        self.connectDebugger(port, remoteAddress, redirect)

        self._fncache = {}
        self.dircache = []
        sys.argv = progargs[:]
        sys.argv[0] = os.path.abspath(sys.argv[0])
        sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
        if wd == '':
            os.chdir(sys.path[1])
        else:
            os.chdir(wd)
        self.running = sys.argv[0]
        self.__setCoding(self.running)
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
        res = self.mainThread.run(
            'exec(open(' + repr(self.running) + ').read())',
            self.debugMod.__dict__)
        self.progTerminated(res)

    @staticmethod
    def __resolveHost(host):
        """resolve a hostname to an IP address"""
        try:
            host, version = host.split('@@')
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
            wdir = ''
            tracePython = False
            exceptions = True
            redirect = True
            while args[0]:
                if args[0] == '-h':
                    host = args[1]
                    del args[0]
                    del args[0]
                elif args[0] == '-p':
                    port = int(args[1])
                    del args[0]
                    del args[0]
                elif args[0] == '-w':
                    wdir = args[1]
                    del args[0]
                    del args[0]
                elif args[0] == '-t':
                    tracePython = True
                    del args[0]
                elif args[0] == '-e':
                    exceptions = False
                    del args[0]
                elif args[0] == '-n':
                    redirect = False
                    del args[0]
                elif args[0] == '--no-encoding':
                    self.noencoding = True
                    del args[0]
                elif args[0] == '--fork-child':
                    self.forkAuto = True
                    self.forkChild = True
                    del args[0]
                elif args[0] == '--fork-parent':
                    self.forkAuto = True
                    self.forkChild = False
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
                if not self.noencoding:
                    self.__coding = self.defaultCoding
                self.startProgInDebugger(args, wdir, host, port,
                                         exceptions=exceptions,
                                         tracePython=tracePython,
                                         redirect=redirect)
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
            self.sendJSONCommand(METHOD_REQUEST_FORK_TO, {})
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

           It prevents the debugger connections from being closed"""
        if fdescriptor not in [self.readstream.fileno(),
                               self.writestream.fileno(),
                               self.errorstream.fileno()]:
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
