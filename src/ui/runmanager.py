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


class RemoteProcessProxy( QThread ):
    " Thread which monitors the remote process "

    def __init__( self, cmdLine, workingDir, environment, needRedirection ):
        self.__cmdLine = cmdLine
        self.__workingDir = workingDir
        self.__environment = environment
        self.__needRedirection = needRedirection
        self.__stopRequest = False
        return

    def needRedirection( self ):
        return self.__needRedirection

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


class RemoteProcess:
    " Stores attributes of a single process "

    def __init__( self ):
        self.thread = None
        self.widget = None
        self.isProfiling = False
        return


class RunManager:
    " Manages the external running processes "

    def __init__( self, mainWindow ):
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
        remoteProc.thread = RemoteProcessProxy( cmd, workingDir, environment,
                                    Settings().terminalType == TERM_REDIRECT )
        if Settings().terminalType == TERM_REDIRECT:
            # TODO: Create a widget
            # TODO: Connect signals
            pass
        else:
            # TODO: Connect signals
            remoteProc.widget = None
        remoteProc.isProfiling = False

        self.__processes.append( remoteProc )
        remoteProc.run()
        return

    def profile( self, path ):
        " Profiles the given script with redirected IO "
        return

    def close( self ):
        " Stops all the threads and kills all the processes if needed "
        return
