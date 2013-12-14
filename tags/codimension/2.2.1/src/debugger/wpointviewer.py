#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Watch points viewer "


from PyQt4.QtCore import Qt, SIGNAL, QModelIndex
from PyQt4.QtGui import ( QSizePolicy, QFrame, QTreeView, QToolButton,
                          QHeaderView, QVBoxLayout,
                          QLabel, QWidget, QAbstractItemView, QMenu,
                          QSpacerItem, QHBoxLayout, QPalette,
                          QSortFilterProxyModel )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.project import CodimensionProject
from utils.settings import Settings



class WatchPointView( QTreeView ):
    " Watch expression viewer widget "
    def __init__( self, parent, wpointsModel ):
        QTreeView.__init__( self, parent )

        self.__model = None
        self.setModel( wpointsModel )

        self.setItemsExpandable( False )
        self.setRootIsDecorated( False )
        self.setAlternatingRowColors( True )
        self.setUniformRowHeights( True )
        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        self.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self,
                      SIGNAL( 'customContextMenuRequested(const QPoint &)' ),
                      self.__showContextMenu )
        self.connect( self,
                      SIGNAL( 'doubleClicked(const QModelIndex &)' ),
                      self.__doubleClicked )

        self.__createPopupMenus()
        return

    def setModel( self, model ):
        " Sets the watch expression model "
        self.__model = model

        self.sortingModel = QSortFilterProxyModel()
        self.sortingModel.setSourceModel( self.__model )
        QTreeView.setModel( self, self.sortingModel )

        header = self.header()
        header.setSortIndicator( 0, Qt.AscendingOrder )
        header.setSortIndicatorShown( True )
        header.setClickable( True )

        self.setSortingEnabled( True )
        self.__layoutDisplay()
        return

    def __layoutDisplay( self ):
        " Performs the layout operation "
        self.__resizeColumns()
        self.__resort()
        return

    def __resizeColumns( self ):
        " Resizes the view when items get added, edited or deleted "
        self.header().resizeSections( QHeaderView.ResizeToContents )
        self.header().setStretchLastSection( True )
        return

    def __resort( self ):
        " Resorts the tree "
        self.model().sort( self.header().sortIndicatorSection(),
                           self.header().sortIndicatorOrder() )
        return

    def __toSourceIndex( self, index ):
        " Converts an index to a source index "
        return self.sortingModel.mapToSource( index )

    def __fromSourceIndex( self, sindex ):
        " Converts a source index to an index "
        return self.sortingModel.mapFromSource( sindex )

    def __setRowSelected( self, index, selected = True ):
        " Selects a row "
        if not index.isValid():
            return

        if selected:
            flags = QItemSelectionModel.SelectionFlags(
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows )
        else:
            flags = QItemSelectionModel.SelectionFlags(
                QItemSelectionModel.Deselect | QItemSelectionModel.Rows )
        self.selectionModel().select( index, flags )
        return

    def __createPopupMenus(self):
        """
        Private method to generate the popup menus.
        """
        self.menu = QMenu()
        self.menu.addAction(self.trUtf8("Add"), self.__addWatchPoint)
        self.menu.addAction(self.trUtf8("Edit..."), self.__editWatchPoint)
        self.menu.addSeparator()
        self.menu.addAction(self.trUtf8("Enable"), self.__enableWatchPoint)
        self.menu.addAction(self.trUtf8("Enable all"), self.__enableAllWatchPoints)
        self.menu.addSeparator()
        self.menu.addAction(self.trUtf8("Disable"), self.__disableWatchPoint)
        self.menu.addAction(self.trUtf8("Disable all"), self.__disableAllWatchPoints)
        self.menu.addSeparator()
        self.menu.addAction(self.trUtf8("Delete"), self.__deleteWatchPoint)
        self.menu.addAction(self.trUtf8("Delete all"), self.__deleteAllWatchPoints)

        self.backMenuActions = {}
        self.backMenu = QMenu()
        self.backMenu.addAction(self.trUtf8("Add"), self.__addWatchPoint)
        self.backMenuActions["EnableAll"] = \
            self.backMenu.addAction(self.trUtf8("Enable all"),
                self.__enableAllWatchPoints)
        self.backMenuActions["DisableAll"] = \
            self.backMenu.addAction(self.trUtf8("Disable all"),
                self.__disableAllWatchPoints)
        self.backMenuActions["DeleteAll"] = \
            self.backMenu.addAction(self.trUtf8("Delete all"),
                self.__deleteAllWatchPoints)
        self.connect(self.backMenu, SIGNAL('aboutToShow()'), self.__showBackMenu)

        self.multiMenu = QMenu()
        self.multiMenu.addAction(self.trUtf8("Add"), self.__addWatchPoint)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.trUtf8("Enable selected"),
            self.__enableSelectedWatchPoints)
        self.multiMenu.addAction(self.trUtf8("Enable all"), self.__enableAllWatchPoints)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.trUtf8("Disable selected"),
            self.__disableSelectedWatchPoints)
        self.multiMenu.addAction(self.trUtf8("Disable all"), self.__disableAllWatchPoints)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.trUtf8("Delete selected"),
            self.__deleteSelectedWatchPoints)
        self.multiMenu.addAction(self.trUtf8("Delete all"), self.__deleteAllWatchPoints)
        return

    def __showContextMenu( self, coord ):
        """
        Private slot to show the context menu.

        @param coord the position of the mouse pointer (QPoint)
        """
        cnt = self.__getSelectedItemsCount()
        if cnt <= 1:
            index = self.indexAt(coord)
            if index.isValid():
                cnt = 1
                self.__setRowSelected(index)
        coord = self.mapToGlobal(coord)
        if cnt > 1:
            self.multiMenu.popup(coord)
        elif cnt == 1:
            self.menu.popup(coord)
        else:
            self.backMenu.popup(coord)

    def __findDuplicates( self, cond, special,
                          showMessage = False, index = QModelIndex() ):
        " Checks if an entry already exists "
        cond = unicode( cond )
        special = unicode( special )
        idx = self.__model.getWatchPointIndex( cond, special )
        duplicate = idx.isValid() and idx.internalPointer() != index.internalPointer()
