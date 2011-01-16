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

import os, os.path, sys, logging
from PyQt4.QtCore               import SIGNAL, Qt, QSize, QTimer
from PyQt4.QtGui                import QLabel, QToolBar, QWidget, QMessageBox, \
                                       QVBoxLayout, QSplitter, QDialog, \
                                       QSizePolicy, QAction, QMainWindow, \
                                       QShortcut, QFrame, QApplication, \
                                       QCursor, QMenu, QToolButton
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
from editorsmanager             import EditorsManager
from linecounter                import LineCounterDialog
from projectproperties          import ProjectPropertiesDialog
from utils.settings             import Settings
from findreplacewidget          import FindWidget, ReplaceWidget
from gotolinewidget             import GotoLineWidget
from pylintviewer               import PylintViewer
from pylintparser.pylintparser  import Pylint
from utils.fileutils            import PythonFileType, \
                                       Python3FileType, detectFileType


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

        # The size restore is done twice to avoid huge flickering
        # This one is approximate, the one in the timer handler is precise
        self.resize( self.settings.width, self.settings.height )
        self.move( self.settings.xpos + settings.xdelta,
                   self.settings.ypos + settings.ydelta )

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
                      self.__onFindNext )
        findPrevAction = QShortcut( 'Shift+F3', self )
        self.connect( findPrevAction, SIGNAL( "activated()" ),
                      self.__onFindPrev )

        # Needs for a proper update of the pylint menu
        self.connect( GlobalData().project, SIGNAL( 'fsChanged' ),
                      self.__onFSChanged )


        # 0 does not work, the window must be properly
        # drawn before restoring the old position
        QTimer.singleShot( 1, self.__restorePosition )
        return

    def __restorePosition( self ):
        " Makes sure that the window frame delta is proper "
        if self.settings.xpos != self.x() or \
           self.settings.ypos != self.y():
            # The saved delta is incorrect, update it
            self.settings.xdelta = self.settings.xpos - self.x()
            self.settings.ydelta = self.settings.ypos - self.y()
            self.settings.xpos = self.x()
            self.settings.ypos = self.y()
        self.__initialisation = False
        return

    def __onMaximizeEditor( self ):
        " Triggered when F11 is pressed "
        self.__leftSideBar.shrink()
        self.__bottomSideBar.shrink()
        return

    def __onFindNext( self ):
        " Triggered when F3 is pressed "
        self.editorsManagerWidget.editorsManager.findNext()
        return

    def __onFindPrev( self ):
        " Triggered when Shift+F3 is pressed "
        self.editorsManagerWidget.editorsManager.findPrev()
        return

    def __createLayout( self, settings ):
        """ creates the UI layout """

        self.editorsManagerWidget = EditorsManagerWidget( self )
        self.editorsManagerWidget.findWidget.hide()
        self.editorsManagerWidget.replaceWidget.hide()
        self.editorsManagerWidget.gotoLineWidget.hide()

        # The layout is a sidebar-style one
        self.__bottomSideBar = SideBar( SideBar.South )
        self.__leftSideBar   = SideBar( SideBar.West )

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
        recentProjectsViewer = RecentProjectsViewer()
        self.__leftSideBar.addTab( recentProjectsViewer,
                                   PixmapCache().getIcon( 'project.png' ),
                                   "Recent" )
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
                                   PixmapCache().getIcon( 'method.png' ),
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
        self.connect( self.__pylintViewer, SIGNAL( 'updatePylinTooltip' ),
                      self.__onPylinTooltip )
        if GlobalData().pylintAvailable:
            self.__onPylinTooltip( "No results available" )
        else:
            self.__onPylinTooltip( "Pylint is not available" )

        # Create splitters
        self.__horizontalSplitter = QSplitter( Qt.Horizontal )
        self.__verticalSplitter = QSplitter( Qt.Vertical )

        self.__horizontalSplitter.addWidget( self.__leftSideBar )
        self.__horizontalSplitter.addWidget( self.editorsManagerWidget )

        self.__verticalSplitter.addWidget( self.__horizontalSplitter )
        self.__verticalSplitter.addWidget( self.__bottomSideBar )

        self.setCentralWidget( self.__verticalSplitter )

        self.__leftSideBar.setSplitter( self.__horizontalSplitter )
        self.__bottomSideBar.setSplitter( self.__verticalSplitter )

        self.__leftSideBar.setSplitter( self.__horizontalSplitter )
        self.__bottomSideBar.setSplitter( self.__verticalSplitter )

        # restore the side bar state
        self.__horizontalSplitter.setSizes( settings.hSplitterSizes )
        self.__verticalSplitter.setSizes( settings.vSplitterSizes )
        if settings.leftBarMinimized:
            self.__leftSideBar.shrink()
        if settings.bottomBarMinimized:
            self.__bottomSideBar.shrink()

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
            logging.info( "The 'file' utility is available" )
        else:
            logging.warning( "The 'file' utility is not found. " \
                             "Some functionality will not be available." )

        if globalData.pylintAvailable:
            logging.info( "The 'pylint' utility is available" )
        else:
            logging.warning( "The 'pylint' utility is not found. " \
                             "Some functionality will not be available." )

        if globalData.doxygenAvailable:
            logging.info( "The 'doxygen' utility is available" )
        else:
            logging.warning( "The 'doxygen' utility is not found. " \
                             "Some functionality will not be available." )

        if globalData.graphvizAvailable:
            logging.info( "The 'graphviz' utility is available" )
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
        self.settings.hSplitterSizes = hList
        return

    def __createStatusBar( self ):
        """ creates status bar """

        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled( True )

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
        font.setPointSize( font.pointSize() + 1 )
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

        createProjectButton = QAction( PixmapCache().getIcon( 'createproject.png' ),
                                       'Create new project', self )
        createProjectButton.setStatusTip( "Create a new project" )
        self.connect( createProjectButton, SIGNAL( "triggered()" ),
                      self.__createNewProject )

        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        printButton.setStatusTip( 'Print the current editor content' )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.notImplementedYet )

        aboutButton = QAction( PixmapCache().getIcon( 'about.png' ),
                               'About (Ctrl+B)', self )
        aboutButton.setShortcut( 'Ctrl+B' )
        aboutButton.setStatusTip( 'About message' )
        self.connect( aboutButton, SIGNAL( 'triggered()' ),
                      self.aboutButtonClicked )

        packageDiagramButton = QAction( \
                PixmapCache().getIcon( 'packagediagram.png' ),
                'Generate package diagram', self )
        importsDiagramButton = QAction( \
                PixmapCache().getIcon( 'importsdiagram.png' ),
                'Generate imports diagram', self )
        applicationDiagramButton = QAction( \
                PixmapCache().getIcon( 'applicationdiagram.png' ),
                'Generate application diagram', self )
        doxygenButton = QAction( \
                PixmapCache().getIcon( 'doxygen.png' ),
                'Generate doxygen documentation', self )
        fixedSpacer2 = QWidget()
        fixedSpacer2.setFixedWidth( 5 )
        neverUsedButton = QAction( \
                PixmapCache().getIcon( 'neverused.png' ),
                'Analysis for never used variables, functions, classes', self )

        # pylint button
        self.__existentPylintRCMenu = QMenu( self )
        editAct = self.__existentPylintRCMenu.addAction( PixmapCache().getIcon( 'edit.png' ),
                                                         'Edit the project pylintrc' )
        self.connect( editAct, SIGNAL( 'triggered()' ), self.__onEditPylintRC )
        self.__existentPylintRCMenu.addSeparator()
        delAct = self.__existentPylintRCMenu.addAction( PixmapCache().getIcon( 'trash.png' ),
                                                        'Delete the project pylintrc' )
        self.connect( delAct, SIGNAL( 'triggered()' ), self.__onDelPylintRC )

        self.__absentPylintRCMenu = QMenu( self )
        genAct = self.__absentPylintRCMenu.addAction( PixmapCache().getIcon( 'generate.png' ),
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

        self.linecounterButton = QAction( PixmapCache().getIcon( 'linecounter.png' ),
                                          'Line counter', self )
        self.linecounterButton.setStatusTip( 'Line counter' )
        self.connect( self.linecounterButton, SIGNAL( 'triggered()' ),
                      self.linecounterButtonClicked )


        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.__toolbar = QToolBar()
        self.__toolbar.setMovable( False )
        self.__toolbar.setAllowedAreas( Qt.TopToolBarArea )
        self.__toolbar.setIconSize( QSize( 24, 24 ) )
        self.__toolbar.addAction( createProjectButton )
        self.__toolbar.addAction( printButton )
        self.__toolbar.addAction( packageDiagramButton )
        self.__toolbar.addAction( importsDiagramButton )
        self.__toolbar.addAction( applicationDiagramButton )
        self.__toolbar.addAction( doxygenButton )
        self.__toolbar.addWidget( fixedSpacer2 )
        self.__toolbar.addAction( neverUsedButton )
        self.__toolbar.addWidget( self.__pylintButton )
        self.__toolbar.addWidget( spacer )
        self.__toolbar.addAction( self.linecounterButton )
        self.__toolbar.addAction( aboutButton )

        self.addToolBar( self.__toolbar )
        return


    def resizeEvent( self, resizeEv ):
        """ Memorizes the new window size """

        if self.__initialisation:
            return

        self.settings.width = resizeEv.size().width()
        self.settings.height = resizeEv.size().height()
        self.vSplitterMoved( 0, 0 )
        self.hSplitterMoved( 0, 0 )
        return

    def moveEvent( self, moveEv ):
        """ Memorizes the new window position """

        if self.__initialisation:
            return

        self.settings.xpos = moveEv.pos().x()
        self.settings.ypos = moveEv.pos().y()
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
        return

    def aboutButtonClicked( self ):
        """ Shows the 'About' dialog """

        QMessageBox.about( self, 'About codimension',
                "<b>Codimension - two way python code editor " \
                "and analyzer</b> v. " + \
                   GlobalData().version + \
                """<p>Written by Sergey Satskiy, (c) 2010
                   <p>Allows editing textual and graphics
                      representaions of the python code""" )
        return

    def linecounterButtonClicked( self ):
        " Triggered when the line counter button is clicked "
        LineCounterDialog().exec_()
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

    def openFile( self, fileName, lineNo ):
        " User double clicked on a file or an item in a file "
        #logging.debug( "Item opening requested. File: " + fileName + \
        #               " Line: " + str( lineNo ) )
        self.editorsManagerWidget.editorsManager.openFile( fileName, lineNo )
        return

    def openPixmapFile( self, fileName ):
        " User double clicked on a file "
        #logging.debug( "Pixmap opening request. File: " + fileName )
        self.editorsManagerWidget.editorsManager.openPixmapFile( fileName )
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
        GlobalData().project.createNew( dialog.projectFileName,
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
        self.settings.bottomBarMinimized = self.__bottomSideBar.isMinimized()
        self.settings.leftBarMinimized = self.__leftSideBar.isMinimized()

        # Ask the editors manager to close all the editors
        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.getUnsavedCount() == 0:
            GlobalData().project.setTabsStatus( editorsManager.getTabsStatus() )

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

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentWidget( self.__pylintViewer )
        self.__bottomSideBar.raise_()
        return

    def __onPylinTooltip( self, tooltip ):
        " Updates the pylint viewer tab tooltip "
        self.__bottomSideBar.setTabToolTip( 2, tooltip )
        return

    def getWidgetByUUID( self, uuid ):
        " Provides the widget found by the given UUID "
        for widget in self.editorsManagerWidget.editorsManager.widgets:
            if uuid == widget.getUUID():
                return widget
        return None

    def pylintButtonClicked( self, action ):
        " Project pylint report is requested "

        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        filesToProcess = []
        for item in GlobalData().project.filesList:
            if detectFileType( item ) in [ PythonFileType,
                                           Python3FileType ]:
                filesToProcess.append( item )
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()

        if len( filesToProcess ) == 0:
            logging.error( "No python files in the project" )
            return

        self.showPylintReport( PylintViewer.ProjectFiles,
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

