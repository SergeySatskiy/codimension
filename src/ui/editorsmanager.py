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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" The real main widget - tab bar with editors """


import logging, os.path
from PyQt4.QtCore               import Qt, SIGNAL, QPoint, QByteArray, \
                                       QMimeData, QVariant, QDir, QUrl
from PyQt4.QtGui                import QTabWidget, QTabBar, QApplication, \
                                       QDrag, QWidget, QHBoxLayout, QMenu, \
                                       QToolButton, QShortcut, QFileDialog, \
                                       QDialog, QMessageBox
from utils.pixmapcache          import PixmapCache
from welcomewidget              import WelcomeWidget
from helpwidget                 import QuickHelpWidget
from editor.texteditor          import TextEditorTabWidget
from pixmapwidget               import PixmapTabWidget
from utils.fileutils            import detectFileType, getFileIcon, \
                                       HTMLFileType, PythonFileType, \
                                       Python3FileType, PixmapFileType
from utils.misc                 import getNewFileTemplate
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from utils.globals              import GlobalData
from utils.settings             import Settings


class DragAndDropTabBar( QTabBar ):
    " QTabBar extension "

    def __init__( self, parent = None ):

        QTabBar.__init__( self, parent )
        self.setTabsClosable( False )
        self.setAcceptDrops( True )

        self.__dragStartPos = QPoint()
        return

    def mousePressEvent( self, event ):
        " Handles mouse press events "

        if event.button() == Qt.LeftButton:
            self.__dragStartPos = QPoint( event.pos() )
            # print "Drag start memorized"
        QTabBar.mousePressEvent( self, event )
        return

    def mouseMoveEvent( self, event ):
        " Handles mouse move events "

        # print "mouseMoveEvent"
        if event.buttons() == Qt.MouseButtons( Qt.LeftButton ) and \
           ( event.pos() - self.__dragStartPos ).manhattanLength() > \
                QApplication.startDragDistance():
            drag = QDrag( self )
            mimeData = QMimeData()
            index = self.tabAt( event.pos() )
            mimeData.setText( self.tabText( index ) )
            mimeData.setData( "action", "tab-reordering" )
            mimeData.setData( "tabbar-id", QByteArray.number( id( self ) ) )
            drag.setMimeData( mimeData )

            # 0 means ignore => should check the cursor position
            result = drag.exec_()
            #print result
        QTabBar.mouseMoveEvent( self, event )
        return

    def dragEnterEvent( self, event ):
        " Handles the drag enter events "

        # print "Drag enter event"
        mimeData = event.mimeData()
        formats = mimeData.formats()
        if formats.contains( "action" ) and \
           mimeData.data( "action" ) == "tab-reordering" and \
           formats.contains( "tabbar-id" ) and \
           mimeData.data( "tabbar-id" ).toLong()[ 0 ] == id( self ):
            event.acceptProposedAction()
        QTabBar.dragEnterEvent( self, event )
        return

    def dropEvent( self, event ):
        " Handles the drop events "

        fromIndex = self.tabAt( self.__dragStartPos )
        toIndex = self.tabAt( event.pos() )
        if fromIndex != toIndex:
            self.emit( SIGNAL("tabMoveRequested(int, int)"),
                       int(fromIndex), int(toIndex) )
            # print "drop event. From: " + str(fromIndex) + " To: " + str(toIndex)
            event.acceptProposedAction()
        QTabBar.dropEvent( self, event )
        return


