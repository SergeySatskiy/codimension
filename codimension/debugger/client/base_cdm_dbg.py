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


"""
Module implementing the debug base class
"""

import sys
import os
import types
import atexit
import inspect
import ctypes
import time
from inspect import CO_GENERATOR
from bp_wp_cdm_dbg import Breakpoint, Watch
from cdm_dbg_utils import formatArgValues, getArgValues, printerr
import _thread


RECURSION_LIMIT = 64


def setRecursionLimit(limit):
    " Sets the recursion limit "
    global RECURSION_LIMIT
    RECURSION_LIMIT = limit


class DebugBase(object):

    """
    Base class of the debugger - the part which is external to IDE.
    """

    # Don't thrust distutils.sysconfig.get_python_lib: possible case mismatch
    # on Windows
    lib = os.path.dirname(inspect.__file__)

    # Tuple required because it's accessed a lot of times by startswith method
    pathsToSkip = ('<', os.path.dirname(__file__), inspect.__file__[:-1])
    filesToSkip = {}

    # Cache for fixed file names
    _fnCache = {}

    # Stop all timers, when greenlets are used
    pollTimerEnabled = True

    def __init__(self, dbgClient):
        self._dbgClient = dbgClient

        # Some informations about the thread
        self.isMainThread = False
        self.quitting = False
        self.id = -1
        self.name = ''

        self.tracePythonLibs(0)

        # Special handling of a recursion error
        self.skipFrames = 0

        self.isBroken = False
        self.cFrame = None

        # current frame we are at
        self.currentFrame = None

        # frames, where we want to stop or release debugger
        self.stopframe = None
        self.returnframe = None
        self.stop_everywhere = False

        self.__recursionDepth = -1
        self.setRecursionDepth(inspect.currentframe())

        # background task to periodicaly check for client interactions
        self.eventPollFlag = False
        self.timer = _thread.start_new_thread(self.__eventPollTimer, ())

        # provide a hook to perform a hard breakpoint
        # Use it like this:
        # if hasattr(sys, 'breakpoint): sys.breakpoint()
        sys.breakpoint = self.set_trace
        if sys.version_info[:2] >= (3, 7):
            sys.breakpointhook = self.set_trace

    def __eventPollTimer(self):
        """Sets a flag every 0.5 sec to check for new messages"""
        while DebugBase.pollTimerEnabled:
            time.sleep(0.5)
            self.eventPollFlag = True

        self.eventPollFlag = False

    def getCurrentFrame(self):
        """Provides the current frame"""
        if self.quitting:
            return None
        return self.currentFrame

    def getFrameLocals(self, frmnr=0):
        """Provides the locals dictionary of the current frame"""
        f = self.currentFrame
        while f is not None and frmnr > 0:
            f = f.f_back
            frmnr -= 1
        return f.f_locals

    def storeFrameLocals(self, frmnr=0):
        """Stores the locals into the frame.

        Thus an access to frame.f_locals returns the last data
        """
        cf = self.currentFrame
        while cf is not None and frmnr > 0:
            cf = cf.f_back
            frmnr -= 1

        try:
            if '__pypy__' in sys.builtin_module_names:
                import __pypy__
                __pypy__.locals_to_fast(cf)
                return
        except Exception:
            pass

        ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object(cf),
                                              ctypes.c_int(0))

    def step(self, traceMode):
        """Performs step in this thread"""
        if traceMode:
            self.set_step()
        else:
            self.set_next(self.currentFrame)

    def stepOut(self):
        """Performs a step out of the current call"""
        self.set_return(self.currentFrame)

    def go(self, special):
        """Resumes the thread"""
        self.set_continue(special)

    def setRecursionDepth(self, frame):
        """Determines the current recursion depth"""
        self.__recursionDepth = 0
        while frame is not None:
            self.__recursionDepth += 1
            frame = frame.f_back

    def profileWithRecursion(self, frame, event, arg):
        """Traces some stuff independent of the debugger trace function"""
        if event == 'return':
            self.cFrame = frame.f_back
            self.__recursionDepth -= 1
            if self._dbgClient.callTraceEnabled:
                self.__sendCallTrace(event, frame, self.cFrame)
        elif event == 'call':
            if self._dbgClient.callTraceEnabled:
                self.__sendCallTrace(event, self.cFrame, frame)
            self.cFrame = frame
            self.__recursionDepth += 1
            if self.__recursionDepth > RECURSION_LIMIT:
                raise RuntimeError('maximum recursion depth exceeded\n'
                                   '(offending frame is two down the stack)')

    def profile(self, frame, event, arg):
        """Traces some stuff independant of the debugger trace function"""
        if event == 'return':
            self.__sendCallTrace(event, frame, frame.f_back)
        elif event == 'call':
            self.__sendCallTrace(event, frame.f_back, frame)

    def __sendCallTrace(self, event, fromFrame, toFrame):
        """Sends a call/return trace"""
        if not self.__skipFrame(fromFrame) and not self.__skipFrame(toFrame):
            fromInfo = {
                "filename": self._dbgClient.absPath(
                    self.fix_frame_filename(fromFrame)),
                "linenumber": fromFrame.f_lineno,
                "codename": fromFrame.f_code.co_name}
            toInfo = {
                "filename": self._dbgClient.absPath(
                    self.fix_frame_filename(toFrame)),
                "linenumber": toFrame.f_lineno,
                "codename": toFrame.f_code.co_name}
            self._dbgClient.sendCallTrace(event, fromInfo, toInfo)

    def trace_dispatch(self, frame, event, arg):
        """Reimplemented from bdb.py to do some special things"""
        # give the client a chance to push through new break points.
        if self.eventPollFlag:
            self._dbgClient.eventPoll()
            self.eventPollFlag = False

            if self.quitting:
                raise SystemExit

        if event == 'line':
            if self.stop_here(frame) or self.break_here(frame):
                if (self.stop_everywhere and frame.f_back and
                        frame.f_back.f_code.co_name == "sendJSONCommand"):
                    # Just stepped into print statement, so skip these frames
                    self._set_stopinfo(None, frame.f_back)
                else:
                    self.user_line(frame)
            return self.trace_dispatch

        if event == 'call':
            if (self.stop_here(frame) or
                    self.__checkBreakInFrame(frame) or
                    Watch.WATCHES != []):
                return self.trace_dispatch
            # No need to trace this function
            return

        if event == 'return':
            if frame == self.returnframe:
                # Only true if we didn't stopped in this frame, because it's
                # belonging to the eric debugger.
                self._set_stopinfo(None, frame.f_back)
            return

        if event == 'exception':
            if not self.__skipFrame(frame):
                # When stepping with next/until/return in a generator frame,
                # skip the internal StopIteration exception (with no traceback)
                # triggered by a subiterator run with the 'yield from'
                # statement.
                if not (frame.f_code.co_flags & CO_GENERATOR and
                        arg[0] is StopIteration and arg[2] is None):
                    self.user_exception(arg)
            # Stop at the StopIteration or GeneratorExit exception when the
            # user has set stopframe in a generator by issuing a return
            # command, or a next/until command at the last statement in the
            # generator before the exception.
            elif (self.stopframe and frame is not self.stopframe and
                  self.stopframe.f_code.co_flags & CO_GENERATOR and
                  arg[0] in (StopIteration, GeneratorExit)):
                self.user_exception(arg)
            return

        if event == 'c_call':
            return
        if event == 'c_exception':
            return
        if event == 'c_return':
            return

        print('DebugBase.trace_dispatch:'
              ' unknown debugging event: ',
              repr(event))
        return self.trace_dispatch

    def set_trace(self, frame=None):
        """Starts debugging from 'frame'"""
        if frame is None:
            frame = sys._getframe().f_back  # Skip set_trace method

        if sys.version_info[0] == 2:
            stopOnHandleLine = self._dbgClient.handleLine.func_code
        else:
            stopOnHandleLine = self._dbgClient.handleLine.__code__

        frame.f_trace = self.trace_dispatch
        while frame.f_back is not None:
            # stop at erics debugger frame or a threading bootstrap
            if (frame.f_back.f_code == stopOnHandleLine):
                frame.f_trace = self.trace_dispatch
                break

            frame = frame.f_back

        self.stop_everywhere = True
        sys.settrace(self.trace_dispatch)
        sys.setprofile(self._dbgClient.callTraceEnabled)

    def bootstrap(self, target, args, kwargs):
        """Bootstraps a thread"""
        try:
            # Because in the initial run method the "base debug" function is
            # set up, it's also valid for the threads afterwards.
            sys.settrace(self.trace_dispatch)

            target(*args, **kwargs)
        except Exception:
            excinfo = sys.exc_info()
            self.user_exception(excinfo, True)
        finally:
            sys.settrace(None)
            sys.setprofile(None)

    def run(self, cmd, globalsDict=None, localsDict=None, debug=True):
        """Starts a given command under debugger control"""
        if globalsDict is None:
            import __main__
            globalsDict = __main__.__dict__

        if localsDict is None:
            localsDict = globalsDict

        if not isinstance(cmd, types.CodeType):
            cmd = compile(cmd, "<string>", "exec")

        if debug:
            # First time the trace_dispatch function is called, a "base debug"
            # function has to be returned, which is called at every user code
            # function call. This is ensured by setting stop_everywhere.
            self.stop_everywhere = True
            sys.settrace(self.trace_dispatch)

        try:
            exec(cmd, globalsDict, localsDict)
            atexit._run_exitfuncs()
            self._dbgClient.progTerminated(0)
        except SystemExit:
            atexit._run_exitfuncs()
            excinfo = sys.exc_info()
            exitcode, message = self.__extractSystemExitMessage(excinfo)
            self._dbgClient.progTerminated(exitcode, message)
        except Exception:
            excinfo = sys.exc_info()
            self.user_exception(excinfo, True)
        finally:
            self.quitting = True
            sys.settrace(None)

    def _set_stopinfo(self, stopframe, returnframe):
        """Updates the frame pointers"""
        self.stopframe = stopframe
        self.returnframe = returnframe
        if returnframe is not None:
            # Ensure to be able to stop on the return frame
            returnframe.f_trace = self.trace_dispatch
        self.stop_everywhere = False

    def set_continue(self, special):
        """Stops only on next breakpoint"""
        # Here we only set a new stop frame if it is a normal continue.
        if not special:
            self._set_stopinfo(None, None)

        # Disable tracing if not started in debug mode
        if not self._dbgClient.debugging:
            sys.settrace(None)
            sys.setprofile(None)

    def set_step(self):
        """Stops after one line of code"""
        self._set_stopinfo(None, None)
        self.stop_everywhere = True

    def set_next(self, frame):
        """Stops on the next line in or below the given frame"""
        self._set_stopinfo(frame, frame.f_back)
        frame.f_trace = self.trace_dispatch

    def set_return(self, frame):
        """Stops when returning from the given frame"""
        self._set_stopinfo(None, frame.f_back)

    def move_instruction_pointer(self, lineno):
        """Moves the instruction pointer to another line"""
        try:
            self.currentFrame.f_lineno = lineno
            stack = self.getStack(self.currentFrame)
            self._dbgClient.sendResponseLine(stack)
        except Exception as exc:
            printerr(str(exc))

    def set_quit(self):
        """Quits"""
        sys.setprofile(None)
        self.stopframe = None
        self.returnframe = None
        for debugThread in self._dbgClient.threads.values():
            debugThread.quitting = True

    def fix_frame_filename(self, frame):
        """Fixups the filename for a given frame"""
        # get module name from __file__
        fn = frame.f_globals.get('__file__')
        try:
            return self._fnCache[fn]
        except KeyError:
            if fn is None:
                return frame.f_code.co_filename

            absFilename = os.path.abspath(fn)
            if absFilename.endswith(('.pyc', '.pyo', '.pyd')):
                fixedName = absFilename[:-1]
                if not os.path.exists(fixedName):
                    fixedName = absFilename
            else:
                fixedName = absFilename
            # update cache
            self._fnCache[fn] = fixedName
            return fixedName

    def __checkBreakInFrame(self, frame):
        """Checks if the function/method has a line number which is a bp"""
        try:
            return Breakpoint.BREAK_IN_FRAME_CACHE[
                frame.f_globals.get('__file__'),
                frame.f_code.co_firstlineno]
        except KeyError:
            filename = self.fix_frame_filename(frame)
            if filename not in Breakpoint.BREAK_IN_FILE:
                Breakpoint.BREAK_IN_FRAME_CACHE[
                    frame.f_globals.get('__file__'),
                    frame.f_code.co_firstlineno] = False
                return False
            lineNo = frame.f_code.co_firstlineno
            lineNumbers = [lineNo]

            if sys.version_info[0] == 2:
                co_lnotab = map(ord, frame.f_code.co_lnotab[1::2])
            else:
                co_lnotab = frame.f_code.co_lnotab[1::2]

            # No need to handle special case if a lot of lines between
            # (e.g. closure), because the additional lines won't cause a bp
            for co_lno in co_lnotab:
                lineNo += co_lno
                lineNumbers.append(lineNo)

            for bp in Breakpoint.BREAK_IN_FILE[filename]:
                if bp in lineNumbers:
                    Breakpoint.BREAK_IN_FRAME_CACHE[
                        frame.f_globals.get('__file__'),
                        frame.f_code.co_firstlineno] = True
                    return True
            Breakpoint.BREAK_IN_FRAME_CACHE[
                frame.f_globals.get('__file__'),
                frame.f_code.co_firstlineno] = False
            return False

    def break_here(self, frame):
        """Reimplemented from bdb.py to fix the filename from the frame"""
        filename = self.fix_frame_filename(frame)
        if (filename, frame.f_lineno) in Breakpoint.BREAKS:
            bp, flag = Breakpoint.effectiveBreak(
                filename, frame.f_lineno, frame)
            if bp:
                # flag says ok to delete temp. bp
                if flag and bp.temporary:
                    self.__do_clearBreak(filename, frame.f_lineno)
                return True

        if Watch.WATCHES != []:
            bp, flag = Watch.effectiveWatch(frame)
            if bp:
                # flag says ok to delete temp. watch
                if flag and bp.temporary:
                    self.__do_clearWatch(bp.cond)
                return True

        return False

    def __do_clearBreak(self, filename, lineno):
        """Clears a temporary breakpoint"""
        Breakpoint.clear_break(filename, lineno)
        self._dbgClient.sendClearTemporaryBreakpoint(filename, lineno)

    def __do_clearWatch(self, cond):
        """Clears a temporary watch expression"""
        Watch.clear_watch(cond)
        self._dbgClient.sendClearTemporaryWatch(cond)

    def getStack(self, frame=None, applyTrace=False):
        """Provides the stack"""
        if frame is None:
            fr = self.getCurrentFrame()
        elif type(frame) == list:
            fr = frame.pop(0)
        else:
            fr = frame

        stack = []
        while fr is not None:
            if applyTrace:
                # Reset the trace function so we can be sure
                # to trace all functions up the stack... This gets around
                # problems where an exception/breakpoint has occurred
                # but we had disabled tracing along the way via a None
                # return from dispatch_call
                fr.f_trace = self.trace_dispatch

            fname = self._dbgClient.absPath(self.fix_frame_filename(fr))
            # Always show at least one stack frame, even if it's from
            # codimension
            if stack and os.path.basename(fname).startswith(
                    ('base_cdm_dbg.py', "clientbase_cdm_dbg.py",
                     "threadextension_cdm_dbg.py", "threading.py")):
                break

            fline = fr.f_lineno
            ffunc = fr.f_code.co_name

            if ffunc == '?':
                ffunc = ''

            if ffunc and not ffunc.startswith("<"):
                argInfo = getArgValues(fr)
                try:
                    fargs = formatArgValues(
                        argInfo.args, argInfo.varargs,
                        argInfo.keywords, argInfo.locals)
                except Exception:
                    fargs = ""
            else:
                fargs = ""

            stack.append([fname, fline, ffunc, fargs])

            # is it a stack frame or exception list?
            if type(frame) == list:
                if frame != []:
                    fr = frame.pop(0)
                else:
                    fr = None
            else:
                fr = fr.f_back
        return stack

    def user_line(self, frame):
        """Reimplemented to the execution a particular line"""
        # We never stop on line 0.
        if frame.f_lineno == 0:
            return

        self.isBroken = True
        self.currentFrame = frame
        stack = self.getStack(frame, applyTrace=True)

        self._dbgClient.lockClient()
        self._dbgClient.currentThread = self
        self._dbgClient.currentThreadExec = self

        self._dbgClient.sendResponseLine(stack)
        self._dbgClient.eventLoop()

        self.isBroken = False
        self._dbgClient.unlockClient()

    def user_exception(self, excinfo, unhandled=False):
        """Reimplemented to report an exception to the debug server"""
        exctype, excval, exctb = excinfo

        if ((exctype in [GeneratorExit, StopIteration] and unhandled == False)
            or exctype == SystemExit):
            # ignore these
            return

        if exctype in [SyntaxError, IndentationError]:
            try:
                # tuple could only occure on Python 2, but not always!
                if type(excval) == tuple:
                    message, details = excval
                    filename, lineno, charno, text = details
                else:
                    message = excval.msg
                    filename = excval.filename
                    lineno = excval.lineno
                    charno = excval.offset

                if filename is None:
                    realSyntaxError = False
                else:
                    if charno is None:
                        charno = 0

                    filename = os.path.abspath(filename)
                    realSyntaxError = os.path.exists(filename)

            except (AttributeError, ValueError):
                message = ""
                filename = ""
                lineno = 0
                charno = 0
                realSyntaxError = True

            if realSyntaxError:
                self._dbgClient.sendSyntaxError(
                    message, filename, lineno, charno)
                self._dbgClient.eventLoop()
                return

        self.skipFrames = 0
        if (exctype == RuntimeError and
                str(excval).startswith('maximum recursion depth exceeded') or
                sys.version_info >= (3, 5) and
                exctype == RecursionError):
            excval = 'maximum recursion depth exceeded'
            depth = 0
            tb = exctb
            while tb:
                tb = tb.tb_next

                if (tb and tb.tb_frame.f_code.co_name == 'trace_dispatch' and
                        __file__.startswith(tb.tb_frame.f_code.co_filename)):
                    depth = 1
                self.skipFrames += depth

            # always 1 if running without debugger
            self.skipFrames = max(1, self.skipFrames)

        exctype = self.__extractExceptionName(exctype)

        if excval is None:
            excval = ''

        if unhandled:
            exctypetxt = "Unhandled {0!s}".format(str(exctype))
        else:
            exctypetxt = str(exctype)

        # Don't step into libraries, which are used by our debugger methods
        if exctb is not None:
            self.stop_everywhere = False

        self.isBroken = True

        stack = []
        if exctb:
            frlist = self.__extract_stack(exctb)
            frlist.reverse()

            self.currentFrame = frlist[0]
            stack = self.getStack(frlist[self.skipFrames:])

        self._dbgClient.lockClient()
        self._dbgClient.currentThread = self
        self._dbgClient.currentThreadExec = self
        self._dbgClient.sendException(exctypetxt, str(excval), stack)
        self._dbgClient.dumpThreadList()

        if exctb is not None:
            # When polling kept enabled, it isn't possible to resume after an
            # unhandled exception without further user interaction.
            self._dbgClient.eventLoop(True)

        self.skipFrames = 0

        self.isBroken = False
        stop_everywhere = self.stop_everywhere
        self.stop_everywhere = False
        self.eventPollFlag = False
        self._dbgClient.unlockClient()
        self.stop_everywhere = stop_everywhere

    @staticmethod
    def __extractExceptionName(exctype):
        """Extracts the exception name given the exception type object"""
        return str(exctype).replace("<class '", "").replace("'>", "")

    def __extract_stack(self, exctb):
        """Returns a list of stack frames"""
        tb = exctb
        stack = []
        while tb is not None:
            stack.append(tb.tb_frame)
            tb = tb.tb_next
        tb = None
        return stack

    def __extractSystemExitMessage(self, excinfo):
        """Provides the SystemExit code and message"""
        exctype, excval, exctb = excinfo
        if excval is None:
            exitcode = 0
            message = ""
        elif isinstance(excval, str):
            exitcode = 1
            message = excval
        elif isinstance(excval, bytes):
            exitcode = 1
            message = excval.decode()
        elif isinstance(excval, int):
            exitcode = excval
            message = ""
        elif isinstance(excval, SystemExit):
            code = excval.code
            if isinstance(code, str):
                exitcode = 1
                message = code
            elif isinstance(code, bytes):
                exitcode = 1
                message = code.decode()
            elif isinstance(code, int):
                exitcode = code
                message = ""
            else:
                exitcode = 1
                message = str(code)
        else:
            exitcode = 1
            message = str(excval)

        return exitcode, message

    def stop_here(self, frame):
        """Reimplemented to filter out debugger files"""
        if self.__skipFrame(frame):
            return False

        return (self.stop_everywhere or
                frame is self.stopframe or
                frame is self.returnframe)

    def tracePythonLibs(self, enable):
        """Updates the settings to trace into Python libraries"""
        pathsToSkip = list(self.pathsToSkip)
        # don't trace into Python library?
        if enable:
            pathsToSkip = [x for x in pathsToSkip if not x.endswith(
                ("site-packages", "dist-packages", self.lib))]
        else:
            pathsToSkip.append(self.lib)
            localLib = [x for x in sys.path
                        if x.endswith(("site-packages", "dist-packages")) and
                        not x.startswith(self.lib)]
            pathsToSkip.extend(localLib)

        self.pathsToSkip = tuple(set(pathsToSkip))

    def __skipFrame(self, frame):
        """Filters out debugger files"""
        try:
            return self.filesToSkip[frame.f_code.co_filename]
        except KeyError:
            ret = frame.f_code.co_filename.startswith(self.pathsToSkip)
            self.filesToSkip[frame.f_code.co_filename] = ret
            return ret
        except AttributeError:
            # if frame is None
            return True
