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

""" Pyflakes results viewer """
 
from PyQt4.QtCore import SIGNAL, QTimer, QObject, Qt, QVariant
from PyQt4.QtGui import QMenu
from utils.pixmapcache import PixmapCache
from utils.fileutils import PythonFileType, Python3FileType, detectFileType
from mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.ierrors import getFileErrors



class PyflakesAttributes:
    " Holds all the attributes associated with pyflakes results "

    def __init__( self ):
        self.messages = []      # Complains
        self.changed = False
        return

    def hasComplains( self ):
        " True if there are any complains "
        if self.messages:
            return True
        return False


class PyflakesViewer( QObject ):
    """ The pyflakes viewer """

    def __init__( self, editorsManager, uiLabel, parent = None ):
        QObject.__init__( self, parent )

        self.__editorsManager = editorsManager
        self.__uiLabel = uiLabel
        self.setFlakesNotAvailable( self.__uiLabel )

        self.connect( self.__editorsManager, SIGNAL( "currentChanged(int)" ),
                      self.__onTabChanged )
        self.connect( self.__editorsManager, SIGNAL( "tabClosed" ),
                      self.__onTabClosed )
        self.connect( self.__editorsManager, SIGNAL( 'bufferSavedAs' ),
                      self.__onSavedBufferAs )
        self.connect( self.__editorsManager, SIGNAL( 'fileTypeChanged' ),
                      self.__onFileTypeChanged )

        self.__flakesResults = {}  # UUID -> PyflakesAttributes
        self.__currentUUID = None
        self.__updateTimer = QTimer( self )
        self.__updateTimer.setSingleShot( True )
        self.connect( self.__updateTimer, SIGNAL( 'timeout()' ),
                                          self.__updateView )

        # Context menu for the messages icon
        self.__uiLabel.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.__uiLabel,
                      SIGNAL( 'customContextMenuRequested(const QPoint &)' ),
                      self.__showPyflakesContextMenu )
        self.connect( self.__uiLabel,
                      SIGNAL( 'doubleClicked' ),
                      self.__jumpToFirstMessage )
        return

    def __onTabChanged( self, index ):
        " Triggered when another tab becomes active "

        # If the timer is still active that means the tab was switched before
        # the handler had a chance to work. Therefore update the previous tab
        # first if so.
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
            self.__updateView()

        # Now, switch the pyflakes browser to the new tab
        if index == -1:
            widget = self.__editorsManager.currentWidget()
        else:
            widget = self.__editorsManager.getWidgetByIndex( index )
        if widget is None:
            self.__currentUUID = None
            self.setFlakesNotAvailable( self.__uiLabel )
            return

        if widget.getType() not in [ MainWindowTabWidgetBase.PlainTextEditor ]:
            self.__currentUUID = None
            self.setFlakesNotAvailable( self.__uiLabel )
            return

        # This is text editor, detect the file type
        if widget.getFileType() not in [ PythonFileType, Python3FileType ]:
            self.__currentUUID = None
            self.setFlakesNotAvailable( self.__uiLabel )
            return


        # This is a python file, check if we already have the parsed info in
        # the cache
        uuid = widget.getUUID()
        self.__currentUUID = uuid
        if uuid in self.__flakesResults:
            # We have it, change the icon and the tooltip correspondingly
            results = self.__flakesResults[ uuid ].messages
            self.setFlakesResults( self.__uiLabel, results, None )
            return

        # It is first time we are here, create a new
        editor = widget.getEditor()
        self.connect( editor, SIGNAL( 'SCEN_CHANGE()' ),
                              self.__onBufferChanged )
        self.connect( editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                              self.__cursorPositionChanged )

        results = getFileErrors( str( editor.text() ) )
        attributes = PyflakesAttributes()
        attributes.messages = results
        attributes.changed = False
        self.__flakesResults[ uuid ] = attributes
        self.__currentUUID = uuid

        self.setFlakesResults( self.__uiLabel, results, editor )
        return

    def __cursorPositionChanged( self, xpos, ypos ):
        " Triggered when a cursor position is changed "
        if self.__updateTimer.isActive():
            # If a file is very large and the cursor is moved
            # straight after changes this will delay the update till
            # the real pause.
            self.__updateTimer.stop()
            self.__updateTimer.start( 1500 )
        return

    def __onBufferChanged( self ):
        " Triggered when a change in the buffer is identified "
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID( self.__currentUUID )
        if widget is None:
            return
        if widget.getEditor().ignoreBufferChangedSignal:
            return

        self.__updateTimer.stop()
        if self.__currentUUID in self.__flakesResults:
            if self.__flakesResults[ self.__currentUUID ].changed == False:
                self.__flakesResults[ self.__currentUUID ].changed = True
                self.setFlakesWaiting( self.__uiLabel )
        self.__updateTimer.start( 1500 )
        return

    def __updateView( self ):
        " Updates the view when a file is changed "
        self.__updateTimer.stop()
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID( self.__currentUUID )
        if widget is None:
            return

        if self.__flakesResults[ self.__currentUUID ].changed == False:
            return

        editor = widget.getEditor()
        results = getFileErrors( str( editor.text() ) )

        self.__flakesResults[ self.__currentUUID ].messages = results
        self.__flakesResults[ self.__currentUUID ].changed = False

        self.setFlakesResults( self.__uiLabel, results, editor )
        return

    def __onTabClosed( self, uuid ):
        " Triggered when a tab is closed "
        if uuid in self.__flakesResults:
            del self.__flakesResults[ uuid ]
        return

    def __onSavedBufferAs( self, fileName, uuid ):
        " Triggered when a file is saved with a new name "

        if uuid in self.__flakesResults:

            if detectFileType( fileName ) not in [ PythonFileType,
                                                   Python3FileType ]:
                # It's not a python file anymore
                self.__currentUUID = None
                del self.__flakesResults[ uuid ]
                self.setFlakesNotAvailable( self.__uiLabel )
        return

    def __onFileTypeChanged( self, fileName, uuid, newFileType ):
        " Triggered when the current buffer file type is changed, e.g. .cgi "
        if newFileType in [ PythonFileType, Python3FileType ]:
            # The file became a python one
            if uuid not in self.__flakesResults:
                self.__onTabChanged( -1 )
        else:
            if uuid in self.__flakesResults:
                # It's not a python file any more
                if uuid == self.__currentUUID:
                    self.__currentUUID = None

                del self.__flakesResults[ uuid ]
                self.setFlakesNotAvailable( self.__uiLabel )
        return

    def __showPyflakesContextMenu( self, pos ):
        " Triggered when the icon context menu is requested "
        if self.__currentUUID is None:
            return
        if self.__currentUUID not in self.__flakesResults:
            return

        messages = self.__flakesResults[ self.__currentUUID ].messages
        if not messages:
            return

        # OK, we have something to show
        contextMenu = QMenu( self.__uiLabel )
        for item in messages:
            act = contextMenu.addAction(
                        PixmapCache().getIcon( 'pyflakesmsgmarker.png' ),
                        "Line " + str( item[ 1 ] ) + ": " + item[ 0 ] )
            act.setData( QVariant( item[ 1 ] ) )
        self.connect( contextMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__onContextMenu )
        contextMenu.popup( self.__uiLabel.mapToGlobal( pos ) )
        return

    def __onContextMenu( self, act ):
        " Triggered when a context menu item is selected "
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID( self.__currentUUID )
        if widget is None:
            return

        lineNum, isOK = act.data().toInt()
        if not isOK:
            return

        self.__editorsManager.jumpToLine( lineNum )
        return

    def __jumpToFirstMessage( self ):
        " Double click on the icon "
        if self.__currentUUID is None:
            return
        if self.__currentUUID not in self.__flakesResults:
            return

        messages = self.__flakesResults[ self.__currentUUID ].messages
        if not messages:
            return

        widget = self.__editorsManager.getWidgetByUUID( self.__currentUUID )
        if widget is None:
            return

        self.__editorsManager.jumpToLine( messages[ 0 ][ 1 ] )
        return

    @staticmethod
    def __htmlEncode( string ):
        " Encodes HTML "
        return string.replace( "&", "&amp;" ) \
                     .replace( ">", "&gt;" ) \
                     .replace( "<", "&lt;" )

    @staticmethod
    def setFlakesResults( label, results, editor ):
        """ Displays the appropriate icon:
            - pyflakes has no complains
            - pyflakes found errors """

        if editor is not None:
            editor.clearPyflakesMessages()

        if results:
            # There are complains
            complains = "File checked: there are pyflakes complains<br>"
            for item in results:
                if complains:
                    complains += "<br>"
                complains += "Line " + str( item[ 1 ] ) + ": " + \
                             PyflakesViewer.__htmlEncode( item[ 0 ] )
                if editor is not None:
                    editor.addPyflakesMessage( item[ 1 ], item[ 0 ] )
            label.setToolTip( complains.replace( " ", "&nbsp;" ) )
            label.setPixmap( PixmapCache().getPixmap( 'flakeserrors.png' ) )
        else:
            # There are no complains
            label.setToolTip( "File checked: no pyflakes complains" )
            label.setPixmap( PixmapCache().getPixmap( 'flakesok.png' ) )
        return

    @staticmethod
    def setFlakesWaiting( label ):
        """ Displays the appropriate icon that pyflakes is waiting
            for a time slice to start checking """
        label.setToolTip( "File is modified: "
                          "pyflakes is waiting for time slice" )
        label.setPixmap( PixmapCache().getPixmap( 'flakesmodified.png' ) )
        return

    @staticmethod
    def setFlakesNotAvailable( label ):
        " Displays the appropriate icon that pyflakes is not available "
        label.setToolTip( "Not a python file: pyflakes is sleeping" )
        label.setPixmap( PixmapCache().getPixmap( 'flakessleep.png' ) )
        return

