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
# $Id: gotolinewidget.py 17 2011-01-16 21:23:13Z sergey.satskiy@gmail.com $
#


""" Goto line widget implementation """

from PyQt4.QtGui                import QHBoxLayout, QToolButton, QLabel, \
                                       QSizePolicy, QComboBox, QWidget, \
                                       QIntValidator
from utils.pixmapcache          import PixmapCache
from PyQt4.QtCore               import SIGNAL, Qt, QStringList
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase



class GotoLineWidget( QWidget ):
    " goto bar widget "

    maxHistory = 12

    def __init__( self, editorsManager, parent = None ):

        QWidget.__init__( self, parent )
        self.editorsManager = editorsManager

        self.__gotoHistory = QStringList()

        # Common graphics items
        closeButton = QToolButton( self )
        closeButton.setToolTip( "Click to close the dialog (ESC)" )
        closeButton.setIcon( PixmapCache().getIcon( "close.png" ) )
        self.connect( closeButton, SIGNAL( "clicked()" ), self.hide )

        lineLabel = QLabel( self )
        lineLabel.setText( "Goto line:" )

        self.linenumberEdit = QComboBox( self )
        self.linenumberEdit.setEditable( True )
        self.linenumberEdit.setInsertPolicy( QComboBox.InsertAtTop )
        self.linenumberEdit.setAutoCompletion( False )
        self.linenumberEdit.setDuplicatesEnabled( False )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                self.linenumberEdit.sizePolicy().hasHeightForWidth() )
        self.linenumberEdit.setSizePolicy( sizePolicy )
        self.validator = QIntValidator( 1, 100000, self )
        self.linenumberEdit.setValidator( self.validator )
        self.connect( self.linenumberEdit,
                      SIGNAL( 'editTextChanged(const QString&)' ),
                      self.__onEditTextChanged )
        self.connect( self.linenumberEdit.lineEdit(),
                      SIGNAL( "returnPressed()" ),
                      self.__onEnter )

        self.goButton = QToolButton( self )
        self.goButton.setToolTip( "Click to jump to the line (ENTER)" )
        self.goButton.setIcon( PixmapCache().getIcon( "gotoline.png" ) )
        self.goButton.setFocusPolicy( Qt.NoFocus )
        self.goButton.setEnabled( False )
        self.connect( self.goButton, SIGNAL( "clicked()" ), self.__onGo )

        spacer = QWidget()
        spacer.setFixedWidth( 1 )

        horizontalLayout = QHBoxLayout( self )
        horizontalLayout.setMargin( 0 )

        horizontalLayout.addWidget( closeButton )
        horizontalLayout.addWidget( lineLabel )
        horizontalLayout.addWidget( self.linenumberEdit )
        horizontalLayout.addWidget( self.goButton )
        horizontalLayout.addWidget( spacer )
        return

    def keyPressEvent( self, event ):
        """ Handles the key press events """

        if event.key() == Qt.Key_Escape:
            activeWindow = self.editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()
            event.accept()
            self.hide()
        return

    def __updateHistory( self, txt ):
        " Updates the combo history "

        self.__gotoHistory.removeAll( txt )
        self.__gotoHistory.prepend( txt )
        while len( self.__gotoHistory ) > GotoLineWidget.maxHistory:
            del self.__gotoHistory[ len( self.__gotoHistory ) - 1 ]
        self.linenumberEdit.clear()
        self.linenumberEdit.addItems( self.__gotoHistory )
        return

    def show( self ):
        " Overriden show() method "
        self.linenumberEdit.lineEdit().selectAll()
        QWidget.show( self )
        self.activateWindow()
        return

    def setFocus( self ):
        " Overridded setFocus "
        self.linenumberEdit.setFocus()
        return

    def updateStatus( self ):
        " Triggered when the current tab is changed "
        currentWidget = self.editorsManager.currentWidget()
        status = currentWidget.getType() in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]
        self.linenumberEdit.setEnabled( status )
        self.goButton.setEnabled( status and \
                                  self.linenumberEdit.currentText() != "" )
        return

    def __onGo( self ):
        " Triggered when the 'Go!' button is clicked "
        if self.linenumberEdit.currentText() == "":
            return

        currentWidget = self.editorsManager.currentWidget()
        if not currentWidget.getType() in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        txt = self.linenumberEdit.currentText()
        self.__updateHistory( txt )
        editor = currentWidget.getEditor()
        line = min( int( txt ), editor.lines() ) - 1

        editor.setCursorPosition( line, 0 )
        editor.ensureLineVisible( line )
        currentWidget.setFocus()
        return

    def __onEditTextChanged( self, text ):
        " Triggered when the text has been changed "
        self.goButton.setEnabled( text != "" )
        return

    def __onEnter( self ):
        " Triggered when 'Enter' or 'Return' is clicked "
        self.__onGo()
        return

