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


import logging, os, os.path
from PyQt4.QtCore               import Qt, SIGNAL, \
                                       QVariant, QDir, QUrl
from PyQt4.QtGui                import QTabWidget, QDialog, QMessageBox, \
                                       QWidget, QHBoxLayout, QMenu, \
                                       QToolButton, QShortcut, QFileDialog, \
                                       QApplication, QTabBar, QIcon
from utils.pixmapcache          import PixmapCache
from welcomewidget              import WelcomeWidget
from helpwidget                 import QuickHelpWidget
from editor.texteditor          import TextEditorTabWidget
from pixmapwidget               import PixmapTabWidget
from utils.fileutils            import detectFileType, PythonFileType, \
                                       Python3FileType, PixmapFileType, \
                                       DesignerFileType, LinguistFileType
from utils.compatibility        import relpath
from utils.misc                 import getNewFileTemplate
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from utils.globals              import GlobalData
from utils.settings             import Settings
from tabshistory                import TabsHistory
from diagram.importsdgmgraphics import ImportDgmTabWidget
from cdmbriefparser             import getBriefModuleInfoFromMemory
from utils.encoding             import decode



class ClickableTabBar( QTabBar ):
    " Intercepts clicking on the toolbar "

    def __init__( self, parent  = None ):
        QTabBar.__init__( self, parent )
        return

    def mousePressEvent( self, event ):
        """ Intercepts clicking on the toolbar and emits a signal.
            It is used to transfer focus to the currently active tab editor. """
        tabBarPoint = self.mapTo( self, event.pos() )
        if self.tabAt( tabBarPoint ) == self.currentIndex():
            self.emit( SIGNAL( 'currentTabClicked' ) )
        QTabBar.mousePressEvent( self, event )
        return


