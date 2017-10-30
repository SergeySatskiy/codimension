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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Labels which can change its content to fit the label size"""

from utils.fileutils import compactPath
from .qt import Qt, pyqtSignal, QLabel, QApplication, QFrame


class FitLabel(QLabel):

    """a label that squeezes its contents to fit it's size"""

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)
        self.__text = ''

    def paintEvent(self, event):
        """Called when painting is required"""
        metric = self.fontMetrics()
        if metric.width(self.__text) > self.contentsRect().width():
            QLabel.setText(self,
                           metric.elidedText(self.text(),
                                             Qt.ElideMiddle, self.width()))
        else:
            QLabel.setText(self, self.__text)

        QLabel.paintEvent(self, event)

    def setText(self, txt):
        """Set the text to be shown"""
        self.__text = txt
        QLabel.setText(self, txt)


class FitPathLabel(QLabel):

    """a label showing a file path compacted to fit it's size"""

    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)
        self.__path = ''

    def setPath(self, path):
        """Set the path to be shown"""
        self.__path = path
        QLabel.setText(self, path)

    def getPath(self):
        """Provides the stored path"""
        return self.__path

    def paintEvent(self, event):
        """Called when painting is required"""
        sparePixels = 5
        metric = self.fontMetrics()
        requiredWidth = metric.width(self.__path)
        if requiredWidth > self.contentsRect().width() - sparePixels:
            compacted = compactPath(self.__path,
                                    self.contentsRect().width() - sparePixels,
                                    self.length)
            QLabel.setText(self, compacted)
        else:
            QLabel.setText(self, self.__path)
        QLabel.paintEvent(self, event)

    def length(self, txt):
        """Length of a text in pixels"""
        return self.fontMetrics().width(txt)

    def mouseDoubleClickEvent(self, event):
        """Generates the doubleClicked signal"""
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        QLabel.mouseDoubleClickEvent(self, event)


class FramedLabelWithDoubleClick(QLabel):

    """A label with a frame and double click for copy content to clipboard"""

    def __init__(self, text=None, callback=None, parent=None):
        QLabel.__init__(self, parent)
        self.setFrameStyle(QFrame.StyledPanel)
        if text is not None:
            self.setText(text)
        self.__callback = callback

    def mouseDoubleClickEvent(self, event):
        """Handles the mouse double click"""
        if event.button() == Qt.LeftButton:
            if self.__callback is None:
                txt = self.text().strip()
                if txt:
                    QApplication.clipboard().setText(txt)
            else:
                self.__callback()
        QLabel.mouseDoubleClickEvent(self, event)
