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

" Break points viewer "


from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import ( QSizePolicy, QFrame, QTreeView, QToolButton,
                          QHeaderView, QVBoxLayout, QSortFilterProxyModel,
                          QLabel, QWidget, QAbstractItemView, QMenu,
                          QSpacerItem, QHBoxLayout, QPalette, QCursor,
                          QItemSelectionModel, QDialog )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.project import CodimensionProject


class BreakPointView( QTreeView ):
    " Breakpoint viewer widget "

    def __init__( self, parent, bpointsModel ):
        QTreeView.__init__( self, parent )

        self.__model = None
        self.setModel( bpointsModel )

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
        " Sets the breakpoint model "
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

    def toSourceIndex( self, index ):
        " Converts an index to a source index "
        return self.sortingModel.mapToSource( index )

    def __fromSourceIndex( self, sindex ):
        " Convert a source index to an index "
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

    def __createPopupMenus( self ):
        " Generate the popup menu "
        self.menu = QMenu()
        self.menu.addAction( "Edit...", self.__editBreak )
        self.menu.addSeparator()
        self.menu.addAction( "Enable", self.__enableBreak )
        self.menu.addAction( "Enable all", self.__enableAllBreaks )
        self.menu.addSeparator()
        self.menu.addAction( "Disable", self.__disableBreak )
        self.menu.addAction( "Disable all", self.__disableAllBreaks )
        self.menu.addSeparator()
        self.menu.addAction( "Delete", self.__deleteBreak )
        self.menu.addAction( "Delete all", self.__deleteAllBreaks )
        self.menu.addSeparator()
        self.menu.addAction( "Jump to code", self.__showSource )
        return

    def __showContextMenu( self, coord ):
        " Shows the context menu "
        cnt = self.__getSelectedItemsCount()
        if cnt <= 1:
            index = self.indexAt(coord)
            if index.isValid():
                cnt = 1
                self.__setRowSelected(index)
        coord = self.mapToGlobal(coord)
        if cnt == 1:
            self.menu.popup(coord)


    def __doubleClicked( self, index ):
        " Handles the double clicked signal "
        if not index.isValid():
            return

        sindex = self.toSourceIndex( index )
        if not sindex.isValid():
            return

        # Jump to the code
        bpoint = self.__model.getBreakPointByIndex( sindex )
        fileName = bpoint.getAbsoluteFileName()
        line = bpoint.getLineNumber()
        self.jumpToCode( fileName, line )
        return

    def jumpToCode( self, fileName, line ):
        " Jumps to the source code "
        editorsManager = GlobalData().mainWindow.editorsManager()
        editorsManager.openFile( fileName, line )
        editor = editorsManager.currentWidget().getEditor()
        editor.gotoLine( line )
        editorsManager.currentWidget().setFocus()
        return

    def __editBreak( self ):
        " Handle the edit breakpoint context menu entry "
        index = self.currentIndex()
        if index.isValid():
            self.__editBreakpoint( index )
        return

    def __editBreakpoint( self, index ):
        " Edits a breakpoint "
        sindex = self.toSourceIndex( index )
        if sindex.isValid():
            bp = self.__model.getBreakPointByIndex( sindex )
            if not bp:
                return

            fn, line, cond, temp, enabled, count = bp[ : 6 ]

            dlg = EditBreakpointDialog((fn, line), (cond, temp, enabled, count),
                self.condHistory, self, modal = True)
            if dlg.exec_() == QDialog.Accepted:
                cond, temp, enabled, count = dlg.getData()

                self.__model.setBreakPointByIndex( sindex,
                    fn, line, (unicode(cond), temp, enabled, count ) )
                self.__resizeColumns()
                self.__resort()
        return

    def __setBpEnabled( self, index, enabled ):
        " Sets the enabled status of a breakpoint "
        sindex = self.toSourceIndex( index )
        if sindex.isValid():
            self.__model.setBreakPointEnabledByIndex( sindex, enabled )
        return

    def __enableBreak( self ):
        " Handles the enable breakpoint context menu entry "
        index = self.currentIndex()
        self.__setBpEnabled( index, True )
        self.__resizeColumns()
        self.__resort()
        return

    def __enableAllBreaks( self ):
        " Handles the enable all breakpoints context menu entry "
        index = self.model().index( 0, 0 )
        while index.isValid():
            self.__setBpEnabled( index, True )
            index = self.indexBelow( index )
        self.__resizeColumns()
        self.__resort()
        return

    def __enableSelectedBreaks( self ):
        " Handles the enable selected breakpoints context menu entry "
        for index in self.selectedIndexes():
            if index.column() == 0:
                self.__setBpEnabled( index, True )
        self.__resizeColumns()
        self.__resort()
        return

    def __disableBreak( self ):
        " Handles the disable breakpoint context menu entry "
        index = self.currentIndex()
        self.__setBpEnabled( index, False )
        self.__resizeColumns()
        self.__resort()
        return

    def __disableAllBreaks( self ):
        " Handles the disable all breakpoints context menu entry "
        index = self.model().index( 0, 0 )
        while index.isValid():
            self.__setBpEnabled( index, False )
            index = self.indexBelow( index )
        self.__resizeColumns()
        self.__resort()
        return

    def __disableSelectedBreaks( self ):
        " Handles the disable selected breakpoints context menu entry "
        for index in self.selectedIndexes():
            if index.column() == 0:
                self.__setBpEnabled( index, False )
        self.__resizeColumns()
        self.__resort()
        return

    def __deleteBreak( self ):
        " Handles the delete breakpoint context menu entry "
        index = self.currentIndex()
        sindex = self.toSourceIndex( index )
        if sindex.isValid():
            self.__model.deleteBreakPointByIndex( sindex )
        return

    def __deleteAllBreaks( self ):
        " Handles the delete all breakpoints context menu entry "
        self.__model.deleteAll()
        return

    def __deleteSelectedBreaks( self ):
        " Handles the delete selected breakpoints context menu entry "
        idxList = []
        for index in self.selectedIndexes():
            sindex = self.toSourceIndex( index )
            if sindex.isValid() and index.column() == 0:
                idxList.append( sindex )
        self.__model.deleteBreakPoints( idxList )
        return

    def __showSource( self ):
        " Handles the goto context menu entry "
        index = self.currentIndex()
        sindex = self.toSourceIndex( index )
        bp = self.__model.getBreakPointByIndex( sindex )
        if not bp:
            return

        fn, line = bp[ : 2 ]
        self.emit( SIGNAL( "sourceFile" ), fn, line )
        return

    def highlightBreakpoint( self, fn, lineno ):
        " Handles the clientLine signal "
        sindex = self.__model.getBreakPointIndex( fn, lineno )
        if sindex.isValid():
            return

        index = self.__fromSourceIndex( sindex )
        if index.isValid():
            self.__clearSelection()
            self.__setRowSelected( index, True )
        return

    def __getSelectedItemsCount( self ):
        " Provides the count of items selected "
        count = len( self.selectedIndexes() ) / ( self.__model.columnCount() - 1 )
        # column count is 1 greater than selectable
        return count

    def selectionChanged( self, selected, deselected ):
        " The slot is called when the selection has changed "
        if selected.indexes():
            self.emit( SIGNAL( 'selectionChanged' ),
                       selected.indexes()[ 0 ] )
        else:
            self.emit( SIGNAL( 'selectionChanged' ), None )
        QTreeView.selectionChanged( self, selected, deselected )
        return



