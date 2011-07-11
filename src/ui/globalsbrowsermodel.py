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

" Globals browser model "


import os.path
from PyQt4.QtCore       import SIGNAL
from PyQt4.QtCore       import QVariant
from viewitems          import TreeViewGlobalItem
from utils.globals      import GlobalData
from utils.project      import CodimensionProject
from browsermodelbase   import BrowserModelBase
from utils.fileutils    import detectFileType, PythonFileType, Python3FileType


class GlobalsBrowserModel( BrowserModelBase ):
    " Class implementing the globals browser model "

    def __init__( self, parent = None ):
        BrowserModelBase.__init__( self, [ QVariant( "Name" ),
                                           QVariant( "File name" ),
                                           QVariant( "Line" ) ], parent )

        self.__populateModel()

        self.connect( self.globalData.project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( self.globalData.project, SIGNAL( 'fsChanged' ),
                      self.__onFSChanged )
        return

    def __populateModel( self ):
        " Populates the project browser model "

        self.clear()
        project = self.globalData.project
        for fname in project.filesList:
            if fname.endswith( '.py' ) or fname.endswith( '.py3' ):
                info = project.briefModinfoCache.get( fname )
                for globalObj in info.globals:
                    item = TreeViewGlobalItem( self.rootItem, globalObj )
                    item.appendData( [ fname, globalObj.line ] )
                    self._addItem( item, self.rootItem )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what == CodimensionProject.CompleteProject:
            self.__populateModel()
        return

    def __onFSChanged( self, items ):
        " Triggered when files or dirs appeared or removed "

        count = 0
        for path in items:
            path = str( path )
            if path.endswith( os.path.sep ):
                continue # dirs are out of interest
            if not path.endswith( '.py' ) and not path.endswith( '.py3' ):
                continue # not a python file

            if path.startswith( '+' ):
                path = path[ 1: ]
                info = self.globalData.project.briefModinfoCache.get( path )
                for globalObj in info.globals:
                    item = TreeViewGlobalItem( self.rootItem, globalObj )
                    item.appendData( [ path, globalObj.line ] )
                    self._addItem( item, self.rootItem )
                    count += 1
            else:
                path = path[ 1: ]
                idx = len( self.rootItem.childItems ) - 1
                while idx >= 0:
                    item = self.rootItem.childItems[ idx ]
                    if item.getPath() == path:
                        self.rootItem.removeChild( item )
                        count += 1
                    idx -= 1

        if count > 0:
            self.reset()
        return

    def onFileUpdated( self, fileName ):
        " Triggered when a file was updated "

        # Here: python file which belongs to the project
        info = self.globalData.project.briefModinfoCache.get( fileName )

        globalsCopy = list( info.globals )
        itemsToRemove = []
        needUpdate = False

        # For all root items
        path = os.path.realpath( fileName )
        for treeItem in self.rootItem.childItems:
            if os.path.realpath( treeItem.getPath() ) != path:
                continue

            # Item belongs to the modified file
            name = treeItem.data( 0 )
            found = False
            for index in xrange( len( globalsCopy ) ):
                if globalsCopy[ index ].name == name:
                    found = True
                    treeItem.updateData( globalsCopy[ index ] )
                    # Line number might be changed
                    treeItem.setData( 2, globalsCopy[ index ].line )
                    self.__signalItemUpdated( treeItem )
                    del globalsCopy[ index ]
                    break
            if not found:
                itemsToRemove.append( treeItem )

        for item in itemsToRemove:
            needUpdate = True
            self.__removeTreeItem( item )

        # Add those which have been introduced
        for item in globalsCopy:
            needUpdate = True
            newItem = TreeViewGlobalItem( self.rootItem, item )
            newItem.appendData( [ fileName, item.line ] )
            self.__addTreeItem( self.rootItem, newItem )

        return needUpdate

    def __signalItemUpdated( self, treeItem ):
        " Emits a signal that an item is updated "
        index = self.buildIndex( treeItem.getRowPath() )
        self.emit( SIGNAL( "dataChanged(const QModelIndex &," \
                           "const QModelIndex &)" ), index, index )
        return

    def __removeTreeItem( self, treeItem ):
        " Removes the given item "
        index = self.buildIndex( treeItem.getRowPath() )
        self.beginRemoveRows( index.parent(), index.row(), index.row() )
        treeItem.parentItem.removeChild( treeItem )
        self.endRemoveRows()
        return

    def __addTreeItem( self, treeItem, newItem ):
        " Adds the given item "
        parentIndex = self.buildIndex( treeItem.getRowPath() )
        self.addItem( newItem, parentIndex )
        return

