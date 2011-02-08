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

""" Pixmap widget """


import os.path
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from PyQt4.QtGui                import QPalette, QSizePolicy, QScrollArea, \
                                       QImage, QPixmap, QAction, \
                                       QLabel, QToolBar, QWidget, \
                                       QHBoxLayout
from PyQt4.QtCore               import Qt, SIGNAL, QSize
from utils.pixmapcache          import PixmapCache




class PixmapWidget( QScrollArea ):
    " The pixmap widget "

    formatStrings = { QImage.Format_Invalid:                "invalid",
                      QImage.Format_Mono:                   "1-bit per pixel",
                      QImage.Format_MonoLSB:                "1-bit per pixel",
                      QImage.Format_Indexed8:               "8-bit indexes",
                      QImage.Format_RGB32:                  "32-bit RG",
                      QImage.Format_ARGB32:                 "32-bit ARGB",
                      QImage.Format_ARGB32_Premultiplied:   "32-bit ARGB",
                      QImage.Format_RGB16:                  "16-bit RGB",
                      QImage.Format_ARGB8565_Premultiplied: "24-bit ARGB",
                      QImage.Format_RGB666:                 "24-bit RGB",
                      QImage.Format_ARGB6666_Premultiplied: "24-bit ARGB",
                      QImage.Format_RGB555:                 "16-bit RGB",
                      QImage.Format_ARGB8555_Premultiplied: "24-bit ARGB",
                      QImage.Format_RGB888:                 "24-bit RGB",
                      QImage.Format_RGB444:                 "16-bit RGB",
                      QImage.Format_ARGB4444_Premultiplied: "16-bit ARGB" }


    def __init__( self, parent = None ):
        QScrollArea.__init__( self, parent )

        self.pixmapLabel = QLabel()
        self.pixmapLabel.setBackgroundRole( QPalette.Base )
        self.pixmapLabel.setSizePolicy( QSizePolicy.Ignored,
                                        QSizePolicy.Ignored )
        self.pixmapLabel.setScaledContents( True )

        self.zoom = 1.0
        self.info = ""
        self.formatInfo = ""
        self.fileSize = 0

        self.setBackgroundRole( QPalette.Dark )
        self.setWidget( self.pixmapLabel )
        self.setAlignment( Qt.AlignCenter )
        return

    def loadFromFile( self, fileName ):
        " Loads a pixmap from a file "
        image = QImage( fileName )
        if image.isNull():
            raise Exception( "Unsupported pixmap format (" + fileName + ")" )

        self.pixmapLabel.setPixmap( QPixmap.fromImage( image ) )
        self.pixmapLabel.adjustSize()

        self.fileSize = os.path.getsize( fileName )
        if self.fileSize < 1024:
            fileSizeString = str( self.fileSize ) + "bytes"
        else:
            kiloBytes = self.fileSize / 1024
            if (self.fileSize % 1024) >= 512:
                kiloBytes += 1
            fileSizeString = str( kiloBytes ) + "kb"
        self.info = str( image.width() ) + "px/" + \
                    str( image.height() ) + "px/" + fileSizeString
        try:
            self.formatInfo = self.formatStrings[ image.format() ]
        except:
            self.formatInfo = "Unknown"
        return

    def setPixmap( self, pixmap ):
        " Shows the provided pixmap "
        pix = QPixmap.fromImage( pixmap )
        self.pixmapLabel.setPixmap( pix )
        self.pixmapLabel.adjustSize()

        self.info = str( pix.width() ) + "px/" + str( pix.height() ) + "px"
        self.formatInfo = str( pix.depth() ) + " bpp"
        return

    def keyPressEvent( self, event ):
        """ Handles the key press events """

        if event.key() == Qt.Key_Escape:
            self.emit( SIGNAL('ESCPressed') )
            event.accept()
        else:
            QScrollArea.keyPressEvent( self, event )
        return

    def resetZoom( self ):
        " Resets the zoom "
        self.zoom = 1.0
        self.pixmapLabel.adjustSize()
        return

    def doZoom( self, factor ):
        " Performs zooming "

        self.zoom *= factor
        self.pixmapLabel.resize( self.zoom * self.pixmapLabel.pixmap().size() )

        self.__adjustScrollBar( self.horizontalScrollBar(), factor )
        self.__adjustScrollBar( self.verticalScrollBar(), factor )
        return

    def __adjustScrollBar( self, scrollBar, factor ):
        " Adjusts a scrollbar by a certain factor "

        scrollBar.setValue( int( factor * scrollBar.value() +
                                 ( (factor - 1) * scrollBar.pageStep()/2) ) )
        return


