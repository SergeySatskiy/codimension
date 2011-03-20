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

" Common functionality of various browser models "


import sys, os, logging
from PyQt4.QtCore       import Qt, QAbstractItemModel, QVariant, \
                               QModelIndex
from viewitems          import TreeViewItem, TreeViewDirectoryItem, \
                               TreeViewFileItem, \
                               TreeViewGlobalsItem, TreeViewImportsItem, \
                               TreeViewFunctionsItem, TreeViewClassesItem, \
                               TreeViewStaticAttributesItem, \
                               TreeViewInstanceAttributesItem, \
                               TreeViewCodingItem, TreeViewImportItem, \
                               TreeViewFunctionItem, TreeViewClassItem, \
                               TreeViewDecoratorItem, TreeViewAttributeItem, \
                               TreeViewGlobalItem, TreeViewWhatItem, \
                               DirectoryItemType, SysPathItemType, \
                               FileItemType, GlobalsItemType, \
                               ImportsItemType, FunctionsItemType, \
                               ClassesItemType, StaticAttributesItemType, \
                               InstanceAttributesItemType, \
                               FunctionItemType, ClassItemType, ImportItemType
from utils.fileutils    import detectFileType, PythonFileType, Python3FileType
from utils.globals      import GlobalData
from utils.pixmapcache  import PixmapCache



