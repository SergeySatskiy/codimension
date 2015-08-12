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

from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import ( QToolBar, QWidget, QGraphicsView, QPainter,
                          QApplication, QGraphicsScene, QHBoxLayout )
from cdmcf import getControlFlowFromMemory
from flowui.vcanvas import VirtualCanvas
from flowui.cflowsettings import getDefaultCflowSettings


class CFGraphicsView( QGraphicsView ):
    """ Central widget """

    def __init__( self, parent = None ):
        super( CFGraphicsView, self ).__init__( parent )
        self.setRenderHint( QPainter.Antialiasing )
        self.setRenderHint( QPainter.TextAntialiasing )
        return

    def wheelEvent( self, event ):
        """ Mouse wheel event """
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = 1.41 ** ( -event.delta() / 240.0 )
            self.scale( factor, factor )
        else:
            QGraphicsView.wheelEvent( self, event )
        return

    def zoomIn( self ):
        """ Zoom when a button clicked """
        factor = 1.41 ** (120.0/240.0)
        self.scale( factor, factor )
        return

    def zoomOut( self ):
        """ Zoom when a button clicked """
        factor = 1.41 ** (-120.0/240.0)
        self.scale( factor, factor )
        return



class FlowUIWidget( QWidget ):
    " The widget which goes along with the text editor "

    def __init__( self, editor, parent ):
        QWidget.__init__( self, parent )

        self.__editor = editor

        self.cflowSettings = getDefaultCflowSettings( self )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )

        hLayout.addWidget( self.__createGraphicsView() )
        hLayout.addWidget( self.__createToolbar() )

        self.setLayout( hLayout )
        return

    def __createToolbar( self ):
        " Creates the toolbar "
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        return toolbar

    def __createGraphicsView( self ):
        """ Creates the graphics view """
        self.scene = QGraphicsScene( self )
        self.view = CFGraphicsView( self )
        self.view.setScene( self.scene )
        return self.view

    def process( self, content ):
        """ Parses the content and displays the results """

        self.cf = getControlFlowFromMemory( content )
        if len( self.cf.errors ) != 0:
            print "No drawing due to parsing errors"
            return

        if len( self.cf.warnings ) != 0:
            self.logMessage( "Parser warnings: " )
            for warn in self.cf.warnings:
                print str( warn[0] ) + ": " + warn[1]

        self.scene.clear()
        try:
            # Top level canvas has no adress and no parent canvas
            canvas = VirtualCanvas( self.cflowSettings, None, None, None )
            canvas.layout( self.cf )
            width, height = canvas.render()
            self.scene.setSceneRect( 0, 0, width, height )
            canvas.draw( self.scene, 0, 0 )
        except Exception, exc:
            print "Exception:\n" + str( exc )
        return

