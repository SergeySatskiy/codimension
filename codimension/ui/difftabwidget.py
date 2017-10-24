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

"""Diff viewer tab widget"""

from utils.settings import Settings
from .qt import Qt, QEvent, QApplication
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .htmltabwidget import HTMLTabWidget


class DiffTabWidget(HTMLTabWidget):

    """The widget which displays a RO diff page"""

    def __init__(self, parent=None):
        HTMLTabWidget.__init__(self, parent)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Event filter to catch shortcuts on UBUNTU"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if modifiers == Qt.ControlModifier:
                if key == Qt.Key_Minus:
                    Settings().onZoomOut()
                    return True
                if key == Qt.Key_Equal:
                    Settings().onZoomIn()
                    return True
                if key == Qt.Key_0:
                    Settings().onZoomReset()
                    return True
            if modifiers == Qt.KeypadModifier | Qt.ControlModifier:
                if key == Qt.Key_Minus:
                    Settings().onZoomOut()
                    return True
                if key == Qt.Key_Plus:
                    Settings().onZoomIn()
                    return True
                if key == Qt.Key_0:
                    Settings().onZoomReset()
                    return True
        return HTMLTabWidget.eventFilter(self, obj, event)

    def wheelEvent(self, event):
        """Mouse wheel event"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            angleDelta = event.angleDelta()
            if not angleDelta.isNull():
                if angleDelta.y() > 0:
                    Settings().onZoomIn()
                else:
                    Settings().onZoomOut()
            event.accept()
        else:
            HTMLTabWidget.wheelEvent(self, event)

    def setHTML(self, content):
        """Sets the content from the given string"""
        HTMLTabWidget.setHTML(self, content)
        self.onTextZoomChanged()

    def loadFormFile(self, path):
        """Loads the content from the given file"""
        HTMLTabWidget.loadFormFile(self, path)
        self.zoomTo(Settings().zoom)

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.DiffViewer

    def getLanguage(self):
        """Tells the content language"""
        return "diff"
