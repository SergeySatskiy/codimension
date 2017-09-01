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
from subprocess import Popen
from editor.redirectedrun import RunConsoleTabWidget
from debugger.client.protocol_cdm_dbg import METHOD_PROC_ID_INFO
from debugger.client.cdm_dbg_utils import parseJSONMessage, prepareJSONMessage
from ui.runparamsdlg import RunDialog
from ui.qt import (QObject, Qt, QTimer, QDialog, QApplication, QCursor,
                   QTcpServer, QHostAddress, QAbstractSocket, pyqtSignal)
from .run import getCwdCmdEnv
from .runparams import RUN, PROFILE, DEBUG
from .procfeedback import killProcess
from .globals import GlobalData
from .settings import Settings
from .diskvaluesrelay import getRunParameters, addRunParams


# Finish codes in addition to the normal exit code
KILLED = -1000000
DISCONNECTED = -2000000

HANDSHAKE_TIMEOUT = 15
POLL_INTERVAL = 0.1
BRUTAL_SHUTDOWN_TIMEOUT = 0.2
GRACEFUL_SHUTDOWN_TIMEOUT = 5


NEXT_ID = 0


STATE_PROLOGUE = 0
STATE_IN_CLIENT = 1



# Used from outside too
def getWorkingDir(path, params):
    """Provides the working directory"""
    if params['useScriptLocation']:
        return os.path.dirname(path)
    return params['specificDir']


def getNextID():
    """Provides the next available ID"""
    global NEXT_ID
    current = int(NEXT_ID)
    NEXT_ID += 1
    return current


