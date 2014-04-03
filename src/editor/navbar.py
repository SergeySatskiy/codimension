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


from PyQt4.QtCore import SIGNAL, QTimer, Qt
from PyQt4.QtGui import QFrame, QHBoxLayout, QLabel, QWidget, QSizePolicy
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import Python3FileType, PythonFileType
from utils.pixmapcache import PixmapCache
from cdmbriefparser import getBriefModuleInfoFromMemory
from autocomplete.bufferutils import getContext


IDLE_TIMEOUT = 1500


class NavigationBar( QFrame ):
    " Navigation bar at the top of the editor (python only) "

    STATE_OK_UTD = 0        # Parsed OK, context up to date
    STATE_OK_CHN = 1        # Parsed OK, context changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, context up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, context changed
    STATE_UNKNOWN = 4

    def __init__( self, editor, parent ):
        QFrame.__init__( self, parent )
        self.__editor = editor

        # It is always not visible at the beginning because there is no
        # editor content at the start
        self.setVisible( False )

        # There is no parser info used to display values
        self.__currentInfo = None
        self.__currentIconState = self.STATE_UNKNOWN
        self.__connected = False

        self.__createLayout()

        # Create the update timer
        self.__updateTimer = QTimer( self )
        self.__updateTimer.setSingleShot( True )
        self.connect( self.__updateTimer, SIGNAL( 'timeout()' ),
                      self.updateBar )

        # Connect to the change file type signal
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        self.connect( editorsManager, SIGNAL( 'fileTypeChanged' ),
                      self.__onFileTypeChanged )
        return

    def __connectEditorSignals( self ):
        " When it is a python file - connect to the editor signals "
        if self.__connected:
            return

        self.connect( self.__editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__cursorPositionChanged )
        self.connect( self.__editor, SIGNAL( 'SCEN_CHANGE()' ),
                      self.__onBufferChanged )
        self.__connected = True
        return

    def __disconnectEditorSignals( self ):
        " Disconnect the editor signals when the file is not a python one "
        if not self.__connected:
            return

        self.disconnect( self.__editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                         self.__cursorPositionChanged )
        self.disconnect( self.__editor, SIGNAL( 'SCEN_CHANGE()' ),
                         self.__onBufferChanged )
        self.__connected = False
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

        self.__contextLabel = QLabel()
        self.__contextLabel.setAlignment( Qt.AlignLeft )
        self.__layout.addWidget( self.__contextLabel )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.__layout.addWidget( spacer )
        return

    def __updateInfoIcon( self, state ):
        " Updates the information icon "
        if state == self.__currentIconState:
            return

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
        " Editor has resized "
        QFrame.resizeEvent( self, event )
        return

    def __onFileTypeChanged( self, fileName, uuid, newFileType ):
        " Triggered when a buffer content type has changed "

        if self.parent().getUUID() != uuid:
            return

        if newFileType not in [ Python3FileType, PythonFileType ] or \
           not Settings().showNavigationBar:
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__currentInfo = None
            self.setVisible( False )
            self.__currentIconState = self.STATE_UNKNOWN
            return

        # Update the bar and show it
        self.setVisible( True )
        self.updateBar()
        return

    def updateSettings( self ):
        " Called when navigation bar settings have been updated "
        if not Settings().showNavigationBar:
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__currentInfo = None
            self.setVisible( False )
        return

    def updateBar( self ):
        " Triggered when the timer is fired "
        self.__updateTimer.stop()  # just in case

        if self.parent().getFileType() not in [ Python3FileType,
                                                PythonFileType ]:
            return

        if not self.__connected:
            self.__connectEditorSignals()

        # Parse the buffer content
        self.__currentInfo = getBriefModuleInfoFromMemory(
                                                str( self.__editor.text() ) )

        # Decide what icon to use
        if self.__currentInfo.isOK:
            self.__updateInfoIcon( self.STATE_OK_UTD )
        else:
            self.__updateInfoIcon( self.STATE_BROKEN_UTD )

        # Calc the cursor context
        context = getContext( self.__editor, self.__currentInfo, True, False )

        # Display the context
        self.__contextLabel.setText( str( context ) )
        return

    def __cursorPositionChanged( self, line, pos ):
        " Cursor position changed "
        self.__onNeedUpdate()
        return

    def __onBufferChanged( self ):
        " Buffer changed "
        self.__onNeedUpdate()
        return

    def __onNeedUpdate( self ):
        self.__updateTimer.stop()
        if self.__currentInfo.isOK:
            self.__updateInfoIcon( self.STATE_OK_CHN )
        else:
            self.__updateInfoIcon( self.STATE_BROKEN_CHN )
        self.__updateTimer.start( IDLE_TIMEOUT )
        return
