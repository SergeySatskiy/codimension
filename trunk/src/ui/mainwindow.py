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

import os.path, sys, logging, ConfigParser, gc
from PyQt4.QtCore import SIGNAL, Qt, QSize, QTimer, QDir, QVariant, QUrl
from PyQt4.QtGui import ( QLabel, QToolBar, QWidget, QMessageBox, QFont,
                          QVBoxLayout, QSplitter, QSizePolicy,
                          QAction, QMainWindow, QShortcut, QFrame,
                          QApplication, QCursor, QMenu, QToolButton,
                          QToolTip, QPalette, QColor, QFileDialog, QDialog,
                          QDesktopServices, QStyleFactory, QActionGroup )
from fitlabel import FitPathLabel
from utils.globals import GlobalData
from utils.project import CodimensionProject
from utils.misc import ( getDefaultTemplate, getIDETemplateFile,
                         getProjectTemplateFile, getIDEPylintFile )
from sidebar import SideBar
from logviewer import LogViewer
from taghelpviewer import TagHelpViewer
from todoviewer import TodoViewer
from redirector import Redirector
from utils.pixmapcache import PixmapCache
from functionsviewer import FunctionsViewer
from globalsviewer import GlobalsViewer
from classesviewer import ClassesViewer
from recentprojectsviewer import RecentProjectsViewer
from projectviewer import ProjectViewer
from outline import FileOutlineViewer
from pyflakesviewer import PyflakesViewer
from editorsmanager import EditorsManager
from linecounter import LineCounterDialog
from projectproperties import ProjectPropertiesDialog
from utils.settings import thirdpartyDir
from findreplacewidget import FindWidget, ReplaceWidget
from gotolinewidget import GotoLineWidget
from pylintviewer import PylintViewer
from pylintparser.pylintparser import Pylint
from utils.fileutils import ( PythonFileType, Python3FileType, detectFileType,
                              PixmapFileType, CodimensionProjectFileType,
                              closeMagicLibrary, isFileTypeSearchable )
from pymetricsviewer import PymetricsViewer
from pymetricsparser.pymetricsparser import PyMetrics
from findinfiles import FindInFilesDialog
from findinfilesviewer import FindInFilesViewer, hideSearchTooltip
from findname import FindNameDialog
from findfile import FindFileDialog
from mainwindowtabwidgetbase import MainWindowTabWidgetBase
from diagram.importsdgm import ( ImportsDiagramDialog, ImportsDiagramProgress,
                                 ImportDiagramOptions )
from runparams import RunDialog
from utils.run import ( getWorkingDir,
                        parseCommandLineArguments, getNoArgsEnvironment,
                        TERM_AUTO, TERM_KONSOLE, TERM_GNOME, TERM_XTERM,
                        TERM_REDIRECT )
from debugger.context import DebuggerContext
from debugger.modifiedunsaved import ModifiedUnsavedDialog
from debugger.server import CodimensionDebugger
from debugger.excpt import DebuggerExceptions
from debugger.bpwp import DebuggerBreakWatchPoints
from diffviewer import DiffViewer
from thirdparty.diff2html.diff2html import parse_from_memory
from analysis.notused import NotUsedAnalysisProgress
from autocomplete.completelists import getOccurrences
from findinfiles import ItemToSearchIn, getSearchItemIndex
from profiling.profui import ProfilingProgressDialog
from profiling.disasm import getDisassembled
from debugger.bputils import clearValidBreakpointLinesCache
from about import AboutDialog
from utils.skin import getMonospaceFontList
from plugins.manager.pluginmanagerdlg import PluginsDialog
from plugins.vcssupport.vcsmanager import VCSManager
from plugins.vcssupport.intervaldlg import VCSUpdateIntervalConfigDialog
from utils.fileutils import MAGIC_AVAILABLE
from statusbarslots import StatusBarSlots
from editor.redirectedioconsole import IOConsoleTabWidget
from runmanager import RunManager



