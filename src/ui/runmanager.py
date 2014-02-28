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

import os
from PyQt4.QtCore import QThread, SIGNAL, QObject, QTextCodec, QString
from PyQt4.QtGui import QDialog, QApplication
from PyQt4.QtNetwork import QTcpServer, QHostAddress, QAbstractSocket
from subprocess import Popen
from utils.run import getCwdCmdEnv, CMD_TYPE_RUN, TERM_REDIRECT
from utils.procfeedback import killProcess
from utils.globals import GlobalData
from utils.settings import Settings
from runparams import RunDialog
import logging, time
from editor.redirectedrun import RunConsoleTabWidget
from debugger.client.protocol_cdm_dbg import ( EOT, RequestContinue,
                                               StdoutStderrEOT, ResponseRaw,
                                               ResponseExit, ResponseStdout,
                                               ResponseStderr, RequestExit )


# Finish codes in addition to the normal exit code
KILLED = -1000000
DISCONNECTED = -2000000


NEXT_ID = 0
def getNextID():
    " Provides the next available ID "
    global NEXT_ID
    current = int( NEXT_ID )
    NEXT_ID += 1
    return current



class RemoteProcessWrapper( QThread ):
    " Thread which monitors the remote process "

    PROTOCOL_CONTROL = 0
    PROTOCOL_STDOUT = 1
    PROTOCOL_STDERR = 2

    def __init__( self, path ):
        QThread.__init__( self )
        self.__threadID = getNextID()
        self.__path = path
        self.__needRedirection = Settings().terminalType == TERM_REDIRECT
        self.__tcpServer = None
        self.__clientSocket = None
        self.__stopRequest = False
        self.__disconnectReceived = False
        self.__procExitReceived = False
        self.__retCode = -1
        self.__codec = QTextCodec.codecForName( "utf-8" )
        self.__protocolState = self.PROTOCOL_CONTROL
        self.__buffer = ""
        self.__proc = None
        self.__serverPort = None
        return

    def needRedirection( self ):
        " True if redirection required "
        return self.__needRedirection

    def threadID( self ):
        " Provides the thread ID "
        return self.__threadID

    def path( self ):
        " Provides the script path "
        return self.__path

    def run( self ):
        " Thread running function "
        params = GlobalData().getRunParameters( self.__path )
        if self.__needRedirection:
            try:
                self.__tcpServer = QTcpServer()
                self.connect( self.__tcpServer, SIGNAL( "newConnection()" ),
                              self.__newConnection )
                self.__tcpServer.listen( QHostAddress.LocalHost )
            except Exception, exc:
                logging.error( str( exc ) )

            self.__serverPort = self.__tcpServer.serverPort()
            workingDir, cmd, environment = getCwdCmdEnv( CMD_TYPE_RUN,
                                                         self.__path, params,
                                                         Settings().terminalType,
                                                         None, self.__serverPort )
        else:
            workingDir, cmd, environment = getCwdCmdEnv( CMD_TYPE_RUN,
                                                         self.__path, params,
                                                         Settings().terminalType )

        if self.__needRedirection:
            self.__runRedirected( workingDir, cmd, environment )
        else:
            self.__runDetached( workingDir, cmd, environment )
        return

    def __runRedirected( self, workingDir, cmd, environment ):
        " Runs a redirected IO process "
        try:
            self.__proc = Popen( cmd, shell = True,
                                 cwd = workingDir, env = environment )
        except Exception, exc:
            logging.error( str( exc ) )
            return

        # Wait till incoming connection
        self.__waitIncomingConnection()
        if not self.__clientSocket:
            logging.error( "Error running the script in the redirected IO mode: "
                           "incoming connection timeout." )
            return

        # Send the signal to notify the manager - should install the widget
        # and produce an IDE message
        self.emit( SIGNAL( 'Started' ), self.__threadID )

        self.connect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                      self.__parseClientLine )
        self.__parseClientLine()

        # Send runnee the 'start' message
        self.__sendStart()

        # Wait till runnee finishes
        while not self.__stopRequest and \
              not self.__disconnectReceived and \
              not self.__procExitReceived:
            time.sleep( 0.01 )
            QApplication.processEvents()

        try:
            self.__proc.wait()
        except:
            pass

        if self.__clientSocket:
            try:
                self.__clientSocket.close()
            except:
                pass

        # Process has finished some way:
        # - stop requested
        # - process finished
        # - process disconnected
        if self.__procExitReceived:
            signalValue = self.__retCode
        elif self.__stopRequest:
            signalValue = KILLED
        else:
            signalValue = DISCONNECTED
        self.emit( SIGNAL( 'Finished' ), self.__threadID, signalValue )
        return

    def __runDetached( self, workingDir, cmd, environment ):
        " Runs a detached process "
        self.__proc = None
        try:
            self.__proc = Popen( cmd, shell = True,
                          cwd = workingDir, env = environment )
            while not self.__stopRequest:
                time.sleep( 0.05 )
                if self.__proc.poll() is not None:
                    break
        except Exception, exc:
            logging.error( str( exc ) )

        try:
            self.__proc.wait()
        except:
            pass
        return

    def stop( self ):
        " Sets the thread stop request "
        if self.__clientSocket:
            try:
                self.disconnect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                                 self.__parseClientLine )
                self.disconnect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                                 self.__disconnected )
            except:
                pass

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

        self.__stopRequest = True
        return

    def __getChildPID( self ):
        " Provides the child process PID if redirected "
        if self.__serverPort is None:
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
                            return int( item )
                except:
                    pass
        return None

    def __newConnection( self ):
        " Handles new incoming connections "
        sock = self.__tcpServer.nextPendingConnection()
        self.__clientSocket = sock
        self.__clientSocket.setSocketOption( QAbstractSocket.KeepAliveOption, 1 )
        self.connect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                      self.__disconnected )
        self.disconnect( self.__tcpServer, SIGNAL( "newConnection()" ),
                         self.__newConnection )
        return

    def __waitIncomingConnection( self ):
        " Waits the incoming connection "
        startTime = time.time()
        while True:
            time.sleep( 0.01 )
            QApplication.processEvents()
            if self.__clientSocket:
                break
            if time.time() - startTime > 10:
                break
        return

    def __disconnected( self ):
        " Triggered when the client closed the connection "
        # It is possible that there are some data in the socket
        try:
            self.__parseClientLine()
        except:
            pass
        self.__disconnectReceived = True
        return

    def __sendStart( self ):
        " Sends the start command to the runnee "
        if self.__clientSocket:
            self.__clientSocket.write( RequestContinue + EOT )
            self.__clientSocket.flush()
        return

    def __sendExit( self ):
        " sends the exit command to the runnee "
        if self.__clientSocket:
            self.__clientSocket.write( RequestExit + EOT )
            self.__clientSocket.flush()
        return

    def __parseClientLine( self ):
        " Parses a single line from the running client "
        while self.__clientSocket and self.__clientSocket.bytesAvailable() > 0:
            qs = self.__clientSocket.readAll()
            us = self.__codec.fromUnicode( QString( qs ) )
            self.__buffer += str( us )

            # print "Received: '" + str( us ) + "'"

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
                return False
            else:
                value = self.__buffer
                self.__buffer = ""
                if isStdout:
                    self.emit( SIGNAL( 'ClientStdout' ), value )
                else:
                    self.emit( SIGNAL( 'ClientStderr' ), value )
                return False
        else:
            value = self.__buffer[ 0 : index ]
            self.__buffer = self.__buffer[ index + 2 : ]
            self.__protocolState = self.PROTOCOL_CONTROL
            if isStdout:
                self.emit( SIGNAL( 'ClientStdout' ), value )
            else:
                self.emit( SIGNAL( 'ClientStderr' ), value )
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
                self.__retCode = int( content )
            except:
                pass
            self.__procExitReceived = True
            self.__sendExit()
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
            self.__clientSocket.write( collectedString + "\n" )
            self.__clientSocket.flush()
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

        remoteProc = RemoteProcess()
        remoteProc.thread = RemoteProcessWrapper( path )
        self.connect( remoteProc.thread, SIGNAL( 'Finished' ),
                      self.__onProcessFinished )
        if Settings().terminalType == TERM_REDIRECT:
            remoteProc.widget = RunConsoleTabWidget( remoteProc.thread.threadID() )
            self.connect( remoteProc.thread, SIGNAL( 'Started' ),
                          self.__onProcessStarted )
            self.connect( remoteProc.thread, SIGNAL( 'ClientStdout' ),
                          remoteProc.widget.appendStdoutMessage )
            self.connect( remoteProc.thread, SIGNAL( 'ClientStderr' ),
                          remoteProc.widget.appendStderrMessage )
            self.connect( remoteProc.thread, SIGNAL( 'ClientRawInput' ),
                          remoteProc.widget.rawInput )
            self.connect( remoteProc.widget, SIGNAL( 'UserInput' ),
                          self.__onUserInput )
        else:
            remoteProc.widget = None
        remoteProc.isProfiling = False

        self.__processes.append( remoteProc )
        remoteProc.thread.start()
        return

    def profile( self, path ):
        " Profiles the given script with redirected IO "
        return

    def killAll( self ):
        " Stops all the threads and kills all the processes if needed "
        index = len( self.__processes ) - 1
        while index >= 0:
            item = self.__processes[ index ]
            if item.thread.needRedirection():
                item.thread.stop()
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
            if self.__processes[ index ].thread.needRedirection():
                count += 1
            index -= 1
        return count

    def kill( self, threadID ):
        " Kills a single process "
        index = self.__getProcessIndex( threadID )
        if index is None:
            return
        item = self.__processes[ index ]
        if not item.thread.needRedirection():
            return

        item.thread.stop()
        return

    def __getProcessIndex( self, threadID ):
        " Returns a process index in the list "
        for index, item in enumerate( self.__processes ):
            if item.thread.threadID() == threadID:
                return index
        return None

    def __onProcessFinished( self, threadID, retCode ):
        " Triggered when a process has finished "
        index = self.__getProcessIndex( threadID )
        if index is not None:
            item = self.__processes[ index ]
            if item.thread.needRedirection():
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
                    item.widget.appendIDEMessage( msg )
                    self.__mainWindow.updateIOConsoleTooltip( threadID, tooltip )
            del self.__processes[ index ]
        return

    def __onProcessStarted( self, threadID ):
        " Triggered when a process has started "
        index = self.__getProcessIndex( threadID )
        if index is not None:
            item = self.__processes[ index ]
            if item.widget:
                self.__mainWindow.installIOConsole( item.widget )
                item.widget.appendIDEMessage( "Script " + item.thread.path() + " started" )
        return

    def __onUserInput( self, threadID, userInput ):
        " Triggered when the user input is collected "
        index = self.__getProcessIndex( threadID )
        if index is not None:
            item = self.__processes[ index ]
            if item.thread.needRedirection():
                item.thread.userInput( userInput )
        return
