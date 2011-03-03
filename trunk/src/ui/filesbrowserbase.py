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


" Base and auxiliary classes for FS and project browsers "


import os.path, logging
from PyQt4.QtCore       import Qt, QModelIndex, SIGNAL
from PyQt4.QtGui        import QAbstractItemView, QApplication, \
                               QSortFilterProxyModel, QTreeView, \
                               QCursor
from utils.globals      import GlobalData
from viewitems          import DirectoryItemType, SysPathItemType, \
                               GlobalsItemType, ImportsItemType, \
                               FunctionsItemType, ClassesItemType, \
                               StaticAttributesItemType, \
                               InstanceAttributesItemType, \
                               CodingItemType, ImportItemType, \
                               FileItemType, FunctionItemType, \
                               ClassItemType, DecoratorItemType, \
                               AttributeItemType, GlobalItemType, \
                               ImportWhatItemType, TreeViewDirectoryItem, \
                               TreeViewFileItem
from utils.fileutils    import CodimensionProjectFileType, \
                               BrokenSymlinkFileType, PixmapFileType
from itemdelegates      import NoOutlineHeightDelegate
from parsererrors       import ParserErrorsDialog
from utils.fileutils    import detectFileType
from findinfiles        import FindInFilesDialog


class FilesBrowserSortFilterProxyModel( QSortFilterProxyModel ):
    """
    Files (filesystem and project) browser sort filter proxy model
    implementation. It allows filtering basing on top level items.
    """

    def __init__( self, isProjectFilter, parent = None ):
        QSortFilterProxyModel.__init__( self, parent )
        self.__sortColumn = None    # Avoid pylint complains
        self.__sortOrder = None     # Avoid pylint complains
        self.__shouldFilter = isProjectFilter
        return

    def sort( self, column, order ):
        " Sorts the items "
        self.__sortColumn = column
        self.__sortOrder = order
        QSortFilterProxyModel.sort( self, column, order )
        return

    def lessThan( self, left, right ):
        " Sorts the displayed items "
        lhs = left.model() and left.model().item( left ) or None
        rhs = right.model() and right.model().item( right ) or None

        if lhs and rhs:
            return lhs.lessThan( rhs, self.__sortColumn, self.__sortOrder )
        return False

    def item( self, index ):
        " Provides a reference to the item "
        if not index.isValid():
            return None

        sourceIndex = self.mapToSource( index )
        return self.sourceModel().item( sourceIndex )

    def hasChildren( self, parent = QModelIndex() ):
        " Checks the presence of the child items "
        sourceIndex = self.mapToSource( parent )
        return self.sourceModel().hasChildren( sourceIndex )

    def filterAcceptsRow( self, sourceRow, sourceParent ):
        " Filters rows "
        if not self.__shouldFilter:
            return True     # Show everything

        # Filter using the loaded project filter
        if not sourceParent.isValid():
            return True

        item = sourceParent.internalPointer().child( sourceRow )
        return not GlobalData().project.shouldExclude( item.data( 0 ) )