class BreakPointViewer( QWidget ):
    " Implements the break point viewer for a debugger "

    def __init__( self, parent, bpointsModel ):
        QWidget.__init__( self, parent )

        self.__currentItem = None
        self.__createLayout( bpointsModel )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( self.__bpointsList,
                      SIGNAL( "selectionChanged" ),
                      self.__onSelectionChanged )
        return

    def setFocus( self ):
        " Sets the widget focus "
        self.__bpointsList.setFocus()
        return

    def __createLayout( self, bpointsModel ):
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

        self.__breakpointLabel = QLabel( "Breakpoints" )

        fixedSpacer = QSpacerItem( 3, 3 )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__breakpointLabel )
        self.headerFrame.setLayout( headerLayout )

        self.__bpointsList = BreakPointView( self, bpointsModel )

        self.__editButton = QToolButton()
        self.__editButton.setIcon( PixmapCache().getIcon( 'bpprops.png' ) )
        self.__editButton.setFixedSize( 24, 24 )
        self.__editButton.setToolTip( "Edit breakpoint properties" )
        self.__editButton.setFocusPolicy( Qt.NoFocus )
        self.__editButton.setEnabled( False )
        self.connect( self.__editButton, SIGNAL( 'clicked()' ),
                      self.__onEdit )

        self.__enableButton = QToolButton()
        self.__enableButton.setIcon( PixmapCache().getIcon( 'bpenable.png' ) )
        self.__enableButton.setFixedSize( 24, 24 )
        self.__enableButton.setToolTip( "Enable/disable the breakpoint" )
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
        toolbarLayout.addWidget( self.__editButton )
        toolbarLayout.addWidget( self.__enableButton )
        toolbarLayout.addSpacerItem( expandingSpacer )
        toolbarLayout.addWidget( self.__jumpToCodeButton )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addLayout( toolbarLayout )
        verticalLayout.addWidget( self.__bpointsList )
        return

    def clear( self ):
        " Clears the content "
#        self.__bpointsList.clear()
        self.__updateBreakpointsLabel()
        self.__jumpToCodeButton.setEnabled( False )
        self.__currentItem = None
        return

    def __updateBreakpointsLabel( self ):
        " Updates the breakpoints header label "
        total = self.getTotalCount()
        if total > 0:
            self.__breakpointLabel.setText( "Breakpoints (total: " +
                                       str( total ) + ")" )
        else:
            self.__breakpointLabel.setText( "Breakpoints" )
        return

    def getTotalCount( self ):
        " Provides the total number of exceptions "
        count = 0
        return count
        for index in xrange( self.__exceptionsList.topLevelItemCount() ):
            count += self.__exceptionsList.topLevelItem( index ).getCount()
        return count

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "
        if what == CodimensionProject.CompleteProject:
            self.clear()
        return

    def __onSelectionChanged( self, index ):
        " Triggered when the current item is changed "
        if index is None:
            self.__currentItem = None
        else:
            srcModel = self.__bpointsList.model().sourceModel()
            sindex = self.__bpointsList.toSourceIndex( index )
            self.__currentItem = srcModel.getBreakPointByIndex( sindex )
        self.__updateButtons()
        return

    def __updateButtons( self ):
        " Updates the buttons status "
        if self.__currentItem is None:
            self.__editButton.setEnabled( False )
            self.__enableButton.setEnabled( False )
            self.__jumpToCodeButton.setEnabled( False )
        else:
            self.__editButton.setEnabled( True )
            self.__enableButton.setEnabled( True )
            self.__jumpToCodeButton.setEnabled( True )
        return

    def __onEnableDisable( self ):
        " Triggered when a breakpoint should be enabled/disabled "
        return

    def __onEdit( self ):
        " Triggered when a breakpoint should be edited "
        return

    def __onJumpToCode( self ):
        " Triggered when should jump to source "
        if self.__currentItem is None:
            return
        self.__bpointsList.jumpToCode( self.__currentItem.getAbsoluteFileName(),
                                       self.__currentItem.getLineNumber() )
        return
