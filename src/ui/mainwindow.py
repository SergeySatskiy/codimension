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

""" codimension main window """

import os, os.path, sys, logging, ConfigParser
from subprocess                 import Popen
from PyQt4.QtCore               import SIGNAL, Qt, QSize, QTimer, QDir, QVariant, \
                                       QUrl
from PyQt4.QtGui                import QLabel, QToolBar, QWidget, QMessageBox, \
                                       QVBoxLayout, QSplitter, QDialog, \
                                       QSizePolicy, QAction, QMainWindow, \
                                       QShortcut, QFrame, QApplication, \
                                       QCursor, QMenu, QToolButton, QToolTip, \
                                       QPalette, QColor, QFileDialog, QDialog, \
                                       QDesktopServices
from fitlabel                   import FitPathLabel
from utils.globals              import GlobalData
from utils.project              import CodimensionProject
from sidebar                    import SideBar
from logviewer                  import LogViewer
from taghelpviewer              import TagHelpViewer
from todoviewer                 import TodoViewer
from redirector                 import Redirector
from utils.pixmapcache          import PixmapCache
from functionsviewer            import FunctionsViewer
from globalsviewer              import GlobalsViewer
from classesviewer              import ClassesViewer
from recentprojectsviewer       import RecentProjectsViewer
from projectviewer              import ProjectViewer
from outline                    import FileOutlineViewer
from editorsmanager             import EditorsManager
from linecounter                import LineCounterDialog
from projectproperties          import ProjectPropertiesDialog
from utils.settings             import Settings
from findreplacewidget          import FindWidget, ReplaceWidget
from gotolinewidget             import GotoLineWidget
from pylintviewer               import PylintViewer
from pylintparser.pylintparser  import Pylint
from utils.fileutils            import PythonFileType, \
                                       Python3FileType, detectFileType, \
                                       PixmapFileType, SOFileType, \
                                       ELFFileType, PDFFileType, \
                                       PythonCompiledFileType, \
                                       CodimensionProjectFileType
from pymetricsviewer            import PymetricsViewer
from pymetricsparser.pymetricsparser    import PyMetrics
from findinfiles                import FindInFilesDialog
from findinfilesviewer          import FindInFilesViewer, hideSearchTooltip
from findname                   import FindNameDialog
from findfile                   import FindFileDialog
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from diagram.importsdgm         import ImportsDiagramDialog, \
                                       ImportsDiagramProgress, \
                                       ImportDiagramOptions
from ui.runparams               import RunDialog
from utils.run                  import getCwdCmdEnv
from debugger.console           import DebuggerConsole
from debugger.context           import DebuggerContext
from debugger.modifiedunsaved   import ModifiedUnsavedDialog
from debugger.main              import CodimensionDebugger


class EditorsManagerWidget( QWidget ):
    " Tab widget which has tabs with editors and viewers "

    def __init__( self, parent ):

        QWidget.__init__( self )

        self.editorsManager = EditorsManager( parent )
        self.findWidget = FindWidget( self.editorsManager )
        self.replaceWidget = ReplaceWidget( self.editorsManager )
        self.gotoLineWidget = GotoLineWidget( self.editorsManager )
        self.editorsManager.registerAuxWidgets( self.findWidget,
                                                self.replaceWidget,
                                                self.gotoLineWidget )

        self.editorsManager.setSizePolicy( QSizePolicy.Preferred,
                                           QSizePolicy.Expanding )
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins( 1, 1, 1, 1 )

        self.layout.addWidget( self.editorsManager )
        self.layout.addWidget( self.findWidget )
        self.layout.addWidget( self.replaceWidget )
        self.layout.addWidget( self.gotoLineWidget )

        self.setLayout( self.layout )
        return


class CodimensionMainWindow( QMainWindow ):
    """ Main application window """

    def __init__( self, splash, settings ):
        QMainWindow.__init__( self )

        self.debugMode = False
        self.__debugger = CodimensionDebugger( self )
        self.settings = settings
        self.__initialisation = True

        # This prevents context menu on the main window toolbar.
        # I don't really know why but it is what I need
        self.setContextMenuPolicy( Qt.NoContextMenu )

        # The size restore is done twice to avoid huge flickering
        # This one is approximate, the one in the timer handler is precise
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != settings.screenWidth or \
           screenSize.height() != settings.screenHeight:
            # The screen resolution has been changed, use the default pos
            defXPos, defYpos, \
            defWidth, defHeight = settings.getDefaultGeometry()
            self.resize( defWidth, defHeight )
            self.move( defXPos, defYpos )
        else:
            # No changes in the screen resolution
            self.resize( settings.width, settings.height )
            self.move( settings.xpos + settings.xdelta,
                       settings.ypos + settings.ydelta )

        splash.showMessage( "Initializing status bar..." )
        self.__statusBar = None
        self.sbLanguage = None
        self.sbFile = None
        self.sbEol = None
        self.sbPos = None
        self.sbLine = None
        self.sbWritable = None
        self.sbEncoding = None
        self.__createStatusBar()

        splash.showMessage( "Creating toolbar..." )
        self.__createToolBar()

        splash.showMessage( "Creating layout..." )
        self.__leftSideBar = None
        self.__bottomSideBar = None
        self.__rightSideBar = None

        # Setup output redirectors
        sys.stdout = Redirector( True )
        sys.stderr = Redirector( False )

        self.__horizontalSplitter = None
        self.__verticalSplitter = None
        self.__logViewer = None
        self.__createLayout( settings )

        splash.showMessage( "Initializing main menu bar..." )
        self.__initMainMenu()

        self.updateWindowTitle()
        self.__printThirdPartyAvailability()

        findNextAction = QShortcut( 'F3', self )
        self.connect( findNextAction, SIGNAL( "activated()" ),
                      self.editorsManagerWidget.editorsManager.findNext )
        findPrevAction = QShortcut( 'Shift+F3', self )
        self.connect( findPrevAction, SIGNAL( "activated()" ),
                      self.editorsManagerWidget.editorsManager.findPrev )

        # Needs for a proper update of the pylint menu
        self.connect( GlobalData().project, SIGNAL( 'fsChanged' ),
                      self.__onFSChanged )


        # 0 does not work, the window must be properly
        # drawn before restoring the old position
        QTimer.singleShot( 1, self.__restorePosition )
        return

    def __restorePosition( self ):
        " Makes sure that the window frame delta is proper "
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != self.settings.screenWidth or \
           screenSize.height() != self.settings.screenHeight:
            # The screen resolution has been changed, save the new values
            self.settings.screenWidth = screenSize.width()
            self.settings.screenHeight = screenSize.height()
            self.settings.xdelta = self.settings.xpos - self.x()
            self.settings.ydelta = self.settings.ypos - self.y()
            self.settings.xpos = self.x()
            self.settings.ypos = self.y()

            self.__initialisation = False
            return


        # Screen resolution is the same as before
        if self.settings.xpos != self.x() or \
           self.settings.ypos != self.y():
            # The saved delta is incorrect, update it
            self.settings.xdelta = self.settings.xpos - self.x() + \
                                   self.settings.xdelta
            self.settings.ydelta = self.settings.ypos - self.y() + \
                                   self.settings.ydelta
            self.settings.xpos = self.x()
            self.settings.ypos = self.y()
        self.__initialisation = False
        return

    def __onMaximizeEditor( self ):
        " Triggered when F11 is pressed "
        self.__leftSideBar.shrink()
        self.__bottomSideBar.shrink()
        self.__rightSideBar.shrink()
        return

    def __createLayout( self, settings ):
        """ creates the UI layout """

        self.editorsManagerWidget = EditorsManagerWidget( self )
        self.editorsManagerWidget.findWidget.hide()
        self.editorsManagerWidget.replaceWidget.hide()
        self.editorsManagerWidget.gotoLineWidget.hide()

        # The layout is a sidebar-style one
        self.__bottomSideBar = SideBar( SideBar.South, self )
        self.__leftSideBar   = SideBar( SideBar.West, self )
        self.__rightSideBar = SideBar( SideBar.East, self )

        # Create tabs on bars
        self.__logViewer = LogViewer()
        self.__bottomSideBar.addTab( self.__logViewer,
                                     PixmapCache().getIcon( 'logviewer.png' ),
                                     'Log' )
        self.connect( sys.stdout, SIGNAL('appendToStdout'), self.toStdout )
        self.connect( sys.stderr, SIGNAL('appendToStderr'), self.toStderr )

        # replace logging streamer to self.stdout
        logging.root.handlers = []
        handler = logging.StreamHandler( sys.stdout )
        handler.setFormatter( \
            logging.Formatter( "%(levelname) -10s %(asctime)s %(message)s",
            None ) )
        logging.root.addHandler( handler )


        self.projectViewer = ProjectViewer( self )
        self.__leftSideBar.addTab( self.projectViewer,
                                   PixmapCache().getIcon( 'project.png' ),
                                   "Project" )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.projectViewer.onFileUpdated )
        self.recentProjectsViewer = RecentProjectsViewer( self )
        self.__leftSideBar.addTab( self.recentProjectsViewer,
                                   PixmapCache().getIcon( 'project.png' ),
                                   "Recent" )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.recentProjectsViewer.onFileUpdated )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( "bufferSavedAs" ),
                      self.recentProjectsViewer.onFileUpdated )
        self.connect( self.projectViewer, SIGNAL( "fileUpdated" ),
                      self.recentProjectsViewer.onFileUpdated )

        #self.__leftSideBar.setTabToolTip( 1, "Recently loaded projects" )
        self.classesViewer = ClassesViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.classesViewer.onFileUpdated )
        self.__leftSideBar.addTab( self.classesViewer,
                                   PixmapCache().getIcon( 'class.png' ),
                                   "Classes" )
        self.functionsViewer = FunctionsViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.functionsViewer.onFileUpdated )
        self.__leftSideBar.addTab( self.functionsViewer,
                                   PixmapCache().getIcon( 'fx.png' ),
                                   "Functions" )
        self.globalsViewer = GlobalsViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.globalsViewer.onFileUpdated )
        self.__leftSideBar.addTab( self.globalsViewer,
                                   PixmapCache().getIcon( 'globalvar.png' ),
                                   "Globals" )


        # Create todo viewer
        todoViewer = TodoViewer()
        self.__bottomSideBar.addTab( todoViewer,
                                     PixmapCache().getIcon( 'todo.png' ),
                                     'Todo' )
        self.__bottomSideBar.setTabEnabled( 1, False )

        # Create pylint viewer
        self.__pylintViewer = PylintViewer()
        self.__bottomSideBar.addTab( self.__pylintViewer,
                                     PixmapCache().getIcon( 'pylint.png' ),
                                     'Pylint viewer' )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.__pylintViewer.onFileUpdated )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'bufferSavedAs' ),
                      self.__pylintViewer.onFileUpdated )
        self.connect( self.__pylintViewer, SIGNAL( 'updatePylintTooltip' ),
                      self.__onPylintTooltip )
        if GlobalData().pylintAvailable:
            self.__onPylintTooltip( "No results available" )
        else:
            self.__onPylintTooltip( "Pylint is not available" )

        # Create pymetrics viewer
        self.__pymetricsViewer = PymetricsViewer()
        self.__bottomSideBar.addTab( self.__pymetricsViewer,
                                     PixmapCache().getIcon( 'metrics.png' ),
                                     'Metrics viewer' )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.__pymetricsViewer.onFileUpdated )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'bufferSavedAs' ),
                      self.__pymetricsViewer.onFileUpdated )
        self.connect( self.__pymetricsViewer,
                      SIGNAL( 'updatePymetricsTooltip' ),
                      self.__onPymetricsTooltip )
        self.__onPymetricsTooltip( "No results available" )

        # Create search results viewer
        self.__findInFilesViewer = FindInFilesViewer()
        self.__bottomSideBar.addTab( self.__findInFilesViewer,
                                     PixmapCache().getIcon( 'findindir.png' ),
                                     'Search results' )

        # Create tag help viewer
        self.__tagHelpViewer = TagHelpViewer()
        self.__bottomSideBar.addTab( self.__tagHelpViewer,
                                     PixmapCache().getIcon( 'helpviewer.png' ),
                                     'Context help' )
        self.__bottomSideBar.setTabToolTip( 5, "Ctrl+F1 in python file" )

        # Create the debugger console
        self.__debuggerConsole = DebuggerConsole()