class FilesBrowser( QTreeView ):
    " Common functionality of the FS and project browsers "

    def __init__( self, sourceModel, isProjectFilter, parent = None ):
        QTreeView.__init__(self, parent)

        self.__model = sourceModel
        self.__sortModel = FilesBrowserSortFilterProxyModel( isProjectFilter )
        self.__sortModel.setSourceModel( self.__model )
        self.setModel( self.__sortModel )

        self.connect( self, SIGNAL( "activated(const QModelIndex &)" ),
                      self.openSelectedItem )
        self.connect( self, SIGNAL( "expanded(const QModelIndex &)" ),
                      self._resizeColumns )
        self.connect( self, SIGNAL( "collapsed(const QModelIndex &)" ),
                      self._resizeColumns )

        self.setRootIsDecorated( True )
        self.setAlternatingRowColors( True )
        self.setUniformRowHeights( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        header = self.header()
        header.setSortIndicator( 0, Qt.AscendingOrder )
        header.setSortIndicatorShown( True )
        header.setClickable( True )

        self.setSortingEnabled( True )

        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )

        self.header().setStretchLastSection( True )
        self.layoutDisplay()
        return

    def layoutDisplay( self ):
        " Performs the layout operation "
        self.doItemsLayout()
        self._resizeColumns( QModelIndex() )
        self._resort()
        return

    def _resizeColumns( self, index ):
        " Resizes the view when items get expanded or collapsed "

        rowCount = self.model().rowCount()
        self.header().setStretchLastSection( True )

        width = max( 100, self.sizeHintForColumn( 0 ) )
        self.header().resizeSection( 0, width )
        return

    def _resort( self ):
        " Re-sorts the tree "
        self.model().sort( self.header().sortIndicatorSection(),
                           self.header().sortIndicatorOrder() )
        return

    def mouseDoubleClickEvent( self, mouseEvent ):
        """
        Reimplemented to disable expanding/collapsing of items when
        double-clicking. Instead the double-clicked entry is opened.
        """

        index = self.indexAt( mouseEvent.pos() )
        if not index.isValid():
            return

        item = self.model().item( index )
        if item.itemType in [ GlobalsItemType,
                              ImportsItemType, FunctionsItemType,
                              ClassesItemType, StaticAttributesItemType,
                              InstanceAttributesItemType,
                              DirectoryItemType, SysPathItemType ]:
            QTreeView.mouseDoubleClickEvent( self, mouseEvent )
        else:
            self.openItem( item )
        return

    def openSelectedItem( self ):
        " Triggers when an item is clicked or double clicked "
        item = self.model().item( self.currentIndex() )
        self.openItem( item )
        return

    def openItem( self, item ):
        " Handles the case when an item is activated "
        if item.itemType in [ GlobalsItemType,
                              ImportsItemType, FunctionsItemType,
                              ClassesItemType, StaticAttributesItemType,
                              InstanceAttributesItemType,
                              DirectoryItemType, SysPathItemType ]:
            return
        if item.itemType == FileItemType:
            if item.fileType == BrokenSymlinkFileType:
                return

            itemPath = item.getPath()
            if not os.path.exists( itemPath ):
                logging.error( "Cannot open " + itemPath )
                return

            if os.path.islink( itemPath ):
                # Convert it to the real path and the decide what to do
                itemPath = os.path.realpath( itemPath )
                # The type may differ...
                itemFileType = detectFileType( itemPath )
            else:
                # The intermediate directory could be a link, so use the real
                # path
                itemPath = os.path.realpath( itemPath )
                itemFileType = item.fileType

            if itemFileType == CodimensionProjectFileType:
                # This not the current project. Load it if still exists.
                if itemPath != GlobalData().project.fileName:
                    QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
                    try:
                        GlobalData().project.loadProject( itemPath )
                    except Exception, exc:
                        logging.error( str( exc ) )
                    QApplication.restoreOverrideCursor()
                    return
                else:
                    # This is the currenly loaded project
                    # Make it possible to look at the project file content
                    # I trust the developer
                    pass
            GlobalData().mainWindow.openFileByType( itemFileType, itemPath, -1 )
            return
        if item.itemType in [ CodingItemType, ImportItemType, FunctionItemType,
                              ClassItemType, DecoratorItemType,
                              AttributeItemType, GlobalItemType,
                              ImportWhatItemType ]:
            GlobalData().mainWindow.openFile( item.getPath(),
                                              item.sourceObj.line )
        return

    def copyToClipboard( self ):
        " Copies the path to the file where the element is to the clipboard "
        item = self.model().item( self.currentIndex() )
        path = item.getPath()
        QApplication.clipboard().setText( path )
        return

    def showParsingErrors( self, path ):
        " Fires the show errors dialog window "

        try:
            dialog = ParserErrorsDialog( path )
            dialog.exec_()
        except Exception, ex:
            logging.error( str( ex ) )
        return

    def findInDirectory( self ):
        " Find in directory popup menu handler "
        index = self.currentIndex()
        searchDir = self.model().item( index ).getPath()

        dlg = FindInFilesDialog( FindInFilesDialog.inDirectory,
                                 "", searchDir )
        dlg.exec_()
        if len( dlg.searchResults ) != 0:
            GlobalData().mainWindow.displayFindInFiles( dlg.searchRegexp,
                                                        dlg.searchResults )
        return

    def selectionChanged( self, selected, deselected ):
        " Triggered when the selection changed "

        QTreeView.selectionChanged( self, selected, deselected )
        indexesList = selected.indexes()
        if len( indexesList ) == 0:
            self.emit( SIGNAL( 'firstSelectedItem' ), None )
        else:
            self.emit( SIGNAL( 'firstSelectedItem' ), indexesList[ 0 ] )
        return

    def _onFSChanged( self, items ):
        " Triggered when the project files set has been changed "

        itemsToDel = []
        itemsToAdd = []
        for item in items:
            item = str( item )
            if item.startswith( '-' ):
                itemsToDel.append( item[ 1: ] )
            else:
                itemsToAdd.append( item[ 1: ] )
        itemsToDel.sort()
        itemsToAdd.sort()

        # It is important that items are deleted first and then new are added!
        for item in itemsToDel:
            dirname, basename = self.__splitPath( item )

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__delFromTree( treeItem, dirname, basename )


        for item in itemsToAdd:
            dirname, basename = self.__splitPath( item )

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__addToTree( treeItem, item, dirname, basename )


        self.layoutDisplay()
        return

    def __addToTree( self, treeItem, item, dirname, basename ):
        " Recursive function which adds an item to the displayed tree "

        # treeItem is always of the directory type
        if not treeItem.populated:
            return

        srcModel = self.model().sourceModel()
        treePath = treeItem.getPath()
        if treePath != "":
            # Guard for the sys.path item
            treePath = os.path.realpath( treePath ) + os.path.sep
        if treePath == dirname:
            # Need to add an item but only if there is no this item already!
            foundInChildren = False
            for i in treeItem.childItems:
                if basename == i.data( 0 ):
                    foundInChildren = True
                    break

            if not foundInChildren:
                if item.endswith( os.path.sep ):
                    newItem = TreeViewDirectoryItem( \
                                treeItem, treeItem.getPath() + basename, False )
                else:
                    newItem = TreeViewFileItem( treeItem,
                                                treeItem.getPath() + basename )
                parentIndex = srcModel.buildIndex( treeItem.getRowPath() )
                srcModel.addItem( newItem, parentIndex )

        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                self.__addToTree( i, item, dirname, basename )
            elif i.isLink:
                # Check if it was a broken link to the newly appeared item
                if os.path.realpath( i.getPath() ) == dirname + basename:
                    # Update the link status
                    i.updateLinkStatus( i.getPath() )
                    index = srcModel.buildIndex( i.getRowPath() )
                    srcModel.emit( SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
                                   index, index )
        return


    def __delFromTree( self, treeItem, dirname, basename ):
        " Recursive function which deletes an item from the displayed tree "

        # treeItem is always of the directory type
        srcModel = self.model().sourceModel()

        d_dirname, d_basename = self.__splitPath( treeItem.getPath() )
        if d_dirname == dirname and d_basename == basename:
            index = srcModel.buildIndex( treeItem.getRowPath() )
            srcModel.beginRemoveRows( index.parent(), index.row(), index.row() )
            treeItem.parentItem.removeChild( treeItem )
            srcModel.endRemoveRows()
            return

        if treeItem.isLink:
            # Link to a directory
            if os.path.realpath( treeItem.getPath() ) == dirname + basename:
                # Broken link now
                treeItem.updateStatus()
                index = srcModel.buildIndex( treeItem.getRowPath() )
                srcModel.emit( SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
                               index, index )
                return


        # Walk the directory items
        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                # directory
                self.__delFromTree( i, dirname, basename )
            else:
                # file
                if i.isLink:
                    l_dirname, l_basename = self.__splitPath( i.getPath() )
                    if dirname == l_dirname and basename == l_basename:
                        index = srcModel.buildIndex( i.getRowPath() )
                        srcModel.beginRemoveRows( index.parent(),
                                                  index.row(), index.row() )
                        i.parentItem.removeChild( i )
                        srcModel.endRemoveRows()
                    elif os.path.realpath( i.getPath() ) == dirname + basename:
                        i.updateLinkStatus( i.getPath() )
                        index = srcModel.buildIndex( i.getRowPath() )
                        srcModel.emit( SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
                                       index, index )
                else:
                    # Regular final file
                    if os.path.realpath( i.getPath() ) == dirname + basename:
                        index = srcModel.buildIndex( i.getRowPath() )
                        srcModel.beginRemoveRows( index.parent(),
                                                  index.row(), index.row() )
                        i.parentItem.removeChild( i )
                        srcModel.endRemoveRows()

        return

    @staticmethod
    def __splitPath( path ):
        " Provides the dirname and the base name "
        if path.endswith( os.path.sep ):
            # directory
            dirname = os.path.realpath( os.path.dirname( path[ :-1 ] ) ) + \
                      os.path.sep
            basename = os.path.basename( path[ :-1 ] )
        else:
            dirname = os.path.realpath( os.path.dirname( path ) ) + os.path.sep
            basename = os.path.basename( path )
        return dirname, basename

