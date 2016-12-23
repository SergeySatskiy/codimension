#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2014-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Run/profile manager"""

import os
from PyQt5.QtCore import QObject, QTextCodec, Qt, QTimer
from PyQt5.QtGui import QDialog, QApplication, QCursor
from PyQt5.QtNetwork import QTcpServer, QHostAddress, QAbstractSocket
from subprocess import Popen
from utils.run import getCwdCmdEnv, CMD_TYPE_RUN, TERM_REDIRECT
from utils.procfeedback import killProcess
from utils.globals import GlobalData
from utils.settings import Settings
from runparams import RunDialog
import logging, time
from editor.redirectedrun import RunConsoleTabWidget
from debugger.client.protocol_cdm_dbg import (EOT, RequestContinue,
                                              StdoutStderrEOT, ResponseRaw,
                                              ResponseExit, ResponseStdout,
                                              ResponseStderr, RequestExit,
                                              ResponseProcID)


# Finish codes in addition to the normal exit code
KILLED = -1000000
DISCONNECTED = -2000000


NEXT_ID = 0
def getNextID():
    """Provides the next available ID"""
    global NEXT_ID
    current = int(NEXT_ID)
    NEXT_ID += 1
    return current


class RemoteProcessWrapper(QObject):

    """Wrapper to control the remote process"""

    PROTOCOL_CONTROL = 0
    PROTOCOL_STDOUT = 1
    PROTOCOL_STDERR = 2

    def __init__(self, path, serverPort):
        QObject.__init__(self)
        self.__procID = getNextID()
        self.__path = path
        self.__serverPort = serverPort
        self.__clientSocket = None
        self.__needRedirection = Settings().terminalType == TERM_REDIRECT
        self.__protocolState = self.PROTOCOL_CONTROL
        self.__buffer = ""
        self.__proc = None

    def needRedirection(self):
        """True if redirection required"""
        return self.__needRedirection

    def procID(self):
        """Provides the process ID"""
        return self.__procID

    def path(self):
        """Provides the script path"""
        return self.__path

    def start(self):
        """Starts the remote process"""
        params = GlobalData().getRunParameters(self.__path)
        if self.__needRedirection:
            workingDir, cmd, \
            environment = getCwdCmdEnv(CMD_TYPE_RUN, self.__path, params,
                                       Settings().terminalType,
                                       None, self.__serverPort, self.__procID)
        else:
            workingDir, cmd, \
            environment = getCwdCmdEnv( CMD_TYPE_RUN, self.__path, params,
                                        Settings().terminalType )

        try:
            self.__proc = Popen( cmd, shell = True,
                                 cwd = workingDir, env = environment )
        except Exception as exc:
            logging.error( str( exc ) )
            return False
        return True

    def setSocket( self, clientSocket ):
        " Called when an incoming connection has come "
        self.__clientSocket = clientSocket
        self.__connectSocket()
        self.__parseClientLine()

        # Send runnee the 'start' message
        self.__sendStart()
        return

    def stop( self ):
        " Kills the process "
        self.__disconnectSocket()
        self.__kill()
        self.emit( SIGNAL( 'Finished' ), self.__procID, KILLED )
        return

    def __connectSocket( self ):
        " Connects the socket slots "
        if self.__clientSocket:
            self.connect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                          self.__parseClientLine )
            self.connect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                          self.__disconnected )
        return

    def __disconnectSocket( self ):
        " Disconnects the socket related slots "
        if self.__clientSocket:
            try:
                self.disconnect( self.__clientSocket,
                                 SIGNAL( 'readyRead()' ),
                                 self.__parseClientLine )
                self.disconnect( self.__clientSocket,
                                 SIGNAL( 'disconnected()' ),
                                 self.__disconnected )
            except:
                pass
        return

    def __closeSocket( self ):
        " Closes the client socket if so "
        if self.__clientSocket:
            try:
                self.__clientSocket.close()
            except:
                pass
            self.__clientSocket = None
        return

    def wait( self ):
        " Waits for the process "
        if self.__proc is not None:
            try:
                self.__proc.wait()
            except:
                pass
        self.__closeSocket()
        return

    def waitDetached( self ):
        " Needs to avoid zombies "
        try:
            if self.__proc.poll() is not None:
                self.__proc.wait()
                return True
        except:
            return True
        return False

    def __kill( self ):
        " Kills the process or checks there is no process in memory "
        if self.__proc is not None:
            try:
                self.__proc.kill()
            except:
                pass

        childPID = self.__getChildPID()
        while childPID is not None:
            try:
                # Throws an exception if cannot kill the process
                killProcess( childPID )
            except:
                pass
            nextPID = self.__getChildPID()
            if nextPID == childPID:
                break
            childPID = nextPID

        # Here: the process killed
        self.wait()
        self.__proc = None
        return

    def __getChildPID( self ):
        " Provides the child process PID if redirected "
        if self.__serverPort is None or self.__procID is None:
            return None

        for item in os.listdir( "/proc" ):
            if item.isdigit():
                try:
                    f = open( "/proc/" + item + "/cmdline", "r" )
                    content = f.read()
                    f.close()

                    if "client/client_cdm_run.py" in content:
                        if "-p" in content and \
                           str( self.__serverPort ) in content:
                            if "-i" in content and \
                                str( self.__procID ) in content:
                                return int( item )
                except:
                    pass
        return None

    def __disconnected( self ):
        " Triggered when the client closed the connection "
        self.__kill()
        self.emit( SIGNAL( 'Finished' ), self.__procID, DISCONNECTED )
        return

    def __sendStart( self ):
        " Sends the start command to the runnee "
        if self.__clientSocket:
            data = RequestContinue + EOT
            self.__clientSocket.write( data )
        return

    def __sendExit( self ):
        " sends the exit command to the runnee "
        self.__disconnectSocket()
        if self.__clientSocket:
            data = RequestExit + EOT
            QApplication.processEvents()
            self.__clientSocket.write( data )
            self.__clientSocket.waitForBytesWritten()
        return

    def __parseClientLine( self ):
        " Parses a single line from the running client "
        while self.__clientSocket and self.__clientSocket.bytesAvailable() > 0:
            qs = self.__clientSocket.readAll()
            us = CODEC.fromUnicode( str( qs ) )
            self.__buffer += str( us )

            tryAgain = True
            while tryAgain:
                if self.__protocolState == self.PROTOCOL_CONTROL:
                    tryAgain = self.__processControlState()
                elif self.__protocolState == self.PROTOCOL_STDOUT:
                    tryAgain = self.__processStdoutStderrState( True )
                elif self.__protocolState == self.PROTOCOL_STDERR:
                    tryAgain = self.__processStdoutStderrState( False )
                else:
                    raise Exception( "Unexpected protocol state" )
        return

    def __processStdoutStderrState( self, isStdout ):
        " Analyzes receiving buffer in the STDOUT/STDERR state "
        # Collect till "\x04\x04"
        index = self.__buffer.find( StdoutStderrEOT )
        if index == -1:
            # End has not been found
            if self.__buffer.endswith( '\x04' ):
                value = self.__buffer[ : -1 ]
                self.__buffer = '\x04'
                if isStdout:
                    self.emit( SIGNAL( 'ClientStdout' ), value )
                else:
                    self.emit( SIGNAL( 'ClientStderr' ), value )
                QApplication.processEvents()
                return False

            # Partial stdout/stderr received
            value = self.__buffer
            self.__buffer = ""
            if isStdout:
                self.emit( SIGNAL( 'ClientStdout' ), value )
            else:
                self.emit( SIGNAL( 'ClientStderr' ), value )
            QApplication.processEvents()
            return False

        # Here stdout/stderr has been received in full
        value = self.__buffer[ 0 : index ]
        self.__buffer = self.__buffer[ index + 2 : ]
        self.__protocolState = self.PROTOCOL_CONTROL
        if isStdout:
            self.emit( SIGNAL( 'ClientStdout' ), value )
        else:
            self.emit( SIGNAL( 'ClientStderr' ), value )
        QApplication.processEvents()
        return True

    def __processControlState( self ):
        " Analyzes receiving buffer in the CONTROL state "
        # Buffer is going to start with >ZZZ< message and ends with EOT
        index = self.__buffer.find( EOT )
        if index == -1:
            return False

        line = self.__buffer[ 0 : index ]
        self.__buffer = self.__buffer[ index + len( EOT ) : ]

        if not line.startswith( '>' ):
            print "Unexpected message received (no '>' at the beginning): '" + \
                  line + "'"
            return self.__buffer != ""

        cmdIndex = line.find( '<' )
        if cmdIndex == -1:
            print "Unexpected message received (no '<' found): '" + line + "'"
            return self.__buffer != ""

        cmd = line[ 0 : cmdIndex + 1 ]
        content = line[ cmdIndex + 1 : ]

        if cmd == ResponseRaw:
            prompt, echo = eval( content )
            self.emit( SIGNAL( 'ClientRawInput' ), prompt, echo )
            return self.__buffer != ""

        if cmd == ResponseExit:
            try:
                retCode = int( content )
            except:
                # Must never happened
                retCode = -1
            self.__sendExit()
            self.emit( SIGNAL( 'Finished' ), self.__procID, retCode )
            QApplication.processEvents()
            return self.__buffer != ""

        if cmd == ResponseStdout:
            self.__protocolState = self.PROTOCOL_STDOUT
            return self.__buffer != ""

        if cmd == ResponseStderr:
            self.__protocolState = self.PROTOCOL_STDERR
            return self.__buffer != ""

        print "Unexpected message received (no control match): '" + line + "'"
        return self.__buffer != ""

    def userInput( self, collectedString ):
        " Called when the user finished input "
        if self.__clientSocket:
            data = collectedString.encode( "utf8" ) + "\n"
            self.__clientSocket.write( data )
        return


