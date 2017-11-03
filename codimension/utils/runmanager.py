# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2014-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Run/profile/debug manager"""

import os.path
import logging
import time
import uuid
from subprocess import Popen
from datetime import datetime
from editor.ioconsolewidget import IOConsoleWidget
from editor.redirectedmsg import printableTimestamp
from debugger.client.protocol_cdm_dbg import (METHOD_PROC_ID_INFO,
                                              METHOD_PROLOGUE_CONTINUE,
                                              METHOD_EPILOGUE_EXIT_CODE,
                                              METHOD_EPILOGUE_EXIT,
                                              METHOD_STDOUT, METHOD_STDERR,
                                              METHOD_STDIN, KILLED,
                                              DISCONNECTED, FAILED_TO_START,
                                              STOPPED_BY_REQUEST,
                                              SYNTAX_ERROR_AT_START,
                                              UNHANDLED_EXCEPTION)
from debugger.client.cdm_dbg_utils import getParsedJSONMessage, sendJSONCommand
from ui.runparamsdlg import RunDialog
from ui.qt import (QObject, Qt, QTimer, QDialog, QApplication, QCursor,
                   QTcpServer, QHostAddress, QAbstractSocket, pyqtSignal)
from .run import getCwdCmdEnv
from .runparams import RUN, PROFILE, DEBUG
from .procfeedback import killProcess
from .globals import GlobalData
from .settings import Settings, CLEAR_AND_REUSE, NO_REUSE
from .diskvaluesrelay import getRunParameters, addRunParams


IDE_DEBUG = False
HANDSHAKE_TIMEOUT = 15

STATE_PROLOGUE = 0
STATE_RUNNING = 1

# Used from outside too
def getWorkingDir(path, params):
    """Provides the working directory"""
    if params['useScriptLocation']:
        return os.path.dirname(path)
    return params['specificDir']