class TabWidget( QTabWidget ):
    " Extension to QTabWidget "

    def __init__( self, parent = None ):
        QTabWidget.__init__( self, parent )

        self._tabBar = DragAndDropTabBar( self )
        self.setTabBar( self._tabBar )
        self.connect( self._tabBar, SIGNAL( "tabMoveRequested(int, int)" ),
                      self.moveTab )

        self.__lastCurrentIndex = -1
        self.__currentIndex = -1
        return

    def _memorizeLastIndex( self, index ):
        " Handles the currentChanged signal "

        if index == -1:
            self.__lastCurrentIndex = -1
        else:
            self.__lastCurrentIndex = self.__currentIndex
        self.__currentIndex = index
        return

    def switchTab( self ):
        " Switches between the current and the previous current tab "

        if self.__lastCurrentIndex == -1 or self.__currentIndex == -1:
            return

        self.setCurrentIndex( self.__lastCurrentIndex )
        self.currentWidget().setFocus()
        return

    def nextTab( self ):
        " Shows the next tab "

        ind = self.currentIndex() + 1
        if ind == self.count():
            ind = 0

        self.setCurrentIndex( ind )
        self.currentWidget().setFocus()
        return

    def prevTab( self ):
        " Shows the previous tab "

        ind = self.currentIndex() - 1
        if ind == -1:
            ind = self.count() - 1

        self.setCurrentIndex( ind )
        self.currentWidget().setFocus()
        return

    def activateTab( self, index ):
        " Activates the given tab "
        if index >= self.tabBar().count():
            return
        self.setCurrentIndex( index )
        self.currentWidget().setFocus()
        return

    def getTabIndex( self, pos ):
        " Provides the index of a tab for the given position "
        _tabbar = self.tabBar()
        for index in range( _tabbar.count() ):
            rect = _tabbar.tabRect( index )
            if rect.contains( pos ):
                return index
        return -1

    def moveTab( self, curIndex, newIndex ):
        """ Moves a tab to a new index """

        # step 1: save the tab data of tab to be moved
        toolTip = self.tabToolTip( curIndex )
        text = self.tabText( curIndex )
        icon = self.tabIcon( curIndex )
        whatsThis = self.tabWhatsThis( curIndex )
        widget = self.widget( curIndex )
        curWidget = self.currentWidget()

        # step 2: move the tab
        self.removeTab( curIndex )
        self.insertTab( newIndex, widget, icon, text )

        # step 3: set the tab data again
        self.setTabToolTip( newIndex, toolTip )
        self.setTabWhatsThis( newIndex, whatsThis )

        # step 4: set current widget
        self.__currentIndex = newIndex
        self.setCurrentWidget( curWidget )
        self.tabMoved( curIndex, newIndex )
        self.currentWidget().setFocus()
        return

    def tabMoved( self, currentIndex, newIndex ):
        " Should be re-implemented in the deriving class "
        return



