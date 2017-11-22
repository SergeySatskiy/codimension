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

"""definition of the codimension QT based application class"""

from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from .garbagecollector import GarbageCollector
from .qt import Qt, QEvent, QApplication, QMenuBar


KEY_PRESS = QEvent.KeyPress
APP_ACTIVATE = QEvent.ApplicationActivate
APP_DEACTIVATE = QEvent.ApplicationDeactivate


class CodimensionApplication(QApplication):

    """Codimension application class"""

    def __init__(self, argv, style):
        QApplication.__init__(self, argv)

        # Sick! The QT doc recommends the following:
        # "To ensure that the application's style is set correctly, it is best
        # to call this function before the QApplication constructor, if
        # possible". However if I do it before QApplication.__init__() then
        # there is a crash! At least with some styles on Ubuntu 12.04 64 bit.
        # So I have to call the initialization after the __init__ call.
        QApplication.setStyle(style)

        self.mainWindow = None
        self.__lastFocus = None
        self.__beforeMenuBar = None

        # Sick! It seems that QT sends Activate/Deactivate signals every time
        # a dialog window is opened/closed. This happens very quickly (and
        # totally unexpected!). So the last focus widget must not be focused
        # unconditionally as the last focus may come from a dialog which has
        # already been destroyed. Without checking that a widget is still alive
        # (e.g. clicking 'Cancel' in a dialog box) leads to a core dump.

        QApplication.setWindowIcon(getIcon('icon.png'))

        self.focusChanged.connect(self.__onFocusChanged)

        # Avoid having rectangular frames on the status bar and
        # some application wide style changes
        appCSS = GlobalData().skin['appCSS']
        if appCSS:
            self.setStyleSheet(appCSS)

        # Install custom GC
        self.__gc = GarbageCollector(self)

        self.installEventFilter(self)

    def setMainWindow(self, window):
        """Memorizes the new window reference"""
        self.mainWindow = window

    @staticmethod
    def __areWidgetsAlive(widget1, widget2):
        """True, True if QT still has the widgets"""
        first = False
        second = False
        for item in QApplication.allWidgets():
            if not first and item == widget1:
                first = True
                if second:
                    return first, second
            if not second and item == widget2:
                second = True
                if first:
                    return first, second
        return first, second

    def eventFilter(self, obj, event):
        """Event filter to catch ESC application wide.

        Pass focus explicitly on broken window managers when the app is
        activated; Catch Ctrl+1 and Ctrl+2 application wide;
        """
        del obj     # unused argument
        try:
            eventType = event.type()
            if eventType == KEY_PRESS:
                key = event.key()
                modifiers = int(event.modifiers())
                if key == Qt.Key_Escape:
                    if self.mainWindow:
                        self.mainWindow.hideTooltips()
                if modifiers == int(Qt.ControlModifier):
                    if key == Qt.Key_1:
                        if self.mainWindow:
                            return self.mainWindow.passFocusToEditor()
                    elif key == Qt.Key_2:
                        if self.mainWindow:
                            return self.mainWindow.passFocusToFlow()
            elif eventType == APP_ACTIVATE:
                lastFocus, \
                beforeMenuBar = self.__areWidgetsAlive(self.__lastFocus,
                                                       self.__beforeMenuBar)
                if lastFocus:
                    if isinstance(self.__lastFocus, QMenuBar):
                        if beforeMenuBar:
                            self.__beforeMenuBar.setFocus()
                self.__lastFocus = None
                if self.mainWindow:
                    self.mainWindow.checkOutsideFileChanges()
            elif eventType == APP_DEACTIVATE:
                if QApplication.activeModalWidget() is not None:
                    self.__lastFocus = None
                else:
                    self.__lastFocus = QApplication.focusWidget()
        except:
            pass
        return False

    def __onFocusChanged(self, fromWidget, toWidget):
        """Triggered when a focus is passed from one widget to another"""
        if isinstance(toWidget, QMenuBar):
            self.__beforeMenuBar = fromWidget
