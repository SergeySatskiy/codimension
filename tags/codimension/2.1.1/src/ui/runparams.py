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
# $Id: runparams.py 1438 2013-05-14 20:42:11Z sergey.satskiy@gmail.com $
#


""" Run parameters dialog """


import os, os.path, copy
from PyQt4.QtCore   import Qt, SIGNAL, QStringList
from PyQt4.QtGui    import QDialog, QDialogButtonBox, QVBoxLayout, \
                           QSizePolicy, QLabel, QGridLayout, QHBoxLayout, \
                           QRadioButton, QGroupBox, QPushButton, QFileDialog, \
                           QLineEdit, QTreeWidget, QAbstractItemView, \
                           QTreeWidgetItem, QCheckBox, QDoubleValidator
from itemdelegates  import NoOutlineHeightDelegate
from utils.run      import RunParameters, parseCommandLineArguments, \
                           TERM_AUTO, TERM_GNOME, TERM_KONSOLE, TERM_XTERM


class EnvVarDialog( QDialog ):
    " Single environment variable add/edit dialog "
    def __init__( self, name = '', value = '', parent = None ):
        QDialog.__init__( self, parent )

        self.name = name
        self.value = value

        self.__nameEdit = None
        self.__valueEdit = None
        self.__OKButton = None
        self.__createLayout()

        self.setWindowTitle( "Environment variable" )
        self.setMaximumHeight( self.sizeHint().height() )
        self.setMaximumHeight( self.sizeHint().height() )

        self.__nameEdit.setText( name )
        self.__valueEdit.setText( value )

        self.__nameEdit.setEnabled( name == "" )
        self.__OKButton.setEnabled( name != "" )
        return

    def __createLayout( self ):
        " Creates the dialog layout "

        self.resize( 300, 50 )
        self.setSizeGripEnabled( True )

        # Top level layout
        layout = QVBoxLayout( self )

        gridLayout = QGridLayout()
        nameLabel = QLabel( "Name" )
        gridLayout.addWidget( nameLabel, 0, 0 )
        valueLabel = QLabel( "Value" )
        gridLayout.addWidget( valueLabel, 1, 0 )
        self.__nameEdit = QLineEdit()
        self.connect( self.__nameEdit,
                      SIGNAL( 'textChanged(const QString &)' ),
                      self.__nameChanged )
        gridLayout.addWidget( self.__nameEdit, 0, 1 )
        self.__valueEdit = QLineEdit()
        self.connect( self.__valueEdit,
                      SIGNAL( 'textChanged(const QString &)' ),
                      self.__valueChanged )
        gridLayout.addWidget( self.__valueEdit, 1, 1 )
        layout.addLayout( gridLayout )

        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setDefault( True )
        self.connect( buttonBox, SIGNAL( "accepted()" ), self.accept )
        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        layout.addWidget( buttonBox )
        return

    def __nameChanged( self, newName ):
        " Triggered when a variable name is changed "
        strippedName = str( newName ).strip()
        self.__OKButton.setEnabled( strippedName != "" and \
                                    ' ' not in strippedName )
        self.name = strippedName
        return

    def __valueChanged( self, newValue ):
        " Triggered when a variable value is changed "
        self.value = newValue
        return



