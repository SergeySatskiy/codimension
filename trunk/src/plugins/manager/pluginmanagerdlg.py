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
                          QHeaderView, QPushButton )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
import os.path


STATE_COL = 0       # Enabled/disabled
CONFLICT_COL = 1    # Exclamation sign
TYPE_COL = 2        # Sys/user
NAME_COL = 3
VERSION_COL = 4
SETTINGS_COL = 5    # Settings button

class PluginItem( QTreeWidgetItem ):
    " Single plugin item "

    def __init__( self, pluginManager, cdmPlugin, active, category ):
        self.plugin = cdmPlugin
        self.active = active
        self.category = category

        name = self.plugin.getName()
        ver = self.plugin.getVersion()
        QTreeWidgetItem.__init__( self,
            QStringList() << "" << "" << "" << name << ver )

        if not self.plugin.conflictType in [ pluginManager.NO_CONFLICT,
                                             pluginManager.USER_DISABLED ]:
            self.setIcon( CONFLICT_COL, PixmapCache().getIcon( 'pluginconflict.png' ) )
            self.setToolTip( CONFLICT_COL, self.plugin.conflictMessage )

        self.setToolTip( STATE_COL, "Enable / disable" )
        self.setToolTip( CONFLICT_COL, "Conflict" )

        if self.plugin.isUser():
            self.setIcon( TYPE_COL, PixmapCache().getIcon( 'pluginuser.png' ) )
            self.setToolTip( TYPE_COL, "User plugin" )
        else:
            self.setIcon( TYPE_COL, PixmapCache().getIcon( 'pluginsystem.png' ) )
            self.setToolTip( TYPE_COL, "System wide plugin" )

        self.setFlags( self.flags() | Qt.ItemIsUserCheckable )
        if active:
            self.setCheckState( STATE_COL, Qt.Checked )
        else:
            self.setCheckState( STATE_COL, Qt.Unchecked )
        return



