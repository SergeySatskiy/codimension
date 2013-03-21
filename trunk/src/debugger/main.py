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
from subprocess import Popen
from PyQt4.QtCore import SIGNAL, QTimer, QObject, Qt
from PyQt4.QtGui import QApplication, QCursor
from PyQt4.QtNetwork import QTcpServer, QHostAddress, QAbstractSocket

from utils.globals import GlobalData
from utils.run import getCwdCmdEnv, CMD_TYPE_DEBUG
from utils.settings import Settings


class CodimensionDebugger( QObject ):
    " Debugger server implementation "

    STATE_IDLE = 0
    STATE_PROLOGUE = 1
    STATE_DEBUGGING = 2
    STATE_FINISHING = 3

    def __init__( self, mainWindow ):
        QObject.__init__( self )

        # To control the user interface elements
        self.__mainWindow = mainWindow
        self.__state = self.STATE_IDLE

        self.__procFeedbackSocket = None
        self.__procFeedbackPort = None
        self.__tcpServer = None
        self.__clientSocket = None
        self.__procWatchTimer = None
        self.__procPID = None

        return

    def startDebugging( self, fileName ):
        " Starts debugging a script "
        if self.__state != self.STATE_IDLE:
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
        self.__state = self.STATE_PROLOGUE
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

        print "Debug working dir: " + str( workingDir )
        print "Debug command: " + str( cmd )
        print "Environment: " + str( environment )

        # Run the client -  exception is processed in the outer scope
#        Popen( cmd, shell = True, cwd = workingDir, env = environment )

        # Wait for the child PID


        # Wait till the client incoming connection

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

    def __newConnection( self ):
        " Handles new incoming connections "
        sock = self.__tcpServer.nextPendingConnection()
        if self.__state != self.STATE_PROLOGUE or \
           self.__clientSocket is not None:
            sock.abort()
            return

        self.__clientSocket = sock
        self.__clientSocket.setSocketOption( QAbstractSocket.KeepAliveOption, 1 )
        self.connect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                      self.__disconnected )
        self.connect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                      self.__parseClientLine )

        print "New connection has been accepted"
        return

    def __parseClientLine( self ):
        print "Client sent a packet "

    def __disconnected( self ):
        print "Client disconnected"

    def stopDebugging( self ):
        " Stops debugging "
        if self.__state in [ self.STATE_IDLE, self.STATE_FINISHING ]:
            return

        self.__state = self.STATE_FINISHING

        # Close the process feedback socket if so
        if self.__procFeedbackSocket is not None:
            self.__procFeedbackSocket.close()
        self.__procFeedbackSocket = None
        self.__procFeedbackPort = None

        # Close the TCP server
        if self.__tcpServer is not None:
            self.disconnect( self.__tcpServer, SIGNAL( "newConnection()" ),
                             self.__newConnection )
            self.__tcpServer.close()
        self.__tcpServer = None
        if self.__clientSocket is not None:
            self.disconnect( self.__clientSocket, SIGNAL( 'disconnected()' ),
                             self.__disconnected )
            self.disconnect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                             self.__parseClientLine )
            self.__clientSocket.close()
        self.__clientSocket = None

        self.__mainWindow.switchDebugMode( False )
        self.__state = self.STATE_IDLE
        return
