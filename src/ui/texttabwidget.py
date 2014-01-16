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

""" Text viewer tab widget """


import os.path
from PyQt4.QtGui import QTextBrowser, QHBoxLayout, QWidget
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from PyQt4.QtCore import Qt, SIGNAL


class TextViewer( QTextBrowser ):
    " Text viewer "

    def __init__( self, parent = None ):
        QTextBrowser.__init__( self, parent )
        self.setOpenExternalLinks( True )
        self.copyAvailable = False
        self.connect( self, SIGNAL( 'copyAvailable(bool)' ),
                      self.__onCopyAvailable )
        return

    def __onCopyAvailable( self, available ):
        " Triggered when copying is available "
        self.copyAvailable = available
        return

    def isCopyAvailable( self ):
        " True if text copying is available "
        return self.copyAvailable


    def keyPressEvent( self, event ):
        " Handles the key press events "
        if event.key() == Qt.Key_Escape:
            self.emit( SIGNAL( 'ESCPressed' ) )
            event.accept()
        else:
            QTextBrowser.keyPressEvent( self, event )
        return



class TextTabWidget( QWidget, MainWindowTabWidgetBase ):
    " The widget which displays a RO HTML page "

    def __init__( self, parent = None ):
        QWidget.__init__( self )
        MainWindowTabWidgetBase.__init__( self )

        layout = QHBoxLayout( self )
        layout.setMargin( 0 )

        self.__editor = TextViewer( self )
        self.connect( self.__editor, SIGNAL( 'ESCPressed' ),
                      self.__onEsc )
        layout.addWidget( self.__editor )

        self.__fileName = ""
        self.__shortName = ""
        self.__encoding = "n/a"
        return

    def __onEsc( self ):
        " Triggered when Esc is pressed "
        self.emit( SIGNAL( 'ESCPressed' ) )
        return

    def setHTML( self, content ):
        " Sets the content from the given string "
        self.__editor.setHtml( content )
        return

    def getHTML( self ):
        " Provides the currently shown HTML "
        return self.__editor.toHtml()

    def loadFormFile( self, path ):
        " Loads the content from the given file "
        f = open( path, 'r' )
        content = f.read()
        f.close()
        self.setHTML( content )
        self.__fileName = path
        self.__shortName = os.path.basename( path )
        return

    def getViewer( self ):
        " Provides the QTextBrowser "
        return self.__editor

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
        return "n/a"

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
        return "n/a"

    def getLine( self ):
        " Tells the cursor line "
        return "n/a"

    def getPos( self ):
        " Tells the cursor column "
        return "n/a"

    def getEncoding( self ):
        " Tells the content encoding "
        return self.__encoding

    def setEncoding( self, newEncoding ):
        " Sets the encoding - used for Diff files "
        self.__encoding = newEncoding
        return

    def getShortName( self ):
        " Tells the display name "
        return self.__shortName

    def setShortName( self, name ):
        " Sets the display name "
        self.__shortName = name
        return
