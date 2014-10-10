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
import os.path
from subprocess import Popen
from PyQt4.QtCore import SIGNAL, QTimer, QObject, Qt, QTextCodec, QString, QModelIndex, pyqtSignal
from PyQt4.QtGui import QApplication, QCursor, QMessageBox, QDialog
from PyQt4.QtNetwork import QTcpServer, QHostAddress, QAbstractSocket

from utils.globals import GlobalData
from utils.run import getCwdCmdEnv, CMD_TYPE_DEBUG, getUserShell, TERM_REDIRECT
from utils.settings import Settings
from utils.procfeedback import decodeMessage, isProcessAlive, killProcess
from utils.pixmapcache import PixmapCache
from client.protocol_cdm_dbg import ( EOT, RequestStep, RequestStepOver, RequestStepOut,
                                      RequestShutdown, ResponseLine, ResponseStack,
                                      RequestContinue, RequestThreadList,
                                      RequestVariables, ResponseThreadList,
                                      ResponseVariables, RequestVariable,
                                      ResponseVariable, RequestExec, RequestEval,
                                      RequestBreak, ResponseException, RequestForkTo,
                                      ResponseForkTo, RequestStack, ResponseSyntax,
                                      ResponseExit, PassiveStartup, RequestBreakEnable,
                                      RequestBreakIgnore, ResponseClearBreak,
                                      ResponseBPConditionError, ResponseEval,
                                      ResponseEvalOK, ResponseEvalError,
                                      ResponseExec, ResponseExecError,
                                      RequestThreadSet, ResponseThreadSet,
                                      ResponseRaw, StdoutStderrEOT,
                                      ResponseStdout, ResponseStderr, ResponseExecOK )

