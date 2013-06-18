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

from PyQt4.QtCore       import Qt, QEvent, QTimer, SIGNAL
from PyQt4.QtGui        import QApplication
from utils.pixmapcache  import PixmapCache
from utils.globals      import GlobalData


class CodimensionApplication( QApplication ):
    """ codimension application class """

    def __init__( self, argv, style ):
        QApplication.setStyle( style )
        QApplication.__init__( self, argv )

        self.mainWindow = None
        self.__lastFocus = None

        # Sick! It seems that QT sends Activate/Deactivate signals every time
        # a dialog window is opened/closed. This happens very quickly (and
        # totally unexpected!). The last focus window must not be memorized
        # for these cases. The timer before helps to handle this wierd
        # behavior. Without the timer clicking 'Cancel' in a dialog box leads
        # to a core dump.
        self.__deactivateTimer = QTimer( self )
        self.__deactivateTimer.setSingleShot( True )
        self.connect( self.__deactivateTimer, SIGNAL( 'timeout()' ),
                                              self.__onDeactivate )

        QApplication.setWindowIcon( PixmapCache().getIcon( 'icon.png' ) )

        # Avoid having rectabgular frames on the status bar
        appCSS = GlobalData().skin.appCSS
        if appCSS != "":
            self.setStyleSheet( appCSS )

        self.installEventFilter( self )
        return

    def __onDeactivate( self ):
        " Triggered when timer fires "
        if self.__deactivateTimer.isActive():
            self.__deactivateTimer.stop()
        self.__lastFocus = QApplication.focusWidget()
        return

    def setMainWindow( self, window ):
        " Memorizes the new window reference "
        self.mainWindow = window
        return

    def eventFilter( self, obj, event ):
        " Event filter to catch ESC application wide "
        try:
            eventType = event.type()
            if eventType == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    if self.mainWindow is not None:
                        self.mainWindow.hideTooltips()
            elif eventType == QEvent.ApplicationActivate:
                if self.__deactivateTimer.isActive():
                    self.__deactivateTimer.stop()
                if self.__lastFocus is not None:
                    self.__lastFocus.setFocus()
                    self.__lastFocus = None
                if self.mainWindow is not None:
                    self.mainWindow.checkOutsideFileChanges()
            elif eventType == QEvent.ApplicationDeactivate:
                if self.__deactivateTimer.isActive():
                    self.__deactivateTimer.stop()
                self.__deactivateTimer.start( 25 )
        except:
            pass

        try:
            return QApplication.eventFilter( self, obj, event )
        except:
            return True
