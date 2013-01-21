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

" Classes browser model "


import os.path
from PyQt4.QtCore       import SIGNAL
from PyQt4.QtCore       import QVariant
from viewitems          import TreeViewClassItem
from utils.project      import CodimensionProject
from browsermodelbase   import BrowserModelBase


class ClassesBrowserModel( BrowserModelBase ):
    " Class implementing the project browser model "

    def __init__( self, parent = None ):
        BrowserModelBase.__init__( self, [ QVariant( "Name" ),
                                           QVariant( "File name" ),
                                           QVariant( "Line" ) ], parent )

        self.__populateModel()

        self.connect( self.globalData.project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def __populateModel( self ):
        " Populates the project browser model "

        self.clear()
        project = self.globalData.project
        for fname in project.filesList:
            if fname.endswith( '.py' ) or fname.endswith( '.py3' ) or \
               fname.endswith( '.pyw' ):
                info = project.briefModinfoCache.get( fname )
                for classObj in info.classes:
                    item = TreeViewClassItem( self.rootItem, classObj )
                    item.appendData( [ fname, classObj.line ] )
                    self._addItem( item, self.rootItem )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what == CodimensionProject.CompleteProject:
            self.__populateModel()
        return

    def onFSChanged( self, addedPythonFiles, deletedPythonFiles ):
        " Triggered when some files appeared or disappeared "

        needUpdate = False
        itemsToDelete = []
        for path in deletedPythonFiles:
            for item in self.rootItem.childItems:
                if os.path.realpath( path ) == \
                   os.path.realpath( item.getPath() ):
                    itemsToDelete.append( item )

        for item in itemsToDelete:
            needUpdate = True
            self.removeTreeItem( item )

        for path in addedPythonFiles:
            info = self.globalData.project.briefModinfoCache.get( path )
            for classObj in info.classes:
                needUpdate = True
                newItem = TreeViewClassItem( self.rootItem, classObj )
                newItem.appendData( path )
                newItem.appendData( classObj.line )
                self.addTreeItem( self.rootItem, newItem )
        return needUpdate

    def onFileUpdated( self, fileName ):
        " Triggered when a file was updated "

        # Here: python file which belongs to the project
        info = self.globalData.project.briefModinfoCache.get( fileName )

        existingClasses = []
        itemsToRemove = []
        needUpdate = False

        # For all root items
        path = os.path.realpath( fileName )
        for treeItem in self.rootItem.childItems:
            if os.path.realpath( treeItem.getPath() ) != path:
                continue

            # Item belongs to the modified file
            name = treeItem.sourceObj.name
            found = False
            for cls in info.classes:
                if cls.name == name:
                    found = True
                    existingClasses.append( name )
                    treeItem.updateData( cls )
                    treeItem.setData( 2, cls.line )
                    self.signalItemUpdated( treeItem )
                    self.updateSingleClassItem( treeItem, cls )
                    break
            if not found:
                itemsToRemove.append( treeItem )

        for item in itemsToRemove:
            needUpdate = True
            self.removeTreeItem( item )

        # Add those which have been introduced
        for item in info.classes:
            if not item.name in existingClasses:
                needUpdate = True
                newItem = TreeViewClassItem( self.rootItem, item )
                newItem.appendData( [ fileName, item.line ] )
                self.addTreeItem( self.rootItem, newItem )

        return needUpdate

