# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Run parameters dialog"""

import os
import os.path
import copy
from utils.runparams import RunParameters, RUN, PROFILE, DEBUG
from utils.run import parseCommandLineArguments, checkOutput
from .qt import (Qt, QDoubleValidator, QDialog, QDialogButtonBox, QVBoxLayout,
                 QSizePolicy, QLabel, QGridLayout, QHBoxLayout, QRadioButton,
                 QGroupBox, QPushButton, QFileDialog, QLineEdit, QTreeWidget,
                 QAbstractItemView, QTreeWidgetItem, QCheckBox)
from .itemdelegates import NoOutlineHeightDelegate


class EnvVarDialog(QDialog):

    """Single environment variable add/edit dialog"""

    def __init__(self, name='', value='', parent=None):
        QDialog.__init__(self, parent)

        self.name = name
        self.value = value

        self.__nameEdit = None
        self.__valueEdit = None
        self.__OKButton = None
        self.__createLayout()

        self.setWindowTitle("Environment variable")
        self.setMaximumHeight(self.sizeHint().height())
        self.setMaximumHeight(self.sizeHint().height())

        self.__nameEdit.setText(name)
        self.__valueEdit.setText(value)

        self.__nameEdit.setEnabled(name == "")
        self.__OKButton.setEnabled(name != "")

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(300, 50)
        self.setSizeGripEnabled(True)

        # Top level layout
        layout = QVBoxLayout(self)

        gridLayout = QGridLayout()
        nameLabel = QLabel("Name")
        gridLayout.addWidget(nameLabel, 0, 0)
        valueLabel = QLabel("Value")
        gridLayout.addWidget(valueLabel, 1, 0)
        self.__nameEdit = QLineEdit()
        self.__nameEdit.textChanged.connect(self.__nameChanged)
        gridLayout.addWidget(self.__nameEdit, 0, 1)
        self.__valueEdit = QLineEdit()
        self.__valueEdit.textChanged.connect(self.__valueChanged)
        gridLayout.addWidget(self.__valueEdit, 1, 1)
        layout.addLayout(gridLayout)

        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        self.__OKButton = buttonBox.button(QDialogButtonBox.Ok)
        self.__OKButton.setDefault(True)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.close)
        layout.addWidget(buttonBox)

    def __nameChanged(self, newName):
        """Triggered when a variable name is changed"""
        strippedName = str(newName).strip()
        self.__OKButton.setEnabled(strippedName != "" and
                                   ' ' not in strippedName)
        self.name = strippedName

    def __valueChanged(self, newValue):
        """Triggered when a variable value is changed"""
        self.value = newValue


