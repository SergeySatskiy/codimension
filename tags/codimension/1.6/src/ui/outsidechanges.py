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
# $Id$
#

from PyQt4.QtCore       import Qt, SIGNAL, QStringList, QEventLoop
from PyQt4.QtGui        import QSizePolicy, QFrame, \
                               QTreeWidget, QApplication, \
                               QTreeWidgetItem, QHeaderView, \
                               QLabel, QPushButton, \
                               QApplication, QColor, \
                               QHeaderView, QSizePolicy, QGridLayout, \
                               QFontMetrics
from utils.globals      import GlobalData
import os.path


class OutsideChangeWidget( QFrame ):
    " Frameless dialogue to deal with outside changes "

    def __init__( self, parent ):
        QFrame.__init__( self, parent )

        # Make the frame nice looking
        panelColor = QColor( 224, 0, 0, 255 )
        palette = self.palette()
        palette.setColor( self.backgroundRole(), panelColor )
        self.setPalette( palette )

        self.setFrameShape( QFrame.StyledPanel )
        self.setLineWidth( 2 )
        self.setAutoFillBackground( True )

        self.__markers = []
        self.__createLayout()

        for item in self.__markers:
            item.hide()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        self.__messageLabel = QLabel( "This file has been modified " \
                                      "outside of codimension. What " \
                                      "would you like to do?" )
        self.__messageLabel.setWordWrap( True )
        self.__messageLabel.setAlignment( Qt.AlignHCenter )
        palette = self.__messageLabel.palette()
        palette.setColor( self.foregroundRole(), QColor( 255, 255, 255, 255 ) )
        self.__messageLabel.setPalette( palette )

        self.__leaveAsIsButton = QPushButton( "Continue editing", self )
        self.__leaveAsIsButton.setToolTip( "ESC" )
        self.connect( self.__leaveAsIsButton, SIGNAL( 'clicked()' ), self.hide )

        self.__reloadButton = QPushButton( self )
        self.connect( self.__reloadButton, SIGNAL( 'clicked()' ),
                      self.__reload )

        txt = "Reload all non-modified files"
        self.__reloadAllNonChangedButton = QPushButton( txt, self )
        self.connect( self.__reloadAllNonChangedButton, SIGNAL( 'clicked()' ),
                      self.__reloadAllNonModified )

        # This will prevent the buttons growing wider than necessary
        fontMetrics = QFontMetrics( self.__reloadAllNonChangedButton.font() )
        buttonWidth = fontMetrics.width( txt ) + 20
        self.__reloadAllNonChangedButton.setFixedWidth( buttonWidth )

        gridLayout = QGridLayout( self )
        gridLayout.setMargin( 3 )

        gridLayout.addWidget( self.__messageLabel, 0, 0, 1, 1 )
        gridLayout.addWidget( self.__leaveAsIsButton, 0, 1, 1, 1 )
        gridLayout.addWidget( self.__reloadButton, 1, 1, 1, 1 )
        gridLayout.addWidget( self.__reloadAllNonChangedButton, 2, 1, 1, 1 )

        self.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.move( 5, 5 )


        self.__markers.append( QFrame( self.parent() ) )
        self.__markers.append( QFrame( self.parent() ) )
        self.__markers.append( QFrame( self.parent() ) )
        self.__markers.append( QFrame( self.parent() ) )

        markerColor = QColor( 224, 0, 0, 255 )
        for item in self.__markers:
            pal = item.palette()
            pal.setColor( item.backgroundRole(), markerColor )
            item.setPalette( pal )
            item.setFrameShape( QFrame.StyledPanel )
            item.setLineWidth( 1 )
            item.setAutoFillBackground( True )
            item.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        return

    def resize( self ):
        " Resizes the dialogue to match the editor size "

        vscroll = self.parent().verticalScrollBar()
        if vscroll.isVisible():
            scrollWidth = vscroll.width()
        else:
            scrollWidth = 0

        hscroll = self.parent().horizontalScrollBar()
        if hscroll.isVisible():
            scrollHeight = hscroll.height()
        else:
            scrollHeight = 0

        # Dialogue
        width = self.parent().width()
        height = self.parent().height()
        widgetWidth = width - scrollWidth - 10 - 1

        self.setFixedWidth( widgetWidth )

        # Marker
        self.__markers[ 0 ].move( 1, 1 )
        self.__markers[ 0 ].setFixedWidth( width - scrollWidth - 4 )
        self.__markers[ 0 ].setFixedHeight( 3 )

        self.__markers[ 1 ].move( width - scrollWidth - 5, 1 )
        self.__markers[ 1 ].setFixedWidth( 3 )
        self.__markers[ 1 ].setFixedHeight( height - scrollHeight - 4 )

        self.__markers[ 2 ].move( 1, height - scrollHeight - 5 )
        self.__markers[ 2 ].setFixedWidth( width - scrollWidth - 4 )
        self.__markers[ 2 ].setFixedHeight( 3 )

        self.__markers[ 3 ].move( 1, 1 )
        self.__markers[ 3 ].setFixedWidth( 3 )
        self.__markers[ 3 ].setFixedHeight( height - scrollHeight - 4 )
        return

    def showChoice( self, modified, allEnabled ):
        " Brings up the panel with the correct text and buttons "
        if modified:
            self.__reloadButton.setText( "Reload loosing changes" )
        else:
            self.__reloadButton.setText( "Reload" )
        self.__reloadAllNonChangedButton.setEnabled( allEnabled )

        QApplication.processEvents( QEventLoop.ExcludeUserInputEvents )

        self.resize()
        self.show()
        for item in self.__markers:
            item.show()
        self.__leaveAsIsButton.setFocus()
        self.parent().setReadOnly( True )
        return

    def setFocus( self ):
        " Passes the focus to the default button "
        self.__leaveAsIsButton.setFocus()
        return

    def keyPressEvent( self, event ):
        " Handles the key press events "
        if event.key() == Qt.Key_Escape:
            editorsManager = GlobalData().mainWindow.editorsManager()
            activeWindow = editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()
            event.accept()
            self.hide()
        return

    def hide( self ):
        " Handles the hiding of the panel and markers "
        for item in self.__markers:
            item.hide()
        QFrame.hide( self )
        self.parent().setReadOnly( False )
        self.parent().setFocus()
        return

    def __reload( self ):
        " Reloads the file from the disk "
        self.emit( SIGNAL( 'ReloadRequest' ) )
        return

    def __reloadAllNonModified( self ):
        " Reloads all the non-modified buffers "
        self.emit( SIGNAL( 'ReloadAllNonModifiedRequest' ) )
        return
