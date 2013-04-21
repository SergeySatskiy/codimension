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
from PyQt4.QtCore               import SIGNAL, Qt, QSize, QTimer, QDir, QVariant
from PyQt4.QtGui                import QLabel, QToolBar, QWidget, QMessageBox, \
                                       QVBoxLayout, QSplitter, QDialog, \
                                       QSizePolicy, QAction, QMainWindow, \
                                       QShortcut, QFrame, QApplication, \
                                       QCursor, QMenu, QToolButton, QToolTip, \
                                       QPalette, QColor
from fitlabel                   import FitPathLabel
from utils.globals              import GlobalData
from utils.project              import CodimensionProject
from sidebar                    import SideBar
from logviewer                  import LogViewer
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
                                       ELFFileType, PDFFileType
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

        splash.showMessage( "Initializing statusbar..." )
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
        self.__toolbar = None
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

        self.updateWindowTitle()
        self.__printThirdPartyAvailability()

        maximizeAction = QShortcut( 'F11', self )
        self.connect( maximizeAction, SIGNAL( "activated()" ),
                      self.__onMaximizeEditor )
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
                                     'Log viewer' )
        self.connect( sys.stdout, SIGNAL('appendToStdout'), self.toStdout )
        self.connect( sys.stderr, SIGNAL('appendToStderr'), self.toStderr )

        # replace logging streamer to self.stdout
        logging.root.handlers = []
        handler = logging.StreamHandler( sys.stdout )
        handler.setFormatter( \
            logging.Formatter( "%(levelname) -10s %(asctime)s %(message)s",
            None ) )
        logging.root.addHandler( handler )


        projectViewer = ProjectViewer()
        self.__leftSideBar.addTab( projectViewer,
                                   PixmapCache().getIcon( 'project.png' ),
                                   "Project" )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      projectViewer.onFileUpdated )
        recentProjectsViewer = RecentProjectsViewer()
        self.__leftSideBar.addTab( recentProjectsViewer,
                                   PixmapCache().getIcon( 'project.png' ),
                                   "Recent" )
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      recentProjectsViewer.onFileUpdated )
        #self.__leftSideBar.setTabToolTip( 1, "Recently loaded projects" )
        classesViewer = ClassesViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      classesViewer.onFileUpdated )
        self.__leftSideBar.addTab( classesViewer,
                                   PixmapCache().getIcon( 'class.png' ),
                                   "Classes" )
        functionsViewer = FunctionsViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      functionsViewer.onFileUpdated )
        self.__leftSideBar.addTab( functionsViewer,
                                   PixmapCache().getIcon( 'fx.png' ),
                                   "Functions" )
        globalsViewer = GlobalsViewer()
        self.connect( self.editorsManagerWidget.editorsManager,
                      SIGNAL( 'fileUpdated' ),
                      globalsViewer.onFileUpdated )
        self.__leftSideBar.addTab( globalsViewer,
                                   PixmapCache().getIcon( 'globalvar.png' ),
                                   "Globals" )


        # Create todo viewer
        todoViewer = TodoViewer()
        self.__bottomSideBar.addTab( todoViewer,
                                     PixmapCache().getIcon( 'todo.png' ),
                                     'Todo viewer' )
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

        # Create outline viewer
        self.__outlineViewer = FileOutlineViewer( self.editorsManagerWidget.editorsManager )
        self.__rightSideBar.addTab( self.__outlineViewer,
                                    PixmapCache().getIcon( 'filepython.png' ),
                                    'File outline' )

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

        if globalData.doxygenAvailable:
            logging.debug( "The 'doxygen' utility is available" )
        else:
            logging.warning( "The 'doxygen' utility is not found. " \
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

        self.sbLanguage = QLabel( self.__statusBar )
        self.sbLanguage.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbLanguage )
        self.sbLanguage.setToolTip( "Editor language" )

        self.sbEncoding = QLabel( self.__statusBar )
        self.sbEncoding.setFrameStyle( QFrame.StyledPanel )
        self.__statusBar.addPermanentWidget( self.sbEncoding )
        self.sbEncoding.setToolTip( "Editor encoding" )

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
        self.sbFile.setToolTip( "Editor file name" )

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

    def __createToolBar( self ):
        """ creates the buttons bar """

        createProjectButton = QAction( \
                                PixmapCache().getIcon( 'createproject.png' ),
                                'Create new project', self )
        self.connect( createProjectButton, SIGNAL( "triggered()" ),
                      self.__createNewProject )

        # Imports diagram button and its menu
        importsMenu = QMenu( self )
        importsDlgAct = importsMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Fine tuned imports diagram' )
        self.connect( importsDlgAct, SIGNAL( 'triggered()' ),
                      self.__onImportDgmTuned )
        self.importsDiagramButton = QToolButton( self )
        self.importsDiagramButton.setIcon( PixmapCache().getIcon( 'importsdiagram.png' ) )
        self.importsDiagramButton.setToolTip( 'Generate imports diagram' )
        self.importsDiagramButton.setPopupMode( QToolButton.DelayedPopup )
        self.importsDiagramButton.setMenu( importsMenu )
        self.importsDiagramButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.importsDiagramButton, SIGNAL( 'clicked(bool)' ),
                      self.__onImportDgm )

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
        doxygenButton = QAction( \
                PixmapCache().getIcon( 'doxygen.png' ),
                'Generate doxygen documentation', self )
        doxygenButton.setEnabled( False )
        doxygenButton.setVisible( False )
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
                                    'Line counter', self )
        self.connect( self.linecounterButton, SIGNAL( 'triggered()' ),
                      self.linecounterButtonClicked )

        self.__findInFilesButton = QAction( \
                                    PixmapCache().getIcon( 'findindir.png' ),
                                    'Find in project (Ctrl+Shift+F)', self )
        self.__findInFilesButton.setShortcut( 'Ctrl+Shift+F' )
        self.connect( self.__findInFilesButton, SIGNAL( 'triggered()' ),
                      self.findInFilesClicked )

        self.__findNameButton = QAction( \
                                    PixmapCache().getIcon( 'findname.png' ),
                                    'Find name (Alt+Shift+S)', self )
        self.__findNameButton.setShortcut( 'Alt+Shift+S' )
        self.connect( self.__findNameButton, SIGNAL( 'triggered()' ),
                      self.findNameClicked )

        self.__findFileButton = QAction( \
                                    PixmapCache().getIcon( 'findfile.png' ),
                                    'Find project file (Alt+Shift+O)', self )
        self.__findFileButton.setShortcut( 'Alt+Shift+O' )
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



        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.__toolbar = QToolBar()
        self.__toolbar.setMovable( False )
        self.__toolbar.setAllowedAreas( Qt.TopToolBarArea )
        self.__toolbar.setIconSize( QSize( 24, 24 ) )
        self.__toolbar.addAction( createProjectButton )
        self.__toolbar.addSeparator()
        self.__toolbar.addAction( packageDiagramButton )
        self.__toolbar.addWidget( self.importsDiagramButton )
        self.__toolbar.addAction( applicationDiagramButton )
        self.__toolbar.addAction( doxygenButton )
        self.__toolbar.addSeparator()
        self.__toolbar.addAction( neverUsedButton )
        self.__toolbar.addWidget( self.__pylintButton )
        self.__toolbar.addAction( self.__pymetricsButton )
        self.__toolbar.addAction( self.linecounterButton )
        self.__toolbar.addSeparator()
        self.__toolbar.addAction( self.__findInFilesButton )
        self.__toolbar.addAction( self.__findNameButton )
        self.__toolbar.addAction( self.__findFileButton )
        self.__toolbar.addWidget( spacer )
        self.__toolbar.addWidget( editorSettingsButton )

        self.addToolBar( self.__toolbar )
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
            if GlobalData().project.fileName != "":
                self.settings.projectLoaded = True
                editorsManager = self.editorsManagerWidget.editorsManager
                editorsManager.restoreTabs( GlobalData().project.tabsStatus )

                if os.path.exists( self.__getPylintRCFileName() ):
                    self.__pylintButton.setMenu( self.__existentPylintRCMenu )
                else:
                    self.__pylintButton.setMenu( self.__absentPylintRCMenu )
            else:
                self.settings.projectLoaded = False
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
        projectLoaded = GlobalData().project.fileName != ""
        self.linecounterButton.setEnabled( projectLoaded )
        self.__pylintButton.setEnabled( projectLoaded and \
                                        GlobalData().pylintAvailable )
        self.importsDiagramButton.setEnabled( GlobalData().graphvizAvailable )
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
            logging.error( "Cannot open " + path + ", does not esist" )
            return
        if os.path.islink( path ):
            path = os.path.realpath( path )
            if not os.path.exists( path ):
                logging.error( "Cannot open " + path + ", does not esist" )
                return
            # The type may differ...
            fileType = detectFileType( path )
        else:
            # The intermediate directory could be a link, so use the real path
            path = os.path.realpath( path )

        if not os.access( path, os.R_OK ):
            logging.error( "No read permissions to open " + path )
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

        dialog = ProjectPropertiesDialog()
        if dialog.exec_() != QDialog.Accepted:
            return

        # Request accepted
        GlobalData().project.createNew( \
                        dialog.projectFileName,
                        str( dialog.authorEdit.text() ).strip(),
                        str( dialog.licenseEdit.text() ).strip(),
                        str( dialog.copyrightEdit.text() ).strip(),
                        str( dialog.descriptionEdit.toPlainText() ).strip(),
                        str( dialog.creationDateEdit.text() ).strip(),
                        str( dialog.versionEdit.text() ).strip(),
                        str( dialog.emailEdit.text() ).strip() )
        Settings().addRecentProject( dialog.projectFileName )
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
            if project.fileName != "":
                project.setTabsStatus( editorsManager.getTabsStatus() )
                self.settings.tabsStatus = []
            else:
                self.settings.tabsStatus = editorsManager.getTabsStatus()

        return editorsManager.closeEvent( event )

    def showPylintReport( self, reportOption, fileOrContent,
                                displayName, uuid ):
        " Passes data to the pylint viewer "

        # This is a python file, let's pylint it
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        # Detect the project pylintrc file if so
        pylintrcFile = ""
        if GlobalData().project.fileName != "":
            fName = os.path.dirname( GlobalData().project.fileName ) + \
                    os.path.sep + "pylintrc"
            if os.path.exists( fName ):
                pylintrcFile = fName

        try:
            lint = Pylint()
            if reportOption == PylintViewer.SingleBuffer:
                lint.analyzeBuffer( fileOrContent, pylintrcFile )
            else:
                lint.analyzeFile( fileOrContent, pylintrcFile )

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

        self.showPylintReport( PylintViewer.ProjectFiles,
                               filesToProcess,
                               "", "" )
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

    def __onImportDgm( self, action ):
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

