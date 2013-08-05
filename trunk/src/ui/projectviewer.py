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

""" project viewer implementation """


import os, os.path, logging, shutil
from PyQt4.QtCore       import SIGNAL, QSize, Qt
from PyQt4.QtGui        import QWidget, QVBoxLayout, \
                               QSplitter, QToolBar, QAction, \
                               QToolButton, QHBoxLayout, \
                               QLabel, QSpacerItem, QSizePolicy, QDialog, \
                               QMenu, QCursor, QFrame, QApplication, \
                               QMessageBox, QPalette
from utils.pixmapcache  import PixmapCache
from utils.globals      import GlobalData
from utils.settings     import Settings
from projectproperties  import ProjectPropertiesDialog
from utils.project      import CodimensionProject
from filesystembrowser  import FileSystemBrowser
from projectbrowser     import ProjectBrowser
from viewitems          import NoItemType, DirectoryItemType, SysPathItemType, \
                               FileItemType, GlobalsItemType, \
                               ImportsItemType, FunctionsItemType, \
                               ClassesItemType, StaticAttributesItemType, \
                               InstanceAttributesItemType, \
                               CodingItemType, ImportItemType, \
                               FunctionItemType, ClassItemType, \
                               DecoratorItemType, AttributeItemType, \
                               GlobalItemType, ImportWhatItemType
from utils.fileutils    import BrokenSymlinkFileType, PythonFileType, \
                               Python3FileType, detectFileType
from pylintviewer       import PylintViewer
from pymetricsviewer    import PymetricsViewer
from newnesteddir       import NewProjectDirDialog
from diagram.importsdgm import ImportsDiagramDialog, \
                               ImportDiagramOptions, \
                               ImportsDiagramProgress
from utils.compatibility import relpath


