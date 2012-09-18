#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

" File outline browser and its model "


from PyQt4.QtGui        import QTreeView
from PyQt4.QtCore       import QVariant
from utils.globals      import GlobalData
from browsermodelbase   import BrowserModelBase
from utils.pixmapcache  import PixmapCache
from filesbrowserbase   import FilesBrowser
from viewitems          import DirectoryItemType, SysPathItemType, \
                               GlobalsItemType, ImportsItemType, \
                               FunctionsItemType, ClassesItemType, \
                               StaticAttributesItemType, \
                               InstanceAttributesItemType, \
                               CodingItemType, ImportItemType, \
                               FunctionItemType, \
                               ClassItemType, DecoratorItemType, \
                               AttributeItemType, GlobalItemType, \
                               ImportWhatItemType, \
                               TreeViewCodingItem, \
                               TreeViewGlobalsItem, \
                               TreeViewImportsItem, \
                               TreeViewFunctionsItem, TreeViewClassesItem



class OutlineBrowserModel( BrowserModelBase ):
    " Class implementing the file outline browser model "

    def __init__( self, shortName, info, parent = None ):
        BrowserModelBase.__init__( self, QVariant( shortName ), parent )
        self.populateModel( info )
        return

    def populateModel( self, info ):
        " Populates the browser model "
        self.clear()
        if info.encoding is not None:
            self.addItem( TreeViewCodingItem( self.rootItem, info.encoding ) )
        if len( info.imports ) > 0:
            self.addItem( TreeViewImportsItem( self.rootItem, info ) )
        if len( info.globals ) > 0:
            self.addItem( TreeViewGlobalsItem( self.rootItem, info ) )
        if len( info.functions ) > 0:
            self.addItem( TreeViewFunctionsItem( self.rootItem, info ) )
        if len( info.classes ) > 0:
            self.addItem( TreeViewClassesItem( self.rootItem, info ) )
        return


class OutlineBrowser( FilesBrowser ):
    " File outline browser "

    def __init__( self, uuid, shortName, info, parent = None ):

        FilesBrowser.__init__( self, OutlineBrowserModel( shortName, info ),
                               False, parent )

        self.__bufferUUID = uuid

        self.setWindowTitle( 'File outline' )
        self.setWindowIcon( PixmapCache().getIcon( 'icon.png' ) )
        return

    def reload( self ):
        " Reloads the filesystem view "
        self.model().sourceModel().populateModel()
        self.model().reset()
        self.layoutDisplay()
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

    def openItem( self, item ):
        " Handles the case when an item is activated "
        if item.itemType in [ GlobalsItemType,
                              ImportsItemType, FunctionsItemType,
                              ClassesItemType, StaticAttributesItemType,
                              InstanceAttributesItemType ]:
            return

        if item.itemType in [ CodingItemType, ImportItemType, FunctionItemType,
                              ClassItemType, DecoratorItemType,
                              AttributeItemType, GlobalItemType,
                              ImportWhatItemType ]:
            GlobalData().mainWindow.gotoInBuffer( self.__bufferUUID,
                                                  item.sourceObj.line )
        return

