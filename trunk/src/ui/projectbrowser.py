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

" Project browser with module browsing capabilities "

import os, os.path
from PyQt4.QtCore        import SIGNAL
from utils.pixmapcache   import PixmapCache
from utils.globals       import GlobalData
from projectbrowsermodel import ProjectBrowserModel
from filesbrowserbase    import FilesBrowser
from viewitems           import DirectoryItemType, \
                                TreeViewDirectoryItem, TreeViewFileItem


class ProjectBrowser( FilesBrowser ):
    " Project tree browser "

    def __init__( self, parent = None ):

        FilesBrowser.__init__( self, ProjectBrowserModel(), True, parent )

        self.setWindowTitle( 'Project browser' )
        self.setWindowIcon( PixmapCache().getIcon( 'icon.png' ) )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( GlobalData().project, SIGNAL( 'fsChanged' ),
                      self.__onFSChanged )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "
        self.model().reset()
        return

    def __onFSChanged( self, items ):
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
        treePath = os.path.realpath( treeItem.getPath() ) + os.path.sep
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


    def reload( self ):
        " Reloads the projects view "
        self.model().sourceModel().populateModel()
        self.model().reset()
        self.layoutDisplay()
        return

