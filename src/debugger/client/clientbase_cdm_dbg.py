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

DebugClientInstance = None


def debugClientRawInput(prompt='', echo=True):
    """Replacement for the standard raw_input builtin.
       This function works with the split debugger.
    """
    if DebugClientInstance is None or DebugClientInstance.redirect == 0:
        return DebugClientOrigRawInput(prompt)
    return DebugClientInstance.raw_input(prompt, echo)


# Use our own raw_input().
try:
    DebugClientOrigRawInput = __builtins__.__dict__['raw_input']
    __builtins__.__dict__['raw_input'] = debugClientRawInput
except (AttributeError, KeyError):
    import __main__
    DebugClientOrigRawInput = __main__.__builtins__.__dict__['raw_input']
    __main__.__builtins__.__dict__['raw_input'] = debugClientRawInput


def debugClientInput(prompt=""):
    """Replacement for the standard input builtin.
       This function works with the split debugger.
    """
    if DebugClientInstance is None or DebugClientInstance.redirect == 0:
        return DebugClientOrigInput(prompt)
    return DebugClientInstance.input(prompt)


# Use our own input().
try:
    DebugClientOrigInput = __builtins__.__dict__['input']
    __builtins__.__dict__['input'] = debugClientInput
except (AttributeError, KeyError):
    import __main__
    DebugClientOrigInput = __main__.__builtins__.__dict__['input']
    __main__.__builtins__.__dict__['input'] = debugClientInput


def debugClientFork():
    """Replacement for the standard os.fork()"""
    if DebugClientInstance is None:
        return DebugClientOrigFork()
    return DebugClientInstance.fork()


# use our own fork().
if 'fork' in dir(os):
    DebugClientOrigFork = os.fork
    os.fork = debugClientFork


def debugClientClose(filedesc):
    """Replacement for the standard os.close(fd)"""
    if DebugClientInstance is None:
        DebugClientOrigClose(filedesc)
    DebugClientInstance.close(filedesc)


# use our own close().
if 'close' in dir(os):
    DebugClientOrigClose = os.close
    os.close = debugClientClose


def debugClientSetRecursionLimit(limit):
    """Replacement for the standard sys.setrecursionlimit(limit)"""
    rlimit = max(limit, 64)
    setRecursionLimit(rlimit)
    DebugClientOrigSetRecursionLimit(rlimit + 64)


# use our own setrecursionlimit().
if 'setrecursionlimit' in dir(sys):
    DebugClientOrigSetRecursionLimit = sys.setrecursionlimit
    sys.setrecursionlimit = debugClientSetRecursionLimit
    debugClientSetRecursionLimit(sys.getrecursionlimit())