from bputils import getBreakpointLines
from breakpointmodel import BreakPointModel
from watchpointmodel import WatchPointModel
from editbreakpoint import BreakpointEditDialog

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

    PROTOCOL_CONTROL = 0
    PROTOCOL_EVALEXEC = 1
    PROTOCOL_STDOUT = 2
    PROTOCOL_STDERR = 3

    clientClearBreak = pyqtSignal( str, int )
    clientBreakConditionError = pyqtSignal( str, int )
    clientIDEMessage = pyqtSignal( str )

    def __init__( self, mainWindow ):
        QObject.__init__( self )

        # To control the user interface elements
        self.__mainWindow = mainWindow
        self.__state = self.STATE_STOPPED

        self.__procFeedbackSocket = None
        self.__procFeedbackPort = None
        self.__tcpServer = None
        self.__clientSocket = None
        self.__proc = None
        self.__procPID = None
        self.__disconnectReceived = None
        self.__stopAtFirstLine = None
        self.__translatePath = None

        self.__protocolState = self.PROTOCOL_CONTROL
        self.__buffer = ""

        self.__exitCode = None
        self.__fileName = None
        self.__runParameters = None
        self.__debugSettings = None

        self.__codec = QTextCodec.codecForName( "utf-8" )

        self.__breakpointModel = BreakPointModel( self )
        self.__watchpointModel = WatchPointModel( self )

        self.connect( self.__breakpointModel,
                      SIGNAL( "rowsAboutToBeRemoved(const QModelIndex &, int, int)" ),
                      self.__deleteBreakPoints )
        self.connect( self.__breakpointModel,
                      SIGNAL( "dataAboutToBeChanged(const QModelIndex &, const QModelIndex &)" ),
                      self.__breakPointDataAboutToBeChanged )
        self.connect( self.__breakpointModel,
                      SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
                      self.__changeBreakPoints )
        self.connect( self.__breakpointModel,
                      SIGNAL( "rowsInserted(const QModelIndex &, int, int)" ),
                      self.__addBreakPoints )
        self.clientClearBreak.connect( self.__clientClearBreakPoint )
        self.clientBreakConditionError.connect( self.__clientBreakConditionError )
        return

    def getScriptPath( self ):
        " Provides the path to the debugged script "
        return self.__fileName

    def getRunDebugParameters( self ):
        " Provides the running and debugging parameters "
        return self.__runParameters, self.__debugSettings

    def getBreakPointModel( self ):
        " Provides a reference to the breakpoints model "
        return self.__breakpointModel

    def getWatchPointModel( self ):
        " Provides a reference to the watch points model "
        return self.__watchpointModel

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

        self.__protocolState = self.PROTOCOL_CONTROL
        self.__buffer = ""
        self.__exitCode = None
        self.__fileName = None
        self.__runParameters = None
        self.__debugSettings = None

        try:
            QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
            self.__initiatePrologue( fileName )
            QApplication.restoreOverrideCursor()

            self.connect( self.__clientSocket, SIGNAL( 'readyRead()' ),
                          self.__parseClientLine )
            self.__parseClientLine()
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            self.stopDebugging()
        return

    def __initiatePrologue( self, fileName ):
        " Prologue is starting here "
        self.__fileName = fileName 
        self.__changeDebuggerState( self.STATE_PROLOGUE )
        self.__disconnectReceived = False

        # For the time being there is no path translation
        self.__translatePath = self.__noPathTranslation

        self.__mainWindow.switchDebugMode( True )
        terminalType = Settings().terminalType

        if terminalType == TERM_REDIRECT and Settings().clearDebugIO:
            self.__mainWindow.clearDebugIOConsole()

        self.clientIDEMessage.emit( "Start debugging session for " + fileName )
        self.__createProcfeedbackSocket()
        self.__createTCPServer()

        self.__runParameters = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv(
                                            CMD_TYPE_DEBUG,
                                            fileName, self.__runParameters,
                                            terminalType,
                                            self.__procFeedbackPort,
                                            self.__tcpServer.serverPort() )

        self.__debugSettings = Settings().getDebuggerSettings()
        self.__stopAtFirstLine = self.__debugSettings.stopAtFirstLine

        # Run the client -  exception is processed in the outer scope
        self.__proc = Popen( cmd, shell = True, cwd = workingDir,
                             env = environment )

        # Wait for the child PID
        self.__waitChildPID()
        self.__adjustChildPID()

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
                                 "error spawning process to debug" )
        return

    def __adjustChildPID( self ):
        " Detects the debugged process shell reliable "

        # On some systems, e.g. recent Fedora, the way shells are spawned
        # differs to the usual scheme. These systems have a single server which
        # brings children up. This server fools $PPID and thus a child process
        # PID is not detected properly. The fix is here.
        # After a feedback message with a PID is received, we check again in
        # /proc what is the child PID is.
        # Later on, the feedback step can be removed completely.

        for item in os.listdir( "/proc" ):
            if item.isdigit():
                try:
                    f = open( "/proc/" + item + "/cmdline", "r" )
                    content = f.read()
                    f.close()

                    if "client/client_cdm_dbg.py" in content:
                        if str( self.__tcpServer.serverPort() ) in content:
                            if content.startswith( getUserShell() ):
                                self.__procPID = int( item )
                                return
                except:
                    pass
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

        # The readyRead() signal should not be connected here. Sometimes
        # e.g. in case of syntax errors, a message from the remote side comes
        # very quickly, before the prologue is finished.
        # So, connecting this signal is moved to the top level, see
        # startDebugging()
        # self.connect( self.__clientSocket, SIGNAL( 'readyRead()' ),
        #               self.__parseClientLine )

        self.__changeStateWhenReady()
        return

    def __changeStateWhenReady( self ):
        """ Changes the debugger state from prologue to in client when
            all the required connections are ready """
        if self.__clientSocket is None:
            return

        # All the conditions are met, the state can be changed
        self.__changeDebuggerState( self.STATE_IN_CLIENT )
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
        while self.__clientSocket and self.__clientSocket.bytesAvailable() > 0:
            qs = self.__clientSocket.readAll()
            us = self.__codec.fromUnicode( QString( qs ) )
            self.__buffer += str( us )

            # print "Received: '" + str( us ) + "'"

            tryAgain = True
            while tryAgain:
                if self.__protocolState == self.PROTOCOL_CONTROL:
                    tryAgain = self.__processControlState()
                elif self.__protocolState == self.PROTOCOL_EVALEXEC:
                    tryAgain = self.__processEvalexecState()
                elif self.__protocolState == self.PROTOCOL_STDOUT:
                    tryAgain = self.__processStdoutStderrState( True )
                elif self.__protocolState == self.PROTOCOL_STDERR:
                    tryAgain = self.__processStdoutStderrState( False )
                else:
                    raise Exception( "Unexpected protocol state" )
        return

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
        if cmd == ResponseLine or cmd == ResponseStack:
            stack = eval( content )
            for s in stack:
                s[ 0 ] = self.__translatePath( s[ 0 ], True )

            if self.__stopAtFirstLine:
                cf = stack[ 0 ]
                self.emit( SIGNAL( 'ClientLine' ), cf[ 0 ], int( cf[ 1 ] ),
                           cmd == ResponseStack )
                self.emit( SIGNAL( 'ClientStack' ), stack )
            else:
                self.__stopAtFirstLine = True
                QTimer.singleShot( 0, self.remoteContinue )

            if cmd == ResponseLine:
                self.__changeDebuggerState( self.STATE_IN_IDE )
            return self.__buffer != ""

        if cmd == ResponseThreadList:
            currentThreadID, threadList = eval( content )
            self.emit( SIGNAL( 'ClientThreadList' ),
                       currentThreadID, threadList )
            return self.__buffer != ""

        if cmd == ResponseVariables:
            vlist = eval( content )
            scope = vlist[ 0 ]
            try:
                variables = vlist[ 1 : ]
            except IndexError:
                variables = []
            self.emit( SIGNAL( 'ClientVariables' ), scope, variables )
            return self.__buffer != ""

        if cmd == ResponseVariable:
            vlist = eval( content )
            scope = vlist[ 0 ]
            try:
                variables = vlist[ 1 : ]
            except IndexError:
                variables = []
            self.emit( SIGNAL( 'ClientVariable' ), scope, variables )
            return self.__buffer != ""

        if cmd == ResponseException:
            self.__changeDebuggerState( self.STATE_IN_IDE )
            try:
                excList = eval( content )
                excType = excList[ 0 ]
                excMessage = excList[ 1 ]
                stackTrace = excList[ 2 : ]
                if stackTrace and stackTrace[ 0 ] and \
                   stackTrace[ 0 ][ 0 ] == "<string>":
                    stackTrace = []
            except (IndexError, ValueError, SyntaxError):
                excType = None
                excMessage = ""
                stackTrace = []
            self.emit( SIGNAL( 'ClientException' ),
                       excType, excMessage, stackTrace )
            return self.__buffer != ""

        if cmd == ResponseSyntax:
            try:
                message, ( fileName, lineNo, charNo ) = eval( content )
                if fileName is None:
                    fileName = ""
            except ( IndexError, ValueError ):
                message = None
                fileName = ''
                lineNo = 0
                charNo = 0
            if charNo is None:
                charNo = 0
            self.emit( SIGNAL( 'ClientSyntaxError' ),
                       message, fileName, lineNo, charNo )
            return self.__buffer != ""

        if cmd == RequestForkTo:
            self.__askForkTo()
            return self.__buffer != ""

        if cmd == PassiveStartup:
            self.__sendBreakpoints()
            self.__sendWatchpoints()
            return self.__buffer != ""

        if cmd == ResponseThreadSet:
            self.emit( SIGNAL( 'ClientThreadSet' ) )
            return self.__buffer != ""

        if cmd == ResponseClearBreak:
            fileName, lineNo = content.split( ',' )
            lineNo = int( lineNo )
            self.clientClearBreak.emit( fileName, lineNo )
            return self.__buffer != ""

        if cmd == ResponseBPConditionError:
            fileName, lineNo = content.split( ',' )
            lineNo = int( lineNo )
            self.clientBreakConditionError.emit( fileName, lineNo )
            return self.__buffer != ""

        if cmd == ResponseRaw:
            prompt, echo = eval( content )
            self.emit( SIGNAL( 'ClientRawInput' ), prompt, echo )
            return self.__buffer != ""

        if cmd == ResponseExit:
            message = "Debugged script finished with exit code " + content
            self.clientIDEMessage.emit( message )
            try:
                self.__exitCode = int( content )
            except:
                pass
            return self.__buffer != ""

        if cmd == ResponseEval:
            self.__protocolState = self.PROTOCOL_EVALEXEC
            return self.__buffer != ""

        if cmd == ResponseExec:
            self.__protocolState = self.PROTOCOL_EVALEXEC
            return self.__buffer != ""

        if cmd == ResponseStdout:
            self.__protocolState = self.PROTOCOL_STDOUT
            return self.__buffer != ""

        if cmd == ResponseStderr:
            self.__protocolState = self.PROTOCOL_STDERR
            return self.__buffer != ""

        print "Unexpected message received (no control match): '" + line + "'"
        return self.__buffer != ""

    def __processEvalexecState( self ):
        " Analyzes receiving buffer in the EVALEXEC state "
        # Collect till ResponseEvalOK, ResponseEvalError,
        #              ResponseExecOK, ResponseExecError

        index = self.__buffer.find( ResponseEvalOK + EOT )
        if index != -1:
            self.emit( SIGNAL( 'EvalOK' ),
                       self.__buffer[ 0 : index ].replace( EOT, "" ) )
            self.__protocolState = self.PROTOCOL_CONTROL
            self.__buffer = self.__buffer[ index + len( ResponseEvalOK ) + len( EOT ) : ]
            return self.__buffer != ""

        index = self.__buffer.find( ResponseEvalError + EOT )
        if index != -1:
            self.emit( SIGNAL( 'EvalError' ),
                       self.__buffer[ 0 : index ].replace( EOT, "" ) )
            self.__protocolState = self.PROTOCOL_CONTROL
            self.__buffer = self.__buffer[ index + len( ResponseEvalError ) + len( EOT ) : ]
            return self.__buffer != ""

        index = self.__buffer.find( ResponseExecOK + EOT )
        if index != -1:
            self.emit( SIGNAL( 'ExecOK' ),
                       self.__buffer[ 0 : index ].replace( EOT, "" ) )
            self.__protocolState = self.PROTOCOL_CONTROL
            self.__buffer = self.__buffer[ index + len( ResponseExecOK ) + len( EOT ) : ]
            return self.__buffer != ""

        index = self.__buffer.find( ResponseExecError + EOT )
        if index != -1:
            self.emit( SIGNAL( 'ExecError' ),
                       self.__buffer[ 0 : index ].replace( EOT, "" ) )
            self.__protocolState = self.PROTOCOL_CONTROL
            self.__buffer = self.__buffer[ index + len( ResponseExecError ) + len( EOT ) : ]
            return self.__buffer != ""

        return False

    def __processStdoutStderrState( self, isStdout ):
        " Analyzes receiving buffer in the STDOUT/STDERR state "
        # Collect till "\x04\x04"
        index = self.__buffer.find( StdoutStderrEOT )
        if index == -1:
            # End has not been found
            if self.__buffer.endswith( '\x04' ):
                if isStdout:
                    self.emit( SIGNAL( 'ClientStdout' ), self.__buffer[ : -1 ] )
                else:
                    self.emit( SIGNAL( 'ClientStderr' ), self.__buffer[ : -1 ] )
                self.__buffer = '\x04'
                return False
            else:
                if isStdout:
                    self.emit( SIGNAL( 'ClientStdout' ), self.__buffer )
                else:
                    self.emit( SIGNAL( 'ClientStderr' ), self.__buffer )
                self.__buffer = ""
                return False
        else:
            if isStdout:
                self.emit( SIGNAL( 'ClientStdout' ), self.__buffer[ 0 : index ] )
            else:
                self.emit( SIGNAL( 'ClientStderr' ), self.__buffer[ 0 : index ] )
            self.__buffer = self.__buffer[ index + 2 : ]
            self.__protocolState = self.PROTOCOL_CONTROL
            return True

    def __disconnected( self ):
        " Triggered when the client closed the connection "
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

        # Close the TCP server if so
        if self.__tcpServer is not None:
            self.disconnect( self.__tcpServer, SIGNAL( "newConnection()" ),
                             self.__newConnection )
            self.__tcpServer.close()
        self.__tcpServer = None

        # Deal with the process if so
        if self.__procPID is not None:
            killOnSuccess = False
            if self.__exitCode is not None and self.__exitCode == 0:
                if self.__runParameters is not None and \
                   self.__runParameters.closeTerminal:
                    killOnSuccess = True

            if Settings().terminalType != TERM_REDIRECT:
                if brutal or killOnSuccess:
                    try:
                        # Throws exceptions if cannot kill the process
                        killProcess( self.__procPID )
                    except:
                        pass
        self.__procPID = None
        if self.__proc is not None:
            try:
                self.__proc.wait()
            except:
                pass
            self.__proc = None

        self.__mainWindow.switchDebugMode( False )
        self.__changeDebuggerState( self.STATE_STOPPED )

        self.__fileName = None
        self.__runParameters = None
        self.__debugSettings = None

        message = "Debugging session has been stopped"
        if brutal and Settings().terminalType != TERM_REDIRECT:
            message += " and the console has been closed"
        self.clientIDEMessage.emit( message )
        return

    def __noPathTranslation( self, fname, remote2local = True ):
        """ Dump to support later path translations """
        return unicode( fname )

    def __askForkTo( self ):
        " Asks what to follow, a parent or a child "
        dlg = QMessageBox( QMessageBox.Question, "Client forking",
                           "Select the fork branch to follow" )
        dlg.addButton( QMessageBox.Ok )
        dlg.addButton( QMessageBox.Cancel )

        btn1 = dlg.button( QMessageBox.Ok )
        btn1.setText( "&Child process" )
        btn1.setIcon( PixmapCache().getIcon( '' ) )

        btn2 = dlg.button( QMessageBox.Cancel )
        btn2.setText( "&Parent process" )
        btn2.setIcon( PixmapCache().getIcon( '' ) )

        dlg.setDefaultButton( QMessageBox.Cancel )
        res = dlg.exec_()

        if res == QMessageBox.Cancel:
            self.__sendCommand( ResponseForkTo + 'parent\n' )
        else:
            self.__sendCommand( ResponseForkTo + 'child\n' )
        return

    def __validateBreakpoints( self ):
        " Checks all the breakpoints validity and deletes invalid "
        # It is excepted that the method is called when all the files are
        # saved, e.g. when a new debugging session is started.
        for row in xrange( 0, self.__breakpointModel.rowCount() ):
            index = self.__breakpointModel.index( row, 0, QModelIndex() )
            bpoint = self.__breakpointModel.getBreakPointByIndex( index )
            fileName = bpoint.getAbsoluteFileName()
            line = bpoint.getLineNumber()

            if not os.path.exists( fileName ):
                logging.warning( "Breakpoint at " + fileName + ":" +
                                 str( line ) + " is invalid (the file "
                                 "disappeared from the filesystem). "
                                 "The breakpoint is deleted." )
                self.__breakpointModel.deleteBreakPointByIndex( index )
                continue

            breakableLines = getBreakpointLines( fileName, None, True )
            if breakableLines is None:
                logging.warning( "Breakpoint at " + fileName + ":" +
                                 str( line ) + " does not point to a breakable "
                                 "line (the file could not be compiled). "
                                 "The breakpoint is deleted." )
                self.__breakpointModel.deleteBreakPointByIndex( index )
                continue
            if line not in breakableLines:
                logging.warning( "Breakpoint at " + fileName + ":" +
                                 str( line ) + " does not point to a breakable "
                                 "line (the file was modified). "
                                 "The breakpoint is deleted." )
                self.__breakpointModel.deleteBreakPointByIndex( index )
                continue

            # The breakpoint is OK, keep it
        return

    def __sendBreakpoints( self ):
        " Sends the breakpoints to the debugged program "
        self.__validateBreakpoints()
        self.__addBreakPoints( QModelIndex(), 0,
                               self.__breakpointModel.rowCount() - 1 )
        return

    def __addBreakPoints( self, parentIndex, start, end ):
        " Adds breakpoints "
        if self.__state in [ self.STATE_PROLOGUE,
                             self.STATE_STOPPED,
                             self.STATE_FINISHING,
                             self.STATE_BRUTAL_FINISHING ]:
            return

        for row in xrange( start, end + 1 ):
            index = self.__breakpointModel.index( row, 0, parentIndex )
            bpoint = self.__breakpointModel.getBreakPointByIndex( index )
            fileName = bpoint.getAbsoluteFileName()
            line = bpoint.getLineNumber()
            self.remoteBreakpoint( fileName, line, True,
                                   bpoint.getCondition(),
                                   bpoint.isTemporary() )
            if not bpoint.isEnabled():
                self.__remoteBreakpointEnable( fileName, line, False )
            ignoreCount = bpoint.getIgnoreCount()
            if ignoreCount > 0:
                self.__remoteBreakpointIgnore( fileName, line,
                                               ignoreCount )
        return

    def __deleteBreakPoints( self, parentIndex, start, end ):
        " Deletes breakpoints "
        if self.__state in [ self.STATE_PROLOGUE,
                             self.STATE_STOPPED,
                             self.STATE_FINISHING,
                             self.STATE_BRUTAL_FINISHING ]:
            return

        for row in xrange( start, end + 1 ):
            index = self.__breakpointModel.index( row, 0, parentIndex )
            bpoint = self.__breakpointModel.getBreakPointByIndex( index )
            fileName = bpoint.getAbsoluteFileName()
            line = bpoint.getLineNumber()
            self.remoteBreakpoint( fileName, line, False )
        return

    def __breakPointDataAboutToBeChanged( self, startIndex, endIndex ):
        " Handles the dataAboutToBeChanged signal of the breakpoint model "
        self.__deleteBreakPoints( QModelIndex(),
                                  startIndex.row(), endIndex.row() )
        return

    def __changeBreakPoints( self, startIndex, endIndex ):
        " Sets changed breakpoints "
        self.__addBreakPoints( QModelIndex(), startIndex.row(), endIndex.row() )
        return


    def __sendWatchpoints( self ):
        " Sends the watchpoints to the debugged program "
        return

    def __remoteBreakpointEnable( self, fileName, line, enable ):
        " Sends the breakpoint enability "
        if enable:
            enable = 1
        else:
            enable = 0
        self.__sendCommand( RequestBreakEnable + fileName + ',' +
                            str( line ) + ',' + str( enable ) + '\n' )
        return

    def __remoteBreakpointIgnore( self, fileName, line, ignoreCount ):
        " Sends the breakpoint ignore count "
        self.__sendCommand( RequestBreakIgnore + fileName + ',' +
                            str( line ) + ',' + str( ignoreCount ) + '\n' )
        return

    def __clientClearBreakPoint( self, fileName, line ):
        " Handles the clientClearBreak signal "
        if self.__state in [ self.STATE_PROLOGUE,
                             self.STATE_STOPPED,
                             self.STATE_FINISHING,
                             self.STATE_BRUTAL_FINISHING ]:
            return

        index = self.__breakpointModel.getBreakPointIndex( fileName, line )
        if index.isValid():
            self.__breakpointModel.deleteBreakPointByIndex( index )
        return

    def __clientBreakConditionError( self, fileName, line ):
        " Handles the condition error "
        logging.error( "The condition of the breakpoint at " +
                       fileName + ":" + str( line ) +
                       " contains a syntax error." )
        index = self.__breakpointModel.getBreakPointIndex( fileName, line )
        if not index.isValid():
            return
        bpoint = self.__breakpointModel.getBreakPointByIndex( index )
        if not bpoint:
            return

        dlg = BreakpointEditDialog( bpoint )
        if dlg.exec_() == QDialog.Accepted:
            newBpoint = dlg.getData()
            if newBpoint == bpoint:
                return
            self.__breakpointModel.setBreakPointByIndex( index, newBpoint )
        return

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

    def remoteStack( self ):
        " Provides the current thread stack "
        self.__sendCommand( RequestStack + "\n" )
        return

    def remoteClientVariables( self, scope, framenr = 0 ):
        """ Provides the client variables.
            scope - 0 => local, 1 => global """
        scope = int( scope )
        self.__sendCommand( RequestVariables +
                            str( framenr ) + ", " + str( scope ) + "\n" )
        return

    def remoteClientVariable( self, scope, var, framenr = 0 ):
        """ Provides the client variable.
            scope - 0 => local, 1 => global """
        scope = int( scope )
        self.__sendCommand( RequestVariable +
                            unicode( var ) + ", " +
                            str( framenr ) + ", " + str( scope ) + "\n" )
        return

    def remoteEval( self, expression, framenr ):
        " Evaluates the expression in the current context of the debuggee "
        self.__sendCommand( RequestEval +
                            str( framenr ) + ", " + expression + "\n" )
        return

    def remoteExec( self, statement, framenr ):
        " Executes the expression in the current context of the debuggee "
        self.__sendCommand( RequestExec +
                            str( framenr ) + ", " + statement + "\n" )
        return

    def remoteBreakpoint( self, fileName, line,
                          isSetting, condition = None, temporary = False ):
        " Sets or clears a breakpoint "
        self.__sendCommand( RequestBreak + fileName + "@@" + str( line ) +
                            "@@" + str( int( temporary ) ) + "@@" +
                            str( int( isSetting ) ) + "@@" +
                            str( condition ) + "\n" )
        return

    def remoteSetThread( self, tid ):
        " Sets the given thread as the current "
        self.__sendCommand( RequestThreadSet + str( tid ) + "\n" )
        return

    def remoteRawInput( self, userInput ):
        " Sends the remote user input "
        self.__sendCommand( userInput + "\n" )
        return
