#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing the debug thread
"""

import bdb
import sys

from base_cdm_dbg import DebugBase



class DebugThread( DebugBase ):
    """
    Class implementing a debug thread.

    It represents a thread in the python interpreter that we are tracing.

    Provides simple wrapper methods around bdb for the 'owning' client to
    call to step etc.
    """
    def __init__( self, dbgClient, targ = None, args = None, kwargs = None,
                  mainThread = 0 ):
        """
        Constructor

        @param dbgClient the owning client
        @param targ the target method in the run thread
        @param args  arguments to be passed to the thread
        @param kwargs arguments to be passed to the thread
        @param mainThread 0 if this thread is not the mainscripts thread
        """
        DebugBase.__init__( self, dbgClient )

        self._target = targ
        self._args = args
        self._kwargs = kwargs
        self._mainThread = mainThread

        # thread running tracks execution state of client code
        # it will always be 0 for main thread as that is tracked
        # by DebugClientThreads and Bdb...
        self._threadRunning = 0

        self.__ident = None     # id of this thread
        self.__name = ""
        return

    def set_ident( self, threadID ):
        """
        Public method to set the id for this thread.

        @param id id for this thread (int)
        """
        self.__ident = threadID
        return

    def get_ident( self ):
        """
        Public method to return the id of this thread.

        @return the id of this thread (int)
        """
        return self.__ident

    def get_name( self ):
        """
        Public method to return the name of this thread.

        @return name of this thread (string)
        """
        return self.__name

    def traceThread( self ):
        """
        Private method to setup tracing for this thread.
        """
        self.set_trace()
        if not self._mainThread:
            self.set_continue( 0 )
        return

    def bootstrap( self ):
        """
        Private method to bootstrap the thread.

        It wraps the call to the user function to enable tracing
        before hand.
        """
        try:
            try:
                self._threadRunning = 1
                self.traceThread()
                self._target( *self._args, **self._kwargs )
            except bdb.BdbQuit:
                pass
        finally:
            self._threadRunning = 0
            self.quitting = 1
            self._dbgClient.threadTerminated( self )
            sys.settrace( None )
            sys.setprofile( None )
        return

    def trace_dispatch( self, frame, event, arg ):
        """
        Private method wrapping the trace_dispatch of bdb.py.

        It wraps the call to dispatch tracing into
        bdb to make sure we have locked the client to prevent multiple
        threads from entering the client event loop.

        @param frame The current stack frame.
        @param event The trace event (string)
        @param arg The arguments
        @return local trace function
        """
        try:
            self._dbgClient.lockClient()
            # if this thread came out of a lock, and we are quitting
            # and we are still running, then get rid of
            # tracing for this thread
            if self.quitting and self._threadRunning:
                sys.settrace( None )
                sys.setprofile( None )
            import threading
            self.__name = threading.currentThread().getName()
            retval = DebugBase.trace_dispatch( self, frame, event, arg )
        finally:
            self._dbgClient.unlockClient()

        return retval