class RemoteProcessWrapper(QObject):

    """Wrapper to control the remote process"""

    sigFinished = pyqtSignal(str, int)
    sigClientStdout = pyqtSignal(str, str)
    sigClientStderr = pyqtSignal(str, str)
    sigClientInput = pyqtSignal(str, str, int)
    sigIncomingMessage = pyqtSignal(str, str, object)

    def __init__(self, path, serverPort, redirected, kind):
        QObject.__init__(self)
        self.procuuid = str(uuid.uuid1())
        self.path = path
        self.redirected = redirected
        self.kind = kind
        self.state = None
        self.startTime = None
        self.finishTime = None

        self.__serverPort = serverPort
        self.__clientSocket = None
        self.__proc = None

    def start(self):
        """Starts the remote process"""
        params = getRunParameters(self.path)
        if self.redirected:
            cmd, environment = getCwdCmdEnv(self.kind, self.path, params,
                                            self.__serverPort, self.procuuid)
        else:
            cmd, environment = getCwdCmdEnv(self.kind, self.path, params,
                                            self.__serverPort, self.procuuid)

        self.__proc = Popen(cmd, shell=True,
                            cwd=getWorkingDir(self.path, params),
                            env=environment)

    def setSocket(self, clientSocket):
        """Called when an incoming connection has come"""
        self.__clientSocket = clientSocket
        self.state = STATE_RUNNING

        self.__connectSocket()
        self.__parseClientLine()

        # Send runnee the 'start' message
        self.__sendStart()

    def stop(self):
        """Kills the process"""
        self.__disconnectSocket()
        self.__kill()
        self.sigFinished.emit(self.procuuid, KILLED)

    def __connectSocket(self):
        """Connects the socket slots"""
        if self.__clientSocket:
            self.__clientSocket.readyRead.connect(self.__parseClientLine)
            self.__clientSocket.disconnected.connect(self.__disconnected)

    def __disconnectSocket(self):
        """Disconnects the socket related slots"""
        if self.__clientSocket:
            try:
                self.__clientSocket.readyRead.disconnect(
                    self.__parseClientLine)
                self.__clientSocket.disconnected.disconnect(
                    self.__disconnected)
            except:
                pass

    def __closeSocket(self):
        """Closes the client socket if so"""
        if self.__clientSocket:
            try:
                self.__clientSocket.close()
            except:
                pass
            self.__clientSocket = None

    def wait(self):
        """Waits for the process"""
        self.__closeSocket()
        if self.__proc is not None:
            try:
                self.__proc.wait()
            except:
                # E.g. wait timeout
                pass

    def waitDetached(self):
        """Needs to avoid zombies"""
        try:
            if self.__proc.poll() is not None:
                self.__proc.wait()
                return True
        except:
            return True
        return False

    def __kill(self):
        """Kills the process or checks there is no process in memory"""
        if self.__proc is not None:
            try:
                self.__proc.kill()
            except:
                pass

        childPID = self.__getChildPID()
        while childPID is not None:
            try:
                # Throws an exception if cannot kill the process
                killProcess(childPID)
            except:
                pass
            nextPID = self.__getChildPID()
            if nextPID == childPID:
                break
            childPID = nextPID

        # Here: the process killed
        self.wait()
        self.__proc = None

    def __getChildPID(self):
        """Provides the child process PID if redirected"""
        if self.__serverPort is None or self.procuuid is None:
            return None

        if self.kind == RUN:
            wrapper = os.path.join('client', 'client_cdm_run.py')
        elif self.kind == PROFILE:
            wrapper = os.path.join('client', 'client_cdm_profile.py')
        else:
            wrapper = os.path.join('client', 'client_cdm_dbg.py')
        for item in os.listdir("/proc"):
            if item.isdigit():
                try:
                    f = open("/proc/" + item + "/cmdline", "r")
                    content = f.read()
                    f.close()

                    if wrapper in content:
                        if '--port' in content:
                            if str(self.__serverPort) in content:
                                if '--procuuid' in content:
                                    if self.procuuid in content:
                                        return int(item)
                except:
                    pass
        return None

    def __disconnected(self):
        """Triggered when the client closed the connection"""
        self.__kill()
        self.sigFinished.emit(self.procuuid, DISCONNECTED)

    def __sendStart(self):
        """Sends the start command to the runnee"""
        sendJSONCommand(self.__clientSocket, METHOD_PROLOGUE_CONTINUE,
                        self.procuuid, None)

    def __sendExit(self):
        """sends the exit command to the runnee"""
        self.__disconnectSocket()
        sendJSONCommand(self.__clientSocket, METHOD_EPILOGUE_EXIT,
                        self.procuuid, None)

    def sendJSONCommand(self, method, params):
        """Sends a command to the debuggee. Used by the debugger."""
        sendJSONCommand(self.__clientSocket, method, self.procuuid, params)

    def __parseClientLine(self):
        """Parses a single line from the running client"""
        while self.__clientSocket and self.__clientSocket.canReadLine():
            try:
                method, procuuid, params, jsonStr = getParsedJSONMessage(
                    self.__clientSocket)
                del procuuid    # unused

                if IDE_DEBUG:
                    print("Process wrapper received: " + str(jsonStr))

                if method == METHOD_EPILOGUE_EXIT_CODE:
                    self.__sendExit()
                    self.sigFinished.emit(self.procuuid, params['exitCode'])
                    QApplication.processEvents()
                    continue
                if method == METHOD_STDOUT:
                    self.sigClientStdout.emit(self.procuuid, params['text'])
                    QApplication.processEvents()
                    continue
                if method == METHOD_STDERR:
                    self.sigClientStderr.emit(self.procuuid, params['text'])
                    QApplication.processEvents()
                    continue
                if method == METHOD_STDIN:
                    prompt = params['prompt']
                    echo = params['echo']
                    self.sigClientInput.emit(self.procuuid, prompt, echo)
                    QApplication.processEvents()
                    continue

                # The other messages may appear only when a code is debugged
                # so they are processed outside of a generic run manager
                self.sigIncomingMessage.emit(self.procuuid, method, params)

            except Exception as exc:
                logging.error('Failure to get a message '
                              'from a remote process: ' + str(exc))

    def userInput(self, collectedString):
        """Called when the user finished input"""
        if self.__clientSocket:
            sendJSONCommand(self.__clientSocket, METHOD_STDIN,
                            self.procuuid, {'input': collectedString})


class RemoteProcess:

    """Stores attributes of a single process"""

    def __init__(self):
        self.procWrapper = None
        self.widget = None
        self.kind = None


