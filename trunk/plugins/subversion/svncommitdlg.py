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


from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import ( QDialog, QVBoxLayout, QDialogButtonBox, QTextEdit,
                          QHBoxLayout, QLabel, QToolButton, QTreeWidget,
                          QTreeWidgetItem, QFontMetrics, QHeaderView,
                          QFrame, QPalette, QSpacerItem, QSizePolicy,
                          QPushButton, QApplication, QCursor )
from ui.itemdelegates import NoOutlineHeightDelegate
from svnstrconvert import STATUS
from utils.pixmapcache import PixmapCache
from svnindicators import pluginHomeDir, IND_REPLACED, IND_ADDED, IND_DELETED
from ui.difftabwidget import DiffTabWidget
from thirdparty.diff2html.diff2html import parse_from_memory
import os.path
import difflib
import logging
from utils.fileutils import detectFileType, isFileTypeSearchable


class DiffButton( QPushButton ):
    " Custom diff button "

    def __init__( self ):
        QPushButton.__init__( self,
                              PixmapCache().getIcon( pluginHomeDir + 'svnmenudiff.png' ),
                              "" )
        self.setFixedSize( 24, 24 )
        self.setFocusPolicy( Qt.NoFocus )

        self.path = ""
        self.status = None
        self.clicked.connect( self.onClick )
        return

    def onClick( self ):
        " Emits a signal with the button index "
        self.emit( SIGNAL( "CustomClick" ), self.path, self.status )
        return


# Columns for the commit path list
CHECK_COL = 0
PATH_COL = 1
STATUS_COL = 2
DIFF_COL = 3