class EditorsManager( QTabWidget ):
    " Tab bar with editors "

    def __init__( self, parent ):

        QTabWidget.__init__( self, parent )
        self.setTabBar( ClickableTabBar() )
        self.setMovable( True )

        self.newIndex = -1
        self.newCloneIndex = -1
        self.__mainWindow = parent
        self.__navigationMenu = None
        self.__historyBackMenu = None
        self.__historyFwdMenu = None
        self.__skipHistoryUpdate = False
        self.__doNotSaveTabs = False
        self.__restoringTabs = False
        self.navigationButton = None
        self.historyBackButton = None
        self.historyFwdButton = None
        self.createNavigationButtons()

        self.__debugMode = False
        self.__debugScript = ""     # If a single script is debugged
        self.connect( self.__mainWindow, SIGNAL( 'debugModeChanged' ),
                      self.__onDebugMode )

        # Auxiliary widgets - they are created in the main window
        self.findWidget = None
        self.replaceWidget = None
        self.gotoWidget = None
        self.__lastDisplayedWasFindWidget = True

        self.history = TabsHistory( self )
        self.connect( self.history, SIGNAL( 'historyChanged' ),
                      self.__onHistoryChanged )

        self.__welcomeWidget = WelcomeWidget()
        self.addTab( self.__welcomeWidget,
                     self.__welcomeWidget.getShortName() )
        self.connect( self.__welcomeWidget, SIGNAL( 'ESCPressed' ),
                      self.__onESC )

        self.__helpWidget = QuickHelpWidget()
        self.connect( self.__helpWidget, SIGNAL( 'ESCPressed' ),
                      self.__onESC )

        self.__updateControls()
        self.__installActions()
        self.__updateStatusBar()

        self.connect( self, SIGNAL( "tabCloseRequested(int)" ),
                      self.__onCloseRequest )
        self.connect( self, SIGNAL( "currentChanged(int)" ),
                      self.__currentChanged )

        # Context menu
        self.__tabContextMenu = QMenu( self )
        self.__cloneAct = self.__tabContextMenu.addAction( \
                                    PixmapCache().getIcon( "clonetabmenu.png" ),
                                    "&Clone",
                                    self.onClone )
        self.__copyPathAct = self.__tabContextMenu.addAction( \
                                    PixmapCache().getIcon( "copytoclipboard.png" ),
                                    "Copy &path to clipboard",
                                    self.__copyTabPath )
        self.__reloadAct = self.__tabContextMenu.addAction( \
                                    PixmapCache().getIcon( "reload.png" ),
                                    "&Reload", self.onReload )
        self.__closeOtherAct = self.__tabContextMenu.addAction( \
                                    PixmapCache().getIcon( "" ),
                                    "Close oth&er tabs",
                                    self.onCloseOther )
        self.__tabContextMenu.addSeparator()
        self.__delCurrentAct = self.__tabContextMenu.addAction( \
                                    PixmapCache().getIcon( "trash.png" ),
                                    "Close and &delete from disk",
                                    self.__closeDelete )
        self.tabBar().setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.tabBar(),
                      SIGNAL( 'customContextMenuRequested(const QPoint &)' ),
                      self.__showTabContextMenu )
        self.connect( self.tabBar(), SIGNAL( 'currentTabClicked' ),
                      self.__currentTabClicked )
        return

    def __currentTabClicked( self ):
        " Triggered when the currently active tab is clicked "
        if self.count() > 0:
            self.widget( self.currentIndex() ).setFocus()
            self._updateIconAndTooltip( self.currentIndex() )
        return

    def __showTabContextMenu( self, pos ):
        " Shows a context menu if required "
        clickedIndex = self.tabBar().tabAt( pos )
        tabIndex = self.currentIndex()

        if tabIndex == clickedIndex:
            widget = self.widget( tabIndex )
            widgetType = widget.getType()
            if widgetType not in [ MainWindowTabWidgetBase.PlainTextEditor,
                                   MainWindowTabWidgetBase.PictureViewer ]:
                return

            fName = widget.getFileName()
            self.__cloneAct.setEnabled( widgetType == \
                                MainWindowTabWidgetBase.PlainTextEditor )
            self.__closeOtherAct.setEnabled( self.closeOtherAvailable() )
            self.__copyPathAct.setEnabled( fName != "" )

            if widget.getFileName() != "":
                if not widget.doesFileExist():
                    self.__reloadAct.setText( "&Reload" )
                    self.__reloadAct.setEnabled( False )
                elif widget.isDiskFileModified():
                    if widget.isModified():
                        self.__reloadAct.setText( "&Reload loosing changes" )
                    else:
                        self.__reloadAct.setText( "&Reload" )
                    self.__reloadAct.setEnabled( True )
                else:
                    self.__reloadAct.setText( "&Reload" )
                    self.__reloadAct.setEnabled( False )
            else:
                self.__reloadAct.setText( "&Reload" )
                self.__reloadAct.setEnabled( False )
            self.__tabContextMenu.popup( self.mapToGlobal( pos ) )
        return

    def closeOtherAvailable( self ):
        " True if the menu option is available "
        return self.widget( 0 ) != self.__welcomeWidget and self.count() > 1

    def __copyTabPath( self ):
        " Triggered when copy path to clipboard item is selected "
        QApplication.clipboard().setText( \
                self.widget( self.currentIndex() ).getFileName() )
        return

    def __closeDelete( self ):
        """ Triggered when the current tab is requested to be closed and the
            loaded file deleted from the disk """
        tabIndex = self.currentIndex()
        widget = self.widget( tabIndex )
        fileName = widget.getFileName()

        res = QMessageBox.warning( self, "Close tab and delete",
                "<p>Are you sure to close the tab and delete " \
                "<b>" + fileName + "</b> from the disk?</p>",
                QMessageBox.StandardButtons( QMessageBox.Cancel | \
                                             QMessageBox.Yes ),
                QMessageBox.Cancel )
        if res == QMessageBox.Cancel:
            return

        try:
            if os.path.exists( fileName ):
                os.remove( fileName )
            else:
                logging.info( "Could not find " + fileName + \
                              " on the disk. Ignoring and closing tab." )
        except Exception, exc:
            logging.error( str( exc ) )
            return

        # Finally, close the tab
        self.__onCloseRequest( tabIndex, True )
        return

    def onClone( self ):
        " Triggered when a tab is requested for cloning "
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType != MainWindowTabWidgetBase.PlainTextEditor:
            return

        editor = widget.getEditor()
        firstVisible = editor.firstVisibleLine()
        line, pos = editor.getCursorPosition()

        # Create a new tab
        self.newTabClicked( editor.text(),
                            self.getNewCloneName( widget.getShortName() ) )

        # Put the cursor to the exact same position as it was in the cloned tab
        newWidget = self.currentWidget()
        self.__restorePosition( newWidget.getEditor(), line, pos, firstVisible )
        return

    def onCloseOther( self ):
        " Triggered when all other tabs are requested to be closed "
        notSaved = []
        toClose = []
        for index in xrange( self.count() ):
            if index == self.currentIndex():
                continue
            if self.widget( index ).isModified():
                notSaved.append( self.widget( index ).getShortName() )
            else:
                # The tab will be closed soon, so save the file position
                self.__updateFilePosition( index )
                toClose.insert( 0, index )

        if len( notSaved ) > 0:
            # There are not saved files
            logging.error( "Please close or save the modified files " \
                           "explicitly (" + ", ".join( notSaved ) + ")" )

        for index in toClose:
            self.__onCloseRequest( index )
        return

    def __installActions( self ):
        " Installs various key combinations handlers "
        findAction = QShortcut( 'Ctrl+F', self )
        self.connect( findAction, SIGNAL( 'activated()' ),
                      self.onFind )
        hiddenFindAction = QShortcut( 'Ctrl+F3', self )
        self.connect( hiddenFindAction, SIGNAL( "activated()" ),
                      self.onHiddenFind )
        replaceAction = QShortcut( 'Ctrl+R', self )
        self.connect( replaceAction, SIGNAL( 'activated()' ),
                      self.onReplace )
        closeTabAction = QShortcut( 'Ctrl+F4', self )
        self.connect( closeTabAction, SIGNAL( 'activated()' ),
                      self.onCloseTab )
        nextTabAction = QShortcut( 'Ctrl+PgUp', self )
        self.connect( nextTabAction, SIGNAL( 'activated()' ),
                      self.__onNextTab )
        flipTabAction = QShortcut( 'Ctrl+Tab', self )
        self.connect( flipTabAction, SIGNAL( 'activated()' ),
                      self.__onFlipTab )
        prevTabAction = QShortcut( 'Ctrl+PgDown', self )
        self.connect( prevTabAction, SIGNAL( 'activated()' ),
                      self.__onPrevTab )
        gotoAction = QShortcut( 'Ctrl+G', self )
        self.connect( gotoAction, SIGNAL( 'activated()' ),
                      self.onGoto )
        return

    def registerAuxWidgets( self, find, replace, goto ):
        " Memorizes references to the auxiliary widgets "
        self.findWidget = find
        self.replaceWidget = replace
        self.gotoWidget = goto
        return

    def getNewName( self ):
        " Provides a dummy name for the new tab file "
        self.newIndex += 1
        return "unnamed" + str( self.newIndex ) + ".py"

    def getNewCloneName( self, shortName ):
        " Provides a new name for a cloned file "
        self.newCloneIndex += 1
        if '.' in shortName:
            parts = shortName.split( '.' )
            name = '.'.join( parts[ 0 : len( parts ) - 1 ] )
            ext = parts[ -1 ]
            return name + "-clone" + str( self.newCloneIndex ) + "." + ext

        # No '.' in the name
        return shortName + "-clone" + str( self.newCloneIndex )

    def activateTab( self, index ):
        " Activates the given tab "
        self.setCurrentIndex( index )
        self.currentWidget().setFocus()
        return

    def __onNextTab( self ):
        " Triggers when Ctrl+PgUp is received "
        count = self.count()
        if count > 1:
            newIndex = self.currentIndex() + 1
            if newIndex >= count:
                newIndex = 0
            self.activateTab( newIndex )
        return

    def __onPrevTab( self ):
        " triggers when Ctrl+PgDown is received "
        count = self.count()
        if count > 1:
            newIndex = self.currentIndex() - 1
            if newIndex < 0:
                newIndex = count - 1
            self.activateTab( newIndex )
        return

    def newTabClicked( self, initialContent = None, shortName = None ):
        " new tab click handler "

        if self.widget( 0 ) == self.__welcomeWidget:
            # It is the only welcome widget on the screen
            self.removeTab( 0 )
            self.setTabsClosable( True )

        newWidget = TextEditorTabWidget( self )
        self.connect( newWidget, SIGNAL( 'ReloadRequest' ),
                      self.onReload )
        self.connect( newWidget, SIGNAL( 'ReloadAllNonModifiedRequest' ),
                      self.onReloadAllNonModified )
        editor = newWidget.getEditor()
        if shortName is None:
            newWidget.setShortName( self.getNewName() )
        else:
            newWidget.setShortName( shortName )

        fileType = detectFileType( newWidget.getShortName() )

        if initialContent is None:
            # Load a template content if available
            initialContent = getNewFileTemplate()
            if initialContent != "":
                editor.setText( initialContent )
                lineNo = editor.lines()
                self.__restorePosition( editor, lineNo - 1,
                                        editor.lineLength( lineNo - 1 ), -1 )
                editor.ensureLineVisible( lineNo - 1 )
        else:
            editor.setText( initialContent )
        editor.setModified( False )

        # Bind a lexer
        editor.bindLexer( newWidget.getShortName(), fileType )

        self.insertTab( 0, newWidget, newWidget.getShortName() )
        self.activateTab( 0 )

        self.__updateControls()
        self.__connectEditorWidget( newWidget )
        self.__updateStatusBar()
        editor.setFocus()
        newWidget.updateStatus()
        self.setWidgetDebugMode( newWidget )
        return

    def __updateControls( self ):
        " Updates the navigation buttons status "
        self.navigationButton.setEnabled( self.widget( 0 ) != \
                                          self.__welcomeWidget )
        return

    def __onHistoryChanged( self ):
        " historyChanged signal handler "
        self.historyBackButton.setEnabled( self.history.backAvailable() )
        self.historyFwdButton.setEnabled( self.history.forwardAvailable() )
        return

    def onCloseTab( self ):
        " Triggered when Ctrl+F4 is received "
        if self.widget( 0 ) != self.__welcomeWidget:
            self.__onCloseRequest( self.currentIndex() )
        return

    def isTabClosable( self ):
        " Returns True if the current TAB is closable "
        return self.widget( 0 ) != self.__welcomeWidget

    def __onCloseRequest( self, index, enforced = False ):
        " Close tab handler "

        wasDiscard = False
        if self.widget( index ).isModified() and enforced == False:
            # Ask the user if the changes should be discarded
            self.activateTab( index )
            res = QMessageBox.warning( \
                        self.widget( index ),
                        "Unsaved changes",
                        "<b>This document has been modified.</b>" \
                        "<p>Do you want to save changes?</p>",
                        QMessageBox.StandardButtons( \
                            QMessageBox.Cancel | \
                            QMessageBox.Discard | \
                            QMessageBox.Save ),
                        QMessageBox.Save )
            if res == QMessageBox.Save:
                if self.onSave() != True:
                    # Failed to save
                    return
            if res == QMessageBox.Cancel:
                return
            wasDiscard = res == QMessageBox.Discard

        # Here:
        # - the user decided to discard changes
        # - the changes were saved successfully
        # - there were no changes

        closingUUID = self.widget( index ).getUUID()
        if not wasDiscard and not enforced:
            self.__updateFilePosition( index )

        self.__skipHistoryUpdate = True
        self.removeTab( index )

        if self.count() == 0:
            self.setTabsClosable( False )
            self.addTab( self.__welcomeWidget,
                         self.__welcomeWidget.getShortName() )
            self.__welcomeWidget.setFocus()
            self.gotoWidget.hide()
            self.findWidget.hide()
            self.replaceWidget.hide()
            self.history.clear()
        else:
            # Need to identify a tab for displaying
            self.history.tabClosed( closingUUID )
            if self.history.getCurrentIndex() == -1:
                # There is nothing in the history yet
                self.history.addCurrent()
            else:
                self.__activateHistoryTab()

        self.__skipHistoryUpdate = False
        self.__updateControls()
        self.saveTabsStatus()
        self.emit( SIGNAL( 'tabClosed' ), closingUUID )
        return

    def __updateFilePosition( self, index ):
        " Updates the file position of a file which is loaded to the given tab "

        if self.widget( index ).getType() == \
            MainWindowTabWidgetBase.PlainTextEditor:
            # Save the current cursor position
            editor = self.widget( index ).getEditor()
            line, pos = editor.getCursorPosition()
            Settings().filePositions.updatePosition( \
                            self.widget( index ).getFileName(),
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
        newTabButton.setToolTip( "New file (Ctrl+N)" )
        newTabButton.setEnabled( True )
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


        self.__historyBackMenu = QMenu( self )
        self.connect( self.__historyBackMenu, SIGNAL( "aboutToShow()" ),
                      self.__showHistoryBackMenu )
        self.connect( self.__historyBackMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__historyMenuTriggered )

        self.__historyFwdMenu = QMenu( self )
        self.connect( self.__historyFwdMenu, SIGNAL( "aboutToShow()" ),
                      self.__showHistoryFwdMenu )
        self.connect( self.__historyFwdMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__historyMenuTriggered )

        leftCornerWidget = QWidget( self )
        leftCornerWidgetLayout = QHBoxLayout( leftCornerWidget )
        leftCornerWidgetLayout.setMargin( 0 )
        leftCornerWidgetLayout.setSpacing( 0 )
        self.historyBackButton = QToolButton( self )
        self.historyBackButton.setIcon( \
                PixmapCache().getIcon( "1leftarrow.png" ) )
        self.historyBackButton.setToolTip( "Back (Alt+PgDown)" )
        self.historyBackButton.setShortcut( "Alt+PgDown" )
        self.historyBackButton.setPopupMode( QToolButton.DelayedPopup )
        self.historyBackButton.setMenu( self.__historyBackMenu )
        self.historyBackButton.setEnabled( False )
        self.connect( self.historyBackButton, SIGNAL( 'clicked()' ),
                      self.historyBackClicked )
        leftCornerWidgetLayout.addWidget( self.historyBackButton )
        self.historyFwdButton = QToolButton( self )
        self.historyFwdButton.setIcon( \
                PixmapCache().getIcon( "1rightarrow.png" ) )
        self.historyFwdButton.setToolTip( "Forward (Alt+PgUp)" )
        self.historyFwdButton.setShortcut( "Alt+PgUp" )
        self.historyFwdButton.setPopupMode( QToolButton.DelayedPopup )
        self.historyFwdButton.setMenu( self.__historyFwdMenu )
        self.historyFwdButton.setEnabled( False )
        self.connect( self.historyFwdButton, SIGNAL( 'clicked()' ),
                      self.historyForwardClicked )
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
        if not isOK or self.currentIndex() == index:
            return

        if index != 0:
            # Memorize the tab attributes
            tooltip = self.tabToolTip( index )
            text = self.tabText( index )
            icon = self.tabIcon( index )
            whatsThis = self.tabWhatsThis( index )
            widget = self.widget( index )

            # Remove the tab from the old position
            self.removeTab( index )

            # Insert the tab at position 0
            self.insertTab( 0, widget, icon, text )
            self.setTabToolTip( 0, tooltip )
            self.setTabWhatsThis( 0, whatsThis )

        self.activateTab( 0 )
        return

    def __currentChanged( self, index ):
        " Handles the currentChanged signal "
        if index == -1:
            return

        self._updateIconAndTooltip( self.currentIndex() )
        self.__updateStatusBar()

        self.gotoWidget.updateStatus()
        self.findWidget.updateStatus()
        self.replaceWidget.updateStatus()

        self.currentWidget().setFocus()

        # Update history
        if not self.__skipHistoryUpdate:
            if self.widget( 0 ) != self.__welcomeWidget:
                # No need to update history when there is only welcome widget
                self.history.updateForCurrentIndex()
                self.history.addCurrent()

        if self.currentWidget().doesFileExist():
            if self.currentWidget().isDiskFileModified():
                if not self.currentWidget().getReloadDialogShown():
                    self.currentWidget().showOutsideChangesBar( \
                                    self.__countDiskModifiedUnchanged() > 1 )
                    # Just in case check the other tabs
                    self.checkOutsideFileChanges()
        return

    def onHelp( self ):
        " Triggered when F1 is received "
        shortName = self.__helpWidget.getShortName()
        # Check if it is already opened
        for index in range( self.count() ):
            if self.widget( index ).getShortName() == shortName and \
               self.widget( index ).getType() == \
                    MainWindowTabWidgetBase.HTMLViewer:
                # Found
                self.activateTab( index )
                return
        # Not found
        if self.widget( 0 ) == self.__welcomeWidget:
            # It is the only welcome widget on the screen
            self.removeTab( 0 )
            self.setTabsClosable( True )
        self.addTab( self.__helpWidget, shortName )
        self.activateTab( self.count() - 1 )
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
            if info.docstring is not None:
                return info.docstring.text
            return ""
        except:
            return ""

    def _updateIconAndTooltip( self, widgetIndex, fileType = None ):
        " Updates the current tab icon and tooltip after the file is saved "
        fileName = self.widget( widgetIndex ).getFileName()

        if fileType is None:
            fileType = detectFileType( fileName )

        if os.path.isabs( fileName ):
            # It makes sense to test if a file disappeared or modified
            if not self.widget( widgetIndex ).doesFileExist():
                self.setTabToolTip( widgetIndex,
                                    "File does not exist on the disk" )
                self.setTabIcon( widgetIndex,
                                 PixmapCache().getIcon( 'disappearedfile.png' ) )
                return
            if self.widget( widgetIndex ).isDiskFileModified():
                self.setTabToolTip( widgetIndex,
                                    "The file has been modified outside codimension" )
                self.setTabIcon( widgetIndex,
                                 PixmapCache().getIcon( 'modifiedfile.png' ) )
                return

        if fileType not in [ PythonFileType, Python3FileType ]:
            self.setTabIcon( widgetIndex, QIcon() )
            self.setTabToolTip( widgetIndex,
                                self.widget( widgetIndex ).getTooltip() )
            return

        try:
            if GlobalData().project.isProjectFile( fileName ):
                infoSrc = GlobalData().project.briefModinfoCache
            else:
                infoSrc = GlobalData().briefModinfoCache
            info = infoSrc.get( fileName )

            if len( info.errors ) + len( info.lexerErrors ) > 0:
                self.setTabIcon( widgetIndex,
                                 PixmapCache().getIcon( 'filepythonbroken.png' ) )
                self.setTabToolTip( widgetIndex, "File has parsing errors" )
            else:
                self.setTabIcon( widgetIndex, QIcon() )

                if info.docstring is not None:
                    self.setTabToolTip( widgetIndex, info.docstring.text )
                else:
                    self.setTabToolTip( widgetIndex, "" )
        except:
            self.setTabToolTip( widgetIndex, "" )
            self.setTabIcon( widgetIndex,
                             PixmapCache().getIcon( 'filepythonbroken.png' ) )
        return

    def openPixmapFile( self, fileName ):
        " Shows the required picture "

        try:
            # Check if the file is already opened
            for index in range( self.count() ):
                if self.widget( index ).getFileName() == fileName:
                    # Found
                    self.activateTab( index )
                    return True
            # Not found - create a new one
            newWidget = PixmapTabWidget()
            self.connect( newWidget, SIGNAL( 'ESCPressed' ),
                          self.__onESC )
            self.connect( newWidget, SIGNAL( 'ReloadRequest' ),
                          self.onReload )
            self.connect( newWidget, SIGNAL( 'ReloadAllNonModifiedRequest' ),
                          self.onReloadAllNonModified )

            newWidget.loadFromFile( fileName )

            if self.widget( 0 ) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab( 0 )
                self.setTabsClosable( True )

            self.insertTab( 0, newWidget, newWidget.getShortName() )
            self.activateTab( 0 )
            self.__updateControls()
            self.__updateStatusBar()
            newWidget.setFocus()
            self.saveTabsStatus()
            if self.__restoringTabs == False:
                GlobalData().project.addRecentFile( fileName )
            self.setWidgetDebugMode( newWidget )
        except Exception, exc:
            logging.error( str( exc ) )
            return False
        return True

    def openDiagram( self, scene, tooltip ):
        " Opens a tab with a graphics scene on it "

        try:
            newWidget = ImportDgmTabWidget()
            self.connect( newWidget, SIGNAL( 'ESCPressed' ),
                          self.__onESC )
            newWidget.setScene( scene )

            if self.widget( 0 ) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab( 0 )
                self.setTabsClosable( True )

            self.insertTab( 0, newWidget, newWidget.getShortName() )
            if tooltip != "":
                self.setTabToolTip( 0, tooltip )
                newWidget.setTooltip( tooltip )
            self.activateTab( 0 )
            self.__updateControls()
            self.__updateStatusBar()
            newWidget.setFocus()
            self.saveTabsStatus()

        except Exception, exc:
            logging.error( str( exc ) )
            return False
        return True

    def jumpToLine( self, lineNo ):
        " Jumps to the given line within the current buffer "

        # Used when rope works with unsaved buffer and a definition line is
        # given without a resource - we need to jump within the buffer
        self.history.updateForCurrentIndex()
        editor = self.currentWidget().getEditor()
        if editor.isLineVisible( lineNo - 1 ):
            firstVisible = 0
        else:
            firstVisible = lineNo - 2
            if firstVisible <= 0:
                firstVisible = 1

        self.__restorePosition( editor, lineNo - 1, 0, firstVisible - 1 )
        self.history.addCurrent()
        self.currentWidget().setFocus()
        return

    def openFile( self, fileName, lineNo ):
        " Opens the required file "
        try:
            # Check if the file is already opened
            for index in range( self.count() ):
                if self.widget( index ).getFileName() == fileName:
                    # Found
                    if self.currentIndex() == index:
                        self.history.updateForCurrentIndex()
                    if lineNo > 0:
                        editor = self.widget( index ).getEditor()
                        if self.currentIndex() == index and \
                           editor.isLineVisible( lineNo - 1 ):
                            editor.setCursorPosition( lineNo - 1, 0 )
                            editor.setHScrollOffset( 0 ) # avoid unwanted scrolling
                        else:
                            firstVisible = lineNo - 2
                            if firstVisible <= 0:
                                firstVisible = 1
                            self.__restorePosition( editor,
                                                    lineNo - 1, 0, firstVisible - 1 )
                    self.activateTab( index )
                    if self.currentIndex() == index:
                        self.history.addCurrent()
                    return True

            # Not found - create a new one
            newWidget = TextEditorTabWidget( self )
            self.connect( newWidget, SIGNAL( 'ReloadRequest' ),
                          self.onReload )
            self.connect( newWidget, SIGNAL( 'ReloadAllNonModifiedRequest' ),
                          self.onReloadAllNonModified )
            editor = newWidget.getEditor()
            newWidget.readFile( fileName )

            newWidget.setFileName( fileName )
            editor.setModified( False )
            fileType = detectFileType( newWidget.getShortName() )

            if self.widget( 0 ) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab( 0 )
                self.setTabsClosable( True )

            # Bind a lexer
            editor.bindLexer( newWidget.getFileName(), fileType )

            self.insertTab( 0, newWidget, newWidget.getShortName() )
            self.activateTab( 0 )

            if lineNo > 0:
                # Jump to the asked line
                firstVisible = lineNo - 2
                if firstVisible <= 0:
                    firstVisible = 1
                self.__restorePosition( editor, lineNo - 1, 0, firstVisible - 1 )
            else:
                # Restore the last position
                line, pos, firstVisible = \
                            Settings().filePositions.getPosition( fileName )
                if line != -1:
                    self.__restorePosition( editor, line, pos, firstVisible )

            self._updateIconAndTooltip( self.currentIndex(), fileType )
            self.__updateControls()
            self.__connectEditorWidget( newWidget )
            self.__updateStatusBar()
            editor.setFocus()
            newWidget.updateStatus()
            self.saveTabsStatus()
            if self.__restoringTabs == False:
                GlobalData().project.addRecentFile( fileName )
            self.setWidgetDebugMode( newWidget )
        except Exception, exc:
            logging.error( str( exc ) )
            return False
        return True

    def gotoInBuffer( self, uuid, lineNo ):
        " Jumps to the given line in the current buffer if it matches uuid "
        widget = self.currentWidget()
        if widget.getUUID() != uuid:
            return
        self.history.updateForCurrentIndex()
        firstVisible = lineNo - 2
        if firstVisible <= 0:
            firstVisible = 1
        self.__restorePosition( widget.getEditor(),
                                lineNo - 1, 0, firstVisible - 1 )
        self.history.addCurrent()
        widget.setFocus()
        return

    def onSave( self, index = -1 ):
        " Triggered when Ctrl+S is received "
        if index == -1:
            widget = self.currentWidget()
            index = self.currentIndex()
        else:
            widget = self.widget( index )

        if widget.getType() != MainWindowTabWidgetBase.PlainTextEditor:
            return True

        # This is a text editor
        editor = widget.getEditor()
        fileName = widget.getFileName()
        if fileName != "":
            # This is the buffer which has the corresponding file on FS
            if widget.isDiskFileModified() and \
               widget.doesFileExist():
                if index != self.currentIndex():
                    self.activateTab( index )
                self._updateIconAndTooltip( index )
                widget.setReloadDialogShown( True )
                # The disk file was modified
                res = QMessageBox.warning( \
                    self, "Save File",
                    "<p>The file <b>" + fileName + \
                    "</b> has been changed since reading it. " \
                    "Do you really want to write into it?</p>",
                    QMessageBox.StandardButtons( QMessageBox.Abort | \
                                                QMessageBox.Save ),
                    QMessageBox.Abort )
                if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                    return False
            else:
                # The disk file is the same as we read it
                if not editor.isModified():
                    return True

            # Save the buffer into the file
            if widget.writeFile( fileName ):
                editor.setModified( False )
                self._updateIconAndTooltip( index )
                if GlobalData().project.fileName == fileName:
                    GlobalData().project.onProjectFileUpdated()
                self.emit( SIGNAL( 'fileUpdated' ), fileName,
                           widget.getUUID() )
                return True
            # Error saving the buffer
            return False

        # This is the new one - call Save As
        return self.onSaveAs( index )

    def onSaveAs( self, index = -1 ):
        " Triggered when Ctrl+Shift+S is received "
        if index == -1:
            widget = self.currentWidget()
            index = self.currentIndex()
        else:
            widget = self.widget( index )

        if widget.getType() != MainWindowTabWidgetBase.PlainTextEditor:
            return True

        if index != self.currentIndex():
            self.activateTab( index )

        dialog = QFileDialog( self, 'Save as' )
        dialog.setFileMode( QFileDialog.AnyFile )
        dialog.setLabelText( QFileDialog.Accept, "Save" )
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        project = GlobalData().project
        if project.isLoaded():
            urls.append( QUrl.fromLocalFile( project.getProjectDir() ) )
        dialog.setSidebarUrls( urls )

        if widget.getFileName() != "":
            dialog.setDirectory( os.path.dirname( widget.getFileName() ) )
            dialog.selectFile( os.path.basename( widget.getFileName() ) )
        else:
            if project.isLoaded():
                dialog.setDirectory( project.getProjectDir() )
            else:
                dialog.setDirectory( QDir.currentPath() )
            dialog.selectFile( widget.getShortName() )

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

        if self.isFileOpened( fileName ) and widget.getFileName() != fileName:
            QMessageBox.critical( self, "Save file",
                                  "<p>The file <b>" + fileName + \
                                  "</b> is opened in another tab.</p>" \
                                  "<p>Cannot save under this name." )
            return False

        if os.path.exists( fileName ) and \
           fileName != widget.getFileName():
            res = QMessageBox.warning( \
                self, "Save File",
                "<p>The file <b>" + fileName + "</b> already exists.</p>",
                QMessageBox.StandardButtons( QMessageBox.Abort | \
                                             QMessageBox.Save ),
                QMessageBox.Abort )
            if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                return False

        oldType = detectFileType( widget.getShortName() )

        existedBefore = os.path.exists( fileName )

        # OK, the file name was properly selected
        if self.__debugMode and self.__debugScript == fileName:
            logging.error( "Cannot overwrite a script which is currently debugged." )
            return False

        newType = detectFileType( fileName )
        if widget.writeFile( fileName ):
            widget.setFileName( fileName )
            widget.getEditor().setModified( False )
            self._updateIconAndTooltip( index, newType )
            if newType != oldType:
                widget.getEditor().bindLexer( \
                    widget.getFileName(), newType )

            if GlobalData().project.fileName == fileName:
                GlobalData().project.onProjectFileUpdated()

            if existedBefore:
                self.emit( SIGNAL( 'fileUpdated' ), fileName,
                           widget.getUUID() )
            else:
                self.emit( SIGNAL( 'bufferSavedAs' ), fileName,
                           widget.getUUID() )
                GlobalData().project.addRecentFile( fileName )
            widget.updateStatus()
            self.__updateStatusBar()
            self.__mainWindow.updateRunDebugButtons()
            return True

        return False

    def onFind( self ):
        " Triggered when Ctrl+F is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        if self.replaceWidget.isVisible():
            self.replaceWidget.hide()
        if self.gotoWidget.isVisible():
            self.gotoWidget.hide()

        searchText = self.currentWidget().getEditor().getSearchText()
        if self.findWidget.isHidden():
            self.findWidget.show( searchText )
        else:
            if len( searchText ) > 0:
                self.findWidget.show( searchText )
        self.findWidget.setFocus()
        self.__lastDisplayedWasFindWidget = True
        return

    def onHiddenFind( self ):
        " Triggered when Ctrl+F3 is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        searchText = str( self.currentWidget().getEditor().getSearchText() )
        if len( searchText ) > 0:
            self.findWidget.startHiddenSearch( searchText )
            self.__lastDisplayedWasFindWidget = True
        else:
            GlobalData().mainWindow.showStatusBarMessage( \
                    "No current word to start searching" )
        return

    def onReplace( self ):
        " Triggered when Ctrl+R is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        if self.findWidget.isVisible():
            self.findWidget.hide()
        if self.gotoWidget.isVisible():
            self.gotoWidget.hide()

        searchText = self.currentWidget().getEditor().getSearchText()
        if self.replaceWidget.isHidden():
            self.replaceWidget.show( searchText )
        else:
            if len( searchText ) > 0:
                self.replaceWidget.show( searchText )
        self.replaceWidget.setFocus()
        self.__lastDisplayedWasFindWidget = False
        return

    def onGoto( self ):
        " Triggered when Ctrl+G is received "
        if self.currentWidget().getType() not in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        if self.replaceWidget.isVisible():
            self.replaceWidget.hide()
        if self.findWidget.isVisible():
            self.findWidget.hide()
        if self.gotoWidget.isHidden():
            self.gotoWidget.show()
        self.gotoWidget.setFocus()
        return

    def findNext( self ):
        " triggered when F3 is received "
        if self.__lastDisplayedWasFindWidget:
            if self.findWidget.getLastSearchString() != "":
                self.findWidget.onNext()
                return
            if self.replaceWidget.getLastSearchString() != "":
                self.replaceWidget.onNext()
                return
            return  # Nothing to search for

        # The last on the screen was the replace widget
        if self.replaceWidget.getLastSearchString() != "":
            self.replaceWidget.onNext()
            return
        if self.findWidget.getLastSearchString() != "":
            self.findWidget.onNext()
            return
        return  # nothing to search for

    def findPrev( self ):
        "Triggered when Shift+F3 is received "
        if self.__lastDisplayedWasFindWidget:
            if self.findWidget.getLastSearchString() != "":
                self.findWidget.onPrev()
                return
            if self.replaceWidget.getLastSearchString() != "":
                self.replaceWidget.onPrev()
                return
            return  # Nothing to search for

        # The last on the screen was the replace widget
        if self.replaceWidget.getLastSearchString() != "":
            self.replaceWidget.onPrev()
            return
        if self.findWidget.getLastSearchString() != "":
            self.findWidget.onPrev()
            return
        return  # nothing to search for

    def __addHistoryMenuItem( self, menu, index, currentHistoryIndex ):
        " Prepares the history menu item "
        entry = self.history.getEntry( index )
        text = entry.displayName
        if entry.tabType in [ MainWindowTabWidgetBase.PlainTextEditor ]:
            text += ", " + str( entry.line + 1 ) + ":" + str( entry.pos + 1 )
        act = menu.addAction( entry.icon, text )
        act.setData( QVariant( index ) )
        if index == currentHistoryIndex:
            font = act.font()
            font.setBold( True )
            act.setFont( font )
        return

    def __showHistoryBackMenu( self ):
        " Shows the history button menu "
        self.history.updateForCurrentIndex()
        self.__historyBackMenu.clear()
        currentIndex = self.history.getCurrentIndex()

        index = 0
        while index <= currentIndex:
            self.__addHistoryMenuItem( self.__historyBackMenu,
                                       index, currentIndex )
            index += 1
        return

    def __showHistoryFwdMenu( self ):
        " Shows the history button menu "
        self.history.updateForCurrentIndex()
        self.__historyFwdMenu.clear()
        currentIndex = self.history.getCurrentIndex()
        maxIndex = self.history.getSize() - 1

        index = currentIndex
        while index <= maxIndex:
            self.__addHistoryMenuItem( self.__historyFwdMenu,
                                       index, currentIndex )
            index += 1
        return

    def __activateHistoryTab( self ):
        " Activates the tab advised by the current history entry "
        self.__skipHistoryUpdate = True
        entry = self.history.getCurrentEntry()
        index = self.getIndexByUUID( entry.uuid )
        widget = self.getWidgetByUUID( entry.uuid )
        self.activateTab( index )
        if widget.getType() in [ MainWindowTabWidgetBase.PlainTextEditor ]:
            # Need to jump to the memorized position
            editor = widget.getEditor()
            self.__restorePosition( editor, entry.line, entry.pos,
                                    entry.firstVisible )
        self.__skipHistoryUpdate = False
        return

    def historyForwardClicked( self ):
        " Back in history clicked "
        self.history.updateForCurrentIndex()
        if self.history.stepForward():
            self.__activateHistoryTab()
        return

    def historyBackClicked( self ):
        " Forward in history clicked "
        self.history.updateForCurrentIndex()
        if self.history.stepBack():
            self.__activateHistoryTab()
        return

    def __onFlipTab( self ):
        " Flip between last two tabs "
        self.history.updateForCurrentIndex()
        if self.history.flip():
            self.__activateHistoryTab()
        return

    def __historyMenuTriggered( self, act ):
        " Handles the history menu selection "
        index, isOK = act.data().toInt()
        if isOK:
            if index != self.history.getCurrentIndex():
                self.history.updateForCurrentIndex()
                self.history.setCurrentIndex( index )
                self.__activateHistoryTab()
        return

    def __connectEditorWidget( self, editorWidget ):
        " Connects the editor's signals "

        editor = editorWidget.getEditor()
        self.connect( editor, SIGNAL( 'modificationChanged(bool)' ),
                      self.__modificationChanged )
        self.connect( editor, SIGNAL( "SCEN_CHANGE()" ),
                      self.__contentChanged )
        self.connect( editor, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__cursorPositionChanged )
        self.connect( editor, SIGNAL( 'ESCPressed' ),
                      self.__onESC )

        self.connect( editorWidget, SIGNAL( 'TextEditorZoom' ),
                      self.__onZoom )
        return

    def __modificationChanged( self, modified ):
        " Triggered when the file is changed "
        index = self.currentIndex()
        currentWidget = self.currentWidget()
        if modified:
            title = Settings().modifiedFormat % currentWidget.getShortName()
            self.setTabText( index, title )
        else:
            self.setTabText( index, currentWidget.getShortName() )
        self.emit( SIGNAL( "bufferModified" ), currentWidget.getFileName(),
                                               str( currentWidget.getUUID() ) )
        return

    def __contentChanged( self ):
        " Triggered when a buffer content is changed "
        currentWidget = self.currentWidget()
        self.emit( SIGNAL( "bufferModified" ), currentWidget.getFileName(),
                                               str( currentWidget.getUUID() ) )
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
        " Provides the number of buffers which were not saved "
        return len( self.getModifiedList() )

    def closeRequest( self ):
        """ Returns True if it could be closed.
            If it cannot then an error messages is logged, first unsaved tab
            is activated and False is returned. """
        notSaved = []
        firstIndex = -1
        for index in xrange( self.count() ):
            if self.widget( index ).isModified():
                notSaved.append( self.widget( index ).getShortName() )
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
        # Hide completer if so
        curWidget = self.currentWidget()
        if curWidget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            curWidget.getEditor().hideCompleter()

        if self.closeRequest():
            event.accept()
        else:
            event.ignore()
        return

    def closeAll( self ):
        " Close all the editors tabs "
        curWidget = self.currentWidget()
        if curWidget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            curWidget.getEditor().hideCompleter()

        if self.closeRequest() == False:
            return

        # It's safe to close all the tabs
        self.__doNotSaveTabs = True
        while self.widget( 0 ) != self.__welcomeWidget:
            self.__onCloseRequest( 0 )
        self.__doNotSaveTabs = False
        return

    def saveTabsStatus( self ):
        " Saves the tabs status to project or global settings "
        if self.__doNotSaveTabs:
            return

        if GlobalData().project.isLoaded():
            GlobalData().project.setTabsStatus( self.getTabsStatus() )
        else:
            Settings().tabsStatus = self.getTabsStatus()
        return

    def getTabsStatus( self ):
        " Provides all the tabs status and cursor positions "
        if self.widget( 0 ) == self.__welcomeWidget:
            return []

        status = []
        helpShortName = self.__helpWidget.getShortName()
        curWidget = self.currentWidget()


        for index in range( self.count() ):
            item = self.widget( index )
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
                    relativePath = relpath( fileName, prjDir )
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

        self.__restoringTabs = True
        self.history.clear()

        # Force close all the tabs if any
        while self.count() > 0:
            self.removeTab( 0 )

        # Walk the status list
        activeIndex = -1
        for index in range( len( status ) - 1, -1, -1 ):
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
                if self.widget( 0 ) == self.__welcomeWidget:
                    # It is the only welcome widget on the screen
                    self.removeTab( 0 )
                    self.setTabsClosable( True )
                shortName = self.__helpWidget.getShortName()
                self.addTab( self.__helpWidget, shortName )
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
                self.__restorePosition( self.widget( 0 ).getEditor(),
                                        line, pos, firstLine )

        # Switch to the last active tab
        if self.count() == 0:
            # No one was restored - display the welcome widget
            self.setTabsClosable( False )
            self.addTab( self.__welcomeWidget,
                         self.__welcomeWidget.getShortName() )
            activeIndex = 0
            self.activateTab( activeIndex )
            self.history.clear()
            self.__restoringTabs = False
            return

        # There are restored tabs
        self.setTabsClosable( True )
        if activeIndex == -1 or activeIndex >= self.count():
            activeIndex = 0
        self.activateTab( activeIndex )
        self.history.clear()
        self.history.addCurrent()
        self.__restoringTabs = False
        return

    @staticmethod
    def __restorePosition( editor, line, pos, firstVisible ):
        """ Set the cursor to the required position and
            makes sure a certain line is visible if given """
        editor.setCursorPosition( line, pos )
        editor.setHScrollOffset( 0 ) # avoid unwanted scrolling

        if firstVisible != -1:
            editor.ensureLineVisible( firstVisible )
            currentLine = editor.firstVisibleLine()
            editor.scrollVertical( firstVisible - currentLine )
        return

    def __onZoom( self, zoomValue ):
        " Sets the zoom value for all the opened editor tabs "
        Settings().zoom = zoomValue

        for index in xrange( self.count() ):
            item = self.widget( index )
            if item.getType() in [ MainWindowTabWidgetBase.PlainTextEditor ]:
                item.getEditor().zoomTo( zoomValue )
        return

    def getTextEditors( self ):
        " Provides a list of the currently opened text editors "
        result = []
        for index in xrange( self.count() ):
            item = self.widget( index )
            if item.getType() in [ MainWindowTabWidgetBase.PlainTextEditor ]:
                result.append( [ item.getUUID(), item.getFileName(), item ] )
        return result

    def updateEditorsSettings( self ):
        " makes all the text editors updating settings "
        for index in xrange( self.count() ):
            item = self.widget( index )
            if item.getType() in [ MainWindowTabWidgetBase.PlainTextEditor ]:
                item.getEditor().updateSettings()
                if item.isDiskFileModified():
                    # This will make the modification markers re-drawn
                    # properly for the case when auto line wrap toggled
                    item.resizeBars()
        return

    def getWidgetByUUID( self, uuid ):
        " Provides the widget found by the given UUID "
        for index in xrange( self.count() ):
            widget = self.widget( index )
            if uuid == widget.getUUID():
                return widget
        return None

    def getIndexByUUID( self, uuid ):
        " Provides the tab index for the given uuid "
        for index in xrange( self.count() ):
            widget = self.widget( index )
            if uuid == widget.getUUID():
                return index
        return -1

    def getWidgetByIndex( self, index ):
        " Provides the widget for the given index on None "
        if index >= self.count():
            return None
        return self.widget( index )

    def getWidgetForFileName( self, fname ):
        " Provides the widget found by the given file name "
        for index in xrange( self.count() ):
            widget = self.widget( index )
            if fname == widget.getFileName():
                return widget
        return None

    def checkOutsideFileChanges( self ):
        " Checks all the tabs if the files were changed / disappeared outside "
        for index in xrange( self.count() ):
            self._updateIconAndTooltip( index )

        if self.currentWidget().doesFileExist():
            if self.currentWidget().isDiskFileModified():
                if not self.currentWidget().getReloadDialogShown():
                    self.currentWidget().showOutsideChangesBar( \
                                    self.__countDiskModifiedUnchanged() > 1 )
        return

    def __countDiskModifiedUnchanged( self ):
        """ Returns the number of buffers with non modified
            content for which the disk file is modified """
        cnt = 0
        for index in xrange( self.count() ):
            if self.widget( index ).isModified() == False:
                if self.widget( index ).isDiskFileModified():
                    cnt += 1
        return cnt

    def onReload( self ):
        " Called when the current tab file should be reloaded "
        self.reloadTab( self.currentIndex() )
        return

    def reloadTab( self, index ):
        " Reloads a single tab "

        # This may happened for a text file or for a picture
        isTextEditor = self.widget( index ).getType() == \
                                    MainWindowTabWidgetBase.PlainTextEditor

        try:
            if isTextEditor:
                editor = self.widget( index ).getEditor()
                line , pos = editor.getCursorPosition()
                firstLine = editor.firstVisibleLine()

            self.widget( index ).reload()

            if isTextEditor:
                self.__restorePosition( editor, line, pos, firstLine )
        except Exception, exc:
            # Error reloading the file, nothing to be changed
            logging.error( str( exc ) )
            return

        self._updateIconAndTooltip( index )

        if isTextEditor:
            self.history.tabClosed( self.widget( index ).getUUID() )
            if index == self.currentIndex():
                self.history.addCurrent()
        return

    def onReloadAllNonModified( self ):
        """ Called when all the disk changed and not
            modified files should be reloaded """
        for index in xrange( self.count() ):
            if self.widget( index ).isModified() == False:
                if self.widget( index ).isDiskFileModified():
                    self.reloadTab( index )
        return

    def getModifiedList( self, projectOnly = False ):
        " Prpovides a list of modified file names with the corresponding UUIDs "
        result = []

        for index in xrange( self.count() ):
            widget = self.widget( index )
            if widget.isModified():
                fileName = widget.getFileName()
                if projectOnly:
                    if not GlobalData().project.isProjectFile( fileName ):
                        continue
                result.append( [ fileName, widget.getUUID() ] )
        return result

    def getOpenedList( self, projectOnly = False ):
        " provides a list of opened files "
        result = []
        for index in xrange( self.count() ):
            widget = self.widget( index )
            fileName = widget.getFileName()
            if projectOnly:
                if not GlobalData().project.isProjectFile( fileName ):
                    continue
            result.append( [ fileName, widget.getUUID() ] )
        return result

    def isFileOpened( self, fileName ):
        " True if the file is loaded "
        for attrs in self.getOpenedList():
            if attrs[ 0 ] == fileName:
                return True
        return False

    def saveModified( self, projectOnly = False ):
        " Saves the modified files. Stops on first error. "
        for index in xrange( self.count() ):
            widget = self.widget( index )
            if widget.isModified():
                fileName = widget.getFileName()
                if projectOnly:
                    if not GlobalData().project.isProjectFile( fileName ):
                        continue
                # Save the file
                try:
                    if self.onSave( index ) == False:
                        return False
                    self.setTabText( index, widget.getShortName() )
                except Exception, excpt:
                    logging.error( str( excpt ) )
                    return False
        return True

    def __onDebugMode( self, newState ):
        " Triggered when the debug mode state is changed "
        self.__debugMode = newState
        if self.__debugMode:
            if not GlobalData().project.isLoaded():
                self.__debugScript = self.currentWidget().getFileName()
        else:
            self.__debugScript = ""

        for index in xrange( self.count() ):
            self.setWidgetDebugMode( self.widget( index ) )
        return

    def setWidgetDebugMode( self, widget ):
        " Sets the widget debug mode "

        fileName = widget.getFileName()
        fileType = detectFileType( fileName )
        if widget.getType() not in [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return
        if detectFileType( fileName ) not in [ PythonFileType,
                                               Python3FileType ]:
            return

        # Need to send the notification only to the python editors
        isPrjFile = GlobalData().project.isProjectFile( fileName ) or \
                    fileName == self.__debugScript
        widget.setDebugMode( self.__debugMode, isPrjFile )
        return

    def zoomIn( self ):
        " Called if main menu item is selected "
        widget = self.currentWidget()
        if widget.getType() in [ MainWindowTabWidgetBase.PlainTextEditor,
                                 MainWindowTabWidgetBase.PictureViewer,
                                 MainWindowTabWidgetBase.GeneratedDiagram ]:
            widget.onZoomIn()
        return

    def zoomOut( self ):
        " Called if main menu item is selected "
        widget = self.currentWidget()
        if widget.getType() in [ MainWindowTabWidgetBase.PlainTextEditor,
                                 MainWindowTabWidgetBase.PictureViewer,
                                 MainWindowTabWidgetBase.GeneratedDiagram ]:
            widget.onZoomOut()
        return

    def zoomReset( self ):
        " Called if main menu item is selected "
        widget = self.currentWidget()
        if widget.getType() in [ MainWindowTabWidgetBase.PlainTextEditor,
                                 MainWindowTabWidgetBase.PictureViewer,
                                 MainWindowTabWidgetBase.GeneratedDiagram ]:
            widget.onZoomReset()
        return

    def isCopyAvailable( self ):
        " Checks if Ctrl+C works for the current widget "
        widget = self.currentWidget()
        if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            return True
        if widget.getType() == MainWindowTabWidgetBase.HTMLViewer:
            return widget.getViewer().selectedText() != ""
        return False

    def onCopy( self ):
        " Called when Ctrl+C is selected via main menu "
        widget = self.currentWidget()
        if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            widget.getEditor().onCtrlC()
            return
        if widget.getType() == MainWindowTabWidgetBase.HTMLViewer:
            text = widget.getViewer().selectedText()
            if text != "":
                QApplication.clipboard().setText( text )
        return