class PluginsDialog( QDialog ):
    " Codimension plugins dialog "

    def __init__( self, pluginManager, parent = None ):
        QDialog.__init__( self, parent )
        self.__pluginManager = pluginManager
        self.__createLayout()
        self.__populate()
        self.__pluginsView.setFocus()
        self.__inItemChange = False
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
                QStringList() << "" << "" << "" << "Name" << "Version" << "" )
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
        self.__details = QTreeWidget()
        self.__details.setAlternatingRowColors( False )
        self.__details.setRootIsDecorated( False )
        self.__details.setItemsExpandable( False )
        self.__details.setSortingEnabled( False )
        self.__details.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__details.setUniformRowHeights( True )

        detailsHeader = QTreeWidgetItem( QStringList() << "" << "" )
        self.__details.setHeaderItem( detailsHeader )
        self.__details.setHeaderHidden( True )

        metrics = QFontMetrics( self.__details.font() )
        rect = metrics.boundingRect( "X" )
        self.__details.setFixedHeight( rect.height() * 6 + 5 )
        layout.addWidget( self.__details )

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
                settingsButton = QPushButton( PixmapCache().getIcon( 'pluginmanagermenu.png' ), "" )
                settingsButton.setFixedSize( 24, 24 )
                configFunction = cdmPlugin.getObject().getConfigFunction()
                if configFunction is None:
                    settingsButton.setToolTip( "Plugin does not need configuring" )
                    settingsButton.setEnabled( False )
                else:
                    settingsButton.setToolTip( "Click to configure" )
                    self.connect( settingsButton, SIGNAL( 'clicked()' ),
                                  configFunction )

                settingsButton.setFocusPolicy( Qt.NoFocus )
                self.__pluginsView.setItemWidget( newItem, SETTINGS_COL, settingsButton )

        for category in self.__pluginManager.inactivePlugins:
            for cdmPlugin in self.__pluginManager.inactivePlugins[ category ]:
                newItem = PluginItem( self.__pluginManager, cdmPlugin, False, category )
                self.__pluginsView.addTopLevelItem( newItem )
                settingsButton = QPushButton( PixmapCache().getIcon( 'pluginmanagermenu.png' ), "" )
                settingsButton.setFixedSize( 24, 24 )
                configFunction = cdmPlugin.getObject().getConfigFunction()
                if configFunction is None:
                    settingsButton.setToolTip( "Plugin does not need configuring" )
                else:
                    settingsButton.setToolTip( "Enable plugin and then click to configure" )
                    self.connect( settingsButton, SIGNAL( 'clicked()' ),
                                  configFunction )
                settingsButton.setFocusPolicy( Qt.NoFocus )
                settingsButton.setEnabled( False )
                self.__pluginsView.setItemWidget( newItem, SETTINGS_COL, settingsButton )

        for cdmPlugin in self.__pluginManager.unknownPlugins:
            newItem = PluginItem( self.__pluginManager, cdmPlugin, False, None )
            self.__pluginsView.addTopLevelItem( newItem )
            settingsButton = QPushButton( PixmapCache().getIcon( 'pluginmanagermenu.png' ), "" )
            settingsButton.setFixedSize( 24, 24 )
            settingsButton.setToolTip( "Unknown plugins are not configurable" )
            settingsButton.setFocusPolicy( Qt.NoFocus )
            settingsButton.setEnabled( False )
            self.__pluginsView.setItemWidget( newItem, SETTINGS_COL, settingsButton )

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
        self.__pluginsView.header().setStretchLastSection( False )
        self.__pluginsView.header().resizeSections(
                                        QHeaderView.ResizeToContents )
        self.__pluginsView.header().resizeSection( STATE_COL, 28 )
        self.__pluginsView.header().setResizeMode( STATE_COL, QHeaderView.Fixed )
        self.__pluginsView.header().resizeSection( CONFLICT_COL, 28 )
        self.__pluginsView.header().setResizeMode( CONFLICT_COL, QHeaderView.Fixed )
        self.__pluginsView.header().resizeSection( TYPE_COL, 28 )
        self.__pluginsView.header().setResizeMode( TYPE_COL, QHeaderView.Fixed )

        self.__pluginsView.header().setResizeMode( VERSION_COL, QHeaderView.Stretch )
        self.__pluginsView.header().resizeSection( SETTINGS_COL, 24 )
        self.__pluginsView.header().setResizeMode( SETTINGS_COL, QHeaderView.Fixed )
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
        self.__details.clear()
        self.__errorsText.setText( "" )

        if item is None:
            return

        self.__details.addTopLevelItem(
                    QTreeWidgetItem( QStringList() << "Author" << item.plugin.getAuthor() ) )
        self.__details.addTopLevelItem(
                    QTreeWidgetItem( QStringList() << "Path" << os.path.normpath( item.plugin.getPath() ) ) )
        self.__details.addTopLevelItem(
                    QTreeWidgetItem( QStringList() << "Description" << item.plugin.getDescription() ) )
        self.__details.addTopLevelItem(
                    QTreeWidgetItem( QStringList() << "Web site" << item.plugin.getWebsite() ) )

        copyright = item.plugin.getCopyright()
        if copyright is not None:
            if copyright.lower() != "unknown":
                self.__details.addTopLevelItem(
                    QTreeWidgetItem( QStringList() << "Copyright" << copyright ) )

        for name in item.plugin.getDetails():
            value = item.plugin.getDetails()[ name ]
            self.__details.addTopLevelItem(
                    QTreeWidgetItem( QStringList() << name << value ) )

        self.__errorsText.setText( item.plugin.conflictMessage )
        return

    def __onItemChanged( self, item, column ):
        " Triggered when an item is changed "

        if self.__inItemChange:
            return

        if item.active:
            self.__inItemChange = True
            item.plugin.disable()
            item.active = False

            settingsButton = self.__pluginsView.itemWidget( item, SETTINGS_COL )
            settingsButton.setEnabled( False )
            if item.plugin.getObject().getConfigFunction() is not None:
                settingsButton.setToolTip( "Enable plugin and then click to configure" )

            if item.category in self.__pluginManager.inactivePlugins:
                self.__pluginManager.inactivePlugins[ item.category ].append( item.plugin )
            else:
                self.__pluginManager.inactivePlugins[ item.category ] = [ item.plugin ]
            self.__pluginManager.activePlugins[ item.category ].remove( item.plugin )
            self.__pluginManager.saveDisabledPlugins()
            self.__inItemChange = False
            return

        self.__inItemChange = True
        message = self.__pluginManager.checkConflict( item.plugin )
        if message is not None:
            item.setCheckState( STATE_COL, Qt.Unchecked )
            self.__errorsText.setText( message )
            self.__inItemChange = False
            return

        try:
            item.plugin.enable()
            item.active = True
            if item.category in self.__pluginManager.activePlugins:
                self.__pluginManager.activePlugins[ item.category ].append( item.plugin )
            else:
                self.__pluginManager.activePlugins[ item.category ] = [ item.plugin ]
            self.__pluginManager.inactivePlugins[ item.category ].remove( item.plugin )
            self.__pluginManager.saveDisabledPlugins()
            self.__errorsText.setText( "" )

            settingsButton = self.__pluginsView.itemWidget( item, SETTINGS_COL )
            if item.plugin.getObject().getConfigFunction() is not None:
                settingsButton.setToolTip( "Click to configure" )
                settingsButton.setEnabled( True )
        except:
            item.setCheckState( STATE_COL, Qt.Unchecked )
            self.__errorsText.setText( "Error activating the plugin - exception is generated" )

        self.__inItemChange = False
        return

