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
                               QSortFilterProxyModel, QTreeView
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
                               ImportWhatItemType
from utils.fileutils    import CodimensionProjectFileType, \
                               BrokenSymlinkFileType, PixmapFileType
from itemdelegates      import NoOutlineHeightDelegate
from parsererrors       import ParserErrorsDialog



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
            if item.fileType == PixmapFileType:
                GlobalData().mainWindow.openPixmapFile( item.getPath() )
                return
            if item.fileType == CodimensionProjectFileType:
                # This not the current project. Load it if still exists.
                if item.getPath() != GlobalData().project.fileName:
                    if os.path.exists( item.getPath() ):
                        GlobalData().project.loadProject( item.getPath() )
                    else:
                        logging.error( "The project " + \
                                       os.path.basename( item.getPath() ) + \
                                       " disappeared from the file system." )
                else:
                    return  # This is the currenly loaded project
            GlobalData().mainWindow.openFile( item.getPath(), -1 )
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

        #findFilesDialog = e4App().getObject("FindFilesDialog")
        #findFilesDialog.setSearchDirectory(searchDir)
        #findFilesDialog.show()
        #findFilesDialog.raise_()
        #findFilesDialog.activateWindow()
        return

    def replaceInDirectory( self ):
        " Find & Replace in directory popup menu handler "
        index = self.currentIndex()
        searchDir = self.model().item( index ).getPath()

        #replaceFilesDialog = e4App().getObject("ReplaceFilesDialog")
        #replaceFilesDialog.setSearchDirectory(searchDir)
        #replaceFilesDialog.show()
        #replaceFilesDialog.raise_()
        #replaceFilesDialog.activateWindow()
        return

