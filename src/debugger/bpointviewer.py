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


from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import ( QSizePolicy, QFrame, QTreeView, QToolButton,
                          QHeaderView, QVBoxLayout, QSortFilterProxyModel,
                          QLabel, QWidget, QAbstractItemView, QMenu,
                          QSpacerItem, QHBoxLayout, QPalette, QCursor,
                          QItemSelectionModel, QDialog )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.project import CodimensionProject
from editbreakpoint import BreakpointEditDialog


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
        self.layoutDisplay()
        return

    def layoutDisplay( self ):
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
        self.__editAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpprops.png' ),
                                "Edit...", self.__editBreak )
        self.__jumpToCodeAct = self.menu.addAction(
                                PixmapCache().getIcon( 'gotoline.png' ),
                                "Jump to code", self.__showSource )
        self.menu.addSeparator()
        self.__enableAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpenable.png' ),
                                "Enable", self.enableBreak )
        self.__enableAllAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpenableall.png' ),
                                "Enable all", self.enableAllBreaks )
        self.menu.addSeparator()
        self.__disableAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpdisable.png' ),
                                "Disable", self.disableBreak )
        self.__disableAllAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpdisableall.png' ),
                                "Disable all", self.disableAllBreaks )
        self.menu.addSeparator()
        self.__delAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpdel.png' ),
                                "Delete", self.deleteBreak )
        self.__delAllAct = self.menu.addAction(
                                PixmapCache().getIcon( 'bpdelall.png' ),
                                "Delete all", self.deleteAllBreaks )
        return

    def __showContextMenu( self, coord ):
        " Shows the context menu "
        index = self.currentIndex()
        if not index.isValid():
            return
        sindex = self.toSourceIndex( index )
        if not sindex.isValid():
            return
        bp = self.__model.getBreakPointByIndex( sindex )
        if not bp:
            return

        enableCount, disableCount = self.__model.getCounts()

        self.__editAct.setEnabled( True )
        self.__enableAct.setEnabled( not bp.isEnabled() )
        self.__disableAct.setEnabled( bp.isEnabled() )
        self.__jumpToCodeAct.setEnabled( True )
        self.__delAct.setEnabled( True )
        self.__enableAllAct.setEnabled( disableCount > 0 )
        self.__disableAllAct.setEnabled( enableCount > 0 )
        self.__delAllAct.setEnabled( enableCount + disableCount > 0 )

        self.menu.popup( QCursor.pos() )
        return

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

            dlg = BreakpointEditDialog( bp )
            if dlg.exec_() == QDialog.Accepted:
                newBpoint = dlg.getData()
                if newBpoint == bp:
                    return
                self.__model.setBreakPointByIndex( sindex, newBpoint )
                self.layoutDisplay()
        return

    def __setBpEnabled( self, index, enabled ):
        " Sets the enabled status of a breakpoint "
        sindex = self.toSourceIndex( index )
        if sindex.isValid():
            self.__model.setBreakPointEnabledByIndex( sindex, enabled )
        return

    def enableBreak( self ):
        " Handles the enable breakpoint context menu entry "
        index = self.currentIndex()
        self.__setBpEnabled( index, True )
        self.__resizeColumns()
        self.__resort()
        return

    def enableAllBreaks( self ):
        " Handles the enable all breakpoints context menu entry "
        index = self.model().index( 0, 0 )
        while index.isValid():
            self.__setBpEnabled( index, True )
            index = self.indexBelow( index )
        self.__resizeColumns()
        self.__resort()
        return

    def disableBreak( self ):
        " Handles the disable breakpoint context menu entry "
        index = self.currentIndex()
        self.__setBpEnabled( index, False )
        self.__resizeColumns()
        self.__resort()
        return

    def disableAllBreaks( self ):
        " Handles the disable all breakpoints context menu entry "
        index = self.model().index( 0, 0 )
        while index.isValid():
            self.__setBpEnabled( index, False )
            index = self.indexBelow( index )
        self.__resizeColumns()
        self.__resort()
        return

    def deleteBreak( self ):
        " Handles the delete breakpoint context menu entry "
        index = self.currentIndex()
        sindex = self.toSourceIndex( index )
        if sindex.isValid():
            self.__model.deleteBreakPointByIndex( sindex )
        return

    def deleteAllBreaks( self ):
        " Handles the delete all breakpoints context menu entry "
        self.__model.deleteAll()
        return

    def __showSource( self ):
        " Handles the goto context menu entry "
        index = self.currentIndex()
        self.__doubleClicked( index )
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
        self.connect( bpointsModel,
                      SIGNAL( 'BreakpoinsChanged' ),
                      self.__onModelChanged )
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
        self.__enableButton.setToolTip( "Enable the breakpoint" )
        self.__enableButton.setFocusPolicy( Qt.NoFocus )
        self.__enableButton.setEnabled( False )
        self.connect( self.__enableButton,
                      SIGNAL( 'clicked()' ),
                      self.__onEnableDisable )

        self.__disableButton = QToolButton()
        self.__disableButton.setIcon( PixmapCache().getIcon( 'bpdisable.png' ) )
        self.__disableButton.setFixedSize( 24, 24 )
        self.__disableButton.setToolTip( "Disable the breakpoint" )
        self.__disableButton.setFocusPolicy( Qt.NoFocus )
        self.__disableButton.setEnabled( False )
        self.connect( self.__disableButton,
                      SIGNAL( 'clicked()' ),
                      self.__onEnableDisable )

        self.__enableAllButton = QToolButton()
        self.__enableAllButton.setIcon( PixmapCache().getIcon( 'bpenableall.png' ) )
        self.__enableAllButton.setFixedSize( 24, 24 )
        self.__enableAllButton.setToolTip( "Enable all the breakpoint" )
        self.__enableAllButton.setFocusPolicy( Qt.NoFocus )
        self.__enableAllButton.setEnabled( False )
        self.connect( self.__enableAllButton,
                      SIGNAL( 'clicked()' ),
                      self.__onEnableAll )

        self.__disableAllButton = QToolButton()
        self.__disableAllButton.setIcon( PixmapCache().getIcon( 'bpdisableall.png' ) )
        self.__disableAllButton.setFixedSize( 24, 24 )
        self.__disableAllButton.setToolTip( "Disable all the breakpoint" )
        self.__disableAllButton.setFocusPolicy( Qt.NoFocus )
        self.__disableAllButton.setEnabled( False )
        self.connect( self.__disableAllButton,
                      SIGNAL( 'clicked()' ),
                      self.__onDisableAll )

        self.__jumpToCodeButton = QToolButton()
        self.__jumpToCodeButton.setIcon( PixmapCache().getIcon( 'gotoline.png' ) )
        self.__jumpToCodeButton.setFixedSize( 24, 24 )
        self.__jumpToCodeButton.setToolTip( "Jump to the code" )
        self.__jumpToCodeButton.setFocusPolicy( Qt.NoFocus )
        self.__jumpToCodeButton.setEnabled( False )
        self.connect( self.__jumpToCodeButton,
                      SIGNAL( 'clicked()' ),
                      self.__onJumpToCode )

        self.__delButton = QToolButton()
        self.__delButton.setIcon( PixmapCache().getIcon( 'bpdel.png' ) )
        self.__delButton.setFixedSize( 24, 24 )
        self.__delButton.setToolTip( "Delete the breakpoint" )
        self.__delButton.setFocusPolicy( Qt.NoFocus )
        self.__delButton.setEnabled( False )
        self.connect( self.__delButton,
                      SIGNAL( 'clicked()' ),
                      self.__onDel )

        self.__delAllButton = QToolButton()
        self.__delAllButton.setIcon( PixmapCache().getIcon( 'bpdelall.png' ) )
        self.__delAllButton.setFixedSize( 24, 24 )
        self.__delAllButton.setToolTip( "Delete all the breakpoint" )
        self.__delAllButton.setFocusPolicy( Qt.NoFocus )
        self.__delAllButton.setEnabled( False )
        self.connect( self.__delAllButton,
                      SIGNAL( 'clicked()' ),
                      self.__onDelAll )


        toolbarLayout = QHBoxLayout()
        toolbarLayout.addWidget( self.__editButton )
        toolbarLayout.addWidget( self.__jumpToCodeButton )
        fixedSpacer2 = QSpacerItem( 5, 5 )
        toolbarLayout.addSpacerItem( fixedSpacer2 )
        toolbarLayout.addWidget( self.__enableButton )
        toolbarLayout.addWidget( self.__enableAllButton )
        fixedSpacer3 = QSpacerItem( 5, 5 )
        toolbarLayout.addSpacerItem( fixedSpacer3 )
        toolbarLayout.addWidget( self.__disableButton )
        toolbarLayout.addWidget( self.__disableAllButton )
        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer4 = QSpacerItem( 5, 5 )
        toolbarLayout.addSpacerItem( fixedSpacer4 )
        toolbarLayout.addSpacerItem( expandingSpacer )
        toolbarLayout.addWidget( self.__delButton )
        fixedSpacer5 = QSpacerItem( 5, 5 )
        toolbarLayout.addSpacerItem( fixedSpacer5 )
        toolbarLayout.addWidget( self.__delAllButton )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addLayout( toolbarLayout )
        verticalLayout.addWidget( self.__bpointsList )
        return

    def clear( self ):
        " Clears the content "
        self.__onDelAll()
        self.__updateBreakpointsLabel()
        self.__currentItem = None
        return

    def __updateBreakpointsLabel( self ):
        " Updates the breakpoints header label "
        enableCount, \
        disableCount = self.__bpointsList.model().sourceModel().getCounts()
        total = enableCount + disableCount
        if total > 0:
            self.__breakpointLabel.setText( "Breakpoints (total: " +
                                       str( total ) + ")" )
        else:
            self.__breakpointLabel.setText( "Breakpoints" )
        return

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

        enableCount, \
        disableCount = self.__bpointsList.model().sourceModel().getCounts()

        if self.__currentItem is None:
            self.__editButton.setEnabled( False )
            self.__enableButton.setEnabled( False )
            self.__disableButton.setEnabled( False )
            self.__jumpToCodeButton.setEnabled( False )
            self.__delButton.setEnabled( False )
        else:
            self.__editButton.setEnabled( True )
            self.__enableButton.setEnabled( not self.__currentItem.isEnabled() )
            self.__disableButton.setEnabled( self.__currentItem.isEnabled() )
            self.__jumpToCodeButton.setEnabled( True )
            self.__delButton.setEnabled( True )

        self.__enableAllButton.setEnabled( disableCount > 0 )
        self.__disableAllButton.setEnabled( enableCount > 0 )
        self.__delAllButton.setEnabled( enableCount + disableCount > 0 )
        return

    def __onEnableDisable( self ):
        " Triggered when a breakpoint should be enabled/disabled "
        if self.__currentItem is None:
            return

        if self.__currentItem.isEnabled():
            self.__bpointsList.disableBreak()
        else:
            self.__bpointsList.enableBreak()
        return

    def __onEdit( self ):
        " Triggered when a breakpoint should be edited "
        if self.__currentItem is None:
            return

        dlg = BreakpointEditDialog( self.__currentItem )
        if dlg.exec_() == QDialog.Accepted:
            newBpoint = dlg.getData()
            if newBpoint == self.__currentItem:
                return
            model = self.__bpointsList.model().sourceModel()
            index = model.getBreakPointIndex( self.__currentItem.getAbsoluteFileName(),
                                              self.__currentItem.getLineNumber() )
            model.setBreakPointByIndex( index, newBpoint )
            self.__bpointsList.layoutDisplay()
        return

    def __onJumpToCode( self ):
        " Triggered when should jump to source "
        if self.__currentItem is None:
            return
        self.__bpointsList.jumpToCode( self.__currentItem.getAbsoluteFileName(),
                                       self.__currentItem.getLineNumber() )
        return

    def __onEnableAll( self ):
        " Triggered when all the breakpoints should be enabled "
        self.__bpointsList.enableAllBreaks()
        return

    def __onDisableAll( self ):
        " Triggered when all the breakpoints should be disabled "
        self.__bpointsList.disableAllBreaks()
        return

    def __onDel( self ):
        " Triggered when a breakpoint should be deleted "
        if self.__currentItem is None:
            return
        self.__bpointsList.deleteBreak()
        return

    def __onDelAll( self ):
        " Triggered when all the breakpoints should be deleted "
        self.__bpointsList.deleteAllBreaks()
        return

    def __onModelChanged( self ):
        " Triggered when something has changed in any of the breakpoints "
        self.__updateBreakpointsLabel()
        self.__updateButtons()
        self.__bpointsList.layoutDisplay()
        return
