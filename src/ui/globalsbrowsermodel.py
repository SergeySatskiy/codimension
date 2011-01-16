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
        if not self.globalData.project.isProjectFile( fileName ):
            # Not a project file
            return

        if detectFileType( fileName ) not in [ PythonFileType,
                                               Python3FileType ]:
            return

        count = 0
        # Remove all the items which belong to this file
        idx = len( self.rootItem.childItems ) - 1
        while idx >= 0:
            item = self.rootItem.childItems[ idx ]
            if item.getPath() == fileName:
                self.rootItem.removeChild( item )
                count += 1
            idx -= 1

        # Insert the new items which belong to this file
        info = self.globalData.project.briefModinfoCache.get( fileName )
        for globalObj in info.globals:
            item = TreeViewGlobalItem( self.rootItem, globalObj )
            item.appendData( [ fileName, globalObj.line ] )
            self._addItem( item, self.rootItem )
            count += 1

        # Reset the model if there are any changes
        if count > 0:
            self.reset()
        return

