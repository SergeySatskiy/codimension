#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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
# $Id
#

" Navigation bar implementation "


from PyQt4.QtCore import SIGNAL, QTimer
from PyQt4.QtGui import QFrame, QHBoxLayout
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import TexFileType
from utils.pixmapcache import PixmapCache


IDLE_TIMEOUT = 1500


class NavigationBar( QFrame ):
    " Navigation bar at the top of the editor (python only) "

    def __init__( self, editor, parent = None ):
        QFrame.__init__( self, parent )
        self.setFixedHeight( 16 )
        self.__layout = QHBoxLayout( self )

        if not Settings().showNavigationBar:
            self.setVisible( False )

        # Setup the background color


        self.__bufferBrokenPixmap = PixmapCache().getIcon( '' )
        self.__bufferParsedOK = PixmapCache().getIcon( '' )
        self.__positionChanged = PixmapCache().getIcon( '' )

        self.__editor = editor
        self.connect( editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__cursorPositionChanged )

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        self.connect( editorsManager, SIGNAL( 'fileTypeChanged' ),
                      self.__onFileTypeChanged )

        self.__updateTimer = QTimer( self )
        self.__updateTimer.setSingleShot( True )
        self.connect( self.__updateTimer, SIGNAL( 'timeout()' ),
                                          self.__updateBar )

        self.connect( self.__editor, SIGNAL( 'SCEN_CHANGE()' ),
                      self.__onBufferChanged )
        return

    def __setPositionChangedIcon( self ):
        " Sets the position changed icon "
        return

    def __setBufferParsedOKIcon( self ):
        " Sets the icon that the buffer parsed OK and the info is up to date "
        return

    def __setBufferBrokenIcon( self ):
        " Sets the buffer broken icon "
        return

    def resizeEvent( self, event ):
        # Do not forget call the base class resize
        QFrame.resizeEvent( self, event )
        return

    def __onFileTypeChanged( self, fileName, uuid, newFileType ):
        # Each tab widget is issued a UUID upon creation. You can get yours as
        # follows:
        # self.parent().getUUID() if parent was passed as the tab widget when
        # the bar is created

        # file types are here: src/utils/fileutils.py

        return

    def __updateBar( self ):
        " Triggered when the timer is fired "
        self.__updateTimer.stop()  # just in case
        return

    def __cursorPositionChanged( self, line, pos ):
        self.__updateTimer.stop()
        # Update the bar icon, telling that its info is invalid
        self.__updateTimer.start( IDLE_TIMEOUT )

    def __onBufferChanged( self ):
        self.__updateTimer.stop()
        # Update the bar icon, telling that its info is invalid
        self.__updateTimer.start( IDLE_TIMEOUT )
        return

You would also need to deal with a setting to enable/disable the bar. The setting goes to src/utils/settings.py All you need to do is to create a new record in the CDM_SETTINGS dictionary and then the option will be available for you via the settings singleton as follows: Settings().yourOptionName. The saving/loading will be done for you.

One more thing is skinning. It's a good idea to have colors skinnable.
Similarly to the settings you need to add a record to the SKIN_SETTINGS list in src/utils/skin.py
Then Settings().skin.yourName can be used.


