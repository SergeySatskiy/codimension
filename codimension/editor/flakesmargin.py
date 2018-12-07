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


"""Pyflakes margin"""

import math
import logging
from html import escape
import qutepart
from qutepart.margins import MarginBase
from radon.complexity import cc_rank
from ui.qt import QWidget, QPainter, QToolTip
from utils.misc import extendInstance
from utils.globals import GlobalData
from utils.fileutils import isPythonMime
from utils.pixmapcache import getPixmap

# Pixmaps for the margin - populated once
MARKS = {}

class CDMFlakesMargin(QWidget):

    """Pyflakes area widget"""

    EXC_MARK = 1
    CURRENT_MARK = 2
    FLAKES_MARK = 3

    COMPLEXITY_A_MARK = ord('A')
    COMPLEXITY_B_MARK = ord('B')
    COMPLEXITY_C_MARK = ord('C')
    COMPLEXITY_D_MARK = ord('D')
    COMPLEXITY_E_MARK = ord('E')
    COMPLEXITY_F_MARK = ord('F')

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        extendInstance(self, MarginBase)
        MarginBase.__init__(self, parent, "cdm_flakes_margin", 1)
        self.setMouseTracking(True)

        self.__messages = {}
        self.__ccMessages = {}
        self.__bgColor = GlobalData().skin['flakesMarginPaper']
        self.__noTooltip = True

        self.currentDebugLine = None
        self.excptionLine = None

        if not MARKS:
            MARKS[self.CURRENT_MARK] = getPixmap('dbgcurrentmarker.png')
            MARKS[self.EXC_MARK] = getPixmap('dbgexcptmarker.png')
            MARKS[self.FLAKES_MARK] = getPixmap('pyflakesmsgmarker.png')
            MARKS[self.COMPLEXITY_A_MARK] = getPixmap('complexity-a.png')
            MARKS[self.COMPLEXITY_B_MARK] = getPixmap('complexity-b.png')
            MARKS[self.COMPLEXITY_C_MARK] = getPixmap('complexity-c.png')
            MARKS[self.COMPLEXITY_D_MARK] = getPixmap('complexity-d.png')
            MARKS[self.COMPLEXITY_E_MARK] = getPixmap('complexity-e.png')
            MARKS[self.COMPLEXITY_F_MARK] = getPixmap('complexity-f.png')

            for item in MARKS:
                if MARKS[item].height() != MARKS[item].width():
                    logging.error('analysis margin pixmap needs to be square')

        self.myUUID = None
        if hasattr(self._qpart._parent, 'getUUID'):
            self.myUUID = self._qpart._parent.getUUID()

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)
        self._qpart.blockCountChanged.connect(self.update)

    def paintEvent(self, event):
        """Paints the margin"""
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
                lineNo = block.blockNumber() + 1
                pixmap = None
                if lineNo == self.excptionLine:
                    pixmap = MARKS[self.EXC_MARK]
                elif lineNo == self.currentDebugLine:
                    pixmap = MARKS[self.CURRENT_MARK]
                elif self.isBlockMarked(block):
                    if lineNo in self.__ccMessages:
                        pixmap = MARKS[self.__ccMessages[lineNo][1]]
                    else:
                        pixmap = MARKS[self.FLAKES_MARK]

                if pixmap:
                    xPos = 0
                    yPos = top
                    pixmapSide = self.width()   # Pixmap is square!
                    if oneLineHeight >= pixmapSide:
                        # More than enough vertical space, width is fixed
                        yPos += math.ceil((oneLineHeight - pixmapSide) / 2)
                    else:
                        # Not enough vertical space, width is fixed
                        xPos += math.ceil((pixmapSide - oneLineHeight) / 2)
                        pixmapSide = oneLineHeight
                    painter.drawPixmap(xPos, yPos,
                                       pixmapSide, pixmapSide, pixmap)
            top += height

    def mouseMoveEvent(self, event):
        """Tooltips for the marks"""
        if not self.__noTooltip:
            blockNumber = self._qpart.cursorForPosition(
                event.pos()).blockNumber()
            lineno = blockNumber + 1
            msg = None

            if lineno == self.excptionLine:
                msg = 'Exception line'
            elif lineno == self.currentDebugLine:
                msg = 'Current debugger line'
            elif lineno in self.__ccMessages:
                msg = self.__ccMessages[lineno][0]
            elif lineno in self.__messages:
                msg = ''
                for part in self.__messages[lineno]:
                    if msg:
                        msg += '<br/>'
                    msg += escape(part)
                msg = "<p style='white-space:pre'>" + msg + "</p>"

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

    def __onFileTypeChanged(self, _, uuid, newFileType):
        """Triggered on the changed file type"""
        if uuid == self.myUUID:
            MarginBase.setVisible(self, isPythonMime(newFileType))

    def __onBlockCountChanged(self):
        """Triggered when the block count changed"""
        self.__noTooltip = True
        self.update()

    def clearAnalysisMessages(self):
        """Clears all the messages"""
        self.__messages = {}
        self.__ccMessages = {}
        self.clear()

    def clearDebugMarks(self):
        """Clears all debug marks"""
        self.excptionLine = None
        self.currentDebugLine = None
        self.clear()
        self.update()

    def setCurrentDebugLine(self, currentDebugLine):
        """Sets the current debug line"""
        self.currentDebugLine = currentDebugLine
        self.excptionLine = None
        self.update()

    def setExceptionLine(self, exceptionLine):
        """Sets the exception line"""
        self.excptionLine = exceptionLine
        self.currentDebugLine = None
        self.update()

    def setAnalysisMessages(self, messages, ccMessages):
        """Sets a new set of messages"""
        self.__messages = dict(messages)

        for lineno in self.__messages:
            if lineno > 0:
                self.setBlockValue(
                    self._qpart.document().findBlockByNumber(lineno - 1), 1)

        self.__ccMessages = {}
        for item in ccMessages:
            if item.lineno not in self.__messages:
                complexity = cc_rank(item.complexity)
                if complexity != 'A':
                    msg = 'Cyclomatic complexity is ' + complexity + \
                          ' (value: ' + str(item.complexity) + ')'
                    self.__ccMessages[item.lineno] = (msg, ord(complexity))
                    self.setBlockValue(
                        self._qpart.document().findBlockByNumber(item.lineno - 1), 1)

        self.__noTooltip = False
        self.update()
