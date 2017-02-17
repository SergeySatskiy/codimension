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


class CDMFlakesMargin(QWidget):

    """Pyflakes area widget"""

    RESERVED_BITS = 6

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        extendInstance(self, MarginBase)
        MarginBase.__init__(self, parent, "cdm_flakes_margin",
                            self.RESERVED_BITS)
        self.__maxMarks = 2 ** self.RESERVED_BITS - 1

        self.__bgColor = GlobalData().skin['flakesMarginPaper']

    def paintEvent(self, event):
        """Paints the margin"""
        if self.__firstTime:
            self.__updateWidth()
            self.__firstTime = False

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
