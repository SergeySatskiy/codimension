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
from PyQt4.QtGui import QFrame, QHBoxLayout, QLabel
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import Python3FileType, PythonFileType
from utils.pixmapcache import PixmapCache


IDLE_TIMEOUT = 1500


class NavigationBar( QFrame ):
    " Navigation bar at the top of the editor (python only) "

    STATE_OK_UTD = 0        # Parsed OK, context up to date
    STATE_OK_CHN = 1        # Parsed OK, context changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, context up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, context changed
    STATE_UNKNOWN = 4

    def __init__( self, editor, parent = None ):
        QFrame.__init__( self, parent )
        self.__editor = editor

        # It is always not visible at the beginning because there is no
        # editor content at the start
        self.setVisible( False )

        # There is no parser info used to display values
        self.__currentInfo = None
        self.__currentIconState = self.STATE_UNKNOWN

        self.__createLayout()

        # Make signal connections and set up the timer
        self.connect( editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__cursorPositionChanged )

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        self.connect( editorsManager, SIGNAL( 'fileTypeChanged' ),
                      self.__onFileTypeChanged )

        self.__updateTimer = QTimer( self )
        self.__updateTimer.setSingleShot( True )
        self.connect( self.__updateTimer, SIGNAL( 'timeout()' ),
                                          self.updateBar )

        self.connect( self.__editor, SIGNAL( 'SCEN_CHANGE()' ),
                      self.__onBufferChanged )
        return

    def __createLayout( self ):
        " Creates the layout "
        self.setFixedHeight( 24 )
        self.__layout = QHBoxLayout( self )
        self.__layout.setMargin( 0 )
        self.__layout.setContentsMargins( 0, 0, 0, 0 )

        # Set the background color

        # Create info icon
        self.__infoIcon = QLabel()
        self.__layout.addWidget( self.__infoIcon )
        return

    def __updateInfoIcon( self, state ):
        " Updates the information icon "
        if state == self.STATE_OK_UTD:
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'nbokutd.png' ) )
            self.__infoIcon.setToolTip( "Context is up to date" )
            self.__currentIconState = self.STATE_OK_UTD
        elif state == self.STATE_OK_CHN:
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'nbokchn.png' ) )
            self.__infoIcon.setToolTip( "Context is not up to date; will be updated on idle" )
            self.__currentIconState = self.STATE_OK_CHN
        elif state == self.STATE_BROKEN_UTD:
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'nbbrokenutd.png' ) )
            self.__infoIcon.setToolTip( "Context might be invalid due to invalid python code" )
            self.__currentIconState = self.STATE_BROKEN_UTD
        else:
            # STATE_BROKEN_CHN
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'nbbrokenchn.png' ) )
            self.__infoIcon.setToolTip( "Context might be invalid; will be updated on idle" )
            self.__currentIconState = self.STATE_BROKEN_CHN
        return

    def resizeEvent( self, event ):
        # Do not forget call the base class resize
        QFrame.resizeEvent( self, event )
        return

    def __onFileTypeChanged( self, fileName, uuid, newFileType ):
        " Triggered when a buffer content type has changed "
        if self.parent().getUUID() != uuid:
            return

        if newFileType not in [ Python3FileType, PythonFileType ]:
            self.__currentInfo = None
            self.setVisible( False )
            return

        if not Settings().showNavigationBar:
            self.__currentInfo = None
            self.setVisible( False )
            return

        # Update the bar and show it
        self.setVisible( True )
        self.updateBar()
        return

    def updateBar( self ):
        " Triggered when the timer is fired "
        self.__updateTimer.stop()  # just in case

        if not self.isVisible():
            return

        # Parse the buffer content

        # Decide what icon to use

        # Calc the cursor context

        # Display the context

        return

    def __cursorPositionChanged( self, line, pos ):
        " Cursor position changed "
        self.__updateTimer.stop()
        # Update the bar icon, telling that its info is invalid
        self.__updateTimer.start( IDLE_TIMEOUT )

    def __onBufferChanged( self ):
        " Buffer changed "
        self.__updateTimer.stop()
        # Update the bar icon, telling that its info is invalid
        self.__updateTimer.start( IDLE_TIMEOUT )
        return

#You would also need to deal with a setting to enable/disable the bar. The setting goes to src/utils/settings.py All you need to do is to create a new record in the CDM_SETTINGS dictionary and then the option will be available for you via the settings singleton as follows: Settings().yourOptionName. The saving/loading will be done for you.
#
#One more thing is skinning. It's a good idea to have colors skinnable.
#Similarly to the settings you need to add a record to the SKIN_SETTINGS list in src/utils/skin.py
#Then Settings().skin.yourName can be used.


