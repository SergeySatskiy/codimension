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
                                      METHOD_BP_ENABLE, METHOD_BP_IGNORE,
                                      METHOD_STEP_QUIT, METHOD_CALL_TRACE,
                                      METHOD_EXECUTE_STATEMENT,
                                      METHOD_EXEC_STATEMENT_ERROR,
                                      METHOD_EXEC_STATEMENT_OUTPUT,
                                      METHOD_SIGNAL, METHOD_THREAD_SET)
from .bputils import getBreakpointLines
from .breakpointmodel import BreakPointModel
from .watchpointmodel import WatchPointModel
from .editbreakpoint import BreakpointEditDialog


class CodimensionDebugger(QObject):

    """Debugger server implementation"""

    sigDebuggerStateChanged = pyqtSignal(int)
    sigClientLine = pyqtSignal(str, int, bool)
    sigClientException = pyqtSignal(str, str, list, bool)
    sigClientSyntaxError = pyqtSignal(str, str, str, int, int)
    sigClientStack = pyqtSignal(list)
    sigClientThreadList = pyqtSignal(int, list)
    sigClientVariables = pyqtSignal(int, list)
    sigClientVariable = pyqtSignal(int, list)
    sigClientThreadSet = pyqtSignal()
    sigClientClearBreak = pyqtSignal(str, int)
    sigClientBreakConditionError = pyqtSignal(str, int)
    sigClientCallTrace = pyqtSignal(bool, str, int, str, str, int, str)

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

        self.__handlers = {}
        self.__initHandlers()

    def __initHandlers(self):
        """Initializes the incoming messages handlers"""
        self.__handlers = {
            METHOD_LINE: self.__handleLine,
            METHOD_STACK: self.__handleStack,
            METHOD_THREAD_LIST: self.__handleThreadList,
            METHOD_VARIABLES: self.__handleVariables,
            METHOD_DEBUG_STARTUP: self.__handleStartup,
            METHOD_FORK_TO: self.__handleForkTo,
            METHOD_CLEAR_BP: self.__handleClearBP,
            METHOD_SYNTAX_ERROR: self.__handleSyntaxError,
            METHOD_VARIABLE: self.__handleVariable,
            METHOD_BP_CONDITION_ERROR: self.__handleBPConditionError,
            METHOD_EXCEPTION: self.__handleException,
            METHOD_CALL_TRACE: self.__handleCallTrace,
            METHOD_EXEC_STATEMENT_ERROR: self.__handleExecStatementError,
            METHOD_EXEC_STATEMENT_OUTPUT: self.__handleExecuteStatementOutput,
            METHOD_SIGNAL: self.__handleSignal,
            METHOD_THREAD_SET: self.__handleThreadSet}

    def getScriptPath(self):
        """Provides the path to the debugged script"""
        return self.__fileName

    def getState(self):
        """Provides the debugger state"""
        return self.__state

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
        if self.__procuuid == procuuid:
            try:
                self.__handlers[method](params)
            except KeyError:
                logging.error('Unhandled message received by the debugger. '
                              'Method: ' + str(method) +
                              ' Parameters: ' + repr(params))

    def __handleLine(self, params):
        """Handles METHOD_LINE"""
        stack = params['stack']
        if self.__stopAtFirstLine:
            topFrame = stack[0]
            self.sigClientLine.emit(topFrame[0], int(topFrame[1]), False)
            self.sigClientStack.emit(stack)
        else:
            self.__stopAtFirstLine = True
            QTimer.singleShot(0, self.remoteContinue)

        self.__changeDebuggerState(self.STATE_IN_IDE)

    def __handleStack(self, params):
        """Handles METHOD_STACK"""
        stack = params['stack']
        if self.__stopAtFirstLine:
            topFrame = stack[0]
            self.sigClientLine.emit(topFrame[0], int(topFrame[1]), True)
            self.sigClientStack.emit(stack)
        else:
            self.__stopAtFirstLine = True
            QTimer.singleShot(0, self.remoteContinue)

    def __handleThreadList(self, params):
        """Handles METHOD_THREAD_LIST"""
        self.sigClientThreadList.emit(params['currentID'],
                                      params['threadList'])

    def __handleVariables(self, params):
        """Handles METHOD_VARIABLES"""
        self.sigClientVariables.emit(params['scope'], params['variables'])

    def __handleStartup(self, params):
        """Handles METHOD_DEBUG_STARTUP"""
        del params  # unused argument
        self.__sendBreakpoints()
        self.__sendWatchpoints()

    def __handleForkTo(self, params):
        """Handles METHOD_FORK_TO"""
        del params  # unused argument
        self.__askForkTo()

    def __handleClearBP(self, params):
        """Handles METHOD_CLEAR_BP"""
        self.sigClientClearBreak.emit(params['filename'], params['line'])

    def __handleSyntaxError(self, params):
        """Handles METHOD_SYNTAX_ERROR"""
        self.sigClientSyntaxError.emit(self.__procuuid,
                                       params['message'], params['filename'],
                                       params['line'],
                                       params['characternumber'])

    def __handleVariable(self, params):
        """Handles METHOD_VARIABLE"""
        self.sigClientVariable.emit(params['scope'],
                                    [params['variable']] + params['variables'])

    def __handleBPConditionError(self, params):
        """Handles METHOD_BP_CONDITION_ERROR"""
        self.sigClientBreakConditionError.emit(params['filename'],
                                               params['line'])

    def __handleException(self, params):
        """Handles METHOD_EXCEPTION"""
        self.__changeDebuggerState(self.STATE_IN_IDE)
        if params:
            stack = params['stack']
            if stack:
                if stack[0] and stack[0][0] == "<string>":
                    for stackEntry in stack:
                        if stackEntry[0] == "<string>":
                            stackEntry[0] = self.__fileName
                        else:
                            break
            excType = params['type']
            isUnhandled = excType is None or \
                excType.lower().startswith('unhandled') or \
                not stack
            self.sigClientException.emit(excType, params['message'],
                                         stack, isUnhandled)
        else:
            isUnhandled = True
            self.sigClientException.emit('', '', [], True)

    def __handleCallTrace(self, params):
        """Handles METHOD_CALL_TRACE"""
        isCall = params['event'] == 'c'
        src = params['from']
        dest = params['to']
        self.sigClientCallTrace.emit(
            isCall, src['filename'], src['linenumber'], src['codename'],
            dest['filename'], dest['linenumber'], dest['codename'])

    @staticmethod
    def __handleExecStatementError(params):
        """Handles METHOD_EXEC_STATEMENT_ERROR"""
        logging.error('Execute statement error:\n' + params['text'])

    @staticmethod
    def __handleExecuteStatementOutput(params):
        """Handles METHOD_EXEC_STATEMENT_OUTPUT"""
        text = params['text']
        if text:
            logging.info('Statement execution succeeded. Output:\n' + text)
        else:
            logging.info('Statement execution succeeded. No output generated.')

    def __handleSignal(self, params):
        """Handles METHOD_SIGNAL"""
        message = params['message']
        fileName = params['filename']
        linenumber = params['linenumber']
        # funcName = params['function']
        # arguments = params['arguments']

        self.sigClientLine.emit(fileName, linenumber, False)
        logging.error('The program generated the signal "' + message + '"\n'
                      'File: ' + fileName + ' Line: ' + str(linenumber))

    def __handleThreadSet(self, params):
        """Handles METHOD_THREAD_SET"""
        del params  # unused argument
        self.sigClientThreadSet.emit()

    def onProcessFinished(self, procuuid, retCode):
        """Process finished. The retCode may indicate a disconnection."""
        del retCode     # unused argument

        if self.__procuuid == procuuid:
            self.__procWrapper = None
            self.__procuuid = None
            self.__fileName = None
            self.__runParameters = None
            self.__debugSettings = None
            self.__stopAtFirstLine = None

            self.__changeDebuggerState(self.STATE_STOPPED)
            self.__mainWindow.switchDebugMode(False)

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

    def remoteClientVariable(self, scope, var, framenr=0, filters=None):
        """Provides the client variable.

        scope - 0 => local, 1 => global
        """
        self.__sendJSONCommand(METHOD_VARIABLE,
                               {'frameNumber': framenr, 'variable': var,
                                'scope': scope, 'filters': filters})

    def remoteExecuteStatement(self, statement, framenr):
        """Executes the expression in the current context of the debuggee"""
        self.__sendJSONCommand(METHOD_EXECUTE_STATEMENT,
                               {'statement': statement,
                                'frameNumber': framenr})

    def remoteBreakpoint(self, fileName, line,
                         isSetting, condition=None, temporary=False):
        """Sets or clears a breakpoint"""
        params = {'filename': fileName, 'line': line,
                  'setBreakpoint': isSetting, 'condition': condition,
                  'temporary': temporary}
        self.__sendJSONCommand(METHOD_SET_BP, params)

    def remoteSetThread(self, tid):
        """Sets the given thread as the current"""
        self.__sendJSONCommand(METHOD_THREAD_SET, {'threadID': tid})

    def stopDebugging(self, exitCode=None):
        """Stops the debugging session"""
        if self.__procWrapper:
            if exitCode is None:
                self.__sendJSONCommand(METHOD_STEP_QUIT, None)
            else:
                self.__sendJSONCommand(METHOD_STEP_QUIT,
                                       {'exitCode': exitCode})

    def stopCalltrace(self):
        """Sends a message to stop call tracing"""
        if self.__procWrapper:
            self.__sendJSONCommand(METHOD_CALL_TRACE, {'enable': False})

    def startCalltrace(self):
        """Sends a message to start call tracing"""
        if self.__procWrapper:
            self.__sendJSONCommand(METHOD_CALL_TRACE, {'enable': True})

    def __sendJSONCommand(self, method, params):
        """Sends a message to the debuggee"""
        if self.__procWrapper:
            self.__procWrapper.sendJSONCommand(method, params)
        else:
            raise Exception('Trying to send JSON command from the debugger '
                            'to the debugged program wneh there is no remote '
                            'process wrapper. Method: ' + str(method) +
                            'Parameters: ' + repr(params))
