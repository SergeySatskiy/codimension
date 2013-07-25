#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2013  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" Plugins manager dialog """

from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import ( QDialog, QTreeWidgetItem, QTreeWidget, QVBoxLayout,
                          QTextEdit, QDialogButtonBox, QLabel, QFontMetrics,
                          QHeaderView )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache



class PluginItem( QTreeWidgetItem ):
    " Single plugin item "

    def __init__( self, pluginManager, cdmPlugin, active, category ):
        self.plugin = cdmPlugin
        self.active = active
        self.category = category

        QTreeWidgetItem.__init__( self,
            QStringList() << "" << "" << "" << self.plugin.getName() << self.plugin.getVersion() )

        if not self.plugin.conflictType in [ pluginManager.NO_CONFLICT,
                                             pluginManager.USER_DISABLED ]:
            self.setIcon( 0, PixmapCache().getIcon( 'pluginconflict.png' ) )
            self.setToolTip( 0, self.plugin.conflictMessage )

        if self.plugin.isUser:
            self.setIcon( 1, PixmapCache().getIcon( 'pluginuser.png' ) )
            self.setToolTip( 1, "User plugin" )
        else:
            self.setIcon( 1, PixmapCache().getIcon( 'pluginsystem.png' ) )
            self.setToolTip( 1, "System wide plugin" )

        self.setFlags( self.flags() | Qt.ItemIsUserCheckable )
        self.setCheckState( 2, active )
        return



class PluginsDialog( QDialog ):
    " Codimension plugins dialog "

    def __init__( self, pluginManager, parent = None ):
        QDialog.__init__( self, parent )
        self.__pluginManager = pluginManager
        self.__createLayout()
        self.__populate()
        self.__pluginsView.setFocus()
        return

    def __createLayout( self ):
        " Creates the dialog layout "
        self.resize( 640, 480 )
        self.setSizeGripEnabled( True )

        layout = QVBoxLayout()

        # Plugins list
        self.__pluginsView = QTreeWidget()
        self.__pluginsView.setAlternatingRowColors( True )
        self.__pluginsView.setRootIsDecorated( False )
        self.__pluginsView.setItemsExpandable( False )
        self.__pluginsView.setSortingEnabled( True )
        self.__pluginsView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__pluginsView.setUniformRowHeights( True )

        # Alert | system/user | Enable | Name | Version
        self.__pluginsHeader = QTreeWidgetItem(
                QStringList() << "" << "" << "Enable" << "Name" << "Version" )
        self.__pluginsView.setHeaderItem( self.__pluginsHeader )
        self.__pluginsView.header().setSortIndicator( 3, Qt.AscendingOrder )
        self.connect( self.__pluginsView,
                      SIGNAL( "itemSelectionChanged()" ),
                      self.__pluginSelectionChanged )
        self.connect( self.__pluginsView,
                      SIGNAL( "itemChanged(QTreeWidgetItem*,int)" ),
                      self.__onItemChanged )

        layout.addWidget( self.__pluginsView )

        # Detailed information
        detailsLabel = QLabel( "Detailed information" )
        layout.addWidget( detailsLabel )
        self.__detailsText = QTextEdit()
        self.__detailsText.setReadOnly( True )
        self.__detailsText.setAcceptRichText( False )
        metrics = QFontMetrics( self.__detailsText.font() )
        rect = metrics.boundingRect( "X" )
        self.__detailsText.setFixedHeight( rect.height() * 6 + 5 )
        layout.addWidget( self.__detailsText )

        # Errors/warnings
        errorsLabel = QLabel( "Errors / warnings" )
        layout.addWidget( errorsLabel )
        self.__errorsText = QTextEdit()
        self.__errorsText.setReadOnly( True )
        self.__errorsText.setAcceptRichText( False )
        metrics = QFontMetrics( self.__errorsText.font() )
        rect = metrics.boundingRect( "X" )
        self.__errorsText.setFixedHeight( rect.height() * 4 + 5 )
        layout.addWidget( self.__errorsText )

        # Buttons box
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setDefault( True )
        self.connect( buttonBox, SIGNAL( "accepted()" ), self.close )
        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        layout.addWidget( buttonBox )

        self.setLayout( layout )
        return

    def __populate( self ):
        " Populates the list with the plugins "
        for category in self.__pluginManager.activePlugins:
            for cdmPlugin in self.__pluginManager.activePlugins[ category ]:
                newItem = PluginItem( self.__pluginManager, cdmPlugin, True, category )
                self.__pluginsView.addTopLevelItem( newItem )

        for category in self.__pluginManager.inactivePlugins:
            for cdmPlugin in self.__pluginManager.inactivePlugins[ category ]:
                newItem = PluginItem( self.__pluginManager, cdmPlugin, False, category )
                self.__pluginsView.addTopLevelItem( newItem )

        for cdmPlugin in self.__pluginManager.unknownPlugins:
            newItem = PluginItem( self.__pluginManager, cdmPlugin, False, None )
            self.__pluginsView.addTopLevelItem( newItem )

        self.__sortPlugins()
        self.__resizePlugins()
        return


    def __sortPlugins( self ):
        " Sorts the plugins table "
        self.__pluginsView.sortItems(
                    self.__pluginsView.sortColumn(),
                    self.__pluginsView.header().sortIndicatorOrder() )
        return

    def __resizePlugins( self ):
        " Resizes the plugins table "
        self.__pluginsView.header().setStretchLastSection( True )
        self.__pluginsView.header().resizeSections(
                                        QHeaderView.ResizeToContents )
        self.__pluginsView.header().resizeSection( 0, 22 )
        self.__pluginsView.header().setResizeMode( 0, QHeaderView.Fixed )
        self.__pluginsView.header().resizeSection( 1, 22 )
        self.__pluginsView.header().setResizeMode( 1, QHeaderView.Fixed )
        return

    def __pluginSelectionChanged( self ):
        " Triggered when an item is selected "
        selected = list( self.__pluginsView.selectedItems() )
        if selected:
            self.__updateDetails( selected[ 0 ] )
        else:
            self.__updateDetails( None )
        return

    def __updateDetails( self, item ):
        " Updates the content of the details and the error boxes "
        if item is None:
            self.__detailsText.setText( "" )
            self.__errorsText.setText( "" )
            return

        self.__detailsText.setText( "Author: " + item.plugin.getAuthor() + "\n"
                                    "Path: " + item.plugin.getPath() + "\n"
                                    "Description: " + item.plugin.getDescription() + "\n"
                                    "Web site: " + item.plugin.getWebsite() )

        self.__errorsText.setText( item.plugin.conflictMessage )
        return

    def __onItemChanged( self, item, column ):
        " Triggered when an item is changed "
        if item.checkState( 2 ) == item.active:
            return

        if item.active:
            print "Need to disable"
        else:
            print "Need to enable"
        return

