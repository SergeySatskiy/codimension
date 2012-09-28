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

from PyQt4.QtCore       import Qt, QEvent
from PyQt4.QtGui        import QApplication
from utils.pixmapcache  import PixmapCache
from utils.globals      import GlobalData


class CodimensionApplication( QApplication ):
    """ codimension application class """

    def __init__( self, argv ):
        QApplication.__init__( self, argv )
        QApplication.setStyle( 'plastique' )

        self.mainWindow = None
        self.__lastFocus = None

        QApplication.setWindowIcon( PixmapCache().getIcon( 'icon.png' ) )

        # Avoid having rectabgular frames on the status bar
        appCSS = GlobalData().skin.appCSS
        if appCSS != "":
            self.setStyleSheet( appCSS )

        self.installEventFilter( self )
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
                if self.__lastFocus is not None:
                    self.__lastFocus.setFocus()
                    self.__lastFocus = None
                if self.mainWindow is not None:
                    self.mainWindow.checkOutsideFileChanges()
            elif eventType == QEvent.ApplicationDeactivate:
                self.__lastFocus = QApplication.focusWidget()
        except:
            pass

        try:
            return QApplication.eventFilter( self, obj, event )
        except:
            return True

