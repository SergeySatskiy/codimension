# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""Line edit which shows specific text when inactive"""


from .qt import Qt, QLineEdit, QStyleOptionFrame, QStyle, QPainter, QPalette


class InactiveLineEdit(QLineEdit):

    """Line edit widget showing some inactive text"""

    def __init__(self, parent=None, inactiveText=""):
        QLineEdit.__init__(self, parent)
        self.__inactiveText = inactiveText

    def inactiveText(self):
        """Provides the inactive text"""
        return self.__inactiveText

    def setInactiveText(self, inactiveText):
        """Sets the inactive text"""
        self.__inactiveText = inactiveText
        self.update()

    def paintEvent(self, evt):
        """Paint event handler"""
        QLineEdit.paintEvent(self, evt)
        if self.text() == "" and self.__inactiveText != "" and \
           not self.hasFocus():
            panel = QStyleOptionFrame()
            self.initStyleOption(panel)
            textRect = self.style().subElementRect(QStyle.SE_LineEditContents,
                                                   panel, self)
            textRect.adjust(2, 0, 0, 0)
            painter = QPainter(self)
            painter.setPen(self.palette().brush(QPalette.Disabled,
                                                QPalette.Text).color())
            painter.drawText(textRect, Qt.AlignLeft | Qt.AlignVCenter,
                             self.__inactiveText)
