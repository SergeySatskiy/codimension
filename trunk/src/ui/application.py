#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#


""" definition of the codimension QT based application class """

from PyQt4.QtCore       import Qt, QEvent, SIGNAL
from PyQt4.QtGui        import QApplication, QMenuBar
from utils.pixmapcache  import PixmapCache
from utils.globals      import GlobalData
from garbagecollector   import GarbageCollector


class CodimensionApplication( QApplication ):
    """ codimension application class """

    def __init__( self, argv, style ):
        QApplication.__init__( self, argv )

        # Sick! The QT doc recommends the following:
        # "To ensure that the application's style is set correctly, it is best
        # to call this function before the QApplication constructor, if
        # possible". However if I do it before QApplication.__init__() then
        # there is a crash! At least with some styles on Ubuntu 12.04 64 bit.
        # So I have to call the initialization after the __init__ call.
        QApplication.setStyle( style )

        self.mainWindow = None
        self.__lastFocus = None
        self.__beforeMenuBar = None

        # Sick! It seems that QT sends Activate/Deactivate signals every time
        # a dialog window is opened/closed. This happens very quickly (and
        # totally unexpected!). So the last focus widget must not be focused
        # unconditionally as the last focus may come from a dialog which has
        # already been destroyed. Without checking that a widget is still alive
        # (e.g. clicking 'Cancel' in a dialog box) leads to a core dump.

        QApplication.setWindowIcon( PixmapCache().getIcon( 'icon.png' ) )

        self.connect( self, SIGNAL( "focusChanged(QWidget*, QWidget*)" ),
                      self.__onFocusChanged )

        # Avoid having rectabgular frames on the status bar
        appCSS = GlobalData().skin.appCSS
        if appCSS != "":
            self.setStyleSheet( appCSS )


        self.__gc = GarbageCollector( self, True )

        self.installEventFilter( self )
        return

    def setMainWindow( self, window ):
        " Memorizes the new window reference "
        self.mainWindow = window
        return

    def isWidgetAlive( self, widget ):
        for item in QApplication.allWidgets():
            if item == widget:
                return True
        return False

    def eventFilter( self, obj, event ):
        " Event filter to catch ESC application wide "
        try:
            eventType = event.type()
            if eventType == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    if self.mainWindow is not None:
                        self.mainWindow.hideTooltips()
            elif eventType == QEvent.ApplicationActivate:
                if self.isWidgetAlive( self.__lastFocus ):
                    if isinstance( self.__lastFocus, QMenuBar ):
                        if self.isWidgetAlive( self.__beforeMenuBar ):
                            self.__beforeMenuBar.setFocus()
                self.__lastFocus = None
                if self.mainWindow is not None:
                    self.mainWindow.checkOutsideFileChanges()
            elif eventType == QEvent.ApplicationDeactivate:
                if QApplication.activeModalWidget() is not None:
                    self.__lastFocus = None
                else:
                    self.__lastFocus = QApplication.focusWidget()
        except:
            pass

        try:
            return QApplication.eventFilter( self, obj, event )
        except:
            return True

    def __onFocusChanged( self, fromWidget, toWidget ):
        " Triggered when a focus is passed from one widget to another "
        if isinstance( toWidget, QMenuBar ):
            self.__beforeMenuBar = fromWidget
        return