class EditorsManager( TabWidget ):
    " Tab bar with editors "


    def __init__( self, parent = None ):

        TabWidget.__init__( self, parent )

        self.__mainWindow = parent
        self.__navigationMenu = None
        self.__historyMenu = None
        self.navigationButton = None
        self.historyBackButton = None
        self.historyFwdButton = None
        self.createNavigationButtons()

        # Auxiliary widgets - they are created in the main window
        self.findWidget = None
        self.replaceWidget = None
        self.gotoWidget = None

        self.widgets = []       # Widgets on displayed tabs
        self.history = []       # Global tabs history
                                # Each history item is 4 items list:
                                # - icon
                                # - file name
                                # - display name
                                # - line number
        self.historyIndex = -1  # Current position in the history
        self.newIndex = -1

        self.__welcomeWidget = WelcomeWidget()
        self.addTab( self.__welcomeWidget, getFileIcon( HTMLFileType ),
                     self.__welcomeWidget.getShortName() )
        self.connect( self.__welcomeWidget, SIGNAL( 'ESCPressed' ),
                      self.__onESC )

        self.__helpWidget = QuickHelpWidget()
        self.connect( self.__helpWidget, SIGNAL( 'ESCPressed' ),
                      self.__onESC )

        self.__updateControls()
        self.__installActions()
        self.__updateStatusBar()

        self.connect( self._tabBar, SIGNAL( "tabCloseRequested(int)" ),
                      self.__onCloseRequest )
        self.connect( self, SIGNAL( "currentChanged(int)" ),
                      self.__currentChanged )
        return

    def __installActions( self ):
        " Installs various key combinations handlers "
        openAction = QShortcut( 'Ctrl+O', self )
        self.connect( openAction, SIGNAL( "activated()" ),
                      self.__onOpen )
        saveAction = QShortcut( 'Ctrl+S', self )
        self.connect( saveAction, SIGNAL( "activated()" ),
                      self.__onSave )
        saveAsAction = QShortcut( 'Ctrl+Shift+S', self )
        self.connect( saveAsAction, SIGNAL( "activated()" ),
                      self.__onSaveAs )
        findAction = QShortcut( 'Ctrl+F', self )
        self.connect( findAction, SIGNAL( 'activated()' ),
                      self.__onFind )
        replaceAction = QShortcut( 'Ctrl+R', self )
        self.connect( replaceAction, SIGNAL( 'activated()' ),
                      self.__onReplace )
        closeTabAction = QShortcut( 'Ctrl+F4', self )
        self.connect( closeTabAction, SIGNAL( 'activated()' ),
                      self.__onCloseTab )
        nextTabAction = QShortcut( 'Ctrl+PgUp', self )
        self.connect( nextTabAction, SIGNAL( 'activated()' ),
                      self.__onNextTab )
        nextTabActionSyn = QShortcut( 'Ctrl+Tab', self )
        self.connect( nextTabActionSyn, SIGNAL( 'activated()' ),
                      self.__onNextTab )
        prevTabAction = QShortcut( 'Ctrl+PgDown', self )
        self.connect( prevTabAction, SIGNAL( 'activated()' ),
                      self.__onPrevTab )
        helpAction = QShortcut( 'F1', self )
        self.connect( helpAction, SIGNAL( 'activated()' ),
                      self.__onHelp )
        gotoAction = QShortcut( 'Ctrl+G', self )
        self.connect( gotoAction, SIGNAL( 'activated()' ),
                      self.__onGoto )
        return

    def registerAuxWidgets( self, find, replace, goto ):
        " Memorizes references to the auxiliary widgets "
        self.findWidget = find
        self.replaceWidget = replace
        self.gotoWidget = goto
        return

    def tabMoved( self, currentIndex, newIndex ):
        " Base class calls this method when two tabs are exchanged "
        temp = self.widgets[ currentIndex ]
        self.widgets[ currentIndex ] = self.widgets[ newIndex ]
        self.widgets[ newIndex ] = temp
        self.__updateStatusBar()
        return

    def getNewName( self ):
        " Provides a dummy name for the new tab file "
        self.newIndex += 1
        return "unnamed" + str( self.newIndex ) + ".py"

    def __onNextTab( self ):
        " Triggers when Ctrl+PgUp is received "
        if len( self.widgets ) != 0:
            self.nextTab()
        return

    def __onPrevTab( self ):
        " triggers when Ctrl+PgDown is received "
        if len( self.widgets ) != 0:
            self.prevTab()
        return

    def newTabClicked( self ):
        " new tab click handler "

        if len( self.widgets ) == 0:
            # It is the only welcome widget on the screen
            self.removeTab( 0 )
            self._tabBar.setTabsClosable( True )

        newWidget = TextEditorTabWidget()
        editor = newWidget.getEditor()
        newWidget.setShortName( self.getNewName() )
        self.widgets.append( newWidget )

        fileType = detectFileType( newWidget.getShortName() )

        # Load a template content if available
        initialContent = getNewFileTemplate()
        if initialContent != "":
            editor.setText( initialContent )
            lineNo = editor.lines()
            editor.setCursorPosition( lineNo - 1,
                                      editor.lineLength( lineNo - 1 ) )
            editor.ensureLineVisible( lineNo - 1 )
            editor.setModified( False )

        # Bind a lexer
        editor.bindLexer( newWidget.getShortName(), fileType )

        self.addTab( newWidget, getFileIcon( fileType ),
                     newWidget.getShortName() )
        self.activateTab( len( self.widgets ) - 1 )
        self.__updateControls()
        self.__connectEditorWidget( newWidget )
        self.__updateStatusBar()
        editor.setFocus()
        newWidget.updateStatus()
        return

    def __updateControls( self ):
        " Updates the history/navigation buttons status "
        self.navigationButton.setEnabled( False )
        self.historyBackButton.setEnabled( False )
        self.historyFwdButton.setEnabled( False )

        if len( self.widgets ) > 0:
            self.navigationButton.setEnabled( True )

        if len( self.history ) == 0:
            return
        if self.historyIndex > 0:
            self.historyBackButton.setEnabled( True )
        if self.historyIndex < len( self.history ) - 1:
            self.historyFwdButton.setEnabled( True )
        return

    def __onCloseTab( self ):
        " Triggered when Ctrl+F4 is received "
        if len( self.widgets ) == 0:
            return
        self.__onCloseRequest( self.currentIndex() )
        return

    def __onCloseRequest( self, index ):
        " Close tab handler "

        wasDiscard = False
        if self.widgets[ index ].isModified():
            # Ask the user if the changes should be discarded
            res = QMessageBox.warning( \
                        self.widgets[ index ],
                        "Unsaved changes",
                        "<b>The document has been modified.<b>" \
                        "<p>Do you want to save changes?</p>",
                        QMessageBox.StandardButtons( \
                            QMessageBox.Cancel | \
                            QMessageBox.Discard | \
                            QMessageBox.Save ),
                        QMessageBox.Save )
            if res == QMessageBox.Save:
                if self.__onSave() != True:
                    # Failed to save
                    return
            if res == QMessageBox.Cancel:
                return
            wasDiscard = res == QMessageBox.Discard

        # Here:
        # - the user decided to discard changes
        # - the changes were saved successfully
        # - there were no changes

        if not wasDiscard:
            self.__updateFilePosition( index )

        del self.widgets[ index ]
        self.removeTab( index )
        if len( self.widgets ) == 0:
            self._tabBar.setTabsClosable( False )
            self.addTab( self.__welcomeWidget, getFileIcon( HTMLFileType ),
                         self.__welcomeWidget.getShortName() )
            self.activateTab( len( self.widgets ) - 1 )
            self.gotoWidget.hide()
            self.findWidget.hide()
            self.replaceWidget.hide()
        self.__updateControls()
        return

    def __updateFilePosition( self, index ):
        " Updates the file position of a file which is loaded to the given tab "

        if self.widgets[ index ].getType() == \
            MainWindowTabWidgetBase.PlainTextEditor:
            # Save the current cursor position
            editor = self.widgets[ index ].getEditor()
            line, pos = editor.getCursorPosition()
            Settings().filePositions.updatePosition( \
                            self.widgets[ index ].getFileName(),
                            line, pos,
                            editor.firstVisibleLine() )
            Settings().filePositions.save()
        return

    def createNavigationButtons( self ):
        " Creates widgets navigation button at the top corners "

        rightCornerWidget = QWidget( self )
        rightCornerWidgetLayout = QHBoxLayout( rightCornerWidget )
        rightCornerWidgetLayout.setMargin( 0 )
        rightCornerWidgetLayout.setSpacing( 0 )

        self.__navigationMenu = QMenu( self )
        self.connect( self.__navigationMenu, SIGNAL( "aboutToShow()" ),
                      self.__showNavigationMenu )
        self.connect( self.__navigationMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__navigationMenuTriggered )

        newTabButton = QToolButton( self )
        newTabButton.setIcon( PixmapCache().getIcon( "newfiletab.png" ) )
        newTabButton.setToolTip( "New tab (Ctrl+T)" )
        newTabButton.setEnabled( True )
        newTabButton.setShortcut( "Ctrl+T" )
        self.connect( newTabButton, SIGNAL( 'clicked()' ), self.newTabClicked )
        rightCornerWidgetLayout.addWidget( newTabButton )
        self.navigationButton = QToolButton( self )
        self.navigationButton.setIcon( \
                PixmapCache().getIcon( "1downarrow.png" ) )
        self.navigationButton.setToolTip( "Show a navigation menu" )
        self.navigationButton.setPopupMode( QToolButton.InstantPopup )
        self.navigationButton.setMenu( self.__navigationMenu )
        self.navigationButton.setEnabled( False )
        rightCornerWidgetLayout.addWidget( self.navigationButton )

        self.setCornerWidget( rightCornerWidget, Qt.TopRightCorner )


        self.__historyMenu = QMenu( self )
        self.connect( self.__historyMenu, SIGNAL( "aboutToShow()" ),
                      self.__showHistoryMenu )
        self.connect( self.__historyMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__historyMenuTriggered )

        leftCornerWidget = QWidget( self )
        leftCornerWidgetLayout = QHBoxLayout( leftCornerWidget )
        leftCornerWidgetLayout.setMargin( 0 )
        leftCornerWidgetLayout.setSpacing( 0 )
        self.historyBackButton = QToolButton( self )
        self.historyBackButton.setIcon( \
                PixmapCache().getIcon( "1leftarrow.png" ) )
        self.historyBackButton.setToolTip( "Back" )
        self.historyBackButton.setShortcut( "Alt+Left" )
        self.historyBackButton.setPopupMode( QToolButton.DelayedPopup )
        self.historyBackButton.setMenu( self.__historyMenu )
        self.historyBackButton.setEnabled( False )
        leftCornerWidgetLayout.addWidget( self.historyBackButton )
        self.historyFwdButton = QToolButton( self )
        self.historyFwdButton.setIcon( \
                PixmapCache().getIcon( "1rightarrow.png" ) )
        self.historyFwdButton.setToolTip( "Forward" )
        self.historyFwdButton.setShortcut( "Alt+Right" )
        self.historyFwdButton.setEnabled( False )
        leftCornerWidgetLayout.addWidget( self.historyFwdButton )

        self.setCornerWidget( leftCornerWidget, Qt.TopLeftCorner )

        return

    def __showNavigationMenu( self ):
        " Shows the navigation button menu "

        self.__navigationMenu.clear()

        items = []
        for index in range( self.count() ):
            items.append( [ self.tabIcon( index ), self.tabText( index ),
                            index ] )

        items.sort( key = lambda c: c[ 1 ] )
        for item in items:
            act = self.__navigationMenu.addAction( item[ 0 ], item[ 1 ] )
            index = item[ 2 ]
            act.setData( QVariant( index ) )
            if self.currentIndex() == index:
                font = act.font()
                font.setBold( True )
                act.setFont( font )
        return

    def __navigationMenuTriggered( self, act ):
        " Handles the navigation button menu selection "

        index, isOK = act.data().toInt()
        if isOK:
            self.setCurrentIndex( index )
        return

    def __currentChanged( self, index ):
        " Handles the currentChanged signal "
        self._memorizeLastIndex( index )
        self.__updateStatusBar()

        self.gotoWidget.updateStatus()
        self.findWidget.updateStatus()
        self.replaceWidget.updateStatus()
        return

    def __onHelp( self ):
        " Triggered when F1 is received "
        shortName = self.__helpWidget.getShortName()
        # Check if it is already opened
        for index in range( len( self.widgets ) ):
            if self.widgets[ index ].getShortName() == shortName and \
               self.widgets[ index ].getType() == \
                    MainWindowTabWidgetBase.HTMLViewer:
                # Found
                self.activateTab( index )
                return
        # Not found
        if len( self.widgets ) == 0:
            # It is the only welcome widget on the screen
            self.removeTab( 0 )
            self._tabBar.setTabsClosable( True )
        self.widgets.append( self.__helpWidget )
        self.addTab( self.__helpWidget, getFileIcon( HTMLFileType ), shortName )
        self.activateTab( len( self.widgets ) - 1 )
        return

    @staticmethod
    def getFileDocstring( fileName ):
        " Provides the file docstring "

        if detectFileType( fileName ) not in [ PythonFileType,
                                               Python3FileType ]:
            return ""

        try:
            if GlobalData().project.isProjectFile( fileName ):
                infoSrc = GlobalData().project.briefModinfoCache
            else:
                infoSrc = GlobalData().briefModinfoCache
            info = infoSrc.get( fileName )
            return info.docstring
        except:
            return ""

    def openPixmapFile( self, fileName ):
        " Shows the required picture "

        try:
            # Check if the file is already opened
            for index in range( len( self.widgets ) ):
                if self.widgets[ index ].getFileName() == fileName:
                    # Found
                    self.activateTab( index )
                    return True
            # Not found - create a new one
            newWidget = PixmapTabWidget()
            newWidget.loadFromFile( fileName )

            if len( self.widgets ) == 0:
                # It is the only welcome widget on the screen
                self.removeTab( 0 )
                self._tabBar.setTabsClosable( True )

            self.widgets.append( newWidget )
            self.addTab( newWidget, getFileIcon( PixmapFileType ),
                         newWidget.getShortName() )
            self.activateTab( len( self.widgets ) - 1 )
            self.__updateControls()
            self.__updateStatusBar()
            newWidget.setFocus()
        except Exception, exc:
            logging.error( str( exc ) )
            return False
        return True

    def openFile( self, fileName, lineNo ):
        " Opens the required file "
        try:
            # Check if the file is already opened
            for index in range( len( self.widgets ) ):
                if self.widgets[ index ].getFileName() == fileName:
                    # Found
                    self.activateTab( index )
                    if lineNo > 0:
                        self.widgets[ index ].getEditor().gotoLine( lineNo )
                    return True
            # Not found - create a new one
            newWidget = TextEditorTabWidget()
            editor = newWidget.getEditor()
            editor.readFile( fileName )

            newWidget.setFileName( fileName )
            editor.setModified( False )
            fileType = detectFileType( newWidget.getShortName() )

            # Read only
            if lineNo > 0:
                editor.gotoLine( lineNo )
            else:
                # Restore the last position
                line, pos, firstVisible = Settings().filePositions.getPosition( fileName )
                if line != -1:
                    editor.setCursorPosition( line, pos )

                    # By some reasons Scintilla scrolls horizontally, so
                    # get it back
                    editor.setHScrollOffset( 0 )
                    editor.ensureLineVisible( firstVisible )
                    currentLine = editor.firstVisibleLine()
                    editor.scrollVertical( firstVisible - currentLine )

            if len( self.widgets ) == 0:
                # It is the only welcome widget on the screen
                self.removeTab( 0 )
                self._tabBar.setTabsClosable( True )

            # Bind a lexer
            editor.bindLexer( newWidget.getFileName(), fileType )

            self.widgets.append( newWidget )
            self.addTab( newWidget, getFileIcon( fileType ),
                         newWidget.getShortName() )
            self.activateTab( len( self.widgets ) - 1 )
            self.setTabToolTip( len( self.widgets ) - 1,
                                self.getFileDocstring( fileName ) )
            self.__updateControls()
            self.__connectEditorWidget( newWidget )
            self.__updateStatusBar()
            editor.setFocus()
            newWidget.updateStatus()

        except Exception, exc:
            logging.error( str( exc ) )
            return False
        return True

    def __onOpen( self ):
        " Triggered when Ctrl+O received "

        dialog = QFileDialog( self, 'Open file' )
        dialog.setFileMode( QFileDialog.ExistingFile )
        projectFile = GlobalData().project.fileName
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        if projectFile != "":
            # Project is loaded
            dialog.setDirectory( os.path.dirname( projectFile ) )
            dirs = GlobalData().project.getProjectDirs()
            for item in dirs:
                urls.append( QUrl.fromLocalFile( item ) )
        else:
            # There is no project loaded
            dialog.setDirectory( QDir.currentPath() )
        dialog.setSidebarUrls( urls )

        if dialog.exec_() != QDialog.Accepted:
            return

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath( str( fileNames[0] ) )

        self.openFile( fileName, -1 )
        return

    def __onSave( self ):
        " Triggered when Ctrl+S is received "
        if len( self.widgets ) == 0:
            return True
        currentWidget = self.widgets[ self.currentIndex() ]
        if currentWidget.getType() != MainWindowTabWidgetBase.PlainTextEditor:
            return True
        editor = currentWidget.getEditor()
        if not editor.isModified() and currentWidget.getFileName() != "":
            return True

        # Now it can be a new file or a modified one
        if currentWidget.getFileName() != "":
            # Existed one - just save
            fileName = currentWidget.getFileName()
            if editor.writeFile( fileName ):
                editor.setModified( False )
                self.setTabToolTip( self.currentIndex(),
                                    self.getFileDocstring( fileName ) )
                self.emit( SIGNAL( 'fileUpdated' ), fileName,
                           currentWidget.getUUID() )
                return True
        else:
            # This is the new one - call Save As
            return self.__onSaveAs()
        return False

    def __onSaveAs( self ):
        " Triggered when Ctrl+Shift+S is received "
        if len( self.widgets ) == 0:
            return True
        currentWidget = self.widgets[ self.currentIndex() ]
        if currentWidget.getType() != MainWindowTabWidgetBase.PlainTextEditor:
            return True

        dialog = QFileDialog( self, 'Save as' )
        dialog.setFileMode( QFileDialog.AnyFile )
        dialog.setLabelText( QFileDialog.Accept, "Save" )
        projectFile = GlobalData().project.fileName
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        if projectFile != "":
            # Project is loaded
            dirs = GlobalData().project.getProjectDirs()
            for item in dirs:
                urls.append( QUrl.fromLocalFile( item ) )
        dialog.setSidebarUrls( urls )

        if currentWidget.getFileName() != "":
            dialog.setDirectory( os.path.dirname( currentWidget.getFileName() ) )
            dialog.selectFile( os.path.basename( currentWidget.getFileName() ) )
        else:
            dialog.setDirectory( QDir.currentPath() )
            dialog.selectFile( currentWidget.getShortName() )

        dialog.setOption( QFileDialog.DontConfirmOverwrite, False )
        if dialog.exec_() != QDialog.Accepted:
            return False

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath( str( fileNames[0] ) )

        if os.path.isdir( fileName ):
            logging.error( "A file must be selected" )
            return False

        # Check permissions to write into the file or to a directory
        if os.path.exists( fileName ):
            # Check write permissions for the file
            if not os.access( fileName, os.W_OK ):
                logging.error( "There is no write permissions for " + fileName )
                return False
        else:
            # Check write permissions to the directory
            dirName = os.path.dirname( fileName )
            if not os.access( dirName, os.W_OK ):
                logging.error( "There is no write permissions for the " \
                               "directory " + dirName )
                return False

        if os.path.exists( fileName ) and fileName != currentWidget.getFileName():
            res = QMessageBox.warning( \
                self, "Save File",
                "<p>The file <b>" + fileName + "</b> already exists.</p>",
                QMessageBox.StandardButtons( QMessageBox.Abort | QMessageBox.Save ),
                QMessageBox.Abort )
            if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                return False

        oldType = detectFileType( currentWidget.getShortName() )

        existedBefore = os.path.exists( fileName )

        # OK, the file name was properly selected
        if currentWidget.getEditor().writeFile( fileName ):
            currentWidget.setFileName( fileName )
            currentWidget.getEditor().setModified( False )
            self.setTabToolTip( self.currentIndex(),
                                self.getFileDocstring( fileName ) )
            newType = detectFileType( currentWidget.getShortName() )
            if newType != oldType:
                self.setTabIcon( self.currentIndex(), getFileIcon( newType ) )
                currentWidget.getEditor().bindLexer( \
                    currentWidget.getFileName(), newType )
            if existedBefore:
                self.emit( SIGNAL( 'fileUpdated' ), fileName,
                           currentWidget.getUUID() )
            else:
                self.emit( SIGNAL( 'bufferSavedAs' ), fileName,
                           currentWidget.getUUID() )
            currentWidget.updateStatus()
            return True

        return False

    def __onFind( self ):
        " Triggered when Ctrl+F is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        self.replaceWidget.hide()
        self.gotoWidget.hide()
        self.findWidget.show( self.currentWidget().getEditor().getSearchText() )
        return

    def __onReplace( self ):
        " Triggered when Ctrl+R is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        self.findWidget.hide()
        self.gotoWidget.hide()
        self.replaceWidget.show()
        self.replaceWidget.show( self.currentWidget().\
                                 getEditor().getSearchText() )
        return

    def __onGoto( self ):
        " Triggered when Ctrl+G is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        self.replaceWidget.hide()
        self.findWidget.hide()
        self.gotoWidget.show()
        self.gotoWidget.setFocus()
        return

    def findNext( self ):
        " triggered when F3 is received "
        self.findWidget.onNext()
        return

    def findPrev( self ):
        "Triggered when Shift+F3 is received "
        self.findWidget.onPrev()
        return

    def __showHistoryMenu( self ):
        " Shows the history button menu "
        self.__historyMenu.clear()
        for index in range( len( self.history ) ):
            act = self.__historyMenu.addAction( self.history[ index ][ 0 ],
                                                self.history[ index ][ 2 ] )
            act.setData( QVariant( index ) )
            if index == self.currentHistoryIndex:
                font = act.font()
                font.setBold( True )
                act.setFont( font )
        return

    def __historyMenuTriggered( self, act ):
        " Handles the history menu selection "

        index, isOK = act.data().toInt()
        if isOK:
            pass
        return

    def __connectEditorWidget( self, editorWidget ):
        " Connects the editor's signals "

        editor = editorWidget.getEditor()
        self.connect( editor, SIGNAL( 'modificationChanged(bool)' ),
                      self.__modificationChanged )
        self.connect( editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__cursorPositionChanged )
        self.connect( editor, SIGNAL( 'copyAvailable(bool)' ),
                      self.findWidget.copyAvailable )
        self.connect( editor, SIGNAL( 'copyAvailable(bool)' ),
                      self.replaceWidget.copyAvailable )
        self.connect( editor, SIGNAL( 'ESCPressed' ),
                      self.__onESC )

        self.connect( editorWidget, SIGNAL( 'TextEditorZoom' ),
                      self.__onZoom )
        return

    def __modificationChanged( self, modified ):
        " Triggered when the file is changed "
        index = self.currentIndex()
        if modified:
            self.setTabText( index,
                             self.widgets[ index ].getShortName() + ", +" )
        else:
            self.setTabText( index,
                             self.widgets[ index ].getShortName() )
        return

    def __onESC( self ):
        " The editor detected ESC pressed "
        if self.gotoWidget.isVisible() or self.findWidget.isVisible() or \
           self.replaceWidget.isVisible():
            self.gotoWidget.hide()
            self.findWidget.hide()
            self.replaceWidget.hide()
            return
        # No aux on screen, remove the indicators then if it is an editor
        # widget
        widget = self.currentWidget()
        if widget.getType() in [ MainWindowTabWidgetBase.PlainTextEditor ]:
            widget.getEditor().clearSearchIndicators()
        return

    def __cursorPositionChanged( self, line, pos ):
        " Triggered when the cursor position changed "
        mainWindow = self.__mainWindow
        mainWindow.sbLine.setText( "Line: " + str( line + 1 ) )
        mainWindow.sbPos.setText( "Pos: " + str( pos + 1 ) )
        return

    def __updateStatusBar( self ):
        " Updates the status bar values "
        currentWidget = self.currentWidget()

        mainWindow = self.__mainWindow
        mainWindow.sbLanguage.setText( currentWidget.getLanguage() )
        mainWindow.sbEol.setText( currentWidget.getEol() )

        cPos = currentWidget.getPos()
        if type( cPos ) == type( 0 ):
            mainWindow.sbPos.setText( "Pos: " + str( cPos + 1 ) )
        else:
            mainWindow.sbPos.setText( "Pos: " + cPos )
        cLine = currentWidget.getLine()
        if type( cLine ) == type( 0 ):
            mainWindow.sbLine.setText( "Line: " + str( cLine + 1 ) )
        else:
            mainWindow.sbLine.setText( "Line: " + cLine )
        mainWindow.sbWritable.setText( currentWidget.getRWMode() )
        mainWindow.sbEncoding.setText( currentWidget.getEncoding() )
        if currentWidget.getFileName() == "":
            mainWindow.sbFile.setPath( "File: N/A" )
        else:
            mainWindow.sbFile.setPath( "File: " + \
                                       currentWidget.getFileName() )
        return

    def getUnsavedCount( self ):
        " Provides the list of short names of what is not saved "
        count = 0
        for item in self.widgets:
            if item.isModified():
                count += 1
        return count

    def closeRequest( self ):
        """ Returns True if it could be closed.
            If it cannot then an error messages is logged, first unsaved tab
            is activated and False is returned. """
        notSaved = []
        firstIndex = -1
        for index in range( len( self.widgets ) ):
            if self.widgets[ index ].isModified():
                notSaved.append( self.widgets[ index ].getShortName() )
                if firstIndex == -1:
                    firstIndex = index
            else:
                # The tab will be closed soon, so save the file position
                self.__updateFilePosition( index )

        if len( notSaved ) == 0:
            return True

        # There are not saved files
        logging.error( "Please close or save the modified files first (" + \
                       ", ".join( notSaved ) + ")" )
        self.activateTab( firstIndex )
        return False

    def closeEvent( self, event ):
        " Handles the request to close "
        if self.closeRequest():
            event.accept()
        else:
            event.ignore()
        return

    def closeAll( self ):
        " Close all the editors tabs "
        if self.closeRequest() == False:
            return

        # It's safe to close all the tabs
        while len( self.widgets ) > 0:
            self.__onCloseRequest( 0 )
        return

    def currentWidget( self ):
        " provides the current widget "
        if len( self.widgets ) > 0:
            return self.widgets[ self.currentIndex() ]
        return self.__welcomeWidget

    def getTabsStatus( self ):
        " Provides all the tabs status and cursor positions "
        status = []

        helpShortName = self.__helpWidget.getShortName()
        curWidget = self.currentWidget()

        for item in self.widgets:
            if item.getType() == MainWindowTabWidgetBase.HTMLViewer and \
               item.getShortName() == helpShortName:
                record = "help:-1:-1:-1"
                if item == curWidget:
                    record = "*:" + record
                status.append( record )
                continue
            if item.getType() in [ MainWindowTabWidgetBase.PlainTextEditor,
                                   MainWindowTabWidgetBase.PictureViewer ]:
                fileName = item.getFileName()
                if fileName == "":
                    continue    # New, not saved yet file

                # Need to save the file name and the cursor position.
                # Modified and not saved files are saved too.
                if item.getType() == MainWindowTabWidgetBase.PlainTextEditor:
                    line, pos = item.getEditor().getCursorPosition()
                    firstLine = item.getEditor().firstVisibleLine()
                else:
                    line, pos = -1, -1
                    firstLine = -1
                if GlobalData().project.isProjectFile( fileName ):
                    prjDir = os.path.dirname( GlobalData().project.fileName )
                    relativePath = os.path.relpath( fileName, prjDir )
                    record = relativePath
                else:
                    record = fileName
                if item == curWidget:
                    record = "*:" + record
                record = record + ':' + str( firstLine ) + ':' + \
                         str( line ) + ':' + str( pos )
                status.append( record )

        return status

    def restoreTabs( self, status ):
        " Restores the tab status, i.e. load files and set cursor pos "

        # Force close all the tabs if any
        while len( self.widgets ) > 0:
            del self.widgets[ 0 ]
            self.removeTab( 0 )

        # Walk the status list
        activeIndex = -1
        for index in range( len( status ) ):
            parts = status[ index ].split( ':' )
            if len( parts ) == 5:
                activeIndex = index
                parts = parts[ 1: ]
            if len( parts ) != 4:
                logging.warning( 'Cannot restore last session tab. ' \
                                 'Unknown status format (' + \
                                 status[ index ] + ')' )
                continue
            fileName = parts[ 0 ]
            firstLine = int( parts[ 1 ] )
            line = int( parts[ 2 ] )
            pos = int( parts[ 3 ] )

            if firstLine == -1 and line == -1 and pos == -1 and \
               fileName == 'help':
                # Help widget
                if len( self.widgets ) == 0:
                    # It is the only welcome widget on the screen
                    self.removeTab( 0 )
                    self._tabBar.setTabsClosable( True )
                shortName = self.__helpWidget.getShortName()
                self.widgets.append( self.__helpWidget )
                self.addTab( self.__helpWidget, getFileIcon( HTMLFileType ),
                             shortName )
                continue

            if not fileName.startswith( os.path.sep ):
                # Relative path - build absolute
                prjDir = os.path.dirname( GlobalData().project.fileName )
                fileName = os.path.abspath( prjDir + os.path.sep + fileName )

            if not os.path.exists( fileName ):
                logging.warning( 'Cannot restore last session tab. ' \
                                 'File is not found (' + \
                                 fileName + ')' )
                continue

            # Detect file type, it could be a picture
            fileType = detectFileType( fileName )
            if fileType == PixmapFileType:
                self.openPixmapFile( fileName )
                continue

            # A usual file
            if self.openFile( fileName, line ):
                editor = self.widgets[ len( self.widgets ) - 1 ].getEditor()
                editor.setCursorPosition( line, pos )
                editor.setHScrollOffset( 0 ) # avoid unwanted scrolling
                editor.ensureLineVisible( firstLine )
                currentLine = editor.firstVisibleLine()
                editor.scrollVertical( firstLine - currentLine )

        # Switch to the last active tab
        if len( self.widgets ) == 0:
            # No one was restored - display the welcome widget
            self._tabBar.setTabsClosable( False )
            self.addTab( self.__welcomeWidget, getFileIcon( HTMLFileType ),
                         self.__welcomeWidget.getShortName() )
        if activeIndex == -1 or activeIndex >= len( self.widgets ):
            activeIndex = 0
        self.activateTab( activeIndex )
        return

    def __onZoom( self, zoomValue ):
        " Sets the zoom value for all the opened editor tabs "
        Settings().zoom = zoomValue

        for item in self.widgets:
            if item.getType() in [ MainWindowTabWidgetBase.PlainTextEditor ]:
                item.getEditor().zoomTo( zoomValue )
        return

