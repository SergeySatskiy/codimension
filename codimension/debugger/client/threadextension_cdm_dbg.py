# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# Copyright (c) 2014 - 2017 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an import hook patching thread modules to get debugged too
"""

import os.path
import sys
import importlib
import threading
import _thread
from protocol_cdm_dbg import METHOD_THREAD_LIST
from base_cdm_dbg import DebugBase
from cdm_dbg_utils import sendJSONCommand

_qtThreadNumber = 1


class ThreadExtension(object):

    """
    Class implementing the thread support for the debugger.

    Provides methods for intercepting thread creation, retriving the running
    threads and their name and state.
    """

    def __init__(self):
        self.threadNumber = 1
        self.enableImportHooks = True
        self._original_start_new_thread = None
        self.threadingAttached = False
        self.qtThreadAttached = False
        self.greenlet = False

        self.clientLock = threading.RLock()

        # dictionary of all threads running {id: DebugBase}
        self.threads = {_thread.get_ident(): self}

        # the "current" thread, basically for variables view
        self.currentThread = self
        # the thread we are at a breakpoint continuing at next command
        self.currentThreadExec = self

        # special objects representing the main scripts thread and frame
        self.mainThread = self
        self.threadModName = '_thread'

        # reset already imported thread module to apply hooks at next import
        del sys.modules[self.threadModName]
        del sys.modules['threading']

        sys.meta_path.insert(0, self)

    def attachThread(self, target=None, args=None, kwargs=None,
                     mainThread=False):
        """
        Public method to setup a standard thread for DebugClient to debug.

        If mainThread is True, then we are attaching to the already
        started mainthread of the app and the rest of the args are ignored.
        """
        if kwargs is None:
            kwargs = {}

        if mainThread:
            ident = _thread.get_ident()
            name = 'MainThread'
            newThread = self.mainThread
            newThread.isMainThread = True
        else:
            newThread = DebugBase(self)
            ident = self._original_start_new_thread(
                newThread.bootstrap, (target, args, kwargs))
            name = 'Thread-{0}'.format(self.threadNumber)
            self.threadNumber += 1

        newThread.id = ident
        newThread.name = name

        self.threads[ident] = newThread

        return ident

    def threadTerminated(self, threadId):
        """Called when a DebugThread has exited"""
        self.lockClient()
        try:
            del self.threads[threadId]
        except KeyError:
            pass
        finally:
            self.unlockClient()

    def lockClient(self, blocking=True):
        """Acquires the lock for this client"""
        if blocking:
            self.clientLock.acquire()
        else:
            return self.clientLock.acquire(blocking)

    def unlockClient(self):
        """Releases the lock for this client"""
        try:
            self.clientLock.release()
        except AssertionError:
            pass

    def setCurrentThread(self, threadId):
        """Sets the current thread"""
        try:
            self.lockClient()
            if threadId is None:
                self.currentThread = None
            else:
                self.currentThread = self.threads.get(threadId)
        finally:
            self.unlockClient()

    def dumpThreadList(self):
        """Sends the list of threads"""
        self.updateThreadList()
        threadList = []
        if len(self.threads) > 1:
            currentId = _thread.get_ident()
            # update thread names set by user (threading.setName)
            threadNames = {t.ident: t.getName() for t in threading.enumerate()}

            for threadId, thd in self.threads.items():
                threadProps = {"id": threadId}
                try:
                    threadProps["name"] = threadNames.get(threadId, thd.name)
                    threadProps["broken"] = thd.isBroken
                except Exception:
                    threadProps["name"] = 'UnknownThread'
                    threadProps["broken"] = False

                threadList.append(threadProps)
        else:
            currentId = -1
            threadProps = {"id": -1}
            threadProps["name"] = "MainThread"
            threadProps["broken"] = self.isBroken
            threadList.append(threadProps)

        sendJSONCommand(self.socket, METHOD_THREAD_LIST,
                        self.procuuid,
                        {"currentID": currentId, "threadList": threadList})

    @staticmethod
    def getExecutedFrame(frame):
        """Returns the currently executed frame"""
        # to get the currently executed frame, skip all frames belonging to the
        # debugger
        while frame is not None:
            baseName = os.path.basename(frame.f_code.co_filename)
            if not baseName.startswith(
                    ('clientbase_cdm_dbg.py', 'base_cdm_dbg.py',
                     'asyncfile_cdm_dbg.py', 'threadextension_cdm_dbg.py')):
                break
            frame = frame.f_back
        return frame

    def updateThreadList(self):
        """Updates the list of running threads"""
        frames = sys._current_frames()
        for threadId, frame in frames.items():
            # skip our own timer thread
            if frame.f_code.co_name == '__eventPollTimer':
                continue

            # Unknown thread
            if threadId not in self.threads:
                newThread = DebugBase(self)
                name = 'Thread-{0}'.format(self.threadNumber)
                self.threadNumber += 1

                newThread.id = threadId
                newThread.name = name
                self.threads[threadId] = newThread

            # adjust current frame
            if "__pypy__" not in sys.builtin_module_names:
                # Don't update with None
                currentFrame = self.getExecutedFrame(frame)
                if (currentFrame is not None and
                        self.threads[threadId].isBroken is False):
                    self.threads[threadId].currentFrame = currentFrame

        # Clean up obsolet because terminated threads
        self.threads = {id_: thrd for id_, thrd in self.threads.items()
                        if id_ in frames}

    # find_module(self, fullname, path=None)
    def find_module(self, fullname, _=None):
        """Returning the module loader"""
        if fullname in sys.modules or not self.debugging:
            return None

        if fullname in [self.threadModName, 'PyQt4.QtCore', 'PyQt5.QtCore',
                        'PySide.QtCore', 'PySide2.QtCore', 'greenlet',
                        'threading'] and self.enableImportHooks:
            # Disable hook to be able to import original module
            self.enableImportHooks = False
            return self
        return None

    def load_module(self, fullname):
        """Loads a module"""
        module = importlib.import_module(fullname)
        sys.modules[fullname] = module
        if (fullname == self.threadModName and
                self._original_start_new_thread is None):
            # make thread hooks available to system
            self._original_start_new_thread = module.start_new_thread
            module.start_new_thread = self.attachThread

        elif fullname == 'greenlet' and self.greenlet is False:
            # Check for greenlet.settrace
            if hasattr(module, 'settrace'):
                self.greenlet = True
                DebugBase.pollTimerEnabled = False

            # TODO: Implement the debugger extension for greenlets

        # Add hook for threading.run()
        elif fullname == "threading" and self.threadingAttached is False:
            self.threadingAttached = True

            # _debugClient as a class attribute can't be accessed in following
            # class. Therefore we need a global variable.
            _debugClient = self

            def _bootstrap(self, run):
                """
                Bootstrap for threading, which reports exceptions correctly.

                @param run the run method of threading.Thread
                @type method pointer
                """
                newThread = DebugBase(_debugClient)
                _debugClient.threads[self.ident] = newThread
                newThread.name = self.name
                # see DebugBase.bootstrap
                sys.settrace(newThread.trace_dispatch)
                try:
                    run()
                except Exception:
                    excinfo = sys.exc_info()
                    newThread.user_exception(excinfo, True)
                finally:
                    sys.settrace(None)

            class ThreadWrapper(module.Thread):

                """Wrapper class for threading.Thread"""

                def __init__(self, *args, **kwargs):
                    # Overwrite the provided run method with our own, to
                    # intercept the thread creation by threading.Thread
                    self.run = lambda s=self, run=self.run: _bootstrap(s, run)

                    super(ThreadWrapper, self).__init__(*args, **kwargs)

            module.Thread = ThreadWrapper

        # Add hook for *.QThread
        elif (fullname in ['PyQt4.QtCore', 'PyQt5.QtCore',
                           'PySide.QtCore', 'PySide2.QtCore'] and
              self.qtThreadAttached is False):
            self.qtThreadAttached = True
            # _debugClient as a class attribute can't be accessed in following
            # class. Therefore we need a global variable.
            _debugClient = self

            def _bootstrapQThread(self, run):
                """Bootstrap for QThread, which reports exceptions correctly"""
                global _qtThreadNumber

                newThread = DebugBase(_debugClient)
                ident = _thread.get_ident()
                name = 'QtThread-{0}'.format(_qtThreadNumber)

                _qtThreadNumber += 1

                newThread.id = ident
                newThread.name = name

                _debugClient.threads[ident] = newThread

                # see DebugBase.bootstrap
                sys.settrace(newThread.trace_dispatch)
                try:
                    run()
                except SystemExit:
                    # *.QThreads doesn't like SystemExit
                    pass
                except Exception:
                    excinfo = sys.exc_info()
                    newThread.user_exception(excinfo, True)
                finally:
                    sys.settrace(None)

            class QThreadWrapper(module.QThread):
                """Wrapper class for *.QThread"""

                def __init__(self, *args, **kwargs):
                    # Overwrite the provided run method with our own, to
                    # intercept the thread creation by Qt
                    self.run = lambda s=self, run=self.run: (
                        _bootstrapQThread(s, run))

                    super(QThreadWrapper, self).__init__(*args, **kwargs)

            module.QThread = QThreadWrapper

        self.enableImportHooks = True
        return module
