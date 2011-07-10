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
from utils.pixmapcache  import PixmapCache
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
                               TreeViewFileItem, TreeViewCodingItem, \
                               TreeViewGlobalsItem, TreeViewGlobalItem, \
                               TreeViewImportsItem, TreeViewImportItem, \
                               TreeViewWhatItem, TreeViewFunctionItem, \
                               TreeViewFunctionsItem, TreeViewClassesItem, \
                               TreeViewClassItem, TreeViewDecoratorItem, \
                               TreeViewStaticAttributesItem, \
                               TreeViewInstanceAttributesItem, \
                               TreeViewAttributeItem
from utils.fileutils    import CodimensionProjectFileType, \
                               BrokenSymlinkFileType, PixmapFileType, \
                               PythonFileType, Python3FileType
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

    def onFileUpdated( self, fileName, uuid ):
        " Triggered when the file is updated "

        if detectFileType( fileName ) in [ PythonFileType, Python3FileType ]:
            path = os.path.realpath( fileName )
            if GlobalData().project.isProjectFile( fileName ):
                infoSrc = GlobalData().project.briefModinfoCache
            else:
                infoSrc = GlobalData().briefModinfoCache
            info = infoSrc.get( fileName )
            if len( info.errors ) == 0:
                icon = PixmapCache().getIcon( 'filepython.png' )
            else:
                icon = PixmapCache().getIcon( 'filepythonbroken.png' )

            # For all root items
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__walkTreeAndUpdate( treeItem, path, icon, info )
        return

    def __signalItemUpdated( self, treeItem ):
        " Emits a signal that an item is updated "
        srcModel = self.model().sourceModel()
        index = srcModel.buildIndex( treeItem.getRowPath() )
        srcModel.emit( SIGNAL( "dataChanged(const QModelIndex &," \
                               "const QModelIndex &)" ), index, index )
        return

    def __removeTreeItem( self, treeItem ):
        " Removes the given item "
        srcModel = self.model().sourceModel()
        index = srcModel.buildIndex( treeItem.getRowPath() )
        srcModel.beginRemoveRows( index.parent(), index.row(), index.row() )
        treeItem.parentItem.removeChild( treeItem )
        srcModel.endRemoveRows()
        return

    def __addTreeItem( self, treeItem, newItem ):
        " Adds the given item "
        srcModel = self.model().sourceModel()
        parentIndex = srcModel.buildIndex( treeItem.getRowPath() )
        srcModel.addItem( newItem, parentIndex )
        self._resort()
        return

    def __walkTreeAndUpdate( self, treeItem, path, icon, info ):
        " Recursively walks the tree items and updates the icon "

        if treeItem.itemType in [ DirectoryItemType, SysPathItemType ]:
            for i in treeItem.childItems:
                if i.itemType in [ DirectoryItemType, SysPathItemType, FileItemType ]:
                    self.__walkTreeAndUpdate( i, path, icon, info )

        if treeItem.itemType == FileItemType:
            if path == os.path.realpath( treeItem.getPath() ):
                # Update icon
                treeItem.setIcon( icon )
                self.__signalItemUpdated( treeItem )

                # Update content if populated
                hadCoding = False
                hadGlobals = False
                hadImports = False
                hadFunctions = False
                hadClasses = False
                itemsToRemove = []
                for fileChildItem in treeItem.childItems:
                    if fileChildItem.itemType == CodingItemType:
                        hadCoding = True
                        if info.encoding is None:
                            itemsToRemove.append( fileChildItem )
                        else:
                            fileChildItem.updateData( info.encoding )
                            self.__signalItemUpdated( fileChildItem )
                        continue
                    elif fileChildItem.itemType == GlobalsItemType:
                        hadGlobals = True
                        if len( info.globals ) == 0:
                            itemsToRemove.append( fileChildItem )
                        else:
                            fileChildItem.updateData( info )
                            self.__updateGlobalsItem( fileChildItem, info.globals )
                        continue
                    elif fileChildItem.itemType == ImportsItemType:
                        hadImports = True
                        if len( info.imports ) == 0:
                            itemsToRemove.append( fileChildItem )
                        else:
                            fileChildItem.updateData( info )
                            self.__updateImportsItem( fileChildItem, info.imports )
                        continue
                    elif fileChildItem.itemType == FunctionsItemType:
                        hadFunctions = True
                        if len( info.functions ) == 0:
                            itemsToRemove.append( fileChildItem )
                        else:
                            fileChildItem.updateData( info )
                            self.__updateFunctionsItem( fileChildItem, info.functions )
                        continue
                    elif fileChildItem.itemType == ClassesItemType:
                        hadClasses = True
                        if len( info.classes ) == 0:
                            itemsToRemove.append( fileChildItem )
                        else:
                            fileChildItem.updateData( info )
                            self.__updateClassesItem( fileChildItem, info.classes )
                        continue

                for item in itemsToRemove:
                    self.__removeTreeItem( item )

                if not hadCoding and treeItem.populated and \
                   info.encoding is not None:
                    # Coding item appeared, so we need to add it
                    newItem = TreeViewCodingItem( treeItem, info.encoding )
                    self.__addTreeItem( treeItem, newItem )

                if not hadGlobals and treeItem.populated and \
                   len( info.globals ) > 0:
                    # Globals item appeared, so we need to add it
                    newItem = TreeViewGlobalsItem( treeItem, info )
                    self.__addTreeItem( treeItem, newItem )

                if not hadImports and treeItem.populated and \
                   len( info.imports ) > 0:
                    # Imports item appeared, so we need to add it
                    newItem = TreeViewImportsItem( treeItem, info )
                    self.__addTreeItem( treeItem, newItem )

                if not hadFunctions and treeItem.populated and \
                   len( info.functions ) > 0:
                    # Functions item appeared, so we need to add it
                    newItem = TreeViewFunctionsItem( treeItem, info )
                    self.__addTreeItem( treeItem, newItem )

                if not hadClasses and treeItem.populated and \
                   len( info.classes ) > 0:
                    # Classes item appeared, so we need to add it
                    newItem = TreeViewClassesItem( treeItem, info )
                    self.__addTreeItem( treeItem, newItem )
        return

    def __updateGlobalsItem( self, treeItem, globalsObj ):
        " Updates globals item "
        if not treeItem.populated:
            return

        # Need to update item by item. There could be 2 global items with
        # the same name, so this stuff of a copied list.
        globalsCopy = list( globalsObj )
        itemsToRemove = []
        for globalItem in treeItem.childItems:
            name = globalItem.data( 0 )
            found = False
            for index in xrange( len( globalsCopy ) ):
                if globalsCopy[ index ].name == name:
                    found = True
                    globalItem.updateData( globalsCopy[ index ] )
                    # No need to send the update signal because the name is
                    # still the same
                    del globalsCopy[ index ]
                    break
            if not found:
                # Disappeared item
                itemsToRemove.append( globalItem )
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in globalsCopy:
            newItem = TreeViewGlobalItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )

        return

    def __updateImportsItem( self, treeItem, importsObj ):
        " Updates imports item "
        if not treeItem.populated:
            return

        # Need to update item by item. There could be 2 import items with
        # the same name, so this stuff of a copied list.
        importsCopy = list( importsObj )
        itemsToRemove = []
        for importItem in treeItem.childItems:
            name = importItem.data( 0 )
            found = False
            for index in xrange( len( importsCopy ) ):
                if importsCopy[ index ].getDisplayName() == name:
                    found = True
                    importItem.updateData( importsCopy[ index ] )
                    # No need to send the update signal because the name is
                    # still the same, but need to update the importwhat items
                    # if so
                    self.__updateSingleImportItem( importItem, importsCopy[ index ] )
                    del importsCopy[ index ]
                    break
            if not found:
                # Disappeared item
                itemsToRemove.append( importItem )
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in importsCopy:
            newItem = TreeViewImportItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )
        return

    def __updateSingleImportItem( self, treeItem, importObject ):
        " Updates single import item, i.e. importWhat "
        if not treeItem.populated:
            return
        importWhatCopy = list( importObject.what )
        itemsToRemove = []
        for importWhatItem in treeItem.childItems:
            name = importWhatItem.data( 0 )
            found = False
            for index in xrange( len( importWhatCopy ) ):
                if importWhatCopy[ index ].getDisplayName() == name:
                    found = True
                    importWhatItem.updateData( importWhatCopy[ index ] )
                    # No need to send the update signal because the name is
                    # still the same
                    del importWhatCopy[ index ]
                    break
            if not found:
                # Disappeared item
                itemsToRemove.append( importWhatItem )
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in importWhatCopy:
            newItem = TreeViewWhatItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )
        return

    def __updateFunctionsItem( self, treeItem, functionsObj ):
        " Updates the functions item "
        if not treeItem.populated:
            return

        functionsCopy = list( functionsObj )
        itemsToRemove = []
        for functionItem in treeItem.childItems:
            name = functionItem.sourceObj.name
            found = False
            for index in xrange( len( functionsCopy ) ):
                if functionsCopy[ index ].name == name:
                    found = True
                    functionItem.updateData( functionsCopy[ index ] )
                    # arguments could be changed, so send change notification
                    self.__signalItemUpdated( functionItem )
                    self.__updateSingleFunctionItem( functionItem,
                                                     functionsCopy[ index ] )
                    del functionsCopy[ index ]
                    break
            if not found:
                itemsToRemove.append( functionItem )
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in functionsCopy:
            newItem = TreeViewFunctionItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )
        return

    def __updateSingleFunctionItem( self, treeItem, functionObj ):
        " Updates a single function tree item "
        # It may have decor, classes and other functions
        decorCopy = list( functionObj.decorators )
        hadFunctions = False
        hadClasses = False
        itemsToRemove = []
        for funcChildItem in treeItem.childItems:
            if funcChildItem.itemType == DecoratorItemType:
                name = funcChildItem.sourceObj.name
                found = False
                for index in xrange( len( decorCopy ) ):
                    if decorCopy[ index ].name == name:
                        found = True
                        funcChildItem.updateData( decorCopy[ index ] )
                        # arguments could be changed, so send change
                        # notification
                        self.__signalItemUpdated( funcChildItem )
                        del decorCopy[ index ]
                        break
                if not found:
                    itemsToRemove.append( funcChildItem )
                continue
            elif funcChildItem.itemType == FunctionsItemType:
                hadFunctions = True
                if len( functionObj.functions ) == 0:
                    itemsToRemove.append( funcChildItem )
                else:
                    funcChildItem.updateData( functionObj )
                    self.__updateFunctionsItem( funcChildItem,
                                                functionObj.functions )
                continue
            elif funcChildItem.itemType == ClassesItemType:
                hadClasses = True
                if len( functionObj.classes ) == 0:
                    itemsToRemove.append( funcChildItem )
                else:
                    funcChildItem.updateData( functionObj )
                    self.__updateClassesItem( funcChildItem,
                                              functionObj.classes )
                continue
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in decorCopy:
            newItem = TreeViewDecoratorItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )

        if not hadFunctions and treeItem.populated and \
           len( functionObj.functions ) > 0:
            newItem = TreeViewFunctionsItem( treeItem, functionObj )
            self.__addTreeItem( treeItem, newItem )
        if not hadClasses and treeItem.populated and \
           len( functionObj.classes ) > 0:
            newItem = TreeViewClassesItem( treeItem, functionObj )
            self.__addTreeItem( treeItem, newItem )
        return

    def __updateClassesItem( self, treeItem, classesObj ):
        " Updates the classes item "
        if not treeItem.populated:
            return

        classesCopy = list( classesObj )
        itemsToRemove = []
        for classItem in treeItem.childItems:
            name = classItem.sourceObj.name
            found = False
            for index in xrange( len( classesCopy ) ):
                if classesCopy[ index ].name == name:
                    found = True
                    classItem.updateData( classesCopy[ index ] )
                    # arguments could be changed, so send change notification
                    self.__signalItemUpdated( classItem )
                    self.__updateSingleClassItem( classItem,
                                                  classesCopy[ index ] )
                    del classesCopy[ index ]
                    break
            if not found:
                itemsToRemove.append( classItem )
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in classesCopy:
            newItem = TreeViewClassItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )
        return

    def __updateSingleClassItem( self, treeItem, classObj ):
        " Updates a single class item "
        # There might be decorators, classes, methods, static attributes and
        # instance attributes
        decorCopy = list( classObj.decorators )
        methodCopy = list( classObj.functions )
        hadStaticAttributes = False
        hadInstanceAttributes = False
        hadClasses = False
        itemsToRemove = []
        for classChildItem in treeItem.childItems:
            if classChildItem.itemType == DecoratorItemType:
                name = classChildItem.sourceObj.name
                found = False
                for index in xrange( len( decorCopy ) ):
                    if decorCopy[ index ].name == name:
                        found = True
                        classChildItem.updateData( decorCopy[ index ] )
                        # arguments could be changed, so send change
                        # notification
                        self.__signalItemUpdated( classChildItem )
                        del decorCopy[ index ]
                        break
                if not found:
                    itemsToRemove.append( classChildItem )
                continue
            elif classChildItem.itemType == ClassesItemType:
                hadClasses = True
                if len( classObj.classes ) == 0:
                    itemsToRemove.append( classChildItem )
                else:
                    classChildItem.updateData( classObj )
                    self.__updateClassesItem( classChildItem,
                                              classObj.classes )
                continue
            elif classChildItem.itemType == FunctionItemType:
                name = classChildItem.sourceObj.name
                found = False
                for index in xrange( len( methodCopy ) ):
                    if methodCopy[ index ].name == name:
                        found = True
                        classChildItem.updateData( methodCopy[ index ] )
                        # arguments could be changed, so send change notification
                        self.__signalItemUpdated( classChildItem )
                        self.__updateSingleFunctionItem( classChildItem,
                                                         methodCopy[ index ] )
                        del methodCopy[ index ]
                        break
                if not found:
                    itemsToRemove.append( classChildItem )
                continue
            elif classChildItem.itemType == StaticAttributesItemType:
                hadStaticAttributes = True
                if len( classObj.classAttributes ) == 0:
                    itemsToRemove.append( classChildItem )
                else:
                    self.__updateAttrItem( classChildItem,
                                           classObj.classAttributes )
                continue
            elif classChildItem.itemType == InstanceAttributesItemType:
                hadInstanceAttributes = True
                if len( classObj.instanceAttributes ) == 0:
                    itemsToRemove.append( classChildItem )
                else:
                    self.__updateAttrItem( classChildItem,
                                           classObj.instanceAttributes )
                continue

        for item in itemsToRemove:
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in decorCopy:
            newItem = TreeViewDecoratorItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )
        for item in methodCopy:
            newItem = TreeViewFunctionItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )

        if not hadClasses and treeItem.populated and \
           len( classObj.classes ) > 0:
            newItem = TreeViewClassesItem( treeItem, functionObj )
            self.__addTreeItem( treeItem, newItem )
        if not hadStaticAttributes and treeItem.populated and \
           len( classObj.classAttributes ) > 0:
            newItem = TreeViewStaticAttributesItem( treeItem )
            self.__addTreeItem( treeItem, newItem )
        if not hadInstanceAttributes and treeItem.populated and \
           len( classObj.instanceAttributes ) > 0:
            newItem = TreeViewInstanceAttributesItem( treeItem )
            self.__addTreeItem( treeItem, newItem )

        return

    def __updateAttrItem( self, treeItem, attributesObj ):
        " Updates the static attributes list "
        if not treeItem.populated:
            return

        attributesCopy = list( attributesObj )
        itemsToRemove = []
        for attrItem in treeItem.childItems:
            name = attrItem.data( 0 )
            found = False
            for index in xrange( len( attributesCopy ) ):
                if attributesCopy[ index ].name == name:
                    found = True
                    attrItem.updateData( attributesCopy[ index ] )
                    del attributesCopy[ index ]
                    break
            if not found:
                itemsToRemove.append( attrItem )
        for item in itemsToRemove:
            self.__removeTreeItem( item )

        for item in attributesCopy:
            newItem = TreeViewAttributeItem( treeItem, item )
            self.__addTreeItem( treeItem, newItem )
        return