class RunDialog(QDialog):

    """Run parameters dialog implementation"""

    ACTION_TO_VERB = {RUN: 'Run',
                      PROFILE: 'Profile',
                      DEBUG: 'Debug'}

    # See utils.run for runParameters
    def __init__(self, path, runParameters,
                 profilerParams, debuggerParams,
                 action, parent=None):
        QDialog.__init__(self, parent)

        # Used as a return value
        self.runParams = copy.deepcopy(runParameters)
        self.profilerParams = copy.deepcopy(profilerParams)
        self.debuggerParams = copy.deepcopy(debuggerParams)

        self.__action = action

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
        self.__debugChildCheckBox = None
        self.__edgeLimitValidator = None
        self.__nodeLimitValidator = None
        self.__intSelectButton = None
        self.__intEdit = None
        self.__redirectedRButton = None
        self.__customIntRButton = None
        self.__customTermRButton = None
        self.__stopAtFirstCheckBox = None
        self.__traceInterpreterCheckBox = None
        self.__autoforkCheckBox = None
        self.__reportExceptionCheckBox = None
        self.__termEdit = None
        self.__inheritedInterpreterRButton = None

        self.__createLayout()
        self.setWindowTitle(RunDialog.ACTION_TO_VERB[action] +
                            ' parameters for ' + path)

        self.__populateValues()

    def __populateValues(self):
        """Populates the dialog UI controls"""
        self.__argsEdit.setText(self.runParams['arguments'])

        self.__populateWorkingDir()
        self.__populateEnvironment()
        self.__populateInterpreter()
        self.__populateIO()

        if self.__action == PROFILE:
            self.__populateProfile()
        elif self.__action == DEBUG:
            self.__populateDebug()

        self.__setRunButtonProps()

    def __populateWorkingDir(self):
        """Populates the working directory"""
        if self.runParams['useScriptLocation']:
            self.__scriptWDRButton.setChecked(True)
            self.__dirEdit.setEnabled(False)
            self.__dirSelectButton.setEnabled(False)
        else:
            self.__dirRButton.setChecked(True)
            self.__dirEdit.setEnabled(True)
            self.__dirSelectButton.setEnabled(True)
        self.__dirEdit.setText(self.runParams['specificDir'])

    def __populateEnvironment(self):
        """Populates the environment variables"""
        self.__populateTable(self.__inhPlusEnvTable,
                             self.runParams['additionToParentEnv'])
        self.__populateTable(self.__specEnvTable,
                             self.runParams['specificEnv'])

        if self.runParams['envType'] == RunParameters.InheritParentEnv:
            self.__inheritParentRButton.setChecked(True)
            self.__setEnabledInheritedPlusEnv(False)
            self.__setEnabledSpecificEnv(False)
        elif self.runParams['envType'] == RunParameters.InheritParentEnvPlus:
            self.__inheritParentPlusRButton.setChecked(True)
            self.__setEnabledSpecificEnv(False)
        else:
            self.__specificRButton.setChecked(True)
            self.__setEnabledInheritedPlusEnv(False)

    def __populateInterpreter(self):
        """Populates the interpreter"""
        if self.runParams['useInherited']:
            self.__inheritedInterpreterRButton.setChecked(True)
            self.__intEdit.setEnabled(False)
            self.__intSelectButton.setEnabled(False)
        else:
            self.__customIntRButton.setChecked(True)
            self.__intEdit.setEnabled(True)
            self.__intSelectButton.setEnabled(True)
        self.__intEdit.setText(self.runParams['customInterpreter'])

    def __populateIO(self):
        """Populate I/O"""
        if self.runParams['redirected']:
            self.__redirectedRButton.setChecked(True)
            self.__termEdit.setEnabled(False)
        else:
            self.__customTermRButton.setChecked(True)
            self.__termEdit.setEnabled(True)
        self.__termEdit.setText(self.runParams['customTerminal'])
        self.__termEdit.setToolTip(
            'Use ${prog} substitution if needed.\n'
            'Otherwise the command line is attached at the end.\n'
            'E.g.: xterm -e /bin/bash -c "${prog}; /bin/bash" &')

    def __populateProfile(self):
        """Populates profile"""
        if self.profilerParams.nodeLimit < 0.0 or \
           self.profilerParams.nodeLimit > 100.0:
            self.profilerParams.nodeLimit = 1.0
        self.__nodeLimitEdit.setText(str(self.profilerParams.nodeLimit))
        if self.profilerParams.edgeLimit < 0.0 or \
           self.profilerParams.edgeLimit > 100.0:
            self.profilerParams.edgeLimit = 1.0
        self.__edgeLimitEdit.setText(str(self.profilerParams.edgeLimit))

    def __populateDebug(self):
        """Populates debug"""
        self.__reportExceptionCheckBox.setChecked(
            self.debuggerParams.reportExceptions)
        self.__traceInterpreterCheckBox.setChecked(
            self.debuggerParams.traceInterpreter)
        self.__stopAtFirstCheckBox.setChecked(
            self.debuggerParams.stopAtFirstLine)
        self.__autoforkCheckBox.setChecked(self.debuggerParams.autofork)
        self.__debugChildCheckBox.setChecked(self.debuggerParams.followChild)
        self.__debugChildCheckBox.setEnabled(self.debuggerParams.autofork)

    @staticmethod
    def __populateTable(table, dictionary):
        """Populates the given table"""
        for key, value in dictionary.items():
            item = QTreeWidgetItem([key, value])
            table.addTopLevelItem(item)
        if dictionary:
            table.setCurrentItem(table.topLevelItem(0))

    def __setEnabledInheritedPlusEnv(self, value):
        """Disables/enables 'inherited and add' section controls"""
        self.__inhPlusEnvTable.setEnabled(value)
        self.__addInhButton.setEnabled(value)
        self.__delInhButton.setEnabled(value)
        self.__editInhButton.setEnabled(value)

    def __setEnabledSpecificEnv(self, value):
        """Disables/enables 'specific env' section controls"""
        self.__specEnvTable.setEnabled(value)
        self.__addSpecButton.setEnabled(value)
        self.__delSpecButton.setEnabled(value)
        self.__editSpecButton.setEnabled(value)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(650, 300)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)  # top level layout
        layout.addLayout(self.__getArgLayout())
        layout.addWidget(self.__getWorkingDirGroupbox())
        layout.addWidget(self.__getEnvGroupbox())
        layout.addWidget(self.__getInterpreterGroupbox())
        layout.addWidget(self.__getIOGroupbox())

        if self.__action == PROFILE:
            layout.addWidget(self.__getProfileLimitsGroupbox())
        elif self.__action == DEBUG:
            layout.addWidget(self.__getDebugGroupbox())

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        self.__runButton = buttonBox.addButton(
            RunDialog.ACTION_TO_VERB[self.__action],
            QDialogButtonBox.AcceptRole)
        self.__runButton.setDefault(True)
        self.__runButton.clicked.connect(self.onAccept)
        layout.addWidget(buttonBox)

        buttonBox.rejected.connect(self.close)

    def __getArgLayout(self):
        """Provides the arguments layout"""
        argsLabel = QLabel("Command line arguments")
        self.__argsEdit = QLineEdit()
        self.__argsEdit.textChanged.connect(self.__argsChanged)
        argsLayout = QHBoxLayout()
        argsLayout.addWidget(argsLabel)
        argsLayout.addWidget(self.__argsEdit)
        return argsLayout

    @staticmethod
    def __getSizePolicy(item):
        """Provides a common size policy"""
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(item.sizePolicy().hasHeightForWidth())
        return sizePolicy

    def __getWorkingDirGroupbox(self):
        """Provides the working dir groupbox"""
        workDirGroupbox = QGroupBox('Working Directory', self)
        workDirGroupbox.setSizePolicy(self.__getSizePolicy(workDirGroupbox))

        gridLayoutWD = QGridLayout(workDirGroupbox)
        self.__scriptWDRButton = QRadioButton("&Use script location",
                                              workDirGroupbox)
        gridLayoutWD.addWidget(self.__scriptWDRButton, 0, 0)
        self.__scriptWDRButton.clicked.connect(lambda: self.__wdDir(True))

        self.__dirRButton = QRadioButton("Select &directory", workDirGroupbox)
        gridLayoutWD.addWidget(self.__dirRButton, 1, 0)
        self.__dirRButton.clicked.connect(lambda: self.__wdDir(False))

        self.__dirEdit = QLineEdit(workDirGroupbox)
        gridLayoutWD.addWidget(self.__dirEdit, 1, 1)
        self.__dirEdit.textChanged.connect(self.__workingDirChanged)

        self.__dirSelectButton = QPushButton("...", workDirGroupbox)
        gridLayoutWD.addWidget(self.__dirSelectButton, 1, 2)
        self.__dirSelectButton.clicked.connect(self.__selectDirClicked)
        return workDirGroupbox

    def __getEnvGroupbox(self):
        """Provides the environment groupbox"""
        envGroupbox = QGroupBox('Environment', self)
        envGroupbox.setSizePolicy(self.__getSizePolicy(envGroupbox))

        layoutEnv = QVBoxLayout(envGroupbox)
        self.__inheritParentRButton = QRadioButton("Inherit &parent",
                                                   envGroupbox)
        self.__inheritParentRButton.clicked.connect(self.__inhClicked)
        layoutEnv.addWidget(self.__inheritParentRButton)

        self.__inheritParentPlusRButton = QRadioButton(
            "Inherit parent and add/&modify", envGroupbox)
        self.__inheritParentPlusRButton.clicked.connect(self.__inhPlusClicked)
        layoutEnv.addWidget(self.__inheritParentPlusRButton)
        hInhPlusLayout = QHBoxLayout()
        self.__inhPlusEnvTable = QTreeWidget()
        self.__inhPlusEnvTable.itemActivated.connect(
            lambda x, y: self.__editInhClicked())
        self.__tuneTable(self.__inhPlusEnvTable)
        hInhPlusLayout.addWidget(self.__inhPlusEnvTable)
        vInhPlusLayout = QVBoxLayout()
        self.__addInhButton = QPushButton('Add')
        self.__addInhButton.clicked.connect(self.__addInhClicked)
        vInhPlusLayout.addWidget(self.__addInhButton)
        self.__delInhButton = QPushButton('Delete')
        self.__delInhButton.clicked.connect(self.__delInhClicked)
        vInhPlusLayout.addWidget(self.__delInhButton)
        self.__editInhButton = QPushButton("Edit")
        self.__editInhButton.clicked.connect(self.__editInhClicked)
        vInhPlusLayout.addWidget(self.__editInhButton)
        hInhPlusLayout.addLayout(vInhPlusLayout)
        layoutEnv.addLayout(hInhPlusLayout)

        self.__specificRButton = QRadioButton("&Specific", envGroupbox)
        self.__specificRButton.clicked.connect(self.__specClicked)
        layoutEnv.addWidget(self.__specificRButton)
        hSpecLayout = QHBoxLayout()
        self.__specEnvTable = QTreeWidget()
        self.__specEnvTable.itemActivated.connect(
            lambda x, y: self.__editSpecClicked())
        self.__tuneTable(self.__specEnvTable)
        hSpecLayout.addWidget(self.__specEnvTable)
        vSpecLayout = QVBoxLayout()
        self.__addSpecButton = QPushButton('Add')
        self.__addSpecButton.clicked.connect(self.__addSpecClicked)
        vSpecLayout.addWidget(self.__addSpecButton)
        self.__delSpecButton = QPushButton('Delete')
        self.__delSpecButton.clicked.connect(self.__delSpecClicked)
        vSpecLayout.addWidget(self.__delSpecButton)
        self.__editSpecButton = QPushButton("Edit")
        self.__editSpecButton.clicked.connect(self.__editSpecClicked)
        vSpecLayout.addWidget(self.__editSpecButton)
        hSpecLayout.addLayout(vSpecLayout)
        layoutEnv.addLayout(hSpecLayout)
        return envGroupbox

    def __getInterpreterGroupbox(self):
        """Creates the interpreter groupbox"""
        interpreterGroupbox = QGroupBox('Python Interpreter', self)
        interpreterGroupbox.setSizePolicy(
            self.__getSizePolicy(interpreterGroupbox))

        gridLayoutInt = QGridLayout(interpreterGroupbox)
        self.__inheritedInterpreterRButton = QRadioButton(
            "&Inherited", interpreterGroupbox)
        gridLayoutInt.addWidget(self.__inheritedInterpreterRButton, 0, 0)
        self.__inheritedInterpreterRButton.clicked.connect(
            lambda: self.__interpreter(True))

        self.__customIntRButton = QRadioButton(
            "Select interpreter (series &3)", interpreterGroupbox)
        gridLayoutInt.addWidget(self.__customIntRButton, 1, 0)
        self.__customIntRButton.clicked.connect(
            lambda: self.__interpreter(False))

        self.__intEdit = QLineEdit(interpreterGroupbox)
        gridLayoutInt.addWidget(self.__intEdit, 1, 1)
        self.__intEdit.textChanged.connect(self.__interpreterChanged)

        self.__intSelectButton = QPushButton("...", interpreterGroupbox)
        gridLayoutInt.addWidget(self.__intSelectButton, 1, 2)
        self.__intSelectButton.clicked.connect(self.__selectIntClicked)
        return interpreterGroupbox

    def __getIOGroupbox(self):
        """Creates the interpreter groupbox"""
        ioGroupbox = QGroupBox('Input/output', self)
        ioGroupbox.setSizePolicy(self.__getSizePolicy(ioGroupbox))

        gridLayoutInt = QGridLayout(ioGroupbox)
        self.__redirectedRButton = QRadioButton("&Redirected I/O", ioGroupbox)
        gridLayoutInt.addWidget(self.__redirectedRButton, 0, 0)
        self.__redirectedRButton.clicked.connect(
            lambda: self.__redirected(True))

        self.__customTermRButton = QRadioButton("Custom terminal string",
                                                ioGroupbox)
        gridLayoutInt.addWidget(self.__customTermRButton, 1, 0)
        self.__customTermRButton.clicked.connect(
            lambda: self.__redirected(False))

        self.__termEdit = QLineEdit(ioGroupbox)
        gridLayoutInt.addWidget(self.__termEdit, 1, 1)
        self.__termEdit.textChanged.connect(self.__customTermChanged)
        return ioGroupbox

    def __getProfileLimitsGroupbox(self):
        """Creates the profile limits groupbox"""
        limitsGroupbox = QGroupBox('Profiler diagram limits (IDE wide)', self)
        limitsGroupbox.setSizePolicy(self.__getSizePolicy(limitsGroupbox))

        layoutLimits = QGridLayout(limitsGroupbox)
        self.__nodeLimitEdit = QLineEdit()
        self.__nodeLimitEdit.textEdited.connect(self.__setRunButtonProps)
        self.__nodeLimitValidator = QDoubleValidator(0.0, 100.0, 2, self)
        self.__nodeLimitValidator.setNotation(
            QDoubleValidator.StandardNotation)
        self.__nodeLimitEdit.setValidator(self.__nodeLimitValidator)
        nodeLimitLabel = QLabel("Hide nodes below")
        self.__edgeLimitEdit = QLineEdit()
        self.__edgeLimitEdit.textEdited.connect(self.__setRunButtonProps)
        self.__edgeLimitValidator = QDoubleValidator(0.0, 100.0, 2, self)
        self.__edgeLimitValidator.setNotation(
            QDoubleValidator.StandardNotation)
        self.__edgeLimitEdit.setValidator(self.__edgeLimitValidator)
        edgeLimitLabel = QLabel("Hide edges below")
        layoutLimits.addWidget(nodeLimitLabel, 0, 0)
        layoutLimits.addWidget(self.__nodeLimitEdit, 0, 1)
        layoutLimits.addWidget(QLabel("%"), 0, 2)
        layoutLimits.addWidget(edgeLimitLabel, 1, 0)
        layoutLimits.addWidget(self.__edgeLimitEdit, 1, 1)
        layoutLimits.addWidget(QLabel("%"), 1, 2)
        return limitsGroupbox

    def __getDebugGroupbox(self):
        """Creates the debug settings groupbox"""
        dbgGroupbox = QGroupBox('Debugger (IDE wide)', self)
        dbgGroupbox.setSizePolicy(self.__getSizePolicy(dbgGroupbox))

        dbgLayout = QVBoxLayout(dbgGroupbox)
        self.__reportExceptionCheckBox = QCheckBox("Report &exceptions")
        self.__reportExceptionCheckBox.stateChanged.connect(
            self.__onReportExceptionChanged)
        self.__traceInterpreterCheckBox = QCheckBox("T&race interpreter libs")
        self.__traceInterpreterCheckBox.stateChanged.connect(
            self.__onTraceInterpreterChanged)
        self.__stopAtFirstCheckBox = QCheckBox("Stop at first &line")
        self.__stopAtFirstCheckBox.stateChanged.connect(
            self.__onStopAtFirstChanged)
        self.__autoforkCheckBox = QCheckBox("&Fork without asking")
        self.__autoforkCheckBox.stateChanged.connect(self.__onAutoforkChanged)
        self.__debugChildCheckBox = QCheckBox("Debu&g child process")
        self.__debugChildCheckBox.stateChanged.connect(self.__onDebugChild)

        dbgLayout.addWidget(self.__reportExceptionCheckBox)
        dbgLayout.addWidget(self.__traceInterpreterCheckBox)
        dbgLayout.addWidget(self.__stopAtFirstCheckBox)
        dbgLayout.addWidget(self.__autoforkCheckBox)
        dbgLayout.addWidget(self.__debugChildCheckBox)
        return dbgGroupbox

    @staticmethod
    def __tuneTable(table):
        """Sets the common settings for a table"""
        table.setAlternatingRowColors(True)
        table.setRootIsDecorated(False)
        table.setItemsExpandable(False)
        table.setUniformRowHeights(True)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setItemDelegate(NoOutlineHeightDelegate(4))
        table.setHeaderLabels(["Variable", "Value"])

        header = table.header()
        header.setSortIndicator(0, Qt.AscendingOrder)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        table.setSortingEnabled(True)

    def __wdDir(self, useScriptLocation):
        """Working dir radio selection changed"""
        self.__dirEdit.setEnabled(not useScriptLocation)
        self.__dirSelectButton.setEnabled(not useScriptLocation)
        self.runParams['useScriptLocation'] = useScriptLocation
        self.__setRunButtonProps()

    def __interpreter(self, useInherited):
        """Interpreter radio selection changed"""
        self.__intEdit.setEnabled(not useInherited)
        self.__intSelectButton.setEnabled(not useInherited)
        self.runParams['useInherited'] = useInherited
        self.__setRunButtonProps()

    def __redirected(self, redirected):
        """I/O radio button changed"""
        self.__termEdit.setEnabled(not redirected)
        self.runParams['redirected'] = redirected
        self.__setRunButtonProps()

    def __customTermChanged(self, value):
        """Triggered when a custom terminal string changed"""
        value = str(value).strip()
        self.runParams['customTerminal'] = value
        self.__setRunButtonProps()

    def __argsChanged(self, value):
        """Triggered when cmd line args are changed"""
        value = str(value).strip()
        self.runParams['arguments'] = value
        self.__setRunButtonProps()

    def __workingDirChanged(self, value):
        """Triggered when a working dir value is changed"""
        value = str(value)
        self.runParams['specificDir'] = value
        self.__setRunButtonProps()

    def __interpreterChanged(self, value):
        """Triggered when an interpreter is changed"""
        value = str(value).strip()
        self.runParams['customInterpreter'] = value
        self.__setRunButtonProps()

    def __onCloseChanged(self, state):
        """Triggered when the close terminal check box changed"""
        self.runParams['closeTerminal'] = state != 0

    def __onReportExceptionChanged(self, state):
        """Triggered when exception report check box changed"""
        self.debuggerParams.reportExceptions = state != 0

    def __onTraceInterpreterChanged(self, state):
        """Triggered when trace interpreter changed"""
        self.debuggerParams.traceInterpreter = state != 0

    def __onStopAtFirstChanged(self, state):
        """Triggered when stop at first changed"""
        self.debuggerParams.stopAtFirstLine = state != 0

    def __onAutoforkChanged(self, state):
        """Triggered when autofork changed"""
        self.debuggerParams.autofork = state != 0
        self.__debugChildCheckBox.setEnabled(self.debuggerParams.autofork)

    def __onDebugChild(self, state):
        """Triggered when debug child changed"""
        self.debuggerParams.followChild = state != 0

    def __argumentsOK(self):
        """Returns True if the arguments are OK"""
        try:
            parseCommandLineArguments(self.runParams['arguments'])
            return True
        except:
            return False

    def __dirOK(self):
        """Returns True if the working dir is OK"""
        if self.__scriptWDRButton.isChecked():
            return True
        return os.path.isdir(self.__dirEdit.text())

    def __interpreterOK(self):
        """Checks if the interpreter is OK"""
        if self.__inheritedInterpreterRButton.isChecked():
            return True
        path = self.__intEdit.text().strip()
        if not path:
            return 'No executable specified'
        try:
            code = "from __future__ import print_function; " \
                "import sys; print(sys.version_info.major)"
            output = checkOutput(path + ' -c "' + code + '"', useShell=True)
            output = output.strip()
            if output != '3':
                return 'Only python series 3 is supported ' \
                    '(provided: series ' + output + ')'
        except:
            return 'Error checking the provided interpreter'

    def __ioOK(self):
        """Checks if the IO is correct"""
        if self.__redirectedRButton.isChecked():
            return True

        term = self.__termEdit.text().strip()
        if not term:
            return 'No custom terminal line specified'

    def __setRunButtonProps(self, _=None):
        """Enable/disable run button and set its tooltip"""
        if not self.__argumentsOK():
            self.__runButton.setEnabled(False)
            self.__runButton.setToolTip("No closing quotation in arguments")
            return

        if not self.__dirOK():
            self.__runButton.setEnabled(False)
            self.__runButton.setToolTip("The given working "
                                        "dir is not found")
            return

        interpreterOK = self.__interpreterOK()
        if isinstance(interpreterOK, str):
            self.__runButton.setEnabled(False)
            self.__runButton.setToolTip('Invalid interpreter. ' +
                                        interpreterOK)
            return

        ioOK = self.__ioOK()
        if isinstance(ioOK, str):
            self.__runButton.setEnabled(False)
            self.__runButton.setToolTip('Invalid terminal. ' + ioOK)
            return

        if self.__nodeLimitEdit is not None:
            txt = self.__nodeLimitEdit.text().strip()
            try:
                value = float(txt)
                if value < 0.0 or value > 100.0:
                    raise Exception("Out of range")
            except:
                self.__runButton.setEnabled(False)
                self.__runButton.setToolTip("The given node limit "
                                            "is out of range")
                return

        if self.__edgeLimitEdit is not None:
            txt = self.__edgeLimitEdit.text().strip()
            try:
                value = float(txt)
                if value < 0.0 or value > 100.0:
                    raise Exception("Out of range")
            except:
                self.__runButton.setEnabled(False)
                self.__runButton.setToolTip("The given edge limit "
                                            "is out of range")
                return

        self.__runButton.setEnabled(True)
        self.__runButton.setToolTip(
            "Save parameters and " +
            RunDialog.ACTION_TO_VERB[self.__action].lower() + " script")

    def __selectDirClicked(self):
        """Selects the script working dir"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly
        dirName = QFileDialog.getExistingDirectory(
            self, "Select the script working directory",
            self.__dirEdit.text(), options=options)

        if dirName:
            self.__dirEdit.setText(os.path.normpath(dirName))

    def __selectIntClicked(self):
        """Selects a python interpreter"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select python series 3 interpreter",
            options=options)

        if path:
            self.__intEdit.setText(os.path.normpath(path))
        self.__setRunButtonProps()

    def __inhClicked(self):
        """Inerit parent env radio button clicked"""
        self.__setEnabledInheritedPlusEnv(False)
        self.__setEnabledSpecificEnv(False)
        self.runParams['envType'] = RunParameters.InheritParentEnv

    def __inhPlusClicked(self):
        """Inherit parent and add radio button clicked"""
        self.__setEnabledInheritedPlusEnv(True)
        self.__setEnabledSpecificEnv(False)
        self.runParams['envType'] = RunParameters.InheritParentEnvPlus

        if self.__inhPlusEnvTable.selectedIndexes():
            self.__delInhButton.setEnabled(True)
            self.__editInhButton.setEnabled(True)
        else:
            self.__delInhButton.setEnabled(False)
            self.__editInhButton.setEnabled(False)

    def __specClicked(self):
        """Specific env radio button clicked"""
        self.__setEnabledInheritedPlusEnv(False)
        self.__setEnabledSpecificEnv(True)
        self.runParams['envType'] = RunParameters.SpecificEnvironment

        if self.__specEnvTable.selectedIndexes():
            self.__delSpecButton.setEnabled(True)
            self.__editSpecButton.setEnabled(True)
        else:
            self.__delSpecButton.setEnabled(False)
            self.__editSpecButton.setEnabled(False)

    @staticmethod
    def __delAndInsert(table, name, value):
        """Deletes an item by name if so; insert new; highlight it"""
        for index in range(table.topLevelItemCount()):
            item = table.topLevelItem(index)
            if str(item.text(0)) == name:
                table.takeTopLevelItem(index)
                break

        item = QTreeWidgetItem([name, value])
        table.addTopLevelItem(item)
        table.setCurrentItem(item)
        return item

    def __addInhClicked(self):
        """Add env var button clicked"""
        dlg = EnvVarDialog()
        if dlg.exec_() == QDialog.Accepted:
            name = str(dlg.name)
            value = str(dlg.value)
            self.__delAndInsert(self.__inhPlusEnvTable, name, value)
            self.runParams['additionToParentEnv'][name] = value
            self.__delInhButton.setEnabled(True)
            self.__editInhButton.setEnabled(True)

    def __addSpecClicked(self):
        """Add env var button clicked"""
        dlg = EnvVarDialog()
        if dlg.exec_() == QDialog.Accepted:
            name = str(dlg.name)
            value = str(dlg.value)
            self.__delAndInsert(self.__specEnvTable, name, value)
            self.runParams['specificEnv'][name] = value
            self.__delSpecButton.setEnabled(True)
            self.__editSpecButton.setEnabled(True)

    def __delInhClicked(self):
        """Delete the highlighted variable"""
        if self.__inhPlusEnvTable.topLevelItemCount() == 0:
            return

        name = self.__inhPlusEnvTable.currentItem().text(0)
        for index in range(self.__inhPlusEnvTable.topLevelItemCount()):
            item = self.__inhPlusEnvTable.topLevelItem(index)
            if name == item.text(0):
                self.__inhPlusEnvTable.takeTopLevelItem(index)
                break

        del self.runParams['additionToParentEnv'][str(name)]
        if self.__inhPlusEnvTable.topLevelItemCount() == 0:
            self.__delInhButton.setEnabled(False)
            self.__editInhButton.setEnabled(False)
        else:
            self.__inhPlusEnvTable.setCurrentItem(
                self.__inhPlusEnvTable.topLevelItem(0))

    def __delSpecClicked(self):
        """Delete the highlighted variable"""
        if self.__specEnvTable.topLevelItemCount() == 0:
            return

        name = self.__specEnvTable.currentItem().text(0)
        for index in range(self.__specEnvTable.topLevelItemCount()):
            item = self.__specEnvTable.topLevelItem(index)
            if name == item.text(0):
                self.__specEnvTable.takeTopLevelItem(index)
                break

        del self.runParams['specificEnv'][str(name)]
        if self.__specEnvTable.topLevelItemCount() == 0:
            self.__delSpecButton.setEnabled(False)
            self.__editSpecButton.setEnabled(False)
        else:
            self.__specEnvTable.setCurrentItem(
                self.__specEnvTable.topLevelItem(0))

    def __editInhClicked(self):
        """Edits the highlighted variable"""
        if self.__inhPlusEnvTable.topLevelItemCount() == 0:
            return

        item = self.__inhPlusEnvTable.currentItem()
        dlg = EnvVarDialog(str(item.text(0)), str(item.text(1)), self)
        if dlg.exec_() == QDialog.Accepted:
            name = str(dlg.name)
            value = str(dlg.value)
            self.__delAndInsert(self.__inhPlusEnvTable, name, value)
            self.runParams['additionToParentEnv'][name] = value

    def __editSpecClicked(self):
        """Edits the highlighted variable"""
        if self.__specEnvTable.topLevelItemCount() == 0:
            return

        item = self.__specEnvTable.currentItem()
        dlg = EnvVarDialog(str(item.text(0)), str(item.text(1)), self)
        if dlg.exec_() == QDialog.Accepted:
            name = str(dlg.name)
            value = str(dlg.value)
            self.__delAndInsert(self.__specEnvTable, name, value)
            self.runParams['specificEnv'][name] = value

    def onAccept(self):
        """Saves the selected terminal and profiling values"""
        if self.__action == PROFILE:
            self.profilerParams.nodeLimit = float(
                self.__nodeLimitEdit.text())
            self.profilerParams.edgeLimit = float(
                self.__edgeLimitEdit.text())

        self.accept()