class EditorsManagerWidget( QWidget ):
    " Tab widget which has tabs with editors and viewers "

    def __init__( self, parent, debugger ):

        QWidget.__init__( self, parent )

        self.editorsManager = EditorsManager( parent, debugger )
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

    DEBUG_ACTION_GO = 1
    DEBUG_ACTION_NEXT = 2
    DEBUG_ACTION_STEP_INTO = 3
    DEBUG_ACTION_RUN_TO_LINE = 4
    DEBUG_ACTION_STEP_OUT = 5

    def __init__( self, splash, settings ):
        QMainWindow.__init__( self )

        self.debugMode = False
        # Last position the IDE received control from the debugger
        self.__lastDebugFileName = None
        self.__lastDebugLineNumber = None
        self.__lastDebugAsException = None
        self.__lastDebugAction = None
        self.__newRunIndex = -1
        self.__newProfileIndex = -1

        self.vcsManager = VCSManager()

        self.__debugger = CodimensionDebugger( self )
        self.connect( self.__debugger, SIGNAL( "DebuggerStateChanged" ),
                      self.__onDebuggerStateChanged )
        self.connect( self.__debugger, SIGNAL( 'ClientLine' ),
                      self.__onDebuggerCurrentLine )
        self.connect( self.__debugger, SIGNAL( 'ClientException' ),
                      self.__onDebuggerClientException )
        self.connect( self.__debugger, SIGNAL( 'ClientSyntaxError' ),
                      self.__onDebuggerClientSyntaxError )
        self.connect( self.__debugger, SIGNAL( 'ClientIDEMessage' ),
                      self.__onDebuggerClientIDEMessage )
        self.connect( self.__debugger.getBreakPointModel(),
                      SIGNAL( 'BreakpoinsChanged' ),
                      self.__onBreakpointsModelChanged )
        self.connect( self.__debugger, SIGNAL( 'EvalOK' ),
                      self.__onEvalOK )
        self.connect( self.__debugger, SIGNAL( 'EvalError' ),
                      self.__onEvalError )
        self.connect( self.__debugger, SIGNAL( 'ExecOK' ),
                      self.__onExecOK )
        self.connect( self.__debugger, SIGNAL( 'ExecError' ),
                      self.__onExecError )
        self.connect( self.__debugger, SIGNAL( 'ClientStdout' ),
                      self.__onClientStdout )
        self.connect( self.__debugger, SIGNAL( 'ClientStderr' ),
                      self.__onClientStderr )
        self.connect( self.__debugger, SIGNAL( 'ClientRawInput' ),
                      self.__onClientRawInput )

        self.settings = settings
        self.__initialisation = True

        # This prevents context menu on the main window toolbar.
        # I don't really know why but it is what I need
        self.setContextMenuPolicy( Qt.NoContextMenu )

        # The size restore is done twice to avoid huge flickering
        # This one is approximate, the one in restoreWindowPosition() is precise
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != settings.screenwidth or \
           screenSize.height() != settings.screenheight:
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
        self.__horizontalSplitterSizes = list( settings.hSplitterSizes )
        self.__verticalSplitterSizes = list( settings.vSplitterSizes )

        self.logViewer = None
        self.redirectedIOConsole = None
        self.__createLayout()

        splash.showMessage( "Initializing main menu bar..." )
        self.__initPluginSupport()
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

        self.__runManager = RunManager( self )
        return

    def restoreWindowPosition( self ):
        " Makes sure that the window frame delta is proper "
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != self.settings.screenwidth or \
           screenSize.height() != self.settings.screenheight:
            # The screen resolution has been changed, save the new values
            self.settings.screenwidth = screenSize.width()
            self.settings.screenheight = screenSize.height()
            self.settings.xdelta = self.settings.xpos - self.x()
            self.settings.ydelta = self.settings.ypos - self.y()
            self.settings.xpos = self.x()
            self.settings.ypos = self.y()
        else:
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

    def __createLayout( self ):
        """ creates the UI layout """

        self.editorsManagerWidget = EditorsManagerWidget( self, self.__debugger )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'TabRunChanged' ),
                      self.setDebugTabAvailable )

        self.editorsManagerWidget.findWidget.hide()
        self.editorsManagerWidget.replaceWidget.hide()
        self.editorsManagerWidget.gotoLineWidget.hide()

        # The layout is a sidebar-style one
        self.__bottomSideBar = SideBar( SideBar.South, self )
        self.__leftSideBar   = SideBar( SideBar.West, self )
        self.__rightSideBar = SideBar( SideBar.East, self )

        # Create tabs on bars
        self.logViewer = LogViewer()
        self.__bottomSideBar.addTab( self.logViewer,
                                     PixmapCache().getIcon( 'logviewer.png' ),
                                     'Log' )
        self.connect( sys.stdout, SIGNAL( 'appendToStdout(QString)' ), self.toStdout )
        self.connect( sys.stderr, SIGNAL( 'appendToStderr(QString)' ), self.toStderr )

        # replace logging streamer to self.stdout
        logging.root.handlers = []
        handler = logging.StreamHandler( sys.stdout )
        handler.setFormatter(
            logging.Formatter( "%(levelname) -10s %(asctime)s %(message)s",
            None ) )
        logging.root.addHandler( handler )


        self.projectViewer = ProjectViewer( self )
        self.__leftSideBar.addTab( self.projectViewer,
                                   PixmapCache().getIcon( '' ),
                                   "Project" )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.projectViewer.onFileUpdated )
        self.recentProjectsViewer = RecentProjectsViewer( self )
        self.__leftSideBar.addTab( self.recentProjectsViewer,
                                   PixmapCache().getIcon( '' ),
                                   "Recent" )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.recentProjectsViewer.onFileUpdated )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( "bufferSavedAs" ),
                      self.recentProjectsViewer.onFileUpdated )
        self.connect( self.projectViewer, SIGNAL( "fileUpdated" ),
                      self.recentProjectsViewer.onFileUpdated )

        self.classesViewer = ClassesViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.classesViewer.onFileUpdated )
        self.__leftSideBar.addTab( self.classesViewer,
                                   PixmapCache().getIcon( '' ),
                                   "Classes" )
        self.functionsViewer = FunctionsViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.functionsViewer.onFileUpdated )
        self.__leftSideBar.addTab( self.functionsViewer,
                                   PixmapCache().getIcon( '' ),
                                   "Functions" )
        self.globalsViewer = GlobalsViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.globalsViewer.onFileUpdated )
        self.__leftSideBar.addTab( self.globalsViewer,
                                   PixmapCache().getIcon( '' ),
                                   "Globals" )


        # Create todo viewer
        todoViewer = TodoViewer()
        self.__bottomSideBar.addTab( todoViewer,
                                     PixmapCache().getIcon( 'todo.png' ),
                                     'Todo' )
        self.__bottomSideBar.setTabEnabled( 1, False )

        # Create pylint viewer
        self.pylintViewer = PylintViewer()
        self.__bottomSideBar.addTab( self.pylintViewer,
                                     PixmapCache().getIcon( 'pylint.png' ),
                                     'Pylint viewer' )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.pylintViewer.onFileUpdated )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'bufferSavedAs' ),
                      self.pylintViewer.onFileUpdated )
        self.connect( self.pylintViewer, SIGNAL( 'updatePylintTooltip' ),
                      self.__onPylintTooltip )
        if GlobalData().pylintAvailable:
            self.__onPylintTooltip( "No results available" )
        else:
            self.__onPylintTooltip( "Pylint is not available" )

        # Create pymetrics viewer
        self.pymetricsViewer = PymetricsViewer()
        self.__bottomSideBar.addTab( self.pymetricsViewer,
                PixmapCache().getIcon( 'metrics.png' ), 'Metrics viewer' )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      self.pymetricsViewer.onFileUpdated )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'bufferSavedAs' ),
                      self.pymetricsViewer.onFileUpdated )
        self.connect( self.pymetricsViewer,
                      SIGNAL( 'updatePymetricsTooltip' ),
                      self.__onPymetricsTooltip )
        self.__onPymetricsTooltip( "No results available" )

        # Create search results viewer
        self.findInFilesViewer = FindInFilesViewer()
        self.__bottomSideBar.addTab( self.findInFilesViewer,
                PixmapCache().getIcon( 'findindir.png' ), 'Search results' )

        # Create tag help viewer
        self.tagHelpViewer = TagHelpViewer()
        self.__bottomSideBar.addTab( self.tagHelpViewer,
                PixmapCache().getIcon( 'helpviewer.png' ), 'Context help' )
        self.__bottomSideBar.setTabToolTip( 5, "Ctrl+F1 in python file" )

        # Create diff viewer
        self.diffViewer = DiffViewer()
        self.__bottomSideBar.addTab( self.diffViewer,
                PixmapCache().getIcon( 'diffviewer.png' ), 'Diff viewer' )
        self.__bottomSideBar.setTabToolTip( 6, 'No diff shown' )

        # Create outline viewer
        self.outlineViewer = FileOutlineViewer(
                                    self.editorsManagerWidget.editorsManager,
                                    self )
        self.__rightSideBar.addTab( self.outlineViewer,
                PixmapCache().getIcon( '' ), 'File outline' )

        # Create the pyflakes viewer
        self.__pyflakesViewer = PyflakesViewer(
                                    self.editorsManagerWidget.editorsManager,
                                    self.sbPyflakes, self )

        self.debuggerContext = DebuggerContext( self.__debugger )
        self.__rightSideBar.addTab( self.debuggerContext,
                PixmapCache().getIcon( '' ), 'Debugger' )
        self.__rightSideBar.setTabEnabled( 1, False )

        self.debuggerExceptions = DebuggerExceptions()
        self.__rightSideBar.addTab( self.debuggerExceptions,
                PixmapCache().getIcon( '' ), 'Exceptions' )
        self.connect( self.debuggerExceptions,
                      SIGNAL( 'ClientExceptionsCleared' ),
                      self.__onClientExceptionsCleared )

        self.debuggerBreakWatchPoints = DebuggerBreakWatchPoints( self,
                                                                  self.__debugger )
        self.__rightSideBar.addTab( self.debuggerBreakWatchPoints,
                PixmapCache().getIcon( '' ), 'Breakpoints' )

        # Create splitters
        self.__horizontalSplitter = QSplitter( Qt.Horizontal )
        self.__verticalSplitter = QSplitter( Qt.Vertical )

        self.__horizontalSplitter.addWidget( self.__leftSideBar )
        self.__horizontalSplitter.addWidget( self.editorsManagerWidget )
        self.__horizontalSplitter.addWidget( self.__rightSideBar )

        # This prevents changing the size of the side panels
        self.__horizontalSplitter.setCollapsible( 0, False )
        self.__horizontalSplitter.setCollapsible( 2, False )
        self.__horizontalSplitter.setStretchFactor( 0, 0 )
        self.__horizontalSplitter.setStretchFactor( 1, 1 )
        self.__horizontalSplitter.setStretchFactor( 2, 0 )

        self.__verticalSplitter.addWidget( self.__horizontalSplitter )
        self.__verticalSplitter.addWidget( self.__bottomSideBar )
        # This prevents changing the size of the side panels
        self.__verticalSplitter.setCollapsible( 1, False )
        self.__verticalSplitter.setStretchFactor( 0, 1 )
        self.__verticalSplitter.setStretchFactor( 1, 1 )

        self.setCentralWidget( self.__verticalSplitter )

        self.__leftSideBar.setSplitter( self.__horizontalSplitter )
        self.__bottomSideBar.setSplitter( self.__verticalSplitter )
        self.__rightSideBar.setSplitter( self.__horizontalSplitter )
        return

    def restoreSplitterSizes( self ):
        " Restore the side bar state "
        self.__horizontalSplitter.setSizes( self.settings.hSplitterSizes )
        self.__verticalSplitter.setSizes( self.settings.vSplitterSizes )
        if self.settings.leftBarMinimized:
            self.__leftSideBar.shrink()
        if self.settings.bottomBarMinimized:
            self.__bottomSideBar.shrink()
        if self.settings.rightBarMinimized:
            self.__rightSideBar.shrink()

        # Setup splitters movement handlers
        self.connect( self.__verticalSplitter,
                      SIGNAL( 'splitterMoved(int,int)' ), self.vSplitterMoved )
        self.connect( self.__horizontalSplitter,
                      SIGNAL( 'splitterMoved(int,int)' ), self.hSplitterMoved )
        return

    @staticmethod
    def __printThirdPartyAvailability():
        " Prints third party tools availability "

        globalData = GlobalData()
        if MAGIC_AVAILABLE:
            logging.debug( "The magic module loaded OK" )
        else:
            logging.warning( "The magic module (file type detection) is not "
                             "found. Some functionality will not be available." )

        if globalData.pylintAvailable:
            logging.debug( "The 'pylint' utility is available" )
        else:
            logging.warning( "The 'pylint' utility is not found or pylint "
                             "version is not recognised. "
                             "Some functionality will not be available." )

        if globalData.graphvizAvailable:
            logging.debug( "The 'graphviz' utility is available" )
        else:
            logging.warning( "The 'graphviz' utility is not found. "
                             "Some functionality will not be available." )

        return

    def vSplitterMoved( self, pos, index ):
        """ vertical splitter moved handler """
        newSizes = list( self.__verticalSplitter.sizes() )

        if not self.__bottomSideBar.isMinimized():
            self.__verticalSplitterSizes[ 0 ] = newSizes[ 0 ]

        self.__verticalSplitterSizes[ 1 ] = sum( newSizes ) - \
                        self.__verticalSplitterSizes[ 0 ]
        return

    def hSplitterMoved( self, pos, index ):
        """ horizontal splitter moved handler """
        newSizes = list( self.__horizontalSplitter.sizes() )

        if not self.__leftSideBar.isMinimized():
            self.__horizontalSplitterSizes[ 0 ] = newSizes[ 0 ]
        if not self.__rightSideBar.isMinimized():
            self.__horizontalSplitterSizes[ 2 ] = newSizes[ 2 ]

        self.__horizontalSplitterSizes[ 1 ] = sum( newSizes ) - \
                        self.__horizontalSplitterSizes[ 0 ] - \
                        self.__horizontalSplitterSizes[ 2 ]
        return

    def __createStatusBar( self ):
        """ creates status bar """

        self.__statusBar = self.statusBar()
        self.statusBarSlots = StatusBarSlots( self.__statusBar )
        self.__statusBar.setSizeGripEnabled( True )

        sbPalette = QPalette( self.__statusBar.palette() )
        sbPalette.setColor( QPalette.Foreground, QColor( 220, 0, 0 ) )
        self.__statusBar.setPalette( sbPalette )
        font = self.__statusBar.font()
        font.setItalic( True )
        self.__statusBar.setFont( font )

        self.sbVCSStatus = FitPathLabel( self.__statusBar )
        self.__statusBar.addPermanentWidget( self.sbVCSStatus )
        self.sbVCSStatus.setVisible( False )
        self.sbVCSStatus.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.sbVCSStatus,
                      SIGNAL( 'customContextMenuRequested(const QPoint &)' ),
                      self.__showVCSLabelContextMenu )

        self.dbgState = QLabel( "Debugger: unknown", self.__statusBar )
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

        # FitPathLabel has support for double click event,
        # so it is used here. Purely it would be better to have another
        # class for a pixmap label. But I am lazy.
        self.sbPyflakes = FitPathLabel( self.__statusBar )
        self.__statusBar.addPermanentWidget( self.sbPyflakes )

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
        self.connect( self.__projectMenu, SIGNAL( "aboutToHide()" ),
                      self.__prjAboutToHide )
        self.__newProjectAct = self.__projectMenu.addAction(
                PixmapCache().getIcon( 'createproject.png' ),
                "&New project", self.__createNewProject, 'Ctrl+Shift+N' )
        self.__openProjectAct = self.__projectMenu.addAction(
                PixmapCache().getIcon( 'project.png' ),
                '&Open project', self.__openProject, 'Ctrl+Shift+O' )
        self.__unloadProjectAct = self.__projectMenu.addAction(
                PixmapCache().getIcon( 'unloadproject.png' ),
                '&Unload project', self.projectViewer.unloadProject )
        self.__projectPropsAct = self.__projectMenu.addAction(
                PixmapCache().getIcon( 'smalli.png' ), '&Properties',
                self.projectViewer.projectProperties )
        self.__projectMenu.addSeparator()
        self.__prjTemplateMenu = QMenu( "Project-specific &template", self )
        self.__createPrjTemplateAct = self.__prjTemplateMenu.addAction(
                PixmapCache().getIcon( 'generate.png' ), '&Create' )
        self.connect( self.__createPrjTemplateAct, SIGNAL( 'triggered()' ),
                      self.__onCreatePrjTemplate )
        self.__editPrjTemplateAct = self.__prjTemplateMenu.addAction(
                PixmapCache().getIcon( 'edit.png' ), '&Edit' )
        self.connect( self.__editPrjTemplateAct, SIGNAL( 'triggered()' ),
                      self.__onEditPrjTemplate )
        self.__prjTemplateMenu.addSeparator()
        self.__delPrjTemplateAct = self.__prjTemplateMenu.addAction(
                PixmapCache().getIcon( 'trash.png' ), '&Delete' )
        self.connect( self.__delPrjTemplateAct, SIGNAL( 'triggered()' ),
                      self.__onDelPrjTemplate )
        self.__prjPylintMenu = QMenu( "Project-specific p&ylintrc", self )
        self.__prjGenPylintrcAct = self.__prjPylintMenu.addAction(
                PixmapCache().getIcon( 'generate.png' ),
                '&Create', self.__onGenPylintRC )
        self.__prjEditPylintrcAct = self.__prjPylintMenu.addAction(
                PixmapCache().getIcon( 'edit.png' ),
                '&Edit', self.__onEditPylintRC )
        self.__prjPylintMenu.addSeparator()
        self.__prjDelPylintrcAct = self.__prjPylintMenu.addAction(
                PixmapCache().getIcon( 'trash.png' ), '&Delete',
                self.__onDelPylintRC )
        self.__projectMenu.addMenu( self.__prjTemplateMenu )
        self.__projectMenu.addMenu( self.__prjPylintMenu )
        self.__prjRopeConfigAct = self.__projectMenu.addAction(
                PixmapCache().getIcon( 'edit.png' ),
                'Edit project-specific rope &config file', self.__onRopeConfig )
        self.__projectMenu.addSeparator()
        self.__recentPrjMenu = QMenu( "&Recent projects", self )
        self.connect( self.__recentPrjMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__onRecentPrj )
        self.__projectMenu.addMenu( self.__recentPrjMenu )
        self.__projectMenu.addSeparator()
        self.__quitAct = self.__projectMenu.addAction(
                PixmapCache().getIcon( 'exitmenu.png' ),
                "E&xit codimension", QApplication.closeAllWindows, "Ctrl+Q" )

        # The Tab menu
        self.__tabMenu = QMenu( "&Tab", self )
        self.connect( self.__tabMenu, SIGNAL( "aboutToShow()" ),
                      self.__tabAboutToShow )
        self.connect( self.__tabMenu, SIGNAL( "aboutToHide()" ),
                      self.__tabAboutToHide )
        self.__newTabAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'filemenu.png' ), "&New tab",
                editorsManager.newTabClicked, 'Ctrl+N' )
        self.__openFileAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'filemenu.png' ),
                '&Open file', self.__openFile, 'Ctrl+O' )
        self.__cloneTabAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'clonetabmenu.png' ),
                '&Clone tab', editorsManager.onClone )
        self.__closeOtherTabsAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( '' ),
                'Close oth&er tabs', editorsManager.onCloseOther )
        self.__closeTabAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'closetabmenu.png' ),
                'Close &tab', editorsManager.onCloseTab )
        self.__tabMenu.addSeparator()
        self.__saveFileAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'savemenu.png' ),
                '&Save', editorsManager.onSave, 'Ctrl+S' )
        self.__saveFileAsAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'saveasmenu.png' ),
                'Save &as...', editorsManager.onSaveAs, "Ctrl+Shift+S" )
        self.__tabJumpToDefAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'definition.png' ),
                "&Jump to definition", self.__onTabJumpToDef )
        self.__calltipAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'calltip.png' ),
                'Show &calltip', self.__onShowCalltip )
        self.__tabJumpToScopeBeginAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'jumpupscopemenu.png' ),
                'Jump to scope &begin', self.__onTabJumpToScopeBegin )
        self.__tabOpenImportAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'imports.png' ),
                'Open &import(s)', self.__onTabOpenImport )
        self.__openAsFileAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'filemenu.png' ),
                'O&pen as file', self.__onOpenAsFile )
        self.__downloadAndShowAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'filemenu.png' ),
                'Download and show', self.__onDownloadAndShow )
        self.__openInBrowserAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'homepagemenu.png' ),
                'Open in browser', self.__onOpenInBrowser )
        self.__tabMenu.addSeparator()
        self.__highlightInPrjAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'highlightmenu.png' ),
                'Highlight in project browser',
                editorsManager.onHighlightInPrj )
        self.__highlightInFSAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'highlightmenu.png' ),
                'Highlight in file system browser',
                editorsManager.onHighlightInFS )
        self.__highlightInOutlineAct = self.__tabMenu.addAction(
                PixmapCache().getIcon( 'highlightmenu.png' ),
                'Highlight in outline browser',
                self.__onHighlightInOutline )
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
        self.__undoAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'undo.png' ),
                '&Undo', self.__onUndo )
        self.__redoAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'redo.png' ),
                '&Redo', self.__onRedo )
        self.__editMenu.addSeparator()
        self.__cutAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'cutmenu.png' ),
                'Cu&t', self.__onCut )
        self.__copyAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'copymenu.png' ),
                '&Copy', editorsManager.onCopy )
        self.__pasteAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'pastemenu.png' ),
                '&Paste', self.__onPaste )
        self.__selectAllAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'selectallmenu.png' ),
                'Select &all', self.__onSelectAll )
        self.__editMenu.addSeparator()
        self.__commentAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'commentmenu.png' ),
                'C&omment/uncomment', self.__onComment )
        self.__duplicateAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'duplicatemenu.png' ),
                '&Duplicate line', self.__onDuplicate )
        self.__autocompleteAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'autocompletemenu.png' ),
                'Autoco&mplete', self.__onAutocomplete )
        self.__expandTabsAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'expandtabs.png' ),
                'Expand tabs (&4 spaces)', self.__onExpandTabs )
        self.__trailingSpacesAct = self.__editMenu.addAction(
                PixmapCache().getIcon( 'trailingws.png' ),
                'Remove trailing &spaces', self.__onRemoveTrailingSpaces )

        # The Search menu
        self.__searchMenu = QMenu( "&Search", self )
        self.connect( self.__searchMenu, SIGNAL( "aboutToShow()" ),
                      self.__searchAboutToShow )
        self.connect( self.__searchMenu, SIGNAL( "aboutToHide()" ),
                      self.__searchAboutToHide )
        self.__searchInFilesAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'findindir.png' ),
                "Find in file&s", self.findInFilesClicked, "Ctrl+Shift+F" )
        self.__searchMenu.addSeparator()
        self.__findNameMenuAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'findname.png' ),
                'Find &name in project', self.findNameClicked, 'Alt+Shift+S' )
        self.__fileProjectFileAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'findfile.png' ),
                'Find &project file', self.findFileClicked, 'Alt+Shift+O' )
        self.__searchMenu.addSeparator()
        self.__findOccurencesAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'findindir.png' ),
                'Find &occurrences', self.__onFindOccurences )
        self.__findAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'findindir.png' ),
                '&Find...', self.__onFind )
        self.__findCurrentAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'find.png' ),
                'Find current &word', self.__onFindCurrent )
        self.__findNextAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( '1rightarrow.png' ),
                "Find &next", self.__onFindNext )
        self.__findPrevAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( '1leftarrow.png' ),
                "Find pre&vious", self.__onFindPrevious )
        self.__replaceAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'replace.png' ),
                '&Replace...', self.__onReplace )
        self.__goToLineAct = self.__searchMenu.addAction(
                PixmapCache().getIcon( 'gotoline.png' ),
                '&Go to line...', self.__onGoToLine )

        # The Tools menu
        self.__toolsMenu = QMenu( "T&ools", self )
        self.connect( self.__toolsMenu, SIGNAL( "aboutToShow()" ),
                      self.__toolsAboutToShow )
        self.connect( self.__toolsMenu, SIGNAL( "aboutToHide()" ),
                      self.__toolsAboutToHide )
        self.__prjPylintAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'pylint.png' ),
                '&Pylint for project', self.pylintButtonClicked )
        self.__tabPylintAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'pylint.png' ),
                'P&ylint for tab', self.__onTabPylint )
        self.__toolsMenu.addSeparator()
        self.__prjPymetricsAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'metrics.png' ),
                'Py&metrics for project', self.pymetricsButtonClicked )
        self.__tabPymetricsAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'metrics.png' ),
                "Pyme&trics for tab", self.__onTabPymetrics )
        self.__toolsMenu.addSeparator()
        self.__prjLineCounterAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'linecounter.png' ),
                "&Line counter for project", self.linecounterButtonClicked )
        self.__tabLineCounterAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'linecounter.png' ),
                "L&ine counter for tab", self.__onTabLineCounter )
        self.__toolsMenu.addSeparator()
        self.__tabPythonTidyAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'pythontidy.png' ),
                'PythonT&idy for tab', self.__onTabPythonTidy )
        self.__tabPythonTidyDlgAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'PythonTi&dy for tab...', self.__onTabPythonTidyDlg )
        self.__toolsMenu.addSeparator()
        self.__unusedClassesAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'notused.png' ),
                'Unused class analysis', self.onNotUsedClasses )
        self.__unusedFunctionsAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'notused.png' ),
                'Unused function analysis', self.onNotUsedFunctions )
        self.__unusedGlobalsAct = self.__toolsMenu.addAction(
                PixmapCache().getIcon( 'notused.png' ),
                'Unused global variable analysis', self.onNotUsedGlobals )

        # The Run menu
        self.__runMenu = QMenu( "&Run", self )
        self.connect( self.__runMenu, SIGNAL( "aboutToShow()" ),
                      self.__runAboutToShow )
        self.__prjRunAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'run.png' ),
                'Run &project main script', self.__onRunProject )
        self.__prjRunDlgAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Run p&roject main script...', self.__onRunProjectSettings )
        self.__tabRunAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'run.png' ),
                'Run &tab script', self.onRunTab )
        self.__tabRunDlgAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Run t&ab script...', self.onRunTabDlg )
        self.__runMenu.addSeparator()
        self.__prjProfileAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'profile.png' ),
                'Profile project main script', self.__onProfileProject )
        self.__prjProfileDlgAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'profile.png' ),
                'Profile project main script...',
                self.__onProfileProjectSettings )
        self.__tabProfileAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'profile.png' ),
                'Profile tab script', self.__onProfileTab )
        self.__tabProfileDlgAct = self.__runMenu.addAction(
                PixmapCache().getIcon( 'profile.png' ),
                'Profile tab script...', self.__onProfileTabDlg )

        # The Debug menu
        self.__debugMenu = QMenu( "Debu&g", self )
        self.connect( self.__debugMenu, SIGNAL( "aboutToShow()" ),
                      self.__debugAboutToShow )
        self.__prjDebugAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'debugger.png' ),
                'Debug &project main script', self.__onDebugProject, "Shift+F5" )
        self.__prjDebugDlgAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Debug p&roject main script...', self.__onDebugProjectSettings, "Ctrl+Shift+F5" )
        self.__tabDebugAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'debugger.png' ),
                'Debug &tab script', self.__onDebugTab, "F5" )
        self.__tabDebugDlgAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Debug t&ab script...', self.__onDebugTabDlg, "Ctrl+F5" )
        self.__debugMenu.addSeparator()
        self.__debugStopBrutalAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgstopbrutal.png' ),
                'Stop session and kill console', self.__onBrutalStopDbgSession, "Ctrl+F10" )
        self.__debugStopBrutalAct.setEnabled( False )
        self.__debugStopAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgstop.png' ),
                'Stop session and keep console if so', self.__onStopDbgSession, "F10" )
        self.__debugStopAct.setEnabled( False )
        self.__debugRestartAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgrestart.png' ),
                'Restart session', self.__onRestartDbgSession, "F4" )
        self.__debugRestartAct.setEnabled( False )
        self.__debugMenu.addSeparator()
        self.__debugContinueAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbggo.png' ),
                'Continue', self.__onDbgGo, "F6" )
        self.__debugContinueAct.setEnabled( False )
        self.__debugStepInAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgstepinto.png' ),
                'Step in', self.__onDbgStepInto, "F7" )
        self.__debugStepInAct.setEnabled( False )
        self.__debugStepOverAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgnext.png' ),
                'Step over', self.__onDbgNext, "F8" )
        self.__debugStepOverAct.setEnabled( False )
        self.__debugStepOutAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgreturn.png' ),
                'Step out', self.__onDbgReturn, "F9" )
        self.__debugStepOutAct.setEnabled( False )
        self.__debugRunToCursorAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgruntoline.png' ),
                'Run to cursor', self.__onDbgRunToLine, "Shift+F6" )
        self.__debugRunToCursorAct.setEnabled( False )
        self.__debugJumpToCurrentAct = self.__debugMenu.addAction(
                PixmapCache().getIcon( 'dbgtocurrent.png' ),
                'Show current line', self.__onDbgJumpToCurrent, "Ctrl+W" )
        self.__debugJumpToCurrentAct.setEnabled( False )
        self.__debugMenu.addSeparator()

        self.__dumpDbgSettingsMenu = QMenu( "Dump debug settings", self )
        self.__debugMenu.addMenu( self.__dumpDbgSettingsMenu )
        self.__debugDumpSettingsAct = self.__dumpDbgSettingsMenu.addAction(
                PixmapCache().getIcon( 'dbgsettings.png' ),
                'Debug session settings',
                self.__onDumpDebugSettings )
        self.__debugDumpSettingsAct.setEnabled( False )
        self.__debugDumpSettingsEnvAct = self.__dumpDbgSettingsMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Session settings with complete environment',
                self.__onDumpFullDebugSettings )
        self.__debugDumpSettingsEnvAct.setEnabled( False )
        self.__dumpDbgSettingsMenu.addSeparator()
        self.__debugDumpScriptSettingsAct = self.__dumpDbgSettingsMenu.addAction(
                PixmapCache().getIcon( 'dbgsettings.png' ),
                'Current script settings',
                self.__onDumpScriptDebugSettings )
        self.__debugDumpScriptSettingsAct.setEnabled( False )
        self.__debugDumpScriptSettingsEnvAct = self.__dumpDbgSettingsMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Current script settings with complete environment',
                self.__onDumpScriptFullDebugSettings )
        self.__debugDumpScriptSettingsEnvAct.setEnabled( False )
        self.__dumpDbgSettingsMenu.addSeparator()
        self.__debugDumpProjectSettingsAct = self.__dumpDbgSettingsMenu.addAction(
                PixmapCache().getIcon( 'dbgsettings.png' ),
                'Project main script settings',
                self.__onDumpProjectDebugSettings )
        self.__debugDumpProjectSettingsAct.setEnabled( False )
        self.__debugDumpProjectSettingsEnvAct = self.__dumpDbgSettingsMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'Project script settings with complete environment',
                self.__onDumpProjectFullDebugSettings )
        self.__debugDumpProjectSettingsEnvAct.setEnabled( False )
        self.connect( self.__dumpDbgSettingsMenu, SIGNAL( "aboutToShow()" ),
                      self.__onDumpDbgSettingsAboutToShow )

        # The Diagrams menu
        self.__diagramsMenu = QMenu( "&Diagrams", self )
        self.connect( self.__diagramsMenu, SIGNAL( "aboutToShow()" ),
                      self.__diagramsAboutToShow )
        self.__prjImportDgmAct = self.__diagramsMenu.addAction(
                PixmapCache().getIcon( 'importsdiagram.png' ),
                '&Project imports diagram', self.__onImportDgm )
        self.__prjImportsDgmDlgAct = self.__diagramsMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'P&roject imports diagram...', self.__onImportDgmTuned )
        self.__tabImportDgmAct = self.__diagramsMenu.addAction(
                PixmapCache().getIcon( 'importsdiagram.png' ),
                '&Tab imports diagram', self.__onTabImportDgm )
        self.__tabImportDgmDlgAct = self.__diagramsMenu.addAction(
                PixmapCache().getIcon( 'detailsdlg.png' ),
                'T&ab imports diagram...', self.__onTabImportDgmTuned )

        # The View menu
        self.__viewMenu = QMenu( "&View", self )
        self.connect( self.__viewMenu, SIGNAL( "aboutToShow()" ),
                      self.__viewAboutToShow )
        self.connect( self.__viewMenu, SIGNAL( "aboutToHide()" ),
                      self.__viewAboutToHide )
        self.__shrinkBarsAct = self.__viewMenu.addAction(
                PixmapCache().getIcon( 'shrinkmenu.png' ),
                "&Hide sidebars", self.__onMaximizeEditor, 'F11' )
        self.__leftSideBarMenu = QMenu( "&Left sidebar", self )
        self.connect( self.__leftSideBarMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__activateSideTab )
        self.__prjBarAct = self.__leftSideBarMenu.addAction(
                PixmapCache().getIcon( 'project.png' ),
                'Activate &project tab' )
        self.__prjBarAct.setData( QVariant( 'prj' ) )
        self.__recentBarAct = self.__leftSideBarMenu.addAction(
                PixmapCache().getIcon( 'project.png' ),
                'Activate &recent tab' )
        self.__recentBarAct.setData( QVariant( 'recent' ) )
        self.__classesBarAct = self.__leftSideBarMenu.addAction(
                PixmapCache().getIcon( 'class.png' ),
                'Activate &classes tab' )
        self.__classesBarAct.setData( QVariant( 'classes' ) )
        self.__funcsBarAct = self.__leftSideBarMenu.addAction(
                PixmapCache().getIcon( 'fx.png' ),
                'Activate &functions tab' )
        self.__funcsBarAct.setData( QVariant( 'funcs' ) )
        self.__globsBarAct = self.__leftSideBarMenu.addAction(
                PixmapCache().getIcon( 'globalvar.png' ),
                'Activate &globals tab' )
        self.__globsBarAct.setData( QVariant( 'globs' ) )
        self.__leftSideBarMenu.addSeparator()
        self.__hideLeftSideBarAct = self.__leftSideBarMenu.addAction(
                PixmapCache().getIcon( "" ),
                '&Hide left sidebar', self.__leftSideBar.shrink )
        self.__viewMenu.addMenu( self.__leftSideBarMenu )

        self.__rightSideBarMenu = QMenu( "&Right sidebar", self )
        self.connect( self.__rightSideBarMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__activateSideTab )
        self.__outlineBarAct = self.__rightSideBarMenu.addAction(
                PixmapCache().getIcon( 'filepython.png' ),
                'Activate &outline tab' )
        self.__outlineBarAct.setData( QVariant( 'outline' ) )
        self.__debugBarAct = self.__rightSideBarMenu.addAction(
                PixmapCache().getIcon( '' ),
                'Activate &debug tab' )
        self.__debugBarAct.setData( QVariant( 'debug' ) )
        self.__excptBarAct = self.__rightSideBarMenu.addAction(
                PixmapCache().getIcon( '' ),
                'Activate &exceptions tab' )
        self.__excptBarAct.setData( QVariant( 'excpt' ) )
        self.__bpointBarAct = self.__rightSideBarMenu.addAction(
                PixmapCache().getIcon( '' ),
                'Activate &breakpoints tab' )
        self.__bpointBarAct.setData( QVariant( 'bpoint' ) )
        self.__rightSideBarMenu.addSeparator()
        self.__hideRightSideBarAct = self.__rightSideBarMenu.addAction(
                PixmapCache().getIcon( "" ),
                '&Hide right sidebar', self.__rightSideBar.shrink )
        self.__viewMenu.addMenu( self.__rightSideBarMenu )

        self.__bottomSideBarMenu = QMenu( "&Bottom sidebar", self )
        self.connect( self.__bottomSideBarMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__activateSideTab )
        self.__logBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( 'logviewer.png' ),
                'Activate &log tab' )
        self.__logBarAct.setData( QVariant( 'log' ) )
        self.__pylintBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( 'pylint.png' ),
                'Activate &pylint tab' )
        self.__pylintBarAct.setData( QVariant( 'pylint' ) )
        self.__pymetricsBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( 'metrics.png' ),
                'Activate py&metrics tab' )
        self.__pymetricsBarAct.setData( QVariant( 'pymetrics' ) )
        self.__searchBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( 'findindir.png' ),
                'Activate &search tab' )
        self.__searchBarAct.setData( QVariant( 'search' ) )
        self.__contextHelpBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( 'helpviewer.png' ),
                'Activate context &help tab' )
        self.__contextHelpBarAct.setData( QVariant( 'contexthelp' ) )
        self.__diffBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( 'diffviewer.png' ),
                'Activate &diff tab' )
        self.__diffBarAct.setData( QVariant( 'diff' ) )
        self.__bottomSideBarMenu.addSeparator()
        self.__hideBottomSideBarAct = self.__bottomSideBarMenu.addAction(
                PixmapCache().getIcon( "" ),
                '&Hide bottom sidebar', self.__bottomSideBar.shrink )
        self.__viewMenu.addMenu( self.__bottomSideBarMenu )
        self.__viewMenu.addSeparator()
        self.__zoomInAct = self.__viewMenu.addAction(
                PixmapCache().getIcon( 'zoomin.png' ),
                'Zoom &in', self.__onZoomIn )
        self.__zoomOutAct = self.__viewMenu.addAction(
                PixmapCache().getIcon( 'zoomout.png' ),
                'Zoom &out', self.__onZoomOut )
        self.__zoom11Act = self.__viewMenu.addAction(
                PixmapCache().getIcon( 'zoomreset.png' ),
                'Zoom r&eset', self.__onZoomReset )

        # Options menu
        self.__optionsMenu = QMenu( "Optio&ns", self )
        self.connect( self.__optionsMenu, SIGNAL( "aboutToShow()" ),
                      self.__optionsAboutToShow )

        self.__ideTemplateMenu = QMenu( "IDE-wide &template", self )
        self.__ideCreateTemplateAct = self.__ideTemplateMenu.addAction(
                                    PixmapCache().getIcon( 'generate.png' ),
                                    '&Create' )
        self.connect( self.__ideCreateTemplateAct, SIGNAL( 'triggered()' ),
                      self.__onCreateIDETemplate )
        self.__ideEditTemplateAct = self.__ideTemplateMenu.addAction(
                                    PixmapCache().getIcon( 'edit.png' ),
                                    '&Edit' )
        self.connect( self.__ideEditTemplateAct, SIGNAL( 'triggered()' ),
                      self.__onEditIDETemplate )
        self.__ideTemplateMenu.addSeparator()
        self.__ideDelTemplateAct = self.__ideTemplateMenu.addAction(
                PixmapCache().getIcon( 'trash.png' ), '&Delete' )
        self.connect( self.__ideDelTemplateAct, SIGNAL( 'triggered()' ),
                      self.__onDelIDETemplate )
        self.__optionsMenu.addMenu( self.__ideTemplateMenu )

        self.__idePylintMenu = QMenu( "IDE-wide &pylint", self )
        self.__ideCreatePylintAct = self.__idePylintMenu.addAction(
                PixmapCache().getIcon( 'generate.png' ), '&Create' )
        self.connect( self.__ideCreatePylintAct, SIGNAL( 'triggered()' ),
                      self.__onCreateIDEPylint )
        self.__ideEditPylintAct = self.__idePylintMenu.addAction(
                    PixmapCache().getIcon( 'edit.png' ), '&Edit' )
        self.connect( self.__ideEditPylintAct, SIGNAL( 'triggered()' ),
                      self.__onEditIDEPylint )
        self.__idePylintMenu.addSeparator()
        self.__ideDelPylintAct = self.__idePylintMenu.addAction(
                    PixmapCache().getIcon( 'trash.png' ), '&Delete' )
        self.connect( self.__ideDelPylintAct, SIGNAL( 'triggered()' ),
                      self.__onDelIDEPylint )
        self.__optionsMenu.addMenu( self.__idePylintMenu )
        self.__optionsMenu.addSeparator()

        verticalEdgeAct = self.__optionsMenu.addAction( 'Show vertical edge' )
        verticalEdgeAct.setCheckable( True )
        verticalEdgeAct.setChecked( self.settings.verticalEdge )
        self.connect( verticalEdgeAct, SIGNAL( 'changed()' ),
                      self.__verticalEdgeChanged )
        showSpacesAct = self.__optionsMenu.addAction( 'Show whitespaces' )
        showSpacesAct.setCheckable( True )
        showSpacesAct.setChecked( self.settings.showSpaces )
        self.connect( showSpacesAct, SIGNAL( 'changed()' ),
                      self.__showSpacesChanged )
        lineWrapAct = self.__optionsMenu.addAction( 'Wrap long lines' )
        lineWrapAct.setCheckable( True )
        lineWrapAct.setChecked( self.settings.lineWrap )
        self.connect( lineWrapAct, SIGNAL( 'changed()' ),
                      self.__lineWrapChanged )
        showEOLAct = self.__optionsMenu.addAction( 'Show EOL' )
        showEOLAct.setCheckable( True )
        showEOLAct.setChecked( self.settings.showEOL )
        self.connect( showEOLAct, SIGNAL( 'changed()' ), self.__showEOLChanged )
        showBraceMatchAct = self.__optionsMenu.addAction(
                                                    'Show brace matching' )
        showBraceMatchAct.setCheckable( True )
        showBraceMatchAct.setChecked( self.settings.showBraceMatch )
        self.connect( showBraceMatchAct, SIGNAL( 'changed()' ),
                      self.__showBraceMatchChanged )
        autoIndentAct = self.__optionsMenu.addAction( 'Auto indent' )
        autoIndentAct.setCheckable( True )
        autoIndentAct.setChecked( self.settings.autoIndent )
        self.connect( autoIndentAct, SIGNAL( 'changed()' ),
                      self.__autoIndentChanged )
        backspaceUnindentAct = self.__optionsMenu.addAction(
                                                        'Backspace unindent' )
        backspaceUnindentAct.setCheckable( True )
        backspaceUnindentAct.setChecked( self.settings.backspaceUnindent )
        self.connect( backspaceUnindentAct, SIGNAL( 'changed()' ),
                      self.__backspaceUnindentChanged )
        tabIndentsAct = self.__optionsMenu.addAction( 'TAB indents' )
        tabIndentsAct.setCheckable( True )
        tabIndentsAct.setChecked( self.settings.tabIndents )
        self.connect( tabIndentsAct, SIGNAL( 'changed()' ),
                      self.__tabIndentsChanged )
        indentationGuidesAct = self.__optionsMenu.addAction(
                                        'Show indentation guides' )
        indentationGuidesAct.setCheckable( True )
        indentationGuidesAct.setChecked( self.settings.indentationGuides )
        self.connect( indentationGuidesAct, SIGNAL( 'changed()' ),
                      self.__indentationGuidesChanged )
        currentLineVisibleAct = self.__optionsMenu.addAction(
                                        'Highlight current line' )
        currentLineVisibleAct.setCheckable( True )
        currentLineVisibleAct.setChecked( self.settings.currentLineVisible )
        self.connect( currentLineVisibleAct, SIGNAL( 'changed()' ),
                      self.__currentLineVisibleChanged )
        jumpToFirstNonSpaceAct = self.__optionsMenu.addAction(
                                        'HOME to first non-space' )
        jumpToFirstNonSpaceAct.setCheckable( True )
        jumpToFirstNonSpaceAct.setChecked( self.settings.jumpToFirstNonSpace )
        self.connect( jumpToFirstNonSpaceAct, SIGNAL( 'changed()' ),
                      self.__homeToFirstNonSpaceChanged )
        removeTrailingOnSpaceAct = self.__optionsMenu.addAction(
                                        'Auto remove trailing spaces on save' )
        removeTrailingOnSpaceAct.setCheckable( True )
        removeTrailingOnSpaceAct.setChecked(
                                    self.settings.removeTrailingOnSave )
        self.connect( removeTrailingOnSpaceAct, SIGNAL( 'changed()' ),
                      self.__removeTrailingChanged )
        editorCalltipsAct = self.__optionsMenu.addAction( 'Editor calltips' )
        editorCalltipsAct.setCheckable( True )
        editorCalltipsAct.setChecked( self.settings.editorCalltips )
        self.connect( editorCalltipsAct, SIGNAL( 'changed()' ),
                      self.__editorCalltipsChanged )
        clearDebugIOAct = self.__optionsMenu.addAction( 'Clear debug IO console on new session' )
        clearDebugIOAct.setCheckable( True )
        clearDebugIOAct.setChecked( self.settings.clearDebugIO )
        self.connect( clearDebugIOAct, SIGNAL( 'changed()' ),
                      self.__clearDebugIOChanged )
        showNavBarAct = self.__optionsMenu.addAction( 'Show navigation bar' )
        showNavBarAct.setCheckable( True )
        showNavBarAct.setChecked( self.settings.showNavigationBar )
        self.connect( showNavBarAct, SIGNAL( 'changed()' ),
                      self.__showNavBarChanged )
        self.__optionsMenu.addSeparator()
        tooltipsMenu = self.__optionsMenu.addMenu( "Tooltips" )
        projectTooltipsAct = tooltipsMenu.addAction( "&Project tab" )
        projectTooltipsAct.setCheckable( True )
        projectTooltipsAct.setChecked(
                                    self.settings.projectTooltips )
        self.connect( projectTooltipsAct, SIGNAL( 'changed()' ),
                      self.__projectTooltipsChanged )
        recentTooltipsAct = tooltipsMenu.addAction( "&Recent tab" )
        recentTooltipsAct.setCheckable( True )
        recentTooltipsAct.setChecked(
                                    self.settings.recentTooltips )
        self.connect( recentTooltipsAct, SIGNAL( 'changed()' ),
                      self.__recentTooltipsChanged )
        classesTooltipsAct = tooltipsMenu.addAction( "&Classes tab" )
        classesTooltipsAct.setCheckable( True )
        classesTooltipsAct.setChecked(
                                    self.settings.classesTooltips )
        self.connect( classesTooltipsAct, SIGNAL( 'changed()' ),
                      self.__classesTooltipsChanged )
        functionsTooltipsAct = tooltipsMenu.addAction( "&Functions tab" )
        functionsTooltipsAct.setCheckable( True )
        functionsTooltipsAct.setChecked(
                                    self.settings.functionsTooltips )
        self.connect( functionsTooltipsAct, SIGNAL( 'changed()' ),
                      self.__functionsTooltipsChanged )
        outlineTooltipsAct = tooltipsMenu.addAction( "&Outline tab" )
        outlineTooltipsAct.setCheckable( True )
        outlineTooltipsAct.setChecked(
                                    self.settings.outlineTooltips )
        self.connect( outlineTooltipsAct, SIGNAL( 'changed()' ),
                      self.__outlineTooltipsChanged )
        findNameTooltipsAct = tooltipsMenu.addAction( "Find &name dialog" )
        findNameTooltipsAct.setCheckable( True )
        findNameTooltipsAct.setChecked(
                                    self.settings.findNameTooltips )
        self.connect( findNameTooltipsAct, SIGNAL( 'changed()' ),
                      self.__findNameTooltipsChanged )
        findFileTooltipsAct = tooltipsMenu.addAction( "Find fi&le dialog" )
        findFileTooltipsAct.setCheckable( True )
        findFileTooltipsAct.setChecked(
                                    self.settings.findFileTooltips )
        self.connect( findFileTooltipsAct, SIGNAL( 'changed()' ),
                      self.__findFileTooltipsChanged )
        editorTooltipsAct = tooltipsMenu.addAction( "&Editor tabs" )
        editorTooltipsAct.setCheckable( True )
        editorTooltipsAct.setChecked( self.settings.editorTooltips )
        self.connect( editorTooltipsAct, SIGNAL( 'changed()' ),
                      self.__editorTooltipsChanged )

        openTabsMenu = self.__optionsMenu.addMenu( "Open tabs button" )
        self.__navigationSortGroup = QActionGroup( self )
        self.__alphasort = openTabsMenu.addAction( "Sort alphabetically" )
        self.__alphasort.setCheckable( True )
        self.__alphasort.setData( QVariant( -1 ) )
        self.__alphasort.setActionGroup( self.__navigationSortGroup )
        self.__tabsort = openTabsMenu.addAction( "Tab order sort" )
        self.__tabsort.setCheckable( True )
        self.__tabsort.setData( QVariant( -2 ) )
        self.__tabsort.setActionGroup( self.__navigationSortGroup )
        if self.settings.tablistsortalpha:
            self.__alphasort.setChecked( True )
        else:
            self.__tabsort.setChecked( True )
        openTabsMenu.addSeparator()
        tabOrderPreservedAct = openTabsMenu.addAction(
                                    "Tab order preserved on selection" )
        tabOrderPreservedAct.setCheckable( True )
        tabOrderPreservedAct.setData( QVariant( 0 ) )
        tabOrderPreservedAct.setChecked( self.settings.taborderpreserved )
        self.connect( tabOrderPreservedAct, SIGNAL( 'changed()' ),
                      self.__tabOrderPreservedChanged )
        self.connect( openTabsMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__openTabsMenuTriggered )

        self.__optionsMenu.addSeparator()
        themesMenu = self.__optionsMenu.addMenu( "Themes" )
        availableThemes = self.__buildThemesList()
        for theme in availableThemes:
            themeAct = themesMenu.addAction( theme[ 1 ] )
            themeAct.setData( QVariant( theme[ 0 ] ) )
            if theme[ 0 ] == self.settings.skin:
                font = themeAct.font()
                font.setBold( True )
                themeAct.setFont( font )
        self.connect( themesMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__onTheme )

        styleMenu = self.__optionsMenu.addMenu( "Styles" )
        availableStyles = QStyleFactory.keys()
        self.__styles = []
        for style in availableStyles:
            styleAct = styleMenu.addAction( style )
            styleAct.setData( QVariant( style ) )
            self.__styles.append( ( str( style ), styleAct ) )
        self.connect( styleMenu, SIGNAL( 'triggered(QAction*)' ),
                      self.__onStyle )
        self.connect( styleMenu, SIGNAL( "aboutToShow()" ),
                      self.__styleAboutToShow )

        fontFaceMenu = self.__optionsMenu.addMenu( "Mono font face" )
        for fontFace in getMonospaceFontList():
            faceAct = fontFaceMenu.addAction( fontFace )
            faceAct.setData( QVariant( fontFace ) )
            f = faceAct.font()
            f.setFamily( fontFace )
            faceAct.setFont( f )
        self.connect( fontFaceMenu, SIGNAL( 'triggered(QAction*)' ),
                      self.__onMonoFont )

        # The plugins menu
        self.__pluginsMenu = QMenu( "P&lugins", self )
        self.__recomposePluginMenu()

        # The Help menu
        self.__helpMenu = QMenu( "&Help", self )
        self.connect( self.__helpMenu, SIGNAL( "aboutToShow()" ),
                      self.__helpAboutToShow )
        self.connect( self.__helpMenu, SIGNAL( "aboutToHide()" ),
                      self.__helpAboutToHide )
        self.__shortcutsAct = self.__helpMenu.addAction(
            PixmapCache().getIcon( 'shortcutsmenu.png' ),
            '&Major shortcuts', editorsManager.onHelp, 'F1' )
        self.__contextHelpAct = self.__helpMenu.addAction(
            PixmapCache().getIcon( 'helpviewer.png' ),
            'Current &word help', self.__onContextHelp )
        self.__callHelpAct = self.__helpMenu.addAction(
            PixmapCache().getIcon( 'helpviewer.png' ),
            '&Current call help', self.__onCallHelp )
        self.__helpMenu.addSeparator()
        self.__allShotcutsAct = self.__helpMenu.addAction(
            PixmapCache().getIcon( 'allshortcutsmenu.png' ),
            '&All shortcuts (web page)', self.__onAllShortcurs )
        self.__homePageAct = self.__helpMenu.addAction(
            PixmapCache().getIcon( 'homepagemenu.png' ),
            'Codimension &home page', self.__onHomePage )
        self.__helpMenu.addSeparator()
        self.__aboutAct = self.__helpMenu.addAction(
            PixmapCache().getIcon( "logo.png" ),
            "A&bout codimension", self.__onAbout )

        menuBar = self.menuBar()
        menuBar.addMenu( self.__projectMenu )
        menuBar.addMenu( self.__tabMenu )
        menuBar.addMenu( self.__editMenu )
        menuBar.addMenu( self.__searchMenu )
        menuBar.addMenu( self.__runMenu )
        menuBar.addMenu( self.__debugMenu )
        menuBar.addMenu( self.__toolsMenu )
        menuBar.addMenu( self.__diagramsMenu )
        menuBar.addMenu( self.__viewMenu )
        menuBar.addMenu( self.__optionsMenu )
        menuBar.addMenu( self.__pluginsMenu )
        menuBar.addMenu( self.__helpMenu )
        return

    def __createToolBar( self ):
        """ creates the buttons bar """

        # Imports diagram button and its menu
        importsMenu = QMenu( self )
        importsDlgAct = importsMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Fine tuned imports diagram' )
        self.connect( importsDlgAct, SIGNAL( 'triggered()' ),
                      self.__onImportDgmTuned )
        self.importsDiagramButton = QToolButton( self )
        self.importsDiagramButton.setIcon(
                            PixmapCache().getIcon( 'importsdiagram.png' ) )
        self.importsDiagramButton.setToolTip( 'Generate imports diagram' )
        self.importsDiagramButton.setPopupMode( QToolButton.DelayedPopup )
        self.importsDiagramButton.setMenu( importsMenu )
        self.importsDiagramButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.importsDiagramButton, SIGNAL( 'clicked(bool)' ),
                      self.__onImportDgm )

        # Run project button and its menu
        runProjectMenu = QMenu( self )
        runProjectAct = runProjectMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run parameters' )
        self.connect( runProjectAct, SIGNAL( 'triggered()' ),
                      self.__onRunProjectSettings )
        self.runProjectButton = QToolButton( self )
        self.runProjectButton.setIcon(
                            PixmapCache().getIcon( 'run.png' ) )
        self.runProjectButton.setToolTip( 'Project is not loaded' )
        self.runProjectButton.setPopupMode( QToolButton.DelayedPopup )
        self.runProjectButton.setMenu( runProjectMenu )
        self.runProjectButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.runProjectButton, SIGNAL( 'clicked(bool)' ),
                      self.__onRunProject )

        # profile project button and its menu
        profileProjectMenu = QMenu( self )
        profileProjectAct = profileProjectMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set profile parameters' )
        self.connect( profileProjectAct, SIGNAL( 'triggered()' ),
                      self.__onProfileProjectSettings )
        self.profileProjectButton = QToolButton( self )
        self.profileProjectButton.setIcon(
                            PixmapCache().getIcon( 'profile.png' ) )
        self.profileProjectButton.setToolTip( 'Project is not loaded' )
        self.profileProjectButton.setPopupMode( QToolButton.DelayedPopup )
        self.profileProjectButton.setMenu( profileProjectMenu )
        self.profileProjectButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.profileProjectButton, SIGNAL( 'clicked(bool)' ),
                      self.__onProfileProject )


        # Debug project button and its menu
        debugProjectMenu = QMenu( self )
        debugProjectAct = debugProjectMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set debug parameters' )
        self.connect( debugProjectAct, SIGNAL( 'triggered()' ),
                      self.__onDebugProjectSettings )
        self.debugProjectButton = QToolButton( self )
        self.debugProjectButton.setIcon(
                            PixmapCache().getIcon( 'debugger.png' ) )
        self.debugProjectButton.setToolTip( 'Project is not loaded' )
        self.debugProjectButton.setPopupMode( QToolButton.DelayedPopup )
        self.debugProjectButton.setMenu( debugProjectMenu )
        self.debugProjectButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.debugProjectButton, SIGNAL( 'clicked(bool)' ),
                      self.__onDebugProject )
        self.debugProjectButton.setVisible( True )

        packageDiagramButton = QAction(
                PixmapCache().getIcon( 'packagediagram.png' ),
                'Generate package diagram', self )
        packageDiagramButton.setEnabled( False )
        packageDiagramButton.setVisible( False )
        applicationDiagramButton = QAction(
                PixmapCache().getIcon( 'applicationdiagram.png' ),
                'Generate application diagram', self )
        applicationDiagramButton.setEnabled( False )
        applicationDiagramButton.setVisible( False )
        neverUsedButton = QAction(
                PixmapCache().getIcon( 'neverused.png' ),
                'Analysis for never used variables, functions, classes', self )
        neverUsedButton.setEnabled( False )
        neverUsedButton.setVisible( False )

        # pylint button
        self.__existentPylintRCMenu = QMenu( self )
        editAct = self.__existentPylintRCMenu.addAction(
                                    PixmapCache().getIcon( 'edit.png' ),
                                    'Edit project-specific pylintrc' )
        self.connect( editAct, SIGNAL( 'triggered()' ), self.__onEditPylintRC )
        self.__existentPylintRCMenu.addSeparator()
        delAct = self.__existentPylintRCMenu.addAction(
                                    PixmapCache().getIcon( 'trash.png' ),
                                    'Delete project-specific pylintrc' )
        self.connect( delAct, SIGNAL( 'triggered()' ), self.__onDelPylintRC )

        self.__absentPylintRCMenu = QMenu( self )
        genAct = self.__absentPylintRCMenu.addAction(
                                    PixmapCache().getIcon( 'generate.png' ),
                                    'Create project-specific pylintrc' )
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
        self.__pymetricsButton = QAction(
                                    PixmapCache().getIcon( 'metrics.png' ),
                                    'Project metrics', self )
        self.connect( self.__pymetricsButton, SIGNAL( 'triggered()' ),
                      self.pymetricsButtonClicked )

        self.linecounterButton = QAction(
                                    PixmapCache().getIcon( 'linecounter.png' ),
                                    'Project line counter', self )
        self.connect( self.linecounterButton, SIGNAL( 'triggered()' ),
                      self.linecounterButtonClicked )

        self.__findInFilesButton = QAction(
                                    PixmapCache().getIcon( 'findindir.png' ),
                                    'Find in files (Ctrl+Shift+F)', self )
        self.connect( self.__findInFilesButton, SIGNAL( 'triggered()' ),
                      self.findInFilesClicked )

        self.__findNameButton = QAction(
                                    PixmapCache().getIcon( 'findname.png' ),
                                    'Find name in project (Alt+Shift+S)', self )
        self.connect( self.__findNameButton, SIGNAL( 'triggered()' ),
                      self.findNameClicked )

        self.__findFileButton = QAction(
                                    PixmapCache().getIcon( 'findfile.png' ),
                                    'Find project file (Alt+Shift+O)', self )
        self.connect( self.__findFileButton, SIGNAL( 'triggered()' ),
                      self.findFileClicked )

        # Debugger buttons
        self.__dbgStopBrutal = QAction( PixmapCache().getIcon( 'dbgstopbrutal.png' ),
                                       'Stop debugging session and '
                                       'kill console (Ctrl+F10)', self )
        self.connect( self.__dbgStopBrutal, SIGNAL( "triggered()" ),
                      self.__onBrutalStopDbgSession )
        self.__dbgStopBrutal.setVisible( False )
        self.__dbgStopAndClearIO = QAction( PixmapCache().getIcon( 'dbgstopcleario.png' ),
                                            'Stop debugging session and clear IO console', self )
        self.connect( self.__dbgStopAndClearIO, SIGNAL( "triggered()" ),
                      self.__onBrutalStopDbgSession )
        self.__dbgStopAndClearIO.setVisible( False )
        self.__dbgStop = QAction( PixmapCache().getIcon( 'dbgstop.png' ),
                                  'Stop debugging session and keep console if so (F10)', self )
        self.connect( self.__dbgStop, SIGNAL( "triggered()" ),
                      self.__onStopDbgSession )
        self.__dbgStop.setVisible( False )
        self.__dbgRestart = QAction( PixmapCache().getIcon( 'dbgrestart.png' ),
                                     'Restart debugging section (F4)', self )
        self.connect( self.__dbgRestart, SIGNAL( "triggered()" ),
                      self.__onRestartDbgSession )
        self.__dbgRestart.setVisible( False )
        self.__dbgGo = QAction( PixmapCache().getIcon( 'dbggo.png' ),
                                'Continue (F6)', self )
        self.connect( self.__dbgGo, SIGNAL( "triggered()" ),
                      self.__onDbgGo )
        self.__dbgGo.setVisible( False )
        self.__dbgNext = QAction( PixmapCache().getIcon( 'dbgnext.png' ),
                                  'Step over (F8)', self )
        self.connect( self.__dbgNext, SIGNAL( "triggered()" ),
                      self.__onDbgNext )
        self.__dbgNext.setVisible( False )
        self.__dbgStepInto = QAction(
            PixmapCache().getIcon( 'dbgstepinto.png' ), 'Step into (F7)', self )
        self.connect( self.__dbgStepInto, SIGNAL( "triggered()" ),
                      self.__onDbgStepInto )
        self.__dbgStepInto.setVisible( False )
        self.__dbgRunToLine = QAction(
            PixmapCache().getIcon( 'dbgruntoline.png' ), 'Run to cursor (Shift+F6)', self )
        self.connect( self.__dbgRunToLine, SIGNAL( "triggered()" ),
                      self.__onDbgRunToLine )
        self.__dbgRunToLine.setVisible( False )
        self.__dbgReturn = QAction( PixmapCache().getIcon( 'dbgreturn.png' ),
                                    'Step out (F9)', self )
        self.connect( self.__dbgReturn, SIGNAL( "triggered()" ),
                      self.__onDbgReturn )
        self.__dbgReturn.setVisible( False )
        self.__dbgJumpToCurrent = QAction( PixmapCache().getIcon( 'dbgtocurrent.png' ),
                                           'Show current debugger line (Ctrl+W)', self )
        self.connect( self.__dbgJumpToCurrent, SIGNAL( "triggered()" ),
                      self.__onDbgJumpToCurrent )
        self.__dbgJumpToCurrent.setVisible( False )

        dumpDebugSettingsMenu = QMenu( self )
        dumpDebugSettingsAct = dumpDebugSettingsMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Dump settings with complete environment' )
        self.connect( dumpDebugSettingsAct, SIGNAL( 'triggered()' ),
                      self.__onDumpFullDebugSettings )
        self.__dbgDumpSettingsButton = QToolButton( self )
        self.__dbgDumpSettingsButton.setIcon(
                            PixmapCache().getIcon( 'dbgsettings.png' ) )
        self.__dbgDumpSettingsButton.setToolTip( 'Dump debug session settings' )
        self.__dbgDumpSettingsButton.setPopupMode( QToolButton.DelayedPopup )
        self.__dbgDumpSettingsButton.setMenu( dumpDebugSettingsMenu )
        self.__dbgDumpSettingsButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__dbgDumpSettingsButton, SIGNAL( 'clicked(bool)' ),
                      self.__onDumpDebugSettings )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.__toolbar = QToolBar()
        self.__toolbar.setMovable( False )
        self.__toolbar.setAllowedAreas( Qt.TopToolBarArea )
        self.__toolbar.setIconSize( QSize( 26, 26 ) )
        self.__toolbar.addAction( packageDiagramButton )
        self.__toolbar.addWidget( self.importsDiagramButton )
        self.__toolbar.addSeparator()
        self.__toolbar.addWidget( self.runProjectButton )
        self.__toolbar.addWidget( self.debugProjectButton )
        self.__toolbar.addWidget( self.profileProjectButton )
        self.__toolbar.addAction( applicationDiagramButton )
        self.__toolbar.addSeparator()
        self.__toolbar.addAction( neverUsedButton )
        self.__toolbar.addWidget( self.__pylintButton )
        self.__toolbar.addAction( self.__pymetricsButton )
        self.__toolbar.addAction( self.linecounterButton )
        self.__toolbar.addSeparator()
        self.__toolbar.addAction( self.__findInFilesButton )
        self.__toolbar.addAction( self.__findNameButton )
        self.__toolbar.addAction( self.__findFileButton )

        # Debugger part begin
        dbgSpacer = QWidget()
        dbgSpacer.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        dbgSpacer.setFixedWidth( 40 )
        self.__toolbar.addWidget( dbgSpacer )
        self.__toolbar.addAction( self.__dbgStopBrutal )
        self.__toolbar.addAction( self.__dbgStopAndClearIO )
        self.__toolbar.addAction( self.__dbgStop )
        self.__toolbar.addAction( self.__dbgRestart )
        self.__toolbar.addAction( self.__dbgGo )
        self.__toolbar.addAction( self.__dbgStepInto )
        self.__toolbar.addAction( self.__dbgNext )
        self.__toolbar.addAction( self.__dbgRunToLine )
        self.__toolbar.addAction( self.__dbgReturn )
        self.__toolbar.addAction( self.__dbgJumpToCurrent )
        self.__dbgDumpSettingsAct = self.__toolbar.addWidget(
                                                self.__dbgDumpSettingsButton )

        # Heck! The only QAction can be hidden
        self.__dbgDumpSettingsAct.setVisible( False )
        # Debugger part end

        self.addToolBar( self.__toolbar )
        return

    def getToolbar( self ):
        " Provides the top toolbar reference "
        return self.__toolbar

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
            self.closeAllIOConsoles()
            self.updateToolbarStatus()
            self.updateWindowTitle()

            projectLoaded = GlobalData().project.isLoaded()
            self.__unloadProjectAct.setEnabled( projectLoaded )
            self.__projectPropsAct.setEnabled( projectLoaded )
            self.__prjRopeConfigAct.setEnabled( projectLoaded and
                                os.path.exists( self.__getRopeConfig() ) )
            self.__prjTemplateMenu.setEnabled( projectLoaded )
            self.__findNameMenuAct.setEnabled( projectLoaded )
            self.__fileProjectFileAct.setEnabled( projectLoaded )
            self.__prjPylintAct.setEnabled( projectLoaded )
            self.__prjPymetricsAct.setEnabled( projectLoaded )
            self.__prjLineCounterAct.setEnabled( projectLoaded )
            self.__prjImportDgmAct.setEnabled( projectLoaded )
            self.__prjImportsDgmDlgAct.setEnabled( projectLoaded )

            self.settings.projectLoaded = projectLoaded
            if projectLoaded:
                if os.path.exists( self.__getPylintRCFileName() ):
                    self.__pylintButton.setMenu( self.__existentPylintRCMenu )
                else:
                    self.__pylintButton.setMenu( self.__absentPylintRCMenu )

                # The editor tabs must be loaded after a VCS plugin has a
                # chance to receive projectChanged signal where it reads
                # the plugin configuration
                QTimer.singleShot( 1, self.__delayedEditorsTabRestore )


        self.updateRunDebugButtons()
        return

    def __delayedEditorsTabRestore( self ):
        " Delayed restore editor tabs "
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.restoreTabs( GlobalData().project.tabsStatus )
        return

    def updateWindowTitle( self ):
        """ updates the main window title with the current so file """

        if GlobalData().project.fileName != "":
            self.setWindowTitle( 'Codimension for Python: ' +
                                 os.path.basename(
                                    GlobalData().project.fileName ) )
        else:
            self.setWindowTitle( 'Codimension for Python: no project selected' )
        return

    def updateToolbarStatus( self ):
        " Enables/disables the toolbar buttons "
        projectLoaded = GlobalData().project.isLoaded()
        self.linecounterButton.setEnabled( projectLoaded )
        self.__pylintButton.setEnabled( projectLoaded and
                                        GlobalData().pylintAvailable )
        self.importsDiagramButton.setEnabled( projectLoaded and
                                              GlobalData().graphvizAvailable )
        self.__pymetricsButton.setEnabled( projectLoaded )
        self.__findNameButton.setEnabled( projectLoaded )
        self.__findFileButton.setEnabled( projectLoaded )
        return

    def updateRunDebugButtons( self ):
        " Updates the run/debug buttons statuses "
        if self.debugMode:
            self.runProjectButton.setEnabled( False )
            self.runProjectButton.setToolTip( "Cannot run project - "
                                              "debug in progress" )
            self.debugProjectButton.setEnabled( False )
            self.debugProjectButton.setToolTip( "Cannot debug project - "
                                                "debug in progress" )
            self.__prjDebugAct.setEnabled( False )
            self.__prjDebugDlgAct.setEnabled( False )
            self.__tabDebugAct.setEnabled( False )
            self.__tabDebugDlgAct.setEnabled( False )
            self.profileProjectButton.setEnabled( False )
            self.profileProjectButton.setToolTip( "Cannot profile project - "
                                                  "debug in progress" )
            return

        if not GlobalData().project.isLoaded():
            self.runProjectButton.setEnabled( False )
            self.runProjectButton.setToolTip( "Run project" )
            self.debugProjectButton.setEnabled( False )
            self.debugProjectButton.setToolTip( "Debug project" )
            self.__prjDebugAct.setEnabled( False )
            self.__prjDebugDlgAct.setEnabled( False )
            self.profileProjectButton.setEnabled( False )
            self.profileProjectButton.setToolTip( "Profile project" )
            return

        if not GlobalData().isProjectScriptValid():
            self.runProjectButton.setEnabled( False )
            self.runProjectButton.setToolTip(
                "Cannot run project - script is not specified or invalid" )
            self.debugProjectButton.setEnabled( False )
            self.debugProjectButton.setToolTip(
                "Cannot debug project - script is not specified or invalid" )
            self.__prjDebugAct.setEnabled( False )
            self.__prjDebugDlgAct.setEnabled( False )
            self.profileProjectButton.setEnabled( False )
            self.profileProjectButton.setToolTip(
                "Cannot profile project - script is not specified or invalid" )
            return

        self.runProjectButton.setEnabled( True )
        self.runProjectButton.setToolTip( "Run project" )
        self.debugProjectButton.setEnabled( True )
        self.debugProjectButton.setToolTip( "Debug project" )
        self.__prjDebugAct.setEnabled( True )
        self.__prjDebugDlgAct.setEnabled( True )
        self.profileProjectButton.setEnabled( True )
        self.profileProjectButton.setToolTip( "Profile project" )
        return

    @staticmethod
    def linecounterButtonClicked():
        " Triggered when the line counter button is clicked "
        LineCounterDialog().exec_()
        return

    def findInFilesClicked( self ):
        " Triggered when the find in files button is clicked "

        searchText = ""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget.getType() in \
                [ MainWindowTabWidgetBase.PlainTextEditor ]:
            searchText = currentWidget.getEditor().getSearchText()

        dlg = FindInFilesDialog( FindInFilesDialog.inProject, searchText )
        dlg.exec_()
        if dlg.searchResults:
            self.displayFindInFiles( dlg.searchRegexp, dlg.searchResults )
        return

    def toStdout( self, txt ):
        " Triggered when a new message comes "
        self.showLogTab()
        self.logViewer.append( str( txt ) )
        return

    def toStderr( self, txt ):
        " Triggered when a new message comes "
        self.showLogTab()
        self.logViewer.appendError( str( txt ) )
        return

    def showLogTab( self ):
        " Makes sure that the log tab is visible "
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.logViewer )
        self.__bottomSideBar.raise_()
        return

    def openFile( self, path, lineNo, pos = 0 ):
        " User double clicked on a file or an item in a file "
        self.editorsManagerWidget.editorsManager.openFile( path, lineNo, pos )
        return

    def gotoInBuffer( self, uuid, lineNo ):
        " Usually needs when an item is clicked in the file outline browser "
        self.editorsManagerWidget.editorsManager.gotoInBuffer( uuid, lineNo )
        return

    def jumpToLine( self, lineNo ):
        """ Usually needs when rope provided definition
            in the current unsaved buffer """
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
        if not isFileTypeSearchable( fileType ):
            logging.error( "Cannot open non-text file for editing" )
            return

        self.openFile( path, lineNo )
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

        GlobalData().project.createNew(
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
        self.settings.addRecentProject( dialog.absProjectFileName )
        return

    def notImplementedYet( self ):
        " Shows a dummy window "

        QMessageBox.about( self, 'Not implemented yet',
                "This function has not been implemented yet" )
        return

    def closeEvent( self, event ):
        " Triggered when the IDE is closed "
        # Save the side bars status
        self.settings.vSplitterSizes = self.__verticalSplitterSizes
        self.settings.hSplitterSizes = self.__horizontalSplitterSizes
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

        if editorsManager.closeEvent( event ):
            # The IDE is going to be closed just now
            if self.debugMode:
                self.__onBrutalStopDbgSession()

            project = GlobalData().project
            project.fileBrowserPaths = self.getProjectExpandedPaths()
            project.unloadProject( False )

            # Close the magic library nicely to avoid complaining on implicit
            # DB unloading
            closeMagicLibrary()

            # Stop the VCS manager threads
            self.vcsManager.dismissAllPlugins()

            # Kill all the non-detached processes
            self.__runManager.killAll()

            # On ubuntu codimension produces core dumps coming from QT when:
            # - a new project is created
            # - the IDE is closed via Alt+F4
            # It seems that python GC conflicts with QT at finishing. Explicit
            # call of GC resolves the problem.
            while gc.collect():
                pass

        return

    def dismissVCSPlugin( self, plugin ):
        " Dismisses the given VCS plugin "
        self.vcsManager.dismissPlugin( plugin )
        return

    def getProjectExpandedPaths( self ):
        " Provides a list of expanded project directories "
        project = GlobalData().project
        if project.isLoaded():
            return self.projectViewer.projectTreeView.getExpanded()
        return []

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
        if projectDir:
            # First try project-specific pylintrc
            fName = projectDir + "pylintrc"
            if os.path.exists( fName ):
                pylintrcFile = fName

        if not pylintrcFile:
            # Second try IDE-wide pylintrc
            fName = getIDEPylintFile()
            if os.path.exists( fName ):
                pylintrcFile = fName

        try:
            if projectDir:
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
        self.pylintViewer.showReport( lint, reportOption,
                                        displayName, uuid )

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = self.settings.vSplitterSizes
            splitterSizes[ 0 ] -= 200
            splitterSizes[ 1 ] += 200
            self.__verticalSplitter.setSizes( splitterSizes )

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.pylintViewer )
        self.__bottomSideBar.raise_()
        return

    def showPymetricsReport( self, reportOption, fileOrContent,
                                   displayName, uuid ):
        " Passes data to the pymetrics viewer "

        # This is a python file, let's pymetric it
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        try:
            path = thirdpartyDir + "pymetrics" + os.path.sep + "pymetrics.py"
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
            logging.info( "Note: pymetrics does not work for syntactically "
                          "incorrect files. Please check that your files "
                          "are OK before running pymetrics." )
            return

        QApplication.restoreOverrideCursor()
        self.pymetricsViewer.showReport( metrics, reportOption,
                                           displayName, uuid )

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = self.settings.vSplitterSizes
            splitterSizes[ 0 ] -= 200
            splitterSizes[ 1 ] += 200
            self.__verticalSplitter.setSizes( splitterSizes )

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.pymetricsViewer )
        self.__bottomSideBar.raise_()
        return

    def __calltipDisplayable( self, calltip ):
        " True if calltip is displayable "
        if calltip is None:
            return False
        if calltip.strip() == "":
            return False
        return True

    def __docstringDisplayable( self, docstring ):
        " True if docstring is displayable "
        if docstring is None:
            return False
        if isinstance( docstring, dict ):
            if docstring[ "docstring" ].strip() == "":
                return False
            return True
        if docstring.strip() == "":
            return False
        return True

    def showTagHelp( self, calltip, docstring ):
        " Shows a tag help "
        if not self.__calltipDisplayable( calltip ) and \
           not self.__docstringDisplayable( docstring ):
            return

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.tagHelpViewer )
        self.__bottomSideBar.raise_()

        self.tagHelpViewer.display( calltip, docstring )
        return

    def showDiff( self, diff, tooltip ):
        " Shows the diff "

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.diffViewer )
        self.__bottomSideBar.raise_()

        try:
            self.__bottomSideBar.setTabToolTip( 6, tooltip )
            self.diffViewer.setHTML( parse_from_memory( diff, False, True ),
                                     tooltip )
        except Exception, exc:
            logging.error( "Error showing diff: " + str( exc ) )
        return

    def showDiffInMainArea( self, content, tooltip ):
        " Shows the given diff in the main editing area "
        self.editorsManagerWidget.editorsManager.showDiff( content, tooltip )
        return

    def zoomDiff( self, zoomValue ):
        " Zooms the diff view at the bottom "
        self.diffViewer.zoomTo( zoomValue )
        return

    def zoomIOconsole( self, zoomValue ):
        " Zooms the IO console "
        # Handle run/profile IO consoles and the debug IO console
        index = self.__bottomSideBar.count() - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget( index )
            if hasattr( widget, "getType" ):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.zoomTo( zoomValue )
            index -= 1
        return

    def onIOConsoleSettingUpdated( self ):
        " Initiates updating all the IO consoles settings "
        index = self.__bottomSideBar.count() - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget( index )
            if hasattr( widget, "getType" ):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.consoleSettingsUpdated()
            index -= 1
        return

    def showProfileReport( self, widget, tooltip ):
        " Shows the given profile report "
        self.editorsManagerWidget.editorsManager.showProfileReport( widget,
                                                                    tooltip )
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
        editorsManager = self.editorsManagerWidget.editorsManager
        return editorsManager.getWidgetForFileName( fname )

    def editorsManager( self ):
        " Provides the editors manager "
        return self.editorsManagerWidget.editorsManager

    @staticmethod
    def __buildPythonFilesList():
        " Builds the list of python project files "
        ropeDir = os.path.sep + ".ropeproject" + os.path.sep

        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        filesToProcess = []
        for item in GlobalData().project.filesList:
            if ropeDir in item:
                continue
            if detectFileType( item ) in [ PythonFileType,
                                           Python3FileType ]:
                filesToProcess.append( item )
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        return filesToProcess

    def pylintButtonClicked( self, action = None):
        " Project pylint report is requested "

        filesToProcess = self.__buildPythonFilesList()
        if not filesToProcess:
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
        if not filesToProcess:
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

    @staticmethod
    def __getRopeConfig():
        " Provides the rope config file path "
        projectDir = os.path.dirname( GlobalData().project.fileName )
        if not projectDir.endswith( os.path.sep ):
            projectDir += os.path.sep
        return projectDir + ".ropeproject" + os.path.sep + "config.py"

    def __onRopeConfig( self ):
        " Requests to load rope config file for editing "
        fileName = self.__getRopeConfig()
        if not os.path.exists( fileName ):
            logging.error( "Cannot find the project rope  config file (" +
                           fileName + ")" )
            return
        self.openFile( fileName, -1 )
        return

    def __onEditPylintRC( self ):
        " Request to edit the project pylint rc "
        fileName = self.__getPylintRCFileName()
        if not os.path.exists( fileName ):
            logging.error( "Cannot find the project pylintrc (" +
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
                logging.error( "Error generating the project pylintrc (" +
                               fileName + ")" )
                return
        self.__pylintButton.setMenu( self.__existentPylintRCMenu )
        self.openFile( fileName, -1 )
        return

    def __onCreatePrjTemplate( self ):
        " Triggered when project template should be created "
        self.createTemplateFile( getProjectTemplateFile() )
        return

    def __onEditPrjTemplate( self ):
        " Triggered when project template should be edited "
        self.editTemplateFile( getProjectTemplateFile() )
        return

    @staticmethod
    def __onDelPrjTemplate():
        " Triggered when project template should be deleted "
        fileName = getProjectTemplateFile()
        if fileName is not None:
            if os.path.exists( fileName ):
                os.unlink( fileName )
                logging.info( "Project new file template deleted" )
        return

    def __onCreateIDETemplate( self ):
        " Triggered to create IDE template "
        self.createTemplateFile( getIDETemplateFile() )
        return

    def createTemplateFile( self, fileName ):
        " Creates a template file "
        try:
            f = open( fileName, "w" )
            f.write( getDefaultTemplate() )
            f.close()
        except Exception, exc:
            logging.error( "Error creating a template file: " + str( exc ) )
            return
        self.openFile( fileName, -1 )
        return

    def __onEditIDETemplate( self ):
        " Triggered to edit IDE template "
        self.editTemplateFile( getIDETemplateFile() )
        return

    def editTemplateFile( self, fileName ):
        " Edits the timepale file "
        if fileName is not None:
            if not os.path.exists( fileName ):
                logging.error( "The template file " + fileName +
                               " disappeared from the file system." )
                return
            self.openFile( fileName, -1 )
        return

    @staticmethod
    def __onDelIDETemplate():
        " Triggered to del IDE template "
        fileName = getIDETemplateFile()
        if fileName is not None:
            if os.path.exists( fileName ):
                os.unlink( fileName )
                logging.info( "IDE new file template deleted" )
        return

    def __onCreateIDEPylint( self ):
        " Triggered to create IDE pylint "
        fileName = getIDEPylintFile()
        if not os.path.exists( fileName ):
            if os.system( "pylint --generate-rcfile > " + fileName ) != 0:
                logging.error( "Error generating the project pylintrc (" +
                               fileName + ")" )
                return
        self.openFile( fileName, -1 )
        return

    def __onEditIDEPylint( self ):
        " Triggered to edit IDE pylint "
        fileName = getIDEPylintFile()
        if not os.path.exists( fileName ):
            logging.error( "Cannot find the IDE-wide pylintrc (" +
                           fileName + ")" )
            return
        self.openFile( fileName, -1 )
        return

    @staticmethod
    def __onDelIDEPylint():
        " Triggered to delete IDE pylint "
        fileName = getIDEPylintFile()
        if os.path.exists( fileName ):
            os.unlink( fileName )
        return

    def __onFSChanged( self, items ):
        " Update the pylint button menu if pylintrc appeared/disappeared "
        pylintRCFileName = self.__getPylintRCFileName()
        for path in items:
            path = str( path )
            if path.endswith( pylintRCFileName ):
                if path.startswith( '+' ):
                    self.__pylintButton.setMenu( self.__existentPylintRCMenu )
                else:
                    self.__pylintButton.setMenu( self.__absentPylintRCMenu )
                break
        return

    def displayFindInFiles( self, searchRegexp, searchResults ):
        " Displays the results on a tab "
        self.findInFilesViewer.showReport( searchRegexp, searchResults )

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = self.settings.vSplitterSizes
            splitterSizes[ 0 ] -= 200
            splitterSizes[ 1 ] += 200
            self.__verticalSplitter.setSizes( splitterSizes )

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.findInFilesViewer )
        self.__bottomSideBar.raise_()
        return

    @staticmethod
    def findNameClicked():
        " Find name dialog should come up "
        try:
            FindNameDialog().exec_()
        except Exception, exc:
            logging.error( str( exc ) )
        return

    @staticmethod
    def findFileClicked():
        " Find file dialog should come up "
        try:
            FindFileDialog().exec_()
        except Exception, exc:
            logging.error( str( exc ) )
        return

    @staticmethod
    def hideTooltips():
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
        self.__runManager.run( fileName, True )
        return

    def __onProfileProjectSettings( self ):
        " Brings up the dialog with profile script settings "
        if self.__checkProjectScriptValidity() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        params = GlobalData().getRunParameters( fileName )
        termType = self.settings.terminalType
        profilerParams = self.settings.getProfilerSettings()
        debuggerParams = self.settings.getDebuggerSettings()
        dlg = RunDialog( fileName, params, termType,
                         profilerParams, debuggerParams, "Profile" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                self.settings.terminalType = dlg.termType
            if dlg.profilerParams != profilerParams:
                self.settings.setProfilerSettings( dlg.profilerParams )
            self.__onProfileProject()
        return

    def __onDebugProjectSettings( self ):
        " Brings up the dialog with debug script settings "
        if self.__checkDebugPrerequisites() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        params = GlobalData().getRunParameters( fileName )
        termType = self.settings.terminalType
        profilerParams = self.settings.getProfilerSettings()
        debuggerParams = self.settings.getDebuggerSettings()
        dlg = RunDialog( fileName, params, termType,
                         profilerParams, debuggerParams, "Debug" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                self.settings.terminalType = dlg.termType
            if dlg.debuggerParams != debuggerParams:
                self.settings.setDebuggerSettings( dlg.debuggerParams )
            self.__onDebugProject()
        return

    def __onRunProject( self, action = False ):
        " Runs the project with saved sattings "
        if self.__checkProjectScriptValidity() == False:
            return

        fileName = GlobalData().project.getProjectScript()
        self.__runManager.run( fileName, False )
        return

    def __onProfileProject( self, action = False ):
        " Profiles the project with saved settings "
        if self.__checkProjectScriptValidity() == False:
            return

        try:
            dlg = ProfilingProgressDialog(
                        GlobalData().project.getProjectScript(), self )
            dlg.exec_()
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def __onDebugProject( self, action = False ):
        " Debugging is requested "
        if self.debugMode:
            return
        if self.__checkDebugPrerequisites():
            self.debugScript( GlobalData().project.getProjectScript() )
        return

    def debugScript( self, fileName ):
        " Runs a script to debug "
        if self.debugMode:
            return
        self.__debugger.startDebugging( fileName )
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
            logging.error( "Invalid project script. "
                           "Use project properties dialog to "
                           "select existing python script." )
            return False
        return True

    def __verticalEdgeChanged( self ):
        " Editor setting changed "
        self.settings.verticalEdge = not self.settings.verticalEdge
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __showSpacesChanged( self ):
        " Editor setting changed "
        self.settings.showSpaces = not self.settings.showSpaces
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __lineWrapChanged( self ):
        " Editor setting changed "
        self.settings.lineWrap = not self.settings.lineWrap
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __showEOLChanged( self ):
        " Editor setting changed "
        self.settings.showEOL = not self.settings.showEOL
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __showBraceMatchChanged( self ):
        " Editor setting changed "
        self.settings.showBraceMatch = not self.settings.showBraceMatch
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __autoIndentChanged( self ):
        " Editor setting changed "
        self.settings.autoIndent = not self.settings.autoIndent
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __backspaceUnindentChanged( self ):
        " Editor setting changed "
        self.settings.backspaceUnindent = not self.settings.backspaceUnindent
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __tabIndentsChanged( self ):
        " Editor setting changed "
        self.settings.tabIndents = not self.settings.tabIndents
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __indentationGuidesChanged( self ):
        " Editor setting changed "
        self.settings.indentationGuides = not self.settings.indentationGuides
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __currentLineVisibleChanged( self ):
        " Editor setting changed "
        self.settings.currentLineVisible = not self.settings.currentLineVisible
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __homeToFirstNonSpaceChanged( self ):
        " Editor setting changed "
        self.settings.jumpToFirstNonSpace = \
                                not self.settings.jumpToFirstNonSpace
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __removeTrailingChanged( self ):
        " Editor setting changed "
        self.settings.removeTrailingOnSave = \
                                not self.settings.removeTrailingOnSave
        return

    def __editorCalltipsChanged( self ):
        " Editor calltips changed "
        self.settings.editorCalltips = not self.settings.editorCalltips
        return

    def __clearDebugIOChanged( self ):
        " Clear debug IO console before a new session changed "
        self.settings.clearDebugIO = not self.settings.clearDebugIO
        return

    def __showNavBarChanged( self ):
        " Editor setting changed "
        self.settings.showNavigationBar = \
                                not self.settings.showNavigationBar
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()
        return

    def __projectTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.projectTooltips = \
                                not self.settings.projectTooltips
        self.projectViewer.setTooltips( self.settings.projectTooltips )
        return

    def __recentTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.recentTooltips = \
                                not self.settings.recentTooltips
        self.recentProjectsViewer.setTooltips( self.settings.recentTooltips )
        return

    def __classesTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.classesTooltips = \
                                not self.settings.classesTooltips
        self.classesViewer.setTooltips( self.settings.classesTooltips )
        return

    def __functionsTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.functionsTooltips = \
                                not self.settings.functionsTooltips
        self.functionsViewer.setTooltips( self.settings.functionsTooltips )
        return

    def __outlineTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.outlineTooltips = \
                                not self.settings.outlineTooltips
        self.outlineViewer.setTooltips( self.settings.outlineTooltips )
        return

    def __findNameTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.findNameTooltips = \
                                not self.settings.findNameTooltips
        return

    def __findFileTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.findFileTooltips = \
                                not self.settings.findFileTooltips
        return

    def __editorTooltipsChanged( self ):
        " Tooltips setting changed "
        self.settings.editorTooltips = \
                                not self.settings.editorTooltips
        self.editorsManagerWidget.editorsManager.setTooltips(
                        self.settings.editorTooltips )
        return

    def __tabOrderPreservedChanged( self ):
        " Tab order preserved option changed "
        self.settings.taborderpreserved = \
                                not self.settings.taborderpreserved
        return

    def __openTabsMenuTriggered( self, act ):
        " Tab list settings menu triggered "
        value, isOK = act.data().toInt()
        if isOK:
            if value == -1:
                self.settings.tablistsortalpha = True
                self.__alphasort.setChecked( True )
                self.__tabsort.setChecked( False )
            elif value == -2:
                self.settings.tablistsortalpha = False
                self.__alphasort.setChecked( False )
                self.__tabsort.setChecked( True )
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
                if not os.path.exists( localSkinsDir + item +
                                       os.path.sep + "application.css" ) or \
                   not os.path.exists( localSkinsDir + item +
                                       os.path.sep + "general" ) or \
                   not os.path.exists( localSkinsDir + item +
                                       os.path.sep + "lexers" ):
                    continue
                # Get the theme display name from the general file
                config = ConfigParser.ConfigParser()
                try:
                    config.read( [ localSkinsDir + item +
                                   os.path.sep + "general" ] )
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
                if not os.path.exists( skinsDir + item +
                                       os.path.sep + "application.css" ) or \
                   not os.path.exists( skinsDir + item +
                                       os.path.sep + "general" ) or \
                   not os.path.exists( skinsDir + item +
                                       os.path.sep + "lexers" ):
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
        if self.settings.skin == skinSubdir:
            return

        logging.info( "Please restart codimension to apply the new theme" )
        self.settings.skin = skinSubdir
        return

    def __styleAboutToShow( self ):
        " Style menu is about to show "
        currentStyle = self.settings.style.lower()
        for item in self.__styles:
            font = item[ 1 ].font()
            if item[ 0 ].lower() == currentStyle:
                font.setBold( True )
            else:
                font.setBold( False )
            item[ 1 ].setFont( font )
        return

    def __onStyle( self, act ):
        " Sets the selected style "
        styleName = str( act.data().toString() )
        QApplication.setStyle( styleName )
        self.settings.style = styleName.lower()
        return

    def __onMonoFont( self, act ):
        " Sets the new mono font "
        fontFace = str( act.data().toString() )
        try:
            font = QFont()
            font.setFamily( fontFace )
            GlobalData().skin.setMainEditorFont( font )
            GlobalData().skin.setBaseMonoFontFace( fontFace )
        except Exception as exc:
            logging.error( str( exc ) )
            return

        logging.info( "Please restart codimension to apply the new font" )
        return

    def showStatusBarMessage( self, msg, slot, timeout = 10000 ):
        " Shows a temporary status bar message, default 10sec "
        self.statusBarSlots.showMessage( msg, slot, timeout )
        return

    def clearStatusBarMessage( self, slot ):
        " Clears the status bar message in the given slot "
        self.statusBarSlots.clearMessage( slot )
        return

    def checkOutsideFileChanges( self ):
        """ Checks if there are changes in the files
            currently loaded by codimension """
        self.editorsManagerWidget.editorsManager.checkOutsideFileChanges()
        return

    def __getPathLabelFilePath( self ):
        " Provides undecorated path label content "
        txt = str( self.sbFile.getPath() )
        if txt.startswith( "File: " ):
            txt = txt.replace( "File: ", "" )
        return txt

    def __onPathLabelDoubleClick( self ):
        " Double click on the status bar path label "
        txt = self.__getPathLabelFilePath()
        if txt not in [ "", "N/A" ]:
            QApplication.clipboard().setText( txt )
        return

    def __onCopyDirToClipboard( self ):
        " Copies the dir path of the current file into the clipboard "
        txt = self.__getPathLabelFilePath()
        if txt not in [ "", "N/A" ]:
            try:
                QApplication.clipboard().setText( os.path.dirname( txt ) +
                                                  os.path.sep )
            except:
                pass
        return

    def __onCopyFileNameToClipboard( self ):
        " Copies the file name of the current file into the clipboard "
        txt = self.__getPathLabelFilePath()
        if txt not in [ "", "N/A" ]:
            try:
                QApplication.clipboard().setText( os.path.basename( txt ) )
            except:
                pass
        return

    def __onVCSMonitorInterval( self ):
        " Runs the VCS monitor interval setting dialog "
        dlg = VCSUpdateIntervalConfigDialog(
                            self.settings.vcsstatusupdateinterval, self )
        if dlg.exec_() == QDialog.Accepted:
            self.settings.vcsstatusupdateinterval = dlg.interval
        return

    def __showPathLabelContextMenu( self, pos ):
        " Triggered when a context menu is requested for the path label "
        contextMenu = QMenu( self )
        contextMenu.addAction( PixmapCache().getIcon( "copytoclipboard.png" ),
                               "Copy full path to clipboard (double click)",
                               self.__onPathLabelDoubleClick )
        contextMenu.addSeparator()
        contextMenu.addAction( PixmapCache().getIcon( "" ),
                               "Copy directory path to clipboard",
                               self.__onCopyDirToClipboard )
        contextMenu.addAction( PixmapCache().getIcon( "" ),
                               "Copy file name to clipboard",
                               self.__onCopyFileNameToClipboard )
        contextMenu.popup( self.sbFile.mapToGlobal( pos ) )
        return

    def __showVCSLabelContextMenu( self, pos ):
        " Triggered when a context menu is requested for a VCS label "
        contextMenu = QMenu( self )
        contextMenu.addAction( PixmapCache().getIcon( "vcsintervalmenu.png" ),
                               "Configure monitor interval",
                               self.__onVCSMonitorInterval )
        contextMenu.popup( self.sbVCSStatus.mapToGlobal( pos ) )
        return

    def switchDebugMode( self, newState ):
        " Switches the debug mode to the desired "
        if self.debugMode == newState:
            return

        self.debugMode = newState
        self.__removeCurrenDebugLineHighlight()
        clearValidBreakpointLinesCache()

        # Satatus bar
        self.dbgState.setVisible( newState )
        self.sbLanguage.setVisible( not newState )
        self.sbEncoding.setVisible( not newState )
        self.sbEol.setVisible( not newState )

        # Toolbar buttons
        self.__dbgStopBrutal.setVisible( newState and
                                         self.settings.terminalType != TERM_REDIRECT )
        self.__dbgStopAndClearIO.setVisible( newState and
                                             self.settings.terminalType == TERM_REDIRECT )
        self.__dbgStop.setVisible( newState )
        self.__dbgRestart.setVisible( newState )
        self.__dbgGo.setVisible( newState )
        self.__dbgNext.setVisible( newState )
        self.__dbgStepInto.setVisible( newState )
        self.__dbgRunToLine.setVisible( newState )
        self.__dbgReturn.setVisible( newState )
        self.__dbgJumpToCurrent.setVisible( newState )
        self.__dbgDumpSettingsAct.setVisible( newState )

        if newState == False:
            self.__debugStopBrutalAct.setEnabled( False )
            self.__debugStopAct.setEnabled( False )
            self.__debugRestartAct.setEnabled( False )
            self.__debugContinueAct.setEnabled( False )
            self.__debugStepOverAct.setEnabled( False )
            self.__debugStepInAct.setEnabled( False )
            self.__debugStepOutAct.setEnabled( False )
            self.__debugRunToCursorAct.setEnabled( False )
            self.__debugJumpToCurrentAct.setEnabled( False )
            self.__debugDumpSettingsAct.setEnabled( False )
            self.__debugDumpSettingsEnvAct.setEnabled( False )

        self.updateRunDebugButtons()

        # Tabs at the right
        if newState == True:
            self.__rightSideBar.setTabEnabled( 1, True )    # vars etc.
            self.debuggerContext.clear()
            self.debuggerExceptions.clear()
            self.__rightSideBar.setTabText( 2, "Exceptions" )
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.debuggerContext )
            self.__rightSideBar.raise_()
            self.__lastDebugAction = None
            self.__debugDumpSettingsAct.setEnabled( True )
            self.__debugDumpSettingsEnvAct.setEnabled( True )
        else:
            if not self.__rightSideBar.isMinimized():
                if self.__rightSideBar.currentIndex() == 1:
                    self.__rightSideBar.setCurrentWidget( self.outlineViewer )
            self.__rightSideBar.setTabEnabled( 1, False )    # vars etc.

        self.emit( SIGNAL( 'debugModeChanged' ), newState )
        return

    def __onDebuggerStateChanged( self, newState ):
        " Triggered when the debugger reported its state changed "
        if newState != CodimensionDebugger.STATE_IN_IDE:
            self.__removeCurrenDebugLineHighlight()
            self.debuggerContext.switchControl( False )
        else:
            self.debuggerContext.switchControl( True )

        if newState == CodimensionDebugger.STATE_STOPPED:
            self.__dbgStopBrutal.setEnabled( False )
            self.__dbgStopAndClearIO.setEnabled( False )
            self.__debugStopBrutalAct.setEnabled( False )
            self.__dbgStop.setEnabled( False )
            self.__debugStopAct.setEnabled( False )
            self.__dbgRestart.setEnabled( False )
            self.__debugRestartAct.setEnabled( False )
            self.__setDebugControlFlowButtonsState( False )
            self.dbgState.setText( "Debugger: stopped" )
            self.redirectedIOConsole.sessionStopped()
        elif newState == CodimensionDebugger.STATE_PROLOGUE:
            self.__dbgStopBrutal.setEnabled( True )
            self.__dbgStopAndClearIO.setEnabled( True )
            self.__debugStopBrutalAct.setEnabled( self.settings.terminalType != TERM_REDIRECT )
            self.__dbgStop.setEnabled( False )
            self.__debugStopAct.setEnabled( False )
            self.__dbgRestart.setEnabled( False )
            self.__debugRestartAct.setEnabled( False )
            self.__setDebugControlFlowButtonsState( False )
            self.dbgState.setText( "Debugger: prologue" )
        elif newState == CodimensionDebugger.STATE_IN_IDE:
            self.__dbgStopBrutal.setEnabled( True )
            self.__dbgStopAndClearIO.setEnabled( True )
            self.__debugStopBrutalAct.setEnabled( self.settings.terminalType != TERM_REDIRECT )
            self.__dbgStop.setEnabled( True )
            self.__debugStopAct.setEnabled( True )
            self.__dbgRestart.setEnabled( True )
            self.__debugRestartAct.setEnabled( True )
            self.__setDebugControlFlowButtonsState( True )
            self.dbgState.setText( "Debugger: idle" )
        elif newState == CodimensionDebugger.STATE_IN_CLIENT:
            self.__dbgStopBrutal.setEnabled( True )
            self.__dbgStopAndClearIO.setEnabled( True )
            self.__debugStopBrutalAct.setEnabled( self.settings.terminalType != TERM_REDIRECT )
            self.__dbgStop.setEnabled( True )
            self.__debugStopAct.setEnabled( True )
            self.__dbgRestart.setEnabled( True )
            self.__debugRestartAct.setEnabled( True )
            self.__setDebugControlFlowButtonsState( False )
            self.dbgState.setText( "Debugger: running" )
        elif newState == CodimensionDebugger.STATE_FINISHING:
            self.__dbgStopBrutal.setEnabled( True )
            self.__dbgStopAndClearIO.setEnabled( True )
            self.__debugStopBrutalAct.setEnabled( self.settings.terminalType != TERM_REDIRECT )
            self.__dbgStop.setEnabled( False )
            self.__debugStopAct.setEnabled( False )
            self.__dbgRestart.setEnabled( False )
            self.__debugRestartAct.setEnabled( False )
            self.__setDebugControlFlowButtonsState( False )
            self.dbgState.setText( "Debugger: finishing" )
        elif newState == CodimensionDebugger.STATE_BRUTAL_FINISHING:
            self.__dbgStopBrutal.setEnabled( False )
            self.__dbgStopAndClearIO.setEnabled( False )
            self.__debugStopBrutalAct.setEnabled( False )
            self.__dbgStop.setEnabled( False )
            self.__dbgStop.setEnabled( False )
            self.__dbgRestart.setEnabled( False )
            self.__debugRestartAct.setEnabled( False )
            self.__setDebugControlFlowButtonsState( False )
            self.dbgState.setText( "Debugger: force finishing" )
        QApplication.processEvents()
        return

    def __onDebuggerCurrentLine( self, fileName, lineNumber, isStack, asException = False ):
        " Triggered when the client reported a new line "
        self.__removeCurrenDebugLineHighlight()

        self.__lastDebugFileName = fileName
        self.__lastDebugLineNumber = lineNumber
        self.__lastDebugAsException = asException
        self.__onDbgJumpToCurrent()
        return

    def __onDebuggerClientException( self, excType, excMessage, excStackTrace ):
        " Debugged program exception handler "

        self.debuggerExceptions.addException( excType, excMessage,
                                              excStackTrace )
        count = self.debuggerExceptions.getTotalClientExceptionCount()
        self.__rightSideBar.setTabText( 2, "Exceptions (" + str( count ) + ")" )

        # The information about the exception is stored in the exception window
        # regardless whether there is a stack trace or not. So, there is no
        # need to show the exception info in the closing dialog (if this dialog
        # is required).

        if excType is None or excType.startswith( "unhandled" ) or not excStackTrace:
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.debuggerExceptions )
            self.__rightSideBar.raise_()

            if not excStackTrace:
                message = "An exception did not report the stack trace.\n" \
                          "The debugging session will be closed."
            else:
                message = "An unhandled exception occured.\n" \
                          "The debugging session will be closed."

            dlg = QMessageBox( QMessageBox.Critical, "Debugging session",
                               message )
            dlg.addButton( QMessageBox.Ok )
            dlg.addButton( QMessageBox.Cancel )

            btn1 = dlg.button( QMessageBox.Ok )
            btn1.setText( "&Close debug console" )
            btn1.setIcon( PixmapCache().getIcon( '' ) )

            btn2 = dlg.button( QMessageBox.Cancel )
            btn2.setText( "&Keep debug console" )
            btn2.setIcon( PixmapCache().getIcon( '' ) )

            dlg.setDefaultButton( QMessageBox.Ok )
            res = dlg.exec_()

            if res == QMessageBox.Cancel:
                QTimer.singleShot( 0, self.__onStopDbgSession )
            else:
                QTimer.singleShot( 0, self.__onBrutalStopDbgSession )
            self.debuggerExceptions.setFocus()
            return


        if self.debuggerExceptions.isIgnored( str( excType ) ):
            # Continue the last action
            if self.__lastDebugAction is None:
                self.__debugger.remoteContinue()
            elif self.__lastDebugAction == self.DEBUG_ACTION_GO:
                self.__debugger.remoteContinue()
            elif self.__lastDebugAction == self.DEBUG_ACTION_NEXT:
                self.__debugger.remoteStepOver()
            elif self.__lastDebugAction == self.DEBUG_ACTION_STEP_INTO:
                self.__debugger.remoteStep()
            elif self.__lastDebugAction == self.DEBUG_ACTION_RUN_TO_LINE:
                self.__debugger.remoteContinue()
            elif self.__lastDebugAction == self.DEBUG_ACTION_STEP_OUT:
                self.__debugger.remoteStepOut()
            return

        # Should stop at the exception
        self.__rightSideBar.show()
        self.__rightSideBar.setCurrentWidget( self.debuggerExceptions )
        self.__rightSideBar.raise_()

        fileName = excStackTrace[ 0 ][ 0 ]
        lineNumber = excStackTrace[ 0 ][ 1 ]
        self.__onDebuggerCurrentLine( fileName, lineNumber, False, True )
        self.__debugger.remoteThreadList()

        # If a stack is explicitly requested then the only deepest frame
        # is reported. It is better to stick with the exception stack
        # for the time beeing.
        self.debuggerContext.onClientStack( excStackTrace )

        self.__debugger.remoteClientVariables( 1, 0 ) # globals
        self.__debugger.remoteClientVariables( 0, 0 ) # locals
        self.debuggerExceptions.setFocus()
        return

    def __onDebuggerClientSyntaxError( self, errMessage, fileName, lineNo, charNo ):
        " Triggered when the client reported a syntax error "

        if errMessage is None:
            message = "The program being debugged contains an unspecified " \
                      "syntax error.\nDebugging session will be closed."
        else:
            # Jump to the source code
            editorsManager = self.editorsManagerWidget.editorsManager
            editorsManager.openFile( fileName, lineNo )
            editor = editorsManager.currentWidget().getEditor()
            editor.gotoLine( lineNo, charNo )

            message = "The file " + fileName + " contains syntax error: '" + \
                       errMessage + "' " \
                       "at line " + str( lineNo ) + ", position " + str( charNo ) + \
                       ".\nDebugging session will be closed."

        dlg = QMessageBox( QMessageBox.Critical, "Debugging session",
                           message )

        if self.settings.terminalType == TERM_REDIRECT:
            dlg.addButton( QMessageBox.Ok )
        else:
            dlg.addButton( QMessageBox.Ok )
            dlg.addButton( QMessageBox.Cancel )

            btn1 = dlg.button( QMessageBox.Ok )
            btn1.setText( "&Close debug console" )
            btn1.setIcon( PixmapCache().getIcon( '' ) )

            btn2 = dlg.button( QMessageBox.Cancel )
            btn2.setText( "&Keep debug console" )
            btn2.setIcon( PixmapCache().getIcon( '' ) )

        dlg.setDefaultButton( QMessageBox.Ok )
        res = dlg.exec_()

        if res == QMessageBox.Cancel or \
           self.settings.terminalType == TERM_REDIRECT:
            QTimer.singleShot( 0, self.__onStopDbgSession )
        else:
            QTimer.singleShot( 0, self.__onBrutalStopDbgSession )
        return

    def __onDebuggerClientIDEMessage( self, message ):
        " Triggered when the debug server has something to report "
        if self.settings.terminalType == TERM_REDIRECT:
            self.__ioconsoleIDEMessage( message )
        else:
            logging.info( message )
        return

    def __removeCurrenDebugLineHighlight( self ):
        " Removes the current debug line highlight "
        if self.__lastDebugFileName is not None:
            editorsManager = self.editorsManagerWidget.editorsManager
            widget = editorsManager.getWidgetForFileName(
                                                self.__lastDebugFileName )
            if widget is not None:
                widget.getEditor().clearCurrentDebuggerLine()
            self.__lastDebugFileName = None
            self.__lastDebugLineNumber = None
            self.__lastDebugAsException = None
        return

    def __setDebugControlFlowButtonsState( self, enabled ):
        " Sets the control flow debug buttons state "
        self.__dbgGo.setEnabled( enabled )
        self.__debugContinueAct.setEnabled( enabled )
        self.__dbgNext.setEnabled( enabled )
        self.__debugStepOverAct.setEnabled( enabled )
        self.__dbgStepInto.setEnabled( enabled )
        self.__debugStepInAct.setEnabled( enabled )
        self.__dbgReturn.setEnabled( enabled )
        self.__debugStepOutAct.setEnabled( enabled )
        self.__dbgJumpToCurrent.setEnabled( enabled )
        self.__debugJumpToCurrentAct.setEnabled( enabled )

        if enabled:
            self.setRunToLineButtonState()
        else:
            self.__dbgRunToLine.setEnabled( False )
            self.__debugRunToCursorAct.setEnabled( False )
        return

    def setRunToLineButtonState( self ):
        " Sets the Run To Line button state "
        # Separate story:
        # - no run to unbreakable line
        # - no run for non-python file
        if not self.debugMode:
            self.__dbgRunToLine.setEnabled( False )
            self.__debugRunToCursorAct.setEnabled( False )
            return
        if not self.__isPythonBuffer():
            self.__dbgRunToLine.setEnabled( False )
            self.__debugRunToCursorAct.setEnabled( False )
            return

        # That's for sure a python buffer, so the widget exists
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget.getType() in [ MainWindowTabWidgetBase.VCSAnnotateViewer ]:
            self.__dbgRunToLine.setEnabled( False )
            self.__debugRunToCursorAct.setEnabled( False )
            return

        enabled = currentWidget.isLineBreakable()
        self.__dbgRunToLine.setEnabled( enabled )
        self.__debugRunToCursorAct.setEnabled( enabled )
        return

    def __onBrutalStopDbgSession( self ):
        " Stop debugging brutally "
        self.__debugger.stopDebugging( True )
        if self.settings.terminalType == TERM_REDIRECT:
            self.redirectedIOConsole.clear()
        return

    def __onStopDbgSession( self ):
        " Debugger stop debugging clicked "
        self.__debugger.stopDebugging( False )
        return

    def __onRestartDbgSession( self ):
        " Debugger restart session clicked "
        fileName = self.__debugger.getScriptPath()
        self.__onBrutalStopDbgSession()
        self.__debugger.startDebugging( fileName )
        return

    def __onDbgGo( self ):
        " Debugger continue clicked "
        self.__lastDebugAction = self.DEBUG_ACTION_GO
        self.__debugger.remoteContinue()
        return

    def __onDbgNext( self ):
        " Debugger step over clicked "
        self.__lastDebugAction = self.DEBUG_ACTION_NEXT
        self.__debugger.remoteStepOver()
        return

    def __onDbgStepInto( self ):
        " Debugger step into clicked "
        self.__lastDebugAction = self.DEBUG_ACTION_STEP_INTO
        self.__debugger.remoteStep()
        return

    def __onDbgRunToLine( self ):
        " Debugger run to cursor clicked "
        # The run-to-line button state is set approprietly
        if not self.__dbgRunToLine.isEnabled():
            return

        self.__lastDebugAction = self.DEBUG_ACTION_RUN_TO_LINE
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        self.__debugger.remoteBreakpoint( currentWidget.getFileName(),
                                          currentWidget.getLine() + 1,
                                          True, None, True )
        self.__debugger.remoteContinue()
        return

    def __onDbgReturn( self ):
        " Debugger step out clicked "
        self.__lastDebugAction = self.DEBUG_ACTION_STEP_OUT
        self.__debugger.remoteStepOut()
        return

    def __onDbgJumpToCurrent( self ):
        " Jump to the current debug line "
        if self.__lastDebugFileName is None or \
           self.__lastDebugLineNumber is None or \
           self.__lastDebugAsException is None:
            return

        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.openFile( self.__lastDebugFileName,
                                 self.__lastDebugLineNumber )

        editor = editorsManager.currentWidget().getEditor()
        editor.gotoLine( self.__lastDebugLineNumber )
        editor.highlightCurrentDebuggerLine( self.__lastDebugLineNumber,
                                             self.__lastDebugAsException )
        editorsManager.currentWidget().setFocus()
        return

    def __openProject( self ):
        " Shows up a dialog to open a project "
        if self.debugMode:
            return
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
            logging.warning( "The selected project to load is "
                             "the currently loaded one." )
            return

        if detectFileType( fileName ) != CodimensionProjectFileType:
            logging.warning( "Codimension project file "
                             "must have .cdm extension" )
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
            if not self.__leftSideBar.isMinimized():
                self.activateProjectTab()
        QApplication.restoreOverrideCursor()
        return

    def __openFile( self ):
        " Triggers when Ctrl+O is pressed "

        dialog = QFileDialog( self, 'Open file' )
        dialog.setFileMode( QFileDialog.ExistingFiles )
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )

        editorsManager = self.editorsManagerWidget.editorsManager
        try:
            fileName = editorsManager.currentWidget().getFileName()
            if os.path.isabs( fileName ):
                dirName = os.path.dirname( fileName )
                url = QUrl.fromLocalFile( dirName )
                if not url in urls:
                    urls.append( url )
        except:
            pass

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

        for fileName in dialog.selectedFiles():
            try:
                self.detectTypeAndOpenFile( os.path.realpath( str( fileName ) ) )
            except Exception, exc:
                logging.error( str( exc ) )
        return

    def __isPlainTextBuffer( self ):
        " Provides if saving is enabled "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
                    [ MainWindowTabWidgetBase.PlainTextEditor,
                      MainWindowTabWidgetBase.VCSAnnotateViewer ]

    def __isTemporaryBuffer( self ):
        " True if it is a temporary text buffer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
                    [ MainWindowTabWidgetBase.VCSAnnotateViewer ]

    def __isPythonBuffer( self ):
        " True if the current tab is a python buffer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
                [ MainWindowTabWidgetBase.PlainTextEditor,
                  MainWindowTabWidgetBase.VCSAnnotateViewer ] and \
               currentWidget.getFileType() in \
                            [ PythonFileType, Python3FileType ]

    def __isGraphicsBuffer( self ):
        " True if is pictures viewer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.PictureViewer

    def __isGeneratedDiagram( self ):
        " True if this is a generated diagram "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        if currentWidget.getType() == MainWindowTabWidgetBase.GeneratedDiagram:
            return True
        if currentWidget.getType() == MainWindowTabWidgetBase.ProfileViewer:
            if currentWidget.isDiagramActive():
                return True
        return False

    def __isProfileViewer( self ):
        " True if this is a profile viewer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.ProfileViewer

    def __isDiffViewer( self ):
        " True if this is a diff viewer "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.DiffViewer

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

    def onRunTab( self ):
        " Triggered when run tab script is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        self.__runManager.run( currentWidget.getFileName(), False )
        return

    def __onDebugTab( self ):
        " Triggered when debug tab is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onDebugScript()
        return

    def __onProfileTab( self ):
        " Triggered when profile script is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onProfileScript()
        return

    def onRunTabDlg( self ):
        " Triggered when run tab script dialog is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        self.__runManager.run( currentWidget.getFileName(), True )
        return

    def __onDebugTabDlg( self ):
        " Triggered when debug tab script dialog is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onDebugScriptSettings()
        return

    def __onProfileTabDlg( self ):
        " Triggered when profile tab script dialog is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onProfileScriptSettings()
        return

    def __onPluginManager( self ):
        " Triggered when a plugin manager dialog is requested "
        dlg = PluginsDialog( GlobalData().pluginManager, self )
        dlg.exec_()
        return

    def __onContextHelp( self ):
        " Triggered when Ctrl+F1 is clicked "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onTagHelp()
        return

    def __onCallHelp( self ):
        " Triggered when a context help for the current call is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onCallHelp()
        return


    @staticmethod
    def __onHomePage():
        " Triggered when opening the home page is requested "
        QDesktopServices.openUrl( QUrl( "http://satsky.spb.ru/codimension/" ) )
        return

    @staticmethod
    def __onAllShortcurs():
        " Triggered when opening key bindings page is requested"
        QDesktopServices.openUrl(
            QUrl( "http://satsky.spb.ru/codimension/keyBindingsEng.php" ) )
        return

    def __onAbout( self ):
        " Triggered when 'About' info is requested "
        dlg = AboutDialog( self )
        dlg.exec_()
        return

    def __activateSideTab( self, act ):
        " Triggered when a side bar should be activated "
        name = str( act.data().toString() )
        if name == "prj":
            self.activateProjectTab()
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
            self.__rightSideBar.setCurrentWidget( self.outlineViewer )
            self.__rightSideBar.raise_()
        elif name == "debug":
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.debuggerContext )
            self.__rightSideBar.raise_()
        elif name == "excpt":
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.debuggerExceptions )
            self.__rightSideBar.raise_()
        elif name == "bpoint":
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentWidget( self.debuggerBreakWatchPoints )
            self.__rightSideBar.raise_()
        elif name == "log":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.logViewer )
            self.__bottomSideBar.raise_()
        elif name == "pylint":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.pylintViewer )
            self.__bottomSideBar.raise_()
        elif name == "pymetrics":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.pymetricsViewer )
            self.__bottomSideBar.raise_()
        elif name == "search":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.findInFilesViewer )
            self.__bottomSideBar.raise_()
        elif name == "contexthelp":
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.tagHelpViewer )
            self.__bottomSideBar.raise_()
        elif name == 'diff':
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentWidget( self.diffViewer )
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

    def __onTabPythonTidy( self ):
        " Triggered when python tidy is requested for a tab "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onPythonTidy()
        return

    def __onTabPythonTidyDlg( self ):
        " Triggered when python tidy with settings is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onPythonTidySettings()
        return

    def __onTabJumpToDef( self ):
        " Triggered when jump to defenition is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onGotoDefinition()
        return

    def __onTabJumpToScopeBegin( self ):
        """ Triggered when jump to the beginning
            of the current scope is requested """
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onScopeBegin()
        return

    def __onFindOccurences( self ):
        " Triggered when search for occurences is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onOccurences()
        return

    def findWhereUsed( self, fileName, item ):
        " Find occurences for c/f/g browsers "

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        # False for no exceptions
        locations = getOccurrences( fileName, item.absPosition, False )
        if len( locations ) == 0:
            QApplication.restoreOverrideCursor()
            self.showStatusBarMessage( "No occurrences of " +
                                       item.name + " found.", 0 )
            return

        # Process locations for find results window
        result = []
        for loc in locations:
            index = getSearchItemIndex( result, loc[ 0 ] )
            if index < 0:
                widget = self.getWidgetForFileName( loc[0] )
                if widget is None:
                    uuid = ""
                else:
                    uuid = widget.getUUID()
                newItem = ItemToSearchIn( loc[ 0 ], uuid )
                result.append( newItem )
                index = len( result ) - 1
            result[ index ].addMatch( item.name, loc[ 1 ] )

        QApplication.restoreOverrideCursor()

        self.displayFindInFiles( "", result )
        return

    def __onTabOpenImport( self ):
        " Triggered when open import is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onOpenImport()
        return

    def __onShowCalltip( self ):
        " Triggered when show calltip is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onShowCalltip()
        return

    def __onOpenAsFile( self ):
        " Triggered when open as file is requested "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().openAsFile()
        return

    def __onDownloadAndShow( self ):
        " Triggered when a selected string should be treated as URL "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().downloadAndShow()
        return

    def __onOpenInBrowser( self ):
        " Triggered when a selected url should be opened in a browser "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().openInBrowser()
        return

    def __onHighlightInOutline( self ):
        " Triggered to highlight the current context in the outline browser "
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().highlightInOutline()
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

    def __getEditor( self ):
        " Provides reference to the editor "
        editorsManager = self.editorsManagerWidget.editorsManager
        return editorsManager.currentWidget().getEditor()

    def __onCut( self ):
        " Triggered when cut is requested "
        self.__getEditor().onShiftDel()
        return

    def __onPaste( self ):
        " Triggered when paste is requested "
        self.__getEditor().paste()
        return

    def __onSelectAll( self ):
        " Triggered when select all is requested "
        self.__getEditor().selectAll()
        return

    def __onComment( self ):
        " Triggered when comment/uncomment is requested "
        self.__getEditor().onCommentUncomment()
        return

    def __onDuplicate( self ):
        " Triggered when duplicate line is requested "
        self.__getEditor().duplicateLine()
        return

    def __onAutocomplete( self ):
        " Triggered when autocomplete is requested "
        self.__getEditor().onAutoComplete()
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
        self.__redoAct.setShortcut( "Ctrl+Y" )
        self.__redoAct.setEnabled( isPlainBuffer and editor.isRedoAvailable() )
        self.__cutAct.setShortcut( "Ctrl+X" )
        self.__cutAct.setEnabled( isPlainBuffer and not editor.isReadOnly() )
        self.__copyAct.setShortcut( "Ctrl+C" )
        self.__copyAct.setEnabled( editorsManager.isCopyAvailable() )
        self.__pasteAct.setShortcut( "Ctrl+V" )
        self.__pasteAct.setEnabled( isPlainBuffer and
                                    QApplication.clipboard().text() != "" and
                                    not editor.isReadOnly() )
        self.__selectAllAct.setShortcut( "Ctrl+A" )
        self.__selectAllAct.setEnabled( isPlainBuffer )
        self.__commentAct.setShortcut( "Ctrl+M" )
        self.__commentAct.setEnabled( isPythonBuffer and
                                      not editor.isReadOnly() )
        self.__duplicateAct.setShortcut( "Ctrl+D" )
        self.__duplicateAct.setEnabled( isPlainBuffer and
                                        not editor.isReadOnly() )
        self.__autocompleteAct.setShortcut( "Ctrl+Space" )
        self.__autocompleteAct.setEnabled( isPlainBuffer and
                                           not editor.isReadOnly() )
        self.__expandTabsAct.setEnabled( isPlainBuffer and
                                         not editor.isReadOnly() )
        self.__trailingSpacesAct.setEnabled( isPlainBuffer and
                                             not editor.isReadOnly() )
        return

    def __tabAboutToShow( self ):
        " Triggered when tab menu is about to show "
        plainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        isGeneratedDiagram = self.__isGeneratedDiagram()
        editorsManager = self.editorsManagerWidget.editorsManager

        self.__cloneTabAct.setEnabled( plainTextBuffer )
        self.__closeOtherTabsAct.setEnabled(
                                    editorsManager.closeOtherAvailable() )
        self.__saveFileAct.setEnabled( plainTextBuffer or isGeneratedDiagram )
        self.__saveFileAsAct.setEnabled( plainTextBuffer or isGeneratedDiagram )
        self.__closeTabAct.setEnabled( editorsManager.isTabClosable() )
        self.__tabJumpToDefAct.setEnabled( isPythonBuffer )
        self.__calltipAct.setEnabled( isPythonBuffer )
        self.__tabJumpToScopeBeginAct.setEnabled( isPythonBuffer )
        self.__tabOpenImportAct.setEnabled( isPythonBuffer )
        if plainTextBuffer:
            widget = editorsManager.currentWidget()
            editor = widget.getEditor()
            self.__openAsFileAct.setEnabled(
                        editor.openAsFileAvailable() )
            self.__downloadAndShowAct.setEnabled(
                        editor.downloadAndShowAvailable() )
            self.__openInBrowserAct.setEnabled(
                        editor.downloadAndShowAvailable() )
        else:
            self.__openAsFileAct.setEnabled( False )
            self.__downloadAndShowAct.setEnabled( False )
            self.__openInBrowserAct.setEnabled( False )

        self.__highlightInPrjAct.setEnabled(
                editorsManager.isHighlightInPrjAvailable() )
        self.__highlightInFSAct.setEnabled(
                editorsManager.isHighlightInFSAvailable() )
        self.__highlightInOutlineAct.setEnabled( isPythonBuffer )

        self.__closeTabAct.setShortcut( "Ctrl+F4" )
        self.__tabJumpToDefAct.setShortcut( "Ctrl+\\" )
        self.__calltipAct.setShortcut( "Ctrl+/" )
        self.__tabJumpToScopeBeginAct.setShortcut( "Alt+U" )
        self.__tabOpenImportAct.setShortcut( "Ctrl+I" )
        self.__highlightInOutlineAct.setShortcut( "Ctrl+B" )

        self.__recentFilesMenu.clear()
        addedCount = 0

        for item in GlobalData().project.recentFiles:
            addedCount += 1
            act = self.__recentFilesMenu.addAction(
                                self.__getAccelerator( addedCount ) + item )
            act.setData( QVariant( item ) )
            act.setEnabled( os.path.exists( item ) )

        self.__recentFilesMenu.setEnabled( addedCount > 0 )
        return

    def __searchAboutToShow( self ):
        " Triggered when search menu is about to show "
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        self.__findOccurencesAct.setEnabled( isPythonBuffer and
                                             os.path.isabs( currentWidget.getFileName() ) )
        self.__goToLineAct.setEnabled( isPlainTextBuffer )
        self.__findAct.setEnabled( isPlainTextBuffer )
        self.__findCurrentAct.setEnabled( isPlainTextBuffer )
        self.__replaceAct.setEnabled( isPlainTextBuffer and
                                      currentWidget.getType() != MainWindowTabWidgetBase.VCSAnnotateViewer )
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
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        enabled = isPythonBuffer and \
            currentWidget.getType() != MainWindowTabWidgetBase.VCSAnnotateViewer
        self.__tabImportDgmAct.setEnabled( enabled )
        self.__tabImportDgmDlgAct.setEnabled( enabled )
        return

    def __runAboutToShow( self ):
        " Triggered when the run menu is about to show "
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()

        enabled = projectLoaded and prjScriptValid and not self.debugMode
        self.__prjRunAct.setEnabled( enabled )
        self.__prjRunDlgAct.setEnabled( enabled )

        self.__prjProfileAct.setEnabled( enabled )
        self.__prjProfileDlgAct.setEnabled( enabled )
        return

    def __debugAboutToShow( self ):
        " Triggered when the debug menu is about to show "
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()

        enabled = projectLoaded and prjScriptValid and not self.debugMode
        self.__prjDebugAct.setEnabled( enabled )
        self.__prjDebugDlgAct.setEnabled( enabled )
        return

    def __toolsAboutToShow( self ):
        " Triggered when tools menu is about to show "
        isPythonBuffer = self.__isPythonBuffer()
        projectLoaded = GlobalData().project.isLoaded()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        pythonBufferNonAnnotate = isPythonBuffer and \
            currentWidget.getType() != MainWindowTabWidgetBase.VCSAnnotateViewer
        self.__tabPylintAct.setEnabled( pythonBufferNonAnnotate )
        self.__tabPymetricsAct.setEnabled( pythonBufferNonAnnotate )
        self.__tabLineCounterAct.setEnabled( isPythonBuffer )
        self.__tabPythonTidyAct.setEnabled( pythonBufferNonAnnotate and not self.debugMode )
        self.__tabPythonTidyDlgAct.setEnabled( pythonBufferNonAnnotate and not self.debugMode )

        if projectLoaded:
            self.__unusedClassesAct.setEnabled(
                            self.classesViewer.getItemCount() > 0 )
            self.__unusedFunctionsAct.setEnabled(
                            self.functionsViewer.getItemCount() > 0 )
            self.__unusedGlobalsAct.setEnabled(
                            self.globalsViewer.getItemCount() > 0 )
        else:
            self.__unusedClassesAct.setEnabled( False )
            self.__unusedFunctionsAct.setEnabled( False )
            self.__unusedGlobalsAct.setEnabled( False )

        self.__tabPylintAct.setShortcut( "Ctrl+L" )
        self.__tabPymetricsAct.setShortcut( "Ctrl+K" )
        return

    def __viewAboutToShow( self ):
        " Triggered when view menu is about to show "
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isGraphicsBuffer = self.__isGraphicsBuffer()
        isGeneratedDiagram = self.__isGeneratedDiagram()
        isProfileViewer = self.__isProfileViewer()
        isDiffViewer = self.__isDiffViewer()
        zoomEnabled = isPlainTextBuffer or isGraphicsBuffer or \
                      isGeneratedDiagram or isDiffViewer
        if zoomEnabled == False and isProfileViewer:
            editorsManager = self.editorsManagerWidget.editorsManager
            currentWidget = editorsManager.currentWidget()
            zoomEnabled = currentWidget.isZoomApplicable()
        self.__zoomInAct.setEnabled( zoomEnabled )
        self.__zoomOutAct.setEnabled( zoomEnabled )
        self.__zoom11Act.setEnabled( zoomEnabled )

        self.__zoomInAct.setShortcut( "Ctrl+=" )
        self.__zoomOutAct.setShortcut( "Ctrl+-" )
        self.__zoom11Act.setShortcut( "Ctrl+0" )

        self.__debugBarAct.setEnabled( self.debugMode )
        return

    def __optionsAboutToShow( self ):
        " Triggered when the options menu is about to show "
        exists = os.path.exists( getIDETemplateFile() )
        self.__ideCreateTemplateAct.setEnabled( not exists )
        self.__ideEditTemplateAct.setEnabled( exists )
        self.__ideDelTemplateAct.setEnabled( exists )

        exists = os.path.exists( getIDEPylintFile() )
        self.__ideCreatePylintAct.setEnabled( not exists )
        self.__ideEditPylintAct.setEnabled( exists )
        self.__ideDelPylintAct.setEnabled( exists )
        return

    def __helpAboutToShow( self ):
        " Triggered when help menu is about to show "
        isPythonBuffer = self.__isPythonBuffer()
        self.__contextHelpAct.setEnabled( isPythonBuffer )
        self.__callHelpAct.setEnabled( isPythonBuffer )

        self.__contextHelpAct.setShortcut( "Ctrl+F1" )
        self.__callHelpAct.setShortcut( "Ctrl+Shift+F1" )
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

    def __prjAboutToHide( self ):
        self.__newProjectAct.setEnabled( True )
        self.__openProjectAct.setEnabled( True )
        return

    def __tabAboutToHide( self ):
        " Triggered when tab menu is about to hide "
        self.__closeTabAct.setShortcut( "" )
        self.__tabJumpToDefAct.setShortcut( "" )
        self.__calltipAct.setShortcut( "" )
        self.__tabJumpToScopeBeginAct.setShortcut( "" )
        self.__tabOpenImportAct.setShortcut( "" )
        self.__highlightInOutlineAct.setShortcut( "" )

        self.__saveFileAct.setEnabled( True )
        self.__saveFileAsAct.setEnabled( True )
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
        self.__callHelpAct.setShortcut( "" )
        return

    @staticmethod
    def __getAccelerator( count ):
        " Provides an accelerator text for a menu item "
        if count < 10:
            return "&" + str( count ) + ".  "
        return "&" + chr( count - 10 + ord( 'a' ) ) + ".  "

    def __prjAboutToShow( self ):
        " Triggered when project menu is about to show "
        self.__newProjectAct.setEnabled( not self.debugMode )
        self.__openProjectAct.setEnabled( not self.debugMode )
        self.__unloadProjectAct.setEnabled( not self.debugMode )

        # Recent projects part
        self.__recentPrjMenu.clear()
        addedCount = 0
        currentPrj = GlobalData().project.fileName
        for item in self.settings.recentProjects:
            if item == currentPrj:
                continue
            addedCount += 1
            act = self.__recentPrjMenu.addAction(
                                self.__getAccelerator( addedCount ) +
                                os.path.basename( item ).replace( ".cdm", "" ) )
            act.setData( QVariant( item ) )
            act.setEnabled( not self.debugMode and os.path.exists( item ) )

        self.__recentPrjMenu.setEnabled( addedCount > 0 )

        if GlobalData().project.isLoaded():
            # Template part
            exists = os.path.exists( getProjectTemplateFile() )
            self.__prjTemplateMenu.setEnabled( True )
            self.__createPrjTemplateAct.setEnabled( not exists )
            self.__editPrjTemplateAct.setEnabled( exists )
            self.__delPrjTemplateAct.setEnabled( exists )
            # Pylint part
            exists = os.path.exists( self.__getPylintRCFileName() )
            self.__prjPylintMenu.setEnabled( True )
            self.__prjGenPylintrcAct.setEnabled( not exists )
            self.__prjEditPylintrcAct.setEnabled( exists )
            self.__prjDelPylintrcAct.setEnabled( exists )
            # Rope part
            self.__prjRopeConfigAct.setEnabled(
                                os.path.exists( self.__getRopeConfig() ) )
        else:
            self.__prjTemplateMenu.setEnabled( False )
            self.__prjPylintMenu.setEnabled( False )
            self.__prjRopeConfigAct.setEnabled( False )

        return

    def __onRecentPrj( self, act ):
        " Triggered when a recent project is requested to be loaded "
        path = str( act.data().toString() )
        if not os.path.exists( path ):
            logging.error( "Could not find project file: " + path )
        else:
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

    def onNotUsedFunctions( self ):
        " Triggered when not used functions analysis requested "
        dlg = NotUsedAnalysisProgress(
                        NotUsedAnalysisProgress.Functions,
                        self.functionsViewer.funcViewer.model().sourceModel(),
                        self )
        dlg.exec_()
        return

    def onNotUsedGlobals( self ):
        " Triggered when not used global vars analysis requested "
        dlg = NotUsedAnalysisProgress(
                        NotUsedAnalysisProgress.Globals,
                        self.globalsViewer.globalsViewer.model().sourceModel(),
                        self )
        dlg.exec_()
        return

    def onNotUsedClasses( self ):
        " Triggered when not used classes analysis requested "
        dlg = NotUsedAnalysisProgress(
                        NotUsedAnalysisProgress.Classes,
                        self.classesViewer.clViewer.model().sourceModel(),
                        self )
        dlg.exec_()
        return

    def showDisassembler( self, scriptPath, name ):
        " Triggered when a disassembler should be shown "
        try:
            code = getDisassembled( scriptPath, name )
            editorsManager = self.editorsManagerWidget.editorsManager
            editorsManager.showDisassembler( scriptPath, name, code )
        except:
            logging.error( "Could not get '" + name + "' from " +
                           scriptPath + " disassembled." )
        return

    def highlightInPrj( self, path ):
        " Triggered when the file is to be highlighted in a project tree "
        if not GlobalData().project.isLoaded():
            return
        if not os.path.isabs( path ):
            return
        if not GlobalData().project.isProjectFile( path ):
            return
        if self.projectViewer.highlightPrjItem( path ):
            self.activateProjectTab()
        return

    def highlightInFS( self, path ):
        " Triggered when the file is to be highlighted in the FS tree "
        if not os.path.isabs( path ):
            return
        if self.projectViewer.highlightFSItem( path ):
            self.activateProjectTab()
        return

    def highlightInOutline( self, context, line ):
        " Triggered when the given context should be highlighted in outline "
        if self.outlineViewer.highlightContextItem( context, line ):
            self.activateOutlineTab()
        return

    def getLogViewerContent( self ):
        " Provides the log viewer window content as a plain text "
        return self.logViewer.getText()

    def getCurrentFrameNumber( self ):
        " Provides the current stack frame number "
        return self.debuggerContext.getCurrentFrameNumber()

    def __onClientExceptionsCleared( self ):
        " Triggered when the user cleared the client exceptions "
        self.__rightSideBar.setTabText( 2, "Exceptions" )
        return

    def __onBreakpointsModelChanged( self ):
        " Triggered when something is changed in the breakpoints list "
        enabledCount, disabledCount = self.__debugger.getBreakPointModel().getCounts()
        total = enabledCount + disabledCount
        if total == 0:
            self.__rightSideBar.setTabText( 3, "Breakpoints" )
        else:
            self.__rightSideBar.setTabText( 3, "Breakpoints (" + str( total ) + ")" )
        return

    def __onEvalOK( self, message ):
        " Triggered when Eval completed successfully "
        logging.info( "Eval succeeded:\n" + message )
        return

    def __onEvalError( self, message ):
        " Triggered when Eval failed "
        logging.error( "Eval failed:\n" + message )
        return

    def __onExecOK( self, message ):
        " Triggered when Exec completed successfully "
        if message:
            logging.info( "Exec succeeded:\n" + message )
        return

    def __onExecError( self, message ):
        " Triggered when Eval failed "
        logging.error( "Exec failed:\n" + message )
        return

    def setDebugTabAvailable( self, enabled ):
        " Sets a new status when a tab is changed or a content has been changed "
        self.__tabDebugAct.setEnabled( enabled )
        self.__tabDebugDlgAct.setEnabled( enabled )

        self.__tabRunAct.setEnabled( enabled )
        self.__tabRunDlgAct.setEnabled( enabled )

        self.__tabProfileAct.setEnabled( enabled )
        self.__tabProfileDlgAct.setEnabled( enabled )
        return

    def __initPluginSupport( self ):
        " Initializes the main window plugin support "
        self.__pluginMenus = {}
        self.connect( GlobalData().pluginManager, SIGNAL( 'PluginActivated' ),
                      self.__onPluginActivated )
        self.connect( GlobalData().pluginManager, SIGNAL( 'PluginDeactivated' ),
                      self.__onPluginDeactivated )
        return

    def __onPluginActivated( self, plugin ):
        " Triggered when a plugin is activated "
        pluginName = plugin.getName()
        try:
            pluginMenu = QMenu( pluginName, self )
            plugin.getObject().populateMainMenu( pluginMenu )
            if pluginMenu.isEmpty():
                pluginMenu = None
                return
            self.__pluginMenus[ plugin.getPath() ] = pluginMenu
            self.__recomposePluginMenu()
        except Exception, exc:
            logging.error( "Error populating " + pluginName + " plugin main menu: " +
                           str( exc ) + ". Ignore and continue." )
        return

    def __recomposePluginMenu( self ):
        " Recomposes the plugin menu "
        self.__pluginsMenu.clear()
        self.__pluginsMenu.addAction(
            PixmapCache().getIcon( 'pluginmanagermenu.png' ),
            'Plugin &manager', self.__onPluginManager )
        if self.__pluginMenus:
            self.__pluginsMenu.addSeparator()
        for path in self.__pluginMenus:
            self.__pluginsMenu.addMenu( self.__pluginMenus[ path ] )
        return

    def __onPluginDeactivated( self, plugin ):
        " Triggered when a plugin is deactivated "
        try:
            path = plugin.getPath()
            if path in self.__pluginMenus:
                del self.__pluginMenus[ path ]
                self.__recomposePluginMenu()
        except Exception, exc:
            pluginName = plugin.getName()
            logging.error( "Error removing " + pluginName + " plugin main menu: " +
                           str( exc ) + ". Ignore and continue." )
        return

    def activateProjectTab( self ):
        " Activates the project tab "
        self.__leftSideBar.show()
        self.__leftSideBar.setCurrentWidget( self.projectViewer )
        self.__leftSideBar.raise_()
        return

    def activateOutlineTab( self ):
        " Activates the outline tab "
        self.__rightSideBar.show()
        self.__rightSideBar.setCurrentWidget( self.outlineViewer )
        self.__rightSideBar.raise_()
        return

    def __dumpDebugSettings( self, fileName, fullEnvironment ):
        " Provides common settings except the environment "
        runParameters = GlobalData().getRunParameters( fileName )
        debugSettings = self.settings.getDebuggerSettings()
        workingDir = getWorkingDir( fileName, runParameters )
        arguments = parseCommandLineArguments( runParameters.arguments )
        environment = getNoArgsEnvironment( runParameters )

        env = "Environment: "
        if runParameters.envType == runParameters.InheritParentEnv:
            env += "inherit parent"
        elif runParameters.envType == runParameters.InheritParentEnvPlus:
            env += "inherit parent and add/modify"
        else:
            env += "specific"

        pathVariables = []
        container = None
        if fullEnvironment:
            container = environment
            keys = environment.keys()
            keys.sort()
            for key in keys:
                env += "\n    " + key + " = " + environment[ key ]
                if 'PATH' in key:
                    pathVariables.append( key )
        else:
            if runParameters.envType == runParameters.InheritParentEnvPlus:
                container = runParameters.additionToParentEnv
                keys = runParameters.additionToParentEnv.keys()
                keys.sort()
                for key in keys:
                    env += "\n    " + key + " = " + runParameters.additionToParentEnv[ key ]
                    if 'PATH' in key:
                        pathVariables.append( key )
            elif runParameters.envType == runParameters.SpecificEnvironment:
                container = runParameters.specificEnv
                keys = runParameters.specificEnv.keys()
                keys.sort()
                for key in keys():
                    env += "\n    " + key + " = " + runParameters.specificEnv[ key ]
                    if 'PATH' in key:
                        pathVariables.append( key )

        if pathVariables:
            env += "\nDetected PATH-containing variables:"
            for key in pathVariables:
                env += "\n    " + key
                for item in container[ key ].split( ':' ):
                    env += "\n        " + item

        terminal = "Terminal to run in: "
        if self.settings.terminalType == TERM_AUTO:
            terminal += "auto detection"
        elif self.settings.terminalType == TERM_KONSOLE:
            terminal += "default KDE konsole"
        elif self.settings.terminalType == TERM_GNOME:
            terminal += "gnome-terminal"
        elif self.settings.terminalType == TERM_XTERM:
            terminal += "xterm"
        elif self.settings.terminalType == TERM_REDIRECT:
            terminal += "redirect to IDE"

        logging.info( "\n".join(
            [ "Current debug session settings",
              "Script: " + fileName,
              "Arguments: " + " ".join( arguments ),
              "Working directory: " + workingDir,
              env, terminal,
              "Report exceptions: " + str( debugSettings.reportExceptions ),
              "Trace interpreter libs: " + str( debugSettings.traceInterpreter ),
              "Stop at first line: " + str( debugSettings.stopAtFirstLine ),
              "Fork without asking: " + str( debugSettings.autofork ),
              "Debug child process: " + str( debugSettings.followChild ),
              "Close terminal upon successfull completion: " + str( runParameters.closeTerminal ) ] ) )
        return

    def __onDumpDebugSettings( self, action = None ):
        " Triggered when dumping visible settings was requested "
        self.__dumpDebugSettings( self.__debugger.getScriptPath(), False )
        return

    def __onDumpFullDebugSettings( self ):
        " Triggered when dumping complete settings is requested "
        self.__dumpDebugSettings( self.__debugger.getScriptPath(), True )
        return

    def __onDumpScriptDebugSettings( self ):
        " Triggered when dumping current script settings is requested "
        if self.__dumpScriptDbgSettingsAvailable():
            editorsManager = self.editorsManagerWidget.editorsManager
            currentWidget = editorsManager.currentWidget()
            self.__dumpDebugSettings( currentWidget.getFileName(), False )
        return

    def __onDumpScriptFullDebugSettings( self ):
        " Triggered when dumping current script complete settings is requested "
        if self.__dumpScriptDbgSettingsAvailable():
            editorsManager = self.editorsManagerWidget.editorsManager
            currentWidget = editorsManager.currentWidget()
            self.__dumpDebugSettings( currentWidget.getFileName(), True )
        return

    def __onDumpProjectDebugSettings( self ):
        " Triggered when dumping project script settings is requested "
        if self.__dumpProjectDbgSettingsAvailable():
            project = GlobalData().project
            self.__dumpDebugSettings( project.getProjectScript(), False )
        return

    def __onDumpProjectFullDebugSettings( self ):
        " Triggered when dumping project script complete settings is requested "
        if self.__dumpProjectDbgSettingsAvailable():
            project = GlobalData().project
            self.__dumpDebugSettings( project.getProjectScript(), True )
        return

    def __dumpScriptDbgSettingsAvailable( self ):
        " True if dumping debug session settings for the script is available "
        if not self.__isPythonBuffer():
            return False
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        fileName  = currentWidget.getFileName()
        if os.path.isabs( fileName ) and os.path.exists( fileName ):
            return True
        return False

    def __dumpProjectDbgSettingsAvailable( self ):
        " True if dumping debug session settings for the project is available "
        project = GlobalData().project
        if not project.isLoaded():
            return False
        fileName = project.getProjectScript()
        if os.path.exists( fileName ) and os.path.isabs( fileName ):
            return True
        return False

    def __onDumpDbgSettingsAboutToShow( self ):
        " Dump debug settings is about to show "
        scriptAvailable = self.__dumpScriptDbgSettingsAvailable()
        self.__debugDumpScriptSettingsAct.setEnabled( scriptAvailable )
        self.__debugDumpScriptSettingsEnvAct.setEnabled( scriptAvailable )

        projectAvailable = self.__dumpProjectDbgSettingsAvailable()
        self.__debugDumpProjectSettingsAct.setEnabled( projectAvailable )
        self.__debugDumpProjectSettingsEnvAct.setEnabled( projectAvailable )
        return

    def installRedirectedIOConsole( self ):
        " Create redirected IO console "
        self.redirectedIOConsole = IOConsoleTabWidget( self )
        self.connect( self.redirectedIOConsole, SIGNAL( 'UserInput' ),
                      self.__onUserInput )
        self.connect( self.redirectedIOConsole, SIGNAL( 'TextEditorZoom' ),
                      self.editorsManagerWidget.editorsManager.onZoom )
        self.connect( self.redirectedIOConsole, SIGNAL( 'SettingUpdated' ),
                      self.onIOConsoleSettingUpdated )
        self.__bottomSideBar.addTab( self.redirectedIOConsole,
                PixmapCache().getIcon( 'ioconsole.png' ), 'IO console' )
        self.__bottomSideBar.setTabToolTip( 7, 'Redirected IO debug console' )
        return

    def clearDebugIOConsole( self ):
        " Clears the content of the debug IO console "
        if self.redirectedIOConsole:
            self.redirectedIOConsole.clear()
        return

    def __onClientStdout( self, data ):
        " Triggered when the client reports stdout "
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.redirectedIOConsole )
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.appendStdoutMessage( data )
        return

    def __onClientStderr( self, data ):
        " Triggered when the client reports stderr "
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.redirectedIOConsole )
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.appendStderrMessage( data )
        return

    def __ioconsoleIDEMessage( self, message ):
        " Sends an IDE message to the IO console "
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.redirectedIOConsole )
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.appendIDEMessage( message )
        return

    def __onClientRawInput( self, prompt, echo ):
        " Triggered when the client input is requested "
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.redirectedIOConsole )
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.rawInput( prompt, echo )
        self.redirectedIOConsole.setFocus()
        return

    def __onUserInput( self, userInput ):
        " Triggered when the user finished input in the redirected IO console "
        self.__debugger.remoteRawInput( userInput )
        return

    def __getNewRunIndex( self ):
        " Provides the new run index "
        self.__newRunIndex += 1
        return self.__newRunIndex

    def __getNewProfileIndex( self ):
        " Provides the new profile index "
        self.__newProfileIndex += 1
        return self.__newProfileIndex

    def installIOConsole( self, widget, isProfile = False ):
        " Installs a new widget at the bottom "
        if isProfile:
            index = str( self.__getNewProfileIndex() )
            caption = "Profiling #" + index
            tooltip = "Redirected IO profile console #" + index + " (running)"
        else:
            index = str( self.__getNewRunIndex() )
            caption = "Run #" + index
            tooltip = "Redirected IO run console #" + index + " (running)"

        self.connect( widget, SIGNAL( 'CloseIOConsole' ),
                      self.__onCloseIOConsole )
        self.connect( widget, SIGNAL( 'KillIOConsoleProcess' ),
                      self.__onKillIOConsoleProcess )
        self.connect( widget, SIGNAL( 'TextEditorZoom' ),
                      self.editorsManagerWidget.editorsManager.onZoom )
        self.connect( widget, SIGNAL( 'SettingUpdated' ),
                      self.onIOConsoleSettingUpdated )

        self.__bottomSideBar.addTab( widget,
                PixmapCache().getIcon( 'ioconsole.png' ), caption )
        self.__bottomSideBar.setTabToolTip(
                self.__bottomSideBar.count() - 1, tooltip )
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( widget )
        self.__bottomSideBar.raise_()
        widget.setFocus()
        return

    def updateIOConsoleTooltip( self, threadID, msg ):
        " Updates the IO console tooltip "
        index = self.__getIOConsoleIndex( threadID )
        if index is not None:
            tooltip = self.__bottomSideBar.tabToolTip( index )
            tooltip = tooltip.replace( "(running)", "(" + msg + ")" )
            self.__bottomSideBar.setTabToolTip( index, tooltip )
        return

    def __getIOConsoleIndex( self, threadID ):
        " Provides the IO console index by the thread ID "
        index = self.__bottomSideBar.count() - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget( index )
            if hasattr( widget, "threadID" ):
                if widget.threadID() == threadID:
                    return index
            index -= 1
        return None

    def __onCloseIOConsole( self, threadID ):
        " Closes the tab with the corresponding widget "
        index = self.__getIOConsoleIndex( threadID )
        if index is not None:
            self.__bottomSideBar.removeTab( index )
        return

    def __onKillIOConsoleProcess( self, threadID ):
        " Kills the process linked to the IO console "
        self.__runManager.kill( threadID )
        return

    def closeAllIOConsoles( self ):
        " Closes all IO run/profile consoles and clears the debug IO console "
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        index = self.__bottomSideBar.count() - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget( index )
            if hasattr( widget, "getType" ):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    if hasattr( widget, "stopAndClose" ):
                        widget.stopAndClose()
            index -= 1

        self.clearDebugIOConsole()
        QApplication.restoreOverrideCursor()
        return

