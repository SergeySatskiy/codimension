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

""" list viewer base class for classes/func etc list viewers """

import os.path, logging
from PyQt4.QtCore       import Qt, SIGNAL, QStringList, QSize
from PyQt4.QtGui        import QTreeWidget, QTreeWidgetItem, \
                               QHeaderView, QMenu, QCursor, \
                               QWidget, QAction, QDialog, \
                               QVBoxLayout, QSizePolicy, QToolBar, \
                               QApplication, QCursor
from utils.pixmapcache  import PixmapCache
from utils.settings     import Settings
from utils.project      import getProjectProperties, CodimensionProject
from utils.globals      import GlobalData
from projectproperties  import ProjectPropertiesDialog
from itemdelegates      import NoOutlineHeightDelegate



class RecentProjectViewItem( QTreeWidgetItem ):
    """ Single recent projects view item data structure """

    def __init__( self, fileName ):

        # full file name is expected
        projectName = os.path.basename( fileName ).replace( '.cdm', '' )
        QTreeWidgetItem.__init__( self,
                QStringList() << "" << projectName + "   " << fileName )

        self.__isValid = True
        self.updateTooltip()
        return

    def updateTooltip( self ):
        " Updates the item tooltip "

        fileName = self.getFilename()

        # Check that the file exists
        if not os.path.exists( fileName ):
            self.__isValid = False
            self.setToolTip( 0, 'Project file does not exist' )
            self.setToolTip( 1, 'Project file does not exist' )
            self.__markBroken()
        else:

            # Get the project properties
            try:
                creationDate, author, lic, \
                copy_right, description, \
                version, email, uuid = getProjectProperties( fileName )
                propertiesToolTip = "Version: " + version + "\n" \
                                    "Description: " + description + "\n" \
                                    "Author: " + author + "\n" \
                                    "e-mail: " + email + "\n" \
                                    "Copyright: " + copy_right + "\n" \
                                    "License: " + lic + "\n" \
                                    "Creation date: " + creationDate + "\n" \
                                    "UUID: " + uuid
                self.setToolTip( 1, propertiesToolTip )
                self.setText( 0, "" )
                if fileName == GlobalData().project.fileName:
                    self.__markCurrent()
            except:
                # cannot get project properties. Mark broken.
                self.__isValid = False
                self.setToolTip( 0, 'Broken project file' )
                self.setToolTip( 1, 'Broken project file' )
                self.__markBroken()
        return

    def __markBroken( self ):
        """ Mark the broken project with an icon """
        self.setIcon( 0, PixmapCache().getIcon( 'brokenproject.png' ) )
        return

    def __markCurrent( self ):
        """ Mark the current project with an icon """
        self.setIcon( 0, PixmapCache().getIcon( 'currentproject.png' ) )
        return

    def getFilename( self ):
        """ Provides the full project filename """
        return str( self.text( 2 ) )

    def isValid( self ):
        """ True if the project is valid """
        return self.__isValid


