# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""Breakpoints margin: shows breakpoints and the current debug line"""

import os.path
import logging
import math
from sys import maxsize
from ui.qt import QWidget, QPainter, QModelIndex, QToolTip
import qutepart
from qutepart.margins import MarginBase
from utils.misc import extendInstance
from utils.pixmapcache import getPixmap
from utils.fileutils import isPythonMime
from utils.globals import GlobalData
from utils.settings import Settings
from debugger.bputils import getBreakpointLines
from debugger.breakpoint import Breakpoint


# Note: it incorporates all the editor related breakpoints functionality:
#       - creating a new one via a click
#       - updating the line numbers if needed
#       - validating
#       - etc.


def getMarginBits():
    """Provides the number of block value bits to cover maxBreakpoints value"""
    # 0 means no block value so +1 is required
    distinctValues = Settings()['maxBreakpoints'] + 1
    bits = 1
    while True:
        if 2**bits >= distinctValues:
            return bits
        bits += 1


class CDMBreakpointMargin(QWidget):

    """Breakpoints area widget"""

    BPOINT_MARK = 1
    TMP_BPOINT_MARK = 2
    DISABLED_BPOINT_MARK = 3

    def __init__(self, parent, debugger):
        QWidget.__init__(self, parent)

        extendInstance(self, MarginBase)
        MarginBase.__init__(self, parent, "cdm_bpoint_margin", getMarginBits())
        self.setMouseTracking(True)

        self.__debugger = debugger
        self.__breakpoints = {}     # block handle -> Breakpoint instance
        self.__breakableLines = None
        self.__maxBreakpoints = Settings()['maxBreakpoints']
        self.__bgColor = GlobalData().skin['bpointsMarginPaper']

        self.__marks = {
            self.BPOINT_MARK: [getPixmap('dbgbpointmarker.png'), 0],
            self.TMP_BPOINT_MARK: [getPixmap('dbgtmpbpointmarker.png'), 0],
            self.DISABLED_BPOINT_MARK: [getPixmap('dbgdisbpointmarker.png'), 0]}

        for item in self.__marks:
            self.__marks[item][1] = self.__marks[item][0].height()
            if self.__marks[item][0].height() != self.__marks[item][0].width():
                logging.error('breakpoint margin pixmap needs to be square')

        self.myUUID = None
        if hasattr(self._qpart._parent, 'getUUID'):
            self.myUUID = self._qpart._parent.getUUID()

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)

        self.blockClicked.connect(self.__onBlockClicked)

        self._qpart.blockCountChanged.connect(self.__onBlockCountChanged)

        bpointModel = self.__debugger.getBreakPointModel()
        bpointModel.rowsAboutToBeRemoved.connect(self.__deleteBreakPoints)
        bpointModel.sigDataAboutToBeChanged.connect(
            self.__breakPointDataAboutToBeChanged)
        bpointModel.dataChanged.connect(self.__changeBreakPoints)
        bpointModel.rowsInserted.connect(self.__addBreakPoints)

    def paintEvent(self, event):
        """Paint the margin"""
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.__bgColor)
        oneLineHeight = self._qpart.fontMetrics().height()

        block = self._qpart.firstVisibleBlock()
        geometry = self._qpart.blockBoundingGeometry(block)
        blockBoundingGeometry = geometry.translated(
            self._qpart.contentOffset())
        top = blockBoundingGeometry.top()
        # bottom = top + blockBoundingGeometry.height()

        for block in qutepart.iterateBlocksFrom(block):
            height = self._qpart.blockBoundingGeometry(block).height()
            if top > event.rect().bottom():
                break
            if block.isVisible():
                # lineNo = block.blockNumber() + 1
                blockValue = self.getBlockValue(block)
                pixmap = None
                if blockValue != 0:
                    bpoint = self.__breakpoints[blockValue]
                    if not bpoint.isEnabled():
                        markType = self.DISABLED_BPOINT_MARK
                    elif bpoint.isTemporary():
                        markType = self.TMP_BPOINT_MARK
                    else:
                        markType = self.BPOINT_MARK
                    pixmap, edge = self.__marks[markType]

                if pixmap:
                    xPos = 0
                    yPos = top
                    if edge <= oneLineHeight:
                        yPos += math.ceil((oneLineHeight - edge) / 2)
                    else:
                        edge = oneLineHeight
                        xPos = math.ceil((self.width() - edge) / 2)
                    painter.drawPixmap(xPos, yPos, edge, edge, pixmap)
            top += height

    def mouseMoveEvent(self, event):
        """Tooltips for the marks"""
        if self.__breakpoints:
            textCursor = self._qpart.cursorForPosition(event.pos())
            block = textCursor.block()
            msg = None

            blockValue = self.getBlockValue(block)
            if blockValue != 0:
                bpoint = self.__breakpoints[blockValue]
                if not bpoint.isEnabled():
                    msg = 'Disabled breakpoint'
                elif bpoint.isTemporary():
                    msg = 'Temporary breakpoint'
                else:
                    msg = 'Regular breakpoint'

            if msg:
                QToolTip.showText(event.globalPos(), msg)
            else:
                QToolTip.hideText()
        return QWidget.mouseMoveEvent(self, event)

    @staticmethod
    def width():
        """Desired width"""
        return 16

    def setBackgroundColor(self, color):
        """Sets the new background color"""
        if self.__bgColor != color:
            self.__bgColor = color
            self.update()

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered on the changed file type"""
        del fileName    # unused argument
        if uuid == self.myUUID:
            MarginBase.setVisible(self, isPythonMime(newFileType))

    def restoreBreakpoints(self):
        """Restores the breakpoints"""
        for _, bpoint in self.__breakpoints.items():
            line = bpoint.getLineNumber()
            self.setBlockValue(
                self._qpart.document().findBlockByNumber(line - 1), 0)
        self.__breakpoints = {}
        self.__addBreakPoints(
            QModelIndex(), 0,
            self.__debugger.getBreakPointModel().rowCount() - 1)
        self.validateBreakpoints()
        self.update()

    def setDebugMode(self, debugOn, disableEditing):
        """Called to switch between debug/development"""
        del debugOn         # unused argument
        del disableEditing  # unused argument
        self.__breakableLines = None

    def isLineBreakable(self, line=None, enforceRecalc=False,
                        enforceSure=False):
        """True if a breakpoint could be placed on the current line"""
        fileName = self._qpart._parent.getFileName()

        if fileName is None or fileName == "" or not os.path.isabs(fileName):
            return False
        if not self._qpart.isPythonBuffer():
            return False

        if line is None:
            curPos = self._qpart.cursorPosition
            line = curPos[0] + 1
        if self.__breakableLines is not None and not enforceRecalc:
            return line in self.__breakableLines

        self.__breakableLines = getBreakpointLines(fileName, self._qpart.text,
                                                   enforceRecalc)

        if self.__breakableLines is None:
            if not enforceSure:
                # Be on the safe side - if there is a problem of
                # getting the breakable lines, let the user decide
                return True
            return False

        return line in self.__breakableLines

    def newBreakpointWithProperties(self, bpoint):
        """Sets a new breakpoint and its properties"""
        if len(self.__breakpoints) >= Settings()['maxBreakpoints']:
            logging.error('The max number of breakpoints per file (' +
                          str(Settings()['maxBreakpoints']) +
                          ') is exceeded')
            return

        line = bpoint.getLineNumber()
        bpointHandle = self.__getAvailableHandle()
        self.__breakpoints[bpointHandle] = bpoint
        self.setBlockValue(self._qpart.document().findBlockByNumber(line - 1),
                           bpointHandle)
        self.update()

    def deleteAllBreakpoints(self):
        """Deletes all the breakpoints in the buffer"""
        self.__deleteBreakPointsInLineRange(1, self._qpart.lines())

    def clearBreakpoint(self, line):
        """Clears a breakpoint"""
        for handle, bpoint in self.__breakpoints.items():
            if bpoint.getLineNumber() == line:
                self.setBlockValue(
                    self._qpart.document().findBlockByNumber(line - 1), 0)
                del self.__breakpoints[handle]
                self.update()
                return

    def validateBreakpoints(self):
        """Checks breakpoints and deletes those which are invalid"""
        if not self.__breakpoints:
            return

        fileName = self._qpart._parent.getFileName()
        breakableLines = getBreakpointLines(fileName, self._qpart.text,
                                            True, False)

        toBeDeleted = []
        for _, bpoint in self.__breakpoints.items():
            bpointLine = bpoint.getLineNumber()
            if breakableLines is None or bpointLine not in breakableLines:
                toBeDeleted.append(bpointLine)

        if toBeDeleted:
            model = self.__debugger.getBreakPointModel()
            for line in toBeDeleted:
                location = ':'.join([fileName, str(line)])
                if breakableLines is None:
                    msg = 'Breakpoint at ' + location + ' does not point to ' \
                          'a breakable line (file is not compilable).'
                else:
                    msg = 'Breakpoint at ' + location + ' does not point to ' \
                          'a breakable line anymore.'
                logging.warning(msg + ' The breakpoint is deleted.')
                index = model.getBreakPointIndex(fileName, line)
                self.setBlockValue(
                    self._qpart.document().findBlockByNumber(line - 1), 0)
                model.deleteBreakPointByIndex(index)

    def __getAvailableHandle(self):
        """Provides the available handle"""
        occupiedHandles = list(self.__breakpoints.keys())
        vacantHandle = 1
        while True:
            if vacantHandle not in occupiedHandles:
                return vacantHandle
            vacantHandle += 1

    def __addBreakpoint(self, line, temporary, enabled=True):
        """Adds a new breakpoint"""
        # The prerequisites:
        # - it is saved buffer
        # - it is a python buffer
        # - it is a breakable line
        # are checked in the function
        if not self.isLineBreakable(line, True, True):
            return

        fileName = self._qpart._parent.getFileName()
        bpoint = Breakpoint(fileName, line, "", temporary, enabled, 0)
        self.__debugger.getBreakPointModel().addBreakpoint(bpoint)

    def __addBreakPoints(self, parentIndex, start, end):
        """Adds breakpoints"""
        bpointModel = self.__debugger.getBreakPointModel()
        fileName = self._qpart._parent.getFileName()

        for row in range(start, end + 1):
            index = bpointModel.index(row, 0, parentIndex)
            bpoint = bpointModel.getBreakPointByIndex(index)
            bpFileName = bpoint.getAbsoluteFileName()

            if bpFileName == fileName:
                self.newBreakpointWithProperties(bpoint)

    def __deleteBreakPoints(self, parentIndex, start, end):
        """Deletes breakpoints"""
        bpointModel = self.__debugger.getBreakPointModel()
        fileName = self._qpart._parent.getFileName()

        for row in range(start, end + 1):
            index = bpointModel.index(row, 0, parentIndex)

            bpoint = bpointModel.getBreakPointByIndex(index)
            bpFileName = bpoint.getAbsoluteFileName()

            if bpFileName == fileName:
                self.clearBreakpoint(bpoint.getLineNumber())

    def __changeBreakPoints(self, startIndex, endIndex):
        """Sets changed breakpoints"""
        self.__addBreakPoints(QModelIndex(),
                              startIndex.row(), endIndex.row())

    def __breakPointDataAboutToBeChanged(self, startIndex, endIndex):
        """Handles the dataAboutToBeChanged signal of the breakpoint model"""
        self.__deleteBreakPoints(QModelIndex(),
                                 startIndex.row(), endIndex.row())

    def __toggleBreakpoint(self, line, temporary=False):
        """Toggles the line breakpoint"""
        # Clicking loop: none->regular->temporary->disabled->none
        fileName = self._qpart._parent.getFileName()
        model = self.__debugger.getBreakPointModel()
        for _, bpoint in self.__breakpoints.items():
            if bpoint.getLineNumber() == line:
                index = model.getBreakPointIndex(fileName, line)
                model.deleteBreakPointByIndex(index)
                if not bpoint.isEnabled():
                    self.setBlockValue(
                        self._qpart.document().findBlockByNumber(line - 1), 0)
                elif bpoint.isTemporary():
                    self.__addBreakpoint(line, False, False)
                else:
                    self.__addBreakpoint(line, True)
                return
        if len(self.__breakpoints) < self.__maxBreakpoints:
            self.__addBreakpoint(line, temporary)
        else:
            logging.error('Max breakpoint number per file (' +
                          str(self.__maxBreakpoints) +
                          ') has been reached. The breakpoint is not added.')

    def __deleteBreakPointsInLineRange(self, startFrom, count):
        """Deletes breakpoints which fall into the given lines range"""
        toBeDeleted = []
        limit = startFrom + count - 1
        for _, bpoint in self.__breakpoints.items():
            bpointLine = bpoint.getLineNumber()
            if bpointLine >= startFrom and bpointLine <= limit:
                toBeDeleted.append(bpointLine)

        if toBeDeleted:
            model = self.__debugger.getBreakPointModel()
            fileName = self._qpart._parent.getFileName()
            for line in toBeDeleted:
                index = model.getBreakPointIndex(fileName, line)
                self.setBlockValue(
                    self._qpart.document().findBlockByNumber(line - 1), 0)
                model.deleteBreakPointByIndex(index)

    def __onBlockClicked(self, block):
        """Margin of the block has been clicked"""
        lineNo = block.blockNumber() + 1
        for _, bpoint in self.__breakpoints.items():
            if bpoint.getLineNumber() == lineNo:
                # Breakpoint marker is set for this line already
                self.__toggleBreakpoint(lineNo)
                return

        # Check if it is a python file
        if not self._qpart.isPythonBuffer():
            return

        fileName = self._qpart._parent.getFileName()
        if fileName is None or fileName == "" or not os.path.isabs(fileName):
            logging.warning("The buffer has to be saved "
                            "before setting breakpoints")
            return

        breakableLines = getBreakpointLines("", self._qpart.text, True, False)
        if breakableLines is None:
            logging.warning("The breakable lines could not be identified "
                            "due to the file compilation errors. Fix the code "
                            "and try again.")
            return

        breakableLines = list(breakableLines)
        breakableLines.sort()
        if not breakableLines:
            logging.warning("There are no breakable lines")
            return

        if lineNo in breakableLines:
            self.__toggleBreakpoint(lineNo)
            return

        # There are breakable lines however the user requested a line which
        # is not breakable
        candidateLine = breakableLines[0]
        if lineNo < breakableLines[0]:
            candidateLine = breakableLines[0]
        elif lineNo > breakableLines[-1]:
            candidateLine = breakableLines[-1]
        else:
            lowerDistance = maxsize
            upperDistance = maxsize

            for breakableLine in breakableLines:
                if breakableLine < lineNo:
                    lowerDistance = min(lowerDistance, lineNo - breakableLine)
                else:
                    upperDistance = min(upperDistance, breakableLine - lineNo)
            if lowerDistance < upperDistance:
                candidateLine = lineNo - lowerDistance
            else:
                candidateLine = lineNo + upperDistance

        if not self._qpart.isLineOnScreen(candidateLine - 1):
            # The redirected breakpoint line is not on the screen, scroll it
            self._qpart.ensureLineOnScreen(candidateLine - 1)
            self._qpart.setFirstVisible(max(0, candidateLine - 2))

        self.__toggleBreakpoint(candidateLine)

    def __onBlockCountChanged(self):
        """Number of lines in the file has changed"""
        if not self.__breakpoints:
            return

        oldSet = set(self.__breakpoints.keys())

        currentSet = set()
        currentHandleToLine = {}
        startBlock = self._qpart.document().firstBlock()
        for block in qutepart.iterateBlocksFrom(startBlock):
            handle = self.getBlockValue(block)
            if handle != 0:
                currentSet.add(handle)
                currentHandleToLine[handle] = block.blockNumber() + 1

        deletedHandles = oldSet - currentSet

        changedLineHandles = set()
        for cHandle, cLine in currentHandleToLine.items():
            if self.__breakpoints[cHandle].getLineNumber() != cLine:
                changedLineHandles.add(cHandle)

        if deletedHandles or changedLineHandles:
            fileName = self._qpart._parent.getFileName()
            model = self.__debugger.getBreakPointModel()

            for deletedHandle in deletedHandles:
                deletedBP = self.__breakpoints[deletedHandle]
                deletedLine = deletedBP.getLineNumber()
                del self.__breakpoints[deletedHandle]
                index = model.getBreakPointIndex(fileName, deletedLine)
                model.deleteBreakPointByIndex(index)

            for changedHandle in changedLineHandles:
                newLineNo = currentHandleToLine[changedHandle]
                self.__breakpoints[changedHandle].updateLineNumber(newLineNo)
                index = model.getBreakPointIndex(fileName, newLineNo)
                model.updateLineNumberByIndex(index, newLineNo)

    def onClose(self):
        """The editor is going to be closed"""
        # Prevent clearing breakpoints when an editor is closed.
        # The signal is generated when the text is deleted and it happens when
        # the editor is destroyed
        self._qpart.blockCountChanged.disconnect(self.__onBlockCountChanged)
