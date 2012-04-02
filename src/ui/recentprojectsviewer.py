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
                               QHeaderView, QMenu, QCursor, QToolButton, \
                               QWidget, QAction, QDialog, QSpacerItem, \
                               QVBoxLayout, QSizePolicy, QToolBar, \
                               QApplication, QCursor, QFrame, QLabel, \
                               QHBoxLayout, QSplitter, QPalette
from utils.pixmapcache  import PixmapCache
from utils.settings     import Settings
from utils.project      import getProjectProperties, CodimensionProject
from utils.globals      import GlobalData
from projectproperties  import ProjectPropertiesDialog
from itemdelegates      import NoOutlineHeightDelegate
from utils.fileutils    import detectFileType, getFileIcon, \
                               PythonFileType, Python3FileType, \
                               CodimensionProjectFileType, PixmapFileType
from utils.compatibility import relpath


class RecentProjectViewItem( QTreeWidgetItem ):
    """ Single recent projects view item data structure """

    def __init__( self, fileName ):

        # full file name is expected
        projectName = os.path.basename( fileName ).replace( '.cdm', '' )
        QTreeWidgetItem.__init__( self,
                QStringList() << "" << projectName + "   " << fileName )

        self.__isValid = True
        self.__isCurrent = False
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
                scriptName, importDirs, creationDate, author, lic, \
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
        self.setToolTip( 2, self.getFilename() )
        return

    def __markBroken( self ):
        """ Mark the broken project with an icon """
        self.setIcon( 0, PixmapCache().getIcon( 'brokenproject.png' ) )
        return

    def __markCurrent( self ):
        """ Mark the current project with an icon """
        self.setIcon( 0, PixmapCache().getIcon( 'currentproject.png' ) )
        self.__isCurrent = True
        return

    def getFilename( self ):
        """ Provides the full project filename """
        return str( self.text( 2 ) )

    def isValid( self ):
        """ True if the project is valid """
        return self.__isValid

    def isCurrent( self ):
        " True if the project is current "
        return self.__isCurrent



class RecentFileViewItem( QTreeWidgetItem ):
    " Single recent file view item data structure "

    def __init__( self, fileName ):

        # full file name is expected
        basename = os.path.basename( fileName )
        QTreeWidgetItem.__init__( self,
                QStringList() << "" << basename + "   " << fileName )

        self.__isValid = True
        self.updateIconAndTooltip()
        return

    def updateIconAndTooltip( self ):
        " Updates the item icon and tooltip if required "
        if not os.path.exists( self.getFilename() ):
            self.__markBroken()
        else:
            self.__markOK()
        return

    def __markBroken( self ):
        " Mark the file as broken "
        self.__isValid = False
        self.setToolTip( 0, 'File does not exist' )
        self.setToolTip( 1, 'File does not exist' )
        self.setToolTip( 2, self.getFilename() )
        self.setIcon( 0, PixmapCache().getIcon( 'brokenproject.png' ) )
        return

    def __markOK( self ):
        " Mark the file as OK "
        self.__isValid = True
        fileName = self.getFilename()
        fileType = detectFileType( fileName )
        if fileType in [ PythonFileType, Python3FileType ]:
            # The tooltip could be the file docstring
            if GlobalData().project.isProjectFile( fileName ):
                infoSrc = GlobalData().project.briefModinfoCache
            else:
                infoSrc = GlobalData().briefModinfoCache
            info = infoSrc.get( fileName )
            if info.docstring is not None:
                self.setToolTip( 1, info.docstring.text )
            else:
                self.setToolTip( 1, "" )
            if info.isOK:
                self.setIcon( 0,
                              PixmapCache().getIcon( 'filepython.png' ) )
            else:
                self.setIcon( 0,
                              PixmapCache().getIcon( 'filepythonbroken.png' ) )
            self.setToolTip( 0, "" )

        elif fileType == CodimensionProjectFileType:
            # Get the project properties
            try:
                scriptName, importDirs, creationDate, author, lic, \
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
                self.setToolTip( 0, "" )
                self.setToolTip( 1, propertiesToolTip )
                self.setText( 0, "" )
            except:
                # cannot get project properties. Mark broken.
                self.__isValid = False
                self.setToolTip( 0, 'Broken project file' )
                self.setToolTip( 1, 'Broken project file' )
            self.setIcon( 0, getFileIcon( fileType ) )
        else:
            # Get the other file type icon
            self.setIcon( 0, getFileIcon( fileType ) )

        self.setToolTip( 2, self.getFilename() )
        return

    def getFilename( self ):
        " Provides the full file name "
        return str( self.text( 2 ) )

    def isValid( self ):
        " True if the file is still valid "
        return self.__isValid