class RecentProjectsViewer( QWidget ):
    """ Recent projects viewer implementation """

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__createLayout()

        # create the context menu
        self.__menu = QMenu( self.projectsView )
        self.__loadMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'load.png' ),
                                'Load',
                                self.__loadProject )
        self.__menu.addSeparator()
        self.__propsMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'smalli.png' ),
                                'Properties',
                                self.__viewProperties )
        self.__menu.addSeparator()
        self.__delMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'trash.png' ),
                                'Delete from recent',
                                self.__deleteProject )
        self.projectsView.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.projectsView,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowContextMenu )

        self.connect( Settings().iInstance, SIGNAL( 'recentListChanged' ),
                      self.__populate )
        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__projectChanged )

        self.__contextItem = None
        self.__populate()
        self.__updateToolbarButtons()
        return

    def __createLayout( self ):
        " Helper to create the viewer layout "

        # Toolbar part - buttons
        self.loadButton = QAction( PixmapCache().getIcon( 'load.png' ),
                                   'Load the highlighted project', self )
        self.connect( self.loadButton, SIGNAL( "triggered()" ),
                      self.__loadProject )
        self.propertiesButton = QAction( PixmapCache().getIcon( 'smalli.png' ),
                                         'Show the highlighted project ' \
                                         'properties', self )
        self.connect( self.propertiesButton, SIGNAL( "triggered()" ),
                      self.__viewProperties )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.trashButton = QAction( PixmapCache().getIcon( 'trash.png' ),
                                    'Remove from the recent list (not from ' \
                                    'the disk)', self )
        self.connect( self.trashButton, SIGNAL( "triggered()" ),
                      self.__deleteProject )

        toolbar = QToolBar()
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.TopToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedHeight( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        toolbar.addAction( self.loadButton )
        toolbar.addAction( self.propertiesButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( self.trashButton )

        self.projectsView = QTreeWidget()
        self.projectsView.setAlternatingRowColors( True )
        self.projectsView.setRootIsDecorated( False )
        self.projectsView.setItemsExpandable( False )
        self.projectsView.setSortingEnabled( True )
        self.projectsView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.projectsView.setUniformRowHeights( True )

        self.__headerItem = QTreeWidgetItem(
                QStringList() << "" << "Project" << "File name" )
        self.projectsView.setHeaderItem( self.__headerItem )

        self.projectsView.header().setSortIndicator( 1, Qt.AscendingOrder )
        self.connect( self.projectsView,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__projectActivated )
        self.connect( self.projectsView,
                      SIGNAL( "itemSelectionChanged()" ),
                      self.__selectionChanged )

        layout = QVBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( toolbar )
        layout.addWidget( self.projectsView )

        self.setLayout( layout )
        return

    def __selectionChanged( self ):
        " Handles the changed selection "

        selected = list( self.projectsView.selectedItems() )
        if len( selected ) > 1:
            raise Exception( "Internal error. Only one recent project must " \
                             "be selectable. Please contact developers." )

        if len( selected ) == 0:
            self.__contextItem = None
        else:
            self.__contextItem = selected[ 0 ]
        self.__updateToolbarButtons()
        return

    def __updateToolbarButtons( self ):
        " Updates the toolbar buttons depending on the __contextItem "

        if self.__contextItem == None:
            self.loadButton.setEnabled( False )
            self.propertiesButton.setEnabled( False )
            self.trashButton.setEnabled( False )
        else:
            enabled = self.__contextItem.isValid()
            self.propertiesButton.setEnabled( enabled )
            if enabled and \
               self.__contextItem.getFilename() != \
                    GlobalData().project.fileName:
                self.loadButton.setEnabled( True )
                self.trashButton.setEnabled( True )
            else:
                self.loadButton.setEnabled( False )
                self.trashButton.setEnabled( False )
        return

    def __handleShowContextMenu( self, coord ):
        " Show the context menu "

        self.__contextItem = self.projectsView.itemAt( coord )
        if self.__contextItem is None:
            return

        enabled = self.__contextItem.isValid()
        self.__propsMenuItem.setEnabled( enabled )
        self.__delMenuItem.setEnabled( True )
        if enabled and \
           self.__contextItem.getFilename() != GlobalData().project.fileName:
            self.__loadMenuItem.setEnabled( True )
        else:
            self.__loadMenuItem.setEnabled( False )

        self.__menu.popup( QCursor.pos() )
        return

    def __sort( self ):
        """ Sort the items """

        self.projectsView.sortItems( \
                self.projectsView.sortColumn(),
                self.projectsView.header().sortIndicatorOrder() )
        return

    def __resizeColumns( self ):
        """ Resize the list columns """

        self.projectsView.header().setStretchLastSection( True )
        self.projectsView.header().resizeSections( \
                                    QHeaderView.ResizeToContents )
        self.projectsView.header().resizeSection( 0, 22 )
        return

    def __projectActivated( self, item, column ):
        """ Handles the double click (or Enter) on the item """

        self.__contextItem = item
        self.__loadProject()
        return

    def __viewProperties( self ):
        """ Handles the 'view properties' context menu item """

        if self.__contextItem is None:
            return
        if not self.__contextItem.isValid():
            return

        if self.__contextItem.getFilename() == GlobalData().project.fileName:
            # This is the current project - it can be edited
            project = GlobalData().project
            dialog = ProjectPropertiesDialog( project )
            if dialog.exec_() == QDialog.Accepted:
                project.updateProperties( \
                    str( dialog.creationDateEdit.text() ).strip(),
                    str( dialog.authorEdit.text() ).strip(),
                    str( dialog.licenseEdit.text() ).strip(),
                    str( dialog.copyrightEdit.text() ).strip(),
                    str( dialog.versionEdit.text() ).strip(),
                    str( dialog.emailEdit.text() ).strip(),
                    str( dialog.descriptionEdit.toPlainText() ).strip() )
        else:
            # This is not the current project - it can be viewed
            dialog = ProjectPropertiesDialog( self.__contextItem.getFilename() )
            dialog.exec_()
        return

    def __deleteProject( self ):
        """ Handles the 'delete from recent' context menu item """

        if self.__contextItem is None:
            return

        # Removal from the visible list is done via a signal which comes back
        # from settings
        Settings().deleteRecentProject( self.__contextItem.getFilename() )
        return

    def __loadProject( self ):
        """ handles 'Load' context menu item """

        if self.__contextItem is None:
            return
        if not self.__contextItem.isValid():
            return

        projectFileName = self.__contextItem.getFilename()
        if projectFileName == GlobalData().project.fileName:
            return  # This is the current project

        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        if os.path.exists( projectFileName ):
            editorsManager = GlobalData().mainWindow.editorsManagerWidget.editorsManager
            if editorsManager.closeRequest():
                GlobalData().project.setTabsStatus( editorsManager.getTabsStatus() )
                editorsManager.closeAll()
                GlobalData().project.loadProject( projectFileName )
        else:
            logging.error( "The project " + \
                           os.path.basename( projectFileName ) + \
                           " disappeared from the file system." )
            self.__populate()
        QApplication.restoreOverrideCursor()
        return

    def __populate( self ):
        " Populates the recent projects "

        self.projectsView.clear()
        for item in Settings().recentProjects:
            self.projectsView.addTopLevelItem( RecentProjectViewItem( item ) )
        self.__sort()
        self.__resizeColumns()

        # It looks a bit dirty when the first item is selected automatically.
        # Let's suppress automatic selection
        #self.__contextItem = self.projectsView.topLevelItem( 0 )
        #if self.__contextItem != None:
        #    self.projectsView.setCurrentItem( self.__contextItem )

        self.__updateToolbarButtons()

       # for index in range( 0, self.projectsView.rowCount() ):
       #     self.projectsView.verticalHeader().resizeSection( index, 22 )

        return

    def __projectChanged( self, what ):
        " Triggered when the current project is changed "

        if what == CodimensionProject.CompleteProject:
            self.__populate()
            return

        if what == CodimensionProject.Properties:
            # Update the corresponding tooltip
            items = self.projectsView.findItems( GlobalData().project.fileName,
                                                 Qt.MatchExactly, 2 )
            if len( items ) != 1:
                logging.error( "Unexpected number of matched projects: " + \
                               str( len( items ) ) )
                return

            items[ 0 ].updateTooltip()
            return

