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

" Codimension SVN plugin LOG command implementation "

import logging
import os.path
import difflib
from PyQt4.QtCore import Qt, SIGNAL, QTimer, QStringList
from PyQt4.QtGui import ( QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                          QApplication, QCursor, QFrame, QSpacerItem,
                          QSizePolicy, QToolButton, QHBoxLayout, QGroupBox,
                          QPalette, QTreeWidget, QTreeWidgetItem,
                          QHeaderView, QPushButton )
from utils.pixmapcache import PixmapCache
from ui.difftabwidget import DiffTabWidget
from svnindicators import pluginHomeDir
from ui.itemdelegates import NoOutlineHeightDelegate
from svnstrconvert import timestampToString
from thirdparty.diff2html.diff2html import parse_from_memory


class SVNLogMixin:

    def __init__( self ):
        return

    def fileLog( self ):
        " Called when log for a file is requested "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnLog( path )
        return

    def bufferLog( self ):
        " Called when log for a buffer is requested "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN log is not "
                          "applicable for never saved buffer" )
            return
        self.__svnLog( path )
        return

    def __svnLog( self, path ):
        " Does SVN annotate "
        client = self.getSVNClient( self.getSettings() )
        dlg = SVNLogProgress( client, path )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        res = dlg.exec_()
        QApplication.restoreOverrideCursor()

        if res == QDialog.Accepted:
            dlg = SVNPluginLogDialog( self, client, path, dlg.logInfo )
            dlg.exec_()
        return


class SVNLogProgress( QDialog ):
    " Minimalistic progress dialog "

    def __init__( self, client, path, parent = None ):
        QDialog.__init__( self, parent )
        self.__cancelRequest = False
        self.__inProcess = False

        self.__client = client
        self.__path = path

        # Transition data
        self.logInfo = None

        self.__createLayout()
        self.setWindowTitle( "SVN Log" )
        QTimer.singleShot( 0, self.__process )
        return

    def keyPressEvent( self, event ):
        " Processes the ESC key specifically "
        if event.key() == Qt.Key_Escape:
            self.__cancelRequest = True
            self.__infoLabel.setText( "Cancelling..." )
            QApplication.processEvents()
        return

    def __createLayout( self ):
        " Creates the dialog layout "
        self.resize( 450, 20 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )
        self.__infoLabel = QLabel( "Retrieving log of '" +
                                   self.__path + "'..." )
        verticalLayout.addWidget( self.__infoLabel )

        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Close )
        verticalLayout.addWidget( buttonBox )

        buttonBox.rejected.connect( self.__onClose )
        return

    def __onClose( self ):
        " Triggered when the close button is clicked "
        self.__cancelRequest = True
        self.__infoLabel.setText( "Cancelling..." )
        QApplication.processEvents()
        return

    def closeEvent( self, event ):
        " Window close event handler "
        if self.__inProcess:
            self.__cancelRequest = True
            self.__infoLabel.setText( "Cancelling..." )
            QApplication.processEvents()
            event.ignore()
        else:
            event.accept()
        return

    def __cancelCallback( self ):
        " Called by pysvn regularly "
        QApplication.processEvents()
        return self.__cancelRequest

    def __process( self ):
        " Update process "
        self.__client.callback_cancel = self.__cancelCallback

        try:
            self.logInfo = self.__client.log( self.__path )
        except Exception, exc:
            logging.error( str( exc ) )
            self.close()
            return
        except:
            logging.error( "Unknown error while retrieving log of " +
                           self.__path )
            self.close()
            return

        if self.__cancelRequest:
            self.close()
        else:
            self.accept()
        return



class DiffButton( QPushButton ):
    " Custom diff button "

    def __init__( self ):
        QPushButton.__init__( self,
                              PixmapCache().getIcon( pluginHomeDir + 'svnmenudiff.png' ),
                              "" )
        self.setFixedSize( 24, 24 )
        self.setFocusPolicy( Qt.NoFocus )

        self.rev = None
        self.prevRev = None
        self.clicked.connect( self.onClick )
        return

    def onClick( self ):
        " Emits a signal with the button index "
        self.emit( SIGNAL( "CustomClick" ), self.rev, self.prevRev )
        return



SELECT_COL = 0
DIFFTONEXT_COL = 1
REVISION_COL = 2
DATE_COL = 3
AUTHOR_COL = 4
MESSAGE_COL = 5


