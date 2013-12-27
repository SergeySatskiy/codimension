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

" File system browser model "


from PyQt4.QtCore import QVariant, QModelIndex, QDir, SIGNAL
from viewitems import TreeViewDirectoryItem, TreeViewSysPathItem
from utils.globals import GlobalData
from utils.project import CodimensionProject
from browsermodelbase import BrowserModelBase
from utils.settings import Settings



class FileSystemBrowserModel( BrowserModelBase ):
    " Class implementing the file system browser model "

    def __init__( self, parent = None ):

        BrowserModelBase.__init__( self, QVariant( "Name" ), parent )
        self.setTooltips( Settings().projectTooltips )

        self.projectTopLevelDirs = []
        self.populateModel()

        self.connect( GlobalData().project,
                      SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def populateModel( self ):
        " Populates the browser model "

        self.clear()
        self.addItem( TreeViewSysPathItem( self.rootItem ) )
        self.addItem( TreeViewDirectoryItem( self.rootItem, QDir.homePath() ) )
        for dname in QDir.drives():
            self.addItem( TreeViewDirectoryItem( self.rootItem,
                                                 dname.absoluteFilePath() ) )
        self.__populateProjectTopLevelDirs()
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what != CodimensionProject.CompleteProject:
            return

        self.__removeProjectTopLevelDirs()      # Remove the previous set
        self.__populateProjectTopLevelDirs()    # Populate the new one
        return

    def __populateProjectTopLevelDirs( self ):
        " Populates the project specific top level dirs "

        for dname in GlobalData().project.topLevelDirs:
            cnt = self.rootItem.childCount()
            self.beginInsertRows( QModelIndex(), cnt, cnt )
            self._addItem( TreeViewDirectoryItem( self.rootItem, dname ),
                           self.rootItem )
            self.endInsertRows()
            self.projectTopLevelDirs.append( dname )
        return

    def __removeProjectTopLevelDirs( self ):
        " Removes all the project top level dirs "

        while len( self.projectTopLevelDirs ) > 0:
            # Find the row index in the children list of the root item
            idx = 0
            for item in self.rootItem.childItems:
                if item.getPath() == self.projectTopLevelDirs[ 0 ]:
                    index = self.index( idx, 0 )
                    self.removeTopLevelDir( index )
                    break
                idx += 1
        return

    def addTopLevelDir( self, dirname ):
        " Adds a new toplevel directory "

        itm = TreeViewDirectoryItem( self.rootItem, dirname )
        self.addItem( itm )
        self.projectTopLevelDirs.append( dirname )
        return

    def removeTopLevelDir( self, index ):
        " Removes a toplevel directory "

        if not index.isValid():
            return

        item = index.internalPointer()
        self.beginRemoveRows( index.parent(), index.row(), index.row() )
        self.rootItem.removeChild( item )
        self.endRemoveRows()

        self.projectTopLevelDirs.remove( item.getPath() )
        return