#        if showMessage and duplicate:
#            if not special:
#                msg = """<p>A watch expression '<b>%1</b>'"""
#                                  """ already exists.</p>""".arg(Utilities.html_encode(unicode(cond)))
#            else:
#                msg = self.trUtf8("""<p>A watch expression '<b>%1</b>'"""
#                                  """ for the variable <b>%2</b> already exists.</p>""")\
#                        .arg(special)\
#                        .arg(Utilities.html_encode(unicode(cond)))
#            KQMessageBox.warning(None,
#                self.trUtf8("Watch expression already exists"),
#                msg)

        return duplicate

    def __clearSelection( self ):
        " Clears the selection "
        for index in self.selectedIndexes():
            self.__setRowSelected( index, False )
        return

    def __addWatchPoint( self ):
        " Adds watch expression via a context menu entry "
#        dlg = EditWatchpointDialog( ( QString( "" ), False, True, 0, QString( "" ) ), self )
#        if dlg.exec_() == QDialog.Accepted:
#            cond, temp, enabled, ignorecount, special = dlg.getData()
#            if not self.__findDuplicates(cond, special, True):
#                self.__model.addWatchPoint(cond, special, (temp, enabled, ignorecount))
#                self.__resizeColumns()
#                self.__resort()
        return

    def __doubleClicked(self, index):
        " Handles the double clicked signal "
        if index.isValid():
            self.__doEditWatchPoint( index )
        return

    def __editWatchPoint( self ):
        " Handles the edit watch expression context menu entry "
        index = self.currentIndex()
        if index.isValid():
            self.__doEditWatchPoint( index )
        return

    def __doEditWatchPoint( self, index ):
        " Edits a watch expression "
        sindex = self.__toSourceIndex( index )
        if sindex.isValid():
            wp = self.__model.getWatchPointByIndex( sindex )
            if not wp:
                return

            cond, special, temp, enabled, count = wp[ : 5 ]

