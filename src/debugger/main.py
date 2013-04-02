#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Debugger server "

import socket
import logging
import errno
import time
from subprocess import Popen
from PyQt4.QtCore import SIGNAL, QTimer, QObject, Qt, QTextCodec, QString
from PyQt4.QtGui import QApplication, QCursor
from PyQt4.QtNetwork import QTcpServer, QHostAddress, QAbstractSocket

from utils.globals import GlobalData
from utils.run import getCwdCmdEnv, CMD_TYPE_DEBUG
from utils.settings import Settings
from utils.procfeedback import decodeMessage, isProcessAlive, killProcess
from client.protocol import ( EOT, RequestStep, RequestStepOver, RequestStepOut,
                              RequestShutdown, ResponseLine, ResponseStack,
                              RequestContinue, RequestThreadList,
                              RequestVariables, ResponseThreadList,
                              ResponseVariables )


POLL_INTERVAL = 0.1
HANDSHAKE_TIMEOUT = 15
BRUTAL_SHUTDOWN_TIMEOUT = 0.2
GRACEFUL_SHUTDOWN_TIMEOUT = 5


class CodimensionDebugger( QObject ):
    " Debugger server implementation "

    STATE_STOPPED = 0
    STATE_PROLOGUE = 1
    STATE_IN_CLIENT = 2
    STATE_IN_IDE = 3
    STATE_FINISHING = 4
    STATE_BRUTAL_FINISHING = 5

    def __init__( self, mainWindow ):
        QObject.__init__( self )

        # To control the user interface elements
        self.__mainWindow = mainWindow
        self.__state = self.STATE_STOPPED

        self.__procFeedbackSocket = None
        self.__procFeedbackPort = None
        self.__tcpServer = None
        self.__clientSocket = None
        self.__procPID = None
        self.__disconnectReceived = None
        self.__stopAtFirstLine = None
        self.__translatePath = None

        self.__codec = QTextCodec.codecForName( "utf-8" )
        return

    def __changeDebuggerState( self, newState ):
        " Changes the debugger state "
        self.__state = newState
        self.emit( SIGNAL( "DebuggerStateChanged" ), newState )
        return

    def startDebugging( self, fileName ):
        " Starts debugging a script "
        if self.__state != self.STATE_STOPPED:
            logging.error( "Cannot start debug session. "
                           "The previous one has not finished yet." )
            return

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            self.__initiatePrologue( fileName )
        except Exception, exc:
            logging.error( str( exc ) )
            self.stopDebugging()
        QApplication.restoreOverrideCursor()
        return

    def __initiatePrologue( self, fileName ):
        " Prologue is starting here "
        self.__changeDebuggerState( self.STATE_PROLOGUE )
        self.__disconnectReceived = False

        # For the time being there is no path translation
        self.__translatePath = self.__noPathTranslation

        self.__mainWindow.switchDebugMode( True )

        self.__createProcfeedbackSocket()
        self.__createTCPServer()

        params = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv(
                                            CMD_TYPE_DEBUG,
                                            fileName, params,
                                            Settings().terminalType,
                                            self.__procFeedbackPort,
                                            self.__tcpServer.serverPort() )

        debugSettings = Settings().getDebuggerSettings()
        self.__stopAtFirstLine = debugSettings.stopAtFirstLine

        print "Debug working dir: " + str( workingDir )
        print "Debug command: " + str( cmd )
        print "Environment: " + str( environment )

        # Run the client -  exception is processed in the outer scope
        Popen( cmd, shell = True, cwd = workingDir, env = environment )

        # Wait for the child PID
        self.__waitChildPID()

        # Wait till the client incoming connection
        self.__waitIncomingConnection()
        return

    def __waitIncomingConnection( self ):
        " Waits till the debugged program comes up "
        startTime = time.time()
        while True:
            time.sleep( POLL_INTERVAL )
            QApplication.processEvents()

            # It does not matter how the state was changed - the user has
            # interrupted it, the client has connected
            if self.__state != self.STATE_PROLOGUE:
                break

            if not isProcessAlive( self.__procPID ):
                # Stop it brutally
                self.stopDebugging( True )
                break

            if time.time() - startTime > HANDSHAKE_TIMEOUT:
                raise Exception( "Handshake timeout: debugged "
                                 "program did not come up." )
        return

    def __waitChildPID( self ):
        " Waits for the child PID on the feedback socket "
        startTime = time.time()
        while True:
            time.sleep( POLL_INTERVAL )
            QApplication.processEvents()

            data = self.__getProcfeedbackData()
            if data != "":
                # We've got the message, extract the PID to watch
                msgParts = decodeMessage( data )
                if len( msgParts ) != 1:
                    raise Exception( "Unexpected handshake message: '" +
                                     data + "'. Expected debuggee child "
                                     "process PID." )
                try:
                    self.__procPID = int( msgParts[ 0 ] )
                    break   # Move to stage 2
                except:
                    raise Exception( "Broken handshake message: '" +
                                     data + ". Cannot convert debuggee "
                                     "child process PID to integer." )

            if time.time() - startTime > HANDSHAKE_TIMEOUT:
                raise Exception( "Handshake timeout: "
                                 "error spawning process to profile" )
        print "Debuggee PID: " + str( self.__procPID )
        return


    def __createProcfeedbackSocket( self ):
        " Creates the process feedback socket "
        self.__procFeedbackSocket = socket.socket( socket.AF_INET,
                                                   socket.SOCK_DGRAM )

        # Zero port allows the system to pick any available port
        self.__procFeedbackSocket.bind( ( "127.0.0.1", 0 ) )
        self.__procFeedbackPort = self.__procFeedbackSocket.getsockname()[ 1 ]
        return

    def __createTCPServer( self ):
        " Creates the TCP server for the commands exchange "
        self.__tcpServer = QTcpServer()
        self.connect( self.__tcpServer, SIGNAL( "newConnection()" ),
                      self.__newConnection )

        # Port will be assigned automatically
        self.__tcpServer.listen( QHostAddress.LocalHost )
        return

    def __getProcfeedbackData( self ):
        " Checks if data avalable in the socket and reads it if so "
        try:
            data = self.__procFeedbackSocket.recv( 1024, socket.MSG_DONTWAIT )
        except socket.error, excpt:
            if excpt[ 0 ] == errno.EWOULDBLOCK:
                return ""
            raise
        return data

    def __newConnection( self ):
        " Handles new incoming connections "
        sock = self.__tcpServer.nextPendingConnection()
        if self.__state != self.STATE_PROLOGUE or \
           self.__clientSocket is not None:
            sock.abort()
            return

        self.__clientSocket = sock
        self.__clientSocket.setSocketOption( QAbstractSocket.KeepAliveOption,
                                             1 )
        self.connect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                      self.__disconnected )
        self.connect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                      self.__parseClientLine )

        self.__changeDebuggerState( self.STATE_IN_CLIENT )
        print "New connection has been accepted"
        return

    def __sendCommand( self, command ):
        " Sends a command to the debuggee "
        if self.__clientSocket:
            self.__clientSocket.write( command.encode( 'utf8' ) )
            self.__clientSocket.flush()
            return

        raise Exception( "Cannot send command to debuggee - "
                         "no connection established. Command: " + command )

    def __parseClientLine( self ):
        " Triggered when something has been received from the client "
        while self.__clientSocket and self.__clientSocket.canReadLine():
            qs = self.__clientSocket.readLine()
            us = self.__codec.fromUnicode( QString( qs ) )
            line = str( us )
            if line.endswith( EOT ):
                line = line[ : -len( EOT ) ]
                if not line:
                    continue

            print "Server received: " + line

            eoc = line.find( '<' ) + 1

            # Deal with case where user has written directly to stdout
            # or stderr, but not line terminated and we stepped over the
            # write call, in that case the >line< will not be the first
            # string read from the socket...
            boc = line.find( '>' )
            if boc > 0 and eoc > boc:
                self.emit( SIGNAL( 'ClientOutput' ), line[ : boc ] )
                line = line[ boc : ]
                eoc = line.find( '<' ) + 1
                boc = line.find( '>' )

            if boc >= 0 and eoc > boc:
                resp = line[ boc : eoc ]

                if resp == ResponseLine or resp == ResponseStack:
                    stack = eval( line[ eoc : -1 ] )
                    for s in stack:
                        s[ 0 ] = self.__translatePath( s[ 0 ], True )

                    if self.__stopAtFirstLine:
                        cf = stack[ 0 ]
                        self.emit( SIGNAL( 'ClientLine' ), cf[ 0 ], int( cf[ 1 ] ),
                                   resp == ResponseStack )
                        self.emit( SIGNAL( 'ClientStack' ), stack )
                    else:
                        self.__stopAtFirstLine = True
                        QTimer.singleShot( 0, self.remoteContinue )

                    if resp == ResponseLine:
                        self.__changeDebuggerState( self.STATE_IN_IDE )
                    continue

                if resp == ResponseThreadList:
                    currentThreadID, threadList = eval( line[ eoc : -1 ] )
                    self.emit( SIGNAL( 'ClientThreadList' ),
                               currentThreadID, threadList )
                    continue

                if resp == ResponseVariables:
                    vlist = eval( line[ eoc : -1 ] )
                    scope = vlist[ 0 ]
                    try:
                        variables = vlist[ 1 : ]
                    except IndexError:
                        variables = []
                    self.emit( SIGNAL( 'ClientVariables' ), scope, variables )
                    continue

        return


    def __disconnected( self ):
        " Triggered when the client closed the connection "
        print "Client disconnected"
        # Note: if the stopDebugging call is done synchronously - you've got
        #       a core dump!
        self.__disconnectReceived = True
        QTimer.singleShot( 1, self.stopDebugging )
        return

    def stopDebugging( self, brutal = False ):
        " Stops debugging "
        if self.__state in [ self.STATE_STOPPED, self.STATE_BRUTAL_FINISHING ]:
            return
        if not brutal and self.__state == self.STATE_FINISHING:
            return

        if brutal:
            self.__changeDebuggerState( self.STATE_BRUTAL_FINISHING )
        else:
            self.__changeDebuggerState( self.STATE_FINISHING )
        QApplication.processEvents()

        # Close the process feedback socket if so
        if self.__procFeedbackSocket is not None:
            self.__procFeedbackSocket.close()
        self.__procFeedbackSocket = None
        self.__procFeedbackPort = None

        # Close the opened socket if so
        if self.__clientSocket is not None:
            self.disconnect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                             self.__parseClientLine )
            self.__sendCommand( RequestShutdown + "\n" )

            # Give the client a chance to shutdown itself
            if brutal:
                timeout = BRUTAL_SHUTDOWN_TIMEOUT
            else:
                timeout = GRACEFUL_SHUTDOWN_TIMEOUT
            start = time.time()
            while True:
                time.sleep( POLL_INTERVAL )
                QApplication.processEvents()
                if self.__disconnectReceived:
                    # The client has shut itself down
                    break
                if time.time() - start > timeout:
                    # Timeout is over, don't wait any more
                    break
            self.disconnect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                             self.__disconnected )
            self.__clientSocket.close()
        self.__clientSocket = None
        print "client socket closed"

        # Close the TCP server if so
        if self.__tcpServer is not None:
            self.disconnect( self.__tcpServer, SIGNAL( "newConnection()" ),
                             self.__newConnection )
            self.__tcpServer.close()
        self.__tcpServer = None

        # Deal with the process if so
        if self.__procPID is not None:
            if brutal:
                try:
                    # Throws exceptions if cannot kill the process
                    killProcess( self.__procPID )
                except:
                    pass
        self.__procPID = None

        self.__mainWindow.switchDebugMode( False )
        self.__changeDebuggerState( self.STATE_STOPPED )
        return


    def __noPathTranslation( self, fname, remote2local = True ):
        """ Dump to support later path translations """
        return unicode( fname )

    def remoteStep( self ):
        " Single step in the debugged program "
        self.__changeDebuggerState( self.STATE_IN_CLIENT )
        self.__sendCommand( RequestStep + '\n' )
        return

    def remoteStepOver( self ):
        " Step over the debugged program "
        self.__changeDebuggerState( self.STATE_IN_CLIENT )
        self.__sendCommand( RequestStepOver + '\n' )
        return

    def remoteStepOut( self ):
        " Step out the debugged program "
        self.__changeDebuggerState( self.STATE_IN_CLIENT )
        self.__sendCommand( RequestStepOut + '\n' )
        return

    def remoteContinue( self, special = False ):
        " Continues the debugged program "
        self.__changeDebuggerState( self.STATE_IN_CLIENT )
        if special:
            self.__sendCommand( RequestContinue + '1\n' )
        else:
            self.__sendCommand( RequestContinue + '0\n' )
        return

    def remoteThreadList( self ):
        " Provides the threads list "
        self.__sendCommand( RequestThreadList + "\n" )
        return

    def remoteClientVariables( self, scope, framenr = 0 ):
        """ Provides the client variables.
            scope - 0 => local, 1 => global """
        self.__sendCommand( RequestVariables +
                            str( framenr ) + ", " + str( scope ) + "\n" )
        return

