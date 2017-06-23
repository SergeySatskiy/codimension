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
import traceback
import os
import time
import imp
import re
from .protocol_cdm_dbg import (ResponseOK, RequestOK, RequestVariable,
                               RequestThreadList, RequestThreadSet, RequestStack,
                               ResponseThreadSet, RequestVariables, ResponseStack,
                               RequestStep, RequestStepOver, RequestStepOut,
                               RequestStepQuit, RequestShutdown, RequestBreak,
                               ResponseThreadList, ResponseException,
                               RequestContinue, RequestBreakIgnore, RequestEval,
                               RequestBreakEnable, RequestWatch, ResponseRaw,
                               RequestForkTo, ResponseBPConditionError,
                               ResponseWPConditionError, RequestWatchEnable,
                               RequestWatchIgnore, RequestExec,
                               ResponseForkTo, ResponseContinue, ResponseExit,
                               ResponseVariables, DebugAddress,
                               ResponseVariable, PassiveStartup,
                               ResponseEval, ResponseEvalOK, ResponseEvalError,
                               ResponseExec, ResponseExecOK, ResponseExecError)
from .base_cdm_dbg import setRecursionLimit
from .asyncfile_cdm_dbg import AsyncFile, AsyncPendingWrite
from .outredir_cdm_dbg import OutStreamRedirector, OutStreamCollector


