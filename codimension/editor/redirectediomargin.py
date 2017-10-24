# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Redirected IO margin"""

from html import escape
from ui.qt import QWidget, QPainter, Qt, QToolTip
from qutepart.margins import MarginBase
from utils.misc import extendInstance
from utils.globals import GlobalData
from utils.colorfont import getZoomedMarginFont
from .redirectedmsg import IOConsoleMsg


class CDMRedirectedIOMargin(QWidget):

    """Redirected IO margin widget"""

    _LEFT_MARGIN = 5
    _RIGHT_MARGIN = 3

    # Prefixes should match the message rendering (when copied to clipboard)
    MSG_TYPE_PROPS = {IOConsoleMsg.IDE_MESSAGE: ['ide ', None],
                      IOConsoleMsg.STDOUT_MESSAGE: ['out ', None],
                      IOConsoleMsg.STDERR_MESSAGE: ['err ', None],
                      IOConsoleMsg.STDIN_MESSAGE: [' in ', None]}

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        # Margin data is:
        # {lineNo: [(text, tooltip, msgType),...], }
        # line number is 1 based, tooltip and fgColor could be None
        self.__data = {}

        extendInstance(self, MarginBase)
        MarginBase.__init__(self, parent, 'cdm_redirected_io_margin', 0)
        self.setMouseTracking(True)

        skin = GlobalData().skin
        self.__bgColor = skin['marginPaper']
        self.__fgColor = skin['marginColor']   # default

        CDMRedirectedIOMargin.MSG_TYPE_PROPS[IOConsoleMsg.IDE_MESSAGE][1] = \
            skin['ioconsoleMarginIDEMsgColor']
        CDMRedirectedIOMargin.MSG_TYPE_PROPS[IOConsoleMsg.STDOUT_MESSAGE][1] = \
            skin['ioconsoleMarginStdoutColor']
        CDMRedirectedIOMargin.MSG_TYPE_PROPS[IOConsoleMsg.STDERR_MESSAGE][1] = \
            skin['ioconsoleMarginStderrColor']
        CDMRedirectedIOMargin.MSG_TYPE_PROPS[IOConsoleMsg.STDIN_MESSAGE][1] = \
            skin['ioconsoleMarginStdinColor']

        self.__width = self.__calculateWidth()
        self.onTextZoomChanged()

        # The width needs to be re-calculated when the margin is drawn the
        # first time. The problem is that if the widget is not on the screen
        # then the font metrics are not calculated properly and thus the width
        # is not shown right. What I observed is an offset up to 2 pixels.
        self.__firstTime = True

    def __updateWidth(self):
        """Updates the margin width"""
        newWidth = self.__calculateWidth()
        if newWidth != self.__width:
            self.__width = newWidth
            self._qpart.updateViewport()

    def paintEvent(self, event):
        """Paints the margin"""
        if self.__firstTime:
            self.__updateWidth()
            self.__firstTime = False

        painter = QPainter(self)
        painter.fillRect(event.rect(), self.__bgColor)

        block = self._qpart.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self._qpart.blockBoundingGeometry(block).
                  translated(self._qpart.contentOffset()).top())
        bottom = top + int(self._qpart.blockBoundingRect(block).height())

        boundingRect = self._qpart.blockBoundingRect(block)
        availableWidth = self.__width - self._RIGHT_MARGIN - self._LEFT_MARGIN

        # The margin font could be smaller than the main area font
        topShift = int((self._qpart.fontMetrics().height() -
                        self.fontMetrics().height()) / 2)
        if topShift < 0:
            topShift = 0

        availableHeight = self._qpart.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                lineno = blockNumber + 1
                props = self.__data.get(lineno, [(None, None, None)])
                text = props[0][0]
                if text:
                    msgType = props[0][2]
                    color = CDMRedirectedIOMargin.MSG_TYPE_PROPS[msgType][1]
                    if color is None:
                        color = self.__fgColor
                    painter.setPen(color)
                    painter.drawText(self._LEFT_MARGIN, top + topShift,
                                     availableWidth,
                                     availableHeight,
                                     Qt.AlignRight, text)
            block = block.next()
            boundingRect = self._qpart.blockBoundingRect(block)
            top = bottom
            bottom = top + int(boundingRect.height())
            blockNumber += 1

    def mouseMoveEvent(self, event):
        """Tooltips for the text"""
        blockNumber = self._qpart.cursorForPosition(
            event.pos()).blockNumber()
        lineno = blockNumber + 1
        if lineno in self.__data:
            props = self.__data.get(lineno, [(None, None, None)])
            tooltipItems = []
            for prop in props:
                if prop[1]:
                    msgType = prop[2]
                    tooltipItems.append(
                        CDMRedirectedIOMargin.MSG_TYPE_PROPS[msgType][0] +
                        prop[1])
            if tooltipItems:
                tooltip = "<p style='white-space:pre'>" + \
                          escape('\n'.join(tooltipItems)) + "</p>"
            QToolTip.showText(event.globalPos(), tooltip)
        else:
            QToolTip.hideText()
        return QWidget.mouseMoveEvent(self, event)

    def __calculateWidth(self):
        """Calculates the margin width"""
        digits = len('88:88:88.888')   # Basically it is a timestamp
        digitsWidth = self.fontMetrics().width('9') * digits
        return self._LEFT_MARGIN + digitsWidth + self._RIGHT_MARGIN

    def width(self):
        """Desired width. Includes text and margins"""
        return self.__width

    def setFont(self, font):
        """Overloaded to adjust the width if needed"""
        QWidget.setFont(self, font)
        self.__updateWidth()

    def setBackgroundColor(self, color):
        """Sets the new background color"""
        if self.__bgColor != color:
            self.__bgColor = color
            self.update()

    def onTextZoomChanged(self):
        """Triggered when a zoom has been changed"""
        self.setFont(getZoomedMarginFont())

    def clear(self):
        """Clears all the data"""
        if self.__data:
            self.__data = {}
            self.update()

    def addData(self, lineno, text, tooltip, msgType):
        """Appends new data; lineno is 1-based"""
        if lineno in self.__data:
            self.__data[lineno].append((text, tooltip, msgType))
        else:
            self.__data[lineno] = [(text, tooltip, msgType)]
            self.update()

    def getLineMessageType(self, lineno):
        """Provides the last line message type"""
        if lineno in self.__data:
            return self.__data[lineno][0][2]
        return None
