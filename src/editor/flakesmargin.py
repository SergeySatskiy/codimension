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


"""Pyflakes margin"""

import qutepart
from cgi import escape
from ui.qt import QWidget, QPainter, Qt, QFont, QToolTip
from qutepart.margins import MarginBase
from utils.misc import extendInstance
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import isPythonMime
from utils.pixmapcache import getPixmap


class CDMFlakesMargin(QWidget):

    """Pyflakes area widget"""

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        extendInstance(self, MarginBase)
        MarginBase.__init__(self, parent, "cdm_flakes_margin", 1)
        self.setMouseTracking(True)

        self.__messages = {}
        self.__bgColor = GlobalData().skin['flakesMarginPaper']
        self.__mark = getPixmap('pyflakesmsgmarker.png')

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

        block = self._qpart.firstVisibleBlock()
        blockBoundingGeometry = self._qpart.blockBoundingGeometry(block).translated(self._qpart.contentOffset())
        top = blockBoundingGeometry.top()
        bottom = top + blockBoundingGeometry.height()

        for block in qutepart.iterateBlocksFrom(block):
            height = self._qpart.blockBoundingGeometry(block).height()
            if top > event.rect().bottom():
                break
            if block.isVisible() and bottom >= event.rect().top():
                if self.isBlockMarked(block):
                    yPos = top + ((height - self.__mark.height()) / 2)  # centered
                    painter.drawPixmap(0, yPos, self.__mark)

            top += height

    def mouseMoveEvent(self, event):
        """Tooltips for the marks"""
        blockNumber = self._qpart.cursorForPosition(event.pos()).blockNumber()
        lineno = blockNumber + 1
        if lineno in self.__messages:
            msg = ''
            for part in self.__messages[lineno]:
                if msg:
                    msg += '<br/>'
                msg += escape(part)
            msg = "<p style='white-space:pre'>" + msg + "</p>"
            QToolTip.showText(event.globalPos(), msg)
        else:
            QToolTip.hideText()
        return QWidget.mouseMoveEvent(self, event)

    def width(self):
        """Desired width"""
        return 16

    def setBackgroundColor(self, color):
        """Sets the new background color"""
        if self.__bgColor != color:
            self.__bgColor = color
            self.update()

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered on the changed file type"""
        if uuid == self.myUUID:
            if isPythonMime(newFileType):
                self.setVisible(True)
            else:
                self.setVisible(False)

    def clearPyflakesMessages(self):
        """Clears all the messages"""
        self.__messages = {}
        self.clear()

    def setPyflakesMessages(self, messages):
        """Sets a new set of messages"""
        self.__messages = dict(messages)

        for lineno in self.__messages.keys():
            if lineno > 0:
                self.setBlockValue(
                    self._qpart.document().findBlockByNumber(lineno - 1), 1)
        self.update()
