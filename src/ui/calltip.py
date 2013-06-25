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

" Custom calltips "


from PyQt4.QtCore import Qt, SIGNAL, QEventLoop
from PyQt4.QtGui import ( QSizePolicy, QFrame, QLabel, QPushButton, QColor,
                          QApplication, QGridLayout, QFontMetrics )
from utils.globals import GlobalData


class Calltip( QFrame ):
    " Frameless panel with a calltip "

    def __init__( self, parent ):
        QFrame.__init__( self, parent )

        # Make the frame nice looking
        palette = self.palette()
        palette.setColor( self.backgroundRole(),
                          GlobalData().skin.calltipPaper )
        self.setPalette( palette )

        self.setFrameShape( QFrame.StyledPanel )
        self.setLineWidth( 2 )
        self.setAutoFillBackground( True )

        # Keep pylint happy
        self.__calltipLabel = None

        self.__createLayout()
        QFrame.hide( self )
        return

    def __createLayout( self ):
        " Creates the widget layout "

        self.__calltipLabel = QLabel( "" )
        self.__calltipLabel.setSizePolicy( QSizePolicy.Ignored,
                                           QSizePolicy.Fixed )
        self.__calltipLabel.setWordWrap( False )
        self.__calltipLabel.setAlignment( Qt.AlignLeft )
        palette = self.__calltipLabel.palette()
        palette.setColor( self.foregroundRole(),
                          GlobalData().skin.calltipColor )
        self.__calltipLabel.setPalette( palette )

        gridLayout = QGridLayout( self )
        gridLayout.setMargin( 3 )
        gridLayout.addWidget( self.__calltipLabel, 0, 0, 1, 1 )

        self.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
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

        vPos = height - self.height() - scrollHeight
        self.move( 5, vPos - 2 )
        return

    def showCalltip( self, message ):
        " Brings up the panel with the required text "
        self.__calltipLabel.setText( message )
        QApplication.processEvents( QEventLoop.ExcludeUserInputEvents )

        self.resize()
        self.show()
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
        QFrame.hide( self )
        self.parent().setFocus()
        return
