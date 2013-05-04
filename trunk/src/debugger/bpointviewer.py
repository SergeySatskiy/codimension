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

    def __toSourceIndex( self, index ):
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
        self.menu.addAction( "Add", self.__addBreak )
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

    def __addBreak( self ):
        " Handles the add breakpoint context menu entry "
        dlg = EditBreakpointDialog((self.fnHistory[0], None), None,
            self.condHistory, self, modal = 1, addMode = 1,
            filenameHistory = self.fnHistory)
        if dlg.exec_() == QDialog.Accepted:
            fn, line, cond, temp, enabled, count = dlg.getAddData()

            self.__model.addBreakPoint( fn, line, (unicode(cond), temp, enabled, count))
            self.__resizeColumns()
            self.__resort()

    def __doubleClicked( self, index ):
        " Handles the double clicked signal "
        if index.isValid():
            self.__editBreakpoint( index )
        return

    def __editBreak( self ):
        " Handle the edit breakpoint context menu entry "
        index = self.currentIndex()
        if index.isValid():
            self.__editBreakpoint( index )
        return

    def __editBreakpoint( self, index ):
        " Edits a breakpoint "
        sindex = self.__toSourceIndex( index )
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
        sindex = self.__toSourceIndex( index )
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
        sindex = self.__toSourceIndex( index )
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
            sindex = self.__toSourceIndex( index )
            if sindex.isValid() and index.column() == 0:
                idxList.append( sindex )
        self.__model.deleteBreakPoints( idxList )
        return

    def __showSource( self ):
        " Handles the goto context menu entry "
        index = self.currentIndex()
        sindex = self.__toSourceIndex( index )
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



class BreakPointViewer( QWidget ):
    " Implements the break point viewer for a debugger "

    def __init__( self, parent, bpointsModel ):
        QWidget.__init__( self, parent )

        self.__currentItem = None

        self.__createPopupMenu()
        self.__createLayout( bpointsModel )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def setFocus( self ):
        " Sets the widget focus "
        self.__bpointsList.setFocus()
        return

    def __createPopupMenu( self ):
        " Creates the popup menu "
        #self.__excptMenu = QMenu()
        #self.__addToIgnoreMenuItem = self.__excptMenu.addAction(
        #            "Add to ignore list", self.__onAddToIgnore )
        #self.__jumpToCodeMenuItem = self.__excptMenu.addAction(
        #            "Jump to code", self.__onJumpToCode )
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

        self.__enableButton = QToolButton()
        self.__enableButton.setIcon( PixmapCache().getIcon( 'add.png' ) )
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
        toolbarLayout.addWidget( self.__enableButton )
        toolbarLayout.addSpacerItem( expandingSpacer )
        toolbarLayout.addWidget( self.__jumpToCodeButton )

        self.connect( self.__bpointsList,
                      SIGNAL( "itemSelectionChanged()" ),
                      self.__onSelectionChanged )

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

    def __onJumpToCode( self ):
        " Jumps to the corresponding source code line "
        return
        if self.__currentItem is not None:
            if self.__currentItem.getType() == STACK_FRAME_ITEM:
                fileName = self.__currentItem.getFileName()
                if '<' not in fileName and '>' not in fileName:
                    lineNumber = self.__currentItem.getLineNumber()

                    editorsManager = GlobalData().mainWindow.editorsManager()
                    editorsManager.openFile( fileName, lineNumber )
                    editor = editorsManager.currentWidget().getEditor()
                    editor.gotoLine( lineNumber )
                    editorsManager.currentWidget().setFocus()
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

    def __onSelectionChanged( self ):
        " Triggered when the current item is changed "
        return
        selected = list( self.__exceptionsList.selectedItems() )
        if selected:
            self.__currentItem = selected[ 0 ]
            if self.__currentItem.getType() == STACK_FRAME_ITEM:
                fileName = self.__currentItem.getFileName()
                if '<' in fileName or '>' in fileName:
                    self.__jumpToCodeButton.setEnabled( False )
                else:
                    self.__jumpToCodeButton.setEnabled( True )
                self.__addToIgnoreButton.setEnabled( False )
            else:
                self.__jumpToCodeButton.setEnabled( False )
                excType = str( self.__currentItem.getExceptionType() )
                if self.__ignoredExceptionsViewer.isIgnored( excType ) or \
                   " " in excType or excType.startswith( "unhandled" ):
                    self.__addToIgnoreButton.setEnabled( False )
                else:
                    self.__addToIgnoreButton.setEnabled( True )
        else:
            self.__currentItem = None
            self.__addToIgnoreButton.setEnabled( False )
            self.__jumpToCodeButton.setEnabled( False )
        return

    def __onEnableDisable( self ):
        " Triggered when a breakpoint should be enabled/disabled "
        return