DEBUG_CLIENT_INSTANCE = None


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
    Indicators = ['()', '[]', '{:}', '{}']

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
        self.passive = None     # used to indicate the passive mode
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

    def rawInput(self, prompt, echo):
        """raw_input() / input() using the event loop"""
        self.sendJsonCommand(
            METHOD_REQUEST_RAW, {'prompt': prompt, 'echo': echo})
        self.eventLoop(True)
        return self.rawLine

    def input(self, prompt):
        """input() (Python 2) using the event loop"""
        return eval(self.rawInput(prompt, True))

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
        self.handleJsonCommand(line)

    def handleJsonCommand(self, jsonStr):
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
                self.sendJsonCommand(METHOD_RESPONSE_THREAD_SET, {})
                stack = self.currentThread.getStack()
                self.sendJsonCommand(METHOD_RESPONSE_STACK, {'stack': stack})

        elif method == METHOD_REQUEST_BANNER:
            self.sendJsonCommand(
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

        elif method == "RequestLoad":
            self._fncache = {}
            self.dircache = []
            sys.argv = []
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            self.running = sys.argv[0]
            self.debugging = True

            self.fork_auto = params["autofork"]
            self.fork_child = params["forkChild"]

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

            self.mainThread.tracePythonLibs(params["traceInterpreter"])

            # This will eventually enter a local event loop.
            self.debugMod.__dict__['__file__'] = self.running
            sys.modules['__main__'] = self.debugMod
            code = self.__compileFileSource(self.running)
            if code:
                sys.setprofile(self.callTraceEnabled)
                self.mainThread.run(code, self.debugMod.__dict__, debug=True)

        elif method == "RequestRun":
            sys.argv = []
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            self.running = sys.argv[0]
            self.botframe = None
            
            self.fork_auto = params["autofork"]
            self.fork_child = params["forkChild"]
            
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

        elif method == "RequestCoverage":
            from coverage import coverage
            sys.argv = []
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])
            
            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()
            
            # generate a coverage object
            self.cover = coverage(
                auto_data=True,
                data_file="{0}.coverage".format(
                    os.path.splitext(sys.argv[0])[0]))
            
            if params["erase"]:
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
        
        elif method == "RequestProfile":
            sys.setprofile(None)
            import PyProfile
            sys.argv = []
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == '':
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()
            
            # generate a profile object
            self.prof = PyProfile.PyProfile(sys.argv[0])
            
            if params["erase"]:
                self.prof.erase()
            self.debugMod.__dict__['__file__'] = sys.argv[0]
            sys.modules['__main__'] = self.debugMod
            script = ''
            if sys.version_info[0] == 2:
                script = 'execfile({0!r})'.format(sys.argv[0])
            else:
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
        
        elif method == "ExecuteStatement":
            if self.buffer:
                self.buffer = self.buffer + '\n' + params["statement"]
            else:
                self.buffer = params["statement"]

            try:
                code = self.compile_command(self.buffer, self.readstream.name)
            except (OverflowError, SyntaxError, ValueError):
                # Report the exception
                sys.last_type, sys.last_value, sys.last_traceback = \
                    sys.exc_info()
                self.sendJsonCommand("ClientOutput", {
                    "text": "".join(traceback.format_exception_only(
                        sys.last_type, sys.last_value))
                })
                self.buffer = ''
            else:
                if code is None:
                    self.sendJsonCommand("ResponseContinue", {})
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
                            if "sys" in _globals:
                                __stdout = _globals["sys"].stdout
                                _globals["sys"].stdout = self.writestream
                                exec(code, _globals, _locals)
                                _globals["sys"].stdout = __stdout
                            elif "sys" in _locals:
                                __stdout = _locals["sys"].stdout
                                _locals["sys"].stdout = self.writestream
                                exec(code, _globals, _locals)
                                _locals["sys"].stdout = __stdout
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
                                    0, "Traceback (innermost last):\n")
                                tlist.extend(traceback.format_exception_only(
                                    exc_type, exc_value))
                        finally:
                            tblist = exc_tb = None

                        self.sendJsonCommand("ClientOutput", {
                            "text": "".join(tlist)
                        })
            
            self.sendJsonCommand("ResponseOK", {})
        
        elif method == "RequestStep":
            self.currentThreadExec.step(True)
            self.eventExit = True

        elif method == "RequestStepOver":
            self.currentThreadExec.step(False)
            self.eventExit = True
        
        elif method == "RequestStepOut":
            self.currentThreadExec.stepOut()
            self.eventExit = True
        
        elif method == "RequestStepQuit":
            if self.passive:
                self.progTerminated(42)
            else:
                self.set_quit()
                self.eventExit = True
        
        elif method == "RequestMoveIP":
            newLine = params["newLine"]
            self.currentThreadExec.move_instruction_pointer(newLine)
        
        elif method == "RequestContinue":
            self.currentThreadExec.go(params["special"])
            self.eventExit = True
        
        elif method == "RawInput":
            # If we are handling raw mode input then break out of the current
            # event loop.
            self.rawLine = params["input"]
            self.eventExit = True
        
        elif method == "RequestBreakpoint":
            if params["setBreakpoint"]:
                if params["condition"] in ['None', '']:
                    cond = None
                elif params["condition"] is not None:
                    try:
                        cond = compile(params["condition"], '<string>', 'eval')
                    except SyntaxError:
                        self.sendJsonCommand("ResponseBPConditionError", {
                            "filename": params["filename"],
                            "line": params["line"],
                        })
                        return
                else:
                    cond = None
                
                Breakpoint(
                    params["filename"], params["line"], params["temporary"],
                    cond)
            else:
                Breakpoint.clear_break(params["filename"], params["line"])
        
        elif method == "RequestBreakpointEnable":
            bp = Breakpoint.get_break(params["filename"], params["line"])
            if bp is not None:
                if params["enable"]:
                    bp.enable()
                else:
                    bp.disable()
        
        elif method == "RequestBreakpointIgnore":
            bp = Breakpoint.get_break(params["filename"], params["line"])
            if bp is not None:
                bp.ignore = params["count"]
        
        elif method == "RequestWatch":
            if params["setWatch"]:
                if params["condition"].endswith(
                        ('??created??', '??changed??')):
                    compiledCond, flag = params["condition"].split()
                else:
                    compiledCond = params["condition"]
                    flag = ''
                
                try:
                    compiledCond = compile(compiledCond, '<string>', 'eval')
                except SyntaxError:
                    self.sendJsonCommand("ResponseWatchConditionError", {
                        "condition": params["condition"],
                    })
                    return
                Watch(
                    params["condition"], compiledCond, flag,
                    params["temporary"])
            else:
                Watch.clear_watch(params["condition"])
        
        elif method == "RequestWatchEnable":
            wp = Watch.get_watch(params["condition"])
            if wp is not None:
                if params["enable"]:
                    wp.enable()
                else:
                    wp.disable()
        
        elif method == "RequestWatchIgnore":
            wp = Watch.get_watch(params["condition"])
            if wp is not None:
                wp.ignore = params["count"]
        
        elif method == "RequestShutdown":
            self.sessionClose()
        
        elif method == "RequestCompletion":
            self.__completionList(params["text"])
        
        elif method == "RequestUTPrepare":
            sys.path.insert(
                0, os.path.dirname(os.path.abspath(params["filename"])))
            os.chdir(sys.path[0])
            
            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()
            
            try:
                import unittest
                utModule = imp.load_source(
                    params["testname"], params["filename"])
                try:
                    if params["failed"]:
                        self.test = unittest.defaultTestLoader\
                            .loadTestsFromNames(params["failed"], utModule)
                    else:
                        self.test = unittest.defaultTestLoader\
                            .loadTestsFromName(params["testfunctionname"],
                                               utModule)
                except AttributeError:
                    self.test = unittest.defaultTestLoader\
                        .loadTestsFromModule(utModule)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.sendJsonCommand("ResponseUTPrepared", {
                    "count": 0,
                    "exception": exc_type.__name__,
                    "message": str(exc_value),
                })
                return
            
            # generate a coverage object
            if params["coverage"]:
                from coverage import coverage
                self.cover = coverage(
                    auto_data=True,
                    data_file="{0}.coverage".format(
                        os.path.splitext(params["coveragefile"])[0]))
                if params["coverageerase"]:
                    self.cover.erase()
            else:
                self.cover = None
            
            self.sendJsonCommand("ResponseUTPrepared", {
                "count": self.test.countTestCases(),
                "exception": "",
                "message": "",
            })
        
        elif method == "RequestUTRun":
            from DCTestResult import DCTestResult
            self.testResult = DCTestResult(self)
            if self.cover:
                self.cover.start()
            self.test.run(self.testResult)
            if self.cover:
                self.cover.stop()
                self.cover.save()
            self.sendJsonCommand("ResponseUTFinished", {})
        
        elif method == "RequestUTStop":
            self.testResult.stop()
        
        elif method == "ResponseForkTo":
            # this results from a separate event loop
            self.fork_child = (params["target"] == 'child')
            self.eventExit = True











    def attachThread(self, target=None, args=None,
                     kwargs=None, mainThread=0):
        """Public method to setup a thread for DebugClient to debug.

           If mainThread is non-zero, then we are attaching to the already
           started mainthread of the app and the rest of the args are ignored.

           This is just an empty function and is overridden in the threaded
           debugger."""
        if self.debugging:
            sys.setprofile(self.profile)

    def __dumpThreadList(self):
        """Sends the list of threads"""
        threadList = []
        if self.threads and self.currentThread:     # indication for the
                                                    # threaded debugger
            currentId = self.currentThread.get_ident()
            for thr in self.threads.values():
                dmp = {}
                dmp["id"] = thr.get_ident()
                dmp["name"] = thr.get_name()
                dmp["broken"] = thr.isBroken()
                threadList.append(dmp)
        else:
            currentId = -1
            dmp = {}
            dmp["id"] = -1
            dmp["name"] = "MainThread"
            dmp["broken"] = self.isBroken()
            threadList.append(dmp)

        self.write('%s%s' % (ResponseThreadList,
                             (currentId, threadList)))

    def __exceptionRaised(self):
        """Called in the case of an exception
           It ensures that the debug server is informed of the raised
           exception"""
        self.pendingResponse = ResponseException


    def write(self, msg):
        """Public method to write data to the output stream"""
        self.writestream.write(msg)
        self.writestream.flush()

    def __interact(self):
        """Interact with the debugger"""
        global DEBUG_CLIENT_INSTANCE

        self.setDescriptors(self.readstream, self.writestream)
        DEBUG_CLIENT_INSTANCE = self

        if not self.passive:
            # At this point simulate an event loop.
            self.eventLoop()

    def eventLoop(self, disablePolling=False):
        """our event loop"""
        self.eventExit = None
        self.pollingDisabled = disablePolling

        while self.eventExit is None:
            wrdy = []

            if AsyncPendingWrite(self.writestream):
                wrdy.append(self.writestream)

            if AsyncPendingWrite(self.errorstream):
                wrdy.append(self.errorstream)

            try:
                rrdy, wrdy, xrdy = select.select([self.readstream],
                                                 wrdy, [])
            except (select.error, KeyboardInterrupt, socket.error):
                # just carry on
                continue

            if self.readstream in rrdy:
                self.readReady(self.readstream.fileno())

            if self.writestream in wrdy:
                self.writeReady(self.writestream.fileno())

            if self.errorstream in wrdy:
                self.writeReady(self.errorstream.fileno())

        self.eventExit = None
        self.pollingDisabled = False

    def eventPoll(self):
        """poll for events like 'set break point'"""
        if self.pollingDisabled:
            return

        # the choice of a ~0.5 second poll interval is arbitrary.
        lasteventpolltime = getattr(self, 'lasteventpolltime', time.time())
        now = time.time()
        if now - lasteventpolltime < 0.5:
            self.lasteventpolltime = lasteventpolltime
            return

        self.lasteventpolltime = now

        wrdy = []
        if AsyncPendingWrite(self.writestream):
            wrdy.append(self.writestream)

        if AsyncPendingWrite(self.errorstream):
            wrdy.append(self.errorstream)

        # immediate return if nothing is ready.
        try:
            rrdy, wrdy, xrdy = select.select([self.readstream],
                                             wrdy, [], 0)
        except (select.error, KeyboardInterrupt, socket.error):
            return

        if self.readstream in rrdy:
            self.readReady(self.readstream.fileno())

        if self.writestream in wrdy:
            self.writeReady(self.writestream.fileno())

        if self.errorstream in wrdy:
            self.writeReady(self.errorstream.fileno())

    def connectDebugger(self, port, remoteAddress=None, redirect=True):
        """Establishes a session with the debugger.

        It opens a network connection to the debugger, connects it to stdin,
        stdout and stderr and saves these file objects in case the application
        being debugged redirects them itself"""
        if remoteAddress is None:                    # default: 127.0.0.1
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((DebugAddress, port))
        else:
            if "@@i" in remoteAddress:
                remoteAddress, index = remoteAddress.split("@@i")
            else:
                index = 0
            if ":" in remoteAddress:                              # IPv6
                sockaddr = socket.getaddrinfo(remoteAddress, port, 0, 0,
                                              socket.SOL_TCP)[0][-1]
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sockaddr = sockaddr[:-1] + (int(index), )
                sock.connect(sockaddr)
            else:                                                   # IPv4
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((remoteAddress, port))

        self.readstream = AsyncFile(sock, sys.stdin.mode, sys.stdin.name)
        self.writestream = AsyncFile(sock, sys.stdout.mode, sys.stdout.name)
        self.errorstream = AsyncFile(sock, sys.stderr.mode, sys.stderr.name)

        if redirect:
            sys.stdout = OutStreamRedirector(sock, True)
            sys.stderr = OutStreamRedirector(sock, False)
            sys.stdin = self.readstream
        self.redirect = redirect

        # attach to the main thread here
        self.attachThread(mainThread=True)

    def __unhandled_exception(self, exctype, excval, exctb):
        """called to report an uncaught exception"""
        self.mainThread.user_exception(None, (exctype, excval, exctb), 1)

    def absPath(self, fname):
        """convert a filename to an absolute name.

           sys.path is used as a set of possible prefixes. The name stays
           relative if a file could not be found"""
        if os.path.isabs(fname):
            return fname

        # Check the cache.
        if fname in self._fncache:
            return self._fncache[fname]

        # Search sys.path.
        for path in sys.path:
            afn = os.path.abspath(os.path.join(path, fname))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                self._fncache[fname] = afn
                dname = os.path.dirname(afn)
                if (dname not in sys.path) and (dname not in self.dircache):
                    self.dircache.append(dname)
                return afn

        # Search the additional directory cache
        for path in self.dircache:
            afn = os.path.abspath(os.path.join(path, fname))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                self._fncache[fname] = afn
                return afn

        # Nothing found
        return fname

    def shouldSkip(self, fname):
        """check if a file should be skipped"""
        if self.mainThread.tracePython:     # trace into Python library
            return 0

        # Eliminate anything that is part of the Python installation.
        afn = self.absPath(fname)
        for dname in self.skipdirs:
            if afn.startswith(dname):
                return True
        return False

    def getRunning(self):
        """True if the main script we are currently running"""
        return self.running

    def progTerminated(self, status):
        """tell the debugger that the program has terminated"""
        if status is None:
            status = 0
        else:
            try:
                int(status)
            except ValueError:
                status = 1

        if self.running:
            self.set_quit()
            self.running = None
            self.write('%s%d' % (ResponseExit, status))

        # reset coding
        self.__coding = self.defaultCoding

    def __dumpVariables(self, frmnr, scope):
        """return the variables of a frame to the debug server"""
        if self.currentThread is None:
            # It rather happens while debugging multithreaded scripts.
            # If nothing was sent then the variable window holds another
            # thread variables which is wrong. It's better to send an empty
            # list to avoid confusion.
            varlist = [scope]
            self.write('%s%s' % (ResponseVariables, varlist))
            return

        # The original version did not change the frame number for the global
        # scope. It had to be changed because the global scope could also be
        # different for different frames, e.g. __file__ for different files.
        # So, change the frame unconditionally
        self.framenr = frmnr

        f = self.currentThread.getCurrentFrame()

        while f is not None and frmnr > 0:
            f = f.f_back
            frmnr -= 1

        if f is None:
            # It rather happens while debugging multithreaded scripts.
            # If nothing was sent then the variable window holds another
            # thread variables which is wrong. It's better to send an empty
            # list to avoid confusion.
            varlist = [scope]
            self.write('%s%s' % (ResponseVariables, varlist))
            return

        if scope:
            varDict = f.f_globals
        else:
            varDict = f.f_locals

            if f.f_globals is f.f_locals:
                scope = -1

        varlist = [scope]

        if scope != -1:
            keylist = varDict.keys()

            vlist = self.__formatVariablesList(keylist, varDict, scope)
            varlist.extend(vlist)

        self.write('%s%s' % (ResponseVariables, varlist))

    def __dumpVariable(self, var, frmnr, scope):
        """return the variables of a frame to the debug server"""
        if self.currentThread is None:
            return

        f = self.currentThread.getCurrentFrame()

        while f is not None and frmnr > 0:
            f = f.f_back
            frmnr -= 1

        if f is None:
            return

        if scope:
            dict = f.f_globals
        else:
            dict = f.f_locals

            if f.f_globals is f.f_locals:
                scope = -1

        varlist = [scope, var]

        if scope != -1:
            # search the correct dictionary
            i = 0
            rvar = var[:]
            dictkeys = None
            obj = None
            isDict = 0
            formatSequences = 0
            access = ""
            oaccess = ""
            odict = dict

            qtVariable = False
            qvar = None
            qvtype = ""

            while i < len(var):
                if len(dict):
                    udict = dict
                ndict = {}
                # this has to be in line with VariablesViewer.indicators
                if var[i][-2:] in ["[]", "()", "{}"]:
                    if i + 1 == len(var):
                        if var[i][:-2] == '...':
                            dictkeys = [var[i - 1]]
                        else:
                            dictkeys = [var[i][:-2]]
                        formatSequences = 1
                        if not access and not oaccess:
                            if var[i][:-2] == '...':
                                access = '["%s"]' % var[i-1]
                                dict = odict
                            else:
                                access = '["%s"]' % var[i][:-2]
                        else:
                            if var[i][:-2] == '...':
                                if oaccess:
                                    access = oaccess
                                else:
                                    access = '%s[%s]' % (access, var[i-1])
                                dict = odict
                            else:
                                if oaccess:
                                    access = '%s[%s]' % (oaccess, var[i][:-2])
                                    oaccess = ''
                                else:
                                    access = '%s[%s]' % (access, var[i][:-2])
                        if var[i][-2:] == "{}":
                            isDict = 1
                        break
                    else:
                        if not access:
                            if var[i][:-2] == '...':
                                access = '["%s"]' % var[i-1]
                                dict = odict
                            else:
                                access = '["%s"]' % var[i][:-2]
                        else:
                            if var[i][:-2] == '...':
                                access = '%s[%s]' % (access, var[i-1])
                                dict = odict
                            else:
                                if oaccess:
                                    access = '%s[%s]' % (oaccess, var[i][:-2])
                                    oaccess = ''
                                else:
                                    access = '%s[%s]' % (access, var[i][:-2])
                else:
                    if access:
                        if oaccess:
                            access = '%s[%s]' % (oaccess, var[i])
                        else:
                            access = '%s[%s]' % (access, var[i])
                        if var[i-1][:-2] == '...':
                            oaccess = access
                        else:
                            oaccess = ''
                        try:
                            exec('mdict = dict%s.__dict__' % access)
                            ndict.update(mdict)
                            exec('obj = dict%s' % access)
                            if "PyQt4." in str(type(obj)):
                                qtVariable = True
                                qvar = obj
                                qvtype = ("%s" % type(qvar))[1:-1]. \
                                                     split()[1][1:-1]
                        except:
                            pass
                        try:
                            exec('mcdict = dict%s.__class__.__dict__' % access)
                            ndict.update(mcdict)
                            if mdict and not "sipThis" in mdict.keys():
                                del rvar[0:2]
                                access = ""
                        except:
                            pass
                        try:
                            cdict = {}
                            exec('slv = dict%s.__slots__' % access)
                            for v in slv:
                                try:
                                    exec('cdict[v] = dict%s.%s' % (access, v))
                                except:
                                    pass
                            ndict.update(cdict)
                            exec('obj = dict%s' % access)
                            access = ""
                            if "PyQt4." in str(type(obj)):
                                qtVariable = True
                                qvar = obj
                                qvtype = ("%s" % type(qvar))[1:-1]. \
                                                     split()[1][1:-1]
                        except:
                            pass
                    else:
                        try:
                            ndict.update(dict[var[i]].__dict__)
                            ndict.update(dict[var[i]].__class__.__dict__)
                            del rvar[0]
                            obj = dict[var[i]]
                            if "PyQt4." in str(type(obj)):
                                qtVariable = True
                                qvar = obj
                                qvtype = ("%s" % type(qvar))[1:-1]. \
                                                     split()[1][1:-1]
                        except:
                            pass
                        try:
                            cdict = {}
                            slv = dict[var[i]].__slots__
                            for v in slv:
                                try:
                                    exec('cdict[v] = dict[var[i]].%s' % v)
                                except:
                                    pass
                            ndict.update(cdict)
                            obj = dict[var[i]]
                            if "PyQt4." in str(type(obj)):
                                qtVariable = True
                                qvar = obj
                                qvtype = ("%s" % type(qvar))[1:-1]. \
                                                     split()[1][1:-1]
                        except:
                            pass
                    odict = dict
                    dict = ndict
                i += 1

            if qtVariable:
                vlist = self.__formatQt4Variable(qvar, qvtype)
            elif ("sipThis" in dict.keys() and len(dict) == 1) or \
               (len(dict) == 0 and len(udict) > 0):
                if access:
                    exec('qvar = udict%s' % access)
                # this has to be in line with VariablesViewer.indicators
                elif rvar and rvar[0][-2:] in ["[]", "()", "{}"]:
                    exec('qvar = udict["%s"][%s]' % (rvar[0][:-2], rvar[1]))
                else:
                    qvar = udict[var[-1]]
                qvtype = ("%s" % type(qvar))[1:-1].split()[1][1:-1]
                if qvtype.startswith("PyQt4"):
                    vlist = self.__formatQt4Variable(qvar, qvtype)
                else:
                    vlist = []
            else:
                qtVariable = False
                if len(dict) == 0 and len(udict) > 0:
                    if access:
                        exec('qvar = udict%s' % access)
                    # this has to be in line with VariablesViewer.indicators
                    elif rvar and rvar[0][-2:] in ["[]", "()", "{}"]:
                        exec('qvar = udict["%s"][%s]' %
                             (rvar[0][:-2], rvar[1]))
                    else:
                        qvar = udict[var[-1]]
                    qvtype = ("%s" % type(qvar))[1:-1].split()[1][1:-1]
                    if qvtype.startswith("PyQt4"):
                        qtVariable = True

                if qtVariable:
                    vlist = self.__formatQt4Variable(qvar, qvtype)
                else:
                    # format the dictionary found
                    if dictkeys is None:
                        dictkeys = dict.keys()
                    else:
                        # treatment for sequences and dictionaries
                        if access:
                            exec("dict = dict%s" % access)
                        else:
                            dict = dict[dictkeys[0]]
                        if isDict:
                            dictkeys = dict.keys()
                        else:
                            dictkeys = range(len(dict))
                    vlist = self.__formatVariablesList(dictkeys, dict,
                                                       scope, formatSequences)
            varlist.extend(vlist)

            if obj is not None and not formatSequences:
                try:
                    if unicode(repr(obj)).startswith('{'):
                        varlist.append(('...', 'dict', "%d" % len(obj.keys())))
                    elif unicode(repr(obj)).startswith('['):
                        varlist.append(('...', 'list', "%d" % len(obj)))
                    elif unicode(repr(obj)).startswith('('):
                        varlist.append(('...', 'tuple', "%d" % len(obj)))
                except:
                    pass

        self.write('%s%s' % (ResponseVariable, varlist))

    def __formatQt4Variable(self, value, vtype):
        """produce a formated output of a simple Qt4 type"""
        qttype = vtype.split('.')[-1]
        varlist = []
        if qttype == 'QString':
            varlist.append(("", "QString", "%s" % value))
        elif qttype == 'QStringList':
            for index in range(value.count()):
                varlist.append(("%d" % index, "QString",
                                "%s" % value[index]))
        elif qttype == 'QByteArray':
            varlist.append(("hex", "QByteArray", "%s" % value.toHex()))
            varlist.append(("base64", "QByteArray",
                            "%s" % value.toBase64()))
            varlist.append(("percent encoding", "QByteArray",
                            "%s" % value.toPercentEncoding()))
        elif qttype == 'QChar':
            varlist.append(("", "QChar",
                            "%s" % value.unicode()))
            varlist.append(("", "int", "%d" % value.unicode()))
        elif qttype == 'QPoint':
            varlist.append(("x", "int", "%d" % value.x()))
            varlist.append(("y", "int", "%d" % value.y()))
        elif qttype == 'QPointF':
            varlist.append(("x", "float", "%g" % value.x()))
            varlist.append(("y", "float", "%g" % value.y()))
        elif qttype == 'QRect':
            varlist.append(("x", "int", "%d" % value.x()))
            varlist.append(("y", "int", "%d" % value.y()))
            varlist.append(("width", "int", "%d" % value.width()))
            varlist.append(("height", "int", "%d" % value.height()))
        elif qttype == 'QRectF':
            varlist.append(("x", "float", "%g" % value.x()))
            varlist.append(("y", "float", "%g" % value.y()))
            varlist.append(("width", "float", "%g" % value.width()))
            varlist.append(("height", "float", "%g" % value.height()))
        elif qttype == 'QSize':
            varlist.append(("width", "int", "%d" % value.width()))
            varlist.append(("height", "int", "%d" % value.height()))
        elif qttype == 'QSizeF':
            varlist.append(("width", "float", "%g" % value.width()))
            varlist.append(("height", "float", "%g" % value.height()))
        elif qttype == 'QColor':
            varlist.append(("name", "QString", "%s" % value.name()))
            r, g, b, a = value.getRgb()
            varlist.append(("rgb", "int", "%d, %d, %d, %d" % (r, g, b, a)))
            h, s, v, a = value.getHsv()
            varlist.append(("hsv", "int", "%d, %d, %d, %d" % (h, s, v, a)))
            c, m, y, k, a = value.getCmyk()
            varlist.append(("cmyk", "int",
                            "%d, %d, %d, %d, %d" % (c, m, y, k, a)))
        elif qttype == 'QDate':
            varlist.append(("", "QDate",
                            "%s" % value.toString()))
        elif qttype == 'QTime':
            varlist.append(("", "QTime",
                            "%s" % value.toString()))
        elif qttype == 'QDateTime':
            varlist.append(("", "QDateTime",
                            "%s" % value.toString()))
        elif qttype == 'QDir':
            varlist.append(("path", "QString",
                            "%s" % value.path()))
            varlist.append(("absolutePath", "QString",
                            "%s" % value.absolutePath()))
            varlist.append(("canonicalPath", "QString",
                            "%s" % value.canonicalPath()))
        elif qttype == 'QFile':
            varlist.append(("fileName", "QString",
                            "%s" % value.fileName()))
        elif qttype == 'QFont':
            varlist.append(("family", "QString",
                            "%s" % value.family()))
            varlist.append(("pointSize", "int",
                            "%d" % value.pointSize()))
            varlist.append(("weight", "int",
                            "%d" % value.weight()))
            varlist.append(("bold", "bool",
                            "%s" % value.bold()))
            varlist.append(("italic", "bool",
                            "%s" % value.italic()))
        elif qttype == 'QUrl':
            varlist.append(("url", "QString",
                            "%s" % value.toString()))
            varlist.append(("scheme", "QString",
                            "%s" % value.scheme()))
            varlist.append(("user", "QString",
                            "%s" % value.userName()))
            varlist.append(("password", "QString",
                            "%s" % value.password()))
            varlist.append(("host", "QString",
                            "%s" % value.host()))
            varlist.append(("port", "int",
                            "%d" % value.port()))
            varlist.append(("path", "QString",
                            "%s" % value.path()))
        elif qttype == 'QModelIndex':
            varlist.append(("valid", "bool", "%s" % value.isValid()))
            if value.isValid():
                varlist.append(("row", "int",
                                "%s" % value.row()))
                varlist.append(("column", "int",
                                "%s" % value.column()))
                varlist.append(("internalId", "int",
                                "%s" % value.internalId()))
                varlist.append(("internalPointer", "void *",
                                "%s" % value.internalPointer()))
        elif qttype == 'QRegExp':
            varlist.append(("pattern", "QString",
                            "%s" % value.pattern()))

        # GUI stuff
        elif qttype == 'QAction':
            varlist.append(("name", "QString",
                            "%s" % value.objectName()))
            varlist.append(("text", "QString",
                            "%s" % value.text()))
            varlist.append(("icon text", "QString",
                            "%s" % value.iconText()))
            varlist.append(("tooltip", "QString",
                            "%s" % value.toolTip()))
            varlist.append(("whatsthis", "QString",
                            "%s" % value.whatsThis()))
            varlist.append(("shortcut", "QString",
                            "%s" % value.shortcut().toString()))
        elif qttype == 'QKeySequence':
            varlist.append(("value", "",
                            "%s" % value.toString()))

        # XML stuff
        elif qttype == 'QDomAttr':
            varlist.append(("name", "QString",
                            "%s" % value.name()))
            varlist.append(("value", "QString",
                            "%s" % value.value()))
        elif qttype == 'QDomCharacterData':
            varlist.append(("data", "QString",
                            "%s" % value.data()))
        elif qttype == 'QDomComment':
            varlist.append(("data", "QString",
                            "%s" % value.data()))
        elif qttype == "QDomDocument":
            varlist.append(("text", "QString",
                            "%s" % value.toString()))
        elif qttype == 'QDomElement':
            varlist.append(("tagName", "QString",
                            "%s" % value.tagName()))
            varlist.append(("text", "QString",
                            "%s" % value.text()))
        elif qttype == 'QDomText':
            varlist.append(("data", "QString",
                            "%s" % value.data()))

        # Networking stuff
        elif qttype == 'QHostAddress':
            varlist.append(("address", "QHostAddress",
                            "%s" % value.toString()))
        return varlist

    def __formatVariablesList(self, keylist, dict, scope,
                              formatSequences=False):
        """produce a formated variables list.

           The dictionary passed in to it is scanned. The formated variables
           list (a list of tuples of 3 values) is returned."""
        varlist = []

        for key in keylist:
            # special handling for '__builtins__' (it's way too big)
            if key == '__builtins__':
                rvalue = '<module __builtin__ (built-in)>'
                valtype = 'module'
            else:
                value = dict[key]
                valtypestr = ("%s" % type(value))[1:-1]

                if valtypestr.split(' ', 1)[0] == 'class':
                    # handle new class type of python 2.2+
                    valtype = valtypestr
                else:
                    valtype = valtypestr[6:-1]

                try:
                    if valtype not in ['list', 'tuple', 'dict']:
                        rvalue = repr(value)
                        if valtype.startswith('class') and \
                           rvalue[0] in ['{', '(', '[']:
                            rvalue = ""
                    else:
                        if valtype == 'dict':
                            rvalue = "%d" % len(value.keys())
                        else:
                            rvalue = "%d" % len(value)
                except:
                    rvalue = ''

            if formatSequences:
                key = "'%s'" % key
            varlist.append((key, valtype, rvalue))
        return varlist

    def startProgInDebugger(self, progargs, wd, host,
                            port, exceptions=True,
                            tracePython=False, redirect=True):
        """start the remote debugger"""
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
        self.mainFrame = None
        self.inRawMode = False
        self.debugging = True

        self.passive = True
        self.write("%s%s|%d" % (PassiveStartup,
                                self.running, exceptions))
        self.__interact()

        self.attachThread(mainThread=True)
        self.mainThread.tracePython = tracePython

        # set the system exception handling function to ensure, that
        # we report on all unhandled exceptions
        sys.excepthook = self.__unhandled_exception

        # This will eventually enter a local event loop.
        # Note the use of backquotes to cause a repr of self.running.
        # The need for this is on Windows os where backslash is the path
        # separator. They will get inadvertantly stripped away during
        # the eval causing IOErrors if self.running is passed as a normal str.
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
            host, version = host.split("@@")
            family = socket.AF_INET6
        except ValueError:
            # version = 'v4'
            family = socket.AF_INET

        return socket.getaddrinfo(host, None, family,
                                  socket.SOCK_STREAM)[0][4][0]

    def main(self):
        """the main method"""
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
                    self.fork_auto = True
                    self.fork_child = True
                    del args[0]
                elif args[0] == '--fork-parent':
                    self.fork_auto = True
                    self.fork_child = False
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

        if not self.fork_auto and not isPopen:
            self.write(RequestForkTo)
            self.eventLoop(True)
        pid = DEBUG_CLIENT_ORIG_FORK()

        if isPopen:
            # Switch to following parent
            oldFollow = self.fork_child
            self.fork_child = False

        if pid == 0:
            # child
            if not self.fork_child:
                sys.settrace(None)
                sys.setprofile(None)
                self.sessionClose(0)
        else:
            # parent
            if self.fork_child:
                sys.settrace(None)
                sys.setprofile(None)
                self.sessionClose(0)

        if isPopen:
            # Switch to what it was before
            self.fork_child = oldFollow
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
        """calculate a path list including the PYTHONPATH environment
           variable"""
        sysPath = [path for path in
                   os.environ.get("PYTHONPATH", "").split(":")
                   if path not in sys.path] + sys.path[:]
        if "" in sysPath:
            sysPath.remove("")
        sysPath.insert(0, firstEntry)
        sysPath.insert(0, '')
        return sysPath
