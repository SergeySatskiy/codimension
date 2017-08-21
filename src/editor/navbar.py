# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Navigation bar implementation"""

from ui.qt import (QTimer, Qt, QEvent, pyqtSignal, QFrame, QHBoxLayout, QLabel,
                   QWidget, QSizePolicy, QComboBox)
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import isPythonMime
from utils.pixmapcache import getPixmap, getIcon
from cdmpyparser import getBriefModuleInfoFromMemory
from autocomplete.bufferutils import getContext


IDLE_TIMEOUT = 1500


class NavBarComboBox(QComboBox):

    """Navigation bar combo box"""

    jumpToLine = pyqtSignal(int)

    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.activated.connect(self.onActivated)

        self.view().installEventFilter(self)

        self.pathIndex = None

    # Arguments: obj, event
    def eventFilter(self, _, event):
        """Event filter for the qcombobox list view"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.parent().getEditor().setFocus()
                return True
            if key == Qt.Key_Left:
                # Move cursor to the left combo
                if self.pathIndex is not None:
                    self.parent().activateCombo(self, self.pathIndex - 1)
                    return True
            if key == Qt.Key_Right:
                # Move cursor to the right combo
                if self.pathIndex is not None:
                    self.parent().activateCombo(self, self.pathIndex + 1)
                else:
                    self.parent().activateCombo(self, 0)
                return True
        return False

    def onActivated(self, index):
        """User selected an item"""
        if index >= 0:
            self.jumpToLine.emit(self.itemData(index))


class PathElement:

    """Single path element"""

    def __init__(self, parent=None):
        self.icon = QLabel()
        self.icon.setPixmap(getPixmap('nbsep.png'))
        self.combo = NavBarComboBox(parent)


class NavigationBar(QFrame):

    """Navigation bar at the top of the editor (python only)"""

    STATE_OK_UTD = 0        # Parsed OK, context up to date
    STATE_OK_CHN = 1        # Parsed OK, context changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, context up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, context changed
    STATE_UNKNOWN = 4

    def __init__(self, editor, parent):
        QFrame.__init__(self, parent)
        self.__editor = editor
        self.__parentWidget = parent

        # It is always not visible at the beginning because there is no
        # editor content at the start
        self.setVisible(False)

        # There is no parser info used to display values
        self.__currentInfo = None
        self.__currentIconState = self.STATE_UNKNOWN
        self.__connected = False

        # List of PathElement starting after the global scope
        self.__path = []

        self.__createLayout()

        # Create the update timer
        self.__updateTimer = QTimer(self)
        self.__updateTimer.setSingleShot(True)
        self.__updateTimer.timeout.connect(self.updateBar)

        # Connect to the change file type signal
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)

    def getEditor(self):
        """Provides the editor"""
        return self.__editor

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

    def __createLayout(self):
        """Creates the layout"""
        self.setFixedHeight(24)
        self.__layout = QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)

        # Set the background color

        # Create info icon
        self.__infoIcon = QLabel()
        self.__layout.addWidget(self.__infoIcon)

        self.__globalScopeCombo = NavBarComboBox(self)
        self.__globalScopeCombo.jumpToLine.connect(self.__onJumpToLine)
        self.__layout.addWidget(self.__globalScopeCombo)

        self.__spacer = QWidget()
        self.__spacer.setSizePolicy(QSizePolicy.Expanding,
                                    QSizePolicy.Expanding)
        self.__layout.addWidget(self.__spacer)

    def __updateInfoIcon(self, state):
        """Updates the information icon"""
        if state != self.__currentIconState:
            if state == self.STATE_OK_UTD:
                self.__infoIcon.setPixmap(getPixmap('nbokutd.png'))
                self.__infoIcon.setToolTip("Context is up to date")
                self.__currentIconState = self.STATE_OK_UTD
            elif state == self.STATE_OK_CHN:
                self.__infoIcon.setPixmap(getPixmap('nbokchn.png'))
                self.__infoIcon.setToolTip("Context is not up to date; "
                                           "will be updated on idle")
                self.__currentIconState = self.STATE_OK_CHN
            elif state == self.STATE_BROKEN_UTD:
                self.__infoIcon.setPixmap(getPixmap('nbbrokenutd.png'))
                self.__infoIcon.setToolTip("Context might be invalid "
                                           "due to invalid python code")
                self.__currentIconState = self.STATE_BROKEN_UTD
            else:
                # STATE_BROKEN_CHN
                self.__infoIcon.setPixmap(getPixmap('nbbrokenchn.png'))
                self.__infoIcon.setToolTip("Context might be invalid; "
                                           "will be updated on idle")
                self.__currentIconState = self.STATE_BROKEN_CHN

    def resizeEvent(self, event):
        """Editor has resized"""
        QFrame.resizeEvent(self, event)

    # Arguments: fileName, uuid, newFileType
    def __onFileTypeChanged(self, _, uuid, newFileType):
        """Triggered when a buffer content type has changed"""
        if self.__parentWidget.getUUID() != uuid:
            return

        if isPythonMime(newFileType) and Settings()['showNavigationBar']:
            # Update the bar and show it
            self.setVisible(True)
            self.updateBar()
        else:
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__currentInfo = None
            self.setVisible(False)
            self.__currentIconState = self.STATE_UNKNOWN

    def updateSettings(self):
        """Called when navigation bar settings have been updated"""
        textMime = self.__parentWidget.getMime()
        if Settings()['showNavigationBar'] and isPythonMime(textMime):
            self.setVisible(True)
            self.updateBar()
        else:
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__currentInfo = None
            self.setVisible(False)

    def updateBar(self):
        """Triggered when the timer is fired"""
        self.__updateTimer.stop()  # just in case

        if not isPythonMime(self.__parentWidget.getMime()):
            return

        if not self.__connected:
            self.__connectEditorSignals()

        # Parse the buffer content
        self.__currentInfo = getBriefModuleInfoFromMemory(self.__editor.text)

        # Decide what icon to use
        if self.__currentInfo.isOK:
            self.__updateInfoIcon(self.STATE_OK_UTD)
        else:
            self.__updateInfoIcon(self.STATE_BROKEN_UTD)

        # Calc the cursor context
        context = getContext(self.__editor, self.__currentInfo, True, False)

        # Display the context
        self.__populateGlobalScope()
        if context.length == 0:
            self.__globalScopeCombo.setCurrentIndex(-1)
        else:
            index = self.__globalScopeCombo.findData(
                context.levels[0][0].line)
            self.__globalScopeCombo.setCurrentIndex(index)

        usedFromStore = 0
        index = 1
        while index < context.length:
            if len(self.__path) < index:
                newPathItem = PathElement(self)
                self.__path.append(newPathItem)
                self.__layout.addWidget(newPathItem.icon)
                self.__layout.addWidget(newPathItem.combo)
                combo = newPathItem.combo
                combo.pathIndex = len(self.__path) - 1
                combo.jumpToLine.connect(self.__onJumpToLine)
            else:
                self.__path[index - 1].icon.setVisible(True)
                self.__path[index - 1].combo.setVisible(True)
                combo = self.__path[index - 1].combo
                combo.clear()

            # Populate the combo box
            self.__populateClassesAndFunctions(context.levels[index - 1][0],
                                               combo)
            combo.setCurrentIndex(combo.findData(context.levels[index][0].line))
            index += 1
            usedFromStore += 1

        # it might need to have one more level with nothing selected
        if context.length > 0:
            if len(context.levels[context.length - 1][0].functions) > 0 or \
               len(context.levels[context.length - 1][0].classes) > 0:
                # Need to add a combo
                if len(self.__path) <= usedFromStore:
                    newPathItem = PathElement(self)
                    self.__path.append(newPathItem)
                    self.__layout.addWidget(newPathItem.icon)
                    self.__layout.addWidget(newPathItem.combo)
                    combo = newPathItem.combo
                    combo.pathIndex = len(self.__path) - 1
                    combo.jumpToLine.connect(self.__onJumpToLine)
                else:
                    self.__path[index - 1].icon.setVisible(True)
                    self.__path[index - 1].combo.setVisible(True)
                    combo = self.__path[index - 1].combo
                    combo.clear()

                self.__populateClassesAndFunctions(
                    context.levels[context.length - 1][0], combo)
                combo.setCurrentIndex(-1)
                usedFromStore += 1

        # Hide extra components if so
        index = usedFromStore
        while index < len(self.__path):
            self.__path[index].icon.setVisible(False)
            self.__path[index].combo.setVisible(False)
            index += 1

        # Make sure the spacer is the last item
        self.__layout.removeWidget(self.__spacer)
        self.__layout.addWidget(self.__spacer)

    def __populateGlobalScope(self):
        """Repopulates the global scope combo box"""
        self.__globalScopeCombo.clear()

        self.__populateClassesAndFunctions(self.__currentInfo,
                                           self.__globalScopeCombo)

        if not Settings()['navbarglobalsimports']:
            return

        if len(self.__currentInfo.globals) == 0 and \
           len(self.__currentInfo.imports) == 0:
            return

        if self.__globalScopeCombo.count() != 0:
            self.__globalScopeCombo.insertSeparator(
                self.__globalScopeCombo.count())

        for glob in self.__currentInfo.globals:
            self.__globalScopeCombo.addItem(getIcon('globalvar.png'),
                                            glob.name, glob.line)
        for imp in self.__currentInfo.imports:
            self.__globalScopeCombo.addItem(getIcon('imports.png'),
                                            imp.name, imp.line)

    @staticmethod
    def __populateClassesAndFunctions(infoObj, combo):
        """Populates the combo with classes and functions from the infoObj"""
        for klass in infoObj.classes:
            combo.addItem(getIcon('class.png'), klass.name, klass.line)
        for func in infoObj.functions:
            if func.isPrivate():
                icon = getIcon('method_private.png')
            elif func.isProtected():
                icon = getIcon('method_protected.png')
            else:
                icon = getIcon('method.png')
            combo.addItem(icon, func.name, func.line)

    def __cursorPositionChanged(self):
        """Cursor position changed"""
        self.__onNeedUpdate()

    def __onBufferChanged(self):
        """Buffer changed"""
        self.__onNeedUpdate()

    def __onNeedUpdate(self):
        """Triggered to update status icon and to restart the timer"""
        self.__updateTimer.stop()
        if self.__currentInfo.isOK:
            self.__updateInfoIcon(self.STATE_OK_CHN)
        else:
            self.__updateInfoIcon(self.STATE_BROKEN_CHN)
        self.__updateTimer.start(IDLE_TIMEOUT)

    def __onJumpToLine(self, line):
        """Triggered when it needs to jump to a line"""
        self.__editor.gotoLine(line, 0)
        self.__editor.setFocus()

    def setFocusToLastCombo(self):
        """Activates the last combo"""
        if self.__currentInfo is None:
            return
        for index in range(len(self.__path) - 1, -1, -1):
            if self.__path[index].combo.isVisible():
                self.__path[index].combo.setFocus()
                self.__path[index].combo.showPopup()
                return

        self.__globalScopeCombo.setFocus()
        self.__globalScopeCombo.showPopup()

    def activateCombo(self, currentCombo, newIndex):
        """Triggered when a neighbour combo should be activated"""
        if newIndex == -1:
            if len(self.__path) > 0:
                if self.__path[0].combo.isVisible():
                    currentCombo.hidePopup()
            self.__globalScopeCombo.setFocus()
            self.__globalScopeCombo.showPopup()
            return

        if newIndex >= len(self.__path):
            # This is the most right one
            return

        if self.__path[newIndex].combo.isVisible():
            currentCombo.hidePopup()
            self.__path[newIndex].combo.setFocus()
            self.__path[newIndex].combo.showPopup()