class ProjectViewer( QWidget ):
    " project viewer widget "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__fsContextItem = None
        self.__prjContextItem = None

        self.upper = self.__createProjectPartLayout()
        self.lower = self.__createFilesystemPartLayout()
        self.__createFilesystemPopupMenu()
        self.__createProjectPopupMenu()

        layout = QVBoxLayout()
        layout.setContentsMargins( 1, 1, 1, 1 )
        splitter = QSplitter( Qt.Vertical )
        splitter.addWidget( self.upper )
        splitter.addWidget( self.lower )
        splitter.setCollapsible( 0, False )
        splitter.setCollapsible( 1, False )

        layout.addWidget( splitter )
        self.setLayout( layout )

        self.__updateFSToolbarButtons()
        self.__updatePrjToolbarButtons()

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( GlobalData().project, SIGNAL( 'restoreProjectExpandedDirs' ),
                      self.__onRestorePrjExpandedDirs )

        # Support switching to debug and back
        self.connect( parent, SIGNAL( 'debugModeChanged' ),
                      self.projectTreeView.onDebugMode )
        self.connect( parent, SIGNAL( 'debugModeChanged' ),
                      self.filesystemView.onDebugMode )

        # At the beginning the FS viewer is shown, so hide it if needed
        if Settings().showFSViewer == False:
            self.__onShowHide( True )
        return

    def setTooltips( self, switchOn ):
        " Triggers the tooltips mode "
        self.projectTreeView.model().sourceModel().setTooltips( switchOn )
        self.filesystemView.model().sourceModel().setTooltips( switchOn )
        return

    def __createProjectPartLayout( self ):
        """ Creates the upper part of the project viewer """

        self.projectTreeView = ProjectBrowser()

        # Header part: label + i-button
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

        self.projectLabel = QLabel()
        self.projectLabel.setText( "Project: none" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )

        self.propertiesButton = QToolButton()
        self.propertiesButton.setAutoRaise( True )
        self.propertiesButton.setIcon( PixmapCache().getIcon( 'smalli.png' ) )
        self.propertiesButton.setFixedSize( 20, 20 )
        self.propertiesButton.setToolTip( "Project properties" )
        self.propertiesButton.setEnabled( False )
        self.propertiesButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.propertiesButton, SIGNAL( "clicked()" ),
                      self.projectProperties )

        self.unloadButton = QToolButton()
        self.unloadButton.setAutoRaise( True )
        self.unloadButton.setIcon( \
                PixmapCache().getIcon( 'unloadproject.png' ) )
        self.unloadButton.setFixedSize( 20, 20 )
        self.unloadButton.setToolTip( "Unload project" )
        self.unloadButton.setEnabled( False )
        self.unloadButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.unloadButton, SIGNAL( "clicked()" ),
                      self.unloadProject )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.addWidget( self.unloadButton )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.projectLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.propertiesButton )
        headerFrame.setLayout( headerLayout )

        # Toolbar part - buttons
        self.prjFindWhereUsedButton = QAction( \
                PixmapCache().getIcon( 'findusage.png' ),
                'Find where the highlighted item is used', self )
        self.connect( self.prjFindWhereUsedButton, SIGNAL( "triggered()" ),
                      self.__findWhereUsed )
        self.prjFindInDirButton = QAction( \
                PixmapCache().getIcon( 'findindir.png' ),
                'Find in highlighted directory', self )
        self.connect( self.prjFindInDirButton, SIGNAL( "triggered()" ),
                      self.projectTreeView.findInDirectory )
        self.prjShowParsingErrorsButton = QAction( \
                PixmapCache().getIcon( 'showparsingerrors.png' ),
                'Show lexer/parser errors', self )
        self.connect( self.prjShowParsingErrorsButton, SIGNAL( "triggered()" ),
                      self.showPrjParserError )
        self.prjNewDirButton = QAction( \
                PixmapCache().getIcon( 'newdir.png' ),
                'Create sub directory', self )
        self.connect( self.prjNewDirButton, SIGNAL( "triggered()" ),
                      self.__createDir )
        self.prjCopyToClipboardButton = QAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self )
        self.connect( self.prjCopyToClipboardButton, SIGNAL( "triggered()" ),
                      self.projectTreeView.copyToClipboard )
        self.prjPylintButton = QAction( \
                PixmapCache().getIcon( 'pylint.png' ),
                'Run pylint for the selected item', self )
        self.connect( self.prjPylintButton, SIGNAL( "triggered()" ),
                      self.__pylintRequest )
        self.prjPymetricsButton = QAction( \
                PixmapCache().getIcon( 'metrics.png' ),
                'Run pymetrics for the selected item', self )
        self.connect( self.prjPymetricsButton, SIGNAL( 'triggered()' ),
                      self.__pymetricsRequest )

        self.upperToolbar = QToolBar()
        self.upperToolbar.setMovable( False )
        self.upperToolbar.setAllowedAreas( Qt.TopToolBarArea )
        self.upperToolbar.setIconSize( QSize( 16, 16 ) )
        self.upperToolbar.setFixedHeight( 28 )
        self.upperToolbar.setContentsMargins( 0, 0, 0, 0 )
        self.upperToolbar.addAction( self.prjFindWhereUsedButton )
        self.upperToolbar.addAction( self.prjFindInDirButton )
        self.upperToolbar.addAction( self.prjShowParsingErrorsButton )
        self.upperToolbar.addAction( self.prjNewDirButton )
        self.upperToolbar.addAction( self.prjCopyToClipboardButton )
        self.upperToolbar.addAction( self.prjPylintButton )
        self.upperToolbar.addAction( self.prjPymetricsButton )

        self.connect( self.projectTreeView,
                      SIGNAL( 'firstSelectedItem' ),
                      self.__prjSelectionChanged )

        self.projectTreeView.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.projectTreeView,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__prjContextMenuRequested )
        pLayout = QVBoxLayout()
        pLayout.setContentsMargins( 0, 0, 0, 0 )
        pLayout.setSpacing( 0 )
        pLayout.addWidget( headerFrame )
        pLayout.addWidget( self.upperToolbar )
        pLayout.addWidget( self.projectTreeView )

        upperContainer = QWidget()
        upperContainer.setContentsMargins( 0, 0, 0, 0 )
        upperContainer.setLayout( pLayout )
        return upperContainer

    def getProjectToolbar( self ):
        " Provides a reference to the project toolbar "
        return self.upperToolbar

    def __createProjectPopupMenu( self ):
        " Generates the various popup menus for the project browser "

        # popup menu for python files content
        self.prjPythonMenu = QMenu( self )
        self.prjUsageAct = self.prjPythonMenu.addAction( \
            PixmapCache().getIcon( 'findusage.png' ),
            'Find occurences', self.__findWhereUsed )
        self.prjPythonMenu.addSeparator()
        self.__disasmMenuItem = self.prjPythonMenu.addAction( \
            PixmapCache().getIcon( 'disasmmenu.png' ),
            'Disassemble', self.__onPrjDisassemble )
        self.prjPythonMenu.addSeparator()
        self.prjCopyAct = self.prjPythonMenu.addAction( \
            PixmapCache().getIcon( 'copytoclipboard.png' ),
            'Copy path to clipboard', self.projectTreeView.copyToClipboard )

        # popup menu for directories
        self.prjDirMenu = QMenu( self )
        self.prjDirPylintAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'pylint.png' ),
                'Run pylint for the directory recursively',
                self.__pylintRequest )
        self.prjDirPymetricsAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'metrics.png' ),
                'Run pymetrics for the directory recursively',
                self.__pymetricsRequest )
        self.prjDirMenu.addSeparator()
        self.prjDirImportDgmAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'importsdiagram.png' ),
                "Imports diagram", self.__onImportDiagram )
        self.prjDirImportDgmTunedAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Fine tuned imports diagram', self.__onImportDgmTuned )
        self.prjDirMenu.addSeparator()
        self.prjDirNewDirAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'newdir.png' ),
                'Create nested directory', self.__createDir )
        self.prjDirMenu.addSeparator()
        self.prjDirFindAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'findindir.png' ),
                'Find in this directory', self.projectTreeView.findInDirectory )
        self.prjDirCopyPathAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self.projectTreeView.copyToClipboard )
        self.prjDirMenu.addSeparator()
        self.prjDirRemoveFromDiskAct = self.prjDirMenu.addAction( \
                PixmapCache().getIcon( 'trash.png' ),
                'Remove directory from the disk recursively',
                self.__removePrj )

        # popup menu for files
        self.prjFileMenu = QMenu( self )
        self.prjFilePylintAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'pylint.png' ),
                'Run pylint for the file', self.__pylintRequest )
        self.prjFilePymetricsAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'metrics.png' ),
                'Run pymetrics for the file', self.__pymetricsRequest )
        self.prjFileMenu.addSeparator()
        self.prjFileImportDgmAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'importsdiagram.png' ),
                "Imports diagram", self.__onImportDiagram )
        self.prjFileImportDgmTunedAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Fine tuned imports diagram', self.__onImportDgmTuned )
        self.prjFileMenu.addSeparator()
        self.prjFileCopyPathAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self.projectTreeView.copyToClipboard )
        self.prjFileShowErrorsAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'showparsingerrors.png' ),
                'Show lexer/parser errors', self.showPrjParserError )
        self.prjFileMenu.addSeparator()
        self.prjFileRemoveFromDiskAct = self.prjFileMenu.addAction( \
                PixmapCache().getIcon( 'trash.png' ),
                'Remove file from the disk',
                self.__removePrj )

        # Popup menu for broken symlinks
        self.prjBrokenLinkMenu = QMenu( self )
        self.prjBrokenLinkMenu.addAction( \
                PixmapCache().getIcon( 'trash.png' ),
                'Remove broken link from the disk', self.__removePrj )

        return

    def __createFilesystemPartLayout( self ):
        " Creates the lower part of the project viewer "

        # Header part: label + show/hide button
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

        projectLabel = QLabel()
        projectLabel.setText( "File system" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise( True )
        self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideButton.setFixedSize( 20, 20 )
        self.__showHideButton.setToolTip( "Hide file system tree" )
        self.__showHideButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__showHideButton, SIGNAL( 'clicked()' ),
                      self.__onShowHide )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 3, 0, 0, 0 )
        headerLayout.addWidget( projectLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__showHideButton )
        self.headerFrame.setLayout( headerLayout )

        # Tree view part
        self.filesystemView = FileSystemBrowser()
        self.connect( self.filesystemView,
                      SIGNAL( 'firstSelectedItem' ),
                      self.__fsSelectionChanged )
        self.filesystemView.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.filesystemView,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__fsContextMenuRequested )

        # Toolbar part - buttons
        self.fsFindInDirButton = QAction( \
                PixmapCache().getIcon( 'findindir.png' ),
                'Find in highlighted directory', self )
        self.connect( self.fsFindInDirButton, SIGNAL( "triggered()" ),
                      self.filesystemView.findInDirectory )
        self.fsAddTopLevelDirButton = QAction( \
                PixmapCache().getIcon( 'addtopleveldir.png' ),
                'Add as a top level directory', self )
        self.connect( self.fsAddTopLevelDirButton, SIGNAL( "triggered()" ),
                      self.addToplevelDir )
        self.fsRemoveTopLevelDirButton = QAction( \
                PixmapCache().getIcon( 'removetopleveldir.png' ),
                'Remove from the top level directories', self )
        self.connect( self.fsRemoveTopLevelDirButton, SIGNAL( "triggered()" ),
                      self.removeToplevelDir )
        self.fsShowParsingErrorsButton = QAction( \
                PixmapCache().getIcon( 'showparsingerrors.png' ),
                'Show lexer/parser errors', self )
        self.connect( self.fsShowParsingErrorsButton, SIGNAL( "triggered()" ),
                      self.showFsParserError )
        self.fsCopyToClipboardButton = QAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self )
        self.connect( self.fsCopyToClipboardButton, SIGNAL( "triggered()" ),
                      self.filesystemView.copyToClipboard )
        fsReloadButton = QAction( PixmapCache().getIcon( 'reload.png' ),
                                  'Re-read the file system tree', self )
        self.connect( fsReloadButton, SIGNAL( "triggered()" ),
                      self.filesystemView.reload )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.lowerToolbar = QToolBar()
        self.lowerToolbar.setMovable( False )
        self.lowerToolbar.setAllowedAreas( Qt.TopToolBarArea )
        self.lowerToolbar.setIconSize( QSize( 16, 16 ) )
        self.lowerToolbar.setFixedHeight( 28 )
        self.lowerToolbar.setContentsMargins( 0, 0, 0, 0 )
        self.lowerToolbar.addAction( self.fsFindInDirButton )
        self.lowerToolbar.addAction( self.fsAddTopLevelDirButton )
        self.lowerToolbar.addAction( self.fsRemoveTopLevelDirButton )
        self.lowerToolbar.addAction( self.fsCopyToClipboardButton )
        self.lowerToolbar.addAction( self.fsShowParsingErrorsButton )
        self.lowerToolbar.addWidget( spacer )
        self.lowerToolbar.addAction( fsReloadButton )


        fsLayout = QVBoxLayout()
        fsLayout.setContentsMargins( 0, 0, 0, 0 )
        fsLayout.setSpacing( 0 )
        fsLayout.addWidget( self.headerFrame )
        fsLayout.addWidget( self.lowerToolbar )
        fsLayout.addWidget( self.filesystemView )

        lowerContainer = QWidget()
        lowerContainer.setContentsMargins( 0, 0, 0, 0 )
        lowerContainer.setLayout( fsLayout )
        return lowerContainer

    def getFileSystemToolbar( self ):
        " Provides a reference to the file system part toolbar "
        return self.lowerToolbar

    def __createFilesystemPopupMenu( self ):
        " Generates the various popup menus for the FS browser "

        # create the popup menu for files
        self.fsFileMenu = QMenu( self )
        self.fsFileCopyPathAct = self.fsFileMenu.addAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self.filesystemView.copyToClipboard )
        self.fsFileShowErrorsAct = self.fsFileMenu.addAction( \
                PixmapCache().getIcon( 'showparsingerrors.png' ),
                'Show lexer/parser errors', self.showFsParserError )
        self.fsFileMenu.addSeparator()
        self.fsFileRemoveAct = self.fsFileMenu.addAction( \
                PixmapCache().getIcon( 'trash.png' ),
                'Remove file from the disk', self.__removeFs )

        # create the directory menu
        self.fsDirMenu = QMenu( self )
        self.fsDirAddAsTopLevelAct = self.fsDirMenu.addAction( \
                PixmapCache().getIcon( 'addtopleveldir.png' ),
                'Add as top level directory',
                self.addToplevelDir )
        self.fsDirRemoveFromToplevelAct = self.fsDirMenu.addAction( \
                PixmapCache().getIcon( 'removetopleveldir.png' ),
                'Remove from top level', self.removeToplevelDir )
        self.fsDirMenu.addSeparator()
        self.fsDirFindAct = self.fsDirMenu.addAction( \
                PixmapCache().getIcon( 'findindir.png' ),
                'Find in this directory', self.filesystemView.findInDirectory )
        self.fsDirCopyPathAct = self.fsDirMenu.addAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self.filesystemView.copyToClipboard )
        self.fsDirMenu.addSeparator()
        self.fsDirRemoveAct = self.fsDirMenu.addAction( \
                PixmapCache().getIcon( 'trash.png' ),
                'Remove directory from the disk recursively', self.__removeFs )

        # create menu for broken symlink
        self.fsBrokenLinkMenu = QMenu( self )
        self.fsBrokenLinkMenu.addAction( \
                PixmapCache().getIcon( 'trash.png' ),
                'Remove broken link from the disk', self.__removeFs )

        # popup menu for python files content
        self.fsPythonMenu = QMenu( self )
        self.fsUsageAct = self.fsPythonMenu.addAction( \
            PixmapCache().getIcon( 'findusage.png' ),
            'Find occurences', self.__fsFindWhereUsed )
        self.fsPythonMenu.addSeparator()
        self.fsDisasmMenuItem = self.fsPythonMenu.addAction( \
            PixmapCache().getIcon( 'disasmmenu.png' ),
            'Disassemble', self.__onFSDisassemble )
        self.fsPythonMenu.addSeparator()
        self.fsCopyAct = self.fsPythonMenu.addAction( \
            PixmapCache().getIcon( 'copytoclipboard.png' ),
            'Copy path to clipboard', self.filesystemView.copyToClipboard )
        return

    @staticmethod
    def unloadProject():
        " Unloads the project "
        # Check first if the project can be unloaded
        globalData = GlobalData()
        mainWindow = globalData.mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        if editorsManager.closeRequest():
            globalData.project.setTabsStatus( editorsManager.getTabsStatus() )
            editorsManager.closeAll()
            globalData.project.fileBrowserPaths = mainWindow.getProjectExpandedPaths()
            globalData.project.unloadProject()
        return

    def __onRestorePrjExpandedDirs( self ):
        " Triggered when a project tree should restore its previous state "
        for path in GlobalData().project.fileBrowserPaths:
            self.projectTreeView.highlightItem( path )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a signal comes "

        if what != CodimensionProject.CompleteProject:
            return

        if GlobalData().project.isLoaded():
            self.projectLabel.setText( 'Project: ' +
                             os.path.basename(
                                GlobalData().project.fileName )[ : -4 ] )
            self.propertiesButton.setEnabled( True )
            self.unloadButton.setEnabled( True )
        else:
            self.projectLabel.setText( 'Project: none' )
            self.propertiesButton.setEnabled( False )
            self.unloadButton.setEnabled( False )
        self.filesystemView.layoutDisplay()
        self.projectTreeView.layoutDisplay()

        self.__fsContextItem = None
        self.__prjContextItem = None

        self.__updateFSToolbarButtons()
        self.__updatePrjToolbarButtons()
        return

    def projectProperties( self ):
        " Triggered when the project properties button is clicked "

        project = GlobalData().project
        dialog = ProjectPropertiesDialog( project )
        if dialog.exec_() == QDialog.Accepted:
            importDirs = []
            for index in xrange( dialog.importDirList.count() ):
                importDirs.append( str( dialog.importDirList.item( \
                                                        index ).text() ) )

            scriptName = str( dialog.scriptEdit.text() ).strip()
            if scriptName != "":
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

            self.emit( SIGNAL( "fileUpdated" ), project.fileName, None )
            self.onFileUpdated( project.fileName, None )
        return

    def __fsSelectionChanged( self, index ):
        " Handles the changed selection in the FS browser "
        if index is None:
            self.__fsContextItem = None
        else:
            self.__fsContextItem = self.filesystemView.model().item( index )
        self.__updateFSToolbarButtons()
        return

    def __prjSelectionChanged( self, index ):
        " Handles the changed selection in the project browser "
        if index is None:
            self.__prjContextItem = None
        else:
            self.__prjContextItem = self.projectTreeView.model().item( index )
        self.__updatePrjToolbarButtons()
        return

    def __updateFSToolbarButtons( self ):
        " Updates the toolbar buttons depending on the __fsContextItem "

        self.fsFindInDirButton.setEnabled( False )
        self.fsAddTopLevelDirButton.setEnabled( False )
        self.fsRemoveTopLevelDirButton.setEnabled( False )
        self.fsShowParsingErrorsButton.setEnabled( False )
        self.fsCopyToClipboardButton.setEnabled( False )

        if self.__fsContextItem is None:
            return

        if self.__fsContextItem.itemType not in \
                    [ NoItemType, SysPathItemType, GlobalsItemType,
                      ImportsItemType, FunctionsItemType,
                      ClassesItemType, StaticAttributesItemType,
                      InstanceAttributesItemType ]:
            self.fsCopyToClipboardButton.setEnabled( True )

        if self.__fsContextItem.itemType == DirectoryItemType:
            self.fsFindInDirButton.setEnabled( True )
            globalData = GlobalData()
            if globalData.project.fileName != "":
                if globalData.project.isTopLevelDir( \
                        self.__fsContextItem.getPath() ):
                    if self.__fsContextItem.parentItem.itemType == NoItemType:
                        self.fsRemoveTopLevelDirButton.setEnabled( True )
                else:
                    if self.__fsContextItem.parentItem.itemType != NoItemType:
                        self.fsAddTopLevelDirButton.setEnabled( True )

        if self.__fsContextItem.itemType == FileItemType:
            if self.__fsContextItem.fileType in [ PythonFileType,
                                                  Python3FileType ] and \
               self.__fsContextItem.fileType != BrokenSymlinkFileType:
                self.fsShowParsingErrorsButton.setEnabled( \
                                self.__fsContextItem.parsingErrors )
        return

    def __updatePrjToolbarButtons( self ):
        " Updates the toolbar buttons depending on the __prjContextItem "

        self.prjFindWhereUsedButton.setEnabled( False )
        self.prjFindInDirButton.setEnabled( False )
        self.prjShowParsingErrorsButton.setEnabled( False )
        self.prjNewDirButton.setEnabled( False )
        self.prjCopyToClipboardButton.setEnabled( False )
