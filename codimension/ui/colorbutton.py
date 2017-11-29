# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Color button"""

from .qt import pyqtSignal, QPushButton, QColorDialog


class ColorButton(QPushButton):

    """A button which uses the selected color as its background"""

    sigColorChanged = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QPushButton.__init__(self, *args, **kwargs)

        self.__color = None
        self.pressed.connect(self.onColorPicker)

    def setColor(self, color):
        """Sets the button color"""
        if color != self.__color:
            self.__color = color
            if self.__color:
                self.setStyleSheet('background-color: ' + self.__color.name())
            else:
                self.setStyleSheet('')
            self.sigColorChanged.emit()

    def color(self):
        """Provides the current color"""
        return self.__color

    def onColorPicker(self):
        """Brings up the standard color picking dialog"""
        dlg = QColorDialog(self.parent())
        dlg.setOptions(QColorDialog.DontUseNativeDialog)
        if self.__color:
            dlg.setCurrentColor(self.__color)

        if dlg.exec_():
            self.setColor(dlg.currentColor())