class RecentProjectsViewer( QWidget ):
    " Recent projects viewer implementation "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__projectContextItem = None
        self.__fileContextItem = None

        self.upper = self.__createRecentFilesLayout()
        self.lower = self.__createRecentProjectsLayout()
        self.__createProjectPopupMenu()
        self.__createFilePopupMenu()

        layout = QVBoxLayout()
        layout.setContentsMargins( 1, 1, 1, 1 )
        splitter = QSplitter( Qt.Vertical )
        splitter.addWidget( self.upper )
        splitter.addWidget( self.lower )
        splitter.setCollapsible( 0, False )
        splitter.setCollapsible( 1, False )

        layout.addWidget( splitter )
        self.setLayout( layout )

        self.__populateProjects()
        self.__populateFiles()
        self.__updateProjectToolbarButtons()
        self.__updateFileToolbarButtons()

        # Debugging mode support
        self.__debugMode = False
        self.connect( parent, SIGNAL( 'debugModeChanged' ),
                      self.__onDebugMode )
        return

    def __createFilePopupMenu( self ):
        " create the recent files popup menu "
        self.__fileMenu = QMenu( self.recentFilesView )
        self.__openMenuItem = self.__fileMenu.addAction( \
                                PixmapCache().getIcon( 'openitem.png' ),
                                'Open', self.__openFile )
        self.__copyPathFileMenuItem = self.__fileMenu.addAction( \
                        PixmapCache().getIcon( 'copytoclipboard.png' ),
                        'Copy path to clipboard', self.__filePathToClipboard )
        self.__fileMenu.addSeparator()
        self.__delFileMenuItem = self.__fileMenu.addAction( \
                                PixmapCache().getIcon( 'trash.png' ),
                                'Delete from recent',
                                self.__deleteFile )
        self.recentFilesView.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.recentFilesView,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowFileContextMenu )

        self.connect( GlobalData().project, SIGNAL( 'recentFilesChanged' ),
                      self.__populateFiles )
        return


    def __createProjectPopupMenu( self ):
        " Creates the recent project popup menu "
        self.__projectMenu = QMenu( self.projectsView )
        self.__prjLoadMenuItem = self.__projectMenu.addAction( \
                                PixmapCache().getIcon( 'load.png' ),
                                'Load',
                                self.__loadProject )
        self.__projectMenu.addSeparator()
        self.__propsMenuItem = self.__projectMenu.addAction( \
                                PixmapCache().getIcon( 'smalli.png' ),
                                'Properties',
                                self.__viewProperties )
        self.__prjCopyPathMenuItem = self.__projectMenu.addAction( \
                                PixmapCache().getIcon( 'copytoclipboard.png' ),
                                'Copy path to clipboard',
                                self.__prjPathToClipboard )
        self.__projectMenu.addSeparator()
        self.__delPrjMenuItem = self.__projectMenu.addAction( \
                                PixmapCache().getIcon( 'trash.png' ),
                                'Delete from recent',
                                self.__deleteProject )
        self.projectsView.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.projectsView,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowPrjContextMenu )

        self.connect( Settings().iInstance, SIGNAL( 'recentListChanged' ),
                      self.__populateProjects )
        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__projectChanged )
        return

    def __createRecentFilesLayout( self ):
        " Creates the upper part - recent files "
        headerFrame = QFrame()
        headerFrame.setFrameStyle( QFrame.StyledPanel )
        headerFrame.setAutoFillBackground( True )
        headerPalette = headerFrame.palette()
        headerBackground = headerPalette.color( QPalette.Background )
        headerBackground.setRgb( min( headerBackground.red() + 30, 255 ),
                                 min( headerBackground.green() + 30, 255 ),
                                 min( headerBackground.blue() + 30, 255 ) )
        headerPalette.setColor( QPalette.Background, headerBackground )
        headerFrame.setPalette( headerPalette )
        headerFrame.setFixedHeight( 24 )

        recentFilesLabel = QLabel()
        recentFilesLabel.setText( "Recent files" )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 3, 0, 0, 0 )
        headerLayout.addWidget( recentFilesLabel )
        headerFrame.setLayout( headerLayout )

        self.recentFilesView = QTreeWidget()
        self.recentFilesView.setAlternatingRowColors( True )
        self.recentFilesView.setRootIsDecorated( False )
        self.recentFilesView.setItemsExpandable( False )
        self.recentFilesView.setSortingEnabled( True )
        self.recentFilesView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.recentFilesView.setUniformRowHeights( True )

        self.__filesHeaderItem = QTreeWidgetItem(
                QStringList() << "" << "File" << "Absolute path" )
        self.recentFilesView.setHeaderItem( self.__filesHeaderItem )
        self.recentFilesView.header().setSortIndicator( 1, Qt.AscendingOrder )

        self.connect( self.recentFilesView,
                      SIGNAL( "itemSelectionChanged()" ),
                      self.__fileSelectionChanged )
        self.connect( self.recentFilesView,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__fileActivated )

        # Toolbar part - buttons
        self.openFileButton = QAction( PixmapCache().getIcon( 'openitem.png' ),
                                       'Open the highlighted file', self )
        self.connect( self.openFileButton, SIGNAL( "triggered()" ),
                      self.__openFile )
        self.copyFilePathButton = QAction( \
                        PixmapCache().getIcon( 'copytoclipboard.png' ),
                        'Copy path to clipboard', self )
        self.connect( self.copyFilePathButton, SIGNAL( "triggered()" ),
                      self.__filePathToClipboard )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.trashFileButton = QAction( PixmapCache().getIcon( 'trash.png' ),
                                        'Remove from the recent list (not ' \
                                        'from the disk)', self )
        self.connect( self.trashFileButton, SIGNAL( "triggered()" ),
                      self.__deleteFile )

        upperToolbar = QToolBar()
        upperToolbar.setMovable( False )
        upperToolbar.setAllowedAreas( Qt.TopToolBarArea )
        upperToolbar.setIconSize( QSize( 16, 16 ) )
        upperToolbar.setFixedHeight( 28 )
        upperToolbar.setContentsMargins( 0, 0, 0, 0 )
        upperToolbar.addAction( self.openFileButton )
        upperToolbar.addAction( self.copyFilePathButton )
        upperToolbar.addWidget( spacer )
        upperToolbar.addAction( self.trashFileButton )

        recentFilesLayout = QVBoxLayout()
        recentFilesLayout.setContentsMargins( 0, 0, 0, 0 )
        recentFilesLayout.setSpacing( 0 )
        recentFilesLayout.addWidget( headerFrame )
        recentFilesLayout.addWidget( upperToolbar )
        recentFilesLayout.addWidget( self.recentFilesView )

        upperContainer = QWidget()
        upperContainer.setContentsMargins( 0, 0, 0, 0 )
        upperContainer.setLayout( recentFilesLayout )
        return upperContainer

    def __createRecentProjectsLayout( self ):
        " Creates the bottom layout "
        self.headerFrame = QFrame()
        self.headerFrame.setFrameStyle( QFrame.StyledPanel )
        self.headerFrame.setAutoFillBackground( True )
        headerPalette = self.headerFrame.palette()
        headerBackground = headerPalette.color( QPalette.Background )
        headerBackground.setRgb( min( headerBackground.red() + 30, 255 ),
                                 min( headerBackground.green() + 30, 255 ),
                                 min( headerBackground.blue() + 30, 255 ) )
        headerPalette.setColor( QPalette.Background, headerBackground )
        self.headerFrame.setPalette( headerPalette )
        self.headerFrame.setFixedHeight( 24 )

        recentProjectsLabel = QLabel()
        recentProjectsLabel.setText( "Recent projects" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise( True )
        self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideButton.setFixedSize( 20, 20 )
        self.__showHideButton.setToolTip( "Hide recent projects list" )
        self.__showHideButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__showHideButton, SIGNAL( 'clicked()' ),
                      self.__onShowHide )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 3, 0, 0, 0 )
        headerLayout.addWidget( recentProjectsLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__showHideButton )
        self.headerFrame.setLayout( headerLayout )

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
        self.copyPrjPathButton = QAction( \
                        PixmapCache().getIcon( 'copytoclipboard.png' ),
                        'Copy path to clipboard', self )
        self.connect( self.copyPrjPathButton, SIGNAL( "triggered()" ),
                      self.__prjPathToClipboard )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.trashButton = QAction( PixmapCache().getIcon( 'trash.png' ),
                                    'Remove from the recent list (not from ' \
                                    'the disk)', self )
        self.connect( self.trashButton, SIGNAL( "triggered()" ),
                      self.__deleteProject )

        self.lowerToolbar = QToolBar()
        self.lowerToolbar.setMovable( False )
        self.lowerToolbar.setAllowedAreas( Qt.TopToolBarArea )
        self.lowerToolbar.setIconSize( QSize( 16, 16 ) )
        self.lowerToolbar.setFixedHeight( 28 )
        self.lowerToolbar.setContentsMargins( 0, 0, 0, 0 )
        self.lowerToolbar.addAction( self.loadButton )
        self.lowerToolbar.addAction( self.propertiesButton )
        self.lowerToolbar.addAction( self.copyPrjPathButton )
        self.lowerToolbar.addWidget( spacer )
        self.lowerToolbar.addAction( self.trashButton )

        self.projectsView = QTreeWidget()
        self.projectsView.setAlternatingRowColors( True )
        self.projectsView.setRootIsDecorated( False )
        self.projectsView.setItemsExpandable( False )
        self.projectsView.setSortingEnabled( True )
        self.projectsView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.projectsView.setUniformRowHeights( True )

        self.__projectsHeaderItem = QTreeWidgetItem(
                QStringList() << "" << "Project" << "Absolute path" )
        self.projectsView.setHeaderItem( self.__projectsHeaderItem )

        self.projectsView.header().setSortIndicator( 1, Qt.AscendingOrder )
        self.connect( self.projectsView,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__projectActivated )
        self.connect( self.projectsView,
                      SIGNAL( "itemSelectionChanged()" ),
                      self.__projectSelectionChanged )

        recentProjectsLayout = QVBoxLayout()
        recentProjectsLayout.setContentsMargins( 0, 0, 0, 0 )
        recentProjectsLayout.setSpacing( 0 )
        recentProjectsLayout.addWidget( self.headerFrame )
        recentProjectsLayout.addWidget( self.lowerToolbar )
        recentProjectsLayout.addWidget( self.projectsView )

        lowerContainer = QWidget()
        lowerContainer.setContentsMargins( 0, 0, 0, 0 )
        lowerContainer.setLayout( recentProjectsLayout )
        return lowerContainer

    def __projectSelectionChanged( self ):
        " Handles the projects changed selection "
        selected = list( self.projectsView.selectedItems() )
        if len( selected ) > 1:
            raise Exception( "Internal error. Only one recent project must " \
                             "be selectable. Please contact developers." )

        if len( selected ) == 0:
            self.__projectContextItem = None
        else:
            self.__projectContextItem = selected[ 0 ]
        self.__updateProjectToolbarButtons()
        return

    def __fileSelectionChanged( self ):
        " Handles the files changed selection "
        selected = list( self.recentFilesView.selectedItems() )
        if len( selected ) > 1:
            raise Exception( "Internal error. Only one recent file must " \
                             "be selectable. Please contact developers." )

        if len( selected ) == 0:
            self.__fileContextItem = None
        else:
            self.__fileContextItem = selected[ 0 ]
        self.__updateFileToolbarButtons()
        return

    def __updateProjectToolbarButtons( self ):
        " Updates the toolbar buttons depending on the __projectContextItem "
        if self.__projectContextItem == None:
            self.loadButton.setEnabled( False )
            self.propertiesButton.setEnabled( False )
            self.copyPrjPathButton.setEnabled( False )
            self.trashButton.setEnabled( False )
        else:
            enabled = self.__projectContextItem.isValid()
            isCurrentProject = self.__projectContextItem.isCurrent()

            self.propertiesButton.setEnabled( enabled )
            self.copyPrjPathButton.setEnabled( True )
            self.loadButton.setEnabled( enabled and \
                                        not isCurrentProject and \
                                        not self.__debugMode )
            self.trashButton.setEnabled( not isCurrentProject )
        return

    def __updateFileToolbarButtons( self ):
        " Updates the toolbar buttons depending on the __fileContextItem "
        enabled = self.__fileContextItem is not None
        self.openFileButton.setEnabled( enabled )
        self.copyFilePathButton.setEnabled( enabled )
        self.trashFileButton.setEnabled( enabled )
        return

    def __handleShowPrjContextMenu( self, coord ):
        " Show the project item context menu "
        self.__projectContextItem = self.projectsView.itemAt( coord )
        if self.__projectContextItem is None:
            return

        enabled = self.__projectContextItem.isValid()
        isCurrentProject = self.__projectContextItem.isCurrent()

        self.__propsMenuItem.setEnabled( enabled )
        self.__delPrjMenuItem.setEnabled( not isCurrentProject )
        fName = self.__projectContextItem.getFilename()
        self.__prjLoadMenuItem.setEnabled( enabled and \
                                           not isCurrentProject and \
                                           not self.__debugMode )

        self.__projectMenu.popup( QCursor.pos() )
        return

    def __sortProjects( self ):
        " Sort the project items "
        self.projectsView.sortItems( \
                self.projectsView.sortColumn(),
                self.projectsView.header().sortIndicatorOrder() )
        return

    def __sortFiles( self ):
        " Sort the file items "
        self.recentFilesView.sortItems( \
                self.recentFilesView.sortColumn(),
                self.recentFilesView.header().sortIndicatorOrder() )
        return

    def __resizeProjectColumns( self ):
        """ Resize the projects list columns """
        self.projectsView.header().setStretchLastSection( True )
        self.projectsView.header().resizeSections( \
                                    QHeaderView.ResizeToContents )
        self.projectsView.header().resizeSection( 0, 22 )
        self.projectsView.header().setResizeMode( 0, QHeaderView.Fixed )
        return

    def __resizeFileColumns( self ):
        " Resize the files list columns "
        self.recentFilesView.header().setStretchLastSection( True )
        self.recentFilesView.header().resizeSections( \
                                    QHeaderView.ResizeToContents )
        self.recentFilesView.header().resizeSection( 0, 22 )
        self.recentFilesView.header().setResizeMode( 0, QHeaderView.Fixed )
        return

    def __projectActivated( self, item, column ):
        " Handles the double click (or Enter) on the item "
        self.__projectContextItem = item
        self.__loadProject()
        return

    def __fileActivated( self, item, column ):
        " Handles the double click (or Enter) on a file item "
        self.__fileContextItem = item
        self.__openFile()
        return

    def __viewProperties( self ):
        " Handles the 'view properties' context menu item "
        if self.__projectContextItem is None:
            return
        if not self.__projectContextItem.isValid():
            return

        if self.__projectContextItem.isCurrent():
            # This is the current project - it can be edited
            project = GlobalData().project
            dialog = ProjectPropertiesDialog( project )
            if dialog.exec_() == QDialog.Accepted:
                importDirs = []
                for index in xrange( dialog.importDirList.count() ):
                    importDirs.append( str( dialog.importDirList.item( \
                                                            index ).text() ) )

                scriptName = str( dialog.scriptEdit.text() ).strip()
                relativePath = relpath( scriptName, project.getProjectDir() )
                if not relativePath.startswith( '..' ):
                    scriptName = relativePath

                project.updateProperties( \
                    scriptName, importDirs,
                    str( dialog.creationDateEdit.text() ).strip(),
                    str( dialog.authorEdit.text() ).strip(),
                    str( dialog.licenseEdit.text() ).strip(),
                    str( dialog.copyrightEdit.text() ).strip(),
                    str( dialog.versionEdit.text() ).strip(),
                    str( dialog.emailEdit.text() ).strip(),
                    str( dialog.descriptionEdit.toPlainText() ).strip() )
        else:
            # This is not the current project - it can be viewed
            fName = self.__projectContextItem.getFilename()
            dialog = ProjectPropertiesDialog( fName )
            dialog.exec_()
        return

    def __deleteProject( self ):
        " Handles the 'delete from recent' context menu item "
        if self.__projectContextItem is None:
            return

        # Removal from the visible list is done via a signal which comes back
        # from settings
        fName = self.__projectContextItem.getFilename()
        Settings().deleteRecentProject( fName )
        return

    def __loadProject( self ):
        " handles 'Load' context menu item "
        if self.__projectContextItem is None:
            return
        if not self.__projectContextItem.isValid():
            return
        if self.__debugMode:
            return

        projectFileName = self.__projectContextItem.getFilename()

        if self.__projectContextItem.isCurrent():
            GlobalData().mainWindow.openFile( projectFileName, -1 )
            return  # This is the current project, open for text editing

        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        if os.path.exists( projectFileName ):
            mainWin = GlobalData().mainWindow
            editorsManager = mainWin.editorsManagerWidget.editorsManager
            if editorsManager.closeRequest():
                prj = GlobalData().project
                prj.setTabsStatus( editorsManager.getTabsStatus() )
                editorsManager.closeAll()
                prj.loadProject( projectFileName )
        else:
            logging.error( "The project " + \
                           os.path.basename( projectFileName ) + \
                           " disappeared from the file system." )
            self.__populateProjects()
        QApplication.restoreOverrideCursor()
        return

    def __populateProjects( self ):
        " Populates the recent projects "
        self.projectsView.clear()
        for item in Settings().recentProjects:
            self.projectsView.addTopLevelItem( RecentProjectViewItem( item ) )

        self.__sortProjects()
        self.__resizeProjectColumns()
        self.__updateProjectToolbarButtons()
        return

    def __populateFiles( self ):
        " Populates the recent files "
        self.recentFilesView.clear()
        for path in GlobalData().project.recentFiles:
            self.recentFilesView.addTopLevelItem( RecentFileViewItem( path ) )

        self.__sortFiles()
        self.__resizeFileColumns()
        self.__updateFileToolbarButtons()
        return

    def __projectChanged( self, what ):
        " Triggered when the current project is changed "
        if what == CodimensionProject.CompleteProject:
            self.__populateProjects()
            self.__populateFiles()
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

    def __openFile( self ):
        " Handles 'open' file menu item "
        self.__fileContextItem.updateIconAndTooltip()
        fName = self.__fileContextItem.getFilename()

        if not self.__fileContextItem.isValid():
            logging.warning( "Cannot open " + fName )
            return

        fileType = detectFileType( fName )

        if fileType == CodimensionProjectFileType:
            if fName == GlobalData().project.fileName:
                # This is the current project, open for text editing
                GlobalData().mainWindow.openFile( fName, -1 )
                return
            if self.__debugMode:
                logging.error( "Cannot change project while in debug mode. " \
                               "Finish debugging first." )
                return
            # Load the project, it is another one
            QApplication.processEvents()
            QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
            if os.path.exists( fName ):
                mainWin = GlobalData().mainWindow
                editorsManager = mainWin.editorsManagerWidget.editorsManager
                if editorsManager.closeRequest():
                    prj = GlobalData().project
                    prj.setTabsStatus( editorsManager.getTabsStatus() )
                    editorsManager.closeAll()
                    prj.loadProject( fName )
            else:
                logging.error( "The project " + \
                               os.path.basename( fName ) + \
                               " disappeared from the file system." )
                self.__populateProjects()
            QApplication.restoreOverrideCursor()
            return

        if fileType == PixmapFileType:
            GlobalData().mainWindow.openPixmapFile( fName )
            return

        GlobalData().mainWindow.openFile( fName, -1 )
        return

    def __deleteFile( self ):
        " Handles 'delete from recent' file menu item "
        fName = self.__fileContextItem.getFilename()
        GlobalData().project.removeRecentFile( fName )
        index = 0
        while True:
            candidate = self.recentFilesView.topLevelItem( index )
            if self.__fileContextItem == candidate:
                self.recentFilesView.takeTopLevelItem( index )
                return
            index += 1
        return

    def __handleShowFileContextMenu( self, coord ):
        " File context menu "
        self.__fileContextItem = self.recentFilesView.itemAt( coord )
        if self.__fileContextItem is not None:
            self.__fileMenu.popup( QCursor.pos() )
        return

    def __filePathToClipboard( self ):
        " Copies the file item path to the clipboard "
        if self.__fileContextItem is not None:
            QApplication.clipboard().setText( \
                    self.__fileContextItem.getFilename() )
        return

    def __prjPathToClipboard( self ):
        " Copies the project item path to the clipboard "
        if self.__projectContextItem is not None:
            QApplication.clipboard().setText( \
                    self.__projectContextItem.getFilename() )
        return

    def onFileUpdated( self, fileName, uuid ):
        " Triggered when the file is updated: python or project "
        realPath = os.path.realpath( fileName )

        count = self.recentFilesView.topLevelItemCount()
        for index in xrange( 0, count ):
            item = self.recentFilesView.topLevelItem( index )

            itemRealPath = os.path.realpath( item.getFilename() )
            if realPath == itemRealPath:
                item.updateIconAndTooltip()
                break

        for index in xrange( 0, self.projectsView.topLevelItemCount() ):
            item = self.projectsView.topLevelItem( index )

            itemRealPath = os.path.realpath( item.getFilename() )
            if realPath == itemRealPath:
                item.updateTooltip()
                break
        return

    def __onShowHide( self ):
        " Triggered when show/hide button is clicked "
        if self.projectsView.isVisible():
            self.projectsView.setVisible( False )
            self.lowerToolbar.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show recent projects list" )

            self.__minH = self.lower.minimumHeight()
            self.__maxH = self.lower.maximumHeight()

            self.lower.setMinimumHeight( self.headerFrame.height() )
            self.lower.setMaximumHeight( self.headerFrame.height() )
        else:
            self.projectsView.setVisible( True )
            self.lowerToolbar.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide recent projects list" )

            self.lower.setMinimumHeight( self.__minH )
            self.lower.setMaximumHeight( self.__maxH )
        return

    def __onDebugMode( self, newState ):
        " Triggered when debug mode has changed "
        self.__debugMode = newState

        # Disable the load project button
        self.__updateProjectToolbarButtons()
        return