#        self.prjDelProjectDirButton.setEnabled( False )
        self.prjPylintButton.setEnabled( False )
        self.prjPymetricsButton.setEnabled( False )

        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType not in \
                    [ NoItemType, SysPathItemType, GlobalsItemType,
                      ImportsItemType, FunctionsItemType,
                      ClassesItemType, StaticAttributesItemType,
                      InstanceAttributesItemType ]:
            self.prjCopyToClipboardButton.setEnabled( True )

        if self.__prjContextItem.itemType == DirectoryItemType:
            self.prjFindInDirButton.setEnabled( True )
            self.prjNewDirButton.setEnabled( True )
            self.prjPylintButton.setEnabled( GlobalData().pylintAvailable )
            self.prjPymetricsButton.setEnabled( True )

            # if it is a top level and not the project file containing dir then
            # the del butten should be enabled
            if self.__prjContextItem.parentItem.itemType == NoItemType:
                projectDir = os.path.dirname(GlobalData().project.fileName) + \
                             os.path.sep

        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.fileType in [ PythonFileType,
                                                   Python3FileType ]:
                self.prjPylintButton.setEnabled( GlobalData().pylintAvailable )
                self.prjPymetricsButton.setEnabled( True )
                self.prjShowParsingErrorsButton.setEnabled( \
                                self.__prjContextItem.parsingErrors )

        if self.__prjContextItem.itemType in [ FunctionItemType, ClassItemType,
                                               AttributeItemType,
                                               GlobalItemType ]:
            self.prjFindWhereUsedButton.setEnabled( True )

        return

    def __fsContextMenuRequested( self, coord ):
        " Triggers when the filesystem menu is requested "

        index = self.filesystemView.indexAt( coord )
        if not index.isValid():
            return

        # This will update the __fsContextItem
        self.__fsSelectionChanged( index )
        if self.__fsContextItem is None:
            return

        if self.__fsContextItem.itemType in [ NoItemType, SysPathItemType,
                                              GlobalsItemType, ImportsItemType,
                                              FunctionsItemType,
                                              ClassesItemType,
                                              StaticAttributesItemType,
                                              InstanceAttributesItemType ]:
            return
        if self.__fsContextItem.itemType == FileItemType:
            if self.__fsContextItem.fileType == BrokenSymlinkFileType:
                self.fsBrokenLinkMenu.popup( QCursor.pos() )
                return

        # Update the menu items status
        self.fsFileCopyPathAct.setEnabled( \
                self.fsCopyToClipboardButton.isEnabled() )
        self.fsCopyAct.setEnabled( \
                self.fsCopyToClipboardButton.isEnabled() )
        self.fsFileShowErrorsAct.setEnabled( \
                self.fsShowParsingErrorsButton.isEnabled() )

        self.fsDirAddAsTopLevelAct.setEnabled( \
                self.fsAddTopLevelDirButton.isEnabled() )
        self.fsDirRemoveFromToplevelAct.setEnabled( \
                self.fsRemoveTopLevelDirButton.isEnabled() )
        self.fsDirFindAct.setEnabled( \
                self.fsFindInDirButton.isEnabled() )
        self.fsDirCopyPathAct.setEnabled( \
                self.fsCopyToClipboardButton.isEnabled() )

        canDisassemble = self.__fsContextItem.canGetDisassembler()
        self.fsDisasmMenuItem.setEnabled( canDisassemble )

        # Add more conditions
        self.fsUsageAct.setEnabled( \
                self.__fsContextItem.itemType in [ FunctionItemType,
                                                   ClassItemType,
                                                   AttributeItemType,
                                                   GlobalItemType ] and \
                GlobalData().project.isProjectFile( \
                        self.__fsContextItem.getPath() ) )

        if self.__fsContextItem.itemType == FileItemType:
            if self.__fsContextItem.isLink:
                self.fsFileRemoveAct.setText( "Remove link from the disk" )
            else:
                self.fsFileRemoveAct.setText( "Remove file from the disk" )
            self.fsFileRemoveAct.setEnabled( \
                    self.__canDeleteFile( self.__fsContextItem.getPath() ) )
            self.fsFileMenu.popup( QCursor.pos() )
        elif self.__fsContextItem.itemType == DirectoryItemType:
            if self.__fsContextItem.isLink:
                self.fsDirRemoveAct.setText( "Remove link from the disk" )
            else:
                self.fsDirRemoveAct.setText( "Remove directory from " \
                                             "the disk recursively" )
            self.fsDirRemoveAct.setEnabled( \
                    self.__canDeleteDir( self.__fsContextItem.getPath() ) )
            self.fsDirMenu.popup( QCursor.pos() )
        elif self.__fsContextItem.itemType in [ CodingItemType, ImportItemType,
                                                FunctionItemType,
                                                ClassItemType,
                                                DecoratorItemType,
                                                AttributeItemType,
                                                GlobalItemType,
                                                ImportWhatItemType ]:
            self.fsPythonMenu.popup( QCursor.pos() )
        return

    def __prjContextMenuRequested( self, coord ):
        " Triggered before the project context menu is shown "

        index = self.projectTreeView.indexAt( coord )
        if not index.isValid():
            return

        # This will update the __prjContextItem
        self.__prjSelectionChanged( index )
        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType in [ NoItemType, SysPathItemType,
                                               GlobalsItemType, ImportsItemType,
                                               FunctionsItemType,
                                               ClassesItemType,
                                               StaticAttributesItemType,
                                               InstanceAttributesItemType ]:
            return
        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.fileType == BrokenSymlinkFileType:
                self.prjBrokenLinkMenu.popup( QCursor.pos() )
                return

        # Update the menu items status
        self.prjUsageAct.setEnabled( \
                self.prjFindWhereUsedButton.isEnabled() )
        self.prjCopyAct.setEnabled( \
                self.prjCopyToClipboardButton.isEnabled() )
        self.prjDirNewDirAct.setEnabled( \
                self.prjNewDirButton.isEnabled() )
        self.prjDirFindAct.setEnabled( \
                self.prjFindInDirButton.isEnabled() )
        self.prjDirCopyPathAct.setEnabled( \
                self.prjCopyToClipboardButton.isEnabled() )
        self.prjFileCopyPathAct.setEnabled( \
                self.prjCopyToClipboardButton.isEnabled() )
        self.prjFileShowErrorsAct.setEnabled( \
                self.prjShowParsingErrorsButton.isEnabled() )
        self.prjDirPylintAct.setEnabled( \
                self.prjPylintButton.isEnabled() )
        self.prjFilePylintAct.setEnabled( \
                self.prjPylintButton.isEnabled() )
        self.prjDirPymetricsAct.setEnabled( \
                self.prjPymetricsButton.isEnabled() )
        self.prjFilePymetricsAct.setEnabled( \
                self.prjPymetricsButton.isEnabled() )

        canDisassemble = self.__prjContextItem.canGetDisassembler()
        self.__disasmMenuItem.setEnabled( canDisassemble )

        # Imports diagram menu
        enabled = False
        if self.__prjContextItem.itemType == DirectoryItemType:
            enabled = True
        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.fileType in [ PythonFileType,
                                                   Python3FileType ]:
                enabled = True
        if not GlobalData().graphvizAvailable:
            enabled = False
        self.prjFileImportDgmAct.setEnabled( enabled )
        self.prjFileImportDgmTunedAct.setEnabled( enabled )
        self.prjDirImportDgmAct.setEnabled( enabled )
        self.prjDirImportDgmTunedAct.setEnabled( enabled )

        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.isLink:
                self.prjFileRemoveFromDiskAct.setText( \
                                            "Remove link from the disk" )
            else:
                self.prjFileRemoveFromDiskAct.setText( \
                                            "Remove file from the disk" )
            self.prjFileRemoveFromDiskAct.setEnabled( \
                    self.__canDeleteFile( self.__prjContextItem.getPath() ) )
            self.prjFileMenu.popup( QCursor.pos() )
        elif self.__prjContextItem.itemType == DirectoryItemType:
            if self.__prjContextItem.isLink:
                self.prjDirRemoveFromDiskAct.setText( \
                                            "Remove link from the disk" )
            else:
                self.prjDirRemoveFromDiskAct.setText( "Remove directory from " \
                                                      "the disk recursively" )
            self.prjDirRemoveFromDiskAct.setEnabled( \
                    self.__canDeleteDir( self.__prjContextItem.getPath() ) )
            self.prjDirMenu.popup( QCursor.pos() )
        elif self.__prjContextItem.itemType in [ CodingItemType, ImportItemType,
                                                 FunctionItemType,
                                                 ClassItemType,
                                                 DecoratorItemType,
                                                 AttributeItemType,
                                                 GlobalItemType,
                                                 ImportWhatItemType ]:
            self.prjPythonMenu.popup( QCursor.pos() )
        return

    def __findWhereUsed( self ):
        " Triggers analysis where the highlighted item is used "
        if self.__prjContextItem is not None:
            GlobalData().mainWindow.findWhereUsed( \
                            self.__prjContextItem.getPath(),
                            self.__prjContextItem.sourceObj )
        return

    def __fsFindWhereUsed( self ):
        " Triggers analysis where the FS highlighted item is used "
        if self.__fsContextItem is not None:
            GlobalData().mainWindow.findWhereUsed( \
                            self.__fsContextItem.getPath(),
                            self.__fsContextItem.sourceObj )
        return

    def __onPrjDisassemble( self ):
        " Triggers disassembling the selected project item "
        if self.__prjContextItem is not None:
            self.__onDisasm( self.__prjContextItem )
        return

    def __onFSDisassemble( self ):
        " Triggers disassembling the selected FS item "
        if self.__fsContextItem is not None:
            self.__onDisasm( self.__fsContextItem )
        return

    def __onDisasm( self, item ):
        " Disassembles the required item "
        if item.itemType not in [ FunctionItemType, ClassItemType ]:
            return
        path = item.getPath()
        qualifiedName = item.getQualifiedName()
        GlobalData().mainWindow.showDisassembler( path, qualifiedName )
        return

    def __createDir( self ):
        " Triggered when a new subdir should be created "
        if self.__prjContextItem is None:
            return
        if self.__prjContextItem.itemType != DirectoryItemType:
            return

        dlg = NewProjectDirDialog( self )
        if dlg.exec_() == QDialog.Accepted:
            try:
                os.mkdir( self.__prjContextItem.getPath() + dlg.getDirName() )
            except Exception, exc:
                logging.error( str( exc ) )
        return

    def showPrjParserError( self ):
        " Triggered when parsing errors must be displayed "
        if self.__prjContextItem is None:
            return
        if self.__prjContextItem.itemType != FileItemType:
            return
        if self.__prjContextItem.fileType not in [ PythonFileType,
                                                   Python3FileType ]:
            return
        self.projectTreeView.showParsingErrors(self.__prjContextItem.getPath())
        return

    def showFsParserError( self ):
        " Triggered when parsing errors must be displayed "
        if self.__fsContextItem is None:
            return
        if self.__fsContextItem.itemType != FileItemType:
            return
        if self.__fsContextItem.fileType not in [ PythonFileType,
                                                  Python3FileType ]:
            return
        self.filesystemView.showParsingErrors( self.__fsContextItem.getPath() )
        return

    def addToplevelDir( self ):
        " Triggered for adding a new top level directory "
        self.filesystemView.addToplevelDir()
        self.__updateFSToolbarButtons()
        return

    def removeToplevelDir( self ):
        " Triggered for removing a top level directory "
        self.filesystemView.removeToplevelDir()
        self.__updateFSToolbarButtons()
        return

    def __pylintRequest( self ):
        " Triggered when pylint is called for a dir or a file "
        if self.__prjContextItem is None:
            return

        QApplication.processEvents()
        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.fileType not in [ PythonFileType,
                                                       Python3FileType ]:
                return

            # This is a file request
            fileName = self.__prjContextItem.getPath()
            GlobalData().mainWindow.showPylintReport( PylintViewer.SingleFile,
                                                      fileName, fileName,
                                                      "", fileName )
            return

        if self.__prjContextItem.itemType != DirectoryItemType:
            return

        # This a directory request
        # The pylint arguments should be detected
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        dirName = self.__prjContextItem.getPath()
        filesToProcess = self.__getPythonFilesInDir( dirName, dirName )
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()

        if len( filesToProcess ) == 0:
            logging.error( "No python files in the " + dirName + " directory" )
            return

        projectDir = GlobalData().project.getProjectDir()
        if projectDir == dirName:
            option = PylintViewer.ProjectFiles
        else:
            option = PylintViewer.DirectoryFiles

        GlobalData().mainWindow.showPylintReport( option,
                                                  filesToProcess,
                                                  dirName, "", dirName )
        return

    def __pymetricsRequest( self ):
        " Triggered when pymetrics is called for a dir or a file "
        if self.__prjContextItem is None:
            return

        QApplication.processEvents()
        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.fileType not in [ PythonFileType,
                                                       Python3FileType ]:
                return

            # This is a file request
            fileName = self.__prjContextItem.getPath()
            GlobalData().mainWindow.showPymetricsReport( \
                                        PymetricsViewer.SingleFile,
                                        fileName, fileName, "" )
            return

        if self.__prjContextItem.itemType != DirectoryItemType:
            return

        # This a directory request
        # The pymetrics arguments should be detected
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        dirName = self.__prjContextItem.getPath()
        filesToProcess = self.__getPythonFilesInDir( dirName, dirName )
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()

        if len( filesToProcess ) == 0:
            logging.error( "No python files in the " + dirName + " directory" )
            return

        projectDir = GlobalData().project.getProjectDir()
        if projectDir == dirName:
            option = PymetricsViewer.ProjectFiles
        else:
            option = PymetricsViewer.DirectoryFiles

        GlobalData().mainWindow.showPymetricsReport( option,
                                                     filesToProcess,
                                                     dirName, "" )
        return

    @staticmethod
    def __getPythonFilesInDir( coveringDir, path ):
        " Provides the list of python files in a dir respecting symlinks "
        ropeDir = os.path.sep + ".ropeproject" + os.path.sep
        files = []
        for item in os.listdir( path ):
            candidate = path + item
            if ropeDir in candidate:
                continue
            if os.path.isdir( candidate ):
                if os.path.islink( candidate ):
                    realpath = os.path.realpath( candidate )
                    if realpath.startswith( coveringDir ):
                        continue
                files += ProjectViewer.__getPythonFilesInDir( coveringDir,
                                                  candidate + os.path.sep )
            else:
                # It's a file
                if os.path.islink( candidate ):
                    realpath = os.path.realpath( candidate )
                    if realpath.startswith( coveringDir ):
                        continue
                    if detectFileType( realpath ) in [ PythonFileType,
                                                       Python3FileType ]:
                        files.append( candidate )
                else:
                    if detectFileType( candidate ) in [ PythonFileType,
                                                        Python3FileType ]:
                        files.append( candidate )
        return files

    def __removePrj( self ):
        " Remove the selected item "
        if self.__prjContextItem is not None:
            fName = self.__prjContextItem.getPath()
            if self.__removeItem( fName ):
                GlobalData().mainWindow.recentProjectsViewer.removeRecentFile(
                                                                        fName )
        return

    def __removeFs( self ):
        " Remove the selected item "
        if self.__fsContextItem is not None:
            fName = self.__fsContextItem.getPath()
            if self.__removeItem( fName ):
                # The item has really been deleted. Update the view
                dirname, basename = self.filesystemView._splitPath( fName )
                self.filesystemView._delFromTree( self.__fsContextItem,
                                                  dirname, basename )
                GlobalData().mainWindow.recentProjectsViewer.removeRecentFile(
                                                                        fName )
        return

    def __removeItem( self, path ):
        " Removes a link, a file or a directory "
        path = os.path.abspath( path )
        if os.path.islink( path ):
            header = "Deleting a link"
            text = "Are you sure you want to delete the " \
                   "symbolic link <b>" + path + "</b>?"
        elif os.path.isdir( path ):
            header = "Deleting a directory"
            text = "Are you sure you want to delete the " \
                   "directory <b>" + path + "</b> recursively?"
        else:
            header = "Deleting a file"
            text = "Are you sure you want to delete the " \
                   "file <b>" + path + "</b>?"

        res = QMessageBox.warning( self, header, text,
                                   QMessageBox.StandardButtons( \
                                        QMessageBox.Cancel | QMessageBox.Yes ),
                                   QMessageBox.Cancel )
        if res == QMessageBox.Yes:
            try:
                # Unfortunately, remote file system may fail to report that
                # something has been deleted. So let's check that the
                # requested item still exists
                if os.path.exists( path ):
                    if os.path.islink( path ):
                        os.remove( path )
                    elif os.path.isdir( path ):
                        shutil.rmtree( path )
                    else:
                        os.remove( path )
                else:
                    logging.info( "Could not find " + path +
                                  " on the disk. Ignoring and "
                                  "deleting from the browser." )
            except Exception, exc:
                logging.error( str( exc ) )
                return False
            return True
        return False

    @staticmethod
    def __canDeleteFile( path ):
        " Returns True if the file can be deleted "
        return GlobalData().project.fileName != os.path.realpath( path )

    @staticmethod
    def __canDeleteDir( path ):
        " Returns True if the dir can be deleted "
        path = os.path.realpath( path )
        if not path.endswith( os.path.sep ):
            path += os.path.sep
        return not GlobalData().project.fileName.startswith( path )

    @staticmethod
    def __areTherePythonFiles( path ):
        " Tests if a directory has at least one python file "
        for item in os.listdir( path ):
            if os.path.isdir( path + item ):
                if ProjectViewer.__areTherePythonFiles( path + item + os.path.sep ):
                    return True
                continue
            if detectFileType( item ) in [ PythonFileType,
                                           Python3FileType ]:
                return True
        return False

    def __onImportDiagram( self ):
        " Triggered when an import diagram is requested "
        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType == DirectoryItemType:
            # Check first if there are python files in it
            if not self.__areTherePythonFiles( self.__prjContextItem.getPath() ):
                logging.warning( "There are no python files in " + \
                                 self.__prjContextItem.getPath() )
                return
            projectDir = GlobalData().project.getProjectDir()
            if projectDir == self.__prjContextItem.getPath():
                what = ImportsDiagramDialog.ProjectFiles
                tooltip = "Generated for the project"
            else:
                what = ImportsDiagramDialog.DirectoryFiles
                tooltip = "Generated for directory " + \
                          self.__prjContextItem.getPath()
            self.__generateImportDiagram( what, ImportDiagramOptions(),
                                          tooltip )
        else:
            self.__generateImportDiagram( ImportsDiagramDialog.SingleFile,
                                          ImportDiagramOptions(),
                                          "Generated for file " + \
                                          self.__prjContextItem.getPath() )
        return

    def __onImportDgmTuned( self ):
        " Triggered when a tuned import diagram is requested "
        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType == DirectoryItemType:
            # Check first if there are python files in it
            if not self.__areTherePythonFiles( self.__prjContextItem.getPath() ):
                logging.warning( "There are no python files in " + \
                                 self.__prjContextItem.getPath() )
                return

        if self.__prjContextItem.itemType == DirectoryItemType:
            projectDir = GlobalData().project.getProjectDir()
            if projectDir == self.__prjContextItem.getPath():
                what = ImportsDiagramDialog.ProjectFiles
                dlg = ImportsDiagramDialog( what )
                tooltip = "Generated for the project"
            else:
                what = ImportsDiagramDialog.DirectoryFiles
                dlg = ImportsDiagramDialog( what,
                                            self.__prjContextItem.getPath() )
                tooltip = "Generated for directory " + \
                          self.__prjContextItem.getPath()
        else:
            what = ImportsDiagramDialog.SingleFile
            dlg = ImportsDiagramDialog( what,
                                        self.__prjContextItem.getPath() )
            tooltip = "Generated for file " + self.__prjContextItem.getPath()

        if dlg.exec_() == QDialog.Accepted:
            self.__generateImportDiagram( what, dlg.options, tooltip )
        return

    def __generateImportDiagram( self, what, options, tooltip ):
        " Show the generation progress and display the diagram "
        progressDlg = ImportsDiagramProgress( what, options,
                                              self.__prjContextItem.getPath() )
        if progressDlg.exec_() == QDialog.Accepted:
            GlobalData().mainWindow.openDiagram( progressDlg.scene,
                                                 tooltip  )
        return

    def onFileUpdated( self, fileName, uuid ):
        " Triggered when the file is updated "
        self.projectTreeView.onFileUpdated( fileName, uuid )
        self.__updatePrjToolbarButtons()
        self.filesystemView.onFileUpdated( fileName, uuid )
        self.__updateFSToolbarButtons()
        return

    def __onShowHide( self, startup = False ):
        " Triggered when show/hide button is clicked "
        if startup or self.filesystemView.isVisible():
            self.filesystemView.setVisible( False )
            self.lowerToolbar.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show file system tree" )

            self.__minH = self.lower.minimumHeight()
            self.__maxH = self.lower.maximumHeight()

            self.lower.setMinimumHeight( self.headerFrame.height() )
            self.lower.setMaximumHeight( self.headerFrame.height() )

            Settings().showFSViewer = False
        else:
            self.filesystemView.setVisible( True )
            self.lowerToolbar.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide file system tree" )

            self.lower.setMinimumHeight( self.__minH )
            self.lower.setMaximumHeight( self.__maxH )

            Settings().showFSViewer = True
        return

    def highlightPrjItem( self, path ):
        " Triggered when the file is to be highlighted in a project tree "
        return self.projectTreeView.highlightItem( path )

    def highlightFSItem( self, path ):
        " Triggered when the file is to be highlighted in the FS tree "
        result = self.filesystemView.highlightItem( path )
        if result:
            # Found, so check if the panel is shown
            if not self.filesystemView.isVisible():
                self.__onShowHide()
        return result