class SVNPluginCommitDialog( QDialog ):
    " SVN Plugin commit dialog "

    NODIFF = '<html><body bgcolor="#ffffe6"></body></html>'

    def __init__( self, plugin, pathsToCommit, pathsToIgnore, parent = None ):
        QDialog.__init__( self, parent )

        self.__plugin = plugin

        self.__createLayout( pathsToCommit, pathsToIgnore )
        self.setWindowTitle( "SVN commit" )

        # Fill the lists
        for item in pathsToCommit:
            newItem = QTreeWidgetItem( [ "", item[ 0 ], STATUS[ item[ 1 ] ] ] )
            newItem.setCheckState( CHECK_COL, Qt.Checked )
            newItem.setToolTip( PATH_COL, item[ 0 ] )
            newItem.setToolTip( STATUS_COL, STATUS[ item[ 1 ] ] )
            self.__pathToCommitView.addTopLevelItem( newItem )

            diffButton = self.__createDiffButton()
            diffButton.path = item[ 0 ]
            diffButton.status = item[ 1 ]

            fileType = detectFileType( item[ 0 ] )

            if os.path.isdir( item[ 0 ] ) or item[ 1 ] in [ IND_REPLACED ] \
                or not isFileTypeSearchable( fileType ):
                diffButton.setEnabled( False )
                diffButton.setToolTip( "Diff is not available" )
            else:
                diffButton.setEnabled( True )
                diffButton.setToolTip( "Click to see diff" )
            self.__pathToCommitView.setItemWidget( newItem, DIFF_COL, diffButton )

        self.__resizeCommitPaths()
        self.__sortCommitPaths()

        for item in pathsToIgnore:
            newItem = QTreeWidgetItem( [ item[ 0 ], STATUS[ item[ 1 ] ] ] )
            newItem.setToolTip( 0, item[ 0 ] )
            newItem.setToolTip( 1, STATUS[ item[ 1 ] ] )
            self.__pathToIgnoreView.addTopLevelItem( newItem )
        self.__pathToIgnoreView.header().resizeSections( QHeaderView.ResizeToContents )

        self.__updateSelectAllStatus()
        self.__updateOKStatus()
        self.__message.setFocus()
        return

    def __resizeCommitPaths( self ):
        " Resizes the plugins table "
        self.__pathToCommitView.header().setStretchLastSection( False )
        self.__pathToCommitView.header().resizeSections(
                                        QHeaderView.ResizeToContents )
        self.__pathToCommitView.header().resizeSection( CHECK_COL, 28 )
        self.__pathToCommitView.header().setResizeMode( CHECK_COL, QHeaderView.Fixed )

        # By some reasons, to have PATH_COL visually adjustable the only STATUS_COL
        # must be set to be stretchable, so there is a comment below.
        # self.__pathToCommitView.header().setResizeMode( PATH_COL, QHeaderView.Stretch )
        self.__pathToCommitView.header().setResizeMode( STATUS_COL, QHeaderView.Stretch )
        self.__pathToCommitView.header().resizeSection( DIFF_COL, 24 )
        self.__pathToCommitView.header().setResizeMode( DIFF_COL, QHeaderView.Fixed )
        return

    def __sortCommitPaths( self ):
        " Sorts the commit paths table "
        self.__pathToCommitView.sortItems(
                    self.__pathToCommitView.sortColumn(),
                    self.__pathToCommitView.header().sortIndicatorOrder() )
        return

    def __createDiffButton( self ):
        " Creates a diff button for a path "
        button = DiffButton()
        self.connect( button, SIGNAL( 'CustomClick' ), self.onDiff )
        return button

    @staticmethod
    def __setLightPalette( frame ):
        " Creates a lighter paletter for the widget background "
        palette = frame.palette()
        background = palette.color( QPalette.Background )
        background.setRgb( min( background.red() + 30, 255 ),
                           min( background.green() + 30, 255 ),
                           min( background.blue() + 30, 255 ) )
        palette.setColor( QPalette.Background, background )
        frame.setPalette( palette )
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

    def __createLayout( self, pathsToCommit, pathsToIgnore ):
        " Creates the dialog layout "

        self.resize( 640, 480 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )

        # Paths to commit part
        commitHeaderFrame = QFrame()
        commitHeaderFrame.setFrameStyle( QFrame.StyledPanel )
        commitHeaderFrame.setAutoFillBackground( True )
        self.__setLightPalette( commitHeaderFrame )
        commitHeaderFrame.setFixedHeight( 24 )

        expandingCommitSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__selectAllButton = QToolButton()
        self.__selectAllButton.setAutoRaise( True )
        self.__selectAllButton.setIcon( PixmapCache().getIcon( pluginHomeDir + 'svnselectall.png' ) )
        self.__selectAllButton.setFixedSize( 20, 20 )
        self.__selectAllButton.setToolTip( "Select all" )
        self.__selectAllButton.setFocusPolicy( Qt.NoFocus )
        self.__selectAllButton.clicked.connect( self.__onSelectAll )

        commitHeaderLayout = QHBoxLayout()
        commitHeaderLayout.setContentsMargins( 3, 0, 0, 0 )
        commitHeaderLayout.addWidget( QLabel( "Paths to commit (total: " +
                                              str( len( pathsToCommit ) ) + ")" ) )
        commitHeaderLayout.addSpacerItem( expandingCommitSpacer )
        commitHeaderLayout.addWidget( self.__selectAllButton )
        commitHeaderFrame.setLayout( commitHeaderLayout )

        vboxLayout.addWidget( commitHeaderFrame )

        self.__pathToCommitView = QTreeWidget()
        self.__configTable( self.__pathToCommitView )

        self.__pathToCommitHeader = QTreeWidgetItem( [ "", "Path", "Status", "" ] )
        self.__pathToCommitView.setHeaderItem( self.__pathToCommitHeader )
        self.__pathToCommitView.header().setSortIndicator( PATH_COL, Qt.AscendingOrder )
        self.__pathToCommitView.itemChanged.connect( self.__onCommitPathChanged )
        vboxLayout.addWidget( self.__pathToCommitView )

        # Paths to ignore part
        headerFrame = QFrame()
        headerFrame.setFrameStyle( QFrame.StyledPanel )
        headerFrame.setAutoFillBackground( True )
        self.__setLightPalette( headerFrame )
        headerFrame.setFixedHeight( 24 )

        ignoreLabel = QLabel( "Ignored paths (total: " +
                              str( len( pathsToIgnore ) ) + ")" )
        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__showHideIgnoredButton = QToolButton()
        self.__showHideIgnoredButton.setAutoRaise( True )
        self.__showHideIgnoredButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideIgnoredButton.setFixedSize( 20, 20 )
        self.__showHideIgnoredButton.setToolTip( "Show ignored path list" )
        self.__showHideIgnoredButton.setFocusPolicy( Qt.NoFocus )
        self.__showHideIgnoredButton.clicked.connect( self.__onShowHideIgnored )

        ignoredHeaderLayout = QHBoxLayout()
        ignoredHeaderLayout.setContentsMargins( 3, 0, 0, 0 )
        ignoredHeaderLayout.addWidget( ignoreLabel )
        ignoredHeaderLayout.addSpacerItem( expandingSpacer )
        ignoredHeaderLayout.addWidget( self.__showHideIgnoredButton )
        headerFrame.setLayout( ignoredHeaderLayout )

        vboxLayout.addWidget( headerFrame )

        self.__pathToIgnoreView = QTreeWidget()
        self.__configTable( self.__pathToIgnoreView )
        self.__pathToIgnoreView.setVisible( False )

        pathToIgnoreHeader = QTreeWidgetItem( [ "Path", "Status" ] )
        self.__pathToIgnoreView.setHeaderItem( pathToIgnoreHeader )
        self.__pathToIgnoreView.header().setSortIndicator( 0, Qt.AscendingOrder )
        vboxLayout.addWidget( self.__pathToIgnoreView )

        # Message part
        vboxLayout.addWidget( QLabel( "Message" ) )
        self.__message = QTextEdit()
        self.__message.setAcceptRichText( False )
        metrics = QFontMetrics( self.__message.font() )
        rect = metrics.boundingRect( "X" )
        self.__message.setFixedHeight( rect.height() * 4 + 5 )
        vboxLayout.addWidget( self.__message )

        # Diff part
        diffHeaderFrame = QFrame()
        diffHeaderFrame.setFrameStyle( QFrame.StyledPanel )
        diffHeaderFrame.setAutoFillBackground( True )
        self.__setLightPalette( diffHeaderFrame )
        diffHeaderFrame.setFixedHeight( 24 )

        diffLabel = QLabel( "Diff" )
        diffExpandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__showHideDiffButton = QToolButton()
        self.__showHideDiffButton.setAutoRaise( True )
        self.__showHideDiffButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideDiffButton.setFixedSize( 20, 20 )
        self.__showHideDiffButton.setToolTip( "Show diff" )
        self.__showHideDiffButton.setFocusPolicy( Qt.NoFocus )
        self.__showHideDiffButton.clicked.connect( self.__onShowHideDiff )

        diffLayout = QHBoxLayout()
        diffLayout.setContentsMargins( 3, 0, 0, 0 )
        diffLayout.addWidget( diffLabel )
        diffLayout.addSpacerItem( diffExpandingSpacer )
        diffLayout.addWidget( self.__showHideDiffButton )
        diffHeaderFrame.setLayout( diffLayout )

        self.__diffViewer = DiffTabWidget()
        self.__diffViewer.setHTML( self.NODIFF )
        self.__diffViewer.setVisible( False )

        vboxLayout.addWidget( diffHeaderFrame )
        vboxLayout.addWidget( self.__diffViewer )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setText( "Commit" )
        buttonBox.button( QDialogButtonBox.Cancel ).setDefault( True )
        buttonBox.accepted.connect( self.userAccept )
        buttonBox.rejected.connect( self.close )
        vboxLayout.addWidget( buttonBox )
        return

    def __onShowHideDiff( self ):
        if self.__diffViewer.isVisible():
            self.__diffViewer.setVisible( False )
            self.__showHideDiffButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideDiffButton.setToolTip( "Show diff" )
        else:
            self.__diffViewer.setVisible( True )
            self.__showHideDiffButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideDiffButton.setToolTip( "Hide diff" )
        return

    def __onShowHideIgnored( self ):
        if self.__pathToIgnoreView.isVisible():
            self.__pathToIgnoreView.setVisible( False )
            self.__showHideIgnoredButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideIgnoredButton.setToolTip( "Show ignored path list" )
        else:
            self.__pathToIgnoreView.setVisible( True )
            self.__showHideIgnoredButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideIgnoredButton.setToolTip( "Hide ignored path list" )
        return

    def userAccept( self ):
        " Triggered when the user clicks OK "
        # Collect the list of checked paths
        self.commitMessage = self.__message.toPlainText().strip()

        self.commitPaths = []
        index = 0
        while index < self.__pathToCommitView.topLevelItemCount():
            item = self.__pathToCommitView.topLevelItem( index )
            if item.checkState( 0 ) == Qt.Checked:
                path = str( item.text( 1 ) )
                if os.path.isdir( path ) and not os.path.islink( path ) and \
                                             not path.endswith( os.path.sep ):
                    path += os.path.sep
                self.commitPaths.append( path )
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

    def onDiff( self, path, status ):
        " Triggered when diff for the path is called "
        if not path:
            return

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        try:
            # Status is one of the following:
            # IND_ADDED, IND_DELETED, IND_MERGED, IND_MODIFIED_LR, IND_MODIFIED_L, IND_CONFLICTED
            repositoryContent = ""
            localContent = ""
            if status != IND_ADDED:
                client = self.__plugin.getSVNClient( self.__plugin.getSettings() )
                repositoryContent = client.cat( path )
            if status != IND_DELETED:
                with open( path ) as f:
                    localContent = f.read()

            diff = difflib.unified_diff( repositoryContent.splitlines(),
                                         localContent.splitlines() )
            nodiffMessage = path + " has no difference to the " \
                                   "repository at revision HEAD"
            if diff is None:
                QApplication.restoreOverrideCursor()
                logging.info( nodiffMessage )
                return

            # There are changes, so replace the text and tell about the changes
            diffAsText = '\n'.join( list( diff ) )
            if diffAsText.strip() == '':
                QApplication.restoreOverrideCursor()
                logging.info( nodiffMessage )
                return

            source = "+++ local " + os.path.basename( path )
            diffAsText = diffAsText.replace( "+++ ", source, 1 )
            diffAsText = diffAsText.replace( "--- ",
                                             "--- repository at revision HEAD", 1 )

            self.__diffViewer.setHTML( parse_from_memory( diffAsText, False, True ) )
            if not self.__diffViewer.isVisible():
                self.__onShowHideDiff()
        except Exception, exc:
            logging.error( str( exc ) )
        except:
            logging.error( "Unknown error while calculating difference for " +
                           path )

        QApplication.restoreOverrideCursor()
        return