class BrowserModelBase( QAbstractItemModel ):
    " Class implementing the file system browser model "

    def __init__( self, headerData, parent = None ):
        QAbstractItemModel.__init__( self, parent )

        self.rootItem = TreeViewItem( None, headerData )
        self.globalData = GlobalData()
        self.projectTopLevelDirs = []
        return

    def columnCount( self, parent = QModelIndex() ):
        " Provides the number of columns "
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self.rootItem.columnCount()

    def data( self, index, role ):
        " Provides data of an item "
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            item = index.internalPointer()
            if index.column() < item.columnCount():
                return QVariant( item.data( index.column() ) )
            elif index.column() == item.columnCount() and \
                 index.column() < self.columnCount( self.parent( index ) ):
                # This is for the case when an item under a multi-column
                # parent doesn't have a value for all the columns
                return QVariant( "" )
        elif role == Qt.DecorationRole:
            if index.column() == 0:
                return QVariant( index.internalPointer().getIcon() )
        elif role == Qt.ToolTipRole:
            item = index.internalPointer()
            if item.toolTip != "":
                return QVariant( item.toolTip )

        return QVariant()

    def flags( self, index ):
        " Provides the item flags "
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData( self, section, orientation, role = Qt.DisplayRole ):
        " Provides the header data "
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= self.rootItem.columnCount():
                return QVariant( "" )
            return self.rootItem.data( section )
        return QVariant()

    def index( self, row, column, parent = QModelIndex() ):
        " Creates an index "

        # The model/view framework considers negative values out-of-bounds,
        # however in python they work when indexing into lists. So make sure
        # we return an invalid index for out-of-bounds row/col
        if row < 0 or column < 0 or \
           row >= self.rowCount( parent ) or \
           column >= self.columnCount( parent ):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        try:
            if not parentItem.populated:
                self.populateItem( parentItem )
            childItem = parentItem.child( row )
        except IndexError:
            childItem = None
            return QModelIndex()

        if childItem:
            return self.createIndex( row, column, childItem )
        return QModelIndex()

    def buildIndex( self, rowPath ):
        " Builds index for the path (path is like [ 1, 2, 1, 16 ]) "
        result = QModelIndex()
        for row in rowPath:
            result = self.index( row, 0, result )
        return result

    def parent( self, index ):
        " Provides the index of the parent object "

        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex( parentItem.row(), 0, parentItem )

    def totalRowCount( self ):
        " Provides the total number of rows "
        return self.rootItem.childCount()

    def rowCount( self, parent = QModelIndex() ):
        " Provides the number of rows "

        # Only the first column should have children
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return self.rootItem.childCount()

        parentItem = parent.internalPointer()
        if not parentItem.populated:    # lazy population
            self.populateItem( parentItem )
        return parentItem.childCount()

    def hasChildren( self, parent = QModelIndex() ):
        " Checks for the presence of child items "

        # Only the first column should have children
        if parent.column() > 0:
            return False

        if not parent.isValid():
            return self.rootItem.childCount() > 0

        if parent.internalPointer().lazyPopulation:
            return True

        return parent.internalPointer().childCount() > 0

    def clear( self ):
        " Clears the model "
        self.rootItem.removeChildren()
        self.reset()
        return

    def item( self, index ):
        " Provides a reference to an item "
        if not index.isValid():
            return None
        return index.internalPointer()

    @staticmethod
    def _addItem( itm, parentItem ):
        " Adds an item "
        parentItem.appendChild( itm )
        return

    def addItem( self, itm, parent = QModelIndex() ):
        " Adds an item "

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        cnt = parentItem.childCount()
        self.beginInsertRows( parent, cnt, cnt )
        self._addItem( itm, parentItem )
        self.endInsertRows()
        return

    def populateItem( self, parentItem, repopulate = False ):
        " Populates an item's subtree "

        if parentItem.itemType == DirectoryItemType:
            self.populateDirectoryItem( parentItem, repopulate )
        elif parentItem.itemType == SysPathItemType:
            self.populateSysPathItem( parentItem, repopulate )
        elif parentItem.itemType == FileItemType:
            self.populateFileItem( parentItem, repopulate )
        elif parentItem.itemType == GlobalsItemType:
            self.populateGlobalsItem( parentItem, repopulate )
        elif parentItem.itemType == ImportsItemType:
            self.populateImportsItem( parentItem, repopulate )
        elif parentItem.itemType == FunctionsItemType:
            self.populateFunctionsItem( parentItem, repopulate )
        elif parentItem.itemType == ClassesItemType:
            self.populateClassesItem( parentItem, repopulate )
        elif parentItem.itemType == ClassItemType:
            self.populateClassItem( parentItem, repopulate )
        elif parentItem.itemType == StaticAttributesItemType:
            self.populateStaticAttributesItem( parentItem, repopulate )
        elif parentItem.itemType == InstanceAttributesItemType:
            self.populateInstanceAttributesItem( parentItem, repopulate )
        elif parentItem.itemType == FunctionItemType:
            self.populateFunctionItem( parentItem, repopulate )
        elif parentItem.itemType == ImportItemType:
            self.populateImportItem( parentItem, repopulate )
        return

    def populateDirectoryItem( self, parentItem, repopulate = False ):
        " Populates a directory item's subtree "

        path = parentItem.getPath()
        if not os.path.exists( path ):
            return

        try:
            items = os.listdir( path )
        except Exception, exc:
            logging.error( "Cannot populate directory. " + str( exc ) )
            return

        index = len( items ) - 1
        while index >= 0:
            if items[ index ].startswith( '.svn' ) or \
               items[ index ].startswith( '.cvs' ):
                del items[ index ]
            index -= 1

        if len( items ) > 0:

            # Pick up the modinfo source
            if self.globalData.project.isProjectDir( path ):
                infoSrc = self.globalData.project.briefModinfoCache
            else:
                infoSrc = self.globalData.briefModinfoCache

            if repopulate:
                self.beginInsertRows( self.createIndex( parentItem.row(),
                                                        0, parentItem ),
                                      0, len( items ) - 1 )
            for item in items:
                if os.path.isdir( path + item ):
                    node = TreeViewDirectoryItem( parentItem,
                                                  path + item, False )
                else:
                    node = TreeViewFileItem( parentItem, path + item )
                    if node.fileType in [ PythonFileType, Python3FileType ]:
                        modInfo = infoSrc.get( path + item )
                        node.toolTip = modInfo.docstring

                        if len( modInfo.errors ) > 0:
                            # Substitute icon and change the tooltip
                            node.icon = PixmapCache().getIcon( \
                                                'filepythonbroken.png' )
                            if node.toolTip != "":
                                node.toolTip += "\n\n"
                            node.toolTip += "Parsing errors:\n" + \
                                            "\n".join( modInfo.errors )
                            node.parsingErrors = True

                        if modInfo.encoding is None and \
                           len( modInfo.imports ) == 0 and \
                           len( modInfo.globals ) == 0 and \
                           len( modInfo.functions ) == 0 and \
                           len( modInfo.classes ) == 0:
                            node.populated = True
                            node.lazyPopulation = False

                self._addItem( node, parentItem )

            if repopulate:
                self.endInsertRows()

        parentItem.populated = True
        return

    def populateSysPathItem( self, parentItem, repopulate = False ):
        " Populates the sys.path item's subtree "

        if len( sys.path ) > 0:
            if repopulate:
                self.beginInsertRows( self.createIndex( parentItem.row(),
                                                        0, parentItem ),
                                      0, len( sys.path ) - 1 )
            for path in sys.path:
                if path == '':
                    path = os.getcwd()

                if os.path.isdir( path ):
                    node = TreeViewDirectoryItem( parentItem, path )
                    self._addItem( node, parentItem )
            if repopulate:
                self.endInsertRows()

        parentItem.populated = True
        return

    def populateFileItem( self, parentItem, repopulate = False ):
        " Populate a file item's subtree "

        path = parentItem.getPath()
        if not detectFileType( path ) in [ PythonFileType, Python3FileType ]:
            return

        if self.globalData.project.isProjectFile( path ):
            modInfo = self.globalData.project.briefModinfoCache.get( path )
        else:
            modInfo = self.globalData.briefModinfoCache.get( path )

        # Count the number of rows to insert
        count = 0
        if modInfo.encoding is not None:
            count += 1
        if len( modInfo.imports ) > 0:
            count += 1
        if len( modInfo.globals ) > 0:
            count += 1
        if len( modInfo.functions ) > 0:
            count += 1
        if len( modInfo.classes ) > 0:
            count += 1

        if count == 0:
            return

        # Insert rows
        if repopulate:
            self.beginInsertRows( self.createIndex( parentItem.row(),
                                                    0, parentItem ),
                                  0, count - 1 )
        if modInfo.encoding is not None:
            node = TreeViewCodingItem( parentItem, modInfo.encoding )
            self._addItem( node, parentItem )

        if len( modInfo.imports ) > 0:
            node = TreeViewImportsItem( parentItem, modInfo )
            self._addItem( node, parentItem )

        if len( modInfo.globals ) > 0:
            node = TreeViewGlobalsItem( parentItem, modInfo )
            self._addItem( node, parentItem )

        if len( modInfo.functions ) > 0:
            node = TreeViewFunctionsItem( parentItem, modInfo )
            self._addItem( node, parentItem )

        if len( modInfo.classes ) > 0:
            node = TreeViewClassesItem( parentItem, modInfo )
            self._addItem( node, parentItem )

        if repopulate:
            self.endInsertRows()

        return

    def __populateList( self, parentItem, items, itemClass,
                        repopulate = False ):
        " Helper for populating lists "

        if repopulate:
            self.beginInsertRows( self.createIndex( parentItem.row(),
                                                    0, parentItem ),
                                  0, len( items ) - 1 )
        for item in items:
            treeItem = itemClass( parentItem, item )
            if parentItem.columnCount() > 1:
                treeItem.appendData( parentItem.data( 1 ) )
                treeItem.appendData( item.line )
            self._addItem( treeItem, parentItem )

        if repopulate:
            self.endInsertRows()
        return

    def populateGlobalsItem( self, parentItem, repopulate = False ):
        " Populates the globals item "

        self.__populateList( parentItem, parentItem.sourceObj.globals,
                             TreeViewGlobalItem, repopulate )
        return


    def populateImportsItem( self, parentItem, repopulate = False ):
        " Populates the imports item "

        self.__populateList( parentItem, parentItem.sourceObj.imports,
                             TreeViewImportItem, repopulate )
        return

    def populateFunctionsItem( self, parentItem, repopulate = False ):
        " Populates functions item "

        self.__populateList( parentItem, parentItem.sourceObj.functions,
                             TreeViewFunctionItem, repopulate )
        return


    def populateClassesItem( self, parentItem, repopulate = False ):
        " Populate classes item "

        self.__populateList( parentItem, parentItem.sourceObj.classes,
                             TreeViewClassItem, repopulate )
        return


    def populateClassItem( self, parentItem, repopulate ):
        " Populates a class item "

        # Count the number of items
        count = len( parentItem.sourceObj.decorators ) + \
                len( parentItem.sourceObj.functions )

        if len( parentItem.sourceObj.classes ) > 0:
            count += 1
        if len( parentItem.sourceObj.classAttributes ) > 0:
            count += 1
        if len( parentItem.sourceObj.instanceAttributes ) > 0:
            count += 1

        if count == 0:
            return

        # Insert rows
        if repopulate:
            self.beginInsertRows( self.createIndex( parentItem.row(),
                                                    0, parentItem ),
                                  0, count - 1 )
        for item in parentItem.sourceObj.decorators:
            node = TreeViewDecoratorItem( parentItem, item )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( item.line )
            self._addItem( node, parentItem )

        for item in parentItem.sourceObj.functions:
            node = TreeViewFunctionItem( parentItem, item )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( item.line )
            self._addItem( node, parentItem )

        if len( parentItem.sourceObj.classes ) > 0:
            node = TreeViewClassesItem( parentItem, parentItem.sourceObj )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( 'n/a' )
            self._addItem( node, parentItem )

        if len( parentItem.sourceObj.classAttributes ) > 0:
            node = TreeViewStaticAttributesItem( parentItem )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( 'n/a' )
            self._addItem( node, parentItem )

        if len( parentItem.sourceObj.instanceAttributes ) > 0:
            node = TreeViewInstanceAttributesItem( parentItem )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( 'n/a' )
            self._addItem( node, parentItem )

        if repopulate:
            self.endInsertRows()

        return

    def populateFunctionItem( self, parentItem, repopulate ):
        " Populates a function item "

        # Count the number of items
        count = len( parentItem.sourceObj.decorators )

        if len( parentItem.sourceObj.functions ) > 0:
            count += 1
        if len( parentItem.sourceObj.classes ) > 0:
            count += 1

        if count == 0:
            return

        # Insert rows
        if repopulate:
            self.beginInsertRows( self.createIndex( parentItem.row(),
                                                    0, parentItem ),
                                  0, count - 1 )
        for item in parentItem.sourceObj.decorators:
            node = TreeViewDecoratorItem( parentItem, item )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( item.line )
            self._addItem( node, parentItem )

        if len( parentItem.sourceObj.functions ) > 0:
            node = TreeViewFunctionsItem( parentItem, parentItem.sourceObj )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( 'n/a' )
            self._addItem( node, parentItem )

        if len( parentItem.sourceObj.classes ) > 0:
            node = TreeViewClassesItem( parentItem, parentItem.sourceObj )
            if parentItem.columnCount() > 1:
                node.appendData( parentItem.data( 1 ) )
                node.appendData( 'n/a' )
            self._addItem( node, parentItem )

        if repopulate:
            self.endInsertRows()

        return

    def populateStaticAttributesItem( self, parentItem, repopulate ):
        " Populates a static attributes item "

        self.__populateList( parentItem,
                             parentItem.parentItem.sourceObj.classAttributes,
                             TreeViewAttributeItem, repopulate )
        return

    def populateInstanceAttributesItem( self, parentItem, repopulate ):
        " Populates an instance attributes item "

        self.__populateList( parentItem,
                             parentItem.parentItem.sourceObj.instanceAttributes,
                             TreeViewAttributeItem, repopulate )
        return

    def populateImportItem( self, parentItem, repopulate ):
        " Populate an import item "

        self.__populateList( parentItem, parentItem.sourceObj.what,
                             TreeViewWhatItem, repopulate )
        return

