# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Control flow UI widget"""

import os.path
import logging
import uuid
from math import ceil
from timeit import default_timer as timer
from ui.qt import (Qt, QSize, QTimer, QDir, QUrl, QSizeF, QPainter, QImage,
                   QToolBar, QWidget, QPrinter, QApplication, QHBoxLayout,
                   QLabel, QVBoxLayout, QFileDialog, QActionGroup, QAction,
                   QDialog, QMenu, QToolButton, QMessageBox, QSvgGenerator,
                   QStackedWidget)
from ui.spacers import ToolBarExpandingSpacer, ToolBarVSpacer
from cdmcfparser import getControlFlowFromMemory
from flowui.vcanvas import VirtualCanvas, formatFlow
from diagram.depsvcanvas import DepsVirtualCanvas
from flowui.cflowsettings import getCflowSettings
from flowui.cml import CMLVersion
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.fileutils import isPythonMime
from utils.settings import Settings
from utils.diskvaluesrelay import (getFilePosition, getCollapsedGroups,
                                   setCollapsedGroups)
from diagram.depsdiagram import collectImportResolutions
from .flowuinavbar import ControlFlowNavigationBar
from .flowuisceneview import CFGraphicsView
from .depssceneview import DepsGraphicsView
from .astview import ASTView
from .disasmview import DisassemblyView
from .binview import BinView


IDLE_TIMEOUT = 1500


SMART_ZOOM_BIN = -3         # Shows the pyc binary
SMART_ZOOM_DISASM = -2      # Show the code disassembly
SMART_ZOOM_AST = -1         # Show the code AST
SMART_ZOOM_ALL = 0          # Show everything
SMART_ZOOM_NO_CONTENT = 1   # All the boxes are without a content
SMART_ZOOM_CONTROL_ONLY = 2 # Only scopes and ifs
SMART_ZOOM_CLASS_FUNC = 3   # Only classes and functions
SMART_ZOOM_FS = 4           # File system dependencies view

SMART_ZOOM_MIN = SMART_ZOOM_BIN
SMART_ZOOM_MAX = SMART_ZOOM_FS

# TODO: Till FS zoom is implemented
SMART_ZOOM_MAX = SMART_ZOOM_CLASS_FUNC


class SmartZoomStaticProps:

    """Zoom level properties"""

    def __init__(self, label, description, viewIndex,
                 isControlFlow, selectionAvailable):
        self.label = label
        self.description = description
        self.viewIndex = viewIndex
        self.isControlFlow = isControlFlow
        self.selectionAvailable = selectionAvailable


# Number: [label, description, view index, is a control flow]
# The dictionary must be in sync with FlowUIWidget::__createStackedViews() in
# terms of the view indexes
ZOOM_PROPS = {
    SMART_ZOOM_BIN:
        SmartZoomStaticProps('B', 'pyc binary', 4, False, False),
    SMART_ZOOM_DISASM:
        SmartZoomStaticProps('D', 'disassembly', 3, False, False),
    SMART_ZOOM_AST: SmartZoomStaticProps('A', 'AST', 2, False, True),
    SMART_ZOOM_ALL:
        SmartZoomStaticProps('0', 'everything is shown', 0, True, True),
    SMART_ZOOM_NO_CONTENT:
        SmartZoomStaticProps('1', 'everything without a content', 0, True, True),
    SMART_ZOOM_CONTROL_ONLY:
        SmartZoomStaticProps('2', 'scopes and ifs', 0, True, True),
    SMART_ZOOM_CLASS_FUNC:
        SmartZoomStaticProps('3', 'only classes and functions', 0, True, True),
    SMART_ZOOM_FS:
        SmartZoomStaticProps('4', 'dependencies', 1, False, True)
}


class SmartZoomDynamicProps:

    """Displaying properties of a certain zoom"""

    def __init__(self, viewIndexes):
        if isinstance(viewIndexes, list):
            self.viewIndexes = viewIndexes
        else:
            self.viewIndexes = [viewIndexes]

        self.navBarState = {'path': '',
                            'state': ControlFlowNavigationBar.STATE_UNKNOWN,
                            'warningsvisible': False,
                            'warnings': '',
                            'icontooltip': 'View state is unknown',
                            'selectiontext': '',
                            'selectiontooltip': ''}
        self.dirty = True


def getSmartZoomDescription(smartZoomLevel):
    """Provides a tooltip for the smart zoom level"""
    prefix = 'Smart zoom level: '
    try:
        return prefix + ZOOM_PROPS[smartZoomLevel].description
    except:
        return 'Unknown smart zoom level'

def getSelectionAvailable(viewIndex):
    for key in ZOOM_PROPS.keys():
        if ZOOM_PROPS[key].viewIndex == viewIndex:
            return ZOOM_PROPS[key].selectionAvailable
    return False

def isControlFlowView(viewIndex):
    for key in ZOOM_PROPS.keys():
        if ZOOM_PROPS[key].viewIndex == viewIndex:
            return ZOOM_PROPS[key].isControlFlow
    return False

def isControlFlowLevel(smartZoom):
    return smartZoom in [SMART_ZOOM_ALL, SMART_ZOOM_NO_CONTENT,
                         SMART_ZOOM_CONTROL_ONLY, SMART_ZOOM_CLASS_FUNC]