#        self.__bottomSideBar.addTab( self.__debuggerConsole,
#                                     PixmapCache().getIcon( 'debuggerconsole.png' ),
#                                     'Debugger console' )
#        self.__bottomSideBar.setTabEnabled( 6, False )

        # Create outline viewer
        self.__outlineViewer = FileOutlineViewer( self.editorsManagerWidget.editorsManager )
        self.__rightSideBar.addTab( self.__outlineViewer,
                                    PixmapCache().getIcon( 'filepython.png' ),
                                    'File outline' )

        self.__debuggerContext = DebuggerContext()
#        self.__rightSideBar.addTab( self.__debuggerContext,
#                                    PixmapCache().getIcon( 'debugger.png' ),
#                                    'Debugger' )
#        self.__rightSideBar.setTabEnabled( 1, False )

        # Create splitters
        self.__horizontalSplitter = QSplitter( Qt.Horizontal )
        self.__verticalSplitter = QSplitter( Qt.Vertical )

        self.__horizontalSplitter.addWidget( self.__leftSideBar )
        self.__horizontalSplitter.addWidget( self.editorsManagerWidget )
        self.__horizontalSplitter.addWidget( self.__rightSideBar )

        self.__verticalSplitter.addWidget( self.__horizontalSplitter )
        self.__verticalSplitter.addWidget( self.__bottomSideBar )

        self.setCentralWidget( self.__verticalSplitter )

        self.__leftSideBar.setSplitter( self.__horizontalSplitter )
        self.__bottomSideBar.setSplitter( self.__verticalSplitter )
        self.__rightSideBar.setSplitter( self.__horizontalSplitter )

        # restore the side bar state
        self.__horizontalSplitter.setSizes( settings.hSplitterSizes )
        self.__verticalSplitter.setSizes( settings.vSplitterSizes )
        if settings.leftBarMinimized:
            self.__leftSideBar.shrink()
        if settings.bottomBarMinimized:
            self.__bottomSideBar.shrink()
        if settings.rightBarMinimized:
            self.__rightSideBar.shrink()

        # Setup splitters movement handlers
        self.connect( self.__verticalSplitter,
                      SIGNAL( 'splitterMoved(int,int)' ),
                      self.vSplitterMoved )
        self.connect( self.__horizontalSplitter,
                      SIGNAL( 'splitterMoved(int,int)' ),
                      self.hSplitterMoved )

        return

    @staticmethod
    def __printThirdPartyAvailability():
        " Prints third party tools availability "

        globalData = GlobalData()
        if globalData.fileAvailable:
            logging.debug( "The 'file' utility is available" )
        else:
            logging.warning( "The 'file' utility is not found. " \
                             "Some functionality will not be available." )

        if globalData.pylintAvailable:
            logging.debug( "The 'pylint' utility is available" )
        else:
            logging.warning( "The 'pylint' utility is not found. " \
                             "Some functionality will not be available." )

        if globalData.graphvizAvailable:
            logging.debug( "The 'graphviz' utility is available" )
        else:
            logging.warning( "The 'graphviz' utility is not found. " \
                             "Some functionality will not be available." )

        return

    def vSplitterMoved( self, pos, index ):
        """ vertical splitter moved handler """
        vList = list( self.__verticalSplitter.sizes() )
        self.settings.bottomBarMinimized = self.__bottomSideBar.isMinimized()
        self.settings.vSplitterSizes = vList
        return

    def hSplitterMoved( self, pos, index ):
        """ horizontal splitter moved handler """
        hList = list( self.__horizontalSplitter.sizes() )
        self.settings.leftBarMinimized = self.__leftSideBar.isMinimized()
        self.settings.rightBarMinimized = self.__rightSideBar.isMinimized()
        self.settings.hSplitterSizes = hList
        return

    def __createStatusBar( self ):
        """ creates status bar """

        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled( True )

        sbPalette = QPalette( self.__statusBar.palette() )
        sbPalette.setColor( QPalette.Foreground, QColor( 220, 0, 0 ) )
        self.__statusBar.setPalette( sbPalette )
        font = self.__statusBar.font()
        font.setItalic( True )
        self.__statusBar.setFont( font )

        self.dbgState = QLabel( "Debugger state: unknown", self.__statusBar )
        self.dbgState.setFrameStyle( QFrame.StyledPanel )
        self.dbgState.setAutoFillBackground( True )
        dbgPalette = self.dbgState.palette()
        dbgPalette.setColor( QPalette.Background, QColor( 255, 255, 127 ) )
        self.dbgState.setPalette( dbgPalette )
        self.__statusBar.addPermanentWidget( self.dbgState )
        self.dbgState.setToolTip( "Debugger status" )
        self.dbgState.setVisible( False )

        self.sbLanguage = QLabel( self.__statusBar )
        self.sbLanguage.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbLanguage )
        self.sbLanguage.setToolTip( "Editor language/image format" )

        self.sbEncoding = QLabel( self.__statusBar )
        self.sbEncoding.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbEncoding )
        self.sbEncoding.setToolTip( "Editor encoding/image size" )

        self.sbEol = QLabel( self.__statusBar )
        self.sbEol.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbEol )
        self.sbEol.setToolTip( "Editor EOL setting" )

        self.sbWritable = QLabel( self.__statusBar )
        self.sbWritable.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbWritable )
        self.sbWritable.setToolTip( "Editor file read/write mode" )

        self.sbFile = FitPathLabel( self.__statusBar )
        self.sbFile.setMaximumWidth( 512 )
        self.sbFile.setMinimumWidth( 128 )
        self.sbFile.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbFile, True )
        self.sbFile.setToolTip( "Editor file name (double click to copy path)" )
        self.connect( self.sbFile, SIGNAL( "doubleClicked" ),
                      self.__onPathLabelDoubleClick )
        self.sbFile.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.sbFile,
                      SIGNAL( 'customContextMenuRequested(const QPoint &)' ),
                      self.__showPathLabelContextMenu )

        self.sbLine = QLabel( self.__statusBar )
        self.sbLine.setMinimumWidth( 72 )
        self.sbLine.setAlignment( Qt.AlignCenter )
        self.sbLine.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbLine )
        self.sbLine.setToolTip( "Editor line number" )

        self.sbPos = QLabel( self.__statusBar )
        self.sbPos.setMinimumWidth( 72 )
        self.sbPos.setAlignment( Qt.AlignCenter )
        self.sbPos.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbPos )
        self.sbPos.setToolTip( "Editor cursor position" )

        # Adjust the font size
        font = self.sbLanguage.font()

        # No need to increase the status bar font in most of the cases.
        # It's better only in case of XServer on PC (Xming in my experience)
        # font.setPointSize( font.pointSize() + 1 )
        self.sbLanguage.setFont( font )
        self.sbEncoding.setFont( font )
        self.sbEol.setFont( font )
        self.sbWritable.setFont( font )
        self.sbFile.setFont( font )
        self.sbLine.setFont( font )
        self.sbPos.setFont( font )

        return

    def __initMainMenu( self ):
        " Initializes the main menu bar "
        editorsManager = self.editorsManagerWidget.editorsManager

        # The Project menu
        self.__projectMenu = QMenu( "&Project", self )
        self.connect( self.__projectMenu, SIGNAL( "aboutToShow()" ),
                      self.__prjAboutToShow )
        self.__newProjectAct = self.__projectMenu.addAction( \
                                        PixmapCache().getIcon( 'project.png' ),
                                        "&New project", self.__createNewProject,
                                        'Ctrl+Shift+N' )
        self.__openProjectAct = self.__projectMenu.addAction( \
                                        PixmapCache().getIcon( 'project.png' ),
                                        '&Open project', self.__openProject,
                                        'Ctrl+Shift+O' )
        self.__unloadProjectAct = self.__projectMenu.addAction( \
                                        PixmapCache().getIcon( 'unloadproject.png' ),
                                        '&Unload project',
                                        self.projectViewer.unloadProject )
        self.__projectPropsAct = self.__projectMenu.addAction( \
                                        PixmapCache().getIcon( 'smalli.png' ),
                                        '&Properties',
                                        self.projectViewer.projectProperties )
        self.__projectMenu.addSeparator()
        self.__recentPrjMenu = QMenu( "&Recent projects", self )
        self.connect( self.__recentPrjMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__onRecentPrj )
        self.__projectMenu.addMenu( self.__recentPrjMenu )
        self.__projectMenu.addSeparator()
        self.__quitAct = self.__projectMenu.addAction( \
                                        PixmapCache().getIcon( 'exitmenu.png' ),
                                        "E&xit codimension", QApplication.closeAllWindows,
                                        "Ctrl+Q" )

        # The Tab menu
        self.__tabMenu = QMenu( "&Tab", self )
        self.connect( self.__tabMenu, SIGNAL( "aboutToShow()" ),
                      self.__tabAboutToShow )
        self.connect( self.__tabMenu, SIGNAL( "aboutToHide()" ),
                      self.__tabAboutToHide )
        self.__newTabAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'filemenu.png' ),
                                        "&New tab",
                                        editorsManager.newTabClicked,
                                        'Ctrl+N' )
        self.__openFileAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'filemenu.png' ),
                                        '&Open file', self.__openFile, 'Ctrl+O' )
        self.__cloneTabAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'clonetabmenu.png' ),
                                        '&Clone tab', editorsManager.onClone )
        self.__closeOtherTabsAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( '' ),
                                        'Close other tabs', editorsManager.onCloseOther )
        self.__closeTabAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'closetabmenu.png' ),
                                        'Close &tab', editorsManager.onCloseTab )
        self.__tabMenu.addSeparator()
        self.__saveFileAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'savemenu.png' ),
                                        '&Save', editorsManager.onSave, 'Ctrl+S' )
        self.__saveFileAsAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'saveasmenu.png' ),
                                        'Save &as...', editorsManager.onSaveAs, "Ctrl+Shift+S" )
        self.__tabJumpToDefAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'definition.png' ),
                                        "&Jump to definition", self.__onTabJumpToDef )
        self.__tabJumpToScopeBeginAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'jumpupscopemenu.png' ),
                                        'Jump to scope &begin', self.__onTabJumpToScopeBegin )
        self.__tabOpenImportAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'imports.png' ),
                                        'Open &import(s)', self.__onTabOpenImport )
        self.__openAsFileAct = self.__tabMenu.addAction( \
                                        PixmapCache().getIcon( 'filemenu.png' ),
                                        'O&pen as file', self.__onOpenAsFile )
        self.__tabMenu.addSeparator()
        self.__recentFilesMenu = QMenu( "&Recent files", self )
        self.connect( self.__recentFilesMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__onRecentFile )
        self.__tabMenu.addMenu( self.__recentFilesMenu )

        # The Edit menu
        self.__editMenu = QMenu( "&Edit", self )
        self.connect( self.__editMenu, SIGNAL( "aboutToShow()" ),
                      self.__editAboutToShow )
        self.connect( self.__editMenu, SIGNAL( "aboutToHide()" ),
                      self.__editAboutToHide )
        self.__undoAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'undo.png' ),
                                        '&Undo', self.__onUndo )
        self.__redoAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'redo.png' ),
                                        '&Redo', self.__onRedo )
        self.__editMenu.addSeparator()
        self.__cutAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'cutmenu.png' ),
                                        'Cu&t', self.__onCut )
        self.__copyAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'copymenu.png' ),
                                        '&Copy', editorsManager.onCopy )
        self.__pasteAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'pastemenu.png' ),
                                        '&Paste', self.__onPaste )
        self.__selectAllAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'selectallmenu.png' ),
                                        'Select &all', self.__onSelectAll )
        self.__editMenu.addSeparator()
        self.__commentAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'commentmenu.png' ),
                                        'C&omment/uncomment', self.__onComment )
        self.__duplicateAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'duplicatemenu.png' ),
                                        '&Duplicate line', self.__onDuplicate )
        self.__autocompleteAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'autocompletemenu.png' ),
                                        'Autoco&mplete', self.__onAutocomplete )
        self.__expandTabsAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'expandtabs.png' ),
                                        'Expand tabs (&4 spaces)',
                                        self.__onExpandTabs )
        self.__trailingSpacesAct = self.__editMenu.addAction( \
                                        PixmapCache().getIcon( 'trailingws.png' ),
                                        'Remove trailing &spaces',
                                        self.__onRemoveTrailingSpaces )

        # The Search menu
        self.__searchMenu = QMenu( "&Search", self )
        self.connect( self.__searchMenu, SIGNAL( "aboutToShow()" ),
                      self.__searchAboutToShow )
        self.connect( self.__searchMenu, SIGNAL( "aboutToHide()" ),
                      self.__searchAboutToHide )
        self.__searchInFilesAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'findindir.png' ),
                                        "Find in file&s", self.findInFilesClicked,
                                        "Ctrl+Shift+F" )
        self.__searchMenu.addSeparator()
        self.__findNameMenuAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'findname.png' ),
                                        'Find &name in project',
                                        self.findNameClicked,
                                        'Alt+Shift+S' )
        self.__fileProjectFileAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'findfile.png' ),
                                        'Find &project file',
                                        self.findFileClicked,
                                        'Alt+Shift+O' )
        self.__searchMenu.addSeparator()
        self.__findOccurencesAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'findindir.png' ),
                                        'Find &occurences', self.__onFindOccurences )
        self.__findAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'findindir.png' ),
                                        '&Find...', self.__onFind )
        self.__findCurrentAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'find.png' ),
                                        'Find current &word',
                                        self.__onFindCurrent )
        self.__findNextAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( '1rightarrow.png' ),
                                        "Find &next", self.__onFindNext )
        self.__findPrevAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( '1leftarrow.png' ),
                                        "Find pre&vious", self.__onFindPrevious )
        self.__replaceAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'replace.png' ),
                                        '&Replace...',
                                        self.__onReplace )
        self.__goToLineAct = self.__searchMenu.addAction( \
                                        PixmapCache().getIcon( 'gotoline.png' ),
                                        '&Go to line...', self.__onGoToLine )

        # The Tools menu
        self.__toolsMenu = QMenu( "T&ools", self )
        self.connect( self.__toolsMenu, SIGNAL( "aboutToShow()" ),
                      self.__toolsAboutToShow )
        self.connect( self.__toolsMenu, SIGNAL( "aboutToHide()" ),
                      self.__toolsAboutToHide )
        self.__prjPylintAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'pylint.png' ),
                                        '&Pylint for project',
                                        self.pylintButtonClicked )
        self.__prjGenPylintrcAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'generate.png' ),
                                        '&Generate project pylintrc',
                                        self.__onGenPylintRC )
        self.__prjEditPylintrcAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'edit.png' ),
                                        '&Edit project pylintrc',
                                        self.__onEditPylintRC )
        self.__prjDelPylintrcAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'trash.png' ),
                                        '&Delete project pylintrc',
                                        self.__onDelPylintRC )
        self.__tabPylintAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'pylint.png' ),
                                        'P&ylint for tab', self.__onTabPylint )
        self.__toolsMenu.addSeparator()
        self.__prjPymetricsAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'metrics.png' ),
                                        'Py&metrics for project',
                                        self.pymetricsButtonClicked )
        self.__tabPymetricsAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'metrics.png' ),
                                        "Pyme&trics for tab", self.__onTabPymetrics )
        self.__toolsMenu.addSeparator()
        self.__prjLineCounterAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'linecounter.png' ),
                                        "&Line counter for project",
                                        self.linecounterButtonClicked )
        self.__tabLineCounterAct = self.__toolsMenu.addAction( \
                                        PixmapCache().getIcon( 'linecounter.png' ),
                                        "L&ine counter for tab",
                                        self.__onTabLineCounter )

        # The Run menu
        self.__runMenu = QMenu( "&Run", self )
        self.connect( self.__runMenu, SIGNAL( "aboutToShow()" ),
                      self.__runAboutToShow )
        self.__prjRunAct = self.__runMenu.addAction( \
                                        PixmapCache().getIcon( 'run.png' ),
                                        'Run &project main script',
                                        self.__onRunProject )
        self.__prjRunDlgAct = self.__runMenu.addAction( \
                                        PixmapCache().getIcon( 'detailsdlg.png' ),
                                        'Run p&roject main script...',
                                        self.__onRunProjectSettings )
        self.__tabRunAct = self.__runMenu.addAction( \
                                        PixmapCache().getIcon( 'run.png' ),
                                        'Run &tab script',
                                        self.__onRunTab )
        self.__tabRunDlgAct = self.__runMenu.addAction( \
                                        PixmapCache().getIcon( 'detailsdlg.png' ),
                                        'Run t&ab script...',
                                        self.__onRunTabDlg )

        # The Diagrams menu
        self.__diagramsMenu = QMenu( "&Diagrams", self )
        self.connect( self.__diagramsMenu, SIGNAL( "aboutToShow()" ),
                      self.__diagramsAboutToShow )
        self.__prjImportDgmAct = self.__diagramsMenu.addAction( \
                                        PixmapCache().getIcon( 'importsdiagram.png' ),
                                        '&Project imports diagram',
                                        self.__onImportDgm )
        self.__prjImportsDgmDlgAct = self.__diagramsMenu.addAction( \
                                        PixmapCache().getIcon( 'detailsdlg.png' ),
                                        'P&roject imports diagram...',
                                        self.__onImportDgmTuned )
        self.__tabImportDgmAct = self.__diagramsMenu.addAction( \
                                        PixmapCache().getIcon( 'importsdiagram.png' ),
                                        '&Tab imports diagram',
                                        self.__onTabImportDgm )
        self.__tabImportDgmDlgAct = self.__diagramsMenu.addAction( \
                                        PixmapCache().getIcon( 'detailsdlg.png' ),
                                        'T&ab imports diagram...',
                                        self.__onTabImportDgmTuned )

        # The View menu
        self.__viewMenu = QMenu( "&View", self )
        self.connect( self.__viewMenu, SIGNAL( "aboutToShow()" ),
                      self.__viewAboutToShow )
        self.connect( self.__viewMenu, SIGNAL( "aboutToHide()" ),
                      self.__viewAboutToHide )
        self.__shrinkBarsAct = self.__viewMenu.addAction( \
                                        PixmapCache().getIcon( 'shrinkmenu.png' ),
                                        "&Hide sidebars", self.__onMaximizeEditor,
                                        'F11' )
        self.__leftSideBarMenu = QMenu( "&Left sidebar", self )
        self.connect( self.__leftSideBarMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__activateSideTab )
        self.__prjBarAct = self.__leftSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'project.png' ),
                                        'Activate &project tab' )
        self.__prjBarAct.setData( QVariant( 'prj' ) )
        self.__recentBarAct = self.__leftSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'project.png' ),
                                        'Activate &recent tab' )
        self.__recentBarAct.setData( QVariant( 'recent' ) )
        self.__classesBarAct = self.__leftSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'class.png' ),
                                        'Activate &classes tab' )
        self.__classesBarAct.setData( QVariant( 'classes' ) )
        self.__funcsBarAct = self.__leftSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'fx.png' ),
                                        'Activate &functions tab' )
        self.__funcsBarAct.setData( QVariant( 'funcs' ) )
        self.__globsBarAct = self.__leftSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'globalvar.png' ),
                                        'Activate &globals tab' )
        self.__globsBarAct.setData( QVariant( 'globs' ) )
        self.__viewMenu.addMenu( self.__leftSideBarMenu )

        self.__rightSideBarMenu = QMenu( "&Right sidebar", self )
        self.connect( self.__rightSideBarMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__activateSideTab )
        self.__outlineBarAct = self.__rightSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'filepython.png' ),
                                        'Activate &outline tab' )
        self.__outlineBarAct.setData( QVariant( 'outline' ) )
        self.__viewMenu.addMenu( self.__rightSideBarMenu )

        self.__bottomSideBarMenu = QMenu( "&Bottom sidebar", self )
        self.connect( self.__bottomSideBarMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__activateSideTab )
        self.__logBarAct = self.__bottomSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'logviewer.png' ),
                                        'Activate &log tab' )
        self.__logBarAct.setData( QVariant( 'log' ) )
        self.__pylintBarAct = self.__bottomSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'pylint.png' ),
                                        'Activate &pylint tab' )
        self.__pylintBarAct.setData( QVariant( 'pylint' ) )
        self.__pymetricsBarAct = self.__bottomSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'metrics.png' ),
                                        'Activate py&metrics tab' )
        self.__pymetricsBarAct.setData( QVariant( 'pymetrics' ) )
        self.__searchBarAct = self.__bottomSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'findindir.png' ),
                                        'Activate &search tab' )
        self.__searchBarAct.setData( QVariant( 'search' ) )
        self.__contextHelpBarAct = self.__bottomSideBarMenu.addAction( \
                                        PixmapCache().getIcon( 'helpviewer.png' ),
                                        'Activate context &help tab' )
        self.__contextHelpBarAct.setData( QVariant( 'contexthelp' ) )
        self.__viewMenu.addMenu( self.__bottomSideBarMenu )
        self.__viewMenu.addSeparator()
        self.__zoomInAct = self.__viewMenu.addAction( \
                                        PixmapCache().getIcon( 'zoomin.png' ),
                                        'Zoom &in', self.__onZoomIn )
        self.__zoomOutAct = self.__viewMenu.addAction( \
                                        PixmapCache().getIcon( 'zoomout.png' ),
                                        'Zoom &out', self.__onZoomOut )
        self.__zoom11Act = self.__viewMenu.addAction( \
                                        PixmapCache().getIcon( 'zoomreset.png' ),
                                        'Zoom r&eset', self.__onZoomReset )

        # The Help menu
        self.__helpMenu = QMenu( "&Help", self )
        self.connect( self.__helpMenu, SIGNAL( "aboutToShow()" ),
                      self.__helpAboutToShow )
        self.connect( self.__helpMenu, SIGNAL( "aboutToHide()" ),
                      self.__helpAboutToHide )
        self.__shortcutsAct = self.__helpMenu.addAction( \
                                        PixmapCache().getIcon( 'shortcutsmenu.png' ),
                                        '&Major shortcuts',
                                        editorsManager.onHelp, 'F1' )
        self.__contextHelpAct = self.__helpMenu.addAction( \
                                        PixmapCache().getIcon( 'helpviewer.png' ),
                                        'Current &word help', self.__onContextHelp )
        self.__helpMenu.addSeparator()
        self.__allShotcutsAct = self.__helpMenu.addAction( \
                                        PixmapCache().getIcon( 'allshortcutsmenu.png' ),
                                        '&All shortcuts (web page)',
                                        self.__onAllShortcurs )
        self.__homePageAct = self.__helpMenu.addAction( \
                                        PixmapCache().getIcon( 'homepagemenu.png' ),
                                        'Codimension &home page',
                                        self.__onHomePage )

        menuBar = self.menuBar()
        menuBar.addMenu( self.__projectMenu )
        menuBar.addMenu( self.__tabMenu )
        menuBar.addMenu( self.__editMenu )
        menuBar.addMenu( self.__searchMenu )
        menuBar.addMenu( self.__runMenu )
        menuBar.addMenu( self.__toolsMenu )
        menuBar.addMenu( self.__diagramsMenu )
        menuBar.addMenu( self.__viewMenu )
        menuBar.addMenu( self.__helpMenu )
        return

    def __createToolBar( self ):
        """ creates the buttons bar """

        self.createProjectButton = QAction( \
                                PixmapCache().getIcon( 'createproject.png' ),
                                'Create new project', self )
        self.connect( self.createProjectButton, SIGNAL( "triggered()" ),
                      self.__createNewProject )

        # Imports diagram button and its menu
        importsMenu = QMenu( self )
        importsDlgAct = importsMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Fine tuned imports diagram' )
        self.connect( importsDlgAct, SIGNAL( 'triggered()' ),
                      self.__onImportDgmTuned )
        self.importsDiagramButton = QToolButton( self )
        self.importsDiagramButton.setIcon( \
                            PixmapCache().getIcon( 'importsdiagram.png' ) )
        self.importsDiagramButton.setToolTip( 'Generate imports diagram' )
        self.importsDiagramButton.setPopupMode( QToolButton.DelayedPopup )
        self.importsDiagramButton.setMenu( importsMenu )
        self.importsDiagramButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.importsDiagramButton, SIGNAL( 'clicked(bool)' ),
                      self.__onImportDgm )

        # Run project button and its menu
        runProjectMenu = QMenu( self )
        runProjectAct = runProjectMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run/debug parameters' )
        self.connect( runProjectAct, SIGNAL( 'triggered()' ),
                      self.__onRunProjectSettings )
        self.runProjectButton = QToolButton( self )
        self.runProjectButton.setIcon( \
                            PixmapCache().getIcon( 'run.png' ) )
        self.runProjectButton.setToolTip( 'Project is not loaded' )
        self.runProjectButton.setPopupMode( QToolButton.DelayedPopup )
        self.runProjectButton.setMenu( runProjectMenu )
        self.runProjectButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.runProjectButton, SIGNAL( 'clicked(bool)' ),
                      self.__onRunProject )

        # Debug project button and its menu
        debugProjectMenu = QMenu( self )
        debugProjectAct = debugProjectMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run/debug parameters' )
        self.connect( debugProjectAct, SIGNAL( 'triggered()' ),
                      self.__onDebugProjectSettings )
        self.debugProjectButton = QToolButton( self )
        self.debugProjectButton.setIcon( \
                            PixmapCache().getIcon( 'debugger.png' ) )
        self.debugProjectButton.setToolTip( 'Project is not loaded' )
        self.debugProjectButton.setPopupMode( QToolButton.DelayedPopup )
        self.debugProjectButton.setMenu( debugProjectMenu )
        self.debugProjectButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.debugProjectButton, SIGNAL( 'clicked(bool)' ),
                      self.__onDebugProject )

        # Hide the button temporarily
        self.debugProjectButton.setVisible( False )

        packageDiagramButton = QAction( \
                PixmapCache().getIcon( 'packagediagram.png' ),
                'Generate package diagram', self )
        packageDiagramButton.setEnabled( False )
        packageDiagramButton.setVisible( False )
        applicationDiagramButton = QAction( \
                PixmapCache().getIcon( 'applicationdiagram.png' ),
                'Generate application diagram', self )
        applicationDiagramButton.setEnabled( False )
        applicationDiagramButton.setVisible( False )
        neverUsedButton = QAction( \
                PixmapCache().getIcon( 'neverused.png' ),
                'Analysis for never used variables, functions, classes', self )
        neverUsedButton.setEnabled( False )
        neverUsedButton.setVisible( False )

        # pylint button
        self.__existentPylintRCMenu = QMenu( self )
        editAct = self.__existentPylintRCMenu.addAction( \
                                    PixmapCache().getIcon( 'edit.png' ),
                                    'Edit the project pylintrc' )
        self.connect( editAct, SIGNAL( 'triggered()' ), self.__onEditPylintRC )
        self.__existentPylintRCMenu.addSeparator()
        delAct = self.__existentPylintRCMenu.addAction( \
                                    PixmapCache().getIcon( 'trash.png' ),
                                    'Delete the project pylintrc' )
        self.connect( delAct, SIGNAL( 'triggered()' ), self.__onDelPylintRC )

        self.__absentPylintRCMenu = QMenu( self )
        genAct = self.__absentPylintRCMenu.addAction( \
                                    PixmapCache().getIcon( 'generate.png' ),
                                    'Generate the project pylintrc' )
        self.connect( genAct, SIGNAL( 'triggered()' ), self.__onGenPylintRC )

        self.__pylintButton = QToolButton( self )
        self.__pylintButton.setIcon( PixmapCache().getIcon( 'pylint.png' ) )
        self.__pylintButton.setToolTip( 'Run pylint for the whole project' )
        self.__pylintButton.setPopupMode( QToolButton.DelayedPopup )
        self.__pylintButton.setMenu( self.__existentPylintRCMenu )
        self.__pylintButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__pylintButton, SIGNAL( 'clicked(bool)' ),
                      self.pylintButtonClicked )

        # pymetrics button
        self.__pymetricsButton = QAction( \
                                    PixmapCache().getIcon( 'metrics.png' ),
                                    'Project metrics', self )
        self.connect( self.__pymetricsButton, SIGNAL( 'triggered()' ),
                      self.pymetricsButtonClicked )

        self.linecounterButton = QAction( \
                                    PixmapCache().getIcon( 'linecounter.png' ),
                                    'Project line counter', self )
        self.connect( self.linecounterButton, SIGNAL( 'triggered()' ),
                      self.linecounterButtonClicked )

        self.__findInFilesButton = QAction( \
                                    PixmapCache().getIcon( 'findindir.png' ),
                                    'Find in project files (Ctrl+Shift+F)', self )
        self.connect( self.__findInFilesButton, SIGNAL( 'triggered()' ),
                      self.findInFilesClicked )

        self.__findNameButton = QAction( \
                                    PixmapCache().getIcon( 'findname.png' ),
                                    'Find name in project (Alt+Shift+S)', self )
        self.connect( self.__findNameButton, SIGNAL( 'triggered()' ),
                      self.findNameClicked )

        self.__findFileButton = QAction( \
                                    PixmapCache().getIcon( 'findfile.png' ),
                                    'Find project file (Alt+Shift+O)', self )
        self.connect( self.__findFileButton, SIGNAL( 'triggered()' ),
                      self.findFileClicked )

        # Editor settings button
        editorSettingsMenu = QMenu( self )
        verticalEdgeAct = editorSettingsMenu.addAction( 'Show vertical edge' )
        verticalEdgeAct.setCheckable( True )
        verticalEdgeAct.setChecked( self.settings.verticalEdge )
        self.connect( verticalEdgeAct, SIGNAL( 'changed()' ), self.__verticalEdgeChanged )
        showSpacesAct = editorSettingsMenu.addAction( 'Show whitespaces' )
        showSpacesAct.setCheckable( True )
        showSpacesAct.setChecked( self.settings.showSpaces )
        self.connect( showSpacesAct, SIGNAL( 'changed()' ), self.__showSpacesChanged )
        lineWrapAct = editorSettingsMenu.addAction( 'Wrap long lines' )
        lineWrapAct.setCheckable( True )
        lineWrapAct.setChecked( self.settings.lineWrap )
        self.connect( lineWrapAct, SIGNAL( 'changed()' ), self.__lineWrapChanged )
        showEOLAct = editorSettingsMenu.addAction( 'Show EOL' )
        showEOLAct.setCheckable( True )
        showEOLAct.setChecked( self.settings.showEOL )
        self.connect( showEOLAct, SIGNAL( 'changed()' ), self.__showEOLChanged )
        showBraceMatchAct = editorSettingsMenu.addAction( 'Show brace matching' )
        showBraceMatchAct.setCheckable( True )
        showBraceMatchAct.setChecked( self.settings.showBraceMatch )
        self.connect( showBraceMatchAct, SIGNAL( 'changed()' ), self.__showBraceMatchChanged )
        autoIndentAct = editorSettingsMenu.addAction( 'Auto indent' )
        autoIndentAct.setCheckable( True )
        autoIndentAct.setChecked( self.settings.autoIndent )
        self.connect( autoIndentAct, SIGNAL( 'changed()' ), self.__autoIndentChanged )
        backspaceUnindentAct = editorSettingsMenu.addAction( 'Backspace unindent' )
        backspaceUnindentAct.setCheckable( True )
        backspaceUnindentAct.setChecked( self.settings.backspaceUnindent )
        self.connect( backspaceUnindentAct, SIGNAL( 'changed()' ), self.__backspaceUnindentChanged )
        tabIndentsAct = editorSettingsMenu.addAction( 'TAB indents' )
        tabIndentsAct.setCheckable( True )
        tabIndentsAct.setChecked( self.settings.tabIndents )
        self.connect( tabIndentsAct, SIGNAL( 'changed()' ), self.__tabIndentsChanged )
        indentationGuidesAct = editorSettingsMenu.addAction( 'Show indentation guides' )
        indentationGuidesAct.setCheckable( True )
        indentationGuidesAct.setChecked( self.settings.indentationGuides )
        self.connect( indentationGuidesAct, SIGNAL( 'changed()' ), self.__indentationGuidesChanged )
        currentLineVisibleAct = editorSettingsMenu.addAction( 'Highlight current line' )
        currentLineVisibleAct.setCheckable( True )
        currentLineVisibleAct.setChecked( self.settings.currentLineVisible )
        self.connect( currentLineVisibleAct, SIGNAL( 'changed()' ), self.__currentLineVisibleChanged )
        jumpToFirstNonSpaceAct = editorSettingsMenu.addAction( 'HOME to first non-space' )
        jumpToFirstNonSpaceAct.setCheckable( True )
        jumpToFirstNonSpaceAct.setChecked( self.settings.jumpToFirstNonSpace )
        self.connect( jumpToFirstNonSpaceAct, SIGNAL( 'changed()' ), self.__homeToFirstNonSpaceChanged )
        removeTrailingOnSpaceAct = editorSettingsMenu.addAction( 'Auto remove trailing spaces on save' )
        removeTrailingOnSpaceAct.setCheckable( True )
        removeTrailingOnSpaceAct.setChecked( self.settings.removeTrailingOnSave )
        self.connect( removeTrailingOnSpaceAct, SIGNAL( 'changed()' ), self.__removeTrailingChanged )
        editorSettingsMenu.addSeparator()
        themesMenu = editorSettingsMenu.addMenu( "Themes" )
        availableThemes = self.__buildThemesList()
        for theme in availableThemes:
            themeAct = themesMenu.addAction( theme[ 1 ] )
            themeAct.setData( QVariant( theme[ 0 ] ) )
            if theme[ 0 ] == Settings().skinName:
                font = themeAct.font()
                font.setBold( True )
                themeAct.setFont( font )
        self.connect( themesMenu, SIGNAL( "triggered(QAction*)" ), self.__onTheme )

        editorSettingsButton = QToolButton( self )
        editorSettingsButton.setIcon( PixmapCache().getIcon( 'editorsettings.png' ) )
        editorSettingsButton.setToolTip( 'Text editor settings' )
        editorSettingsButton.setPopupMode( QToolButton.InstantPopup  )
        editorSettingsButton.setMenu( editorSettingsMenu )
        editorSettingsButton.setFocusPolicy( Qt.NoFocus )

        # Debugger buttons
        self.__dbgBreak = QAction( PixmapCache().getIcon( 'dbgbreak.png' ),
                                   'Break', self )
        self.connect( self.__dbgBreak, SIGNAL( "triggered()" ), self.__onDbgBreak )
        self.__dbgBreak.setVisible( False )
        self.__dbgGo = QAction( PixmapCache().getIcon( 'dbggo.png' ),
                                'Go', self )
        self.connect( self.__dbgGo, SIGNAL( "triggered()" ), self.__onDbgGo )
        self.__dbgGo.setVisible( False )
        self.__dbgNext = QAction( PixmapCache().getIcon( 'dbgnext.png' ),
                                  'Next', self )
        self.connect( self.__dbgNext, SIGNAL( "triggered()" ), self.__onDbgNext )
        self.__dbgNext.setVisible( False )
        self.__dbgStepInto = QAction( PixmapCache().getIcon( 'dbgstepinto.png' ),
                                      'Step into', self )
        self.connect( self.__dbgStepInto, SIGNAL( "triggered()" ), self.__onDbgStepInto )
        self.__dbgStepInto.setVisible( False )
        self.__dbgRunToLine = QAction( PixmapCache().getIcon( 'dbgruntoline.png' ),
                                       'Run to line', self )
        self.connect( self.__dbgRunToLine, SIGNAL( "triggered()" ), self.__onDbgRunToLine )
        self.__dbgRunToLine.setVisible( False )
        self.__dbgReturn = QAction( PixmapCache().getIcon( 'dbgreturn.png' ),
                                    'Return', self )
        self.connect( self.__dbgReturn, SIGNAL( "triggered()" ), self.__onDbgReturn )
        self.__dbgReturn.setVisible( False )
        self.__dbgAnalyzeExc = QAction( PixmapCache().getIcon( "dbganalyzeexc.png" ),
                                        'Analyze exception: OFF', self )
        self.__dbgAnalyzeExc.setCheckable( True )
        self.__dbgAnalyzeExc.setChecked( False )
        self.connect( self.__dbgAnalyzeExc, SIGNAL( "triggered()" ), self.__onDbgAnalyzeExc )
        self.__dbgAnalyzeExc.setVisible( False )
        self.__dbgTrapUnhandled = QAction( PixmapCache().getIcon( "dbgtrapunhandled.png" ),
                                           'Trap unhandled exception: OFF', self )
        self.__dbgTrapUnhandled.setCheckable( True )
        self.__dbgTrapUnhandled.setChecked( False )
        self.connect( self.__dbgTrapUnhandled, SIGNAL( "triggered()" ), self.__onDbgTrapUnhandled )
        self.__dbgTrapUnhandled.setVisible( False )
        self.__dbgSync = QAction( PixmapCache().getIcon( "dbgsync.png" ),
                                  'Sync mode: ON', self )
        self.__dbgSync.setCheckable( True )
        self.__dbgSync.setChecked( True )
        self.connect( self.__dbgSync, SIGNAL( "triggered()" ), self.__onDbgSync )
        self.__dbgSync.setVisible( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        toolbar = QToolBar()
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.TopToolBarArea )
        toolbar.setIconSize( QSize( 26, 26 ) )
        toolbar.addAction( self.createProjectButton )
        toolbar.addSeparator()
        toolbar.addAction( packageDiagramButton )
        toolbar.addWidget( self.importsDiagramButton )
        toolbar.addWidget( self.runProjectButton )
        toolbar.addWidget( self.debugProjectButton )
        toolbar.addAction( applicationDiagramButton )
        toolbar.addSeparator()
        toolbar.addAction( neverUsedButton )
        toolbar.addWidget( self.__pylintButton )
        toolbar.addAction( self.__pymetricsButton )
        toolbar.addAction( self.linecounterButton )
        toolbar.addSeparator()
        toolbar.addAction( self.__findInFilesButton )
        toolbar.addAction( self.__findNameButton )
        toolbar.addAction( self.__findFileButton )
        # Debugger part begin
        self.__dbgSeparator1 = toolbar.addSeparator()
        self.__dbgSeparator1.setVisible( False )
        toolbar.addAction( self.__dbgBreak )
        toolbar.addAction( self.__dbgGo )
        toolbar.addAction( self.__dbgNext )
        toolbar.addAction( self.__dbgStepInto )
        toolbar.addAction( self.__dbgRunToLine )
        toolbar.addAction( self.__dbgReturn )
        self.__dbgSeparator2 = toolbar.addSeparator()
        self.__dbgSeparator2.setVisible( False )
        toolbar.addAction( self.__dbgAnalyzeExc )
        toolbar.addAction( self.__dbgTrapUnhandled )
        toolbar.addAction( self.__dbgSync )
        # Debugger part end
        toolbar.addWidget( spacer )
        toolbar.addWidget( editorSettingsButton )

        self.addToolBar( toolbar )
        return

    def __guessMaximized( self ):
        " True if the window is maximized "

        # Ugly but I don't see any better way.
        # It is impossible to catch the case when the main window is maximized.
        # Especially when networked XServer is used (like xming)
        # So, make a wild guess instead and do not save the status is
        # maximized.
        availGeom = GlobalData().application.desktop().availableGeometry()
        if self.width() + abs( self.settings.xdelta ) > availGeom.width() or \
           self.height() + abs( self.settings.ydelta ) > availGeom.height():
            return True
        return False

    def resizeEvent( self, resizeEv ):
        " Triggered when the window is resized "
        QTimer.singleShot( 1, self.__resizeEventdelayed )
        return

    def __resizeEventdelayed( self ):
        """ Memorizes the new window size """

        if self.__initialisation:
            return
        if self.__guessMaximized():
            return

        self.settings.width = self.width()
        self.settings.height = self.height()
        self.vSplitterMoved( 0, 0 )
        self.hSplitterMoved( 0, 0 )
        return

    def moveEvent( self, moveEv ):
        " Triggered when the window is moved "
        QTimer.singleShot( 1, self.__moveEventDelayed )
        return

    def __moveEventDelayed( self ):
        """ Memorizes the new window position """

        if self.__initialisation:
            return
        if self.__guessMaximized():
            return

        self.settings.xpos = self.x()
        self.settings.ypos = self.y()
        return

    def onProjectChanged( self, what ):
        " Slot to receive projectChanged signal "

        if what == CodimensionProject.CompleteProject:
            self.updateToolbarStatus()
            self.updateWindowTitle()

            projectLoaded = GlobalData().project.isLoaded()
            self.__unloadProjectAct.setEnabled( projectLoaded )
            self.__projectPropsAct.setEnabled( projectLoaded )
            self.__findNameMenuAct.setEnabled( projectLoaded )
            self.__fileProjectFileAct.setEnabled( projectLoaded )
            self.__prjPylintAct.setEnabled( projectLoaded )
            self.__prjPymetricsAct.setEnabled( projectLoaded )
            self.__prjLineCounterAct.setEnabled( projectLoaded )
            self.__prjImportDgmAct.setEnabled( projectLoaded )
            self.__prjImportsDgmDlgAct.setEnabled( projectLoaded )

            self.settings.projectLoaded = projectLoaded
            if projectLoaded:
                editorsManager = self.editorsManagerWidget.editorsManager
                editorsManager.restoreTabs( GlobalData().project.tabsStatus )

                if os.path.exists( self.__getPylintRCFileName() ):
                    self.__pylintButton.setMenu( self.__existentPylintRCMenu )
                else:
                    self.__pylintButton.setMenu( self.__absentPylintRCMenu )
        self.updateRunDebugButtons()
        return

    def updateWindowTitle( self ):
        """ updates the main window title with the current so file """

        if GlobalData().project.fileName != "":
            self.setWindowTitle( 'Codimension for Python: ' + \
                                 os.path.basename( \
                                    GlobalData().project.fileName ) )
        else:
            self.setWindowTitle( 'Codimension for Python: no project selected' )
        return

    def updateToolbarStatus( self ):
        " Enables/disables the toolbar buttons "
        projectLoaded = GlobalData().project.isLoaded()
        self.linecounterButton.setEnabled( projectLoaded )
        self.__pylintButton.setEnabled( projectLoaded and \
                                        GlobalData().pylintAvailable )
        self.importsDiagramButton.setEnabled( projectLoaded and \
                                              GlobalData().graphvizAvailable )
        self.__pymetricsButton.setEnabled( projectLoaded )
        self.__findNameButton.setEnabled( projectLoaded )
        self.__findFileButton.setEnabled( projectLoaded )
        return

    def updateRunDebugButtons( self ):
        " Updates the run/debug buttons statuses "
        if self.debugMode:
            self.runProjectButton.setEnabled( False )
            self.runProjectButton.setToolTip( "Cannot run project - debug in progress" )
            self.debugProjectButton.setEnabled( False )
            self.debugProjectButton.setToolTip( "Cannot debug project - debug in progress" )
            return

        if not GlobalData().project.isLoaded():
            self.runProjectButton.setEnabled( False )
            self.runProjectButton.setToolTip( "Run project" )
            self.debugProjectButton.setEnabled( False )
            self.debugProjectButton.setToolTip( "Debug project" )
            return

        if not GlobalData().isProjectScriptValid():
            self.runProjectButton.setEnabled( False )
            self.runProjectButton.setToolTip( "Cannot run project - script " \
                                              "is not specified or invalid" )
            self.debugProjectButton.setEnabled( False )
            self.debugProjectButton.setToolTip( "Cannot debug project - script " \
                                                "is not specified or invalid" )
            return

        self.runProjectButton.setEnabled( True )
        self.runProjectButton.setToolTip( "Run project" )
        self.debugProjectButton.setEnabled( True )
        self.debugProjectButton.setToolTip( "Debug project" )
        return

    def linecounterButtonClicked( self ):
        " Triggered when the line counter button is clicked "
        LineCounterDialog().exec_()
        return

    def findInFilesClicked( self ):
        " Triggered when the find in files button is clicked "

        searchText = ""
        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.currentWidget().getType() in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            searchText = editorsManager.currentWidget().getEditor().getSearchText()

        dlg = FindInFilesDialog( FindInFilesDialog.inProject, searchText )
        dlg.exec_()
        if len( dlg.searchResults ) != 0:
            self.displayFindInFiles( dlg.searchRegexp, dlg.searchResults )
        return

    def toStdout( self, txt ):
        " Triggered when a new message comes "
        self.showLogTab()
        self.__logViewer.append( txt )
        return

    def toStderr( self, txt ):
        " Triggered when a new message comes "
        self.showLogTab()
        self.__logViewer.appendError( txt )
        return

    def showLogTab( self ):
        " Makes sure that the log tab is visible "
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.__logViewer )
        self.__bottomSideBar.raise_()
        return

    def openFile( self, path, lineNo ):
        " User double clicked on a file or an item in a file "
        self.editorsManagerWidget.editorsManager.openFile( path, lineNo )
        return

    def gotoInBuffer( self, uuid, lineNo ):
        " Usually needs when an item is clicked in the file outline browser "
        self.editorsManagerWidget.editorsManager.gotoInBuffer( uuid, lineNo )
        return

    def jumpToLine( self, lineNo ):
        " Usually needs when rope provided definition in the current unsaved buffer "
        self.editorsManagerWidget.editorsManager.jumpToLine( lineNo )
        return

    def openPixmapFile( self, path ):
        " User double clicked on a file "
        self.editorsManagerWidget.editorsManager.openPixmapFile( path )
        return

    def openDiagram( self, scene, tooltip ):
        " Show a generated diagram "
        self.editorsManagerWidget.editorsManager.openDiagram( scene, tooltip )
        return

    def detectTypeAndOpenFile( self, path, lineNo = -1 ):
        " Detects the file type and opens the corresponding editor / browser "
        self.openFileByType( detectFileType( path ), path, lineNo )
        return

    def openFileByType( self, fileType, path, lineNo = -1 ):
        " Opens editor/browser suitable for the file type "
        path = os.path.abspath( path )
        if not os.path.exists( path ):
            logging.error( "Cannot open " + path + ", does not exist" )
            return
        if os.path.islink( path ):
            path = os.path.realpath( path )
            if not os.path.exists( path ):
                logging.error( "Cannot open " + path + ", does not exist" )
                return
            # The type may differ...
            fileType = detectFileType( path )
        else:
            # The intermediate directory could be a link, so use the real path
            path = os.path.realpath( path )

        if not os.access( path, os.R_OK ):
            logging.error( "No read permissions to open " + path )
            return

        if not os.path.isfile( path ):
            logging.error( path + " is not a file" )
            return

        if fileType == PixmapFileType:
            self.openPixmapFile( path )
            return
        if fileType in [ ELFFileType, SOFileType, PDFFileType ]:
            logging.error( "Cannot open binary file for editing" )
            return

        self.openFile( path, lineNo )
        return

    def findWhereUsed( self, fileName, item ):
        " User requested a search where an item is used "

        logging.debug( "Where used search is requested." \
                       " Item source file: " + fileName + \
                       " Item name: " + item.name + \
                       " ItemType: " + str( type( item ) ) )
        return

    def __createNewProject( self ):
        " Create new action "

        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.closeRequest() == False:
            return

        dialog = ProjectPropertiesDialog()
        if dialog.exec_() != QDialog.Accepted:
            return

        # Request accepted
        baseDir = os.path.dirname( str( dialog.absProjectFileName ) ) + \
                  os.path.sep
        importDirs = []
        index = 0
        while index < dialog.importDirList.count():
            dirName = str( dialog.importDirList.item( index ).text() )
            if dirName.startswith( baseDir ):
                # Replace paths with relative if needed
                dirName = dirName[ len( baseDir ) : ]
                if dirName == "":
                    dirName = "."
            importDirs.append( dirName )
            index += 1

        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        prj = GlobalData().project
        prj.setTabsStatus( editorsManager.getTabsStatus() )
        editorsManager.closeAll()

        GlobalData().project.createNew( \
                        dialog.absProjectFileName,
                        str( dialog.scriptEdit.text() ).strip(),
                        importDirs,
                        str( dialog.authorEdit.text() ).strip(),
                        str( dialog.licenseEdit.text() ).strip(),
                        str( dialog.copyrightEdit.text() ).strip(),
                        str( dialog.descriptionEdit.toPlainText() ).strip(),
                        str( dialog.creationDateEdit.text() ).strip(),
                        str( dialog.versionEdit.text() ).strip(),
                        str( dialog.emailEdit.text() ).strip() )

        QApplication.restoreOverrideCursor()
        Settings().addRecentProject( dialog.absProjectFileName )
        return

    def notImplementedYet( self ):
        " Shows a dummy window "

        QMessageBox.about( self, 'Not implemented yet',
                "This function has not been implemented yet" )
        return

    def closeEvent( self, event ):
        " Triggered when the IDE is closed "
        # Save the side bars status
        self.settings.vSplitterSizes = list( self.__verticalSplitter.sizes() )
        self.settings.hSplitterSizes = list( self.__horizontalSplitter.sizes() )
        self.settings.bottomBarMinimized = self.__bottomSideBar.isMinimized()
        self.settings.leftBarMinimized = self.__leftSideBar.isMinimized()
        self.settings.rightBarMinimized = self.__rightSideBar.isMinimized()

        # Ask the editors manager to close all the editors
        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.getUnsavedCount() == 0:
            project = GlobalData().project
            if project.isLoaded():
                project.setTabsStatus( editorsManager.getTabsStatus() )
                self.settings.tabsStatus = []
            else:
                self.settings.tabsStatus = editorsManager.getTabsStatus()

        return editorsManager.closeEvent( event )

    def showPylintReport( self, reportOption, fileOrContent,
                                displayName, uuid, fileName ):
        " Passes data to the pylint viewer "

        # This is a python file, let's pylint it
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        projectDir = ""
        if GlobalData().project.isLoaded():
            projectDir = os.path.dirname( GlobalData().project.fileName ) + \
                         os.path.sep

        # Detect the project pylintrc file if so
        pylintrcFile = ""
        if projectDir != "":
            fName = projectDir + "pylintrc"
            if os.path.exists( fName ):
                pylintrcFile = fName

        try:
            if projectDir != "":
                workingDir = projectDir
            else:
                workingDir = os.getcwd()

            lint = Pylint()
            if reportOption == PylintViewer.SingleBuffer:
                # No file, it's a buffer content
                importDirs = GlobalData().getProjectImportDirs()
                if os.path.isabs( fileName ):
                    path = os.path.dirname( fileName )
                    if path not in importDirs:
                        importDirs.append( path )

                lint.analyzeBuffer( fileOrContent, pylintrcFile, importDirs,
                                    workingDir )
            else:
                # The file exists
                fNames = fileOrContent
                if type( fileOrContent ) == type( "a" ):
                    fNames = fileOrContent.split()

                importDirs = GlobalData().getProjectImportDirs()
                for fName in fNames:
                    path = os.path.dirname( fName )
                    if path not in importDirs:
                        importDirs.append( path )

                lint.analyzeFile( fileOrContent, pylintrcFile, importDirs,
                                  workingDir )

        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            return

        QApplication.restoreOverrideCursor()
        self.__pylintViewer.showReport( lint, reportOption,
                                        displayName, uuid )

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = Settings().vSplitterSizes
            splitterSizes[ 0 ] -= 200
            splitterSizes[ 1 ] += 200
            self.__verticalSplitter.setSizes( splitterSizes )

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.__pylintViewer )
        self.__bottomSideBar.raise_()
        return

    def showPymetricsReport( self, reportOption, fileOrContent,
                                   displayName, uuid ):
        " Passes data to the pymetrics viewer "

        # This is a python file, let's pylint it
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        try:
            path = os.path.dirname( os.path.abspath( sys.argv[ 0 ] ) ) + \
                   os.path.sep + "thirdparty" + os.path.sep + "pymetrics" + \
                   os.path.sep + "pymetrics.py"
            if os.path.exists( path ):
                metrics = PyMetrics( path )
            else:
                metrics = PyMetrics()
            if reportOption == PylintViewer.SingleBuffer:
                metrics.analyzeBuffer( fileOrContent )
            else:
                metrics.analyzeFile( fileOrContent )

        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            logging.info( "Note: pymetrics does not work for syntactically " \
                          "incorrect files. Please check that your files " \
                          "are OK before running pymetrics." )
            return

        QApplication.restoreOverrideCursor()
        self.__pymetricsViewer.showReport( metrics, reportOption,
                                           displayName, uuid )

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = Settings().vSplitterSizes
            splitterSizes[ 0 ] -= 200
            splitterSizes[ 1 ] += 200
            self.__verticalSplitter.setSizes( splitterSizes )

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.__pymetricsViewer )
        self.__bottomSideBar.raise_()
        return

    def showTagHelp( self, calltip, docstring ):
        " Shows a tag help "
        if calltip is None or calltip == "":
            if docstring is None or docstring == "":
                return

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.__tagHelpViewer )
        self.__bottomSideBar.raise_()

        self.__tagHelpViewer.display( calltip, docstring )
        return

    def __onPylintTooltip( self, tooltip ):
        " Updates the pylint viewer tab tooltip "
        self.__bottomSideBar.setTabToolTip( 2, tooltip )
        return

    def __onPymetricsTooltip( self, tooltip ):
        " Updates the pymetrics viewer tab tooltip "
        self.__bottomSideBar.setTabToolTip( 3, tooltip )
        return

    def getWidgetByUUID( self, uuid ):
        " Provides the widget found by the given UUID "
        return self.editorsManagerWidget.editorsManager.getWidgetByUUID( uuid )

    def getWidgetForFileName( self, fname ):
        " Provides the widget found by the given file name "
        return self.editorsManagerWidget.editorsManager.getWidgetForFileName( fname )

    def editorsManager( self ):
        " Provides the editors manager "
        return self.editorsManagerWidget.editorsManager

    @staticmethod
    def __buildPythonFilesList():
        " Builds the list of python project files "

        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        filesToProcess = []
        for item in GlobalData().project.filesList:
            if detectFileType( item ) in [ PythonFileType,
                                           Python3FileType ]:
                filesToProcess.append( item )
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        return filesToProcess

    def pylintButtonClicked( self, action ):
        " Project pylint report is requested "

        filesToProcess = self.__buildPythonFilesList()
        if len( filesToProcess ) == 0:
            logging.error( "No python files in the project" )
            return

        # This may happen only if a project is loaded, so the working
        # dir is the project dir
        projectDir = os.path.dirname( GlobalData().project.fileName ) + \
                         os.path.sep
        self.showPylintReport( PylintViewer.ProjectFiles,
                               filesToProcess,
                               "", "", projectDir )
        return

    def pymetricsButtonClicked( self ):
        " Project pymetrics report is requested "

        filesToProcess = self.__buildPythonFilesList()
        if len( filesToProcess ) == 0:
            logging.error( "No python files in the project" )
            return

        self.showPymetricsReport( PymetricsViewer.ProjectFiles,
                                  filesToProcess,
                                  "", "" )
        return

    @staticmethod
    def __getPylintRCFileName():
        " Provides the pylintrc full name "
        projectDir = os.path.dirname( GlobalData().project.fileName )
        if not projectDir.endswith( os.path.sep ):
            projectDir += os.path.sep
        return projectDir + "pylintrc"

    def __onEditPylintRC( self ):
        " Request to edit the project pylint rc "
        fileName = self.__getPylintRCFileName()
        if not os.path.exists( fileName ):
            logging.error( "Cannot find the project pylintrc (" + \
                           fileName + ")" )
            return
        self.openFile( fileName, -1 )
        return

    def __onDelPylintRC( self ):
        " Request to delete the project pylint rc "
        fileName = self.__getPylintRCFileName()
        if os.path.exists( fileName ):
            os.unlink( fileName )
        self.__pylintButton.setMenu( self.__absentPylintRCMenu )
        return

    def __onGenPylintRC( self ):
        " Request to generate the project pylintrc "
        fileName = self.__getPylintRCFileName()
        if not os.path.exists( fileName ):
            if os.system( "pylint --generate-rcfile > " + fileName ) != 0:
                logging.error( "Error generating the project pylintrc (" + \
                               fileName + ")" )
                return
        self.__pylintButton.setMenu( self.__existentPylintRCMenu )
        self.openFile( fileName, -1 )
        return

    def __onFSChanged( self, items ):
        " Update the pylint button menu if pylintrc appeared/disappeared "
        fileName = self.__getPylintRCFileName()
        for path in items:
            path = str( path )
            if path.endswith( fileName ):
                if path.startswith( '+' ):
                    self.__pylintButton.setMenu( self.__existentPylintRCMenu )
                else:
                    self.__pylintButton.setMenu( self.__absentPylintRCMenu )
            break
        return

    def displayFindInFiles( self, searchRegexp, searchResults ):
        " Displays the results on a tab "
        self.__findInFilesViewer.showReport( searchRegexp, searchResults )

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = Settings().vSplitterSizes
            splitterSizes[ 0 ] -= 200
            splitterSizes[ 1 ] += 200
            self.__verticalSplitter.setSizes( splitterSizes )

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.__findInFilesViewer )
        self.__bottomSideBar.raise_()
        return

    def findNameClicked( self ):
        " Find name dialog should come up "
        try:
            FindNameDialog().exec_()
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def findFileClicked( self ):
        " Find file dialog should come up "
        try:
            FindFileDialog().exec_()
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def hideTooltips( self ):
        " Hides all the tooltips "
        QToolTip.hideText()
        hideSearchTooltip()
        return

    def __onImportDgmTuned( self ):
        " Runs the settings dialog first "
        dlg = ImportsDiagramDialog( ImportsDiagramDialog.ProjectFiles )
        if dlg.exec_() == QDialog.Accepted:
            self.__generateImportDiagram( dlg.options )
        return

    def __onImportDgm( self, action = False ):
        " Runs the generation process "
        self.__generateImportDiagram( ImportDiagramOptions() )
        return

    def __generateImportDiagram( self, options ):
        " Show the generation progress and display the diagram "
        progressDlg = ImportsDiagramProgress( ImportsDiagramDialog.ProjectFiles,
                                              options )
        if progressDlg.exec_() == QDialog.Accepted:
            self.openDiagram( progressDlg.scene, "Generated for the project" )
        return

    def __onRunProjectSettings( self ):
        " Brings up the dialog with run script settings "
        if self.__checkProjectScriptValidity() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        params = GlobalData().getRunParameters( fileName )
        termType = Settings().terminalType
        dlg = RunDialog( fileName, params, termType, "Run" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType
            self.__onRunProject()
        return

    def __onDebugProjectSettings( self ):
        " Brings up the dialog with debug script settings "
        if self.__checkDebugPrerequisites() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        params = GlobalData().getRunParameters( fileName )
        termType = Settings().terminalType
        dlg = RunDialog( fileName, params, termType, "Debug" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType
            self.__onDebugProject()
        return

    def __onRunProject( self, action = False ):
        " Runs the project with saved sattings "
        if self.__checkProjectScriptValidity() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        params = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv( fileName, params,
                                                     Settings().terminalType )

        try:
            Popen( cmd, shell = True,
                   cwd = workingDir, env = environment )
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def __onDebugProject( self, action = False ):
        " Debugging is requested "
        if self.__checkDebugPrerequisites() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        params = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv( fileName, params,
                                                     Settings().terminalType )
        self.switchDebugMode( True )
        self.__debugger.startDebugging()
        return

    def __checkDebugPrerequisites( self ):
        " Returns True if should continue "
        if self.__checkProjectScriptValidity() == False:
            return False

        editorsManager = self.editorsManagerWidget.editorsManager
        modifiedFiles = editorsManager.getModifiedList( True )
        if len( modifiedFiles ) == 0:
            return True

        dlg = ModifiedUnsavedDialog( modifiedFiles, "Save and debug" )
        if dlg.exec_() != QDialog.Accepted:
            # Selected to cancel
            return False

        # Need to save the modified project files
        return editorsManager.saveModified( True )

    def __checkProjectScriptValidity( self ):
        " Checks and logs error message if so. Returns True if all is OK "
        if not GlobalData().isProjectScriptValid():
            self.updateRunDebugButtons()
            logging.error( "Invalid project script. " \
                           "Use project properties dialog to " \
                           "select existing python script." )
            return False
        return True

    def __verticalEdgeChanged( self ):
        self.settings.verticalEdge = not self.settings.verticalEdge
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __showSpacesChanged( self ):
        self.settings.showSpaces = not self.settings.showSpaces
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __lineWrapChanged( self ):
        self.settings.lineWrap = not self.settings.lineWrap
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __showEOLChanged( self ):
        self.settings.showEOL = not self.settings.showEOL
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __showBraceMatchChanged( self ):
        self.settings.showBraceMatch = not self.settings.showBraceMatch
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __autoIndentChanged( self ):
        self.settings.autoIndent = not self.settings.autoIndent
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __backspaceUnindentChanged( self ):
        self.settings.backspaceUnindent = not self.settings.backspaceUnindent
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __tabIndentsChanged( self ):
        self.settings.tabIndents = not self.settings.tabIndents
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __indentationGuidesChanged( self ):
        self.settings.indentationGuides = not self.settings.indentationGuides
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __currentLineVisibleChanged( self ):
        self.settings.currentLineVisible = not self.settings.currentLineVisible
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __homeToFirstNonSpaceChanged( self ):
        self.settings.jumpToFirstNonSpace = not self.settings.jumpToFirstNonSpace
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __removeTrailingChanged( self ):
        self.settings.removeTrailingOnSave = not self.settings.removeTrailingOnSave
        return

    @staticmethod
    def __buildThemesList():
        " Builds a list of themes - system wide and the user local "

        result = []
        localSkinsDir = os.path.normpath( str( QDir.homePath() ) ) + \
                        os.path.sep + ".codimension" + os.path.sep + "skins" + \
                        os.path.sep
        for item in os.listdir( localSkinsDir ):
            if os.path.isdir( localSkinsDir + item ):
                # Seems to be a skin dir
                if not os.path.exists( localSkinsDir + item + os.path.sep + "application.css" ) or \
                   not os.path.exists( localSkinsDir + item + os.path.sep + "general" ) or \
                   not os.path.exists( localSkinsDir + item + os.path.sep + "lexers" ):
                    continue
                # Get the theme display name from the general file
                config = ConfigParser.ConfigParser()
                try:
                    config.read( [ localSkinsDir + item + os.path.sep + "general" ] )
                    displayName = config.get( 'general', 'name' )
                except:
                    continue

                result.append( [ item, displayName ] )

        # Add the installed names unless the same dirs have been already copied
        # to the user local dir
        srcDir = os.path.dirname( os.path.realpath( sys.argv[0] ) )
        skinsDir = srcDir + os.path.sep + "skins" + os.path.sep
        for item in os.listdir( skinsDir ):
            if os.path.isdir( skinsDir + item ):
                # Seems to be a skin dir
                if not os.path.exists( skinsDir + item + os.path.sep + "application.css" ) or \
                   not os.path.exists( skinsDir + item + os.path.sep + "general" ) or \
                   not os.path.exists( skinsDir + item + os.path.sep + "lexers" ):
                    continue
                # Check if this name alrady added
                found = False
                for theme in result:
                    if theme[ 0 ] == item:
                        found = True
                        break
                if found:
                    continue

                # Get the theme display name from the general file
                config = ConfigParser.ConfigParser()
                try:
                    config.read( [ skinsDir + item + os.path.sep + "general" ] )
                    displayName = config.get( 'general', 'name' )
                except:
                    continue

                result.append( [ item, displayName ] )

        return result

    def __onTheme( self, act ):
        " Triggers when a theme is selected "
        skinSubdir = str( act.data().toString() )
        if Settings().skinName == skinSubdir:
            return

        logging.info( "Please restart codimension to apply the new theme" )
        Settings().skinName = skinSubdir
        return

    def showStatusBarMessage( self, msg, timeout = 10000 ):
        " Shows a temporary status bar message, default 10sec "
        self.statusBar().showMessage( msg, timeout )
        return

    def checkOutsideFileChanges( self ):
        " Checks if there are changes in the files currently loaded by codimension "
        self.editorsManagerWidget.editorsManager.checkOutsideFileChanges()
        return

    def __onPathLabelDoubleClick( self ):
        " Double click on the status bar path label "
        txt = str( self.sbFile.getPath() )
        if txt.startswith( "File: " ):
            txt = txt.replace( "File: ", "" )
        if txt not in [ "", "N/A" ]:
            QApplication.clipboard().setText( txt )
        return

    def __showPathLabelContextMenu( self, pos ):
        " Triggered when a context menu is requested for the path label "
        contextMenu = QMenu( self )
        contextMenu.addAction( PixmapCache().getIcon( "copytoclipboard.png" ),
                               "Copy path to clipboard",
                               self.__onPathLabelDoubleClick )
        contextMenu.popup( self.sbFile.mapToGlobal( pos ) )
        return

    def updateDebuggerState( self, state ):
        " Updates the debugger state label "
        self.dbgState.setText( "Debugger state: " + state )
        return

    def switchDebugMode( self, newState ):
        " Switches the debug mode to the desired "
        if self.debugMode == newState:
            return

        self.debugMode = newState

        # Satatus bar
        self.dbgState.setVisible( newState )
        self.sbLanguage.setVisible( not newState )
        self.sbEncoding.setVisible( not newState )
        self.sbEol.setVisible( not newState )
        self.sbWritable.setVisible( not newState )

        # Toolbar buttons
        self.createProjectButton.setEnabled( not newState )
        self.__dbgSeparator1.setVisible( newState )
        self.__dbgBreak.setVisible( newState )
        self.__dbgGo.setVisible( newState )
        self.__dbgNext.setVisible( newState )
        self.__dbgStepInto.setVisible( newState )
        self.__dbgRunToLine.setVisible( newState )
        self.__dbgReturn.setVisible( newState )
        self.__dbgSeparator2.setVisible( newState )
        self.__dbgAnalyzeExc.setVisible( newState )
        self.__dbgTrapUnhandled.setVisible( newState )
        self.__dbgSync.setVisible( newState )
        self.updateRunDebugButtons()

        # Tabs at the bottom
        self.__bottomSideBar.setTabEnabled( 6, newState )   # console
        if newState == True:
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.__debuggerConsole )
            self.__bottomSideBar.raise_()

        # Tabs at the right
        self.__rightSideBar.setTabEnabled( 1, newState )    # vars etc.
        if newState == True:
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.__debuggerContext )
            self.__rightSideBar.raise_()

        self.emit( SIGNAL( 'debugModeChanged' ), newState )
        return

    def __onDbgBreak( self ):
        pass
    def __onDbgGo( self ):
        pass
    def __onDbgNext( self ):
        pass
    def __onDbgStepInto( self ):
        pass
    def __onDbgRunToLine( self ):
        pass
    def __onDbgReturn( self ):
        pass

    def __onDbgAnalyzeExc( self ):
        if self.__dbgAnalyzeExc.isChecked():
            switch = 'ON'
        else:
            switch = 'OFF'
        self.__dbgAnalyzeExc.setToolTip( 'Analyze exception: ' + switch )
        return

    def __onDbgTrapUnhandled( self ):
        self.setDbgTrapUnhandledState( self.__dbgTrapUnhandled.isChecked() )
        return

    def setDbgTrapUnhandledState( self, state ):
        " Changes the button state and tooltip "
        if state:
            switch = 'ON'
            self.__dbgAnalyzeExc.setChecked( True )
        else:
            switch = 'OFF'
            self.__dbgAnalyzeExc.setChecked( False )
        self.__dbgTrapUnhandled.setToolTip( 'Trap unhandled exception: ' + \
                                            switch )
        return

    def __onDbgSync( self ):
        if self.__dbgSync.isChecked():
            switch = 'ON'
        else:
            switch = 'OFF'
        self.__dbgSync.setToolTip( 'Sync mode: ' + switch )
        return

    def __openProject( self ):
        " Shows up a dialog to open a project "
        dialog = QFileDialog( self, 'Open project' )
        dialog.setFileMode( QFileDialog.ExistingFile )
        dialog.setNameFilter( "Codimension project files (*.cdm)" )
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        dialog.setDirectory( QDir.homePath() )
        dialog.setSidebarUrls( urls )

        if dialog.exec_() != QDialog.Accepted:
            return

        fileNames = dialog.selectedFiles()
        fileName = os.path.realpath( str( fileNames[0] ) )
        if fileName == GlobalData().project.fileName:
            logging.warning( "The selected project to load is " \
                             "the currently loaded one." )
            return

        if detectFileType( fileName ) != CodimensionProjectFileType:
            logging.warning( "Codimension project file must have .cdm extension" )
            return

        self.__loadProject( fileName )
        return

    def __loadProject( self, projectFile ):
        " Loads the given project "
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.closeRequest():
            prj = GlobalData().project
            prj.setTabsStatus( editorsManager.getTabsStatus() )
            editorsManager.closeAll()
            prj.loadProject( projectFile )
        QApplication.restoreOverrideCursor()
        return

    def __openFile( self ):
        " Triggers when Ctrl+O is pressed "

        dialog = QFileDialog( self, 'Open file' )
        dialog.setFileMode( QFileDialog.ExistingFile )
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        project = GlobalData().project
        if project.isLoaded():
            dialog.setDirectory( project.getProjectDir() )
            urls.append( QUrl.fromLocalFile( project.getProjectDir() ) )
        else:
            # There is no project loaded
            dialog.setDirectory( QDir.homePath() )
        dialog.setSidebarUrls( urls )

        if dialog.exec_() != QDialog.Accepted:
            return

        fileNames = dialog.selectedFiles()
        fileName = os.path.realpath( str( fileNames[0] ) )

        fileType = detectFileType( fileName )
        editorsManager = self.editorsManagerWidget.editorsManager

        if fileType == PixmapFileType:
            editorsManager.openPixmapFile( fileName )
        # Just a few file types
        elif fileType in [ SOFileType, ELFFileType,
                           PDFFileType, PythonCompiledFileType ] or \
             fileName.endswith( ".bz2" ) or fileName.endswith( ".zip" ) or \
             fileName.endswith( ".tar" ):
            logging.warning( "No viewer for binary files is available" )
        else:
            editorsManager.openFile( fileName, -1 )
        return

    def __isPlainTextBuffer( self ):
        " Provides if saving is enabled "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == \
                    MainWindowTabWidgetBase.PlainTextEditor

    def __isPythonBuffer( self ):
        " True if the current tab is a python buffer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == \
                MainWindowTabWidgetBase.PlainTextEditor and \
               detectFileType( currentWidget.getShortName() ) \
                          in [ PythonFileType, Python3FileType ]

    def __isGraphicsBuffer( self ):
        " True if is pictures viewer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.PictureViewer

    def __onTabImportDgm( self ):
        " Triggered when tab imports diagram is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onImportDgm()
        return

    def __onTabImportDgmTuned( self ):
        " Triggered when tuned tab imports diagram is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onImportDgmTuned()
        return

    def __onRunTab( self ):
        " Triggered when run tab script is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onRunScript()
        return

    def __onRunTabDlg( self ):
        " Triggered when run tab script dialog is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onRunScriptSettings()
        return

    def __onContextHelp( self ):
        " Triggered when Ctrl+F1 is clicked "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onTagHelp()
        return

    def __onHomePage( self ):
        " Triggered when opening the home page is requested "
        QDesktopServices.openUrl( QUrl( "http://satsky.spb.ru/codimension/" ) )
        return

    def __onAllShortcurs( self ):
        " Triggered when opening key bindings page is requested"
        QDesktopServices.openUrl( QUrl( "http://satsky.spb.ru/codimension/keyBindingsEng.php" ) )
        return

    def __activateSideTab( self, act ):
        " Triggered when a side bar should be activated "
        name = str( act.data().toString() )
        if name == "prj":
            self.__leftSideBar.show()
            self.__leftSideBar.setCurrentWidget( self.projectViewer )
            self.__leftSideBar.raise_()
        elif name == "recent":
            self.__leftSideBar.show()
            self.__leftSideBar.setCurrentWidget( self.recentProjectsViewer )
            self.__leftSideBar.raise_()
        elif name == "classes":
            self.__leftSideBar.show()
            self.__leftSideBar.setCurrentWidget( self.classesViewer )
            self.__leftSideBar.raise_()
        elif name == "funcs":
            self.__leftSideBar.show()
            self.__leftSideBar.setCurrentWidget( self.functionsViewer )
            self.__leftSideBar.raise_()
        elif name == "globs":
            self.__leftSideBar.show()
            self.__leftSideBar.setCurrentWidget( self.globalsViewer )
            self.__leftSideBar.raise_()
        elif name == "outline":
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.__outlineViewer )
            self.__rightSideBar.raise_()
        elif name == "log":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.__logViewer )
            self.__bottomSideBar.raise_()
        elif name == "pylint":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.__pylintViewer )
            self.__bottomSideBar.raise_()
        elif name == "pymetrics":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.__pymetricsViewer )
            self.__bottomSideBar.raise_()
        elif name == "search":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.__findInFilesViewer )
            self.__bottomSideBar.raise_()
        elif name == "contexthelp":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.__tagHelpViewer )
            self.__bottomSideBar.raise_()
        return

    def __onTabPylint( self ):
        " Triggered when pylint for the current tab is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onPylint()
        return

    def __onTabPymetrics( self ):
        " Triggered when pymetrics for the current tab is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onPymetrics()
        return

    def __onTabLineCounter( self ):
        " Triggered when line counter for the current buffer is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onLineCounter()
        return

    def __onTabJumpToDef( self ):
        " Triggered when jump to defenition is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onGotoDefinition()
        return

    def __onTabJumpToScopeBegin( self ):
        " Triggered when jump to the beginning of the current scope is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onScopeBegin()
        return

    def __onFindOccurences( self ):
        " Triggered when search for occurences is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onOccurances()
        return

    def __onTabOpenImport( self ):
        " Triggered when open import is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onOpenImport()
        return

    def __onOpenAsFile( self ):
        " Triggered when open as file is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().openAsFile()
        return

    def __onUndo( self ):
        " Triggered when undo action is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onUndo()
        return

    def __onRedo( self ):
        " Triggered when redo action is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onRedo()
        return

    def __onZoomIn( self ):
        " Triggered when zoom in is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.zoomIn()
        return

    def __onZoomOut( self ):
        " Triggered when zoom out is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.zoomOut()
        return

    def __onZoomReset( self ):
        " Triggered when zoom 1:1 is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.zoomReset()
        return

    def __onGoToLine( self ):
        " Triggered when go to line is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onGoto()
        return

    def __onCut( self ):
        " Triggered when cut is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onShiftDel()
        return

    def __onPaste( self ):
        " Triggered when paste is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().paste()
        return

    def __onSelectAll( self ):
        " Triggered when select all is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().selectAll()
        return

    def __onComment( self ):
        " Triggered when comment/uncomment is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onCommentUncomment()
        return

    def __onDuplicate( self ):
        " Triggered when duplicate line is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().duplicateLine()
        return

    def __onAutocomplete( self ):
        " Triggered when autocomplete is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onAutoComplete()
        return

    def __onFind( self ):
        " Triggered when find is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onFind()
        return

    def __onFindCurrent( self ):
        " Triggered when find of the current identifier is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onHiddenFind()
        return

    def __onReplace( self ):
        " Triggered when replace is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onReplace()
        return

    def __onFindNext( self ):
        " Triggered when find next is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.findNext()
        return

    def __onFindPrevious( self ):
        " Triggered when find previous is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.findPrev()
        return

    def __onExpandTabs( self ):
        " Triggered when tabs expansion is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onExpandTabs()
        return

    def __onRemoveTrailingSpaces( self ):
        " Triggered when trailing spaces removal is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onRemoveTrailingWS()
        return

    def __editAboutToShow( self ):
        " Triggered when edit menu is about to show "
        isPlainBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if isPlainBuffer:
            editor = currentWidget.getEditor()

        self.__undoAct.setShortcut( "Ctrl+Z" )
        self.__undoAct.setEnabled( isPlainBuffer and editor.isUndoAvailable() )
        self.__redoAct.setShortcut( "Ctrl+Shift+Z" )
        self.__redoAct.setEnabled( isPlainBuffer and editor.isRedoAvailable() )
        self.__cutAct.setShortcut( "Ctrl+X" )
        self.__cutAct.setEnabled( isPlainBuffer )
        self.__copyAct.setShortcut( "Ctrl+C" )
        self.__copyAct.setEnabled( editorsManager.isCopyAvailable() )
        self.__pasteAct.setShortcut( "Ctrl+V" )
        self.__pasteAct.setEnabled( isPlainBuffer and \
                                    QApplication.clipboard().text() != "" )
        self.__selectAllAct.setShortcut( "Ctrl+A" )
        self.__selectAllAct.setEnabled( isPlainBuffer )
        self.__commentAct.setShortcut( "Ctrl+M" )
        self.__commentAct.setEnabled( isPythonBuffer )
        self.__duplicateAct.setShortcut( "Ctrl+D" )
        self.__duplicateAct.setEnabled( isPlainBuffer )
        self.__autocompleteAct.setShortcut( "Ctrl+Space" )
        self.__autocompleteAct.setEnabled( isPlainBuffer )
        self.__expandTabsAct.setEnabled( isPlainBuffer )
        self.__trailingSpacesAct.setEnabled( isPlainBuffer )
        return

    def __tabAboutToShow( self ):
        " Triggered when tab menu is about to show "
        plainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        editorsManager = self.editorsManagerWidget.editorsManager

        self.__cloneTabAct.setEnabled( plainTextBuffer )
        self.__closeOtherTabsAct.setEnabled( editorsManager.closeOtherAvailable() )
        self.__saveFileAct.setEnabled( plainTextBuffer )
        self.__saveFileAsAct.setEnabled( plainTextBuffer )
        self.__closeTabAct.setEnabled( editorsManager.isTabClosable() )
        self.__tabJumpToDefAct.setEnabled( isPythonBuffer )
        self.__tabJumpToScopeBeginAct.setEnabled( isPythonBuffer )
        self.__tabOpenImportAct.setEnabled( isPythonBuffer )
        if plainTextBuffer:
            widget = editorsManager.currentWidget()
            available = widget.getEditor().openAsFileAvailable()
            self.__openAsFileAct.setEnabled( available )
        else:
            self.__openAsFileAct.setEnabled( False )

        self.__closeTabAct.setShortcut( "Ctrl+F4" )
        self.__tabJumpToDefAct.setShortcut( "Ctrl+\\" )
        self.__tabJumpToScopeBeginAct.setShortcut( "Alt+U" )
        self.__tabOpenImportAct.setShortcut( "Ctrl+I" )

        self.__recentFilesMenu.clear()
        addedCount = 0

        for item in GlobalData().project.recentFiles:
            addedCount += 1
            act = self.__recentFilesMenu.addAction( \
                                self.__getAccelerator( addedCount ) + \
                                item )
            act.setData( QVariant( item ) )

        self.__recentFilesMenu.setEnabled( addedCount > 0 )
        return

    def __searchAboutToShow( self ):
        " Triggered when search menu is about to show "
        isPlainTextBuffer = self.__isPlainTextBuffer()
        self.__findOccurencesAct.setEnabled( self.__isPythonBuffer() )
        self.__goToLineAct.setEnabled( isPlainTextBuffer )
        self.__findAct.setEnabled( isPlainTextBuffer )
        self.__findCurrentAct.setEnabled( isPlainTextBuffer )
        self.__replaceAct.setEnabled( isPlainTextBuffer )
        self.__findNextAct.setEnabled( isPlainTextBuffer )
        self.__findPrevAct.setEnabled( isPlainTextBuffer )

        self.__findOccurencesAct.setShortcut( "Ctrl+]" )
        self.__goToLineAct.setShortcut( "Ctrl+G" )
        self.__findAct.setShortcut( "Ctrl+F" )
        self.__findCurrentAct.setShortcut( "Ctrl+F3" )
        self.__replaceAct.setShortcut( "Ctrl+R" )
        self.__findNextAct.setShortcut( "F3" )
        self.__findPrevAct.setShortcut( "Shift+F3" )
        return

    def __diagramsAboutToShow( self ):
        " Triggered when the diagrams menu is about to show "
        isPythonBuffer = self.__isPythonBuffer()
        self.__tabImportDgmAct.setEnabled( isPythonBuffer )
        self.__tabImportDgmDlgAct.setEnabled( isPythonBuffer )
        return

    def __runAboutToShow( self ):
        " Triggered when the run menu is about to show "
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()
        isPythonBuffer = self.__isPythonBuffer()

        self.__prjRunAct.setEnabled( projectLoaded and prjScriptValid )
        self.__prjRunDlgAct.setEnabled( projectLoaded and prjScriptValid )
        self.__tabRunAct.setEnabled( isPythonBuffer )
        self.__tabRunDlgAct.setEnabled( isPythonBuffer )
        return

    def __toolsAboutToShow( self ):
        " Triggered when tools menu is about to show "
        isPythonBuffer = self.__isPythonBuffer()
        projectLoaded = GlobalData().project.isLoaded()
        self.__tabPylintAct.setEnabled( isPythonBuffer )
        self.__tabPymetricsAct.setEnabled( isPythonBuffer )
        self.__tabLineCounterAct.setEnabled( isPythonBuffer )

        if projectLoaded:
            rcExists = os.path.exists( self.__getPylintRCFileName() )
            self.__prjGenPylintrcAct.setEnabled( not rcExists )
            self.__prjEditPylintrcAct.setEnabled( rcExists )
            self.__prjDelPylintrcAct.setEnabled( rcExists )
        else:
            self.__prjGenPylintrcAct.setEnabled( False )
            self.__prjEditPylintrcAct.setEnabled( False )
            self.__prjDelPylintrcAct.setEnabled( False )

        self.__tabPylintAct.setShortcut( "Ctrl+L" )
        self.__tabPymetricsAct.setShortcut( "Ctrl+K" )
        return

    def __viewAboutToShow( self ):
        " Triggered when view menu is about to show "
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isGraphicsBuffer = self.__isGraphicsBuffer()
        self.__zoomInAct.setEnabled( isPlainTextBuffer or isGraphicsBuffer )
        self.__zoomOutAct.setEnabled( isPlainTextBuffer or isGraphicsBuffer )
        self.__zoom11Act.setEnabled( isPlainTextBuffer or isGraphicsBuffer )

        self.__zoomInAct.setShortcut( "Ctrl++" )
        self.__zoomOutAct.setShortcut( "Ctrl+-" )
        self.__zoom11Act.setShortcut( "Ctrl+0" )
        return

    def __helpAboutToShow( self ):
        " Triggered when help menu is about to show "
        self.__contextHelpAct.setEnabled( self.__isPythonBuffer() )

        self.__contextHelpAct.setShortcut( "Ctrl+F1" )
        return

    def __editAboutToHide( self ):
        " Triggered when edit menu is about to hide "
        self.__undoAct.setShortcut( "" )
        self.__redoAct.setShortcut( "" )
        self.__cutAct.setShortcut( "" )
        self.__copyAct.setShortcut( "" )
        self.__pasteAct.setShortcut( "" )
        self.__selectAllAct.setShortcut( "" )
        self.__commentAct.setShortcut( "" )
        self.__duplicateAct.setShortcut( "" )
        self.__autocompleteAct.setShortcut( "" )
        return

    def __tabAboutToHide( self ):
        " Triggered when tab menu is about to hide "
        self.__closeTabAct.setShortcut( "" )
        self.__tabJumpToDefAct.setShortcut( "" )
        self.__tabJumpToScopeBeginAct.setShortcut( "" )
        self.__tabOpenImportAct.setShortcut( "" )
        return

    def __searchAboutToHide( self ):
        " Triggered when search menu is about to hide "
        self.__findOccurencesAct.setShortcut( "" )
        self.__goToLineAct.setShortcut( "" )
        self.__findAct.setShortcut( "" )
        self.__findCurrentAct.setShortcut( "" )
        self.__replaceAct.setShortcut( "" )
        self.__findNextAct.setShortcut( "" )
        self.__findPrevAct.setShortcut( "" )
        return

    def __toolsAboutToHide( self ):
        " Triggered when tools menu is about to hide "
        self.__tabPylintAct.setShortcut( "" )
        self.__tabPymetricsAct.setShortcut( "" )
        return

    def __viewAboutToHide( self ):
        " Triggered when view menu is about to hide "
        self.__zoomInAct.setShortcut( "" )
        self.__zoomOutAct.setShortcut( "" )
        self.__zoom11Act.setShortcut( "" )
        return

    def __helpAboutToHide( self ):
        " Triggered when help menu is about to hide "
        self.__contextHelpAct.setShortcut( "" )
        return

    def __getAccelerator( self, count ):
        " Provides an accelerator text for a menu item "
        if count < 10:
            return "&" + str( count ) + ".  "
        return "&" + chr( count - 10 + ord( 'a' ) ) + ".  "

    def __prjAboutToShow( self ):
        " Triggered when recent projects submenu is about to show "
        self.__recentPrjMenu.clear()
        addedCount = 0

        currentPrj = GlobalData().project.fileName
        for item in Settings().recentProjects:
            if item == currentPrj:
                continue
            addedCount += 1
            act = self.__recentPrjMenu.addAction( \
                                self.__getAccelerator( addedCount ) + \
                                os.path.basename( item ).replace( ".cdm", "" ) )
            act.setData( QVariant( item ) )

        self.__recentPrjMenu.setEnabled( addedCount > 0 )
        return

    def __onRecentPrj( self, act ):
        " Triggered when a recent project is requested to be loaded "
        path = str( act.data().toString() )
        self.__loadProject( path )
        return

    def __onRecentFile( self, act ):
        " Triggered when a recent file is requested to be loaded "
        path = str( act.data().toString() )
        fileType = detectFileType( path )
        if fileType == PixmapFileType:
            self.openPixmapFile( path )
            return
        self.openFile( path, -1 )
        return

