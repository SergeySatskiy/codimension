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
Module implementing the multithreaded version of the debug client.
"""

import thread
import sys

# NB: importing the global variable DebugClientInstance explicitly as
# from clientbase_cdm_dbg import DebugClientInstance
# does not work here. The variable is updated later however here it stays
# None forever. I have no ideas why. Importing the whole module and then
# referring to the variable as clientbase_cdm_dbg.DebugClientInstance
# fixes the problem.
import clientbase_cdm_dbg
from debugthread_cdm_dbg import DebugThread
from asyncio_cdm_dbg import AsyncIO


def _debugclient_start_new_thread( target, args, kwargs = {} ):
    """
    Module function used to allow for debugging of multiple threads.

    The way it works is that below, we reset thread._start_new_thread to
    this function object. Thus, providing a hook for us to see when
    threads are started. From here we forward the request onto the
    DebugClient which will create a DebugThread object to allow tracing
    of the thread then start up the thread. These actions are always
    performed in order to allow dropping into debug mode.

    See DebugClientThreads.attachThread and DebugThread.DebugThread in
    DebugThread.py

    @param target the start function of the target thread (i.e. the user code)
    @param args arguments to pass to target
    @param kwargs keyword arguments to pass to target
    @return The identifier of the created thread
    """
    if clientbase_cdm_dbg.DebugClientInstance is not None:
        return clientbase_cdm_dbg.DebugClientInstance.attachThread( target,
                                                                    args,
                                                                    kwargs )
    return _original_start_thread( target, args, kwargs )

# make thread hooks available to system
_original_start_thread = thread.start_new_thread
thread.start_new_thread = _debugclient_start_new_thread

# NOTE: import threading here AFTER above hook, as threading cache's
# thread._start_new_thread.
from threading import RLock

class DebugClientThreads( clientbase_cdm_dbg.DebugClientBase, AsyncIO ):
    """
    Class implementing the client side of the debugger.

    This variant of the debugger implements a threaded debugger client
    by subclassing all relevant base classes.
    """
    def __init__( self ):
        """
        Constructor
        """
        AsyncIO.__init__( self )
        clientbase_cdm_dbg.DebugClientBase.__init__( self )

        # protection lock for synchronization
        self.clientLock = RLock()

        # the "current" thread, basically the thread we are at a breakpoint for.
        self.currentThread = None

        # special objects representing the main scripts thread and frame
        self.mainThread = None
        self.mainFrame = None

        self.variant = 'Threaded'
        return

    def attachThread( self, target = None, args = None,
                      kwargs = None, mainThread = 0 ):
        """
        Public method to setup a thread for DebugClient to debug.

        If mainThread is non-zero, then we are attaching to the already
        started mainthread of the app and the rest of the args are ignored.

        @param target the start function of the target thread (i.e. the user code)
        @param args arguments to pass to target
        @param kwargs keyword arguments to pass to target
        @param mainThread non-zero, if we are attaching to the already
              started mainthread of the app
        @return The identifier of the created thread
        """
        try:
            self.lockClient()
            newThread = DebugThread( self, target, args, kwargs, mainThread )
            ident = -1
            if mainThread:
                ident = thread.get_ident()
                self.mainThread = newThread
                if self.debugging:
                    sys.setprofile( newThread.profile )
            else:
                ident = _original_start_thread( newThread.bootstrap, () )
            newThread.set_ident( ident )
            self.threads[ newThread.get_ident() ] = newThread
        finally:
            self.unlockClient()
        return ident

    def threadTerminated( self, dbgThread ):
        """
        Public method called when a DebugThread has exited.

        @param dbgThread the DebugThread that has exited
        """
        try:
            self.lockClient()
            try:
                del self.threads[ dbgThread.get_ident() ]
            except KeyError:
                pass
        finally:
            self.unlockClient()
        return

    def lockClient( self, blocking = 1 ):
        """
        Public method to acquire the lock for this client.

        @param blocking flag to indicating a blocking lock
        @return flag indicating successful locking
        """
        if blocking:
            return self.clientLock.acquire()
        return self.clientLock.acquire( blocking )

    def unlockClient( self ):
        """
        Public method to release the lock for this client.
        """
        try:
            self.clientLock.release()
        except AssertionError:
            pass
        return

    def setCurrentThread( self, threadID ):
        """
        Private method to set the current thread.

        @param threadID the id the current thread should be set to.
        """
        try:
            self.lockClient()
            if threadID is None:
                self.currentThread = None
            else:
                self.currentThread = self.threads[ threadID ]
        finally:
            self.unlockClient()
        return

    def eventLoop( self, disablePolling = False ):
        """
        Public method implementing our event loop.

        @param disablePolling flag indicating to enter an event loop with
            polling disabled (boolean)
        """
        # make sure we set the current thread appropriately
        threadid = thread.get_ident()
        self.setCurrentThread( threadid )
        clientbase_cdm_dbg.DebugClientBase.eventLoop( self, disablePolling )
        self.setCurrentThread( None )
        return

    def set_quit( self ):
        """
        Private method to do a 'set quit' on all threads.
        """
        try:
            locked = self.lockClient( 0 )
            try:
                for key in self.threads.keys():
                    self.threads[ key ].set_quit()
            except:
                pass
        finally:
            if locked:
                self.unlockClient()
        return

# We are normally called by the debugger to execute directly.

if __name__ == '__main__':
    debugClient = DebugClientThreads()
    debugClient.main()