def tweakSmartSettings(cflowSettings, smartZoom):
    """Tweaks settings in accordance to the smart level"""
    # Default is to show everything
    if smartZoom == SMART_ZOOM_ALL:
        return cflowSettings
    if smartZoom == SMART_ZOOM_NO_CONTENT:
        cflowSettings.noContent = True
        cflowSettings.noComment = True
        cflowSettings.noDocstring = True
        cflowSettings.minWidth = ceil(float(cflowSettings.minWidth) * 0.66)
        return cflowSettings
    if smartZoom == SMART_ZOOM_CONTROL_ONLY:
        cflowSettings.noContent = True
        cflowSettings.noComment = True
        cflowSettings.noDocstring = True
        cflowSettings.noBlock = True
        cflowSettings.noImport = True
        cflowSettings.noContinue = True
        cflowSettings.noBreak = True
        cflowSettings.noReturn = True
        cflowSettings.noRaise = True
        cflowSettings.noAssert = True
        cflowSettings.noSysExit = True
        cflowSettings.noDecor = True
        cflowSettings.noGroup = True
        cflowSettings.minWidth = ceil(float(cflowSettings.minWidth) * 0.66)
        return cflowSettings
    if smartZoom == SMART_ZOOM_CLASS_FUNC:
        cflowSettings.noContent = True
        cflowSettings.noComment = True
        cflowSettings.noDocstring = True
        cflowSettings.noBlock = True
        cflowSettings.noImport = True
        cflowSettings.noContinue = True
        cflowSettings.noBreak = True
        cflowSettings.noReturn = True
        cflowSettings.noRaise = True
        cflowSettings.noAssert = True
        cflowSettings.noSysExit = True
        cflowSettings.noDecor = True
        cflowSettings.noFor = True
        cflowSettings.noWhile = True
        cflowSettings.noWith = True
        cflowSettings.noTry = True
        cflowSettings.noIf = True
        cflowSettings.noGroup = True
        cflowSettings.minWidth = ceil(float(cflowSettings.minWidth) * 0.66)
        return cflowSettings
    return cflowSettings