#            dlg = EditWatchpointDialog(
#                (QString(cond), temp, enabled, count, QString(special)), self)
#            if dlg.exec_() == QDialog.Accepted:
#                cond, temp, enabled, count, special = dlg.getData()
#                if not self.__findDuplicates(cond, special, True, sindex):
#                    self.__model.setWatchPointByIndex(sindex,
#                        unicode(cond), unicode(special), (temp, enabled, count))
#                    self.__resizeColumns()
#                    self.__resort()
        return

    def __setWpEnabled( self, index, enabled ):
        " Sets the enabled status of a watch expression "
        sindex = self.__toSourceIndex( index )
        if sindex.isValid():
            self.__model.setWatchPointEnabledByIndex( sindex, enabled )
        return

    def __enableWatchPoint( self ):
        " Handles the enable watch expression context menu entry "
        index = self.currentIndex()
        self.__setWpEnabled( index, True )
        self.__resizeColumns()
        self.__resort()
        return

    def __enableAllWatchPoints( self ):
        " Handles the enable all watch expressions context menu entry "
        index = self.model().index( 0, 0 )
        while index.isValid():
            self.__setWpEnabled( index, True )
            index = self.indexBelow( index )
        self.__resizeColumns()
        self.__resort()
        return

    def __enableSelectedWatchPoints( self ):
        " Handles the enable selected watch expressions context menu entry "
        for index in self.selectedIndexes():
            if index.column() == 0:
                self.__setWpEnabled( index, True )
        self.__resizeColumns()
        self.__resort()
        return

    def __disableWatchPoint( self ):
        " Handles the disable watch expression context menu entry "
        index = self.currentIndex()
        self.__setWpEnabled( index, False )
        self.__resizeColumns()
        self.__resort()
        return

    def __disableAllWatchPoints( self ):
        " Handles the disable all watch expressions context menu entry "
        index = self.model().index( 0, 0 )
        while index.isValid():
            self.__setWpEnabled( index, False )
            index = self.indexBelow( index )
        self.__resizeColumns()
        self.__resort()
        return

    def __disableSelectedWatchPoints( self ):
        " Handles the disable selected watch expressions context menu entry "
        for index in self.selectedIndexes():
            if index.column() == 0:
                self.__setWpEnabled( index, False )
        self.__resizeColumns()
        self.__resort()
        return

    def __deleteWatchPoint( self ):
        " Handles the delete watch expression context menu entry "
        index = self.currentIndex()
        sindex = self.__toSourceIndex( index )
        if sindex.isValid():
            self.__model.deleteWatchPointByIndex( sindex )
        return

    def __deleteAllWatchPoints( self ):
        " Handles the delete all watch expressions context menu entry "
        self.__model.deleteAll()
        return

    def __deleteSelectedWatchPoints( self ):
        " Handles the delete selected watch expressions context menu entry "
        idxList = []
        for index in self.selectedIndexes():
            sindex = self.__toSourceIndex( index )
            if sindex.isValid() and index.column() == 0:
                lastrow = index.row()
                idxList.append( sindex )
        self.__model.deleteWatchPoints( idxList )
        return

    def __showBackMenu( self ):
        " Handles the aboutToShow signal of the background menu "
        if self.model().rowCount() == 0:
            self.backMenuActions[ "EnableAll" ].setEnabled( False )
            self.backMenuActions[ "DisableAll" ].setEnabled( False )
            self.backMenuActions[ "DeleteAll" ].setEnabled( False )
        else:
            self.backMenuActions[ "EnableAll" ].setEnabled( True )
            self.backMenuActions[ "DisableAll" ].setEnabled( True )
            self.backMenuActions[ "DeleteAll" ].setEnabled( True )
        return

    def __getSelectedItemsCount( self ):
        " Provides the count of items selected "
        count = len( self.selectedIndexes() ) / ( self.__model.columnCount() - 1 )
        # column count is 1 greater than selectable
        return count





class WatchPointViewer( QWidget ):
    " Implements the watch point viewer for a debugger "

    def __init__( self, parent, wpointModel ):
        QWidget.__init__( self, parent )

        self.__currentItem = None

        self.__createPopupMenu()
        self.__createLayout( wpointModel )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )

        if Settings().showWatchPointViewer == False:
            self.__onShowHide( True )
        return

    def __createPopupMenu( self ):
        " Creates the popup menu "