class DebugClientBase(object):
    """Class implementing the client side of the debugger.

       It provides access to the Python interpeter from a debugger running in
       another process whether or not the Qt event loop is running.

       The protocol between the debugger and the client assumes that there will
       be a single source of debugger commands and a single source of Python
       statements.  Commands and statement are always exactly one line and may
       be interspersed.

       The protocol is as follows.  First the client opens a connection to the
       debugger and then sends a series of one line commands. A command is either
       &gt;Load&lt;, &gt;Step&lt;, &gt;StepInto&lt;, ... or a Python statement.
       See DebugProtocol.py for a listing of valid protocol tokens.

       A Python statement consists of the statement to execute, followed (in a
       separate line) by &gt;OK?&lt;.  If the statement was incomplete then the
       response is &gt;Continue&lt;.  If there was an exception then the response
       is &gt;Exception&lt;.
       Otherwise the response is &gt;OK&lt;.  The reason for the &gt;OK?&lt; part
       is to provide a sentinal (ie. the responding &gt;OK&lt;) after any
       possible output as a result of executing the command.

       The client may send any other lines at any other time which should be
       interpreted as program output.

       If the debugger closes the session there is no response from the client.
       The client may close the session at any time as a result of the script
       being debugged closing or crashing.

       <b>Note</b>: This class is meant to be subclassed by individual
       DebugClient classes. Do not instantiate it directly."""

    def __init__(self):
        self.breakpoints = {}
        self.redirect = True

        # The next couple of members are needed for the threaded version.
        # For this base class they contain static values for the non threaded
        # debugger

        # dictionary of all threads running
        self.threads = {}

        # the "current" thread, basically the thread we are at a
        # breakpoint for.
        self.currentThread = self

        # special objects representing the main scripts thread and frame
        self.mainThread = self
        self.mainFrame = None
        self.framenr = 0

        # The context to run the debugged program in.
        self.debugMod = imp.new_module('__main__')

        # The list of complete lines to execute.
        self.buffer = ''

        self.pendingResponse = ResponseOK
        self._fncache = {}
        self.dircache = []
        self.inRawMode = 0
        self.mainProcStr = None     # used for the passive mode
        self.passive = 0            # used to indicate the passive mode
        self.running = None
        self.test = None
        self.tracePython = 0
        self.debugging = 0

        self.fork_auto = False
        self.fork_child = False

        self.readstream = None
        self.writestream = None
        self.errorstream = None
        self.pollingDisabled = False

        self.skipdirs = sys.path[:]

        self.variant = 'You should not see this'

        self.compile_command = codeop.CommandCompiler()

        self.coding_re = re.compile(r"coding[:=]\s*([-\w_.]+)")
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
            default = 'latin-1'
            try:
                f = open(filename, 'rb')
                # read the first and second line
                text = f.readline()
                text = "%s%s" % (text, f.readline())
                f.close()
            except IOError:
                self.__coding = default
                return

            for line in text.splitlines():
                match = self.coding_re.search(line)
                if match:
                    self.__coding = match.group(1)
                    return
            self.__coding = default

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

    def raw_input(self, prompt, echo):
        """raw_input() using the event loop"""
        self.write("%s%s" % (ResponseRaw, (prompt, echo)))
        self.inRawMode = 1
        self.eventLoop(True)
        return self.rawLine

    def input(self, prompt):
        """input() using the event loop"""
        return eval(self.raw_input(prompt, 1))

    def __exceptionRaised(self):
        """Called in the case of an exception
           It ensures that the debug server is informed of the raised
           exception"""
        self.pendingResponse = ResponseException

    def sessionClose(self, shouldExit=True, exitCode=0):
        """Closes the session with the debugger and optionally terminate"""
        try:
            self.set_quit()
        except:
            pass

        # clean up asyncio.
        self.disconnect()
        self.debugging = 0

        # make sure we close down our end of the socket
        # might be overkill as normally stdin, stdout and stderr
        # SHOULD be closed on exit, but it does not hurt to do it here
        self.readstream.close(1)
        self.writestream.close(1)
        self.errorstream.close(1)

        if shouldExit:
            # Ok, go away.
            sys.exit(exitCode)

    def handleLine(self, line):
        """Handles the receipt of a complete line"""
        # Remove any newline.
        if line[-1] == '\n':
            line = line[:-1]

        eoc = line.find('<')

        if eoc >= 0 and line[0] == '>':
            # Get the command part and the arguments
            cmd = line[:eoc + 1]
            arg = line[eoc + 1:]

            if cmd == RequestVariables:
                frmnr, scope = eval(arg)
                self.__dumpVariables(int(frmnr), int(scope))
                return

            if cmd == RequestVariable:
                var, frmnr, scope = eval(arg)
                self.__dumpVariable(var, int(frmnr), int(scope))
                return

            if cmd == RequestThreadList:
                self.__dumpThreadList()
                return

            if cmd == RequestStack:
                stack = self.currentThread.getStack()
                self.write('%s%s' % (ResponseStack, stack))
                return

            if cmd == RequestThreadSet:
                tid = eval(arg)
                if tid in self.threads:
                    self.setCurrentThread(tid)
                    self.write(ResponseThreadSet)
                    stack = self.currentThread.getStack()
                    self.write('%s%s' % (ResponseStack, stack))
                return

            if cmd == RequestStep:
                self.currentThread.step(1)
                self.eventExit = 1
                return

            if cmd == RequestStepOver:
                self.currentThread.step(0)
                self.eventExit = 1
                return

            if cmd == RequestStepOut:
                self.currentThread.stepOut()
                self.eventExit = 1
                return

            if cmd == RequestStepQuit:
                if self.passive:
                    self.progTerminated(42)
                else:
                    self.set_quit()
                    self.eventExit = 1
                return

            if cmd == RequestContinue:
                special = int(arg)
                self.currentThread.go(special)
                self.eventExit = 1
                return

            if cmd == RequestOK:
                self.write(self.pendingResponse)
                self.pendingResponse = ResponseOK
                return

            if cmd == RequestShutdown:
                self.sessionClose(1, 99)
                return

            if cmd == RequestBreak:
                fname, line, temporary, _set, cond = arg.split('@@')
                line = int(line)
                _set = int(_set)
                temporary = int(temporary)

                if _set:
                    if cond == 'None' or cond == '':
                        cond = None
                    else:
                        try:
                            compile(cond, '<string>', 'eval')
                        except SyntaxError:
                            self.write('%s%s,%d' %
                                (ResponseBPConditionError, fname, line))
                            return
                    self.mainThread.set_break(fname, line, temporary, cond)
                else:
                    self.mainThread.clear_break(fname, line)
                return

            if cmd == RequestBreakEnable:
                fname, line, enable = arg.split(',')
                line = int(line)
                enable = int(enable)

                bpoint = self.mainThread.get_break(fname, line)
                if bpoint is not None:
                    if enable:
                        bpoint.enable()
                    else:
                        bpoint.disable()
                return

            if cmd == RequestBreakIgnore:
                fname, line, count = arg.split(',')
                line = int(line)
                count = int(count)

                bpoint = self.mainThread.get_break(fname, line)
                if bpoint is not None:
                    bpoint.ignore = count
                return

            if cmd == RequestWatch:
                cond, temporary, _set = arg.split('@@')
                _set = int(_set)
                temporary = int(temporary)

                if _set:
                    if not cond.endswith('??created??') and \
                       not cond.endswith('??changed??'):
                        try:
                            compile(cond, '<string>', 'eval')
                        except SyntaxError:
                            self.write('%s%s' % (ResponseWPConditionError,
                                                 cond))
                            return
                    self.mainThread.set_watch(cond, temporary)
                else:
                    self.mainThread.clear_watch(cond)
                return

            if cmd == RequestWatchEnable:
                cond, enable = arg.split(',')
                enable = int(enable)

                bpoint = self.mainThread.get_watch(cond)
                if bpoint is not None:
                    if enable:
                        bpoint.enable()
                    else:
                        bpoint.disable()
                return

            if cmd == RequestWatchIgnore:
                cond, count = arg.split(',')
                count = int(count)

                bpoint = self.mainThread.get_watch(cond)
                if bpoint is not None:
                    bpoint.ignore = count
                return

            if cmd == RequestEval:
                parts = arg.split(",", 1)
                frameNumber = int(parts[0])
                expression = parts[1].strip()

                f = self.currentThread.getCurrentFrame()
                while f is not None and frameNumber > 0:
                    f = f.f_back
                    frameNumber -= 1

                if f is None:
                    self.write(ResponseEval)
                    self.write('Bad frame number\n')
                    self.write(ResponseEvalError)
                    return

                _globals = f.f_globals
                _locals = f.f_locals

                try:
                    value = eval(expression, _globals, _locals)
                except SyntaxError as excpt:
                    # Generic way below reports nothing in case of a syntax
                    # error
                    _list = ["Traceback (innermost last):\n"]
                    _list += traceback.format_exception_only(SyntaxError,
                                                             excpt)

                    self.write(ResponseEval)
                    map(self.write, _list)
                    self.write(ResponseEvalError)
                except:
                    # Report the exception and the traceback
                    try:
                        valtype, value, tback = sys.exc_info()
                        sys.last_type = valtype
                        sys.last_value = value
                        sys.last_traceback = tback
                        tblist = traceback.extract_tb(tback)
                        del tblist[:1]
                        _list = traceback.format_list(tblist)
                        if _list:
                            _list.insert(0, "Traceback (innermost last):\n")
                            _list[len(_list):] = \
                                traceback.format_exception_only(valtype,
                                                                value)
                    finally:
                        tblist = tback = None

                    self.write(ResponseEval)
                    map(self.write, _list)
                    self.write(ResponseEvalError)
                else:
                    self.write(ResponseEval)
                    self.write(value + '\n')
                    self.write(ResponseEvalOK)
                return

            if cmd == RequestExec:
                parts = arg.split(",", 1)
                frameNumber = int(parts[0])
                expression = parts[1].strip()

                f = self.currentThread.getCurrentFrame()
                while f is not None and frameNumber > 0:
                    f = f.f_back
                    frameNumber -= 1

                if f is None:
                    self.write(ResponseExec)
                    self.write('Bad frame number\n')
                    self.write(ResponseExecError)
                    return

                currentStdout = sys.stdout
                currentStderr = sys.stderr
                collector = OutStreamCollector()
                sys.stdout = collector
                sys.stderr = collector

                # Locals are copied (not referenced) here!
                _globals = f.f_globals
                _locals = f.f_locals

                try:
                    code = compile(expression + '\n', '<string>', 'exec')
                    exec(code, _globals, _locals)

                    # These two dict updates do not work. If a local
                    # variable is changed in the _locals it is not updated
                    # below. I have no ideas how to fix it.
                    f.f_globals.update(_globals)
                    f.f_locals.update(_locals)
                except SyntaxError as excpt:
                    # Generic way below reports nothing in case of a syntax
                    # error
                    _list = ["Traceback (innermost last):\n"]
                    _list += traceback.format_exception_only(SyntaxError,
                                                             excpt)

                    self.write(ResponseExec)
                    map(self.write, _list)
                    self.write(ResponseExecError)

                    # Restore the output streams
                    sys.stdout = currentStdout
                    sys.stderr = currentStderr
                    return
                except:
                    # Report the exception and the traceback
                    try:
                        valtype, value, tback = sys.exc_info()
                        sys.last_type = valtype
                        sys.last_value = value
                        sys.last_traceback = tback
                        tblist = traceback.extract_tb(tback)
                        del tblist[:1]
                        _list = traceback.format_list(tblist)
                        if _list:
                            _list.insert(0, "Traceback (innermost last):\n")
                            _list[len(_list):] = \
                                traceback.format_exception_only(valtype,
                                                                value)
                    finally:
                        tblist = tback = None

                    self.write(ResponseExec)
                    map(self.write, _list)
                    self.write(ResponseExecError)

                    # Restore the output streams
                    sys.stdout = currentStdout
                    sys.stderr = currentStderr
                    return

                self.write(ResponseExec)
                self.write(collector.buf)
                self.write(ResponseExecOK)

                # Restore the output streams
                sys.stdout = currentStdout
                sys.stderr = currentStderr
                return

            if cmd == ResponseForkTo:
                # this results from a separate event loop
                self.fork_child = (arg == 'child')
                self.eventExit = 1
                return

        # If we are handling raw mode input then reset the mode and break out
        # of the current event loop.
        if self.inRawMode:
            self.inRawMode = 0
            self.rawLine = line
            self.eventExit = 1
            return

        if self.buffer:
            self.buffer = self.buffer + '\n' + line
        else:
            self.buffer = line

        try:
            code = self.compile_command(self.buffer,
                                        self.readstream.name)
        except (OverflowError, SyntaxError, ValueError):
            # Report the exception
            sys.last_type, sys.last_value, sys.last_traceback = sys.exc_info()
            map(self.write,
                traceback.format_exception_only(sys.last_type,
                                                sys.last_value))
            self.buffer = ''
        else:
            if code is None:
                self.pendingResponse = ResponseContinue
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
                            cframe = self.currentThread.getCurrentFrame()
                            # program has terminated
                            if cframe is None:
                                self.running = None
                                _globals = self.debugMod.__dict__
                                _locals = _globals
                            else:
                                frmnr = self.framenr
                                while cframe is not None and frmnr > 0:
                                    cframe = cframe.f_back
                                    frmnr -= 1
                                _globals = cframe.f_globals
                                _locals = self.currentThread. \
                                                    getCurrentFrameLocals()
                        # reset sys.stdout to our redirector (unconditionally)
                        if _globals.has_key("sys"):
                            __stdout = _globals["sys"].stdout
                            _globals["sys"].stdout = self.writestream
                            exec(code, _globals, _locals)
                            _globals["sys"].stdout = __stdout
                        elif _locals.has_key("sys"):
                            __stdout = _locals["sys"].stdout
                            _locals["sys"].stdout = self.writestream
                            exec(code, _globals, _locals)
                            _locals["sys"].stdout = __stdout
                        else:
                            exec(code, _globals, _locals)
                except SystemExit as exc:
                    self.progTerminated(exc.code)
                except:
                    # Report the exception and the traceback
                    try:
                        _type, value, tback = sys.exc_info()
                        sys.last_type = _type
                        sys.last_value = value
                        sys.last_traceback = tback
                        tblist = traceback.extract_tb(tback)
                        del tblist[:1]
                        _list = traceback.format_list(tblist)
                        if _list:
                            _list.insert(0, "Traceback (innermost last):\n")
                            _list[len(_list):] = \
                                traceback.format_exception_only(_type,
                                                                value)
                    finally:
                        tblist = tback = None

                    map(self.write, _list)

    def write(self, msg):
        """Public method to write data to the output stream"""
        self.writestream.write(msg)
        self.writestream.flush()

    def __interact(self):
        """Interact with the debugger"""
        global DebugClientInstance

        self.setDescriptors(self.readstream, self.writestream)
        DebugClientInstance = self

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
        res = self.mainThread.run('execfile(' + `self.running` + ')',
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
        pid = DebugClientOrigFork()

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
            DebugClientOrigClose(fdescriptor)

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
