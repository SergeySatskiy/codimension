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

"""Debugger server"""

import logging
import os.path
from ui.qt import (pyqtSignal, QTimer, QObject, QModelIndex,
                   QMessageBox, QDialog)
from utils.pixmapcache import getIcon
from .client.protocol_cdm_dbg import (METHOD_LINE, METHOD_STACK, METHOD_STEP,
                                      METHOD_THREAD_LIST, METHOD_VARIABLES,
                                      METHOD_CONTINUE, METHOD_DEBUG_STARTUP,
                                      METHOD_FORK_TO, METHOD_CLEAR_BP,
                                      METHOD_SYNTAX_ERROR, METHOD_EXCEPTION,
                                      METHOD_VARIABLE, METHOD_STEP_OVER,
                                      METHOD_BP_CONDITION_ERROR,
                                      METHOD_SET_BP, METHOD_STEP_OUT,
                                      METHOD_BP_ENABLE, METHOD_BP_IGNORE)
from .bputils import getBreakpointLines
from .breakpointmodel import BreakPointModel
from .watchpointmodel import WatchPointModel
from .editbreakpoint import BreakpointEditDialog


class CodimensionDebugger(QObject):

    """Debugger server implementation"""

    sigDebuggerStateChanged = pyqtSignal(int)
    sigClientLine = pyqtSignal(str, int, bool)
    sigClientException = pyqtSignal(str, str, list)
    sigClientSyntaxError = pyqtSignal(str, str, int, int)
    sigEvalOK = pyqtSignal(str)
    sigEvalError = pyqtSignal(str)
    sigExecOK = pyqtSignal(str)
    sigExecError = pyqtSignal(str)
    sigClientStack = pyqtSignal(list)
    sigClientThreadList = pyqtSignal(int, list)
    sigClientVariables = pyqtSignal(int, list)
    sigClientVariable = pyqtSignal(int, list)
    sigClientThreadSet = pyqtSignal()
    sigClientClearBreak = pyqtSignal(str, int)
    sigClientBreakConditionError = pyqtSignal(str, int)

    STATE_STOPPED = 0
    STATE_IN_CLIENT = 1
    STATE_IN_IDE = 2

    def __init__(self, mainWindow):
        QObject.__init__(self)

        # To control the user interface elements
        self.__mainWindow = mainWindow
        self.__state = self.STATE_STOPPED

        self.__stopAtFirstLine = None

        self.__procWrapper = None
        self.__procuuid = None
        self.__fileName = None
        self.__runParameters = None
        self.__debugSettings = None

        self.__breakpointModel = BreakPointModel(self)
        self.__watchpointModel = WatchPointModel(self)

        self.__breakpointModel.rowsAboutToBeRemoved.connect(
            self.__deleteBreakPoints)
        self.__breakpointModel.sigDataAboutToBeChanged.connect(
            self.__breakPointDataAboutToBeChanged)
        self.__breakpointModel.dataChanged.connect(self.__changeBreakPoints)
        self.__breakpointModel.rowsInserted.connect(self.__addBreakPoints)
        self.sigClientClearBreak.connect(self.__clientClearBreakPoint)
        self.sigClientBreakConditionError.connect(
            self.__clientBreakConditionError)

    def getScriptPath(self):
        """Provides the path to the debugged script"""
        return self.__fileName

    def getRunDebugParameters(self):
        """Provides the running and debugging parameters"""
        return self.__runParameters, self.__debugSettings

    def getBreakPointModel(self):
        """Provides a reference to the breakpoints model"""
        return self.__breakpointModel

    def getWatchPointModel(self):
        """Provides a reference to the watch points model"""
        return self.__watchpointModel

    def __changeDebuggerState(self, newState):
        """Changes the debugger state"""
        if newState != self.__state:
            self.__state = newState
            self.sigDebuggerStateChanged.emit(newState)

    def onDebugSessionStarted(self, procWrapper, fileName,
                              runParameters, debugSettings):
        """Starts debugging a script. Run manager informs about it."""
        if self.__state != self.STATE_STOPPED:
            raise Exception('Logic error. Debugging session started while the '
                            'previous one has not finished.')

        self.__procWrapper = procWrapper
        self.__procuuid = procWrapper.procuuid
        self.__fileName = fileName
        self.__runParameters = runParameters
        self.__debugSettings = debugSettings
        self.__stopAtFirstLine = debugSettings.stopAtFirstLine

        self.__mainWindow.switchDebugMode(True)
        self.__changeDebuggerState(self.STATE_IN_CLIENT)

    def onIncomingMessage(self, procuuid, method, params):
        """Message from the debuggee has been received"""
        if self.__procuuid != procuuid:
            return

        if method in [METHOD_LINE, METHOD_STACK]:
            stack = params['stack']
            if self.__stopAtFirstLine:
                topFrame = stack[0]
                self.sigClientLine.emit(topFrame[0], int(topFrame[1]),
                                        method == METHOD_STACK)
                self.sigClientStack.emit(stack)
            else:
                self.__stopAtFirstLine = True
                QTimer.singleShot(0, self.remoteContinue)

            if method == METHOD_LINE:
                self.__changeDebuggerState(self.STATE_IN_IDE)
            return

        if method == METHOD_THREAD_LIST:
            self.sigClientThreadList.emit(params['currentID'],
                                          params['threadList'])
            return

        if method == METHOD_VARIABLES:
            self.sigClientVariables.emit(params['scope'], params['variables'])
            return

        if method == METHOD_DEBUG_STARTUP:
            self.__sendBreakpoints()
            self.__sendWatchpoints()
            return

        if method == METHOD_FORK_TO:
            self.__askForkTo()
            return

        if method == METHOD_CLEAR_BP:
            self.sigClientClearBreak.emit(params['filename'], params['line'])
            return

        if method == METHOD_SYNTAX_ERROR:
            self.sigClientSyntaxError.emit(params['message'],
                                           params['filename'],
                                           params['line'],
                                           params['characternumber'])
            return

        if method == METHOD_VARIABLE:
            self.sigClientVariable.emit(params['scope'],
                                        params['variable'],
                                        params['variables'])
            return

        if method == METHOD_BP_CONDITION_ERROR:
            self.sigClientBreakConditionError.emit(params['filename'],
                                                   params['line'])
            return

        if method == METHOD_EXCEPTION:
            self.__changeDebuggerState(self.STATE_IN_IDE)
            self.sigClientException.emit(params['type'],
                                         params['message'],
                                         params['stack'])
            return




        print('Unprocessed message received by the debugger. '
              'Method: ' + str(method) + ' Parameters: ' + repr(params))

    def onProcessFinished(self, procuuid, retCode):
        """Process finished. The retCode may indicate a disconnection."""
        if self.__procuuid == procuuid:
            self.__procWrapper = None
            self.__procuuid = None
            self.__fileName = None
            self.__runParameters = None
            self.__debugSettings = None
            self.__stopAtFirstLine = None

            self.__changeDebuggerState(self.STATE_STOPPED)
            self.__mainWindow.switchDebugMode(False)

    def __processControlState(self):
        """Analyzes receiving buffer in the CONTROL state"""
        # Buffer is going to start with >ZZZ< message and ends with EOT
        cmd = line[0:cmdIndex + 1]
        content = line[cmdIndex + 1:]


        if cmd == ResponseThreadSet:
            self.sigClientThreadSet.emit()
            return self.__buffer != ""

        if cmd == ResponseEval:
            self.__protocolState = self.PROTOCOL_EVALEXEC
            return self.__buffer != ""

        if cmd == ResponseExec:
            self.__protocolState = self.PROTOCOL_EVALEXEC
            return self.__buffer != ""


        print("Unexpected message received (no control match): '" + line + "'")
        return self.__buffer != ""

    def __processEvalexecState(self):
        """Analyzes receiving buffer in the EVALEXEC state"""
        # Collect till ResponseEvalOK, ResponseEvalError,
        #              ResponseExecOK, ResponseExecError

        self.sigEvalOK.emit("")
        self.sigEvalError.emit("")
        self.sigExecOK.emit("")
        self.sigExecError.emit("")

    def __askForkTo(self):
        " Asks what to follow, a parent or a child "
        dlg = QMessageBox(QMessageBox.Question, "Client forking",
                          "Select the fork branch to follow")
        dlg.addButton(QMessageBox.Ok)
        dlg.addButton(QMessageBox.Cancel)

        btn1 = dlg.button(QMessageBox.Ok)
        btn1.setText("&Child process")
        btn1.setIcon(getIcon(''))

        btn2 = dlg.button(QMessageBox.Cancel)
        btn2.setText("&Parent process")
        btn2.setIcon(getIcon(''))

        dlg.setDefaultButton(QMessageBox.Cancel)
        res = dlg.exec_()

        if res == QMessageBox.Cancel:
            self.__sendJSONCommand(METHOD_FORK_TO, {'target': 'parent'})
        else:
            self.__sendJSONCommand(METHOD_FORK_TO, {'target': 'child'})

    def __validateBreakpoints(self):
        """Checks all the breakpoints validity and deletes invalid"""
        # It is excepted that the method is called when all the files are
        # saved, e.g. when a new debugging session is started.
        for row in range(0, self.__breakpointModel.rowCount()):
            index = self.__breakpointModel.index(row, 0, QModelIndex())
            bpoint = self.__breakpointModel.getBreakPointByIndex(index)
            fileName = bpoint.getAbsoluteFileName()
            line = bpoint.getLineNumber()

            if not os.path.exists(fileName):
                logging.warning("Breakpoint at " + fileName + ":" +
                                str(line) + " is invalid (the file "
                                "disappeared from the filesystem). "
                                "The breakpoint is deleted.")
                self.__breakpointModel.deleteBreakPointByIndex(index)
                continue

            breakableLines = getBreakpointLines(fileName, None, True)
            if breakableLines is None:
                logging.warning("Breakpoint at " + fileName + ":" +
                                str(line) + " does not point to a breakable "
                                "line (the file could not be compiled). "
                                "The breakpoint is deleted.")
                self.__breakpointModel.deleteBreakPointByIndex(index)
                continue
            if line not in breakableLines:
                logging.warning("Breakpoint at " + fileName + ":" +
                                str(line) + " does not point to a breakable "
                                "line (the file was modified). "
                                "The breakpoint is deleted.")
                self.__breakpointModel.deleteBreakPointByIndex(index)
                continue

            # The breakpoint is OK, keep it
        return

    def __sendBreakpoints(self):
        """Sends the breakpoints to the debugged program"""
        self.__validateBreakpoints()
        self.__addBreakPoints(QModelIndex(), 0,
                              self.__breakpointModel.rowCount() - 1)

    def __addBreakPoints(self, parentIndex, start, end):
        """Adds breakpoints"""
        if self.__state == self.STATE_STOPPED:
            return

        for row in range(start, end + 1):
            index = self.__breakpointModel.index(row, 0, parentIndex)
            bpoint = self.__breakpointModel.getBreakPointByIndex(index)
            fileName = bpoint.getAbsoluteFileName()
            line = bpoint.getLineNumber()
            self.remoteBreakpoint(fileName, line, True,
                                  bpoint.getCondition(),
                                  bpoint.isTemporary())
            if not bpoint.isEnabled():
                self.__remoteBreakpointEnable(fileName, line, False)
            ignoreCount = bpoint.getIgnoreCount()
            if ignoreCount > 0:
                self.__remoteBreakpointIgnore(fileName, line,
                                              ignoreCount)

    def __deleteBreakPoints(self, parentIndex, start, end):
        """Deletes breakpoints"""
        if self.__state == self.STATE_STOPPED:
            return

        for row in range(start, end + 1):
            index = self.__breakpointModel.index(row, 0, parentIndex)
            bpoint = self.__breakpointModel.getBreakPointByIndex(index)
            fileName = bpoint.getAbsoluteFileName()
            line = bpoint.getLineNumber()
            self.remoteBreakpoint(fileName, line, False)

    def __breakPointDataAboutToBeChanged(self, startIndex, endIndex):
        """Handles the sigDataAboutToBeChanged signal of the bpoint model"""
        self.__deleteBreakPoints(QModelIndex(),
                                 startIndex.row(), endIndex.row())

    def __changeBreakPoints(self, startIndex, endIndex):
        """Sets changed breakpoints"""
        self.__addBreakPoints(QModelIndex(), startIndex.row(), endIndex.row())

    def __sendWatchpoints(self):
        """Sends the watchpoints to the debugged program"""
        pass

    def __remoteBreakpointEnable(self, fileName, line, enable):
        """Sends the breakpoint enability"""
        self.__sendJSONCommand(METHOD_BP_ENABLE,
                               {'filename': fileName, 'line': line,
                                'enable': enable})

    def __remoteBreakpointIgnore(self, fileName, line, ignoreCount):
        """Sends the breakpoint ignore count"""
        self.__sendJSONCommand(METHOD_BP_IGNORE,
                               {'filename': fileName, 'line': line,
                                'count': ignoreCount})

    def __clientClearBreakPoint(self, fileName, line):
        """Handles the sigClientClearBreak signal"""
        if self.__state == self.STATE_STOPPED:
            return

        index = self.__breakpointModel.getBreakPointIndex(fileName, line)
        if index.isValid():
            self.__breakpointModel.deleteBreakPointByIndex(index)

    def __clientBreakConditionError(self, fileName, line):
        """Handles the condition error"""
        logging.error("The condition of the breakpoint at " +
                      fileName + ":" + str(line) +
                      " contains a syntax error.")
        index = self.__breakpointModel.getBreakPointIndex(fileName, line)
        if not index.isValid():
            return
        bpoint = self.__breakpointModel.getBreakPointByIndex(index)
        if not bpoint:
            return

        dlg = BreakpointEditDialog(bpoint)
        if dlg.exec_() == QDialog.Accepted:
            newBpoint = dlg.getData()
            if newBpoint == bpoint:
                return
            self.__breakpointModel.setBreakPointByIndex(index, newBpoint)

    def remoteStep(self):
        """Single step in the debugged program"""
        self.__changeDebuggerState(self.STATE_IN_CLIENT)
        self.__sendJSONCommand(METHOD_STEP, None)

    def remoteStepOver(self):
        """Step over the debugged program"""
        self.__changeDebuggerState(self.STATE_IN_CLIENT)
        self.__sendJSONCommand(METHOD_STEP_OVER, None)

    def remoteStepOut(self):
        """Step out the debugged program"""
        self.__changeDebuggerState(self.STATE_IN_CLIENT)
        self.__sendJSONCommand(METHOD_STEP_OUT, None)

    def remoteContinue(self, special=False):
        """Continues the debugged program"""
        self.__changeDebuggerState(self.STATE_IN_CLIENT)
        self.__sendJSONCommand(METHOD_CONTINUE, {'special': special})

    def remoteThreadList(self):
        """Provides the threads list"""
        self.__sendJSONCommand(METHOD_THREAD_LIST, None)

    def remoteClientVariables(self, scope, framenr=0, filters=None):
        """Provides the client variables.

        scope - 0 => local, 1 => global
        """
        if filters is None:
            filters = []
        self.__sendJSONCommand(METHOD_VARIABLES,
                               {'frameNumber': framenr,
                                'scope': scope, 'filters': filters})

    def remoteClientVariable(self, scope, var, framenr=0):
        """Provides the client variable.
           scope - 0 => local, 1 => global
        """
        scope = int(scope)
        self.__sendCommand(RequestVariable +
                           var + ", " +
                           str(framenr) + ", " + str(scope) + "\n")

    def remoteEval(self, expression, framenr):
        """Evaluates the expression in the current context of the debuggee"""
        self.__sendCommand(RequestEval +
                           str(framenr) + ", " + expression + "\n")

    def remoteExec(self, statement, framenr):
        """Executes the expression in the current context of the debuggee"""
        self.__sendCommand(RequestExec +
                           str(framenr) + ", " + statement + "\n")

    def remoteBreakpoint(self, fileName, line,
                         isSetting, condition=None, temporary=False):
        """Sets or clears a breakpoint"""
        params = {'filename': fileName, 'line': line,
                  'setBreakpoint': isSetting, 'condition': condition,
                  'temporary': temporary}
        self.__sendJSONCommand(METHOD_SET_BP, params)

    def remoteSetThread(self, tid):
        """Sets the given thread as the current"""
        self.__sendCommand(RequestThreadSet + str(tid) + "\n")

    def __sendJSONCommand(self, method, params):
        """Sends a message to the debuggee"""
        if self.__procWrapper:
            self.__procWrapper.sendJSONCommand(method, params)
        else:
            raise Exception('Trying to send JSON command from the debugger '
                            'to the debugged program wneh there is no remote '
                            'process wrapper. Method: ' + str(method) +
                            'Parameters: ' + repr(params))