class FlowUIWidget(QWidget):

    """The widget which goes along with the text editor"""

    def __init__(self, editor, parent):
        QWidget.__init__(self, parent)

        # It is always not visible at the beginning because there is no
        # editor content at the start
        self.setVisible(False)

        self.__editor = editor
        self.__parentWidget = parent
        self.__connected = False
        self.__needPathUpdate = False
        self.__scrollRestored = False

        self.cflowSettings = getCflowSettings(self)
        self.__displayProps = (self.cflowSettings.hidedocstrings,
                               self.cflowSettings.hidecomments,
                               self.cflowSettings.hideexcepts,
                               self.cflowSettings.hidedecors,
                               Settings()['smartZoom'])
        self.__disasmLevel = Settings()['disasmLevel']
        self.__binLevel = Settings()['disasmLevel']

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)

        # Make pylint happy
        self.__toolbar = None
        self.__navBar = None
        self.__cf = None
        self.__canvas = None
        self.__validGroups = []
        self.__allGroupId = set()

        # Create the update timer
        self.__updateTimer = QTimer(self)
        self.__updateTimer.setSingleShot(True)
        self.__updateTimer.timeout.connect(self.process)

        vLayout.addWidget(self.__createNavigationBar())
        vLayout.addWidget(self.__createStackedViews())

        hLayout.addLayout(vLayout)
        hLayout.addWidget(self.__createToolbar())
        self.setLayout(hLayout)

        self.updateSettings()

        self.__dynamicProps = [
            SmartZoomDynamicProps(
                ZOOM_PROPS[SMART_ZOOM_BIN].viewIndex),
            SmartZoomDynamicProps(
                ZOOM_PROPS[SMART_ZOOM_DISASM].viewIndex),
            SmartZoomDynamicProps(
                ZOOM_PROPS[SMART_ZOOM_AST].viewIndex),
            SmartZoomDynamicProps(
                [ZOOM_PROPS[SMART_ZOOM_ALL].viewIndex,
                 ZOOM_PROPS[SMART_ZOOM_NO_CONTENT].viewIndex,
                 ZOOM_PROPS[SMART_ZOOM_CONTROL_ONLY].viewIndex,
                 ZOOM_PROPS[SMART_ZOOM_CLASS_FUNC].viewIndex]),
            SmartZoomDynamicProps(
                ZOOM_PROPS[SMART_ZOOM_FS].viewIndex)]

        # Connect to the change file type signal
        self.__mainWindow = GlobalData().mainWindow
        editorsManager = self.__mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)

        Settings().sigHideDocstringsChanged.connect(
            self.__onHideDocstringsChanged)
        Settings().sigHideCommentsChanged.connect(self.__onHideCommentsChanged)
        Settings().sigHideExceptsChanged.connect(self.__onHideExceptsChanged)
        Settings().sigHideDecorsChanged.connect(self.__onHideDecorsChanged)
        Settings().sigSmartZoomChanged.connect(self.__onSmartZoomChanged)
        Settings().sigDisasmLevelChanged.connect(self.__onDisasmLevelChanged)

        self.__restoreNavBarProps()
        self.setSmartZoomLevel(Settings()['smartZoom'])

    def __saveNavBarProps(self):
        """Saves the current view props in the dynamic props"""
        currentIndex = self.smartViews.currentIndex()
        for item in self.__dynamicProps:
            if currentIndex in item.viewIndexes:
                item.navBarState = self.__navBar.serialize()
                return

    def __restoreNavBarProps(self):
        """Restores the current view props from the dynamic props"""
        currentIndex = self.smartViews.currentIndex()
        for item in self.__dynamicProps:
            if currentIndex in item.viewIndexes:
                # dirty hack: initial selection values
                if not getSelectionAvailable(currentIndex):
                    item.navBarState['selectiontext'] = 'n/a'
                    item.navBarState['selectiontooltip'] = 'Number of selected items'
                else:
                    if not item.navBarState['selectiontext']:
                        item.navBarState['selectiontext'] = '0'
                        item.navBarState['selectiontooltip'] = 'Number of selected items'
                self.__navBar.deserialize(item.navBarState)
                return

    def __markViewsDirty(self):
        """Marks all the views dirty"""
        for item in self.__dynamicProps:
            item.dirty = True

    def __markViewClean(self):
        currentIndex = self.smartViews.currentIndex()
        for item in self.__dynamicProps:
            if currentIndex in item.viewIndexes:
                item.dirty = False

    def __isCurrentViewDirty(self):
        currentIndex = self.smartViews.currentIndex()
        for item in self.__dynamicProps:
            if currentIndex in item.viewIndexes:
                return item.dirty

    def getParentWidget(self):
        return self.__parentWidget

    def view(self):
        """Provides a reference to the current view"""
        return self.smartViews.currentWidget()

    def scene(self):
        """Provides a reference to the current scene"""
        return self.view().scene

    def __createToolbar(self):
        """Creates the toolbar"""
        self.__toolbar = QToolBar(self)
        self.__toolbar.setOrientation(Qt.Vertical)
        self.__toolbar.setMovable(False)
        self.__toolbar.setAllowedAreas(Qt.RightToolBarArea)
        self.__toolbar.setIconSize(QSize(16, 16))
        self.__toolbar.setFixedWidth(30)
        self.__toolbar.setContentsMargins(0, 0, 0, 0)

        # Buttons
        saveAsMenu = QMenu(self)
        saveAsSVGAct = saveAsMenu.addAction(getIcon('filesvg.png'),
                                            'Save as SVG...')
        saveAsSVGAct.triggered.connect(self.onSaveAsSVG)

        saveAsPDFAct = saveAsMenu.addAction(getIcon('filepdf.png'),
                                            'Save as PDF...')
        saveAsPDFAct.triggered.connect(self.onSaveAsPDF)
        saveAsPNGAct = saveAsMenu.addAction(getIcon('filepixmap.png'),
                                            'Save as PNG...')
        saveAsPNGAct.triggered.connect(self.onSaveAsPNG)
        saveAsMenu.addSeparator()
        saveAsCopyToClipboardAct = saveAsMenu.addAction(
            getIcon('copymenu.png'), 'Copy to clipboard')
        saveAsCopyToClipboardAct.triggered.connect(self.copyToClipboard)

        self.__saveAsButton = QToolButton(self.__toolbar)
        self.__saveAsButton.setIcon(getIcon('saveasmenu.png'))
        self.__saveAsButton.setToolTip('Save as')
        self.__saveAsButton.setPopupMode(QToolButton.InstantPopup)
        self.__saveAsButton.setMenu(saveAsMenu)
        self.__saveAsButton.setFocusPolicy(Qt.NoFocus)

        self.__levelUpButton = QToolButton(self.__toolbar)
        self.__levelUpButton.setFocusPolicy(Qt.NoFocus)
        self.__levelUpButton.setIcon(getIcon('levelup.png'))
        self.__levelUpButton.setToolTip('Smart zoom level up (Shift+wheel)')
        self.__levelUpButton.clicked.connect(self.onSmartZoomLevelUp)
        self.__levelIndicator = QLabel('<b>0</b>', self.__toolbar)
        self.__levelIndicator.setAlignment(Qt.AlignCenter)
        self.__levelIndicator.setStyleSheet('QLabel {background: transparent}')
        self.__levelDownButton = QToolButton(self.__toolbar)
        self.__levelDownButton.setFocusPolicy(Qt.NoFocus)
        self.__levelDownButton.setIcon(getIcon('leveldown.png'))
        self.__levelDownButton.setToolTip('Smart zoom level down (Shift+wheel)')
        self.__levelDownButton.clicked.connect(self.onSmartZoomLevelDown)

        self.__hideDocstrings = QToolButton(self.__toolbar)
        self.__hideDocstrings.setCheckable(True)
        self.__hideDocstrings.setIcon(getIcon('hidedocstrings.png'))
        self.__hideDocstrings.setToolTip('Show/hide docstrings')
        self.__hideDocstrings.setFocusPolicy(Qt.NoFocus)
        self.__hideDocstrings.setChecked(Settings()['hidedocstrings'])
        self.__hideDocstrings.clicked.connect(self.__onHideDocstrings)
        self.__hideComments = QToolButton(self.__toolbar)
        self.__hideComments.setCheckable(True)
        self.__hideComments.setIcon(getIcon('hidecomments.png'))
        self.__hideComments.setToolTip('Show/hide comments')
        self.__hideComments.setFocusPolicy(Qt.NoFocus)
        self.__hideComments.setChecked(Settings()['hidecomments'])
        self.__hideComments.clicked.connect(self.__onHideComments)
        self.__hideExcepts = QToolButton(self.__toolbar)
        self.__hideExcepts.setCheckable(True)
        self.__hideExcepts.setIcon(getIcon('hideexcepts.png'))
        self.__hideExcepts.setToolTip('Show/hide except blocks')
        self.__hideExcepts.setFocusPolicy(Qt.NoFocus)
        self.__hideExcepts.setChecked(Settings()['hideexcepts'])
        self.__hideExcepts.clicked.connect(self.__onHideExcepts)
        self.__hideDecors = QToolButton(self.__toolbar)
        self.__hideDecors.setCheckable(True)
        self.__hideDecors.setIcon(getIcon('hidedecors.png'))
        self.__hideDecors.setToolTip('Show/hide decorators')
        self.__hideDecors.setFocusPolicy(Qt.NoFocus)
        self.__hideDecors.setChecked(Settings()['hidedecors'])
        self.__hideDecors.clicked.connect(self.__onHideDecors)

        # Optimization buttons for disasm view
        self.__optActGroup = QActionGroup(self.__toolbar)
        self.__noOpt = QAction('0', self.__optActGroup)
        f = self.__noOpt.font()
        f.setBold(True)
        self.__noOpt.setFont(f)
        self.__noOpt.setCheckable(True)
        self.__noOpt.setToolTip('No optimization (level 0)')
        self.__noOpt.setChecked(Settings()['disasmLevel'] == 0)
        self.__noOpt.triggered.connect(self.__onOpt0)

        self.__assertOpt = QAction('1', self.__optActGroup)
        f = self.__assertOpt.font()
        f.setBold(True)
        self.__assertOpt.setFont(f)
        self.__assertOpt.setCheckable(True)
        self.__assertOpt.setToolTip('Assert optimization (level 1)')
        self.__assertOpt.setChecked(Settings()['disasmLevel'] == 1)
        self.__assertOpt.triggered.connect(self.__onOpt1)

        self.__docOpt = QAction('2', self.__optActGroup)
        f = self.__docOpt.font()
        f.setBold(True)
        self.__docOpt.setFont(f)
        self.__docOpt.setCheckable(True)
        self.__docOpt.setToolTip('Assert + docstring optimization (level 2)')
        self.__docOpt.setChecked(Settings()['disasmLevel'] == 2)
        self.__docOpt.triggered.connect(self.__onOpt2)

        self.__saveAsAction = self.__toolbar.addWidget(self.__saveAsButton)
        self.__toolbar.addWidget(ToolBarExpandingSpacer(self.__toolbar))
        self.__hideDocAction = self.__toolbar.addWidget(self.__hideDocstrings)
        self.__hideComAction = self.__toolbar.addWidget(self.__hideComments)
        self.__hideExcptAction = self.__toolbar.addWidget(self.__hideExcepts)
        self.__hideDecorActions = self.__toolbar.addWidget(self.__hideDecors)
        self.__toolbar.addAction(self.__noOpt)
        self.__toolbar.addAction(self.__assertOpt)
        self.__toolbar.addAction(self.__docOpt)
        self.__toolbar.addWidget(ToolBarVSpacer(self.__toolbar, 10))
        self.__toolbar.addWidget(self.__levelUpButton)
        self.__toolbar.addWidget(self.__levelIndicator)
        self.__toolbar.addWidget(self.__levelDownButton)

        return self.__toolbar

    def __setToolbarStatus(self, smartZoomLevel):
        """Enable/disable the toolbar buttons"""
        isControlFlow = ZOOM_PROPS[smartZoomLevel].isControlFlow

        # Buttons
        self.__saveAsAction.setVisible(isControlFlow)

        self.__hideDocAction.setVisible(isControlFlow)
        self.__hideComAction.setVisible(isControlFlow)
        self.__hideExcptAction.setVisible(isControlFlow)
        self.__hideDecorActions.setVisible(isControlFlow)

        optEnabled = smartZoomLevel in [SMART_ZOOM_DISASM, SMART_ZOOM_BIN]
        self.__noOpt.setVisible(optEnabled)
        self.__assertOpt.setVisible(optEnabled)
        self.__docOpt.setVisible(optEnabled)

    def __createNavigationBar(self):
        """Creates the navigation bar"""
        self.__navBar = ControlFlowNavigationBar(self)
        return self.__navBar

    def __createStackedViews(self):
        """Creates the graphics view"""
        self.smartViews = QStackedWidget(self)
        self.smartViews.setContentsMargins(0, 0, 0, 0)

        # index 0: control flow
        self.smartViews.addWidget(CFGraphicsView(self.__navBar, self))
        # index 1: dependencies
        self.smartViews.addWidget(DepsGraphicsView(self.__navBar, self))
        # index 2: AST
        astView = ASTView(self.__navBar, self)
        astView.sigGotoLine.connect(self.__gotoLine)
        self.smartViews.addWidget(astView)
        # index 3: Disassembly
        disasmView = DisassemblyView(self.__navBar, self)
        disasmView.sigGotoLine.connect(self.__gotoLine)
        self.smartViews.addWidget(disasmView)
        # index 4: Binary
        self.smartViews.addWidget(BinView(self.__navBar, self))

        # Default view at the beginning is the control flow
        self.smartViews.setCurrentIndex(0)
        return self.smartViews

    def process(self):
        """Parses the content and displays the results"""
        if not self.__connected:
            self.__connectEditorSignals()

        if self.dirty():
            if self.__updateTimer.isActive():
                # Just in case; should not be needed but it is an extra safety
                self.__updateTimer.stop()

            smartZoomLevel = Settings()['smartZoom']
            if ZOOM_PROPS[smartZoomLevel].isControlFlow:
                # print('Populating control flow')
                self.__processControlFlow()
                # print('Populated')
            elif smartZoomLevel == SMART_ZOOM_BIN:
                # print('Populating BIN')
                self.__processBin()
                # print('Populated')
            elif smartZoomLevel == SMART_ZOOM_DISASM:
                # print('Populating disasm')
                self.__processDisasm()
                # print('Populated')
            elif smartZoomLevel == SMART_ZOOM_AST:
                # print('Populating AsT')
                self.__processAST()
                # print('Populated')
            elif smartZoomLevel == SMART_ZOOM_FS:
                # print('Populating FS')
                self.__processFS()
                # print('Populated')

            self.__markViewClean()

    def __processControlFlow(self):
        """Updates everything for the control flow"""
        start = timer()
        cf = getControlFlowFromMemory(self.__editor.text)
        end = timer()
        if cf.errors:
            self.__navBar.updateInfoIcon(self.__navBar.STATE_BROKEN_UTD)
            errors = []
            for err in cf.errors:
                if err[0] == -1 and err[1] == -1:
                    errors.append(err[2])
                elif err[1] == -1:
                    errors.append('[' + str(err[0]) + ':] ' + err[2])
                elif err[0] == -1:
                    errors.append('[:' + str(err[1]) + '] ' + err[2])
                else:
                    errors.append('[' + str(err[0]) + ':' +
                                  str(err[1]) + '] ' + err[2])
            self.__navBar.setErrors(
                'Control flow parser errors:\n' + '\n'.join(errors))
            return

        self.__cf = cf
        if self.isDebugMode():
            logging.info('Parsed file: %s', formatFlow(str(self.__cf)))
            logging.info('Parse timing: %f', end - start)

        # Collect warnings (parser + CML warnings) and valid groups
        self.__validGroups = []
        self.__allGroupId = set()
        allWarnings = self.__cf.warnings + \
                      CMLVersion.validateCMLComments(self.__cf,
                                                     self.__validGroups,
                                                     self.__allGroupId)

        # That will clear the error tooltip as well
        self.__navBar.updateInfoIcon(self.__navBar.STATE_OK_UTD)

        if allWarnings:
            warnings = []
            for warn in allWarnings:
                if warn[0] == -1 and warn[1] == -1:
                    warnings.append(warn[2])
                elif warn[1] == -1:
                    warnings.append('[' + str(warn[0]) + ':] ' + warn[2])
                elif warn[0] == -1:
                    warnings.append('[:' + str(warn[1]) + '] ' + warn[2])
                else:
                    warnings.append('[' + str(warn[0]) + ':' +
                                    str(warn[1]) + '] ' + warn[2])
            self.__navBar.setWarnings(
                'Control flow parser warnings:\n' + '\n'.join(warnings))
        else:
            self.__navBar.clearWarnings()

        self.redrawScene()

    def __processBin(self):
        """Processes the binary view"""
        fileName = self.__parentWidget.getFileName()
        if not fileName:
            # That's a buffer which has never been saved so the source is
            # needed
            fileName = self.__parentWidget.getShortName()
            self.view().populateBinary(
                self.__editor.text, self.__parentWidget.getEncoding(),
                fileName)
        else:
            if self.__parentWidget.isModified():
                # Buffer is modified, so need the source
                self.view().populateBinary(
                    self.__editor.text, self.__parentWidget.getEncoding(),
                    fileName)
            else:
                self.view().populateBinary(
                    None, self.__parentWidget.getEncoding(), fileName)
        self.__binLevel = Settings()['disasmLevel']

    def __processDisasm(self):
        """Processes the disassembly view"""
        fileName = self.__parentWidget.getFileName()
        if not fileName:
            # That's a buffer which has never been saved so the source is
            # needed
            fileName = self.__parentWidget.getShortName()
            self.view().populateDisassembly(
                self.__editor.text, self.__parentWidget.getEncoding(),
                fileName)
        else:
            if self.__parentWidget.isModified():
                # Buffer is modified, so need the source
                self.view().populateDisassembly(
                    self.__editor.text, self.__parentWidget.getEncoding(),
                    fileName)
            else:
                self.view().populateDisassembly(
                    None, self.__parentWidget.getEncoding(), fileName)

        self.__disasmLevel = Settings()['disasmLevel']

    def __processAST(self):
        """Processes the AST view"""
        fileName = self.__parentWidget.getFileName()
        if not fileName:
            fileName = self.__parentWidget.getShortName()

        self.view().populateAST(self.__editor.text, fileName)

    def __processFS(self):
        """Processes the file system view"""
        fileName = self.__parentWidget.getFileName()
        if not fileName:
            fileName = self.__parentWidget.getShortName()

        deps = collectImportResolutions(self.__editor.text, fileName)
        print(deps)

        self.scene().clear()

        smartZoomLevel = Settings()['smartZoom']
        self.cflowSettings = getCflowSettings(self)
        self.cflowSettings.itemID = 0
        self.cflowSettings = tweakSmartSettings(self.cflowSettings,
                                                smartZoomLevel)

        try:
            fileName = self.__parentWidget.getFileName()
            if not fileName:
                fileName = self.__parentWidget.getShortName()

            # Top level canvas has no adress and no parent canvas
            self.__canvas = DepsVirtualCanvas(self.cflowSettings, None, None, None)
            lStart = timer()
            self.__canvas.layoutTopLevel(fileName, deps)
            lEnd = timer()
            width, height = self.__canvas.render()
            rEnd = timer()
            self.scene().setSceneRect(0, 0, width, height)
            self.__canvas.draw(self.scene(), 0, 0)
            dEnd = timer()
            if self.isDebugMode():
                logging.info('Redrawing is done. Size: %d x %d', width, height)
                logging.info('Layout timing: %f', lEnd - lStart)
                logging.info('Render timing: %f', rEnd - lEnd)
                logging.info('Draw timing: %f', dEnd - rEnd)
        except Exception as exc:
            logging.error(str(exc))
            raise

    def __cleanupCanvas(self):
        """Cleans up the canvas"""
        if self.__canvas is not None:
            self.__canvas.cleanup()
            self.__canvas = None

    def redrawScene(self):
        """Redraws the scene"""
        self.scene().clear()

        smartZoomLevel = Settings()['smartZoom']
        self.cflowSettings = getCflowSettings(self)
        if self.dirty():
            self.__displayProps = (self.cflowSettings.hidedocstrings,
                                   self.cflowSettings.hidecomments,
                                   self.cflowSettings.hideexcepts,
                                   self.cflowSettings.hidedecors,
                                   smartZoomLevel)
        self.cflowSettings.itemID = 0
        self.cflowSettings = tweakSmartSettings(self.cflowSettings,
                                                smartZoomLevel)

        try:
            fileName = self.__parentWidget.getFileName()
            if not fileName:
                fileName = self.__parentWidget.getShortName()
            collapsedGroups = getCollapsedGroups(fileName)

            # Top level canvas has no adress and no parent canvas
            self.__canvas = VirtualCanvas(self.cflowSettings, None, None,
                                          self.__validGroups, collapsedGroups,
                                          None)
            lStart = timer()
            self.__canvas.layoutModule(self.__cf)
            lEnd = timer()
            self.__canvas.setEditor(self.__editor)
            width, height = self.__canvas.render()
            rEnd = timer()
            self.scene().setSceneRect(0, 0, width, height)
            self.__canvas.draw(self.scene(), 0, 0)
            dEnd = timer()
            if self.isDebugMode():
                logging.info('Redrawing is done. Size: %d x %d', width, height)
                logging.info('Layout timing: %f', lEnd - lStart)
                logging.info('Render timing: %f', rEnd - lEnd)
                logging.info('Draw timing: %f', dEnd - rEnd)
        except Exception as exc:
            logging.error(str(exc))
            raise

    def onFlowZoomChanged(self):
        """Triggered when a flow zoom is changed"""
        smartZoomLevel = Settings()['smartZoom']
        self.__setToolbarStatus(smartZoomLevel)
        if ZOOM_PROPS[smartZoomLevel].isControlFlow:
            if self.__cf:
                selection = self.scene().serializeSelection()
                firstOnScreen = self.scene().getFirstLogicalItem()
                self.cflowSettings.onFlowZoomChanged()
                self.redrawScene()
                self.updateNavigationToolbar('')
                self.scene().restoreSelectionByID(selection)
                self.__restoreScroll(firstOnScreen)

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered when a buffer content type has changed"""
        if self.__parentWidget.getUUID() != uuid:
            return

        if not isPythonMime(newFileType):
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__cleanupCanvas()
            self.__cf = None
            self.__validGroups = []
            self.setVisible(False)
            self.__navBar.updateInfoIcon(self.__navBar.STATE_UNKNOWN)
            return

        # Update the bar and show it
        self.setVisible(True)
        self.process()

        # The buffer type change event comes when the content is loaded first
        # time. So this is a good point to restore the position
        _, _, _, cflowHPos, cflowVPos = getFilePosition(fileName)
        self.setScrollbarPositions(cflowHPos, cflowVPos)

    def terminate(self):
        """Called when a tab is closed"""
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
        self.__updateTimer.deleteLater()

        self.__disconnectEditorSignals()

        self.__mainWindow = GlobalData().mainWindow
        editorsManager = self.__mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.disconnect(self.__onFileTypeChanged)

        Settings().sigHideDocstringsChanged.disconnect(
            self.__onHideDocstringsChanged)
        Settings().sigHideCommentsChanged.disconnect(self.__onHideCommentsChanged)
        Settings().sigHideExceptsChanged.disconnect(self.__onHideExceptsChanged)
        Settings().sigHideDecorsChanged.disconnect(self.__onHideDecorsChanged)
        Settings().sigSmartZoomChanged.disconnect(self.__onSmartZoomChanged)
        Settings().sigDisasmLevelChanged.disconnect(self.__onDisasmLevelChanged)

        # Helps GC to collect more
        self.__cleanupCanvas()
        for index in range(self.smartViews.count()):
            if hasattr(self.smartViews.widget(index), 'terminate'):
                self.smartViews.widget(index).terminate()
            self.smartViews.widget(index).deleteLater()

        self.smartViews.deleteLater()
        self.__navBar.deleteLater()
        self.__cf = None

        self.__saveAsButton.menu().deleteLater()
        self.__saveAsButton.deleteLater()

        self.__levelUpButton.clicked.disconnect(self.onSmartZoomLevelUp)
        self.__levelUpButton.deleteLater()

        self.__levelDownButton.clicked.disconnect(self.onSmartZoomLevelDown)
        self.__levelDownButton.deleteLater()

        self.__hideDocstrings.clicked.disconnect(self.__onHideDocstrings)
        self.__hideDocstrings.deleteLater()

        self.__hideComments.clicked.disconnect(self.__onHideComments)
        self.__hideComments.deleteLater()

        self.__hideExcepts.clicked.disconnect(self.__onHideExcepts)
        self.__hideExcepts.deleteLater()

        self.__hideDecors.clicked.disconnect(self.__onHideDecors)
        self.__hideDecors.deleteLater()

        self.__toolbar.deleteLater()

        self.__editor = None
        self.__parentWidget = None
        self.cflowSettings = None
        self.__displayProps = None

    def __connectEditorSignals(self):
        """When it is a python file - connect to the editor signals"""
        if not self.__connected:
            QApplication.processEvents()
            self.__editor.cursorPositionChanged.connect(
                self.__cursorPositionChanged)
            self.__editor.textChanged.connect(self.__onBufferChanged)
            self.__connected = True

    def __disconnectEditorSignals(self):
        """Disconnect the editor signals when the file is not a python one"""
        if self.__connected:
            self.__editor.cursorPositionChanged.disconnect(
                self.__cursorPositionChanged)
            self.__editor.textChanged.disconnect(self.__onBufferChanged)
            self.__connected = False

    def __cursorPositionChanged(self):
        """Cursor position changed"""
        # The timer should be reset only in case if the redrawing was delayed
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
            self.__updateTimer.start(IDLE_TIMEOUT)

    def __onBufferChanged(self):
        """Triggered to update status icon and to restart the timer"""
        self.__updateTimer.stop()
        self.__markViewsDirty()
        if self.__navBar.getCurrentState() in [self.__navBar.STATE_OK_UTD,
                                               self.__navBar.STATE_OK_CHN,
                                               self.__navBar.STATE_UNKNOWN]:
            self.__navBar.updateInfoIcon(self.__navBar.STATE_OK_CHN)
        else:
            self.__navBar.updateInfoIcon(self.__navBar.STATE_BROKEN_CHN)
        self.__updateTimer.start(IDLE_TIMEOUT)

    def redrawNow(self):
        """Redraw the diagram regardless of the timer"""
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
        self.process()

    def generateNewGroupId(self):
        """Generates a new group ID (string)"""
        # It can also consider the current set of the groups: valid + invalid
        # and generate an integer id which is shorter
        for vacantGroupId in range(1000):
            groupId = str(vacantGroupId)
            if not groupId in self.__allGroupId:
                return groupId
        # Last resort
        return str(uuid.uuid1())

    def updateNavigationToolbar(self, text):
        """Updates the toolbar text"""
        if self.__needPathUpdate:
            self.__navBar.setPath(text)

    def updateSettings(self):
        """Updates settings"""
        self.__needPathUpdate = Settings()['showCFNavigationBar']
        self.__navBar.setPathVisible(self.__needPathUpdate)
        self.__navBar.setPath('')

    def highlightAtAbsPos(self, absPos, line, pos):
        """Scrolls the view to the item closest to absPos and selects it.

        line and pos are 1-based
        """
        item, _ = self.scene().getNearestItem(absPos, line, pos)
        if item:
            GlobalData().mainWindow.setFocusToFloatingRenderer()
            self.scene().clearSelection()
            item.setSelected(True)
            self.view().scrollTo(item)
            self.setFocus()

    def setFocus(self):
        """Sets the focus"""
        self.view().setFocus()

    @staticmethod
    def __getDefaultSaveDir():
        """Provides the default directory to save files to"""
        project = GlobalData().project
        if project.isLoaded():
            return project.getProjectDir()
        return QDir.currentPath()

    def __selectFile(self, extension):
        """Picks a file of a certain extension"""
        dialog = QFileDialog(self, 'Save flowchart as')
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setLabelText(QFileDialog.Accept, "Save")
        dialog.setNameFilter(extension.upper() + " files (*." +
                             extension.lower() + ")")
        urls = []
        for dname in QDir.drives():
            urls.append(QUrl.fromLocalFile(dname.absoluteFilePath()))
        urls.append(QUrl.fromLocalFile(QDir.homePath()))
        project = GlobalData().project
        if project.isLoaded():
            urls.append(QUrl.fromLocalFile(project.getProjectDir()))
        dialog.setSidebarUrls(urls)

        suggestedFName = self.__parentWidget.getFileName()
        if '.' in suggestedFName:
            dotIndex = suggestedFName.rindex('.')
            suggestedFName = suggestedFName[:dotIndex]

        dialog.setDirectory(self.__getDefaultSaveDir())
        dialog.selectFile(suggestedFName + "." + extension.lower())
        dialog.setOption(QFileDialog.DontConfirmOverwrite, False)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        if dialog.exec_() != QDialog.Accepted:
            return None

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath(str(fileNames[0]))
        if os.path.isdir(fileName):
            logging.error("A file must be selected")
            return None

        if "." not in fileName:
            fileName += "." + extension.lower()

        # Check permissions to write into the file or to a directory
        if os.path.exists(fileName):
            # Check write permissions for the file
            if not os.access(fileName, os.W_OK):
                logging.error("There is no write permissions for " + fileName)
                return None
        else:
            # Check write permissions to the directory
            dirName = os.path.dirname(fileName)
            if not os.access(dirName, os.W_OK):
                logging.error("There is no write permissions for the "
                              "directory " + dirName)
                return None

        if os.path.exists(fileName):
            res = QMessageBox.warning(
                self, "Save flowchart as",
                "<p>The file <b>" + fileName + "</b> already exists.</p>",
                QMessageBox.StandardButtons(QMessageBox.Abort |
                                            QMessageBox.Save),
                QMessageBox.Abort)
            if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                return None

        # All prerequisites are checked, return a file name
        return fileName

    def onSaveAsSVG(self):
        """Triggered on the 'Save as SVG' button"""
        fileName = self.__selectFile("svg")
        if fileName is None:
            return False

        try:
            self.__saveAsSVG(fileName)
        except Exception as excpt:
            logging.error(str(excpt))
            return False
        return True

    def __saveAsSVG(self, fileName):
        """Saves the flowchart as an SVG file"""
        generator = QSvgGenerator()
        generator.setFileName(fileName)
        generator.setSize(QSize(self.scene().width(), self.scene().height()))
        painter = QPainter(generator)
        self.scene().render(painter)
        painter.end()

    def onSaveAsPDF(self):
        """Triggered on the 'Save as PDF' button"""
        fileName = self.__selectFile("pdf")
        if fileName is None:
            return False

        try:
            self.__saveAsPDF(fileName)
        except Exception as excpt:
            logging.error(str(excpt))
            return False
        return True

    def __saveAsPDF(self, fileName):
        """Saves the flowchart as an PDF file"""
        printer = QPrinter()
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setPaperSize(QSizeF(self.scene().width(),
                                    self.scene().height()), QPrinter.Point)
        printer.setFullPage(True)
        printer.setOutputFileName(fileName)

        painter = QPainter(printer)
        self.scene().render(painter)
        painter.end()

    def onSaveAsPNG(self):
        """Triggered on the 'Save as PNG' button"""
        fileName = self.__selectFile("png")
        if fileName is None:
            return False

        try:
            self.__saveAsPNG(fileName)
        except Exception as excpt:
            logging.error(str(excpt))
            return False
        return True

    def __getPNG(self):
        """Renders the scene as PNG"""
        image = QImage(self.scene().width(), self.scene().height(),
                       QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        # It seems that the better results are without antialiasing
        # painter.setRenderHint( QPainter.Antialiasing )
        self.scene().render(painter)
        painter.end()
        return image

    def __saveAsPNG(self, fileName):
        """Saves the flowchart as an PNG file"""
        image = self.__getPNG()
        image.save(fileName, "PNG")

    def copyToClipboard(self):
        """Copies the rendered scene to the clipboard as an image"""
        image = self.__getPNG()
        clip = QApplication.clipboard()
        clip.setImage(image)

    def getScrollbarPositions(self):
        """Provides the scrollbar positions"""
        if self.__scrollRestored:
            cfViewIndex = ZOOM_PROPS[SMART_ZOOM_ALL].viewIndex
            cfWidget = self.smartViews.widget(cfViewIndex)
            hScrollBar = cfWidget.horizontalScrollBar()
            vScrollBar = cfWidget.verticalScrollBar()
            return hScrollBar.value(), vScrollBar.value()
        return None, None

    def setScrollbarPositions(self, hPos, vPos):
        """Sets the scrollbar positions for the view"""
        if not self.__scrollRestored:
            if isControlFlowLevel(Settings()['smartZoom']):
                self.view().horizontalScrollBar().setValue(hPos)
                self.view().verticalScrollBar().setValue(vPos)
                self.__scrollRestored = True

    def __onHideDocstrings(self):
        """Triggered when a hide docstring button is pressed"""
        Settings()['hidedocstrings'] = not Settings()['hidedocstrings']

    def __onHideDocstringsChanged(self):
        """Signalled by settings"""
        selection = self.scene().serializeSelection()
        firstOnScreen = self.scene().getFirstLogicalItem()
        settings = Settings()
        self.__hideDocstrings.setChecked(settings['hidedocstrings'])
        if self.__checkNeedRedraw():
            self.scene().restoreSelectionByID(selection)
            self.__restoreScroll(firstOnScreen)

    def __onHideComments(self):
        """Triggered when a hide comments button is pressed"""
        Settings()['hidecomments'] = not Settings()['hidecomments']

    def __onHideCommentsChanged(self):
        """Signalled by settings"""
        selection = self.scene().serializeSelection()
        firstOnScreen = self.scene().getFirstLogicalItem()
        settings = Settings()
        self.__hideComments.setChecked(settings['hidecomments'])
        if self.__checkNeedRedraw():
            self.scene().restoreSelectionByID(selection)
            self.__restoreScroll(firstOnScreen)

    def __onHideExcepts(self):
        """Triggered when a hide except blocks button is pressed"""
        Settings()['hideexcepts'] = not Settings()['hideexcepts']

    def __onHideExceptsChanged(self):
        """Signalled by settings"""
        selection = self.scene().serializeSelection()
        firstOnScreen = self.scene().getFirstLogicalItem()
        settings = Settings()
        self.__hideExcepts.setChecked(settings['hideexcepts'])
        if self.__checkNeedRedraw():
            self.scene().restoreSelectionByTooltip(selection)
            self.__restoreScroll(firstOnScreen)

    def __onHideDecors(self):
        """Triggered when a hide decorators button is pressed"""
        Settings()['hidedecors'] = not Settings()['hidedecors']

    def __onHideDecorsChanged(self):
        """Signalled by settings"""
        selection = self.scene().serializeSelection()
        firstOnScreen = self.scene().getFirstLogicalItem()
        settings = Settings()
        self.__hideDecors.setChecked(settings['hidedecors'])
        if self.__checkNeedRedraw():
            self.scene().restoreSelectionByTooltip(selection)
            self.__restoreScroll(firstOnScreen)

    def __checkNeedRedraw(self):
        """Redraws the scene if necessary when a display setting is changed"""
        editorsManager = self.__mainWindow.editorsManagerWidget.editorsManager
        if self.__parentWidget == editorsManager.currentWidget():
            self.updateNavigationToolbar('')
            self.process()
            return True
        return False

    def onCurrentTabChanged(self):
        """Editors manager changed the tab"""
        currentSmartZoom = Settings()['smartZoom']
        if self.dirty():
            if ZOOM_PROPS[currentSmartZoom].isControlFlow:
                selection = self.scene().serializeSelection()
                self.process()
                self.scene().restoreSelectionByTooltip(selection)

                # It could be the first time to switch to the tab with
                # the control flow so set the scrollbar position
                if not self.__scrollRestored:
                    fileName = self.__parentWidget.getFileName()
                    if fileName:
                        _, _, _, cflowHPos, cflowVPos = getFilePosition(fileName)
                        self.setScrollbarPositions(cflowHPos, cflowVPos)
            else:
                self.process()

    def dirty(self):
        """True if some other tab has switched display settings"""
        if self.__isCurrentViewDirty():
            return True

        currentSmartZoom = Settings()['smartZoom']
        if ZOOM_PROPS[currentSmartZoom].isControlFlow:
            settings = Settings()
            return self.__displayProps[0] != settings['hidedocstrings'] or \
                self.__displayProps[1] != settings['hidecomments'] or \
                self.__displayProps[2] != settings['hideexcepts'] or \
                self.__displayProps[3] != settings['hidedecors'] or \
                self.__displayProps[4] != settings['smartZoom']
        if currentSmartZoom == SMART_ZOOM_DISASM:
            return self.__disasmLevel != Settings()['disasmLevel']
        if currentSmartZoom == SMART_ZOOM_BIN:
            return self.__binLevel != Settings()['disasmLevel']

        return False

    def onSmartZoomLevelUp(self):
        """Triggered when an upper smart zoom level was requested"""
        Settings().onSmartZoomIn()

    def onSmartZoomLevelDown(self):
        """Triggered when an lower smart zoom level was requested"""
        Settings().onSmartZoomOut()

    def setSmartZoomLevel(self, smartZoomLevel):
        """Sets the new smart zoom level"""
        if smartZoomLevel < SMART_ZOOM_MIN:
            return
        if smartZoomLevel > SMART_ZOOM_MAX:
            return

        self.__levelIndicator.setText(
            '<b>' + ZOOM_PROPS[smartZoomLevel].label + '</b>')
        self.__levelIndicator.setToolTip(
            getSmartZoomDescription(smartZoomLevel))
        self.__levelUpButton.setEnabled(smartZoomLevel < SMART_ZOOM_MAX)
        self.__levelDownButton.setEnabled(smartZoomLevel > SMART_ZOOM_MIN)

        self.__saveNavBarProps()
        self.__setToolbarStatus(smartZoomLevel)
        self.smartViews.setCurrentIndex(ZOOM_PROPS[smartZoomLevel].viewIndex)
        self.__restoreNavBarProps()

    def __onSmartZoomChanged(self):
        """Triggered when a smart zoom changed"""
        newZoomLevel = Settings()['smartZoom']

        isOldCF = isControlFlowView(self.smartViews.currentIndex())
        isNewCF = ZOOM_PROPS[newZoomLevel].isControlFlow

        if isOldCF and isNewCF:
            selection = self.scene().serializeSelection()
            firstOnScreen = self.scene().getFirstLogicalItem()

        self.setSmartZoomLevel(newZoomLevel)

        if self.__checkNeedRedraw():
            if isOldCF and isNewCF:
                self.scene().restoreSelectionByTooltip(selection)
                self.__restoreScroll(firstOnScreen)
            elif isNewCF:
                # May be the scroll position needs to be restored for this
                # particular file
                fileName = self.__parentWidget.getFileName()
                if fileName:
                    _, _, _, cflowHPos, cflowVPos = getFilePosition(fileName)
                    self.setScrollbarPositions(cflowHPos, cflowVPos)

    def __onOpt0(self, checked):
        """Disasm level 0 triggered"""
        if checked and Settings()['disasmLevel'] != 0:
            Settings()['disasmLevel'] = 0

    def __onOpt1(self, checked):
        """Disasm level 1 triggered"""
        if checked and Settings()['disasmLevel'] != 1:
            Settings()['disasmLevel'] = 1

    def __onOpt2(self, checked):
        """Disasm level 2 triggered"""
        if checked and Settings()['disasmLevel'] != 2:
            Settings()['disasmLevel'] = 2

    def __onDisasmLevelChanged(self):
        """Disasm level changed"""
        disasmLevel = Settings()['disasmLevel']
        if disasmLevel == 0:
            self.__noOpt.setChecked(True)
        elif disasmLevel == 1:
            self.__assertOpt.setChecked(True)
        else:
            self.__docOpt.setChecked(True)

        self.__checkNeedRedraw()

    def __restoreScroll(self, toItem):
        """Restores the view scrolling to the best possible position"""
        if toItem:
            lineRange = toItem.getLineRange()
            absPosRange = toItem.getAbsPosRange()
            item, _ = self.scene().getNearestItem(absPosRange[0],
                                                  lineRange[0], 0)
            if item:
                self.view().scrollTo(item, True)
                self.view().horizontalScrollBar().setValue(0)

    def validateCollapsedGroups(self, fileName):
        """Checks that there are no collapsed groups which are invalid"""
        if self.__navBar.getCurrentState() != self.__navBar.STATE_OK_UTD:
            return

        collapsedGroups = getCollapsedGroups(fileName)
        if collapsedGroups:
            toBeDeleted = []
            for groupId in collapsedGroups:
                for validId, start, end in self.__validGroups:
                    del start
                    del end
                    if validId == groupId:
                        break
                else:
                    toBeDeleted.append(groupId)

            if toBeDeleted:
                for groupId in toBeDeleted:
                    collapsedGroups.remove(groupId)
                setCollapsedGroups(fileName, collapsedGroups)
        else:
            setCollapsedGroups(fileName, [])

    def getDocItemByAnchor(self, anchor):
        """Provides the graphics item for the given anchor if so"""
        return self.scene().getDocItemByAnchor(anchor)

    @staticmethod
    def isDebugMode():
        """True if it is a debug mode"""
        return GlobalData().skin['debug']

    def __gotoLine(self, line, pos):
        self.__editor.gotoLine(line, pos)
        self.__editor.setFocus()
