# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Profiling in progress UI"""

import socket
import time
import logging
import errno
import os
from subprocess import Popen
from ui.qt import (Qt, QTimer, QCursor, QDialog, QDialogButtonBox, QVBoxLayout,
                   QLabel, QApplication)
from utils.globals import GlobalData
from utils.settings import Settings
from utils.run import getCwdCmdEnv, CMD_TYPE_PROFILE
from utils.procfeedback import decodeMessage, isProcessAlive, killProcess
from utils.misc import getLocaleDateTime
from utils.diskvaluesrelay import getRunParameters
from .profwidget import ProfileResultsWidget

POLL_INTERVAL = 0.1
HANDSHAKE_TIMEOUT = 15


def createDoneFeedbackSocket():
    """Creates a socket to wait for the 'done' message"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Zero port allows the system to pick any available port
    sock.bind(("127.0.0.1", 0))

    # Returns a bound socket and the port it bound to
    return sock, sock.getsockname()[1]


def getData(sock):
    """Checks if data avalable in the socket and reads it if so"""
    try:
        data = sock.recv(1024, socket.MSG_DONTWAIT)
    except socket.error as excpt:
        if excpt[0] == errno.EWOULDBLOCK:
            return ''
        raise
    return data


class ProfilingProgressDialog(QDialog):

    """Profiling progress message box"""

    def __init__(self, scriptName, parent=None):
        QDialog.__init__(self, parent)
        self.__cancelRequest = False
        self.__inProgress = False
        self.__scriptName = scriptName
        self.__childPID = None

        self.__createLayout()
        self.setWindowTitle('Profiling ' + os.path.basename(scriptName))
        QTimer.singleShot(0, self.__process)

    def keyPressEvent(self, event):
        """Processes the ESC key specifically"""
        if event.key() == Qt.Key_Escape:
            self.__onClose()
        else:
            QDialog.keyPressEvent(self, event)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(450, 20)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)

        # Info label
        self.infoLabel = QLabel(self)
        self.infoLabel.setTextFormat(1)
        self.infoLabel.setText("Profiling of the " + self.__scriptName +
                               " script is in progress...<br/>"
                               "<b>Note:</b> cancelling will try to "
                               "kill the profiler session.")
        verticalLayout.addWidget(self.infoLabel)

        # Buttons
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        self.__cancelButton = buttonBox.button(QDialogButtonBox.Cancel)
        verticalLayout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.__onClose)

    def __onClose(self):
        """Triggered when the cancel button is clicked"""
        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()

    def __process(self):
        """Runs profiling session and waits till it ends,
           fails or is cancelled
        """
        self.__inProgress = True
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        sock, port = createDoneFeedbackSocket()

        params = getRunParameters(self.__scriptName)
        workingDir, cmd, environment = getCwdCmdEnv(CMD_TYPE_PROFILE,
                                                    self.__scriptName, params,
                                                    Settings().terminalType,
                                                    port)
        try:
            # profProc =
            Popen(cmd, shell=True, cwd=workingDir, env=environment)
        except Exception as exc:
            self.__onError(str(exc))
            return

        # First stage: wait for a message with the process id
        startTime = time.time()
        while True:
            time.sleep(POLL_INTERVAL)
            QApplication.processEvents()
            if self.__cancelRequest:
                if self.__childPID is not None:
                    self.__onInterrupt()
                    return
                else:
                    self.infoLabel.setText("Cancel request received.\n"
                                           "Waiting for profiler child "
                                           "pid and finishing...")

            data = getData(sock)
            if data != "":
                # We've got the message, extract the PID to watch
                msgParts = decodeMessage(data)
                if len(msgParts) != 1:
                    self.__onError("Unexpected handshake message: '" +
                                   data + "'. Expected profiler child "
                                   "process PID.")
                    return
                try:
                    self.__childPID = int(msgParts[0])
                    if self.__cancelRequest:
                        self.__onInterrupt()
                        return
                    break   # Move to stage 2
                except:
                    self.__onError("Broken handshake message: '" +
                                   data + ". Cannot convert profiler "
                                   "child process PID to integer.")
                    return

            if time.time() - startTime > HANDSHAKE_TIMEOUT:
                self.__onError("Handshake timeout: "
                               "error spawning process to profile")
                return

        # Second stage: wait till PID has gone or finish confirmation received
        while True:
            time.sleep(POLL_INTERVAL)
            QApplication.processEvents()
            if self.__cancelRequest:
                self.__onInterrupt()
                return

            data = getData(sock)
            if data != "":
                # We've got the message, extract the profiler return code
                # Note: This would be the profiler (not the application) return
                #       I guess this is how the profiler is implemented
                msgParts = decodeMessage(data)
                if len(msgParts) != 1:
                    self.__onError("Unexpected final message: '" +
                                   data + "'. Expected profiler return code.")
                    return

                try:
                    retCode = int(msgParts[0])
                    break   # Collect the results and show them
                except:
                    self.__onError("Broken final message: '" +
                                   data + "'. Cannot convert "
                                   "profiler return code to integer.")
                    return

            # Check if the PID is still alive
            if not isProcessAlive(self.__childPID):
                self.__onError("Profiler session has been killed")
                return

        if retCode != 0:
            self.__onError("Profiler session failed, return code: " +
                           str(retCode))
            return

        # Now, the results are just fine. Collect and present them.
        self.infoLabel.setText("Done. Collecting the results...")
        self.__cancelButton.setEnabled(False)
        QApplication.processEvents()

        outputFile = GlobalData().getProfileOutputPath()

        reportTime = getLocaleDateTime()
        widget = ProfileResultsWidget(self.__scriptName, params, reportTime,
                                      outputFile, self.parentWidget())
        GlobalData().mainWindow.showProfileReport(
            widget, "Profiling report for " +
            os.path.basename(self.__scriptName) + " at " + reportTime)

        QApplication.restoreOverrideCursor()
        self.__inProgress = False
        self.accept()

    def __onError(self, msg):
        """Logs the error and exits"""
        QApplication.restoreOverrideCursor()
        logging.error(msg)
        self.close()

    def __onInterrupt(self):
        """Handles the user interrupt of the process,
           i.e. kill the child and exit"""
        if self.__childPID is None:
            self.__onError("Unknown profiler child process, cannot kill it")
            return

        self.infoLabel.setText("Killing profiler child process (pid: " +
                               str(self.__childPID) + ")...")
        try:
            killProcess(self.__childPID)
        except Exception as excpt:
            logging.error(str(excpt))
        QApplication.restoreOverrideCursor()
        self.close()
