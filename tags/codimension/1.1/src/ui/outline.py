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

""" The file outline viewer implementation """

import os.path, logging
from PyQt4.QtCore               import Qt, SIGNAL, QSize, QTimer
from PyQt4.QtGui                import QMenu, QWidget, QAction, QVBoxLayout, \
                                       QToolBar, QCursor, QFrame, QLabel
from utils.pixmapcache          import PixmapCache
from utils.globals              import GlobalData
from outlinebrowser             import OutlineBrowser
from viewitems                  import FunctionItemType, \
                                       ClassItemType, AttributeItemType, \
                                       GlobalItemType
from utils.fileutils            import PythonFileType, Python3FileType, \
                                       detectFileType
from cdmbriefparser             import getBriefModuleInfoFromMemory
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from parsererrors               import ParserErrorsDialog



class OutlineAttributes:
    " Holds all the attributes associated with an outline browser "

    def __init__( self ):
        self.browser = None
        self.contextItem = None
        self.info = None
        self.shortFileName = ""
        self.changed = False
        return


class FileOutlineViewer( QWidget ):
    """ The file outline viewer widget """

    def __init__( self, editorsManager, parent = None ):
        QWidget.__init__( self, parent )

        self.__editorsManager = editorsManager
        self.connect( self.__editorsManager, SIGNAL( "currentChanged(int)" ),
                      self.__onTabChanged )
        self.connect( self.__editorsManager, SIGNAL( "tabClosed" ),
                      self.__onTabClosed )
        self.connect( self.__editorsManager, SIGNAL( 'bufferSavedAs' ),
                      self.__onSavedBufferAs )

        self.__outlineBrowsers = {}  # UUID -> OutlineAttributes
        self.__currentUUID = None
        self.__updateTimer = QTimer( self )
        self.connect( self.__updateTimer, SIGNAL( 'timeout()' ),
                                          self.__updateView )

        self.findButton = None
        self.outlineViewer = None
        self.__createLayout()

        # create the context menu
        self.__menu = QMenu( self )
        self.__findMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'findusage.png' ),
                                'Find where used', self.__findWhereUsed )
        return

    def __connectOutlineBrowser( self, browser ):
        " Connects a new buffer signals "
        browser.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( browser,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowContextMenu )

        self.connect( browser,
                      SIGNAL( "selectionChanged" ),
                      self.__selectionChanged )
        return

    def __createLayout( self ):
        " Helper to create the viewer layout "

        # Toolbar part - buttons
        self.findButton = QAction( \
                PixmapCache().getIcon( 'findusage.png' ),
                'Find where highlighted item is used', self )
        self.findButton.setVisible( False )
        self.connect( self.findButton, SIGNAL( "triggered()" ),
                      self.__findWhereUsed )
        self.showParsingErrorsButton = QAction( \
                PixmapCache().getIcon( 'showparsingerrors.png' ),
                'Show lexer/parser errors', self )
        self.connect( self.showParsingErrorsButton, SIGNAL( "triggered()" ),
                      self.__showParserError )
        self.showParsingErrorsButton.setEnabled( False )

        toolbar = QToolBar( self )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.TopToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedHeight( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        toolbar.addAction( self.findButton )
        toolbar.addAction( self.showParsingErrorsButton )

        # Prepare members for reuse
        self.__noneLabel = QLabel( "\nNot a python file" )
        self.__noneLabel.setFrameShape( QFrame.StyledPanel )
        self.__noneLabel.setAlignment( Qt.AlignHCenter )
        headerFont = self.__noneLabel.font()
        headerFont.setPointSize( headerFont.pointSize() + 2 )
        self.__noneLabel.setFont( headerFont )

        self.__layout = QVBoxLayout()
        self.__layout.setContentsMargins( 0, 0, 0, 0 )
        self.__layout.setSpacing( 0 )
        self.__layout.addWidget( toolbar )
        self.__layout.addWidget( self.__noneLabel )

        self.setLayout( self.__layout )
        return

    def __selectionChanged( self, index ):
        " Handles the changed selection "
        if index is None:
            self.__outlineBrowsers[ self.__currentUUID ].contentItem = None
        else:
            self.__outlineBrowsers[ self.__currentUUID ].contentItem = \
                self.__outlineBrowsers[ \
                        self.__currentUUID ].browser.model().item( index )

        self.__updateButtons()
        return

    def __handleShowContextMenu( self, coord ):
        """ Show the context menu """

        browser = self.__outlineBrowsers[ self.__currentUUID ].browser
        index = browser.indexAt( coord )
        if not index.isValid():
            return

        # This will update the contextItem
        self.__selectionChanged( index )

        contextItem = self.__outlineBrowsers[ self.__currentUUID ].contentItem
        if contextItem is None:
            return

        self.__findMenuItem.setEnabled( self.findButton.isEnabled() )

        self.__menu.popup( QCursor.pos() )
        return

    def __goToDefinition( self ):
        " Jump to definition context menu handler "
        contextItem = self.__outlineBrowsers[ self.__currentUUID ].contentItem
        if contextItem is not None:
            self.__outlineBrowsers[ \
                        self.__currentUUID ].browser.openItem( contextItem )
        return

    def __findWhereUsed( self ):
        """ Find where used context menu handler """
        contextItem = self.__outlineBrowsers[ self.__currentUUID ].contentItem
        if contextItem is not None:
            GlobalData().mainWindow.findWhereUsed( \
                    contextItem.getPath(),
                    contextItem.sourceObj )
        return

    def __updateButtons( self ):
        " Updates the toolbar buttons depending on what is selected "

        self.findButton.setEnabled( False )

        contextItem = self.__outlineBrowsers[ self.__currentUUID ].contentItem
        if contextItem is None:
            return

        if contextItem.itemType in [ FunctionItemType, ClassItemType,
                                     AttributeItemType, GlobalItemType ]:
            self.findButton.setEnabled( True )
        return

    def __onTabChanged( self, index ):
        " Triggered when another tab becomes active "

        # If the timer is still active that means the tab was switched before
        # the handler had a chance to work. Therefore update the previous tab
        # first if so.
        if self.__updateTimer.isActive():
            self.__updateView()

        # Now, switch the outline browser to the new tab
        widget = self.__editorsManager.getWidgetByIndex( index )
        if widget is None:
            if self.__currentUUID is not None:
                self.__outlineBrowsers[ self.__currentUUID ].browser.hide()
                self.__currentUUID = None
            self.__noneLabel.show()
            self.showParsingErrorsButton.setEnabled( False )
            return
        if widget.getType() not in [ MainWindowTabWidgetBase.PlainTextEditor ]:
            if self.__currentUUID is not None:
                self.__outlineBrowsers[ self.__currentUUID ].browser.hide()
                self.__currentUUID = None
            self.__noneLabel.show()
            self.showParsingErrorsButton.setEnabled( False )
            return

        # This is text editor, detect the file type
        if detectFileType( widget.getShortName() ) not in [ PythonFileType,
                                                            Python3FileType ]:
            if self.__currentUUID is not None:
                self.__outlineBrowsers[ self.__currentUUID ].browser.hide()
                self.__currentUUID = None
            self.__noneLabel.show()
            self.showParsingErrorsButton.setEnabled( False )
            return


        # This is a python file, check if we already have the parsed info in
        # the cache
        uuid = widget.getUUID()
        if self.__outlineBrowsers.has_key( uuid ):
            # We have it, hide the current and show the existed
            if self.__currentUUID is not None:
                self.__outlineBrowsers[ self.__currentUUID ].browser.hide()
                self.__currentUUID = None
            else:
                self.__noneLabel.hide()
            self.__currentUUID = uuid
            self.__outlineBrowsers[ self.__currentUUID ].browser.show()

            info = self.__outlineBrowsers[ self.__currentUUID ].info
            self.showParsingErrorsButton.setEnabled( info.isOK != True )
            return

        # It is first time we are here, create a new
        editor = widget.getEditor()
        self.connect( editor, SIGNAL( 'SCEN_CHANGE()' ),
                              self.__onBufferChanged )

        info = getBriefModuleInfoFromMemory( str( editor.text() ) )

        shortFileName = widget.getShortName()
        browser = OutlineBrowser( uuid, shortFileName, info )
        self.__connectOutlineBrowser( browser )
        self.__layout.addWidget( browser )
        if self.__currentUUID is not None:
            self.__outlineBrowsers[ self.__currentUUID ].browser.hide()
            self.__currentUUID = None
        else:
            self.__noneLabel.hide()

        self.__currentUUID = uuid
        attributes = OutlineAttributes()
        attributes.browser = browser
        attributes.contextItem = None
        attributes.info = info
        attributes.shortFileName = shortFileName
        attributes.changed = False
        self.__outlineBrowsers[ self.__currentUUID ] = attributes
        self.__outlineBrowsers[ self.__currentUUID ].browser.show()
        return

    def __onBufferChanged( self ):
        " Triggered when a change in the buffer is identified "
        self.__updateTimer.stop()
        if self.__outlineBrowsers.has_key( self.__currentUUID ):
            if self.__outlineBrowsers[ self.__currentUUID ].changed == False:
                self.__outlineBrowsers[ self.__currentUUID ].changed = True
                browser = self.__outlineBrowsers[ self.__currentUUID ].browser
                fName = self.__outlineBrowsers[ self.__currentUUID ].shortFileName
                browser.model().sourceModel().updateRootData( 0, fName + ", +" )
        self.__updateTimer.start( 1500 )
        return

    def __updateView( self ):
        " Updates the view when a file is changed "
        self.__updateTimer.stop()
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID( \
                                        self.__currentUUID )
        if widget is None:
            return

        editor = widget.getEditor()
        info = getBriefModuleInfoFromMemory( str( editor.text() ) )
        self.showParsingErrorsButton.setEnabled( info.isOK != True )
        browser = self.__outlineBrowsers[ self.__currentUUID ].browser
        fName = self.__outlineBrowsers[ self.__currentUUID ].shortFileName

        if len( info.lexerErrors ) > 0:
            browser.model().sourceModel().updateRootData( 0, fName + ", +" )
            return

        browser.model().sourceModel().updateRootData( 0, fName )
        self.__outlineBrowsers[ self.__currentUUID ].changed = False

        browser.updateFileItem( browser.model().sourceModel().rootItem, info )
        self.__outlineBrowsers[ self.__currentUUID ].info = info

        return

    def __onTabClosed( self, uuid ):
        " Triggered when a tab is closed "

        if self.__outlineBrowsers.has_key( uuid ):
            del self.__outlineBrowsers[ uuid ]
        return

    def __onSavedBufferAs( self, fileName, uuid ):
        " Triggered when a file is saved with a new name "

        if self.__outlineBrowsers.has_key( uuid ):

            baseName = os.path.basename( fileName )
            if detectFileType( baseName ) not in [ PythonFileType,
                                                   Python3FileType ]:
                # It's not a python file anymore
                if uuid == self.__currentUUID:
                    self.__outlineBrowsers[ uuid ].browser.hide()
                    self.__noneLabel.show()
                    self.__currentUUID = None

                del self.__outlineBrowsers[ uuid ]
                self.showParsingErrorsButton.setEnabled( False )
                self.findButton.setEnabled( False )
                return

            # Still python file with a different name
            browser = self.__outlineBrowsers[ uuid ].browser
            self.__outlineBrowsers[ uuid ].shortFileName = baseName
            if self.__outlineBrowsers[ uuid ].changed:
                title = baseName + ", +"
            else:
                title = baseName
            browser.model().sourceModel().updateRootData( 0, title )
        return

    def __showParserError( self ):
        " Shows the parser errors window "
        if self.__currentUUID is None:
            return

        try:
            fName = self.__outlineBrowsers[ self.__currentUUID ].shortFileName

            widget = self.__editorsManager.getWidgetByUUID( self.__currentUUID )
            if widget is None:
                return

            editor = widget.getEditor()
            info = getBriefModuleInfoFromMemory( str( editor.text() ) )
            dialog = ParserErrorsDialog( fName, info )
            dialog.exec_()
        except Exception, ex:
            logging.error( str( ex ) )
        return

