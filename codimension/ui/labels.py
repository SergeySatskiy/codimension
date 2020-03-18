# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2020  Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""Varous specialized labels used in the IDE"""

from utils.fileutils import compactPath
from .qt import Qt, QLabel, QApplication, pyqtSignal


class FitLabel(QLabel):

    """a label that squeezes its contents to fit it's size"""

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)
        self.__text = ''
        self.__customTooltip = None

    def paintEvent(self, event):
        """Called when painting is required"""
        metric = self.fontMetrics()
        if metric.width(self.__text) > self.contentsRect().width():
            QLabel.setText(self,
                           metric.elidedText(self.__text,
                                             Qt.ElideMiddle, self.width()))
            if self.__customTooltip is None:
                QLabel.setToolTip(self, self.__text)
        else:
            QLabel.setText(self, self.__text)
            if self.__customTooltip is None:
                QLabel.setToolTip(self, '')

        QLabel.paintEvent(self, event)

    def setText(self, txt):
        """Set the text to be shown"""
        self.__text = txt
        QLabel.setText(self, txt)

    def setToolTip(self, tooltip):
        """Sets the custom tooltip"""
        self.__customTooltip = tooltip
        if tooltip is None:
            tooltip = ''
        QLabel.setToolTip(self, tooltip)


class FramedFitLabel(FitLabel):

    """Subclassing for CSS styling"""

    def __init__(self, parent=None):
        FitLabel.__init__(self, parent)


class HeaderFitLabel(FitLabel):

    """Subclassing for CSS styling"""

    def __init__(self, parent=None):
        FitLabel.__init__(self, parent)


# Default double click handler is to copy the text to the buffer
class DoubleClickLabel(QLabel):

    """A label with double click event support"""

    doubleClicked = pyqtSignal()

    def __init__(self, text=None, callback=None, parent=None):
        QLabel.__init__(self, parent)
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
            elif isinstance(self.__callback, str):
                if self.__callback.lower() == 'signal':
                    self.doubleClicked.emit()
                elif self.__callback.lower() == 'ignore':
                    pass
                else:
                    raise Exception(
                        'Unsupported callback value "' + self.__callback +
                        '". Supported values are: "signal" and "ignore".')
            else:
                self.__callback()
        QLabel.mouseDoubleClickEvent(self, event)


# Supposed to have styled:
# - transparent background
# - border color
# - spacing
# Also implements the default double click copying
class FramedLabel(DoubleClickLabel):

    """A label with a frame and double click for copy content to clipboard"""

    def __init__(self, text=None, callback=None, parent=None):
        DoubleClickLabel.__init__(self, text, callback, parent)


# Supposed to have styled:
# - background color
# - border color
# - spacing
# Also implements the default double click copying
class HeaderLabel(DoubleClickLabel):

    """Subclassed for styling via CSS"""

    def __init__(self, text=None, callback=None, parent=None):
        DoubleClickLabel.__init__(self, text, callback, parent)


class FitPathLabel(DoubleClickLabel):

    """a label showing a file path compacted to fit it's size"""

    def __init__(self, callback=None, parent=None):
        DoubleClickLabel.__init__(self, None, callback, parent)
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
            self.setToolTip(self.__path)
        else:
            QLabel.setText(self, self.__path)
            self.setToolTip('')
        QLabel.paintEvent(self, event)

    def length(self, txt):
        """Length of a text in pixels"""
        return self.fontMetrics().width(txt)



class FramedFitPathLabel(FitPathLabel):

    """a label showing a file path compacted to fit it's size"""

    def __init__(self, callback=None, parent=None):
        FitPathLabel.__init__(self, callback, parent)


class HeaderFitPathLabel(FitPathLabel):

    """a label showing a file path compacted to fit it's size"""

    def __init__(self, callback=None, parent=None):
        FitPathLabel.__init__(self, callback, parent)


# Status bar items

# Supposed to have styled:
# - background color
# - border color
# - spacing
# Also implements the default double click copying
class StatusBarFramedLabel(FramedLabel):

    """Subclassed for styling via CSS"""

    def __init__(self, text=None, callback=None, parent=None):
        FramedLabel.__init__(self, text, callback, parent)



# Supposed to have styled:
# - background: transparent
# - no border
class StatusBarPixmapLabel(DoubleClickLabel):

    """Used for items which display an icon"""

    def __init__(self, callback, parent):
        DoubleClickLabel.__init__(self, None, callback, parent)


# Supposed to have styled:
# - background color
# - border color
# - spacing
class StatusBarPathLabel(FitPathLabel):

    """Subclassed for styling via CSS"""

    def __init__(self, callback, parent):
        FitPathLabel.__init__(self, callback, parent)