class LogItem( QTreeWidgetItem ):
    " Single item in the log list "
    def __init__( self, logInfo ):
        self.logInfo = logInfo

        message = ""
        if logInfo.message:
            message = str( logInfo.message )
        authorTooltip = ""
        author = ""
        if logInfo.author:
            authorTooltip = str( logInfo.author )
            author = authorTooltip.split( "@", 1 )[ 0 ]
        revision = ""
        if logInfo.revision:
            if logInfo.revision.number:
                revision = str( logInfo.revision.number )
        date = ""
        if logInfo.date:
            date = timestampToString( logInfo.date )

        QTreeWidgetItem.__init__( self,
            QStringList() << "" << "" << revision << date << author << message )

        self.setCheckState( SELECT_COL, Qt.Unchecked )
        self.setToolTip( REVISION_COL, revision )
        self.setToolTip( DATE_COL, date )
        self.setToolTip( AUTHOR_COL, authorTooltip )
        self.setToolTip( MESSAGE_COL, message )
        return

    def __lt__( self, otherItem ):
        " Provides the custom sorting "
        col = self.treeWidget().sortColumn()
        try:
            if col == REVISION_COL:
                return int( self.text( col ) ) > int( otherItem.text( col ) )
        except ValueError:
            pass
        return self.text( col ) > otherItem.text( col )