class RunManager(QObject):

    """Manages the external running processes"""

    # script path, output file, start time, finish time, redirected
    sigProfilingResults = pyqtSignal(str, str, str, str, bool)
    sigDebugSessionPrologueStarted = pyqtSignal(object, str, object, object)
    sigIncomingMessage = pyqtSignal(str, str, object)
    sigProcessFinished = pyqtSignal(str, int)

    def __init__(self, mainWindow):
        QObject.__init__(self)
        self.__mainWindow = mainWindow
        self.__processes = []
        self.__prologueProcesses = []

        self.__tcpServer = QTcpServer()
        self.__tcpServer.newConnection.connect(self.__newConnection)
        self.__tcpServer.listen(QHostAddress.LocalHost)

        self.__waitTimer = QTimer(self)
        self.__waitTimer.setSingleShot(True)
        self.__waitTimer.timeout.connect(self.__onWaitTimer)

        self.__prologueTimer = QTimer(self)
        self.__prologueTimer.setSingleShot(True)
        self.__prologueTimer.timeout.connect(self.__onPrologueTimer)

    def __newConnection(self):
        """Handles new incoming connections"""
        clientSocket = self.__tcpServer.nextPendingConnection()
        clientSocket.setSocketOption(QAbstractSocket.KeepAliveOption, 1)
        clientSocket.setSocketOption(QAbstractSocket.LowDelayOption, 1)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.__waitForHandshake(clientSocket)
        except:
            QApplication.restoreOverrideCursor()
            raise
        QApplication.restoreOverrideCursor()

    def __waitForHandshake(self, clientSocket):
        """Waits for the message with the proc ID"""
        if clientSocket.waitForReadyRead(1000):
            try:
                method, procuuid, params, jsonStr = getParsedJSONMessage(
                    clientSocket)
                if IDE_DEBUG:
                    print("Run manager (wait for handshake) received: " +
                          str(jsonStr))
                if method != METHOD_PROC_ID_INFO:
                    logging.error('Unexpected message at the handshake stage. '
                                  'Expected: ' + METHOD_PROC_ID_INFO +
                                  '. Received: ' + str(method))
                    self.__safeSocketClose(clientSocket)
                    return None
            except (TypeError, ValueError) as exc:
                self.__mainWindow.showStatusBarMessage(
                    'Unsolicited connection to the RunManager. Ignoring...')
                self.__safeSocketClose(clientSocket)
                return None

            procIndex = self.__getProcessIndex(procuuid)
            if procIndex is not None:
                self.__onProcessStarted(procuuid)
                self.__processes[procIndex].procWrapper.setSocket(clientSocket)
            return params

    @staticmethod
    def __safeSocketClose(clientSocket):
        """No exception socket close"""
        try:
            clientSocket.close()
        except Exception as exc:
            logging.error('Run manager safe socket close: ' + str(exc))

    def __pickWidget(self, procuuid, kind):
        """Picks the widget for a process"""
        consoleReuse = Settings()['ioconsolereuse']
        if consoleReuse == NO_REUSE:
            widget = IOConsoleWidget(procuuid, kind)
            self.__mainWindow.addIOConsole(widget, kind)
            return widget

        widget = None
        consoles = self.__mainWindow.getIOConsoles()
        for console in consoles:
            if console.kind == kind:
                procIndex = self.__getProcessIndex(console.procuuid)
                if procIndex is None:
                    widget = console
                    widget.onReuse(procuuid)
                    self.__mainWindow.onReuseConsole(widget, kind)
                    if consoleReuse == CLEAR_AND_REUSE:
                        widget.clear()
                    break
        if widget is None:
            widget = IOConsoleWidget(procuuid, kind)
            self.__mainWindow.addIOConsole(widget, kind)
        return widget

    def __updateParameters(self, path, kind):
        """Displays the dialog and updates the parameters if needed"""
        params = getRunParameters(path)
        profilerParams = None
        debuggerParams = None
        if kind == PROFILE:
            profilerParams = Settings().getProfilerSettings()
        elif kind == DEBUG:
            debuggerParams = Settings().getDebuggerSettings()
        dlg = RunDialog(path, params, profilerParams, debuggerParams,
                        kind, self.__mainWindow)
        if dlg.exec_() == QDialog.Accepted:
            addRunParams(path, dlg.runParams)
            if kind == PROFILE:
                if dlg.profilerParams != profilerParams:
                    Settings().setProfilerSettings(dlg.profilerParams)
            elif kind == DEBUG:
                if dlg.debuggerParams != debuggerParams:
                    Settings().setDebuggerSettings(dlg.debuggerParams)
            return True
        return False

    def __prepareRemoteProcess(self, path, kind):
        """Prepares the data structures to start a remote proces"""
        redirected = getRunParameters(path)['redirected']
        remoteProc = RemoteProcess()
        remoteProc.kind = kind
        remoteProc.procWrapper = RemoteProcessWrapper(
            path, self.__tcpServer.serverPort(), redirected, kind)
        remoteProc.procWrapper.state = STATE_PROLOGUE
        if redirected or kind == DEBUG:
            self.__prologueProcesses.append((remoteProc.procWrapper.procuuid,
                                             time.time()))
            if not self.__prologueTimer.isActive():
                self.__prologueTimer.start(1000)
        if redirected:
            remoteProc.widget = self.__pickWidget(
                remoteProc.procWrapper.procuuid, kind)
            remoteProc.widget.appendIDEMessage(
                'Starting script ' + path + '...')

            remoteProc.procWrapper.sigClientStdout.connect(
                remoteProc.widget.appendStdoutMessage)
            remoteProc.procWrapper.sigClientStderr.connect(
                remoteProc.widget.appendStderrMessage)
            remoteProc.procWrapper.sigClientInput.connect(
                remoteProc.widget.input)

            remoteProc.widget.sigUserInput.connect(self.__onUserInput)

        remoteProc.procWrapper.sigFinished.connect(self.__onProcessFinished)
        remoteProc.procWrapper.sigIncomingMessage.connect(
            self.__onIncomingMessage)
        self.__processes.append(remoteProc)
        return remoteProc

    def run(self, path, needDialog):
        """Runs the given script regardless if it is redirected"""
        if needDialog:
            if not self.__updateParameters(path, RUN):
                return

        remoteProc = self.__prepareRemoteProcess(path, RUN)
        try:
            remoteProc.procWrapper.start()
            if not remoteProc.procWrapper.redirected:
                remoteProc.procWrapper.startTime = datetime.now()
                if not self.__waitTimer.isActive():
                    self.__waitTimer.start(1000)
        except Exception as exc:
            self.__onProcessFinished(remoteProc.procWrapper.procuuid,
                                     FAILED_TO_START)
            logging.error(str(exc))

    def profile(self, path, needDialog):
        """Profiles the given script regardless if it is redirected"""
        if needDialog:
            if not self.__updateParameters(path, PROFILE):
                return

        remoteProc = self.__prepareRemoteProcess(path, PROFILE)
        try:
            remoteProc.procWrapper.start()
            if not remoteProc.procWrapper.redirected:
                remoteProc.procWrapper.startTime = datetime.now()
                if not self.__waitTimer.isActive():
                    self.__waitTimer.start(1000)
        except Exception as exc:
            self.__onProcessFinished(remoteProc.procWrapper.procuuid,
                                     FAILED_TO_START)
            logging.error(str(exc))

    def debug(self, path, needDialog):
        """Debugs the given script regardless if it is redirected"""
        if needDialog:
            if not self.__updateParameters(path, DEBUG):
                return

        remoteProc = self.__prepareRemoteProcess(path, DEBUG)

        # The run parameters could be changed by another run after the
        # debugging has started so they need to be saved per session
        self.sigDebugSessionPrologueStarted.emit(
            remoteProc.procWrapper, path,
            getRunParameters(path), Settings().getDebuggerSettings())
        try:
            remoteProc.procWrapper.start()
            if not remoteProc.procWrapper.redirected:
                remoteProc.procWrapper.startTime = datetime.now()
                if not self.__waitTimer.isActive():
                    self.__waitTimer.start(1000)
        except Exception as exc:
            self.__onProcessFinished(remoteProc.procWrapper.procuuid,
                                     FAILED_TO_START)
            logging.error(str(exc))

    def killAll(self):
        """Kills all the processes if needed"""
        index = len(self.__processes) - 1
        while index >= 0:
            item = self.__processes[index]
            if item.procWrapper.redirected:
                item.procWrapper.stop()
            index -= 1

        # Wait till all the processes stopped
        count = self.__getDetachedCount()
        while count > 0:
            time.sleep(0.01)
            QApplication.processEvents()
            count = self.__getDetachedCount()

    def __getDetachedCount(self):
        """Return the number of detached processes still running"""
        count = 0
        index = len(self.__processes) - 1
        while index >= 0:
            if self.__processes[index].procWrapper.redirected:
                count += 1
            index -= 1
        return count

    def kill(self, procuuid):
        """Kills a single process"""
        index = self.__getProcessIndex(procuuid)
        if index is None:
            return
        item = self.__processes[index]
        if not item.procWrapper.redirected:
            return
        item.procWrapper.stop()

    def __getProcessIndex(self, procuuid):
        """Returns a process index in the list"""
        for index, item in enumerate(self.__processes):
            if item.procWrapper.procuuid == procuuid:
                return index
        return None

    def __onProcessFinished(self, procuuid, retCode):
        """Triggered when a redirected process has finished"""
        index = self.__getProcessIndex(procuuid)
        if index is not None:
            item = self.__processes[index]
            item.procWrapper.finishTime = datetime.now()

            needProfileSignal = False
            if retCode == KILLED:
                msg = "Script killed"
                tooltip = "killed"
            elif retCode == DISCONNECTED:
                msg = "Connection lost to the script process"
                tooltip = "connection lost"
            elif retCode == FAILED_TO_START:
                msg = "Script failed to start"
                tooltip = "failed to start"
            elif retCode == STOPPED_BY_REQUEST:
                # Debugging only: user clicked 'stop'
                msg = "Script finished by the user request"
                tooltip = "stopped by user"
                item.procWrapper.wait()
            elif retCode == UNHANDLED_EXCEPTION:
                # Debugging only: unhandled exception
                msg = "Script finished due to an unhandled exception"
                tooltip = "unhandled exception"
                item.procWrapper.wait()
            elif retCode == SYNTAX_ERROR_AT_START:
                msg = "Failure to run due to a syntax error"
                tooltip = "syntax error"
                item.procWrapper.wait()
            else:
                msg = "Script finished with exit code " + str(retCode)
                tooltip = "finished, exit code " + str(retCode)
                item.procWrapper.wait()
                if item.kind == PROFILE:
                    needProfileSignal = True

            if item.widget:
                item.widget.scriptFinished()
                item.widget.appendIDEMessage(msg)
                self.__mainWindow.updateIOConsoleTooltip(procuuid, tooltip)
                self.__mainWindow.onConsoleFinished(item.widget)
                item.widget.sigUserInput.disconnect(self.__onUserInput)

            if needProfileSignal:
                self.__sendProfileResultsSignal(item.procWrapper)

            del self.__processes[index]

        self.sigProcessFinished.emit(procuuid, retCode)

    def __onProcessStarted(self, procuuid):
        """Triggered when a process has started"""
        index = self.__getProcessIndex(procuuid)
        if index is not None:
            item = self.__processes[index]
            if item.widget:
                msg = item.widget.appendIDEMessage('Script started')
                item.procWrapper.startTime = msg.timestamp

    def __onUserInput(self, procuuid, userInput):
        """Triggered when the user input is collected"""
        index = self.__getProcessIndex(procuuid)
        if index is not None:
            item = self.__processes[index]
            if item.procWrapper.redirected:
                item.procWrapper.userInput(userInput)

    def __onWaitTimer(self):
        """Triggered when the timer fired"""
        needNewTimer = False
        index = len(self.__processes) - 1
        while index >= 0:
            item = self.__processes[index]
            if not item.procWrapper.redirected:
                if item.procWrapper.waitDetached():
                    item.procWrapper.finishTime = datetime.now()
                    if item.procWrapper.kind == PROFILE:
                        self.__sendProfileResultsSignal(item.procWrapper)
                    del self.__processes[index]
                else:
                    needNewTimer = True
            index -= 1
        if needNewTimer:
            self.__waitTimer.start(1000)

    def __sendProfileResultsSignal(self, procWrapper):
        """Sends a signal to tell that the results are available"""
        self.sigProfilingResults.emit(
            procWrapper.path,
            GlobalData().getProfileOutputPath(procWrapper.procuuid),
            printableTimestamp(procWrapper.startTime),
            printableTimestamp(procWrapper.finishTime),
            procWrapper.redirected)

    def __onIncomingMessage(self, procuuid, method, params):
        """Handles a debugger incoming message"""
        if IDE_DEBUG:
            print('Debugger message from ' + procuuid +
                  ' Method: ' + method + ' Prameters: ' + repr(params))

        self.sigIncomingMessage.emit(procuuid, method, params)

    def __onPrologueTimer(self):
        """Triggered when a prologue phase controlling timer fired"""
        needNewTimer = False
        index = len(self.__prologueProcesses) - 1
        while index >= 0:
            procuuid, startTime = self.__prologueProcesses[index]
            procIndex = self.__getProcessIndex(procuuid)
            if procIndex is None:
                # No such process anymore
                del self.__prologueProcesses[index]
            else:
                item = self.__processes[procIndex]
                if item.procWrapper.state != STATE_PROLOGUE:
                    # The state has been changed
                    del self.__prologueProcesses[index]
                else:
                    if time.time() - startTime > HANDSHAKE_TIMEOUT:
                        # Waited too long
                        item.widget.appendIDEMessage(
                            'Timeout: the process did not start; '
                            'killing the process.')
                        item.procWrapper.stop()
                    else:
                        needNewTimer = True
            index -= 1
        if needNewTimer:
            self.__prologueTimer.start(1000)

    def appendIDEMessage(self, procuuid, message):
        """Appends a message to the appropriate IO window"""
        index = self.__getProcessIndex(procuuid)
        if index is not None:
            item = self.__processes[index]
            if item.widget:
                item.widget.appendIDEMessage(message)
                return
        logging.error(message)
