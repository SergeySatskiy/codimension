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

" Control flow UI widget "

from PyQt4.QtCore import Qt, QSize, QTimer, SIGNAL
from PyQt4.QtGui import ( QToolBar, QWidget, QGraphicsView, QPainter,
                          QApplication, QGraphicsScene, QHBoxLayout,
                          QLabel, QTransform )
from cdmcf import getControlFlowFromMemory
from flowui.vcanvas import VirtualCanvas
from flowui.cflowsettings import getDefaultCflowSettings
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.fileutils import Python3FileType, PythonFileType
from utils.settings import Settings


IDLE_TIMEOUT = 1500


class CFGraphicsView( QGraphicsView ):
    """ Central widget """

    def __init__( self, parent = None ):
        super( CFGraphicsView, self ).__init__( parent )

        self.__currentFactor = 1.0
        self.setRenderHint( QPainter.Antialiasing )
        self.setRenderHint( QPainter.TextAntialiasing )
        Settings().flowScaleChanged.connect( self.__scaleChanged )
        return

    def wheelEvent( self, event ):
        """ Mouse wheel event """
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = 1.41 ** ( -event.delta() / 240.0 )
            self.__currentFactor *= factor
            self.setTransform( QTransform.fromScale( self.__currentFactor,
                                                     self.__currentFactor ) )
            Settings().flowScale = self.__currentFactor
        else:
            QGraphicsView.wheelEvent( self, event )
        return

    def zoomTo( self, scale ):
        " Zooms to the specific factor "
        self.__currentFactor = scale
        self.setTransform( QTransform.fromScale( self.__currentFactor,
                                                 self.__currentFactor ) )
        return

    def __scaleChanged( self ):
        " When another window made a change "
        newScale = Settings().flowScale
        if newScale != self.__currentFactor:
            self.zoomTo( newScale )
        return



class FlowUIWidget( QWidget ):
    " The widget which goes along with the text editor "

    STATE_OK_UTD = 0        # Parsed OK, control flow up to date
    STATE_OK_CHN = 1        # Parsed OK, control flow changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, control flow up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, control flow changed
    STATE_UNKNOWN = 4

    def __init__( self, editor, parent ):
        QWidget.__init__( self, parent )

        # It is always not visible at the beginning because there is no
        # editor content at the start
        self.setVisible( False )

        self.__editor = editor
        self.__parentWidget = parent
        self.__currentIconState = self.STATE_UNKNOWN
        self.__connected = False

        self.cflowSettings = getDefaultCflowSettings( self )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )

        # Make pylint happy
        self.__toolbar = None
        self.__infoIcon = None
        self.__cf = None

        # Create the update timer
        self.__updateTimer = QTimer( self )
        self.__updateTimer.setSingleShot( True )
        self.__updateTimer.timeout.connect( self.process )

        hLayout.addWidget( self.__createGraphicsView() )
        hLayout.addWidget( self.__createToolbar() )
        self.setLayout( hLayout )

        # Connect to the change file type signal
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        self.connect( editorsManager, SIGNAL( 'fileTypeChanged' ),
                      self.__onFileTypeChanged )
        return

    def __createToolbar( self ):
        " Creates the toolbar "
        self.__toolbar = QToolBar( self )
        self.__toolbar.setOrientation( Qt.Vertical )
        self.__toolbar.setMovable( False )
        self.__toolbar.setAllowedAreas( Qt.RightToolBarArea )
        self.__toolbar.setIconSize( QSize( 16, 16 ) )
        self.__toolbar.setFixedWidth( 28 )
        self.__toolbar.setContentsMargins( 0, 0, 0, 0 )

        self.__infoIcon = QLabel()
        self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'cfunknown.png' ) )
        self.__toolbar.addWidget( self.__infoIcon )
        return self.__toolbar

    def __createGraphicsView( self ):
        """ Creates the graphics view """
        self.scene = QGraphicsScene( self )
        self.view = CFGraphicsView( self )
        self.view.setScene( self.scene )
        self.view.zoomTo( Settings().flowScale )
        return self.view

    def __updateInfoIcon( self, state ):
        " Updates the information icon "
        if state == self.__currentIconState:
            return

        if state == self.STATE_OK_UTD:
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'cfokutd.png' ) )
            self.__infoIcon.setToolTip( "Control flow is up to date" )
            self.__currentIconState = self.STATE_OK_UTD
        elif state == self.STATE_OK_CHN:
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'cfokchn.png' ) )
            self.__infoIcon.setToolTip( "Control flow is not up to date; will be updated on idle" )
            self.__currentIconState = self.STATE_OK_CHN
        elif state == self.STATE_BROKEN_UTD:
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'cfbrokenutd.png' ) )
            self.__infoIcon.setToolTip( "Control flow might be invalid due to invalid python code" )
            self.__currentIconState = self.STATE_BROKEN_UTD
        else:
            # STATE_BROKEN_CHN
            self.__infoIcon.setPixmap( PixmapCache().getPixmap( 'cfbrokenchn.png' ) )
            self.__infoIcon.setToolTip( "Control flow might be invalid; will be updated on idle" )
            self.__currentIconState = self.STATE_BROKEN_CHN
        return

    def process( self ):
        """ Parses the content and displays the results """

        if not self.__connected:
            self.__connectEditorSignals()

        content = self.__editor.text()
        self.__cf = getControlFlowFromMemory( content )
        if len( self.__cf.errors ) != 0:
            self.__updateInfoIcon( self.STATE_BROKEN_UTD )
            return

        self.__updateInfoIcon( self.STATE_OK_UTD )

#        if len( self.__cf.warnings ) != 0:
#            self.logMessage( "Parser warnings: " )
#            for warn in self.__cf.warnings:
#                print str( warn[0] ) + ": " + warn[1]

        self.scene.clear()
        try:
            # Top level canvas has no adress and no parent canvas
            canvas = VirtualCanvas( self.cflowSettings, None, None, None )
            canvas.layout( self.__cf )
            width, height = canvas.render()
            self.scene.setSceneRect( 0, 0, width, height )
            canvas.draw( self.scene, 0, 0 )
        except Exception, exc:
            print "Exception:\n" + str( exc )
        return

    def __onFileTypeChanged( self, fileName, uuid, newFileType ):
        " Triggered when a buffer content type has changed "

        if self.__parentWidget.getUUID() != uuid:
            return

        if newFileType not in [ Python3FileType, PythonFileType ]:
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__cf = None
            self.setVisible( False )
            self.__currentIconState = self.STATE_UNKNOWN
            return

        # Update the bar and show it
        self.setVisible( True )
        self.process()
        return

    def __connectEditorSignals( self ):
        " When it is a python file - connect to the editor signals "
        if not self.__connected:
            self.__editor.SCEN_CHANGE.connect( self.__onBufferChanged )
            self.__connected = True
        return

    def __disconnectEditorSignals( self ):
        " Disconnect the editor signals when the file is not a python one "
        if self.__connected:
            self.__editor.SCEN_CHANGE.disconnect( self.__onBufferChanged )
            self.__connected = False
        return

    def __onBufferChanged( self ):
        " Triggered to update status icon and to restart the timer "
        self.__updateTimer.stop()
        if len( self.__cf.errors ) == 0:
            self.__updateInfoIcon( self.STATE_OK_CHN )
        else:
            self.__updateInfoIcon( self.STATE_BROKEN_CHN )
        self.__updateTimer.start( IDLE_TIMEOUT )
        return


