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
from ui.qt import (Qt, QSize, QTimer, QDir, QUrl, QSizeF, QPainter, QImage,
                   QToolBar, QWidget, QPrinter, QApplication, QHBoxLayout,
                   QLabel, QVBoxLayout, QSizePolicy, QFileDialog,
                   QDialog, QMenu, QToolButton, QMessageBox, QSvgGenerator,
                   QStackedWidget)
from cdmcfparser import getControlFlowFromMemory
from flowui.vcanvas import VirtualCanvas
from flowui.cflowsettings import getCflowSettings
from flowui.cml import CMLVersion
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.fileutils import isPythonMime
from utils.settings import Settings
from utils.diskvaluesrelay import (getFilePosition, getCollapsedGroups,
                                   setCollapsedGroups)
from .flowuinavbar import ControlFlowNavigationBar
from .flowuisceneview import CFGraphicsView


IDLE_TIMEOUT = 1500

SMART_ZOOM_ALL = 0          # Show everything
SMART_ZOOM_NO_CONTENT = 1   # All the boxes are without a content
SMART_ZOOM_CONTROL_ONLY = 2 # Only scopes (except decorators) and ifs
SMART_ZOOM_CLASS_FUNC = 3   # Only top level classes and functions


def getSmartZoomDescription(smartZoomLevel):
    """Provides a tooltip for the smart zoom level"""
    if smartZoomLevel == SMART_ZOOM_ALL:
        return 'Smart zoom level: everything is shown'
    elif smartZoomLevel == SMART_ZOOM_NO_CONTENT:
        return 'Smart zoom level: everything without a content'
    elif smartZoomLevel == SMART_ZOOM_CONTROL_ONLY:
        return 'Smart zoom level: scopes (except decorators) and ifs'
    elif smartZoomLevel == SMART_ZOOM_CLASS_FUNC:
        return 'Smart zoom level: top level classes and functions'
    return 'Unknown smart zoom level'


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

        self.cflowSettings = getCflowSettings(self)
        self.__displayProps = (self.cflowSettings.hidedocstrings,
                               self.cflowSettings.hidecomments,
                               self.cflowSettings.hideexcepts,
                               Settings()['smartZoom'])

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

        # Connect to the change file type signal
        self.__mainWindow = GlobalData().mainWindow
        editorsManager = self.__mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)

        Settings().sigHideDocstringsChanged.connect(
            self.__onHideDocstringsChanged)
        Settings().sigHideCommentsChanged.connect(self.__onHideCommentsChanged)
        Settings().sigHideExceptsChanged.connect(self.__onHideExceptsChanged)
        Settings().sigSmartZoomChanged.connect(self.__onSmartZoomChanged)

        self.setSmartZoomLevel(Settings()['smartZoom'])

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

        self.__saveAsButton = QToolButton(self)
        self.__saveAsButton.setIcon(getIcon('saveasmenu.png'))
        self.__saveAsButton.setToolTip('Save as')
        self.__saveAsButton.setPopupMode(QToolButton.InstantPopup)
        self.__saveAsButton.setMenu(saveAsMenu)
        self.__saveAsButton.setFocusPolicy(Qt.NoFocus)

        self.__levelUpButton = QToolButton(self)
        self.__levelUpButton.setFocusPolicy(Qt.NoFocus)
        self.__levelUpButton.setIcon(getIcon('levelup.png'))
        self.__levelUpButton.setToolTip('Smart zoom level up (Shift+wheel)')
        self.__levelUpButton.clicked.connect(self.onSmartZoomLevelUp)
        self.__levelIndicator = QLabel('<b>0</b>', self)
        self.__levelIndicator.setAlignment(Qt.AlignCenter)
        self.__levelDownButton = QToolButton(self)
        self.__levelDownButton.setFocusPolicy(Qt.NoFocus)
        self.__levelDownButton.setIcon(getIcon('leveldown.png'))
        self.__levelDownButton.setToolTip('Smart zoom level down (Shift+wheel)')
        self.__levelDownButton.clicked.connect(self.onSmartZoomLevelDown)

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight(10)

        self.__hideDocstrings = QToolButton(self)
        self.__hideDocstrings.setCheckable(True)
        self.__hideDocstrings.setIcon(getIcon('hidedocstrings.png'))
        self.__hideDocstrings.setToolTip('Show/hide docstrings')
        self.__hideDocstrings.setFocusPolicy(Qt.NoFocus)
        self.__hideDocstrings.setChecked(Settings()['hidedocstrings'])
        self.__hideDocstrings.clicked.connect(self.__onHideDocstrings)
        self.__hideComments = QToolButton(self)
        self.__hideComments.setCheckable(True)
        self.__hideComments.setIcon(getIcon('hidecomments.png'))
        self.__hideComments.setToolTip('Show/hide comments')
        self.__hideComments.setFocusPolicy(Qt.NoFocus)
        self.__hideComments.setChecked(Settings()['hidecomments'])
        self.__hideComments.clicked.connect(self.__onHideComments)
        self.__hideExcepts = QToolButton(self)
        self.__hideExcepts.setCheckable(True)
        self.__hideExcepts.setIcon(getIcon('hideexcepts.png'))
        self.__hideExcepts.setToolTip('Show/hide except blocks')
        self.__hideExcepts.setFocusPolicy(Qt.NoFocus)
        self.__hideExcepts.setChecked(Settings()['hideexcepts'])
        self.__hideExcepts.clicked.connect(self.__onHideExcepts)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.__toolbar.addWidget(self.__saveAsButton)
        self.__toolbar.addWidget(spacer)
        self.__toolbar.addWidget(self.__levelUpButton)
        self.__toolbar.addWidget(self.__levelIndicator)
        self.__toolbar.addWidget(self.__levelDownButton)
        self.__toolbar.addWidget(fixedSpacer)
        self.__toolbar.addWidget(self.__hideDocstrings)
        self.__toolbar.addWidget(self.__hideComments)
        self.__toolbar.addWidget(self.__hideExcepts)
        return self.__toolbar

    def __createNavigationBar(self):
        """Creates the navigation bar"""
        self.__navBar = ControlFlowNavigationBar(self)
        return self.__navBar

    def __createStackedViews(self):
        """Creates the graphics view"""
        self.smartViews = QStackedWidget(self)
        self.smartViews.setContentsMargins(0, 0, 0, 0)

        self.smartViews.addWidget(CFGraphicsView(self.__navBar, self))
        self.smartViews.addWidget(CFGraphicsView(self.__navBar, self))
        return self.smartViews

    def process(self):
        """Parses the content and displays the results"""
        if not self.__connected:
            self.__connectEditorSignals()

        cf = getControlFlowFromMemory(self.__editor.text)
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
            self.__navBar.setErrors(errors)
            return
        self.__cf = cf

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
            self.__navBar.setWarnings(warnings)
        else:
            self.__navBar.clearWarnings()

        self.redrawScene()

    def redrawScene(self):
        """Redraws the scene"""
        smartZoomLevel = Settings()['smartZoom']
        self.cflowSettings = getCflowSettings(self)
        if self.dirty():
            self.__displayProps = (self.cflowSettings.hidedocstrings,
                                   self.cflowSettings.hidecomments,
                                   self.cflowSettings.hideexcepts,
                                   smartZoomLevel)
        self.cflowSettings.itemID = 0
        self.cflowSettings = tweakSmartSettings(self.cflowSettings,
                                                smartZoomLevel)

        self.scene().clear()
        try:
            fileName = self.__parentWidget.getFileName()
            if not fileName:
                fileName = self.__parentWidget.getShortName()
            collapsedGroups = getCollapsedGroups(fileName)

            # Top level canvas has no adress and no parent canvas
            canvas = VirtualCanvas(self.cflowSettings, None, None,
                                   self.__validGroups, collapsedGroups, None)
            canvas.layoutModule(self.__cf)
            canvas.setEditor(self.__editor)
            width, height = canvas.render()
            self.scene().setSceneRect(0, 0, width, height)
            canvas.draw(self.scene(), 0, 0)
        except Exception as exc:
            logging.error(str(exc))
            raise

    def onFlowZoomChanged(self):
        """Triggered when a flow zoom is changed"""
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

    def __connectEditorSignals(self):
        """When it is a python file - connect to the editor signals"""
        if not self.__connected:
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
        hScrollBar = self.view().horizontalScrollBar()
        vScrollBar = self.view().verticalScrollBar()
        return hScrollBar.value(), vScrollBar.value()

    def setScrollbarPositions(self, hPos, vPos):
        """Sets the scrollbar positions for the view"""
        self.view().horizontalScrollBar().setValue(hPos)
        self.view().verticalScrollBar().setValue(vPos)

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

    def __checkNeedRedraw(self):
        """Redraws the scene if necessary when a display setting is changed"""
        editorsManager = self.__mainWindow.editorsManagerWidget.editorsManager
        if self.__parentWidget == editorsManager.currentWidget():
            self.updateNavigationToolbar('')
            self.process()
            return True
        return False

    def dirty(self):
        """True if some other tab has switched display settings"""
        settings = Settings()
        return self.__displayProps[0] != settings['hidedocstrings'] or \
            self.__displayProps[1] != settings['hidecomments'] or \
            self.__displayProps[2] != settings['hideexcepts'] or \
            self.__displayProps[3] != settings['smartZoom']

    def onSmartZoomLevelUp(self):
        """Triggered when an upper smart zoom level was requested"""
        maxSmartZoom = Settings().MAX_SMART_ZOOM
        currentLevel = Settings()['smartZoom']
        if currentLevel < maxSmartZoom:
            Settings()['smartZoom'] = currentLevel + 1

    def onSmartZoomLevelDown(self):
        """Triggered when an lower smart zoom level was requested"""
        currentLevel = Settings()['smartZoom']
        if currentLevel > 0:
            Settings()['smartZoom'] = currentLevel - 1

    def setSmartZoomLevel(self, smartZoomLevel):
        """Sets the new smart zoom level"""
        maxSmartZoom = Settings().MAX_SMART_ZOOM
        if smartZoomLevel < 0 or smartZoomLevel > maxSmartZoom:
            return

        self.__levelIndicator.setText('<b>' + str(smartZoomLevel) + '</b>')
        self.__levelIndicator.setToolTip(
            getSmartZoomDescription(smartZoomLevel))
        self.__levelUpButton.setEnabled(smartZoomLevel < maxSmartZoom)
        self.__levelDownButton.setEnabled(smartZoomLevel > 0)
        self.smartViews.setCurrentIndex(smartZoomLevel)

    def __onSmartZoomChanged(self):
        """Triggered when a smart zoom changed"""
        selection = self.scene().serializeSelection()
        firstOnScreen = self.scene().getFirstLogicalItem()
        self.setSmartZoomLevel(Settings()['smartZoom'])
        if self.__checkNeedRedraw():
            self.scene().restoreSelectionByTooltip(selection)
            self.__restoreScroll(firstOnScreen)

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