class RemoteProcessWrapper(QObject):

    """Wrapper to control the remote process"""

    sigFinished = pyqtSignal(int, int)
    sigClientStdout = pyqtSignal(str)
    sigClientStderr = pyqtSignal(str)
    sigClientRawInput = pyqtSignal(str, int)

    def __init__(self, path, serverPort, redirected):
        QObject.__init__(self)
        self.procID = getNextID()
        self.path = path
        self.redirected = redirected
        self.state = None

        self.__serverPort = serverPort
        self.__clientSocket = None
        self.__proc = None

    def start(self, kind):
        """Starts the remote process"""
        params = getRunParameters(self.path)
        if self.redirected:
            cmd, environment = getCwdCmdEnv(kind, self.path, params,
                                            self.__serverPort, self.procID)
        else:
            cmd, environment = getCwdCmdEnv(kind, self.path, params)

        self.__proc = Popen(cmd, shell=True,
                            cwd=getWorkingDir(self.path, params),
                            env=environment)

    def setSocket(self, clientSocket):
        """Called when an incoming connection has come"""
        self.__clientSocket = clientSocket
        self.__connectSocket()
        self.__parseClientLine()

        # Send runnee the 'start' message
        self.__sendStart()

    def stop(self):
        """Kills the process"""
        self.__disconnectSocket()
        self.__kill()
        self.sigFinished.emit(self.procID, KILLED)

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
        if self.__proc is not None:
            try:
                self.__proc.wait()
            except:
                pass
        self.__closeSocket()

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
        if self.__serverPort is None or self.procID is None:
            return None

        for item in os.listdir("/proc"):
            if item.isdigit():
                try:
                    f = open("/proc/" + item + "/cmdline", "r")
                    content = f.read()
                    f.close()

                    if "client/client_cdm_run.py" in content:
                        if "-p" in content and \
                           str(self.__serverPort) in content:
                            if "-i" in content and \
                                str(self.procID) in content:
                                return int(item)
                except:
                    pass
        return None

    def __disconnected(self):
        """Triggered when the client closed the connection"""
        self.__kill()
        self.sigFinished.emit(self.procID, DISCONNECTED)

    def __sendStart(self):
        """Sends the start command to the runnee"""
        if self.__clientSocket:
            data = RequestContinue + EOT
            self.__clientSocket.write(data)

    def __sendExit(self):
        """sends the exit command to the runnee"""
        self.__disconnectSocket()
        if self.__clientSocket:
            data = RequestExit + EOT
            QApplication.processEvents()
            self.__clientSocket.write(data)
            self.__clientSocket.waitForBytesWritten()

    def __parseClientLine(self):
        """Parses a single line from the running client"""
        while self.__clientSocket and self.__clientSocket.bytesAvailable() > 0:
            self.__buffer += self.__clientSocket.readAll

            tryAgain = True
            while tryAgain:
                if self.__protocolState == self.PROTOCOL_CONTROL:
                    tryAgain = self.__processControlState()
                elif self.__protocolState == self.PROTOCOL_STDOUT:
                    tryAgain = self.__processStdoutStderrState(True)
                elif self.__protocolState == self.PROTOCOL_STDERR:
                    tryAgain = self.__processStdoutStderrState(False)
                else:
                    raise Exception("Unexpected protocol state")

    def __processStdoutStderrState(self, isStdout):
        """Analyzes receiving buffer in the STDOUT/STDERR state"""
        # Collect till "\x04\x04"
        index = self.__buffer.find(StdoutStderrEOT)
        if index == -1:
            # End has not been found
            if self.__buffer.endswith('\x04'):
                value = self.__buffer[:-1]
                self.__buffer = '\x04'
                if isStdout:
                    self.ClientStdout.emit(value)
                else:
                    self.ClientStderr.emit(value)
                QApplication.processEvents()
                return False

            # Partial stdout/stderr received
            value = self.__buffer
            self.__buffer = ""
            if isStdout:
                self.ClientStdout.emit(value)
            else:
                self.ClientStderr.emit(value)
            QApplication.processEvents()
            return False

        # Here stdout/stderr has been received in full
        value = self.__buffer[0:index]
        self.__buffer = self.__buffer[index + 2:]
        self.__protocolState = self.PROTOCOL_CONTROL
        if isStdout:
            self.ClientStdout.emit(value)
        else:
            self.ClientStderr.emit(value)
        QApplication.processEvents()
        return True

    def __processControlState(self):
        """Analyzes receiving buffer in the CONTROL state"""
        # Buffer is going to start with >ZZZ< message and ends with EOT
        index = self.__buffer.find(EOT)
        if index == -1:
            return False

        line = self.__buffer[0:index]
        self.__buffer = self.__buffer[index + len(EOT):]

        if not line.startswith('>'):
            print("Unexpected message received (no '>' at the beginning): '" +
                  line + "'")
            return self.__buffer != ""

        cmdIndex = line.find('<')
        if cmdIndex == -1:
            print("Unexpected message received (no '<' found): '" + line + "'")
            return self.__buffer != ""

        cmd = line[0:cmdIndex + 1]
        content = line[cmdIndex + 1:]

        if cmd == ResponseRaw:
            prompt, echo = eval(content)
            self.sigClientRawInput.emit(prompt, echo)
            return self.__buffer != ""

        if cmd == ResponseExit:
            try:
                retCode = int(content)
            except:
                # Must never happened
                retCode = -1
            self.__sendExit()
            self.sigFinished.emit(self.procID, retCode)
            QApplication.processEvents()
            return self.__buffer != ""

        if cmd == ResponseStdout:
            self.__protocolState = self.PROTOCOL_STDOUT
            return self.__buffer != ""

        if cmd == ResponseStderr:
            self.__protocolState = self.PROTOCOL_STDERR
            return self.__buffer != ""

        print("Unexpected message received (no control match): '" + line + "'")
        return self.__buffer != ""

    def userInput(self, collectedString):
        """Called when the user finished input"""
        if self.__clientSocket:
            data = collectedString.encode("utf8") + "\n"
            self.__clientSocket.write(data)


class RemoteProcess:

    """Stores attributes of a single process"""

    def __init__(self):
        self.procWrapper = None
        self.widget = None
        self.kind = None


