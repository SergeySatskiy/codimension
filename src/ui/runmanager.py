#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2014  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" Run/profile manager """

from PyQt4.QtCore import QThread, SIGNAL
from PyQt4.QtGui import QDialog
from subprocess import Popen
from utils.run import getCwdCmdEnv, CMD_TYPE_RUN, TERM_REDIRECT
from utils.globals import GlobalData
from utils.settings import Settings
from runparams import RunDialog
import logging, time


NEXT_ID = 0
def getNextID( self ):
    " Provides the next available ID "
    global NEXT_ID
    current = int( NEXT_ID )
    NEXT_ID += 1
    return current



class RemoteProcessWrapper( QThread ):
    " Thread which monitors the remote process "

    def __init__( self, cmdLine, workingDir,
                        environment, needRedirection ):
        QThread.__init__( self )
        self.__threadID = getNextID()
        self.__cmdLine = cmdLine
        self.__workingDir = workingDir
        self.__environment = environment
        self.__needRedirection = needRedirection
        self.__stopRequest = False
        self.__retCode = 0

        self.connect( self, SIGNAL( 'finished()' ),
                      self.__threadFinished )
        return

    def needRedirection( self ):
        " True if redirection required "
        return self.__needRedirection

    def threadID( self ):
        " Provides the thread ID "
        return self.__threadID

    def run( self ):
        " Thread running function "
        if self.__needRedirection:
            self.__runRedirected()
        else:
            self.__runDetached()
        return

    def __runRedirected( self ):
        " Runs a redirected IO process "
        return

    def __runDetached( self ):
        " Runs a detached process "
        proc = None
        try:
            proc = Popen( self.__cmdLine, shell = True,
                          cwd = self.__workingDir, env = self.__environment )
            while not self.__stopRequest:
                time.sleep( 0.05 )
                if proc.poll() is not None:
                    break
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def stop( self ):
        " Sets the thread stop request "
        self.__stopRequest = True
        return

    def __threadFinished( self ):
        " Triggered when the thread has finished "
        self.emit( SIGNAL( 'ProcessFinished' ), self.__threadID,
                   self.__retCode )
        return


class RemoteProcess:
    " Stores attributes of a single process "

    def __init__( self ):
        self.thread = None
        self.widget = None
        self.isProfiling = False
        return


class RunManager( QObject ):
    " Manages the external running processes "

    def __init__( self, mainWindow ):
        QObject.__init__( self )
        self.__mainWindow = mainWindow
        self.__processes = []
        return

    def run( self, path, needDialog ):
        " Runs the given script with redirected IO "
        if needDialog:
            params = GlobalData().getRunParameters( path )
            termType = Settings().terminalType
            profilerParams = Settings().getProfilerSettings()
            debuggerParams = Settings().getDebuggerSettings()
            dlg = RunDialog( path, params, termType,
                             profilerParams, debuggerParams, "Run" )
            if dlg.exec_() != QDialog.Accepted:
                return
            GlobalData().addRunParams( path, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType


        params = GlobalData().getRunParameters( path )
        workingDir, cmd, environment = getCwdCmdEnv( CMD_TYPE_RUN,
                                                     path, params,
                                                     Settings().terminalType )

        remoteProc = RemoteProcess()
        remoteProc.thread = RemoteProcessWrapper(
                                cmd, workingDir, environment,
                                Settings().terminalType == TERM_REDIRECT )
        self.connect( remoteProc.thread, SIGNAL( 'ProcessFinished' ),
                      self.__onProcessFinished )
        if Settings().terminalType == TERM_REDIRECT:
            # TODO: Create a widget
            # TODO: Connect signals
            pass
        else:
            # TODO: Connect signals
            remoteProc.widget = None
        remoteProc.isProfiling = False

        self.__processes.append( remoteProc )
        remoteProc.thread.start()
        return

    def profile( self, path ):
        " Profiles the given script with redirected IO "
        return

    def close( self ):
        " Stops all the threads and kills all the processes if needed "
        return

    def __onProcessFinished( self, threadID, retCode ):
        " Triggered when a process has finished "
        found = None
        for index, item in enumerate( self.__processes ):
            if item.thread.threadID() == threadID:
                found = index
                break

        if found:
            # item holds the process description
            del self.__processes[ index ]
        return