class RunDialog( QDialog ):
    """ Run parameters dialog implementation """

    # See utils.run for runParameters
    def __init__( self, path, runParameters, termType,
                  profilerParams, debuggerParams,
                  action = "", parent = None ):
        QDialog.__init__( self, parent )

        # Used as a return value
        self.termType = termType
        self.profilerParams = copy.deepcopy( profilerParams )
        self.debuggerParams = copy.deepcopy( debuggerParams )

        self.__action = action.lower()

        # Avoid pylint complains
        self.__argsEdit = None
        self.__scriptWDRButton = None
        self.__dirRButton = None
        self.__dirEdit = None
        self.__dirSelectButton = None
        self.__inheritParentRButton = None
        self.__inheritParentPlusRButton = None
        self.__inhPlusEnvTable = None
        self.__addInhButton = None
        self.__delInhButton = None
        self.__editInhButton = None
        self.__specificRButton = None
        self.__specEnvTable = None
        self.__addSpecButton = None
        self.__delSpecButton = None
        self.__editSpecButton = None
        self.__runButton = None
        self.__nodeLimitEdit = None
        self.__edgeLimitEdit = None

        self.__createLayout( action )
        self.setWindowTitle( action + " parameters for " + path )

        # Restore the values
        self.runParams = copy.deepcopy( runParameters )
        self.__argsEdit.setText( self.runParams.arguments )

        # Working dir
        if self.runParams.useScriptLocation:
            self.__scriptWDRButton.setChecked( True )
            self.__dirEdit.setEnabled( False )
            self.__dirSelectButton.setEnabled( False )
        else:
            self.__dirRButton.setChecked( True )
            self.__dirEdit.setEnabled( True )
            self.__dirSelectButton.setEnabled( True )

        self.__dirEdit.setText( self.runParams.specificDir )

        # Environment
        self.__populateTable( self.__inhPlusEnvTable,
                              self.runParams.additionToParentEnv )
        self.__populateTable( self.__specEnvTable,
                              self.runParams.specificEnv )

        if self.runParams.envType == RunParameters.InheritParentEnv:
            self.__inheritParentRButton.setChecked( True )
            self.__setEnabledInheritedPlusEnv( False )
            self.__setEnabledSpecificEnv( False )
        elif self.runParams.envType == RunParameters.InheritParentEnvPlus:
            self.__inheritParentPlusRButton.setChecked( True )
            self.__setEnabledSpecificEnv( False )
        else:
            self.__specificRButton.setChecked( True )
            self.__setEnabledInheritedPlusEnv( False )

        # Terminal
        if self.termType == TERM_AUTO:
            self.__autoRButton.setChecked( True )
        elif self.termType == TERM_KONSOLE:
            self.__konsoleRButton.setChecked( True )
        elif self.termType == TERM_GNOME:
            self.__gnomeRButton.setChecked( True )
        else:
            self.__xtermRButton.setChecked( True )

        # Close checkbox
        self.__closeCheckBox.setChecked( self.runParams.closeTerminal )

        # Profile limits if so
        if self.__action == "profile":
            if self.profilerParams.nodeLimit < 0.0 or \
               self.profilerParams.nodeLimit > 100.0:
                self.profilerParams.nodeLimit = 1.0
            self.__nodeLimitEdit.setText( str( self.profilerParams.nodeLimit ) )
            if self.profilerParams.edgeLimit < 0.0 or \
               self.profilerParams.edgeLimit > 100.0:
                self.profilerParams.edgeLimit = 1.0
            self.__edgeLimitEdit.setText( str( self.profilerParams.edgeLimit ) )
        elif self.__action == "debug":
            self.__reportExceptionCheckBox.setChecked(
                                    self.debuggerParams.reportExceptions )
            self.__traceInterpreterCheckBox.setChecked(
                                    self.debuggerParams.traceInterpreter )
            self.__stopAtFirstCheckBox.setChecked(
                                    self.debuggerParams.stopAtFirstLine )
            self.__autoforkCheckBox.setChecked(
                                    self.debuggerParams.autofork )
            self.__debugChildCheckBox.setChecked(
                                    self.debuggerParams.followChild )
            self.__debugChildCheckBox.setEnabled( self.debuggerParams.autofork )

        self.__setRunButtonProps()
        return

    @staticmethod
    def __populateTable( table, dictionary ):
        " Populates the given table "
        for key, value in dictionary.iteritems():
            item = QTreeWidgetItem( QStringList() << key << value )
            table.addTopLevelItem( item )
        if dictionary:
            table.setCurrentItem( table.topLevelItem( 0 ) )
        return

    def __setEnabledInheritedPlusEnv( self, value ):
        " Disables/enables 'inherited and add' section controls "
        self.__inhPlusEnvTable.setEnabled( value )
        self.__addInhButton.setEnabled( value )
        self.__delInhButton.setEnabled( value )
        self.__editInhButton.setEnabled( value )
        return

    def __setEnabledSpecificEnv( self, value ):
        " Disables/enables 'specific env' section controls "
        self.__specEnvTable.setEnabled( value )
        self.__addSpecButton.setEnabled( value )
        self.__delSpecButton.setEnabled( value )
        self.__editSpecButton.setEnabled( value )
        return

    def __createLayout( self, action ):
        """ Creates the dialog layout """

        self.resize( 650, 300 )
        self.setSizeGripEnabled( True )

        # Top level layout
        layout = QVBoxLayout( self )

        # Cmd line arguments
        argsLabel = QLabel( "Command line &arguments" )
        self.__argsEdit = QLineEdit()
        self.connect( self.__argsEdit,
                      SIGNAL( 'textChanged(const QString &)' ),
                      self.__argsChanged )
        argsLayout = QHBoxLayout()
        argsLayout.addWidget( argsLabel )
        argsLayout.addWidget( self.__argsEdit )
        layout.addLayout( argsLayout )

        # Working directory
        workDirGroupbox = QGroupBox( self )
        workDirGroupbox.setTitle( "Working directory" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                        workDirGroupbox.sizePolicy().hasHeightForWidth() )
        workDirGroupbox.setSizePolicy( sizePolicy )

        gridLayoutWD = QGridLayout( workDirGroupbox )
        self.__scriptWDRButton = QRadioButton( workDirGroupbox )
        self.__scriptWDRButton.setText( "&Use script location" )
        gridLayoutWD.addWidget( self.__scriptWDRButton, 0, 0 )
        self.connect( self.__scriptWDRButton, SIGNAL( 'clicked()' ),
                      self.__scriptWDirClicked )

        self.__dirRButton = QRadioButton( workDirGroupbox )
        self.__dirRButton.setText( "Select &directory" )
        gridLayoutWD.addWidget( self.__dirRButton, 1, 0 )
        self.connect( self.__dirRButton, SIGNAL( 'clicked()' ),
                      self.__dirClicked )

        self.__dirEdit = QLineEdit( workDirGroupbox )
        gridLayoutWD.addWidget( self.__dirEdit, 1, 1 )
        self.connect( self.__dirEdit,
                      SIGNAL( 'textChanged(const QString &)' ),
                      self.__workingDirChanged )

        self.__dirSelectButton = QPushButton( workDirGroupbox )
        self.__dirSelectButton.setText( "..." )
        gridLayoutWD.addWidget( self.__dirSelectButton, 1, 2 )
        self.connect( self.__dirSelectButton, SIGNAL( 'clicked()' ),
                      self.__selectDirClicked )

        layout.addWidget( workDirGroupbox )

        # Environment
        envGroupbox = QGroupBox( self )
        envGroupbox.setTitle( "Environment" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                        envGroupbox.sizePolicy().hasHeightForWidth() )
        envGroupbox.setSizePolicy( sizePolicy )

        layoutEnv = QVBoxLayout( envGroupbox )
        self.__inheritParentRButton = QRadioButton( envGroupbox )
        self.__inheritParentRButton.setText( "Inherit &parent" )
        self.connect( self.__inheritParentRButton, SIGNAL( 'clicked()' ),
                      self.__inhClicked )
        layoutEnv.addWidget( self.__inheritParentRButton )

        self.__inheritParentPlusRButton = QRadioButton( envGroupbox )
        self.__inheritParentPlusRButton.setText( "Inherit parent and add/&modify" )
        self.connect( self.__inheritParentPlusRButton, SIGNAL( 'clicked()' ),
                      self.__inhPlusClicked )
        layoutEnv.addWidget( self.__inheritParentPlusRButton )
        hInhPlusLayout = QHBoxLayout()
        self.__inhPlusEnvTable = QTreeWidget()
        self.connect( self.__inhPlusEnvTable,
                      SIGNAL( 'itemActivated(QTreeWidgetItem*, int)' ),
                      self.__inhPlusItemActivated )
        self.__tuneTable( self.__inhPlusEnvTable )
        hInhPlusLayout.addWidget( self.__inhPlusEnvTable )
        vInhPlusLayout = QVBoxLayout()
        self.__addInhButton = QPushButton()
        self.connect( self.__addInhButton, SIGNAL( 'clicked()' ),
                      self.__addInhClicked )
        self.__addInhButton.setText( 'Add' )
        vInhPlusLayout.addWidget( self.__addInhButton )
        self.__delInhButton = QPushButton()
        self.connect( self.__delInhButton, SIGNAL( 'clicked()' ),
                      self.__delInhClicked )
        self.__delInhButton.setText( 'Delete' )
        vInhPlusLayout.addWidget( self.__delInhButton )
        self.__editInhButton = QPushButton()
        self.connect( self.__editInhButton, SIGNAL( 'clicked()' ),
                      self.__editInhClicked )
        self.__editInhButton.setText( "Edit" )
        vInhPlusLayout.addWidget( self.__editInhButton )
        hInhPlusLayout.addLayout( vInhPlusLayout )
        layoutEnv.addLayout( hInhPlusLayout )

        self.__specificRButton = QRadioButton( envGroupbox )
        self.__specificRButton.setText( "&Specific" )
        self.connect( self.__specificRButton, SIGNAL( 'clicked()' ),
                      self.__specClicked )
        layoutEnv.addWidget( self.__specificRButton )
        hSpecLayout = QHBoxLayout()
        self.__specEnvTable = QTreeWidget()
        self.connect( self.__specEnvTable,
                      SIGNAL( 'itemActivated(QTreeWidgetItem*, int)' ),
                      self.__specItemActivated )
        self.__tuneTable( self.__specEnvTable )
        hSpecLayout.addWidget( self.__specEnvTable )
        vSpecLayout = QVBoxLayout()
        self.__addSpecButton = QPushButton()
        self.connect( self.__addSpecButton, SIGNAL( 'clicked()' ),
                      self.__addSpecClicked )
        self.__addSpecButton.setText( 'Add' )
        vSpecLayout.addWidget( self.__addSpecButton )
        self.__delSpecButton = QPushButton()
        self.connect( self.__delSpecButton, SIGNAL( 'clicked()' ),
                      self.__delSpecClicked )
        self.__delSpecButton.setText( 'Delete' )
        vSpecLayout.addWidget( self.__delSpecButton )
        self.__editSpecButton = QPushButton()
        self.connect( self.__editSpecButton, SIGNAL( 'clicked()' ),
                      self.__editSpecClicked )
        self.__editSpecButton.setText( "Edit" )
        vSpecLayout.addWidget( self.__editSpecButton )
        hSpecLayout.addLayout( vSpecLayout )
        layoutEnv.addLayout( hSpecLayout )
        layout.addWidget( envGroupbox )

        # Terminal and profile limits
        if self.__action in [ "profile", "debug" ]:
            layout.addWidget( self.__getIDEWideGroupbox() )
        else:
            termGroupbox = self.__getTermGroupbox()
            termGroupbox.setTitle( "Terminal to run in (IDE wide setting)" )
            layout.addWidget( termGroupbox )

        # Close checkbox
        self.__closeCheckBox = QCheckBox( "&Close terminal upon " \
                                          "successful completion" )
        self.connect( self.__closeCheckBox, SIGNAL( "stateChanged(int)" ),
                      self.__onCloseChanged )
        layout.addWidget( self.__closeCheckBox )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Cancel )
        self.__runButton = buttonBox.addButton( action,
                                                QDialogButtonBox.AcceptRole )
        self.__runButton.setDefault( True )
        self.connect( self.__runButton, SIGNAL( 'clicked()' ),
                      self.onAccept )
        layout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        return

    def __getTermGroupbox( self ):
        " Creates the term groupbox "
        termGroupbox = QGroupBox( self )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                        termGroupbox.sizePolicy().hasHeightForWidth() )
        termGroupbox.setSizePolicy( sizePolicy )

        layoutTerm = QVBoxLayout( termGroupbox )
        self.__autoRButton = QRadioButton( termGroupbox )
        self.__autoRButton.setText( "Aut&o detection" )
        layoutTerm.addWidget( self.__autoRButton )
        self.__konsoleRButton = QRadioButton( termGroupbox )
        self.__konsoleRButton.setText( "Default &KDE konsole" )
        layoutTerm.addWidget( self.__konsoleRButton )
        self.__gnomeRButton = QRadioButton( termGroupbox )
        self.__gnomeRButton.setText( "gnome-&terminal" )
        layoutTerm.addWidget( self.__gnomeRButton )
        self.__xtermRButton = QRadioButton( termGroupbox )
        self.__xtermRButton.setText( "&xterm" )
        layoutTerm.addWidget( self.__xtermRButton )
        return termGroupbox

    def __getIDEWideGroupbox( self ):
        " Creates the IDE wide groupbox "
        ideGroupbox = QGroupBox( self )
        ideGroupbox.setTitle( "IDE Wide Settings" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                        ideGroupbox.sizePolicy().hasHeightForWidth() )
        ideGroupbox.setSizePolicy( sizePolicy )

        layoutIDE = QHBoxLayout( ideGroupbox )

        termGroupbox = self.__getTermGroupbox()
        termGroupbox.setTitle( "Terminal to run in" )
        layoutIDE.addWidget( termGroupbox )

        if self.__action == "profile":
            # Profile version of the dialog
            limitsGroupbox = self.__getProfileLimitsGroupbox()
            layoutIDE.addWidget( limitsGroupbox )
        else:
            # Debug version of the dialog
            dbgGroupbox = self.__getDebugGroupbox()
            layoutIDE.addWidget( dbgGroupbox )
        return ideGroupbox

    def __getProfileLimitsGroupbox( self ):
        " Creates the profile limits groupbox "
        limitsGroupbox = QGroupBox( self )
        limitsGroupbox.setTitle( "Profiler diagram limits" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                limitsGroupbox.sizePolicy().hasHeightForWidth() )
        limitsGroupbox.setSizePolicy( sizePolicy )

        layoutLimits = QGridLayout( limitsGroupbox )
        self.__nodeLimitEdit = QLineEdit()
        self.connect( self.__nodeLimitEdit, SIGNAL( "textEdited(const QString &)" ),
                      self.__setRunButtonProps )
        self.__nodeLimitValidator = QDoubleValidator( 0.0, 100.0, 2, self )
        self.__nodeLimitValidator.setNotation( QDoubleValidator.StandardNotation )
        self.__nodeLimitEdit.setValidator( self.__nodeLimitValidator )
        nodeLimitLabel = QLabel( "Hide &nodes below" )
        self.__edgeLimitEdit = QLineEdit()
        self.connect( self.__edgeLimitEdit, SIGNAL( "textEdited(const QString &)" ),
                      self.__setRunButtonProps )
        self.__edgeLimitValidator = QDoubleValidator( 0.0, 100.0, 2, self )
        self.__edgeLimitValidator.setNotation( QDoubleValidator.StandardNotation )
        self.__edgeLimitEdit.setValidator( self.__edgeLimitValidator )
        edgeLimitLabel = QLabel( "Hide &edges below" )
        layoutLimits.addWidget( nodeLimitLabel, 0, 0 )
        layoutLimits.addWidget( self.__nodeLimitEdit, 0, 1 )
        layoutLimits.addWidget( QLabel( "%" ), 0, 2 )
        layoutLimits.addWidget( edgeLimitLabel, 1, 0 )
        layoutLimits.addWidget( self.__edgeLimitEdit, 1, 1 )
        layoutLimits.addWidget( QLabel( "%" ), 1, 2 )
        return limitsGroupbox

    def __getDebugGroupbox( self ):
        " Creates the debug settings groupbox "
        dbgGroupbox = QGroupBox( self )
        dbgGroupbox.setTitle( "Debugger" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(
                    dbgGroupbox.sizePolicy().hasHeightForWidth() )
        dbgGroupbox.setSizePolicy( sizePolicy )

        dbgLayout = QVBoxLayout( dbgGroupbox )
        self.__reportExceptionCheckBox = QCheckBox( "Report &exceptions" )
        self.connect( self.__reportExceptionCheckBox, SIGNAL( "stateChanged(int)" ),
                      self.__onReportExceptionChanged )
        self.__traceInterpreterCheckBox = QCheckBox( "T&race interpreter libs" )
        self.connect( self.__traceInterpreterCheckBox, SIGNAL( "stateChanged(int)" ),
                      self.__onTraceInterpreterChanged )
        self.__stopAtFirstCheckBox = QCheckBox( "Stop at first &line" )
        self.connect( self.__stopAtFirstCheckBox, SIGNAL( "stateChanged(int)" ),
                      self.__onStopAtFirstChanged )
        self.__autoforkCheckBox = QCheckBox( "&Fork without asking" )
        self.connect( self.__autoforkCheckBox, SIGNAL( "stateChanged(int)" ),
                      self.__onAutoforkChanged )
        self.__debugChildCheckBox = QCheckBox( "Debu&g child process" )
        self.connect( self.__debugChildCheckBox, SIGNAL( "stateChanged(int)" ),
                      self.__onDebugChild )

        dbgLayout.addWidget( self.__reportExceptionCheckBox )
        dbgLayout.addWidget( self.__traceInterpreterCheckBox )
        dbgLayout.addWidget( self.__stopAtFirstCheckBox )
        dbgLayout.addWidget( self.__autoforkCheckBox )
        dbgLayout.addWidget( self.__debugChildCheckBox )
        return dbgGroupbox


    @staticmethod
    def __tuneTable( table ):
        " Sets the common settings for a table "

        table.setAlternatingRowColors( True )
        table.setRootIsDecorated( False )
        table.setItemsExpandable( False )
        table.setUniformRowHeights( True )
        table.setSelectionMode( QAbstractItemView.SingleSelection )
        table.setSelectionBehavior( QAbstractItemView.SelectRows )
        table.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        headerLabels = QStringList() << "Variable" << "Value"
        table.setHeaderLabels( headerLabels )

        header = table.header()
        header.setSortIndicator( 0, Qt.AscendingOrder )
        header.setSortIndicatorShown( True )
        header.setClickable( True )
        table.setSortingEnabled( True )
        return

    def __scriptWDirClicked( self ):
        " The script working dir button is clicked "
        self.__dirEdit.setEnabled( False )
        self.__dirSelectButton.setEnabled( False )
        self.runParams.useScriptLocation = True

        self.__setRunButtonProps()
        return

    def __dirClicked( self ):
        " The script specific working dir button is clicked "
        self.__dirEdit.setEnabled( True )
        self.__dirSelectButton.setEnabled( True )
        self.runParams.useScriptLocation = False

        self.__setRunButtonProps()
        return

    def __argsChanged( self, value ):
        " Triggered when cmd line args are changed "
        value = str( value ).strip()
        self.runParams.arguments = value
        self.__setRunButtonProps()
        return

    def __workingDirChanged( self, value ):
        " Triggered when a working dir value is changed "
        value = str( value )
        self.runParams.specificDir = value
        self.__setRunButtonProps()
        return

    def __onCloseChanged( self, state ):
        " Triggered when the close terminal check box changed "
        self.runParams.closeTerminal = state != 0
        return

    def __onReportExceptionChanged( self, state ):
        " Triggered when exception report check box changed "
        self.debuggerParams.reportExceptions = state != 0
        return

    def __onTraceInterpreterChanged( self, state ):
        " Triggered when trace interpreter changed "
        self.debuggerParams.traceInterpreter = state != 0
        return

    def __onStopAtFirstChanged( self, state ):
        " Triggered when stop at first changed "
        self.debuggerParams.stopAtFirstLine = state != 0
        return

    def __onAutoforkChanged( self, state ):
        " Triggered when autofork changed "
        self.debuggerParams.autofork = state != 0
        self.__debugChildCheckBox.setEnabled( self.debuggerParams.autofork )
        return

    def __onDebugChild( self, state ):
        " Triggered when debug child changed "
        self.debuggerParams.followChild = state != 0
        return

    def __argumentsOK( self ):
        " Returns True if the arguments are OK "
        try:
            parseCommandLineArguments( self.runParams.arguments )
            return True
        except:
            return False

    def __dirOK( self ):
        " Returns True if the working dir is OK "
        if self.__scriptWDRButton.isChecked():
            return True
        return os.path.isdir( str( self.__dirEdit.text() ) )

    def __setRunButtonProps( self, newText = None ):
        " Enable/disable run button and set its tooltip "
        if not self.__argumentsOK():
            self.__runButton.setEnabled( False )
            self.__runButton.setToolTip( "No closing quotation in arguments" )
            return

        if not self.__dirOK():
            self.__runButton.setEnabled( False )
            self.__runButton.setToolTip( "The given working " \
                                         "dir is not found" )
            return

        if self.__nodeLimitEdit is not None:
            txt = str( self.__nodeLimitEdit.text() ).strip()
            try:
                value = float( txt )
                if value < 0.0 or value > 100.0:
                    raise Exception( "Out of range" )
            except:
                self.__runButton.setEnabled( False )
                self.__runButton.setToolTip( "The given node limit " \
                                             "is out of range" )
                return

        if self.__edgeLimitEdit is not None:
            txt = str( self.__edgeLimitEdit.text() ).strip()
            try:
                value = float( txt )
                if value < 0.0 or value > 100.0:
                    raise Exception( "Out of range" )
            except:
                self.__runButton.setEnabled( False )
                self.__runButton.setToolTip( "The given edge limit " \
                                             "is out of range" )
                return

        self.__runButton.setEnabled( True )
        self.__runButton.setToolTip( "Save parameters and " + \
                                     self.__action + " script" )
        return

    def __selectDirClicked( self ):
        " Selects the script working dir "
        dirName = QFileDialog.getExistingDirectory( self,
                    "Select the script working directory",
                    self.__dirEdit.text(),
                    QFileDialog.Options( QFileDialog.ShowDirsOnly ) )

        if not dirName.isEmpty():
            self.__dirEdit.setText( os.path.normpath( str( dirName ) ) )
        return

    def __inhClicked( self ):
        " Inerit parent env radio button clicked "
        self.__setEnabledInheritedPlusEnv( False )
        self.__setEnabledSpecificEnv( False )
        self.runParams.envType = RunParameters.InheritParentEnv
        return

    def __inhPlusClicked( self ):
        " Inherit parent and add radio button clicked "
        self.__setEnabledInheritedPlusEnv( True )
        self.__setEnabledSpecificEnv( False )
        self.runParams.envType = RunParameters.InheritParentEnvPlus

        if self.__inhPlusEnvTable.selectedIndexes():
            self.__delInhButton.setEnabled( True )
            self.__editInhButton.setEnabled( True )
        else:
            self.__delInhButton.setEnabled( False )
            self.__editInhButton.setEnabled( False )
        return

    def __specClicked( self ):
        " Specific env radio button clicked "
        self.__setEnabledInheritedPlusEnv( False )
        self.__setEnabledSpecificEnv( True )
        self.runParams.envType = RunParameters.SpecificEnvironment

        if self.__specEnvTable.selectedIndexes():
            self.__delSpecButton.setEnabled( True )
            self.__editSpecButton.setEnabled( True )
        else:
            self.__delSpecButton.setEnabled( False )
            self.__editSpecButton.setEnabled( False )
        return

    @staticmethod
    def __delAndInsert( table, name, value ):
        " Deletes an item by name if so; insert new; highlight it "
        for index in xrange( table.topLevelItemCount() ):
            item = table.topLevelItem( index )
            if str( item.text( 0 ) ) == name:
                table.takeTopLevelItem( index )
                break

        item = QTreeWidgetItem( QStringList() << name << value )
        table.addTopLevelItem( item )
        table.setCurrentItem( item )
        return item

    def __addInhClicked( self ):
        " Add env var button clicked "
        dlg = EnvVarDialog()
        if dlg.exec_() == QDialog.Accepted:
            name = str( dlg.name )
            value = str( dlg.value )
            self.__delAndInsert( self.__inhPlusEnvTable, name, value )
            self.runParams.additionToParentEnv[ name ] = value
            self.__delInhButton.setEnabled( True )
            self.__editInhButton.setEnabled( True )
        return

    def __addSpecClicked( self ):
        " Add env var button clicked "
        dlg = EnvVarDialog()
        if dlg.exec_() == QDialog.Accepted:
            name = str( dlg.name )
            value = str( dlg.value )
            self.__delAndInsert( self.__specEnvTable, name, value )
            self.runParams.specificEnv[ name ] = value
            self.__delSpecButton.setEnabled( True )
            self.__editSpecButton.setEnabled( True )
        return

    def __delInhClicked( self ):
        " Delete the highlighted variable "
        if self.__inhPlusEnvTable.topLevelItemCount() == 0:
            return

        name = self.__inhPlusEnvTable.currentItem().text( 0 )
        for index in xrange( self.__inhPlusEnvTable.topLevelItemCount() ):
            item = self.__inhPlusEnvTable.topLevelItem( index )
            if name == item.text( 0 ):
                self.__inhPlusEnvTable.takeTopLevelItem( index )
                break

        del self.runParams.additionToParentEnv[ str( name ) ]
        if self.__inhPlusEnvTable.topLevelItemCount() == 0:
            self.__delInhButton.setEnabled( False )
            self.__editInhButton.setEnabled( False )
        else:
            self.__inhPlusEnvTable.setCurrentItem( \
                                self.__inhPlusEnvTable.topLevelItem( 0 ) )
        return

    def __delSpecClicked( self ):
        " Delete the highlighted variable "
        if self.__specEnvTable.topLevelItemCount() == 0:
            return

        name = self.__specEnvTable.currentItem().text( 0 )
        for index in xrange( self.__specEnvTable.topLevelItemCount() ):
            item = self.__specEnvTable.topLevelItem( index )
            if name == item.text( 0 ):
                self.__specEnvTable.takeTopLevelItem( index )
                break

        del self.runParams.specificEnv[ str( name ) ]
        if self.__specEnvTable.topLevelItemCount() == 0:
            self.__delSpecButton.setEnabled( False )
            self.__editSpecButton.setEnabled( False )
        else:
            self.__specEnvTable.setCurrentItem( \
                            self.__specEnvTable.topLevelItem( 0 ) )
        return

    def __editInhClicked( self ):
        " Edits the highlighted variable "
        if self.__inhPlusEnvTable.topLevelItemCount() == 0:
            return

        item = self.__inhPlusEnvTable.currentItem()
        dlg = EnvVarDialog( str( item.text( 0 ) ), str( item.text( 1 ) ), self )
        if dlg.exec_() == QDialog.Accepted:
            name = str( dlg.name )
            value = str( dlg.value )
            self.__delAndInsert( self.__inhPlusEnvTable, name, value )
            self.runParams.additionToParentEnv[ name ] = value
        return

    def __inhPlusItemActivated( self, item, column ):
        " Triggered when a table item is activated "
        self.__editInhClicked()
        return

    def __editSpecClicked( self ):
        " Edits the highlighted variable "
        if self.__specEnvTable.topLevelItemCount() == 0:
            return

        item = self.__specEnvTable.currentItem()
        dlg = EnvVarDialog( str( item.text( 0 ) ), str( item.text( 1 ) ), self )
        if dlg.exec_() == QDialog.Accepted:
            name = str( dlg.name )
            value = str( dlg.value )
            self.__delAndInsert( self.__specEnvTable, name, value )
            self.runParams.specificEnv[ name ] = value
        return

    def __specItemActivated( self, item, column ):
        " Triggered when a table item is activated "
        self.__editSpecClicked()
        return

    def onAccept( self ):
        " Saves the selected terminal and profiling values "
        if self.__autoRButton.isChecked():
            self.termType = TERM_AUTO
        elif self.__konsoleRButton.isChecked():
            self.termType = TERM_KONSOLE
        elif self.__gnomeRButton.isChecked():
            self.termType = TERM_GNOME
        else:
            self.termType = TERM_XTERM

        if self.__action == "profile":
            self.profilerParams.nodeLimit = float(
                                    str( self.__nodeLimitEdit.text() ) )
            self.profilerParams.edgeLimit = float(
                                    str( self.__edgeLimitEdit.text() ) )

        self.accept()
        return