class RunManager(QObject):

    """Manages the external running processes"""

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

        self.__prologueTimer(self)
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
            qs = clientSocket.readLine()
            jsonStr = bytes(qs).decode()

            try:
                method, procid, params = parseJSONMessage(jsonStr)
                if method != METHOD_PROC_ID_INFO:
                    logging.error('Unexpected message at the handshake stage. '
                                  'Expected: ' + METHOD_PROC_ID_INFO +
                                  '. Received: ' + str(method))
                    try:
                        clientSocket.close()
                    except:
                        pass
                    return
            except (TypeError, ValueError) as exc:
                self.__mainWindow.showStatusBarMessage(
                    'Unsolicited connection to the RunManager. Ignoring...')
                try:
                    clientSocket.close()
                except:
                    pass
                return

            procIndex = self.__getProcessIndex(procid)
            if procIndex is not None:
                self.__onProcessStarted(procid)
                self.__processes[procIndex].procWrapper.setSocket(clientSocket)

    def run(self, path, needDialog):
        """Runs the given script with redirected IO"""
        if needDialog:
            params = getRunParameters(path)
            # profilerParams = Settings().getProfilerSettings()
            # debuggerParams = Settings().getDebuggerSettings()
            dlg = RunDialog(path, params, None, None, RUN, self.__mainWindow)
            if dlg.exec_() != QDialog.Accepted:
                return
            addRunParams(path, dlg.runParams)

        # The parameters for the run are ready.
        # Start the run business.
        redirected = getRunParameters(path)['redirected']
        remoteProc = RemoteProcess()
        remoteProc.kind = RUN
        remoteProc.procWrapper = RemoteProcessWrapper(
            path, self.__tcpServer.serverPort(), redirected)
        if redirected:
            remoteProc.procWrapper.state = STATE_PROLOGUE
            self.__prologueProcesses.append((remoteProc.procWrapper.procID,
                                             time.time()))
            if not self.__prologueTimer.isActive():
                self.__prologueTimer.start(1000)
            remoteProc.widget = RunConsoleTabWidget(
                remoteProc.procWrapper.procID)
            self.__mainWindow.installIOConsole(remoteProc.widget, RUN)
            remoteProc.widget.appendIDEMessage(
                'Starting ' + path + '...')

            remoteProc.procWrapper.sigClientStdout.connect(
                remoteProc.widget.appendStdoutMessage)
            remoteProc.procWrapper.sigClientStderr.connect(
                remoteProc.widget.appendStderrMessage)
            remoteProc.procWrapper.sigClientRawInput.connect(
                remoteProc.widget.rawInput)
            remoteProc.widget.sigUserInput.connect(self.__onUserInput)

        remoteProc.procWrapper.sigFinished.connect(self.__onProcessFinished)
        self.__processes.append(remoteProc)

        try:
            remoteProc.procWrapper.start(RUN)
            if not redirected:
                if not self.__waitTimer.isActive():
                    self.__waitTimer.start(1000)
        except Exception as exc:
            # Failed to start:
            # - log approprietly
            # - remove from the list
            if redirected:
                remoteProc.widget.appendIDEMessage("Failed to start: " +
                                                   str(exc))
            else:
                logging.error(str(exc))
            del self.__processes[-1]

    def profile(self, path, needDialog):
        """Profiles the given script with redirected IO"""
        pass

    def debug(self, path, needDialog):
        """Debugs the given script with redirected IO"""
        pass

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

    def kill(self, procID):
        """Kills a single process"""
        index = self.__getProcessIndex(procID)
        if index is None:
            return
        item = self.__processes[index]
        if not item.procWrapper.redirected:
            return
        item.procWrapper.stop()

    def __getProcessIndex(self, procID):
        """Returns a process index in the list"""
        for index, item in enumerate(self.__processes):
            if item.procWrapper.procID == procID:
                return index
        return None

    def __onProcessFinished(self, procID, retCode):
        """Triggered when a process has finished"""
        index = self.__getProcessIndex(procID)
        if index is not None:
            item = self.__processes[index]
            if item.procWrapper.redirected:
                if item.widget:
                    item.widget.scriptFinished()
                    if retCode == KILLED:
                        msg = "Script killed"
                        tooltip = "killed"
                    elif retCode == DISCONNECTED:
                        msg = "Connection lost to the script process"
                        tooltip = "connection lost"
                    else:
                        msg = "Script finished with exit code " + str(retCode)
                        tooltip = "finished, exit code " + str(retCode)
                        item.procWrapper.wait()
                    item.widget.appendIDEMessage(msg)
                    self.__mainWindow.updateIOConsoleTooltip(procID, tooltip)
            del self.__processes[index]

    def __onProcessStarted(self, procID):
        """Triggered when a process has started"""
        index = self.__getProcessIndex(procID)
        if index is not None:
            item = self.__processes[index]
            if item.widget:
                item.widget.appendIDEMessage('Started')

    def __onUserInput(self, procID, userInput):
        """Triggered when the user input is collected"""
        index = self.__getProcessIndex(procID)
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
                    del self.__processes[index]
                else:
                    needNewTimer = True
            index -= 1
        if needNewTimer:
            self.__waitTimer.start(1000)

    def __onPrologueTimer(self):
        """Triggered when a prologue phase controlling timer fired"""
        needNewTimer = False
        index = len(self.__prologueProcesses) - 1
        while index >= 0:
            procid, startTime = self.__prologueProcesses[index]
            procIndex = self.__getProcessIndex(procid)
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
                        item.widget.appendIDEMessage('Timeout: the process did not start; killing the process.')
                        item.procWrapper.stop()
                    else:
                        needNewTimer = True
        if needNewTimer:
            self.__prologueTimer.start(1000)
