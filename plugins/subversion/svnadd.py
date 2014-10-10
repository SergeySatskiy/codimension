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

""" Performs SVN add command """

from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QDialog, QVBoxLayout, QDialogButtonBox,
                          QLabel, QTreeWidget,
                          QTreeWidgetItem, QHeaderView,
                          QApplication, QCursor )
from ui.itemdelegates import NoOutlineHeightDelegate
import logging
import pysvn
import os.path
from svnstrconvert import notifyActionToString


class SVNAddMixin:

    def __init__( self ):
        return

    def fileAddToRepository( self ):
        " Called when add for a file is requested "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnAdd( path, False )
        return

    def dirAddToRepository( self ):
        " Called when add for a directory is requested "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnAdd( path, False )
        return

    def dirAddToRepositoryRecursively( self ):
        " Called when add for a directory recursively is requested "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnAdd( path, True )
        return

    def bufferAddToRepository( self ):
        " Called when add for a buffer is requested "
        path = self.ide.currentEditorWidget.getFileName()
        self.__svnAdd( path, False )
        return

    def __svnAdd( self, path, recursively ):
        " Adds the given path to the repository "
        client = self.getSVNClient( self.getSettings() )
        doSVNAdd( self, client, path, recursively )
        return



def doSVNAdd( plugin, client, path, recursively ):
    " Does SVN add "
    pathList = []
    def notifyCallback( event, paths = pathList ):
        if 'path' not in event:
            return
        if not event[ 'path' ]:
            return

        path = event[ 'path' ]
        if os.path.isdir( path ) and not path.endswith( os.path.sep ) and \
                                     not os.path.islink( path ):
            path += os.path.sep
        action = notifyActionToString( event[ 'action' ] )
        if action:
            logging.info( action + " " + path )
            paths.append( path )
        return

    needToRestoreCursor = False
    try:
        client.callback_notify = notifyCallback
        if recursively:
            # This is a dir. It could be under VCS or not
            dirStatus = plugin.getLocalStatus( path )
            if dirStatus == plugin.NOT_UNDER_VCS:
                QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
                needToRestoreCursor = True
                client.add( path, recurse = True )
                QApplication.restoreOverrideCursor()
                needToRestoreCursor = False
            else:
                # Need to build the list manually
                statuses = plugin.getLocalStatus( path, pysvn.depth.infinity )
                if type( statuses ) != list:
                    logging.error( "Error checking local SVN statuses for " +
                                   path )
                    return

                pathsToAdd = []
                for item in statuses:
                    if item[ 1 ] == plugin.NOT_UNDER_VCS:
                        pathsToAdd.append( item[ 0 ] )

                if not pathsToAdd:
                    logging.info( "No paths to add for " + path )
                    return

                dlg = SVNPluginAddDialog( pathsToAdd )
                res = dlg.exec_()
                if res == QDialog.Accepted:
                    if len( dlg.addPaths ) == 0:
                        return

                    QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
                    needToRestoreCursor = True
                    client.add( dlg.addPaths )
                    QApplication.restoreOverrideCursor()
                    needToRestoreCursor = False
        else:
            # It is a single file
            QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
            needToRestoreCursor = True
            client.add( path )
            QApplication.restoreOverrideCursor()
            needToRestoreCursor = False

        if pathList:
            logging.info( "Finished" )
    except Exception, excpt:
        if needToRestoreCursor:
            QApplication.restoreOverrideCursor()
        logging.error( str( excpt ) )

    for addedPath in pathList:
        plugin.notifyPathChanged( addedPath )
    return



# Columns for the add path list
CHECK_COL = 0
PATH_COL = 1

class SVNPluginAddDialog( QDialog ):
    " SVN Plugin add dialog "

    def __init__( self, pathsToAdd, parent = None ):
        QDialog.__init__( self, parent )

        self.addPaths = []

        self.__createLayout( pathsToAdd )
        self.setWindowTitle( "SVN add" )

        # Fill the lists
        for item in pathsToAdd:
            newItem = QTreeWidgetItem( [ "", item ] )
            newItem.setCheckState( CHECK_COL, Qt.Checked )
            newItem.setToolTip( PATH_COL, item[ 0 ] )
            self.__pathToAddView.addTopLevelItem( newItem )

        self.__resizeAddPaths()
        self.__sortAddPaths()

        self.__updateOKStatus()
        return

    def __resizeAddPaths( self ):
        " Resizes the add table "
        self.__pathToAddView.header().setStretchLastSection( True )
        self.__pathToAddView.header().resizeSections(
                                        QHeaderView.ResizeToContents )
        self.__pathToAddView.header().resizeSection( CHECK_COL, 28 )
        self.__pathToAddView.header().setResizeMode( CHECK_COL,
                                                     QHeaderView.Fixed )
        return

    def __sortAddPaths( self ):
        " Sorts the commit paths table "
        self.__pathToAddView.sortItems(
                    self.__pathToAddView.sortColumn(),
                    self.__pathToAddView.header().sortIndicatorOrder() )
        return

    @staticmethod
    def __configTable( table ):
        " Sets common properties for a table "
        table.setAlternatingRowColors( True )
        table.setRootIsDecorated( False )
        table.setItemsExpandable( False )
        table.setSortingEnabled( True )
        table.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        table.setUniformRowHeights( True )
        return

    def __createLayout( self, pathsToAdd ):
        " Creates the dialog layout "

        self.resize( 640, 480 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )

        # Paths to add part
        vboxLayout.addWidget( QLabel( "Paths to add (total: " +
                                              str( len( pathsToAdd ) ) + ")" ) )

        self.__pathToAddView = QTreeWidget()
        self.__configTable( self.__pathToAddView )

        self.__pathToAddHeader = QTreeWidgetItem( [ "", "Path" ] )
        self.__pathToAddView.setHeaderItem( self.__pathToAddHeader )
        self.__pathToAddView.header().setSortIndicator( PATH_COL,
                                                        Qt.AscendingOrder )
        self.__pathToAddView.itemChanged.connect( self.__onAddPathChanged )
        vboxLayout.addWidget( self.__pathToAddView )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setText( "Add" )
        buttonBox.button( QDialogButtonBox.Cancel ).setDefault( True )
        buttonBox.accepted.connect( self.userAccept )
        buttonBox.rejected.connect( self.close )
        vboxLayout.addWidget( buttonBox )
        return

    def userAccept( self ):
        " Triggered when the user clicks OK "
        # Collect the list of checked paths
        self.addPaths = []
        index = 0
        while index < self.__pathToAddView.topLevelItemCount():
            item = self.__pathToAddView.topLevelItem( index )
            if item.checkState( CHECK_COL ) == Qt.Checked:
                path = str( item.text( 1 ) )
                if os.path.isdir( path ) and not os.path.islink( path ) and \
                                             not path.endswith( os.path.sep ):
                    path += os.path.sep
                self.addPaths.append( path )
            index += 1
        self.accept()
        return

    def __getCheckedCount( self ):
        " Provides the number of selected items in the add paths section "
        index = 0
        checkedCount = 0
        while index < self.__pathToAddView.topLevelItemCount():
            item = self.__pathToAddView.topLevelItem( index )
            if item.checkState( 0 ) == Qt.Checked:
                checkedCount += 1
            index += 1
        return checkedCount

    def __updateOKStatus( self ):
        " Updates the OK button status "
        self.__OKButton.setEnabled( self.__getCheckedCount() > 0 )
        return

    def __onAddPathChanged( self, item, column ):
        " Triggered when an item is changed "
        self.__updateOKStatus()
        return
