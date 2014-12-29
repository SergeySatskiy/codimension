#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Variables viewer "


from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QFrame, QVBoxLayout, QLabel, QWidget,
                          QSizePolicy, QSpacerItem, QGridLayout,
                          QHBoxLayout, QToolButton, QPalette, QPushButton )
from utils.pixmapcache import PixmapCache
from utils.settings import Settings
from ui.combobox import CDMComboBox
from variablesbrowser import VariablesBrowser
from utils.globals import GlobalData


class VariablesViewer( QWidget ):
    " Implements the variables viewer for a debugger "

    # First group of filters
    FilterGlobalAndLocal = 0
    FilterGlobalOnly = 1
    FilterLocalOnly = 2

    def __init__( self, debugger, parent = None ):
        QWidget.__init__( self, parent )

        self.__debugger = debugger
        self.__browser = VariablesBrowser( debugger, self )
        self.__filter = Settings().debugGLFilter
        self.__hideMCFFilter = Settings().debugHideMCF
        self.__createLayout()

        self.setTabOrder( self.__browser, self.__execStatement )
        self.setTabOrder( self.__execStatement, self.__execButton )
        self.setTabOrder( self.__execButton, self.__evalStatement )
        self.setTabOrder( self.__evalStatement, self.__evalButton )

        self.__updateFilter()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 0, 0, 0, 0 )
        verticalLayout.setSpacing( 0 )

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

        self.__headerLabel = QLabel( "Variables" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )
        fixedSpacer1 = QSpacerItem( 5, 5 )

        self.__mcfButton = QToolButton()
        self.__mcfButton.setCheckable( True )
        self.__mcfButton.setChecked( self.__hideMCFFilter )
        self.__mcfButton.setIcon( PixmapCache().getIcon( 'dbgfltmcf.png' ) )
        self.__mcfButton.setFixedSize( 20, 20 )
        self.__mcfButton.setToolTip( "Show/hide modules, classes and functions" )
        self.__mcfButton.setFocusPolicy( Qt.NoFocus )
        self.__mcfButton.clicked.connect( self.__onMCFFilter )

        self.__globalAndLocalButton = QToolButton()
        self.__globalAndLocalButton.setCheckable( True )
        self.__globalAndLocalButton.setChecked( self.__filter == VariablesViewer.FilterGlobalAndLocal )
        self.__globalAndLocalButton.setIcon( PixmapCache().getIcon( 'dbgfltgl.png' ) )
        self.__globalAndLocalButton.setFixedSize( 20, 20 )
        self.__globalAndLocalButton.setToolTip( "Do not filter out global or local variables" )
        self.__globalAndLocalButton.setFocusPolicy( Qt.NoFocus )
        self.__globalAndLocalButton.clicked.connect( self.__onGlobalAndLocalFilter )

        self.__localOnlyButton = QToolButton()
        self.__localOnlyButton.setCheckable( True )
        self.__localOnlyButton.setChecked( self.__filter == VariablesViewer.FilterLocalOnly )
        self.__localOnlyButton.setIcon( PixmapCache().getIcon( 'dbgfltlo.png' ) )
        self.__localOnlyButton.setFixedSize( 20, 20 )
        self.__localOnlyButton.setToolTip( "Filter out global variables" )
        self.__localOnlyButton.setFocusPolicy( Qt.NoFocus )
        self.__localOnlyButton.clicked.connect( self.__onLocalFilter )

        self.__globalOnlyButton = QToolButton()
        self.__globalOnlyButton.setCheckable( True )
        self.__globalOnlyButton.setChecked( self.__filter == VariablesViewer.FilterGlobalOnly )
        self.__globalOnlyButton.setIcon( PixmapCache().getIcon( 'dbgfltgo.png' ) )
        self.__globalOnlyButton.setFixedSize( 20, 20 )
        self.__globalOnlyButton.setToolTip( "Filter out local variables" )
        self.__globalOnlyButton.setFocusPolicy( Qt.NoFocus )
        self.__globalOnlyButton.clicked.connect( self.__onGlobalFilter )

        self.__execStatement = CDMComboBox( True )
        self.__execStatement.setSizePolicy( QSizePolicy.Expanding,
                                            QSizePolicy.Expanding )
        self.__execStatement.lineEdit().setToolTip(
                                "Expression to be executed" )
        self.__execStatement.setFixedHeight( 26 )
        self.__execStatement.editTextChanged.connect( self.__execStatementChanged )
        self.__execStatement.enterClicked.connect( self.__onEnterInExec )
        self.__execButton = QPushButton( "Exec" )
        # self.__execButton.setFocusPolicy( Qt.NoFocus )
        self.__execButton.setEnabled( False )
        self.__execButton.clicked.connect( self.__onExec )

        self.__evalStatement = CDMComboBox( True )
        self.__evalStatement.setSizePolicy( QSizePolicy.Expanding,
                                            QSizePolicy.Expanding )
        self.__evalStatement.lineEdit().setToolTip(
                                "Expression to be evaluated" )
        self.__evalStatement.setFixedHeight( 26 )
        self.__evalStatement.editTextChanged.connect( self.__evalStatementChanged )
        self.__evalStatement.enterClicked.connect( self.__onEnterInEval )
        self.__evalButton = QPushButton( "Eval" )
        # self.__evalButton.setFocusPolicy( Qt.NoFocus )
        self.__evalButton.setEnabled( False )
        self.__evalButton.clicked.connect( self.__onEval )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.setSpacing( 0 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__headerLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__mcfButton )
        headerLayout.addSpacerItem( fixedSpacer1 )
        headerLayout.addWidget( self.__globalAndLocalButton )
        headerLayout.addWidget( self.__localOnlyButton )
        headerLayout.addWidget( self.__globalOnlyButton )
        headerFrame.setLayout( headerLayout )

        execEvalLayout = QGridLayout()
        execEvalLayout.setContentsMargins( 1, 1, 1, 1 )
        execEvalLayout.setSpacing( 1 )
        execEvalLayout.addWidget( self.__execStatement, 0, 0 )
        execEvalLayout.addWidget( self.__execButton, 0, 1 )
        execEvalLayout.addWidget( self.__evalStatement, 1, 0 )
        execEvalLayout.addWidget( self.__evalButton, 1, 1 )

        verticalLayout.addWidget( headerFrame )
        verticalLayout.addWidget( self.__browser )
        verticalLayout.addLayout( execEvalLayout )

        return

    def __onMCFFilter( self ):
        " Triggered when modules/classes/functions filter changed "
        self.__hideMCFFilter = self.__mcfButton.isChecked()
        Settings().debugHideMCF = self.__hideMCFFilter
        self.__updateFilter()
        return

    def __onGlobalAndLocalFilter( self ):
        " Global and local filter has been pressed "
        self.__globalAndLocalButton.setChecked( True )
        self.__localOnlyButton.setChecked( False )
        self.__globalOnlyButton.setChecked( False )

        if self.__filter == VariablesViewer.FilterGlobalAndLocal:
            # No changes
            return

        Settings().debugGLFilter = VariablesViewer.FilterGlobalAndLocal
        self.__filter = VariablesViewer.FilterGlobalAndLocal
        self.__updateFilter()
        return

    def __onLocalFilter( self ):
        " Local only filter has been pressed "
        self.__globalAndLocalButton.setChecked( False )
        self.__localOnlyButton.setChecked( True )
        self.__globalOnlyButton.setChecked( False )

        if self.__filter == VariablesViewer.FilterLocalOnly:
            # No changes
            return

        Settings().debugGLFilter = VariablesViewer.FilterLocalOnly
        self.__filter = VariablesViewer.FilterLocalOnly
        self.__updateFilter()
        return

    def __onGlobalFilter( self ):
        " Global only filter has been pressed "
        self.__globalAndLocalButton.setChecked( False )
        self.__localOnlyButton.setChecked( False )
        self.__globalOnlyButton.setChecked( True )

        if self.__filter == VariablesViewer.FilterGlobalOnly:
            # No changes
            return

        Settings().debugGLFilter = VariablesViewer.FilterGlobalOnly
        self.__filter = VariablesViewer.FilterGlobalOnly
        self.__updateFilter()
        return

    def updateVariables( self, areGlobals, frameNumber, variables ):
        " Triggered when a new set of variables is received "
        self.__browser.showVariables( areGlobals, variables, frameNumber )
        self.__updateHeaderLabel()
        return

    def updateVariable( self, areGlobals, variables ):
        " Triggered when a new variable has been received "
        self.__browser.showVariable( areGlobals, variables )
        self.__updateHeaderLabel()
        return

    def __updateHeaderLabel( self ):
        shown, total = self.__browser.getShownAndTotalCounts()
        if shown == 0 and total == 0:
            self.__headerLabel.setText( "Variables" )
        else:
            self.__headerLabel.setText( "Variables (" + str( shown ) +
                                        " of " + str( total ) + ")" )
        return

    def __textFilterChanged( self, text ):
        " Triggered when a text filter has been changed "
        self.__updateFilter()
        return

    def __updateFilter( self ):
        " Updates the current filter "
        self.__browser.setFilter( self.__hideMCFFilter,
                                  self.__filter, "" )
        self.__updateHeaderLabel()
        return

    def clear( self ):
        " Clears the content "
        self.__browser.clear()
        self.__updateHeaderLabel()
        return

    def clearAll( self ):
        " Clears everything including the history "
        self.clear()
        self.__execStatement.lineEdit().setText( "" )
        self.__execStatement.clear()
        self.__evalStatement.lineEdit().setText( "" )
        self.__evalStatement.clear()
        return

    def __evalStatementChanged( self, text ):
        " Triggered when a eval statement is changed "
        text = str( text ).strip()
        self.__evalButton.setEnabled( text != "" )
        return

    def __onEnterInEval( self ):
        " Enter/return in eval "
        self.__onEval()
        return

    def __onEval( self ):
        " Triggered when the Eval button is clicked "
        text = self.__evalStatement.currentText().strip()
        if text != "":
            currentFrame = GlobalData().mainWindow.getCurrentFrameNumber()
            self.__debugger.remoteEval( text, currentFrame )
            self.__debugger.remoteClientVariables( 1, currentFrame )  # globals
            self.__debugger.remoteClientVariables( 0, currentFrame )  # locals
        return

    def __execStatementChanged( self, text ):
        " Triggered when a exec statement is changed "
        text = str( text ).strip()
        self.__execButton.setEnabled( text != "" )
        return

    def __onEnterInExec( self ):
        " Enter/return clicked in exec "
        self.__onExec()
        return

    def __onExec( self ):
        " Triggered when the Exec button is clicked "
        text = self.__execStatement.currentText().strip()
        if text != "":
            currentFrame = GlobalData().mainWindow.getCurrentFrameNumber()
            self.__debugger.remoteExec( text, currentFrame )
            self.__debugger.remoteClientVariables( 1, currentFrame )  # globals
            self.__debugger.remoteClientVariables( 0, currentFrame )  # locals
        return

    def switchControl( self, isInIDE ):
        " Switches the UI depending where the control flow is "
        self.__browser.setEnabled( isInIDE )
        self.__globalAndLocalButton.setEnabled( isInIDE )
        self.__localOnlyButton.setEnabled( isInIDE )
        self.__globalOnlyButton.setEnabled( isInIDE )

        self.__execStatement.setEnabled( isInIDE )
        if isInIDE:
            text = self.__execStatement.currentText().strip()
            self.__execButton.setEnabled( text != "" )
        else:
            self.__execButton.setEnabled( False )

        self.__evalStatement.setEnabled( isInIDE )
        if isInIDE:
            text = self.__evalStatement.currentText().strip()
            self.__evalButton.setEnabled( text != "" )
        else:
            self.__evalButton.setEnabled( False )
        return
