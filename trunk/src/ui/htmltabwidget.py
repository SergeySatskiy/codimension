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

""" HTML viewer tab widget """


import os.path
from PyQt4.QtGui                import QTextEdit, QWidget, QHBoxLayout
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from PyQt4.QtCore               import Qt, SIGNAL


class HTMLViewer( QTextEdit ):
    " HTML viewer "

    def __init__( self, parent = None ):
        QTextEdit.__init__( self, parent )
        self.setReadOnly( True )

    def keyPressEvent( self, event ):
        """ Handles the key press events """

        if event.key() == Qt.Key_Escape:
            self.emit( SIGNAL( 'ESCPressed' ) )
            event.accept()
        else:
            QTextEdit.keyPressEvent( self, event )
        return


class HTMLTabWidget( MainWindowTabWidgetBase, QWidget ):
    " The widget which displays a RO HTML page "

    def __init__( self, parent = None ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__editor = HTMLViewer( parent )
        self.connect( self.__editor, SIGNAL( 'ESCPressed' ),
                      self.__onEsc )

        layout = QHBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.addWidget( self.__editor )
        self.setLayout( layout )

        self.__fileName = ""
        self.__shortName = ""
        return

    def __onEsc( self ):
        " Triggered when Esc is pressed "
        self.emit( SIGNAL( 'ESCPressed' ) )
        return

    def setHTML( self, content ):
        " Sets the content from the given string "
        self.__editor.setHtml( content )
        return

    def loadFormFile( self, path ):
        " Loads the content from the given file "
        f = open( path, 'r' )
        content = f.read()
        f.close()
        self.__editor.setHtml( content )
        self.__fileName = path
        self.__shortName = os.path.basename( path )
        return

    def setFocus( self ):
        " Overridden setFocus "
        self.__editor.setFocus()
        return

    def isModified( self ):
        " Tells if the file is modifed "
        return False

    def getRWMode( self ):
        " Tells the read/write mode "
        return "RO"

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.HTMLViewer

    def getLanguage( self ):
        " Tells the content language "
        return "HTML"

    def getFileName( self ):
        " Tells what file name of the widget "
        return self.__fileName

    def setFileName( self, path ):
        " Sets the file name "
        self.__fileName = path
        self.__shortName = os.path.basename( path )
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
        return "N/A"

    def getShortName( self ):
        " Tells the display name "
        return self.__shortName

    def setShortName( self, name ):
        " Sets the display name "
        self.__shortName = name
        return

