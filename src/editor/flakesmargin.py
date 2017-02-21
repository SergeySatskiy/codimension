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

from ui.qt import QWidget, QPainter, Qt, QFont
from qutepart.margins import MarginBase
from utils.misc import extendInstance
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import isPythonMime


class CDMFlakesMargin(QWidget):

    """Pyflakes area widget"""

    RESERVED_BITS = 6

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        extendInstance(self, MarginBase)
        MarginBase.__init__(self, parent, "cdm_flakes_margin",
                            self.RESERVED_BITS)

        self.__maxMarks = 2 ** self.RESERVED_BITS - 1
        self.__messages = {}
        self.__bgColor = GlobalData().skin['flakesMarginPaper']

        self.myUUID = None
        if hasattr(self._qpart._parent, 'getUUID'):
            self.myUUID = self._qpart._parent.getUUID()

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)

    def paintEvent(self, event):
        """Paints the margin"""
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.__bgColor)

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
        lineNumbers = list(self.__messages.keys())
        lineNumbers.sort()

        while lineNumbers:
            if lineNumbers[0] == -1:
                lineNumbers.pop()
            else:
                break

        current = 1
        for lineno in lineNumbers:
            if lineno > 0:
                self.setBlockValue(
                    self._qpart.document().findBlockByNumber(lineno - 1),
                    current)
                current += 1
                if current > self.__maxMarks:
                    break
        if current > 1:
            self.update()