#        self.__excptMenu = QMenu()
#        self.__removeMenuItem = self.__excptMenu.addAction(
#                    "Remove from ignore list", self.__onRemoveFromIgnore )
        return

    def __createLayout( self, wpointModel ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 0, 0, 0, 0 )
        verticalLayout.setSpacing( 0 )

        self.headerFrame = QFrame()
        self.headerFrame.setFrameStyle( QFrame.StyledPanel )
        self.headerFrame.setAutoFillBackground( True )
        headerPalette = self.headerFrame.palette()
        headerBackground = headerPalette.color( QPalette.Background )
        headerBackground.setRgb( min( headerBackground.red() + 30, 255 ),
                                 min( headerBackground.green() + 30, 255 ),
                                 min( headerBackground.blue() + 30, 255 ) )
        headerPalette.setColor( QPalette.Background, headerBackground )
        self.headerFrame.setPalette( headerPalette )
        self.headerFrame.setFixedHeight( 24 )

        self.__watchpointLabel = QLabel( "Watchpoints" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise( True )
        self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideButton.setFixedSize( 20, 20 )
        self.__showHideButton.setToolTip( "Hide ignored exceptions list" )
        self.__showHideButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__showHideButton, SIGNAL( 'clicked()' ),
                      self.__onShowHide )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 1, 1, 1, 1 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__watchpointLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__showHideButton )
        self.headerFrame.setLayout( headerLayout )

        self.__wpointsList = WatchPointView( self, wpointModel )

        self.__enableButton = QToolButton()
        self.__enableButton.setIcon( PixmapCache().getIcon( 'add.png' ) )
        self.__enableButton.setFixedSize( 24, 24 )
        self.__enableButton.setToolTip( "Enable/disable the watchpoint" )
        self.__enableButton.setFocusPolicy( Qt.NoFocus )
        self.__enableButton.setEnabled( False )
        self.connect( self.__enableButton,
                      SIGNAL( 'clicked()' ),
                      self.__onEnableDisable )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__jumpToCodeButton = QToolButton()
        self.__jumpToCodeButton.setIcon( PixmapCache().getIcon( 'gotoline.png' ) )
        self.__jumpToCodeButton.setFixedSize( 24, 24 )
        self.__jumpToCodeButton.setToolTip( "Jump to the code" )
        self.__jumpToCodeButton.setFocusPolicy( Qt.NoFocus )
        self.__jumpToCodeButton.setEnabled( False )
        self.connect( self.__jumpToCodeButton,
                      SIGNAL( 'clicked()' ),
                      self.__onJumpToCode )

        toolbarLayout = QHBoxLayout()
        toolbarLayout.addWidget( self.__enableButton )
        toolbarLayout.addSpacerItem( expandingSpacer )
        toolbarLayout.addWidget( self.__jumpToCodeButton )

        self.connect( self.__wpointsList,
                      SIGNAL( "itemSelectionChanged()" ),
                      self.__onSelectionChanged )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addLayout( toolbarLayout )
        verticalLayout.addWidget( self.__wpointsList )
        return

    def clear( self ):
        " Clears the content "
#        self.__wpointsList.clear()
        self.__updateTitle()
        self.__jumpToCodeButton.setEnabled( False )
        self.__currentItem = None
        return

    def __onJumpToCode( self ):
        " Jumps to the corresponding source code line "
        return

    def __onShowHide( self, startup = False ):
        " Triggered when show/hide button is clicked "
        if startup or self.__wpointsList.isVisible():
            self.__wpointsList.setVisible( False )
            self.__enableButton.setVisible( False )
            self.__jumpToCodeButton.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show watchpoints list" )

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight( self.headerFrame.height() )
            self.setMaximumHeight( self.headerFrame.height() )

            Settings().showWatchPointViewer = False
        else:
            self.__wpointsList.setVisible( True )
            self.__enableButton.setVisible( True )
            self.__jumpToCodeButton.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide watchpoints list" )

            self.setMinimumHeight( self.__minH )
            self.setMaximumHeight( self.__maxH )

            Settings().showWatchPointViewer = True
        return

    def __onSelectionChanged( self ):
        " Triggered when the current item is changed "
        return
        selected = list( self.__exceptionsList.selectedItems() )
        if selected:
            self.__currentItem = selected[ 0 ]
            self.__removeButton.setEnabled( True )
        else:
            self.__currentItem = None
            self.__removeButton.setEnabled( False )
        return

    def __updateTitle( self ):
        " Updates the section title "
        count = self.getTotalCount()
        if count == 0:
            self.__watchpointLabel.setText( "Watchpoints" )
        else:
            self.__watchpointLabel.setText( "Watchpoints (total: " +
                                            str( count ) + ")" )
        return

    def getTotalCount( self ):
        " Provides the total number of watch points "
        count = 0
        return count

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "
        if what == CodimensionProject.CompleteProject:
            self.clear()
        return

    def __onEnableDisable( self ):
        " Triggered when a breakpoint should be enabled/disabled "
        return

