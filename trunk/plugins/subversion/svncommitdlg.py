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

" Codimension SVN plugin commit dialog "


from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import ( QDialog, QVBoxLayout, QDialogButtonBox, QTextEdit,
                          QHBoxLayout, QLabel, QToolButton, QTreeWidget,
                          QTreeWidgetItem, QFontMetrics, QHeaderView )
from ui.itemdelegates import NoOutlineHeightDelegate
from svnstrconvert import STATUS


class SVNPluginCommitDialog( QDialog ):
    " SVN Plugin commit dialog "

    def __init__( self, pathsToCommit, pathsToIgnore, parent = None ):
        QDialog.__init__( self, parent )

        self.__createLayout( pathsToCommit, pathsToIgnore )
        self.setWindowTitle( "SVN plugin commit" )

        # Fill the lists
        for item in pathsToCommit:
            newItem = QTreeWidgetItem(
                        QStringList() << "" << item[ 0 ] << STATUS[ item[ 1 ] ] )
            newItem.setCheckState( 0, Qt.Checked )
            newItem.setToolTip( 1, item[ 0 ] )
            newItem.setToolTip( 2, STATUS[ item[ 1 ] ] )
            self.__pathToCommitView.addTopLevelItem( newItem )
        self.__pathToCommitView.header().resizeSections( QHeaderView.ResizeToContents )
        self.__pathToCommitView.header().resizeSection( 0, 20 )
        self.__pathToCommitView.header().setResizeMode( QHeaderView.Fixed )

        for item in pathsToIgnore:
            newItem = QTreeWidgetItem(
                        QStringList() << item[ 0 ] << STATUS[ item[ 1 ] ] )
            newItem.setToolTip( 0, item[ 0 ] )
            newItem.setToolTip( 1, STATUS[ item[ 1 ] ] )
            self.__pathToIgnoreView.addTopLevelItem( newItem )
        self.__pathToIgnoreView.header().resizeSections( QHeaderView.ResizeToContents )

        self.__updateSelectAllStatus()
        self.__updateOKStatus()
        self.__message.setFocus()
        return

    def __createLayout( self, pathsToCommit, pathsToIgnore ):
        " Creates the dialog layout "

        self.resize( 640, 420 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )

        # Paths to commit part
        hboxLayout = QHBoxLayout()
        hboxLayout.addWidget( QLabel( "Paths to commit (total: " +
                              str( len( pathsToCommit ) ) + ")" ) )

        self.__selectAllButton = QToolButton()
        self.__selectAllButton.setText( "Select All" )
        self.connect( self.__selectAllButton, SIGNAL( 'clicked()' ),
                      self.__onSelectAll )
        hboxLayout.addWidget( self.__selectAllButton )
        vboxLayout.addLayout( hboxLayout )

        self.__pathToCommitView = QTreeWidget()
        self.__pathToCommitView.setAlternatingRowColors( True )
        self.__pathToCommitView.setRootIsDecorated( False )
        self.__pathToCommitView.setItemsExpandable( False )
        self.__pathToCommitView.setSortingEnabled( True )
        self.__pathToCommitView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__pathToCommitView.setUniformRowHeights( True )

        self.__pathToCommitHeader = QTreeWidgetItem(
                QStringList() << "" << "Path" << "Status" )
        self.__pathToCommitView.setHeaderItem( self.__pathToCommitHeader )
        self.__pathToCommitView.header().setSortIndicator( 1, Qt.AscendingOrder )
        self.connect( self.__pathToCommitView,
                      SIGNAL( "itemChanged(QTreeWidgetItem*,int)" ),
                      self.__onCommitPathChanged )
        vboxLayout.addWidget( self.__pathToCommitView )

        # Paths to ignore part
        vboxLayout.addWidget( QLabel( "Ignored paths (total: " +
                              str( len( pathsToIgnore ) ) + ")" ) )

        self.__pathToIgnoreView = QTreeWidget()
        self.__pathToIgnoreView.setAlternatingRowColors( True )
        self.__pathToIgnoreView.setRootIsDecorated( False )
        self.__pathToIgnoreView.setItemsExpandable( False )
        self.__pathToIgnoreView.setSortingEnabled( True )
        self.__pathToIgnoreView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__pathToIgnoreView.setUniformRowHeights( True )

        pathToIgnoreHeader = QTreeWidgetItem(
                QStringList() << "Path" << "Status" )
        self.__pathToIgnoreView.setHeaderItem( pathToIgnoreHeader )
        self.__pathToIgnoreView.header().setSortIndicator( 0, Qt.AscendingOrder )
#        metrics = QFontMetrics( self.__pathToIgnoreView.font() )
#        rect = metrics.boundingRect( "X" )
#        self.__pathToIgnoreView.setFixedHeight( rect.height() * 5 + 5 )
        vboxLayout.addWidget( self.__pathToIgnoreView )

        # Message part
        vboxLayout.addWidget( QLabel( "Message" ) )
        self.__message = QTextEdit()
        self.__message.setAcceptRichText( False )
        metrics = QFontMetrics( self.__message.font() )
        rect = metrics.boundingRect( "X" )
        self.__message.setFixedHeight( rect.height() * 4 + 5 )
        vboxLayout.addWidget( self.__message )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setText( "Commit" )
        buttonBox.button( QDialogButtonBox.Cancel ).setDefault( True )
        self.connect( buttonBox, SIGNAL( "accepted()" ), self.userAccept )
        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        vboxLayout.addWidget( buttonBox )
        return

    def userAccept( self ):
        " Triggered when the user clicks OK "
        # Collect the list of checked paths
        self.commitMessage = str( self.__message.toPlainText() ).strip()

        self.commitPaths = []
        index = 0
        while index < self.__pathToCommitView.topLevelItemCount():
            item = self.__pathToCommitView.topLevelItem( index )
            if item.checkState( 0 ) == Qt.Checked:
                self.commitPaths.append( str( item.text( 1 ) ) )
            index += 1
        self.accept()
        return

    def __getCheckedCount( self ):
        " Provides the number of selected items in the commit paths section "
        index = 0
        checkedCount = 0
        while index < self.__pathToCommitView.topLevelItemCount():
            item = self.__pathToCommitView.topLevelItem( index )
            if item.checkState( 0 ) == Qt.Checked:
                checkedCount += 1
            index += 1
        return checkedCount

    def __updateSelectAllStatus( self ):
        " Updates the select all status button "
        total = self.__pathToCommitView.topLevelItemCount()
        if total == 0 or total == self.__getCheckedCount():
            self.__selectAllButton.setEnabled( False )
        else:
            self.__selectAllButton.setEnabled( True )
        return

    def __updateOKStatus( self ):
        " Updates the OK button status "
        self.__OKButton.setEnabled( self.__getCheckedCount() > 0 )
        return

    def __onCommitPathChanged( self, item, column ):
        " Triggered when an item is changed "
        self.__updateSelectAllStatus()
        self.__updateOKStatus()
        return

    def __onSelectAll( self ):
        " Triggered when select all button is clicked "
        index = 0
        while index < self.__pathToCommitView.topLevelItemCount():
            item = self.__pathToCommitView.topLevelItem( index )
            item.setCheckState( 0, Qt.Checked )
            index += 1
        self.__updateSelectAllStatus()
        self.__updateOKStatus()
        return