class RemoteProcess:
    " Stores attributes of a single process "

    def __init__( self ):
        self.procWrapper = None
        self.widget = None
        self.isProfiling = False
        return


class RunManager( QObject ):
    " Manages the external running processes "

    def __init__( self, mainWindow ):
        QObject.__init__( self )
        self.__mainWindow = mainWindow
        self.__processes = []

        self.__tcpServer = QTcpServer()
        self.connect( self.__tcpServer, SIGNAL( "newConnection()" ),
                      self.__newConnection )
        self.__tcpServer.listen( QHostAddress.LocalHost )

        self.__waitTimer = QTimer( self )
        self.__waitTimer.setSingleShot( True )
        self.connect( self.__waitTimer, SIGNAL( 'timeout()' ),
                      self.__onWaitImer )
        return

    def __newConnection( self ):
        " Handles new incoming connections "
        clientSocket = self.__tcpServer.nextPendingConnection()
        clientSocket.setSocketOption( QAbstractSocket.KeepAliveOption, 1 )
        clientSocket.setSocketOption( QAbstractSocket.LowDelayOption, 1 )
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        self.__waitForHandshake( clientSocket )
        QApplication.restoreOverrideCursor()
        return

    def __waitForHandshake( self, clientSocket ):
        " Waits for the message with the proc ID "
        if clientSocket.waitForReadyRead( 1000 ):
            qs = clientSocket.readAll()
            us = str( CODEC.fromUnicode( str( qs ) ) )
            if not us.endswith( EOT ):
                return

            line = us[ 0 : -len( EOT ) ]
            if not line.startswith( '>' ):
                return

            cmdIndex = line.find( '<' )
            if cmdIndex == -1:
                return

            cmd = line[ 0 : cmdIndex + 1 ]
            content = line[ cmdIndex + 1 : ]
            if cmd != ResponseProcID:
                return

            # It could only be a redirected process
            procID = int( content )
            procIndex = self.__getProcessIndex( procID )
            if procIndex is not None:
                self.__onProcessStarted( procID )
                self.__processes[ procIndex ].procWrapper.setSocket(
                                                            clientSocket )
        return

    def run( self, path, needDialog ):
        " Runs the given script with redirected IO "
        if needDialog:
            params = GlobalData().getRunParameters( path )
            termType = Settings().terminalType
            profilerParams = Settings().getProfilerSettings()
            debuggerParams = Settings().getDebuggerSettings()
            dlg = RunDialog( path, params, termType,
                             profilerParams, debuggerParams, "Run",
                             self.__mainWindow )
            if dlg.exec_() != QDialog.Accepted:
                return
            GlobalData().addRunParams( path, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType

        # The parameters for the run are ready.
        # Start the run business.
        remoteProc = RemoteProcess()
        remoteProc.isProfiling = False
        remoteProc.procWrapper = RemoteProcessWrapper( path,
                                        self.__tcpServer.serverPort() )
        if Settings().terminalType == TERM_REDIRECT:
            remoteProc.widget = RunConsoleTabWidget(
                                        remoteProc.procWrapper.procID() )
            self.connect( remoteProc.procWrapper, SIGNAL( 'ClientStdout' ),
                          remoteProc.widget.appendStdoutMessage )
            self.connect( remoteProc.procWrapper, SIGNAL( 'ClientStderr' ),
                          remoteProc.widget.appendStderrMessage )
            self.connect( remoteProc.procWrapper, SIGNAL( 'ClientRawInput' ),
                          remoteProc.widget.rawInput )
            self.connect( remoteProc.widget, SIGNAL( 'UserInput' ),
                          self.__onUserInput )
        else:
            remoteProc.widget = None

        self.connect( remoteProc.procWrapper, SIGNAL( 'Finished' ),
                      self.__onProcessFinished )
        self.__processes.append( remoteProc )
        if remoteProc.procWrapper.start() == False:
            # Failed to start - the fact is logged, just remove from the list
            procIndex = self.__getProcessIndex( remoteProc.procWrapper.procID() )
            if procIndex is not None:
                del self.__processes[ procIndex ]
        else:
            if Settings().terminalType != TERM_REDIRECT:
                if not self.__waitTimer.isActive():
                    self.__waitTimer.start( 1000 )
        return

    def profile( self, path ):
        " Profiles the given script with redirected IO "
        return

    def killAll( self ):
        " Kills all the processes if needed "
        index = len( self.__processes ) - 1
        while index >= 0:
            item = self.__processes[ index ]
            if item.procWrapper.needRedirection():
                item.procWrapper.stop()
            index -= 1

        # Wait till all the processes stopped
        count = self.__getDetachedCount()
        while count > 0:
            time.sleep( 0.01 )
            QApplication.processEvents()
            count = self.__getDetachedCount()
        return

    def __getDetachedCount( self ):
        " Return the number of detached processes still running "
        count = 0
        index = len( self.__processes ) - 1
        while index >= 0:
            if self.__processes[ index ].procWrapper.needRedirection():
                count += 1
            index -= 1
        return count

    def kill( self, procID ):
        " Kills a single process "
        index = self.__getProcessIndex( procID )
        if index is None:
            return
        item = self.__processes[ index ]
        if not item.procWrapper.needRedirection():
            return

        item.procWrapper.stop()
        return

    def __getProcessIndex( self, procID ):
        " Returns a process index in the list "
        for index, item in enumerate( self.__processes ):
            if item.procWrapper.procID() == procID:
                return index
        return None

    def __onProcessFinished( self, procID, retCode ):
        " Triggered when a process has finished "
        index = self.__getProcessIndex( procID )
        if index is not None:
            item = self.__processes[ index ]
            if item.procWrapper.needRedirection():
                if item.widget:
                    item.widget.scriptFinished()
                    if retCode == KILLED:
                        msg  = "Script killed"
                        tooltip = "killed"
                    elif retCode == DISCONNECTED:
                        msg = "Connection lost to the script process"
                        tooltip = "connection lost"
                    else:
                        msg = "Script finished with exit code " + str( retCode )
                        tooltip = "finished, exit code " + str( retCode )
                        item.procWrapper.wait()
                    item.widget.appendIDEMessage( msg )
                    self.__mainWindow.updateIOConsoleTooltip( procID, tooltip )
            del self.__processes[ index ]
        return

    def __onProcessStarted( self, procID ):
        " Triggered when a process has started "
        index = self.__getProcessIndex( procID )
        if index is not None:
            item = self.__processes[ index ]
            if item.widget:
                self.__mainWindow.installIOConsole( item.widget )
                item.widget.appendIDEMessage( "Script " +
                                              item.procWrapper.path() +
                                              " started" )
        return

    def __onUserInput( self, procID, userInput ):
        " Triggered when the user input is collected "
        index = self.__getProcessIndex( procID )
        if index is not None:
            item = self.__processes[ index ]
            if item.procWrapper.needRedirection():
                item.procWrapper.userInput( userInput )
        return

    def __onWaitImer( self ):
        " Triggered when the timer fired "
        needNewTimer = False
        index = len( self.__processes ) - 1
        while index >= 0:
            item = self.__processes[ index ]
            if item.procWrapper.needRedirection() == False:
                if item.procWrapper.waitDetached() == True:
                    del self.__processes[ index ]
                else:
                    needNewTimer = True
            index -= 1
        if needNewTimer:
            self.__waitTimer.start( 1000 )
        return