class PixmapTabWidget( QWidget, MainWindowTabWidgetBase ):
    " Pixmap viewer tab widget "

    def __init__( self, parent = None ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__viewer = PixmapWidget()
        self.__fileName = ""
        self.__shortName = ""

        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the toolbar and layout "

        # Buttons
        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        #printButton.setShortcut( 'Ctrl+' )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )

        printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        #printPreviewButton.setShortcut( 'Ctrl+' )
        self.connect( printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight( 16 )

        zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
                                'Zoom in (Ctrl++)', self )
        zoomInButton.setShortcut( 'Ctrl++' )
        self.connect( zoomInButton, SIGNAL( 'triggered()' ), self.__onZoomIn )

        zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
                                'Zoom out (Ctrl+-)', self )
        zoomOutButton.setShortcut( 'Ctrl+-' )
        self.connect( zoomOutButton, SIGNAL( 'triggered()' ), self.__onZoomOut )

        zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
                                   'Zoom reset (Ctrl+0)', self )
        zoomResetButton.setShortcut( 'Ctrl+0' )
        self.connect( zoomResetButton, SIGNAL( 'triggered()' ),
                      self.__onZoomReset )


        # Toolbar
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        toolbar.addAction( printPreviewButton )
        toolbar.addAction( printButton )
        toolbar.addWidget( fixedSpacer )
        toolbar.addAction( zoomInButton )
        toolbar.addAction( zoomOutButton )
        toolbar.addAction( zoomResetButton )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )
        hLayout.addWidget( self.__viewer )
        hLayout.addWidget( toolbar )

        self.setLayout( hLayout )
        return

    def setFocus( self ):
        " Overridden setFocus "
        self.__viewer.setFocus()
        return

    def loadFromFile( self, path ):
        " Loads the content from the given file "
        self.__viewer.loadFromFile( path )
        self.setFileName( os.path.abspath( path ) )
        return

    def setPixmap( self, pixmap ):
        " Loads the provided pixmap "
        self.__viewer.setPixmap( pixmap )
        return

    def __onPrint( self ):
        " Triggered on the 'print' button "
        pass

    def __onPrintPreview( self ):
        " Triggered on the 'print preview' button "
        pass

    def __onZoomIn( self ):
        " Triggered on the 'zoom in' button "
        self.__viewer.doZoom( 1.25 )
        return

    def __onZoomOut( self ):
        " Triggered on the 'zoom out' button "
        self.__viewer.doZoom( 0.8 )
        return

    def __onZoomReset( self ):
        " Triggered on the 'zoom reset' button "
        self.__viewer.resetZoom()
        return



    # Mandatory interface part is below

    def isModified( self ):
        " Tells if the file is modified "
        return False

    def getRWMode( self ):
        " Tells if the file is read only "
        return "RO"

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.PictureViewer

    def getLanguage( self ):
        " Tells the content language "
        return self.__viewer.formatInfo

    def getFileName( self ):
        " Tells what file name of the widget content "
        return self.__fileName

    def setFileName( self, name ):
        " Sets the file name "
        self.__fileName = name
        self.__shortName = os.path.basename( name )
        return

    def getEol( self ):
        " Tells the EOL style "
        return "N/A"

    def getLine( self ):
        " Tells the cursor line "
        return "N/A"

    def getPos( self ):
        " Tells the cursor column "
        return "N/A"

    def getEncoding( self ):
        " Tells the content encoding "
        return self.__viewer.info

    def getShortName( self ):
        " Tells the display name "
        return self.__shortName

    def setShortName( self, name ):
        " Sets the display name "
        self.__shortName = name
        return