class SVNPluginLogDialog( QDialog ):
    " SVN plugin log dialog "

    NODIFF = '<html><body bgcolor="#ffffe6"></body></html>'

    def __init__( self, plugin, client, path, logInfo, parent = None ):
        QDialog.__init__( self, parent )

        self.__plugin = plugin
        self.__client = client
        self.__path = path
        self.__logInfo = logInfo

        self.__lhsSelected = None
        self.__rhsSelected = None

        self.__createLayout()
        self.setWindowTitle( "SVN Log" )

        lastIndex = len( self.__logInfo ) - 1
        index = 0
        for log in self.__logInfo:
            newItem = LogItem( log )
            self.__logView.addTopLevelItem( newItem )

            if index != lastIndex:
                rev = log.revision.number
                nextRev = self.__logInfo[ index + 1 ].revision.number
                diffButton = self.__createDiffButton( log.revision,
                                                      self.__logInfo[ index + 1 ].revision )
                if rev is not None and nextRev is not None:
                    diffButton.setToolTip( "Click to see diff to the older revision (r." +
                                           str( rev ) + " to r." + str( nextRev ) + ")" )
                else:
                    diffButton.setEnabled( False )
                    diffButton.setToolTip( "Could not determine current or previous revision" )
            else:
                diffButton = self.__createDiffButton( None, None )
                diffButton.setEnabled( False )
                diffButton.setToolTip( "Diff to previous revision is not avalable for the first revision" )

            self.__logView.setItemWidget( newItem, DIFFTONEXT_COL, diffButton )
            index += 1

        self.__resizeLogView()
        self.__sortLogView()

        self.__logView.setFocus()
        return

    def __createDiffButton( self, rev, prevRev ):
        " Creates a diff button for a path "
        button = DiffButton()
        button.rev = rev
        button.prevRev = prevRev
        self.connect( button, SIGNAL( 'CustomClick' ), self.onDiffBetween )
        return button

    def __resizeLogView( self ):
        " Resizes the plugins table "
        self.__logView.header().setStretchLastSection( True )
        self.__logView.header().resizeSections(
                                        QHeaderView.ResizeToContents )
        self.__logView.header().resizeSection( SELECT_COL, 28 )
        self.__logView.header().setResizeMode( SELECT_COL, QHeaderView.Fixed )

        self.__logView.header().resizeSection( DIFFTONEXT_COL, 24 )
        self.__logView.header().setResizeMode( DIFFTONEXT_COL, QHeaderView.Fixed )
        return

    def __sortLogView( self ):
        " Sorts the log table "
        self.__logView.sortItems(
                    self.__logView.sortColumn(),
                    self.__logView.header().sortIndicatorOrder() )
        return

    def __createLayout( self ):
        " Creates the dialog layout "
        self.resize( 640, 480 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )

        # Revisions to compare
        compareGroupbox = QGroupBox( self )
        compareGroupbox.setTitle( "Revisions to compare" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(
                        compareGroupbox.sizePolicy().hasHeightForWidth() )
        compareGroupbox.setSizePolicy( sizePolicy )

        revisionLayout = QHBoxLayout( compareGroupbox )

        self.__lhsRevisionLabel = QLabel()
        self.__lhsRevisionLabel.setFrameStyle( QFrame.StyledPanel )
        self.__lhsResetButton = QToolButton()
        self.__lhsResetButton.setIcon( PixmapCache().getIcon( pluginHomeDir + 'svnclearrev.png' ) )
        self.__lhsResetButton.setFocusPolicy( Qt.NoFocus )
        self.__lhsResetButton.setEnabled( False )
        self.__lhsResetButton.setToolTip( "Reset revision to compare" )
        self.__lhsResetButton.clicked.connect( self.__onLHSReset )
        self.__rhsRevisionLabel = QLabel()
        self.__rhsRevisionLabel.setFrameStyle( QFrame.StyledPanel )
        self.__rhsResetButton = QToolButton()
        self.__rhsResetButton.setIcon( PixmapCache().getIcon( pluginHomeDir + 'svnclearrev.png' ) )
        self.__rhsResetButton.setFocusPolicy( Qt.NoFocus )
        self.__rhsResetButton.setEnabled( False )
        self.__rhsResetButton.setToolTip( "Reset revision to compare" )
        self.__rhsResetButton.clicked.connect( self.__onRHSReset )

        lhsLayout = QHBoxLayout()
        lhsLayout.addWidget( self.__lhsRevisionLabel )
        lhsLayout.addWidget( self.__lhsResetButton )
        rhsLayout = QHBoxLayout()
        rhsLayout.addWidget( self.__rhsRevisionLabel )
        rhsLayout.addWidget( self.__rhsResetButton )
        bothLayout = QVBoxLayout()
        bothLayout.addLayout( lhsLayout )
        bothLayout.addLayout( rhsLayout )
        revisionLayout.addLayout( bothLayout )

        self.__diffButton = QToolButton()
        self.__diffButton.setText( "Diff" )
        self.__diffButton.setFocusPolicy( Qt.NoFocus )
        self.__diffButton.setEnabled( False )
        self.__diffButton.clicked.connect( self.__onDiff )
        revisionLayout.addWidget( self.__diffButton )
        vboxLayout.addWidget( compareGroupbox )

        # Log table
        logHeaderFrame = QFrame()
        logHeaderFrame.setFrameStyle( QFrame.StyledPanel )
        logHeaderFrame.setAutoFillBackground( True )
        self.__setLightPalette( logHeaderFrame )
        logHeaderFrame.setFixedHeight( 24 )

        logHeaderLayout = QHBoxLayout()
        logHeaderLayout.setContentsMargins( 3, 0, 0, 0 )
        logHeaderLayout.addWidget( QLabel( "Subversion log of " + self.__path ) )
        logHeaderFrame.setLayout( logHeaderLayout )
        vboxLayout.addWidget( logHeaderFrame )

        self.__logView = QTreeWidget()
        self.__logView.setAlternatingRowColors( True )
        self.__logView.setRootIsDecorated( False )
        self.__logView.setItemsExpandable( False )
        self.__logView.setSortingEnabled( True )
        self.__logView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        self.__logViewHeader = QTreeWidgetItem(
                QStringList() << "" << "" << "Revision" << "Date" << "Author" << "Message" )
        self.__logView.setHeaderItem( self.__logViewHeader )
        self.__logView.header().setSortIndicator( REVISION_COL, Qt.AscendingOrder )
        self.__logView.itemChanged.connect( self.__onLogViewChanged )
        vboxLayout.addWidget( self.__logView )


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
        buttonBox.setStandardButtons( QDialogButtonBox.Ok )
        buttonBox.button( QDialogButtonBox.Ok ).setDefault( True )
        buttonBox.accepted.connect( self.close )
        vboxLayout.addWidget( buttonBox )
        return

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

    def __onShowHideDiff( self ):
        " On/off the diff section "
        if self.__diffViewer.isVisible():
            self.__diffViewer.setVisible( False )
            self.__showHideDiffButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideDiffButton.setToolTip( "Show diff" )
        else:
            self.__diffViewer.setVisible( True )
            self.__showHideDiffButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideDiffButton.setToolTip( "Hide diff" )
        return

    def onDiffBetween( self, rev, prevRev ):
        " Called when diff is requested between revisions "
        if not rev or not prevRev:
            return

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            lhsContent = self.__client.cat( self.__path, prevRev )
            rhsContent = self.__client.cat( self.__path, rev )
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            return
        except:
            QApplication.restoreOverrideCursor()
            logging.error( "Unknown error while retrieving " + self.__path +
                           " content from the repository." )
            return
        QApplication.restoreOverrideCursor()


        diff = difflib.unified_diff( lhsContent.splitlines(),
                                     rhsContent.splitlines() )
        nodiffMessage = self.__path + " has no difference from revision " + \
                        str( prevRev.number ) + " to revision " + \
                        str( rev.number )
        if diff is None:
            logging.info( nodiffMessage )
            return

        # There are changes, so replace the text and tell about the changes
        diffAsText = '\n'.join( list( diff ) )
        if diffAsText.strip() == '':
            logging.info( nodiffMessage )
            return

        lhs = "--- revision " + str( prevRev.number )
        diffAsText = diffAsText.replace( "--- ", lhs, 1 )
        rhs = "+++ revision " + str( rev.number )
        diffAsText = diffAsText.replace( "+++ ", rhs, 1 )

        self.__diffViewer.setHTML( parse_from_memory( diffAsText, False, True ) )
        if not self.__diffViewer.isVisible():
            self.__onShowHideDiff()
        return

    def __onDiff( self ):
        " Show diff between revisions "
        self.onDiffBetween( self.__rhsSelected.revision,
                            self.__lhsSelected.revision )
        return

    def __onLogViewChanged( self, item, column ):
        " Revision selected for diff "
        if item.checkState( SELECT_COL ) == Qt.Checked:
            # An item has been selected
            if self.__lhsSelected is None:
                self.__lhsSelected = item.logInfo
                self.__normalizeSelected()
                return
            if self.__rhsSelected is None:
                self.__rhsSelected = item.logInfo
                self.__normalizeSelected()
                return

            # Both of the places have been occupied. Pick the one to update.
            if item.logInfo.date > self.__rhsSelected.date:
                self.__rhsSelected = item.logInfo
            else:
                self.__lhsSelected = item.logInfo
            self.__normalizeSelected()
        else:
            # An item has been de-selected
            if self.__lhsSelected is not None:
                if self.__lhsSelected.revision.number == item.logInfo.revision.number:
                    self.__lhsSelected = None
            elif self.__rhsSelected is not None:
                if self.__rhsSelected.revision.number == item.logInfo.revision.number:
                    self.__rhsSelected = None
            self.__normalizeSelected()
        return

    def __onLHSReset( self ):
        " Revision removed from diff "
        if self.__lhsSelected is not None:
            self.__deselectRevision( self.__lhsSelected.revision.number )
        self.__lhsSelected = None
        self.__lhsRevisionLabel.setText( "" )
        self.__diffButton.setEnabled( False )
        self.__lhsResetButton.setEnabled( False )
        return

    def __onRHSReset( self ):
        " Revision removed from diff "
        if self.__rhsSelected is not None:
            self.__deselectRevision( self.__rhsSelected.revision.number )
        self.__rhsSelected = None
        self.__rhsRevisionLabel.setText( "" )
        self.__diffButton.setEnabled( False )
        self.__rhsResetButton.setEnabled( False )
        return

    def __deselectRevision( self, revNumber ):
        " Deselects a revision in the list "
        index = 0
        while index < self.__logView.topLevelItemCount():
            item = self.__logView.topLevelItem( index )
            if item.logInfo.revision.number == revNumber:
                item.setCheckState( SELECT_COL, Qt.Unchecked )
                break
            index += 1
        return

    def __normalizeSelected( self ):
        " Puts the earliest revision first "
        if self.__lhsSelected is not None and self.__rhsSelected is not None:
            # It might be necessary to exchange the versions
            if self.__rhsSelected.date < self.__lhsSelected.date:
                temp = self.__rhsSelected
                self.__rhsSelected = self.__lhsSelected
                self.__lhsSelected = temp
            self.__diffButton.setEnabled( True )
        else:
            self.__diffButton.setEnabled( False )

        if self.__lhsSelected is None:
            self.__lhsRevisionLabel.setText( "" )
            self.__lhsRevisionLabel.setToolTip( "" )
            self.__lhsResetButton.setEnabled( False )
        else:
            self.__lhsRevisionLabel.setText( str( self.__lhsSelected.revision.number ) +
                    " (" + timestampToString( self.__lhsSelected.date ) + ")" )
            self.__lhsRevisionLabel.setToolTip( str( self.__lhsSelected.message ) )
            self.__lhsResetButton.setEnabled( True )

        if self.__rhsSelected is None:
            self.__rhsRevisionLabel.setText( "" )
            self.__rhsRevisionLabel.setToolTip( "" )
            self.__rhsResetButton.setEnabled( False )
        else:
            self.__rhsRevisionLabel.setText( str( self.__rhsSelected.revision.number ) +
                    " (" + timestampToString( self.__rhsSelected.date ) + ")" )
            self.__rhsRevisionLabel.setToolTip( str( self.__rhsSelected.message ) )
            self.__rhsResetButton.setEnabled( True )
        return
