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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""The real main widget - tab bar with editors"""

import logging
import os
import os.path
from utils.pixmapcache import getIcon
from utils.misc import getNewFileTemplate
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import (getFileProperties, isImageViewable,
                             isPythonMime, isPythonFile,
                             getXmlSyntaxFileByMime, isFileSearchable,
                             isMarkdownMime)
from utils.diskvaluesrelay import (getFilePosition, updateFilePosition,
                                   addRecentFile, getCollapsedGroups,
                                   setCollapsedGroups)
from utils.encoding import detectEolString
from diagram.importsdgmgraphics import ImportDgmTabWidget
from editor.vcsannotateviewer import VCSAnnotateViewerTabWidget
from editor.texteditortabwidget import TextEditorTabWidget
from .qt import (Qt, QDir, QUrl, pyqtSignal, QIcon, QTabWidget,
                 QDialog, QMessageBox, QWidget, QHBoxLayout, QMenu,
                 QToolButton, QShortcut, QFileDialog, QApplication, QTabBar)
from .welcomewidget import WelcomeWidget
from .helpwidget import QuickHelpWidget
from .pixmapwidget import PixmapTabWidget
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .tabshistory import TabsHistory
from .mdviewer import MarkdownTabWidget


class ClickableTabBar(QTabBar):

    """Intercepts clicking on the toolbar"""

    sigCurrentTabClicked = pyqtSignal()

    def __init__(self, parent):
        QTabBar.__init__(self, parent)

    def mousePressEvent(self, event):
        """Intercepts clicking on the toolbar and emits a signal.

        It is used to transfer focus to the currently active tab editor.
        """
        tabBarPoint = self.mapTo(self, event.pos())
        if self.tabAt(tabBarPoint) == self.currentIndex():
            self.sigCurrentTabClicked.emit()
        QTabBar.mousePressEvent(self, event)

    def focusInEvent(self, event):
        """Passes focus to the current tab"""
        del event   # unused argument
        self.parent().setFocus()


class EditorsManager(QTabWidget):

    """Tab bar with editors"""

    sigBufferModified = pyqtSignal(str, str)
    sigTabRunChanged = pyqtSignal(bool)
    sigPluginContextMenuAdded = pyqtSignal(QMenu, int)
    sigPluginContextMenuRemoved = pyqtSignal(QMenu, int)
    sigTabClosed = pyqtSignal(str)
    sigFileUpdated = pyqtSignal(str, str)
    sigBufferSavedAs = pyqtSignal(str, str)
    sigFileTypeChanged = pyqtSignal(str, str, str)
    sigTextEditorTabAdded = pyqtSignal(int)

    def __init__(self, parent, debugger):
        QTabWidget.__init__(self, parent)

        self.__debugger = debugger

        self.setTabBar(ClickableTabBar(self))
        self.setMovable(True)

        self.__newIndex = -1
        self.newCloneIndex = -1
        self.__mainWindow = parent
        self.__navigationMenu = None
        self.__historyBackMenu = None
        self.__historyFwdMenu = None
        self.__skipHistoryUpdate = False
        self.__doNotSaveTabs = False
        self.__restoringTabs = False
        self.navigationButton = None
        self.historyBackButton = None
        self.historyFwdButton = None
        self.createNavigationButtons()

        self.__debugMode = False
        self.__debugScript = ""     # If a single script is debugged
        self.__createdWithinDebugSession = []
        self.__mainWindow.debugModeChanged.connect(self.__onDebugMode)

        # Auxiliary widgets - they are created in the main window
        self.findReplaceWidget = None
        self.gotoWidget = None

        self.history = TabsHistory(self)
        self.history.historyChanged.connect(self.__onHistoryChanged)

        self.__welcomeWidget = WelcomeWidget()
        self.addTab(self.__welcomeWidget,
                    self.__welcomeWidget.getShortName())
        self.__welcomeWidget.sigEscapePressed.connect(self.__onESC)

        self.__helpWidget = QuickHelpWidget()
        self.__helpWidget.sigEscapePressed.connect(self.__onESC)

        self.__updateControls()
        self.__installActions()
        self.updateStatusBar()

        self.tabCloseRequested.connect(self.__onCloseRequest)
        self.currentChanged.connect(self.__currentChanged)

        Settings().sigTextZoomChanged.connect(self.onTextZoomChanged)
        Settings().sigFlowZoomChanged.connect(self.onFlowZoomChanged)

        # Context menu
        self.__tabContextMenu = QMenu(self)
        self.__highlightInPrjAct = self.__tabContextMenu.addAction(
            getIcon("highlightmenu.png"), "&Highlight in project browser",
            self.onHighlightInPrj)
        self.__highlightInFSAct = self.__tabContextMenu.addAction(
            getIcon("highlightmenu.png"), "H&ighlight in file system browser",
            self.onHighlightInFS)
        self.__tabContextMenu.addSeparator()
        self.__cloneAct = self.__tabContextMenu.addAction(
            getIcon("clonetabmenu.png"), "&Clone", self.onClone)
        self.__copyFullPathAct = self.__tabContextMenu.addAction(
            getIcon("copymenu.png"), "Copy full &path to clipboard",
            self.__copyTabFullPath)
        self.__copyDirPathAct = self.__tabContextMenu.addAction(
            getIcon(""), "Copy directory p&ath to clipboard",
            self.__copyTabDirPath)
        self.__copyFileNameAct = self.__tabContextMenu.addAction(
            getIcon(""), "Copy &file name to clipboard",
            self.__copyTabFileName)
        self.__reloadAct = self.__tabContextMenu.addAction(
            getIcon("reload.png"), "&Reload", self.onReload)
        self.__closeOtherAct = self.__tabContextMenu.addAction(
            getIcon(""), "Close oth&er tabs", self.onCloseOther)
        self.__tabContextMenu.addSeparator()
        self.__delCurrentAct = self.__tabContextMenu.addAction(
            getIcon("trash.png"), "Close and &delete from disk",
            self.__closeDelete)
        self.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(
            self.__showTabContextMenu)
        self.tabBar().sigCurrentTabClicked.connect(self.__currentTabClicked)

        # Plugins context menus support
        self.__pluginMenus = {}
        GlobalData().pluginManager.sigPluginActivated.connect(
            self.__onPluginActivated)
        GlobalData().pluginManager.sigPluginDeactivated.connect(
            self.__onPluginDeactivated)

        self.__mainWindow.vcsManager.sigVCSFileStatus.connect(
            self.__onVCSStatus)

    def __currentTabClicked(self):
        """Triggered when the currently active tab is clicked"""
        if self.count() > 0:
            self.widget(self.currentIndex()).setFocus()
            self._updateIconAndTooltip(self.currentIndex())

    def setFocus(self):
        """Explicitly sets focus to the current widget"""
        widget = self.currentWidget()
        if widget is not None:
            widget.setFocus()

    def isHighlightInPrjAvailable(self):
        """Returns True if highlight in project should be enabled"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType not in [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.PictureViewer]:
            return False
        fName = widget.getFileName()
        return os.path.isabs(fName) and \
               GlobalData().project.isLoaded() and \
               GlobalData().project.isProjectFile(fName)

    def isHighlightInFSAvailable(self):
        """Returns True if the highlight in FS should be enabled"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType not in [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.PictureViewer]:
            return False
        fName = widget.getFileName()
        return os.path.isabs(fName)

    def __showTabContextMenu(self, pos):
        """Shows a context menu if required"""
        clickedIndex = self.tabBar().tabAt(pos)
        tabIndex = self.currentIndex()

        if tabIndex == clickedIndex:
            widget = self.widget(tabIndex)
            widgetType = widget.getType()
            if widgetType not in [MainWindowTabWidgetBase.PlainTextEditor,
                                  MainWindowTabWidgetBase.PictureViewer]:
                return

            fName = widget.getFileName()
            self.__cloneAct.setEnabled(
                widgetType == MainWindowTabWidgetBase.PlainTextEditor)
            self.__closeOtherAct.setEnabled(self.closeOtherAvailable())
            self.__copyFullPathAct.setEnabled(fName != "")
            self.__copyDirPathAct.setEnabled(fName != "")
            self.__copyFileNameAct.setEnabled(fName != "")
            self.__delCurrentAct.setEnabled(fName != "")
            self.__highlightInPrjAct.setEnabled(
                self.isHighlightInPrjAvailable())
            self.__highlightInFSAct.setEnabled(
                self.isHighlightInFSAvailable())

            if fName != "":
                if not widget.doesFileExist():
                    self.__reloadAct.setText("&Reload")
                    self.__reloadAct.setEnabled(False)
                elif widget.isModified():
                    self.__reloadAct.setText("&Reload losing changes")
                    self.__reloadAct.setEnabled(True)
                else:
                    self.__reloadAct.setText("&Reload")
                    self.__reloadAct.setEnabled(True)
            else:
                # There is no full file name yet, so nothing to reload
                self.__reloadAct.setText("&Reload")
                self.__reloadAct.setEnabled(False)
            self.__tabContextMenu.popup(self.mapToGlobal(pos))

    def closeOtherAvailable(self):
        """True if the menu option is available"""
        return self.widget(0) != self.__welcomeWidget and self.count() > 1

    def __copyTabFullPath(self):
        """Triggered when copy path to clipboard item is selected"""
        QApplication.clipboard().setText(
            self.widget(self.currentIndex()).getFileName())

    def __copyTabDirPath(self):
        """Triggered when copy dir path to clipboard is selected"""
        QApplication.clipboard().setText(
            os.path.dirname(self.widget(self.currentIndex()).getFileName()) +
            os.path.sep)

    def __copyTabFileName(self):
        """Triggered when copy the file name to clipboard is selected"""
        QApplication.clipboard().setText(
            os.path.basename(self.widget(self.currentIndex()).getFileName()))

    def __closeDelete(self):
        """Triggered when the current tab is requested to be closed and the
           loaded file deleted from the disk
        """
        tabIndex = self.currentIndex()
        widget = self.widget(tabIndex)
        fileName = widget.getFileName()

        res = QMessageBox.warning(
            self, "Close tab and delete",
            "<p>Are you sure to close the tab and delete "
            "<b>" + fileName + "</b> from the disk?</p>",
            QMessageBox.StandardButtons(QMessageBox.Cancel | QMessageBox.Yes),
            QMessageBox.Cancel)
        if res == QMessageBox.Cancel:
            return

        try:
            if os.path.exists(fileName):
                # Before deleting the file, remove all breakpoints if so
                if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
                    widget.getEditor().deleteAllBreakpoints()
                os.remove(fileName)
            else:
                logging.info("Could not find " + fileName +
                             " on the disk. Ignoring and closing tab.")
        except Exception as exc:
            logging.error(str(exc))
            return

        # Finally, close the tab
        self.__onCloseRequest(tabIndex, True)
        GlobalData().mainWindow.recentProjectsViewer.removeRecentFile(fileName)

    def onHighlightInPrj(self):
        """Triggered when the file is to be highlighted in a project tree"""
        if GlobalData().project.isLoaded():
            widget = self.currentWidget()
            widgetType = widget.getType()
            if widgetType in [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.PictureViewer]:
                fName = widget.getFileName()
                if os.path.isabs(fName):
                    GlobalData().mainWindow.highlightInPrj(fName)

    def onHighlightInFS(self):
        """Triggered when the file is to be highlighted in the FS tree"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType not in [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.PictureViewer]:
            fName = widget.getFileName()
            if os.path.isabs(fName):
                GlobalData().mainWindow.highlightInFS(fName)

    def onClone(self):
        """Triggered when a tab is requested for cloning"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType != MainWindowTabWidgetBase.PlainTextEditor:
            return

        editor = widget.getEditor()
        firstVisible = editor.firstVisibleLine()
        line, pos = editor.cursorPosition

        # Create a new tab
        self.newTabClicked(editor.text,
                           self.getNewCloneName(widget.getShortName()))

        # Put the cursor to the exact same position as it was in the cloned tab
        newWidget = self.currentWidget()
        newWidget.getEditor().gotoLine(line + 1, pos + 1, firstVisible + 1)

    def onCloseOther(self):
        """Triggered when all other tabs are requested to be closed"""
        notSaved = []
        toClose = []
        for index in range(self.count()):
            if index == self.currentIndex():
                continue
            if self.widget(index).isModified():
                notSaved.append(self.widget(index).getShortName())
            else:
                # The tab will be closed soon, so save the file position
                self.updateFilePosition(index)
                toClose.insert(0, index)

        if notSaved:
            # There are not saved files
            logging.error("Please close or save the modified files "
                          "explicitly (" + ", ".join(notSaved) + ")")

        for index in toClose:
            self.__onCloseRequest(index)

    def __installActions(self):
        """Installs various key combinations handlers"""
        findAction = QShortcut('Ctrl+F', self)
        findAction.activated.connect(self.onFind)
        replaceAction = QShortcut('Ctrl+R', self)
        replaceAction.activated.connect(self.onReplace)
        closeTabAction = QShortcut('Ctrl+F4', self)
        closeTabAction.activated.connect(self.onCloseTab)
        nextTabAction = QShortcut('Ctrl+PgUp', self)
        nextTabAction.activated.connect(self.__onPrevTab)
        flipTabAction = QShortcut('Ctrl+Tab', self)
        flipTabAction.activated.connect(self.__onFlipTab)
        prevTabAction = QShortcut('Ctrl+PgDown', self)
        prevTabAction.activated.connect(self.__onNextTab)
        gotoAction = QShortcut('Ctrl+G', self)
        gotoAction.activated.connect(self.onGoto)

    def registerAuxWidgets(self, findReplace, goto):
        """Memorizes references to the auxiliary widgets"""
        self.findReplaceWidget = findReplace
        self.gotoWidget = goto

    def getNewName(self):
        """Provides a dummy name for the new tab file"""
        dirName = str(self.__getDefaultSaveDir())
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep

        while True:
            self.__newIndex += 1
            candidate = "unnamed" + str(self.__newIndex) + ".py"
            if not os.path.exists(dirName + candidate):
                return candidate

    def getNewDisassemblyName(self, path):
        """Provides a dummy name for a new tab disassembly"""
        basename = os.path.basename(path)
        candidate = basename + '.dis'
        index = -1
        while True:
            for _, _, editor in self.getTextEditors():
                if os.path.basename(editor.getShortName()) == candidate:
                    break
            else:
                return candidate
            index += 1
            candidate = basename + '.' + str(index) + '.dis'

    def getNewCloneName(self, shortName):
        """Provides a new name for a cloned file"""
        self.newCloneIndex += 1
        if '.' in shortName:
            parts = shortName.split('.')
            name = '.'.join(parts[0:len(parts) - 1])
            ext = parts[-1]
            return name + "-clone" + str(self.newCloneIndex) + "." + ext

        # No '.' in the name
        return shortName + "-clone" + str(self.newCloneIndex)

    def activateTab(self, index):
        """Activates the given tab"""
        self.setCurrentIndex(index)
        self.currentWidget().setFocus()

    def __onNextTab(self):
        """Triggers when Ctrl+PgUp is received"""
        count = self.count()
        if count > 1:
            newIndex = self.currentIndex() + 1
            if newIndex >= count:
                newIndex = 0
            self.activateTab(newIndex)

    def __onPrevTab(self):
        """triggers when Ctrl+PgDown is received"""
        count = self.count()
        if count > 1:
            newIndex = self.currentIndex() - 1
            if newIndex < 0:
                newIndex = count - 1
            self.activateTab(newIndex)

    def newTabClicked(self, initialContent=None, shortName=None,
                      mime=None):
        """new tab click handler"""
        if self.widget(0) == self.__welcomeWidget:
            # It is the only welcome widget on the screen
            self.removeTab(0)
            self.setTabsClosable(True)

        newWidget = TextEditorTabWidget(self, self.__debugger)
        newWidget.sigReloadRequest.connect(self.onReload)
        newWidget.reloadAllNonModifiedRequest.connect(
            self.onReloadAllNonModified)
        newWidget.sigTabRunChanged.connect(self.onTabRunChanged)
        editor = newWidget.getEditor()
        if shortName is None:
            newWidget.setShortName(self.getNewName())
        else:
            newWidget.setShortName(shortName)

        if mime is None:
            editor.mime, _, xmlSyntaxFile = \
                getFileProperties(newWidget.getShortName())
        else:
            editor.mime = mime
            xmlSyntaxFile = getXmlSyntaxFileByMime(mime)

        if initialContent is None or isinstance(initialContent, bool):
            # Load a template content if available
            initialContent = getNewFileTemplate()
            if initialContent:
                editor.text = initialContent
                lineNo = len(editor.lines)
                editor.gotoLine(lineNo, len(editor.lines[lineNo - 1]) + 1)
        else:
            editor.text = initialContent

        editor.eol = detectEolString(editor.text)
        editor.encoding = None

        if xmlSyntaxFile:
            editor.detectSyntax(xmlSyntaxFile)

        editor.document().setModified(False)

        self.insertTab(0, newWidget, newWidget.getShortName())
        self.activateTab(0)

        self.__updateControls()
        self.__connectEditorWidget(newWidget)
        self.updateStatusBar()
        self.__cursorPositionChanged()
        editor.setFocus()
        editor.updateSettings()
        newWidget.updateStatus()
        self.setWidgetDebugMode(newWidget)

        self.sigFileTypeChanged.emit(newWidget.getShortName(),
                                     newWidget.getUUID(),
                                     editor.mime if editor.mime else '')
        self.sigTextEditorTabAdded.emit(0)

    def __updateControls(self):
        """Updates the navigation buttons status"""
        self.navigationButton.setEnabled(
            self.widget(0) != self.__welcomeWidget)

    def __onHistoryChanged(self):
        """historyChanged signal handler"""
        self.historyBackButton.setEnabled(self.history.backAvailable())
        self.historyFwdButton.setEnabled(self.history.forwardAvailable())

    def onCloseTab(self):
        """Triggered when Ctrl+F4 is received"""
        if self.widget(0) != self.__welcomeWidget:
            self.__onCloseRequest(self.currentIndex())

    def isTabClosable(self):
        """Returns True if the current TAB is closable"""
        return self.widget(0) != self.__welcomeWidget

    def __onCloseRequest(self, index, enforced=False):
        """Close tab handler"""
        # Note: it is not called when an IDE is closed
        #       but called when a project is changed

        wasDiscard = False
        if self.widget(index).isModified() and not enforced:
            # Ask the user if the changes should be discarded
            self.activateTab(index)
            widget = self.currentWidget()
            fileName = widget.getFileName()

            if fileName and widget.isDiskFileModified() and \
               widget.doesFileExist():
                # Both: the disk and the tab were modified
                self._updateIconAndTooltip(index)

                res = QMessageBox.warning(
                    widget, "Close Tab",
                    "<p>The file <b>" + fileName +
                    "</b> was modified by another process after it was opened "
                    "and modified in this tab.</p>"
                    "<p>Do you want to save the tab content "
                    "(potentially losing other changes) and close the tab, "
                    "discard your changes and close the tab or "
                    "cancel closing the tab?</p>",
                    QMessageBox.StandardButtons(
                        QMessageBox.Cancel | QMessageBox.Discard |
                        QMessageBox.Save),
                    QMessageBox.Save)

                if res == QMessageBox.Save:
                    if self.onSave(-1, True) != True:
                        # Failed to save
                        return
                if res == QMessageBox.Cancel:
                    return
                wasDiscard = res == QMessageBox.Discard
            else:
                # The case when the disk file is the same as the currently
                # loaded
                res = QMessageBox.warning(
                    widget, "Close Tab",
                    "<p>The tab content was modified.</p>"
                    "<p>Do you want to save the tab content and close, "
                    "discard your changes and close the tab or "
                    "cancel closing the tab?</p>",
                    QMessageBox.StandardButtons(
                        QMessageBox.Cancel | QMessageBox.Discard |
                        QMessageBox.Save),
                    QMessageBox.Save)
                if res == QMessageBox.Save:
                    if self.onSave() != True:
                        # Failed to save
                        return
                if res == QMessageBox.Cancel:
                    return
                wasDiscard = res == QMessageBox.Discard

        # Here:
        # - the user decided to discard changes
        # - the changes were saved successfully
        # - there were no changes

        widgetType = self.widget(index).getType()
        if widgetType == MainWindowTabWidgetBase.PlainTextEditor:
            # Check the breakpoints validity
            self.widget(index).getEditor().validateBreakpoints()

        if not wasDiscard and not enforced:
            self.updateFilePosition(index)

        if widgetType in [MainWindowTabWidgetBase.PlainTextEditor,
                          MainWindowTabWidgetBase.VCSAnnotateViewer]:
            # Terminate the syntax highlight if needed
            editor = self.widget(index).getEditor()
            editor.textChanged.disconnect(self.__contentChanged)
            editor.terminate()

        closingUUID = self.widget(index).getUUID()

        # Check if it is necessary to add a file to the recent history
        if widgetType in [MainWindowTabWidgetBase.PlainTextEditor,
                          MainWindowTabWidgetBase.PictureViewer]:
            # Yes, it needs to be saved if it was saved at least once
            fileName = self.widget(index).getFileName()
            if os.path.isabs(fileName) and os.path.exists(fileName):
                addRecentFile(fileName)

        self.__skipHistoryUpdate = True
        self.removeTab(index)

        if self.count() == 0:
            self.setTabsClosable(False)
            self.addTab(self.__welcomeWidget,
                        self.__welcomeWidget.getShortName())
            self.__welcomeWidget.setFocus()
            self.gotoWidget.hide()
            self.findReplaceWidget.hide()
            self.history.clear()
        else:
            # Need to identify a tab for displaying
            self.history.tabClosed(closingUUID)
            if self.history.getCurrentIndex() == -1:
                # There is nothing in the history yet
                self.history.addCurrent()
            else:
                self.__activateHistoryTab()

        self.__skipHistoryUpdate = False
        self.__updateControls()
        self.saveTabsStatus()
        self.sigTabClosed.emit(closingUUID)

    def updateFilePosition(self, index):
        """Updates the file position of a file loaded to the given tab"""
        if index is None:
            widget = self.currentWidget()
        else:
            widget = self.widget(index)
        fileName = widget.getFileName()
        if fileName is None or not os.path.isabs(fileName):
            return
        if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            # Save the current cursor position
            editor = widget.getEditor()
            line, pos = editor.cursorPosition

            scrollHPos = -1
            scrollVPos = -1
            if isPythonMime(widget.getMime()):
                cfEditor = widget.getCFEditor()
                scrollHPos, scrollVPos = cfEditor.getScrollbarPositions()
            elif isMarkdownMime(widget.getMime()):
                mdView = widget.getMDView()
                scrollHPos, scrollVPos = mdView.getScrollbarPositions()

            updateFilePosition(
                fileName, line, pos, editor.firstVisibleLine(),
                scrollHPos, scrollVPos)

    def restoreFilePosition(self, index):
        """Restores the file position"""
        if index is None:
            widget = self.currentWidget()
        else:
            widget = self.widget(index)
        if not os.path.isabs(widget.getFileName()):
            return
        if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            line, pos, firstVisible, _, _ = \
                getFilePosition(widget.getFileName())
            editor = widget.getEditor()
            if line != -1:
                editor.gotoLine(line + 1, pos + 1, firstVisible + 1)
            else:
                editor.gotoLine(1, 1, 1)

    def createNavigationButtons(self):
        """Creates widgets navigation button at the top corners"""
        rightCornerWidget = QWidget(self)
        rightCornerWidgetLayout = QHBoxLayout(rightCornerWidget)
        rightCornerWidgetLayout.setContentsMargins(0, 0, 0, 0)
        rightCornerWidgetLayout.setSpacing(0)

        self.__navigationMenu = QMenu(self)
        self.__navigationMenu.aboutToShow.connect(self.__showNavigationMenu)
        self.__navigationMenu.triggered.connect(self.__navigationMenuTriggered)

        newTabButton = QToolButton(self)
        newTabButton.setIcon(getIcon("newfiletab.png"))
        newTabButton.setToolTip("New file (Ctrl+N)")
        newTabButton.setEnabled(True)
        newTabButton.clicked.connect(self.newTabClicked)
        rightCornerWidgetLayout.addWidget(newTabButton)
        self.navigationButton = QToolButton(self)
        self.navigationButton.setIcon(getIcon("1downarrow.png"))
        self.navigationButton.setToolTip("List the open tabs")
        self.navigationButton.setPopupMode(QToolButton.InstantPopup)
        self.navigationButton.setMenu(self.__navigationMenu)
        self.navigationButton.setEnabled(False)
        rightCornerWidgetLayout.addWidget(self.navigationButton)

        self.setCornerWidget(rightCornerWidget, Qt.TopRightCorner)

        self.__historyBackMenu = QMenu(self)
        self.__historyBackMenu.aboutToShow.connect(self.__showHistoryBackMenu)
        self.__historyBackMenu.triggered.connect(self.__historyMenuTriggered)

        self.__historyFwdMenu = QMenu(self)
        self.__historyFwdMenu.aboutToShow.connect(self.__showHistoryFwdMenu)
        self.__historyFwdMenu.triggered.connect(self.__historyMenuTriggered)

        leftCornerWidget = QWidget(self)
        leftCornerWidgetLayout = QHBoxLayout(leftCornerWidget)
        leftCornerWidgetLayout.setContentsMargins(0, 0, 0, 0)
        leftCornerWidgetLayout.setSpacing(0)
        self.historyBackButton = QToolButton(self)
        self.historyBackButton.setIcon(getIcon("1leftarrow.png"))
        self.historyBackButton.setToolTip("Back (Alt+PgDown)")
        self.historyBackButton.setShortcut("Alt+PgDown")
        self.historyBackButton.setPopupMode(QToolButton.DelayedPopup)
        self.historyBackButton.setMenu(self.__historyBackMenu)
        self.historyBackButton.setEnabled(False)
        self.historyBackButton.clicked.connect(self.historyBackClicked)
        leftCornerWidgetLayout.addWidget(self.historyBackButton)
        self.historyFwdButton = QToolButton(self)
        self.historyFwdButton.setIcon(getIcon("1rightarrow.png"))
        self.historyFwdButton.setToolTip("Forward (Alt+PgUp)")
        self.historyFwdButton.setShortcut("Alt+PgUp")
        self.historyFwdButton.setPopupMode(QToolButton.DelayedPopup)
        self.historyFwdButton.setMenu(self.__historyFwdMenu)
        self.historyFwdButton.setEnabled(False)
        self.historyFwdButton.clicked.connect(self.historyForwardClicked)
        leftCornerWidgetLayout.addWidget(self.historyFwdButton)

        self.setCornerWidget(leftCornerWidget, Qt.TopLeftCorner)

    def __showNavigationMenu(self):
        """Shows the navigation button menu"""
        self.__navigationMenu.clear()
        items = []
        for index in range(self.count()):
            items.append([self.tabIcon(index), self.tabText(index), index])

        if Settings()['tablistsortalpha']:
            items.sort(key=lambda c: c[1])
        else:
            items.sort(key=lambda c: c[2])

        for item in items:
            act = self.__navigationMenu.addAction(item[0], item[1])
            index = item[2]
            act.setData(index)
            if self.currentIndex() == index:
                font = act.font()
                font.setBold(True)
                act.setFont(font)

    def __navigationMenuTriggered(self, act):
        """Handles the navigation button menu selection"""
        index = act.data()
        if self.currentIndex() == index:
            return

        if Settings()['taborderpreserved']:
            self.activateTab(index)
        else:
            if index != 0:
                # Memorize the tab attributes
                tooltip = self.tabToolTip(index)
                text = self.tabText(index)
                icon = self.tabIcon(index)
                whatsThis = self.tabWhatsThis(index)
                widget = self.widget(index)

                # Remove the tab from the old position
                self.removeTab(index)

                # Insert the tab at position 0
                self.insertTab(0, widget, icon, text)
                self.setTabToolTip(0, tooltip)
                self.setTabWhatsThis(0, whatsThis)
            self.activateTab(0)

    def __currentChanged(self, index):
        """Handles the currentChanged signal"""
        GlobalData().mainWindow.clearStatusBarMessage()

        if index == -1:
            self.sigTabRunChanged.emit(False)
            return

        self._updateIconAndTooltip(self.currentIndex())
        self.updateStatusBar()

        self.gotoWidget.updateStatus()
        self.findReplaceWidget.updateStatus()

        widget = self.currentWidget()
        widget.setFocus()

        # Update history
        if not self.__skipHistoryUpdate:
            if self.widget(0) != self.__welcomeWidget:
                # No need to update history when there is only welcome widget
                self.history.updateForCurrentIndex()
                self.history.addCurrent()

        if widget.doesFileExist():
            if widget.isDiskFileModified():
                if not widget.getReloadDialogShown():
                    widget.showOutsideChangesBar(
                        self.__countDiskModifiedUnchanged() > 1)
                    # Just in case check the other tabs
                    self.checkOutsideFileChanges()

        if widget.getType() != MainWindowTabWidgetBase.PlainTextEditor:
            self.sigTabRunChanged.emit(False)
        else:
            # This is a text editor with flow UI
            self.sigTabRunChanged.emit(widget.isTabRunEnabled())
            if widget.getCFEditor().dirty():
                selection = widget.getCFEditor().scene().serializeSelection()
                widget.getCFEditor().process()
                widget.getCFEditor().scene().restoreSelectionByTooltip(selection)

    def onHelp(self):
        """Triggered when F1 is received"""
        shortName = self.__helpWidget.getShortName()
        # Check if it is already opened
        for index in range(self.count()):
            if self.widget(index).getShortName() == shortName and \
               self.widget(index).getType() == \
                    MainWindowTabWidgetBase.HTMLViewer:
                # Found
                self.activateTab(index)
                return
        # Not found
        if self.widget(0) == self.__welcomeWidget:
            # It is the only welcome widget on the screen
            self.removeTab(0)
            self.setTabsClosable(True)
        self.addTab(self.__helpWidget, shortName)
        self.activateTab(self.count() - 1)

    @staticmethod
    def getFileDocstring(fileName):
        """Provides the file docstring"""
        if isPythonFile(fileName):
            try:
                info = GlobalData().briefModinfoCache.get(fileName)
                if info.docstring is not None:
                    return info.docstring.text
            except:
                pass
        return ""

    def _updateIconAndTooltip(self, widgetIndex, fileType=None):
        """Updates the current tab icon and tooltip after the file is saved"""
        widget = self.widget(widgetIndex)
        fileName = widget.getFileName()

        if fileName and os.path.isabs(fileName):
            # It makes sense to test if a file disappeared or modified
            if not widget.doesFileExist():
                self.setTabToolTip(widgetIndex,
                                   "The file does not exist on the disk")
                icon = getIcon('disappearedfile.png')
                self.setTabIcon(widgetIndex, icon)
                self.history.updateIconForTab(widget.getUUID(), icon)
                return
            if widget.isDiskFileModified():
                self.setTabToolTip(widgetIndex,
                                   "The file has been modified "
                                   "outside codimension")
                icon = getIcon('modifiedfile.png')
                self.setTabIcon(widgetIndex, icon)
                self.history.updateIconForTab(widget.getUUID(), icon)
                return

        if fileType is None:
            fileType, _, _ = getFileProperties(fileName)
        if not isPythonMime(fileType):
            self.setTabIcon(widgetIndex, QIcon())
            self.setTabToolTip(widgetIndex, widget.getTooltip())
            self.history.updateIconForTab(widget.getUUID(), QIcon())
            return

        try:
            info = GlobalData().getModInfo(fileName)
            if info.errors  or info.lexerErrors:
                icon = getIcon('filepythonbroken.png')
                self.setTabIcon(widgetIndex, icon)
                self.setTabToolTip(widgetIndex,
                                   "The disk version of file "
                                   "has parsing errors")
                self.history.updateIconForTab(widget.getUUID(), icon)
            else:
                self.setTabIcon(widgetIndex, QIcon())
                self.history.updateIconForTab(widget.getUUID(), QIcon())

                if info.docstring is not None and Settings()['editorTooltips']:
                    self.setTabToolTip(widgetIndex, info.docstring.text)
                else:
                    self.setTabToolTip(widgetIndex, "")
        except:
            self.setTabToolTip(widgetIndex, "")
            icon = getIcon('filepythonbroken.png')
            self.setTabIcon(widgetIndex, icon)
            self.history.updateIconForTab(widget.getUUID(), icon)

    def openMarkdownFullView(self, fileName, readOnly=True):
        """Shows the given markdown file in a full view"""
        try:
            # Check if the file is already opened
            for index in range(self.count()):
                if self.widget(index).getFileName() == fileName:
                    self.activateTab(index)
                    return True
            # Not found - create a new one
            newWidget = MarkdownTabWidget(readOnly, self)
            newWidget.sigEscapePressed.connect(self.__onESC)

            if self.widget(0) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab(0)
                self.setTabsClosable(True)

            self.insertTab(0, newWidget, newWidget.getShortName())
            self.activateTab(0)
            self.__updateControls()
            self.updateStatusBar()
            newWidget.setFocus()
            newWidget.setFileName(fileName)
            self.saveTabsStatus()
            if not self.__restoringTabs:
                if not readOnly:
                    addRecentFile(fileName)
            self.setWidgetDebugMode(newWidget)
        except Exception as exc:
            logging.error(str(exc))
            return False
        return True

    def openPixmapFile(self, fileName):
        """Shows the required picture"""
        try:
            # Check if the file is already opened
            for index in range(self.count()):
                if self.widget(index).getFileName() == fileName:
                    # Found
                    self.activateTab(index)
                    return True
            # Not found - create a new one
            newWidget = PixmapTabWidget(self)
            newWidget.sigEscapePressed.connect(self.__onESC)
            newWidget.reloadRequst.connect(self.onReload)
            newWidget.reloadAllNonModifiedRequest.connect(self.onReloadAllNonModified)

            newWidget.loadFromFile(fileName)

            if self.widget(0) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab(0)
                self.setTabsClosable(True)

            self.insertTab(0, newWidget, newWidget.getShortName())
            self.activateTab(0)
            self.__updateControls()
            self.updateStatusBar()
            newWidget.setFocus()
            self.saveTabsStatus()
            if not self.__restoringTabs:
                addRecentFile(fileName)
            self.setWidgetDebugMode(newWidget)
        except Exception as exc:
            logging.error(str(exc))
            return False
        return True

    def openDiagram(self, scene, tooltip):
        """Opens a tab with a graphics scene on it"""
        try:
            newWidget = ImportDgmTabWidget()
            newWidget.sigEscapePressed.connect(self.__onESC)
            newWidget.setScene(scene)

            if self.widget(0) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab(0)
                self.setTabsClosable(True)

            self.insertTab(0, newWidget, newWidget.getShortName())
            if tooltip != "":
                self.setTabToolTip(0, tooltip)
                newWidget.setTooltip(tooltip)
            self.activateTab(0)
            self.__updateControls()
            self.updateStatusBar()
            newWidget.setFocus()
            self.saveTabsStatus()
        except Exception as exc:
            logging.error(str(exc))
            return False
        return True

    def showProfileReport(self, newWidget, tooltip):
        """Shows profiling report"""
        try:
            newWidget.sigEscapePressed.connect(self.__onESC)

            if self.widget(0) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab(0)
                self.setTabsClosable(True)

            self.insertTab(0, newWidget, newWidget.getShortName())
            if tooltip != "":
                self.setTabToolTip(0, tooltip)
                newWidget.setTooltip(tooltip)
            self.activateTab(0)
            self.__updateControls()
            self.updateStatusBar()
            newWidget.setFocus()
            self.saveTabsStatus()
        except Exception as exc:
            logging.error(str(exc))

    def showDisassembly(self, scriptPath, disassembly):
        """Shows the disassembled code"""
        self.newTabClicked(disassembly,
                           self.getNewDisassemblyName(scriptPath),
                           mime='text/plain')

    def showAnnotated(self, fileName, text, lineRevisions, revisionInfo):
        """Shows the annotated text widget"""
        try:
            parts = os.path.basename(fileName).split('.')
            parts[0] += "-annotate"
            shortName = ".".join(parts)
            tooltip = "Annotated file: " + fileName

            mime, _, _ = getFileProperties(fileName)

            newWidget = VCSAnnotateViewerTabWidget(self)
            newWidget.setFileType(mime)
            newWidget.sigEscapePressed.connect(self.__onESC)

            newWidget.setAnnotatedContent(shortName, text, lineRevisions,
                                          revisionInfo)
            if self.widget(0) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab(0)
                self.setTabsClosable(True)

            self.insertTab(0, newWidget, newWidget.getShortName())
            self.setTabToolTip(0, tooltip)
            newWidget.setTooltip(tooltip)
            self.activateTab(0)
            self.__updateControls()
            self.__connectEditorWidget(newWidget)
            self.updateStatusBar()
            newWidget.setFocus()
            newWidget.getEditor().gotoLine(1, 1)
            self.saveTabsStatus()
        except Exception as exc:
            logging.error(str(exc))

    def jumpToLine(self, lineNo):
        """Jumps to the given line within the current buffer"""
        self.history.updateForCurrentIndex()

        self.currentWidget().getEditor().gotoLine(lineNo)

        self.history.addCurrent()
        self.currentWidget().setFocus()

    def openFile(self, fileName, lineNo, pos=0):
        """Opens the required file"""
        if not fileName:
            return
        if not isFileSearchable(fileName):
            return
        try:
            fileName = os.path.realpath(fileName)
            # Check if the file is already opened
            for index in range(self.count()):
                if self.widget(index).getFileName() == fileName:
                    # Found
                    if self.currentIndex() == index:
                        self.history.updateForCurrentIndex()
                    if lineNo > 0:
                        editor = self.widget(index).getEditor()
                        editor.gotoLine(lineNo, pos)
                    self.activateTab(index)
                    if self.currentIndex() == index:
                        self.history.addCurrent()
                    return True

            # Not found - create a new one
            newWidget = TextEditorTabWidget(self, self.__debugger)
            newWidget.sigReloadRequest.connect(self.onReload)
            newWidget.reloadAllNonModifiedRequest.connect(
                self.onReloadAllNonModified)
            newWidget.sigTabRunChanged.connect(self.onTabRunChanged)
            newWidget.readFile(fileName)

            if self.widget(0) == self.__welcomeWidget:
                # It is the only welcome widget on the screen
                self.removeTab(0)
                self.setTabsClosable(True)

            self.insertTab(0, newWidget, newWidget.getShortName())
            self.activateTab(0)

            editor = newWidget.getEditor()

            self._updateIconAndTooltip(self.currentIndex(), editor.mime)
            self.__updateControls()
            self.__connectEditorWidget(newWidget)
            self.updateStatusBar()
            self.__cursorPositionChanged()
            editor.setFocus()
            newWidget.updateStatus()
            self.saveTabsStatus()
            if not self.__restoringTabs:
                addRecentFile(fileName)
            self.setWidgetDebugMode(newWidget)

            self.sigFileTypeChanged.emit(fileName, newWidget.getUUID(),
                                         editor.mime if editor.mime else '')
            QApplication.processEvents()
            if lineNo > 0:
                # Jump to the asked line
                editor.gotoLine(lineNo, pos)
            else:
                self.restoreFilePosition(None)
            self.sigTextEditorTabAdded.emit(0)

        except Exception as exc:
            logging.error(str(exc))
            return False
        return True

    def gotoInBuffer(self, uuid, lineNo, pos=0):
        """Jumps to the given line in the current buffer if it matches uuid"""
        widget = self.currentWidget()
        if widget.getUUID() == uuid:
            self.history.updateForCurrentIndex()
            widget.getEditor().gotoLine(lineNo, pos)
            self.history.addCurrent()
            widget.setFocus()

    def onSave(self, index=-1, forced=False):
        """Triggered when Ctrl+S is received"""
        if index == -1:
            widget = self.currentWidget()
            index = self.currentIndex()
            widgetType = widget.getType()

            if widgetType == MainWindowTabWidgetBase.GeneratedDiagram:
                return self.onSaveDiagramAs()
            if widgetType == MainWindowTabWidgetBase.ProfileViewer:
                if widget.isDiagramActive():
                    return self.onSaveDiagramAs()
                return self.onSaveCSVAs()
        else:
            widget = self.widget(index)
            widgetType = widget.getType()

        if widgetType == MainWindowTabWidgetBase.VCSAnnotateViewer:
            return self.onSaveAs(index)

        if widgetType != MainWindowTabWidgetBase.PlainTextEditor:
            return True

        # This is a text editor
        editor = widget.getEditor()
        fileName = widget.getFileName()
        if fileName:
            # This is the buffer which has the corresponding file on FS
            existedBefore = os.path.exists(fileName)
            if widget.isDiskFileModified() and \
               widget.doesFileExist() and not forced:
                if index != self.currentIndex():
                    self.activateTab(index)
                self._updateIconAndTooltip(index)
                widget.setReloadDialogShown(True)
                # The disk file was modified
                dlg = QMessageBox(
                    QMessageBox.Warning, "Save File",
                    "<p>The file <b>" + fileName +
                    "</b> was modified by another process after it was opened "
                    "in this tab, so by saving it you could potentially "
                    "overwrite other changes.</p>"
                    "<p>Do you want to save the tab content, "
                    "reload losing your changes, or cancel saving?</p>")
                dlg.addButton(QMessageBox.Cancel)
                dlg.addButton(QMessageBox.Save)
                dlg.addButton(QMessageBox.RestoreDefaults)
                btn = dlg.button(QMessageBox.RestoreDefaults)
                btn.setText("&Reload")
                dlg.setDefaultButton(QMessageBox.Cancel)
                res = dlg.exec_()

                if res == QMessageBox.Cancel:
                    return False
                if res == QMessageBox.RestoreDefaults:
                    # Need to reload from the disk
                    self.reloadTab(self.currentIndex())
                    return True
            else:
                # The disk file is the same as we read it
                if not editor.document().isModified() and widget.doesFileExist():
                    return True

            # Save the buffer into the file
            oldFileMime = widget.getMime()
            if not widget.writeFile(fileName):
                # Error saving
                return False

            # The disk access has happened anyway so it does not make sense
            # to save on one disk operation for detecting a file type.
            # It could be changed due to a symlink or due to a newly populated
            # content like in .cgi files
            newFileMime, _, _ = getFileProperties(fileName, True, True)
            if oldFileMime != newFileMime:
                widget.setFileType(newFileMime)
                widget.getEditor().bindLexer(fileName, newFileMime)
                widget.updateStatus()
                self.updateStatusBar()
                self.__mainWindow.updateRunDebugButtons()
                self.sigFileTypeChanged.emit(
                    fileName, widget.getUUID(),
                    newFileMime if newFileMime else '')

            editor.document().setModified(False)
            self._updateIconAndTooltip(index)
            if GlobalData().project.fileName == fileName:
                GlobalData().project.onProjectFileUpdated()
            if existedBefore:
                # Otherwise the FS watcher will signal the changes
                self.sigFileUpdated.emit(fileName, widget.getUUID())
            self.__mainWindow.vcsManager.setLocallyModified(fileName)

            if isPythonMime(widget.getMime()):
                widget.getCFEditor().validateCollapsedGroups(fileName)
            return True

        # This is the new one - call Save As
        return self.onSaveAs(index)

    def __getDefaultSaveDir(self):
        """Provides the default directory to save files to"""
        project = GlobalData().project
        if project.isLoaded():
            return project.getProjectDir()
        return QDir.currentPath()

    def __getSaveAsDialog(self, title, nameFilter=None):
        """Creates the common save as dialog"""
        dialog = QFileDialog(self, title)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setLabelText(QFileDialog.Accept, 'Save')
        if nameFilter:
            dialog.setNameFilter(nameFilter)

        urls = []
        for dname in QDir.drives():
            urls.append(QUrl.fromLocalFile(dname.absoluteFilePath()))
        urls.append(QUrl.fromLocalFile(QDir.homePath()))
        project = GlobalData().project
        if project.isLoaded():
            urls.append(QUrl.fromLocalFile(project.getProjectDir()))
        dialog.setSidebarUrls(urls)

        dialog.setOption(QFileDialog.DontConfirmOverwrite, False)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        return dialog

    def __checkPermissionsOnSave(self, widget, fName):
        """Checks the common permissions before saving"""
        if os.path.isdir(fName):
            logging.error('A file must be selected')
            return False

        if os.path.exists(fName):
            if not os.access(fName, os.W_OK):
                logging.error('There is no write permissions for ' + fName)
                return False

            if widget.getFileName() != fName:
                if self.isFileOpened(fName):
                    QMessageBox.critical(
                        self, 'Save file', '<p>The file <b>' + fName +
                        '</b> is opened in another tab.</p>'
                        '<p>Cannot save under this name.')
                    return False
                else:
                    res = QMessageBox.warning(
                        self, 'Save as is about to overwrite existing file',
                        '<p>The file <b>' + fName + '</b> already exists.</p>',
                        QMessageBox.StandardButtons(QMessageBox.Abort |
                                                    QMessageBox.Save),
                        QMessageBox.Abort)
                    if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                        return False
        else:
            # Check write permissions to the directory
            dirName = os.path.dirname(fName)
            if not os.access(dirName, os.W_OK):
                logging.error('There is no write permissions for the '
                              'directory ' + dirName)
                return False
        return True

    def onSaveAs(self, index=-1):
        """Triggered when Ctrl+Shift+S is received"""
        if index == -1:
            widget = self.currentWidget()
            index = self.currentIndex()
            widgetType = widget.getType()

            if widgetType == MainWindowTabWidgetBase.GeneratedDiagram:
                return self.onSaveDiagramAs()
            if widgetType == MainWindowTabWidgetBase.ProfileViewer:
                if widget.isDiagramActive():
                    return self.onSaveDiagramAs()
                return self.onSaveCSVAs()
        else:
            widget = self.widget(index)
            widgetType = widget.getType()

        if widgetType not in [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.VCSAnnotateViewer]:
            return True

        if index != self.currentIndex():
            self.activateTab(index)

        dialog = self.__getSaveAsDialog('Save file as...')

        if widget.getFileName().lower() in ['', 'n/a']:
            newFile = True
            oldShortName = widget.getShortName()
            collapsedGroups = getCollapsedGroups(oldShortName)
            dialog.setDirectory(self.__getDefaultSaveDir())
            dialog.selectFile(widget.getShortName())
        else:
            newFile = False
            collapsedGroups = getCollapsedGroups(widget.getFileName())
            dialog.setDirectory(os.path.dirname(widget.getFileName()))
            dialog.selectFile(os.path.basename(widget.getFileName()))

        if dialog.exec_() != QDialog.Accepted:
            return False

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath(str(fileNames[0]))

        if not self.__checkPermissionsOnSave(widget, fileName):
            return False

        oldType = widget.getMime()
        existedBefore = os.path.exists(fileName)

        # OK, the file name was properly selected
        if self.__debugMode and self.__debugScript == fileName:
            logging.error("Cannot overwrite a script "
                          "which is currently debugged.")
            return False

        if not widget.writeFile(fileName):
            # Failed to write, inform and exit
            return False

        # Sets the proper file name even if there were no changes in the
        # content
        self.setTabText(self.currentIndex(), widget.getShortName())

        if widgetType != MainWindowTabWidgetBase.VCSAnnotateViewer:
            editor = widget.getEditor()
            editor.document().setModified(False)
            newType, _, xmlSyntaxFile = getFileProperties(fileName, True, True)
            if newType != oldType or newType is None:
                editor.mime = newType
                editor.clearSyntax()
                if xmlSyntaxFile:
                    editor.detectSyntax(xmlSyntaxFile)
                editor.clearAnalysisMessages()
                self.sigFileTypeChanged.emit(fileName, widget.getUUID(),
                                             newType if newType else '')
            self._updateIconAndTooltip(index, newType)

        if GlobalData().project.fileName == fileName:
            GlobalData().project.onProjectFileUpdated()

        uuid = widget.getUUID()
        if existedBefore:
            self.sigFileUpdated.emit(fileName, uuid)
        else:
            if widgetType != MainWindowTabWidgetBase.VCSAnnotateViewer:
                self.sigBufferSavedAs.emit(fileName, uuid)
                addRecentFile(fileName)

        if widgetType != MainWindowTabWidgetBase.VCSAnnotateViewer:
            self.history.updateFileNameForTab(uuid, fileName)
            widget.updateStatus()
            self.updateStatusBar()
            self.__mainWindow.updateRunDebugButtons()
        self.__mainWindow.vcsManager.setLocallyModified(fileName)

        if self.__debugMode:
            self.__createdWithinDebugSession.append(fileName)
            self.setWidgetDebugMode(widget)

        # Update the collapsed groups information
        if isPythonMime(widget.getMime()):
            if newFile:
                setCollapsedGroups(oldShortName, None)
            setCollapsedGroups(fileName, collapsedGroups)
            widget.getCFEditor().validateCollapsedGroups(fileName)
        return True

    def onSaveDiagramAs(self):
        """Saves the current tab diagram to a file"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType not in [MainWindowTabWidgetBase.GeneratedDiagram,
                              MainWindowTabWidgetBase.ProfileViewer]:
            return
        if widgetType == MainWindowTabWidgetBase.ProfileViewer:
            if not widget.isDiagramActive():
                return

        dialog = self.__getSaveAsDialog('Save diagram as...',
                                        'PNG files (*.png)')
        dialog.setDirectory(self.__getDefaultSaveDir())
        if widgetType == MainWindowTabWidgetBase.GeneratedDiagram:
            dialog.selectFile("imports-diagram.png")
        elif widgetType == MainWindowTabWidgetBase.ProfileViewer:
            dialog.selectFile("profiling-diagram.png")
        else:
            dialog.selectFile("diagram.png")

        if dialog.exec_() != QDialog.Accepted:
            return False

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath(str(fileNames[0]))

        if os.path.isdir(fileName):
            logging.error("A file must be selected")
            return False

        if "." not in fileName:
            fileName += ".png"

        if not __checkPermissionsOnSave(widget, fileName):
            return False

        # All prerequisites are checked, save it
        try:
            widget.onSaveAs(fileName)
        except Exception as exc:
            logging.error(str(exc))
            return False
        return True

    def onSaveCSVAs(self):
        """Saves the current profiling results to a file"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType not in [MainWindowTabWidgetBase.ProfileViewer]:
            return
        if widget.isDiagramActive():
            return

        dialog = self.__getSaveAsDialog('Save data as CSV file...',
                                        'CSV files (*.csv)')
        dialog.setDirectory(self.__getDefaultSaveDir())
        dialog.selectFile("profiling-table.csv")
        if dialog.exec_() != QDialog.Accepted:
            return False

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath(str(fileNames[0]))

        if os.path.isdir(fileName):
            logging.error("A file must be selected")
            return False

        if "." not in fileName:
            fileName += ".csv"

        # Check permissions to write into the file or to a directory
        if not self.__checkPermissionsOnSave(widget, fileName):
            return False

        # All prerequisites are checked, save it
        try:
            widget.onSaveAs(fileName)
        except Exception as exc:
            logging.error(str(exc))
            return False
        return True

    def onFind(self):
        """Triggered when Ctrl+F is received"""
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        if self.currentWidget().getType() in validWidgets:
            self.gotoWidget.hide()

            editor = self.currentWidget().getEditor()
            word, _, startPos, _ = editor.getCurrentOrSelection()
            if word:
                editor.absCursorPosition = startPos
            self.findReplaceWidget.show(self.findReplaceWidget.MODE_FIND, word)

    def onReplace(self):
        """Triggered when Ctrl+R is received"""
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor]
        if self.currentWidget().getType() in validWidgets:
            self.gotoWidget.hide()

            editor = self.currentWidget().getEditor()
            word, _, startPos, _ = editor.getCurrentOrSelection()
            if word:
                editor.absCursorPosition = startPos
            self.findReplaceWidget.show(self.findReplaceWidget.MODE_REPLACE,
                                        word)

    def onGoto(self):
        """Triggered when Ctrl+G is received"""
        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.VCSAnnotateViewer]
        if self.currentWidget().getType() in validWidgets:
            self.findReplaceWidget.hide()
            self.gotoWidget.show()
            self.gotoWidget.setFocus()
            self.gotoWidget.selectAll()

    def findNext(self):
        """triggered when Ctrl+. is received"""
        self.findReplaceWidget.onNext()

    def findPrev(self):
        """Triggered when Ctrl+, is received"""
        self.findReplaceWidget.onPrev()

    def __addHistoryMenuItem(self, menu, index, currentHistoryIndex):
        """Prepares the history menu item"""
        entry = self.history.getEntry(index)
        text = entry.displayName
        if entry.tabType in [MainWindowTabWidgetBase.PlainTextEditor,
                             MainWindowTabWidgetBase.VCSAnnotateViewer]:
            text += ", " + str(entry.line + 1) + ":" + str(entry.pos + 1)
        act = menu.addAction(entry.icon, text)
        act.setData(index)
        if index == currentHistoryIndex:
            font = act.font()
            font.setBold(True)
            act.setFont(font)

    def __showHistoryBackMenu(self):
        """Shows the history button menu"""
        self.history.updateForCurrentIndex()
        self.__historyBackMenu.clear()
        currentIndex = self.history.getCurrentIndex()

        index = 0
        while index <= currentIndex:
            self.__addHistoryMenuItem(self.__historyBackMenu,
                                      index, currentIndex)
            index += 1

    def __showHistoryFwdMenu(self):
        """Shows the history button menu"""
        self.history.updateForCurrentIndex()
        self.__historyFwdMenu.clear()
        currentIndex = self.history.getCurrentIndex()
        maxIndex = self.history.getSize() - 1

        index = currentIndex
        while index <= maxIndex:
            self.__addHistoryMenuItem(self.__historyFwdMenu,
                                      index, currentIndex)
            index += 1

    def __activateHistoryTab(self):
        """Activates the tab advised by the current history entry"""
        self.__skipHistoryUpdate = True
        entry = self.history.getCurrentEntry()
        index = self.getIndexByUUID(entry.uuid)
        widget = self.getWidgetByUUID(entry.uuid)
        self.activateTab(index)
        if widget.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                MainWindowTabWidgetBase.VCSAnnotateViewer]:
            if widget.getLine() != entry.line or \
               widget.getPos() != entry.pos or \
               widget.getEditor().firstVisibleLine() != entry.firstVisible:
                # Need to jump to the memorized position because something
                # has been changed
                editor = widget.getEditor()
                editor.gotoLine(entry.line + 1, entry.pos + 1,
                                entry.firstVisible + 1)
        self.__skipHistoryUpdate = False

    def historyForwardClicked(self):
        """Back in history clicked"""
        self.history.updateForCurrentIndex()
        if self.history.stepForward():
            self.__activateHistoryTab()

    def historyBackClicked(self):
        """Forward in history clicked"""
        self.history.updateForCurrentIndex()
        if self.history.stepBack():
            self.__activateHistoryTab()

    def __onFlipTab(self):
        """Flip between last two tabs"""
        self.history.updateForCurrentIndex()
        if self.history.flip():
            self.__activateHistoryTab()

    def __historyMenuTriggered(self, act):
        """Handles the history menu selection"""
        index, isOK = act.data().toInt()
        if isOK:
            if index != self.history.getCurrentIndex():
                self.history.updateForCurrentIndex()
                self.history.setCurrentIndex(index)
                self.__activateHistoryTab()

    def __connectEditorWidget(self, editorWidget):
        """Connects the editor's signals"""
        editor = editorWidget.getEditor()
        editor.modificationChanged.connect(self.__modificationChanged)
        editor.textChanged.connect(self.__contentChanged)
        editor.cursorPositionChanged.connect(self.__cursorPositionChanged)
        editor.sigEscapePressed.connect(self.__onESC)

    # Arguments: modified
    def __modificationChanged(self, _=None):
        """Triggered when the file is changed"""
        index = self.currentIndex()
        currentWidget = self.currentWidget()
        # Sometimes a signal comes from a tab which has already been closed
        # so the check is done for the current widget
        if currentWidget.isModified():
            title = Settings()['modifiedFormat'] % currentWidget.getShortName()
            self.setTabText(index, title)
        else:
            self.setTabText(index, currentWidget.getShortName())

    def __contentChanged(self):
        """Triggered when a buffer content is changed"""
        currentWidget = self.currentWidget()
        self.sigBufferModified.emit(currentWidget.getFileName(),
                                    currentWidget.getUUID())

    def __onESC(self):
        """The editor detected ESC pressed"""
        if self.gotoWidget.isVisible() or self.findReplaceWidget.isVisible():
            self.gotoWidget.hide()
            self.findReplaceWidget.hide()
            return
        # No aux on screen, remove the indicators then if it is an editor
        # widget
        widget = self.currentWidget()
        if widget.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                MainWindowTabWidgetBase.VCSAnnotateViewer]:
            widget.getEditor().clearSearchIndicators()

    def __cursorPositionChanged(self):
        """Triggered when the cursor position changed"""
        widget = self.currentWidget()
        mainWindow = self.__mainWindow
        line = widget.getLine()
        pos = widget.getPos()

        if line is not None and pos is not None:
            mainWindow.sbLine.setText("Line: " + str(line + 1))
            mainWindow.sbPos.setText("Pos: " + str(pos + 1))

        if self.__debugMode:
            mainWindow.setRunToLineButtonState()

    def updateStatusBar(self):
        """Updates the status bar values"""
        currentWidget = self.currentWidget()
        mainWindow = self.__mainWindow

        mainWindow.sbLanguage.setText(currentWidget.getLanguage())
        editorWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                         MainWindowTabWidgetBase.VCSAnnotateViewer]
        if currentWidget.getType() in editorWidgets:
            mime = currentWidget.getMime()
            if mime:
                mainWindow.sbLanguage.setToolTip('Mime type: ' + mime)
            else:
                mainWindow.sbLanguage.setToolTip('Mime type: unknown')
        else:
            mainWindow.sbLanguage.setToolTip('')

        eol = currentWidget.getEol()
        mainWindow.sbEol.setText(eol if eol else 'n/a')

        cPos = currentWidget.getPos()
        if cPos is not None:
            mainWindow.sbPos.setText('Pos: ' + str(cPos + 1))
        else:
            mainWindow.sbPos.setText('Pos: n/a')
        cLine = currentWidget.getLine()
        if cLine is not None:
            mainWindow.sbLine.setText('Line: ' + str(cLine + 1))
        else:
            mainWindow.sbLine.setText('Line: n/a')

        rwMode = currentWidget.getRWMode()
        if rwMode:
            mainWindow.sbWritable.setText(rwMode)
            mainWindow.sbWritable.setToolTip('')
        else:
            mainWindow.sbWritable.setText('   ')
            mainWindow.sbWritable.setToolTip('RW mode: unknown')

        enc = currentWidget.getEncoding()
        if enc:
            mainWindow.sbEncoding.setText(enc)
            mainWindow.sbEncoding.setToolTip('')
        else:
            mainWindow.sbEncoding.setText('   ')
            mainWindow.sbEncoding.setToolTip('Encoding: unknown')

        fName = currentWidget.getFileName()
        if fName:
            mainWindow.sbFile.setPath("File: " + fName)
        else:
            mainWindow.sbFile.setPath('File: n/a')
        if self.__debugMode:
            mainWindow.setRunToLineButtonState()

        # Update the VCS indicator
        vcsManager = mainWindow.vcsManager
        if vcsManager.activePluginCount() == 0:
            mainWindow.sbVCSStatus.setVisible(False)
            return

        currentVCSStatus = currentWidget.getVCSStatus()
        if currentVCSStatus is None:
            mainWindow.sbVCSStatus.setVisible(False)
        else:
            # Draw the status
            mainWindow.sbVCSStatus.setVisible(True)
            vcsManager.drawStatus(mainWindow.sbVCSStatus, currentVCSStatus)

        validWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                        MainWindowTabWidgetBase.PictureViewer]
        if currentWidget.getType() in validWidgets:
            fileName = currentWidget.getFileName()
            if fileName.startswith(os.path.sep):
                # File exists
                vcsManager.requestStatus(fileName)

    def getUnsavedCount(self):
        """Provides the number of buffers which were not saved"""
        return len(self.getModifiedList())

    def closeRequest(self):
        """Returns True if it could be closed.

        If it cannot then an error messages is logged, first unsaved tab
        is activated and False is returned.
        """
        notSaved = []
        firstIndex = -1
        for index in range(self.count()):
            if self.widget(index).isModified():
                notSaved.append(self.widget(index).getShortName())
                if firstIndex == -1:
                    firstIndex = index
            else:
                # The tab will be closed soon, so save the file position
                self.updateFilePosition(index)

        if not notSaved:
            return True

        # There are not saved files
        logging.error("Please close or save the modified files first (" +
                      ", ".join(notSaved) + ")")
        self.activateTab(firstIndex)
        return False

    def closeEvent(self, event):
        """Handles the request to close"""
        # Hide completer if so
        curWidget = self.currentWidget()
        if curWidget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            curWidget.getEditor().hideCompleter()

        if self.closeRequest():
            # Need to call terminate for all the text editors if so
            for index in range(self.count()):
                editorWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                                 MainWindowTabWidgetBase.VCSAnnotateViewer]
                if self.widget(index).getType() in editorWidgets:
                    editor = self.widget(index).getEditor()
                    editor.textChanged.disconnect(self.__contentChanged)
                    editor.terminate()
            # That's the end of the session, so let's save the tabs status
            self.saveTabsStatus()

            event.accept()
            return True

        event.ignore()
        return False

    def closeAll(self):
        """Close all the editors tabs"""
        curWidget = self.currentWidget()
        if not curWidget:
            return

        if curWidget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            curWidget.getEditor().hideCompleter()

        if self.closeRequest():
            # It's safe to close all the tabs
            self.__doNotSaveTabs = True
            while self.widget(0) != self.__welcomeWidget:
                self.__onCloseRequest(0)
            self.__doNotSaveTabs = False

    def saveTabsStatus(self):
        """Saves the tabs status to project or global settings"""
        if self.__doNotSaveTabs:
            return

        if GlobalData().project.isLoaded():
            GlobalData().project.tabStatus = self.getTabsStatus()
        else:
            Settings().tabStatus = self.getTabsStatus()

    def getTabsStatus(self):
        """Provides all the tabs status and cursor positions"""
        if self.widget(0) == self.__welcomeWidget:
            return []

        status = []
        helpShortName = self.__helpWidget.getShortName()
        curWidget = self.currentWidget()

        for index in range(self.count()):
            item = self.widget(index)
            itemType = item.getType()
            if itemType == MainWindowTabWidgetBase.HTMLViewer and \
               item.getShortName() == helpShortName:
                status.append({'active': item == curWidget,
                               'path': 'help',
                               'mdFullView': False,
                               'mdFullViewReadOnly': mdFullViewReadOnly})
                continue
            if itemType in [MainWindowTabWidgetBase.PlainTextEditor,
                            MainWindowTabWidgetBase.PictureViewer,
                            MainWindowTabWidgetBase.MDViewer]:
                fileName = item.getFileName()
                if not fileName:
                    continue    # New, not saved yet file

                # Need to save the file name only. The cursor position is saved
                # in another file.
                if GlobalData().project.isProjectFile(fileName):
                    prjDir = os.path.dirname(GlobalData().project.fileName)
                    relativePath = os.path.relpath(fileName, prjDir)
                    pathToSave = relativePath
                else:
                    pathToSave = fileName
                if itemType == MainWindowTabWidgetBase.MDViewer:
                    mdFullView = True
                    mdFullViewReadOnly = item.isReadOnly()
                else:
                    mdFullView = False
                    mdFullViewReadOnly = False

                status.append({'active': item == curWidget,
                               'path': pathToSave,
                               'mdFullView': mdFullView,
                               'mdFullViewReadOnly': mdFullViewReadOnly})
        return status

    def restoreTabs(self, status):
        """Restores the tab status, i.e. load files and set cursor pos"""
        self.__restoringTabs = True
        self.history.clear()

        # Force close all the tabs if any
        while self.count() > 0:
            self.removeTab(0)

        # Walk the status list
        activeIndex = -1
        for index in range(len(status) - 1, -1, -1):
            record = status[index]
            if record['active']:
                activeIndex = index
            fileName = record['path']

            if fileName == 'help':
                # Help widget
                if self.widget(0) == self.__welcomeWidget:
                    # It is the only welcome widget on the screen
                    self.removeTab(0)
                    self.setTabsClosable(True)
                shortName = self.__helpWidget.getShortName()
                self.addTab(self.__helpWidget, shortName)
                continue

            if not os.path.isabs(fileName):
                # Relative path - build absolute
                prjDir = os.path.dirname(GlobalData().project.fileName)
                fileName = os.path.abspath(prjDir + os.path.sep + fileName)

            if not os.path.exists(fileName):
                logging.warning('Cannot restore last session tab. '
                                'File is not found (' +
                                fileName + ')')
                continue

            mdFullView = record.get('mdFullView', False)
            if mdFullView:
                mdFullViewReadOnly = record.get('mdFullViewReadOnly', False)
                self.openMarkdownFullView(fileName, mdFullViewReadOnly)
                continue

            # Detect file type, it could be a picture
            mime, _, _ = getFileProperties(fileName)
            if isImageViewable(mime):
                self.openPixmapFile(fileName)
                continue

            # A usual file; position will be restored at the file loading stage
            self.openFile(fileName, -1)

        # This call happens when a project is loaded, so it makes sense to
        # reset a new file index
        self.__newIndex = -1

        # Switch to the last active tab
        if self.count() == 0:
            # No one was restored - display the welcome widget
            self.setTabsClosable(False)
            self.addTab(self.__welcomeWidget,
                        self.__welcomeWidget.getShortName())
            activeIndex = 0
            self.activateTab(activeIndex)
            self.history.clear()
            self.__restoringTabs = False
            return

        # There are restored tabs
        self.setTabsClosable(True)
        if activeIndex == -1 or activeIndex >= self.count():
            activeIndex = 0
        self.activateTab(activeIndex)
        self.history.clear()
        self.history.addCurrent()
        self.__restoringTabs = False

        self.sendAllTabsVCSStatusRequest()

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        GlobalData().mainWindow.showStatusBarMessage(
            "Setting text zoom to " + str(Settings()['zoom']), 10000)
        for index in range(self.count()):
            item = self.widget(index)
            if item.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                  MainWindowTabWidgetBase.VCSAnnotateViewer,
                                  MainWindowTabWidgetBase.DiffViewer]:
                item.onTextZoomChanged()

    def onFlowZoomChanged(self):
        """Triggered when a flow diagram zoom is changed"""
        GlobalData().mainWindow.showStatusBarMessage(
            "Setting flow zoom to " + str(Settings()['flowZoom']), 10000)
        for index in range(self.count()):
            item = self.widget(index)
            if item.getType() in [MainWindowTabWidgetBase.PlainTextEditor]:
                item.onFlowZoomChanged()

    def getTextEditors(self):
        """Provides a list of the currently opened text editors"""
        result = []
        for index in range(self.count()):
            item = self.widget(index)
            if item.getType() in [MainWindowTabWidgetBase.PlainTextEditor]:
                result.append([item.getUUID(), item.getFileName(), item])
        return result

    def updateEditorsSettings(self):
        """makes all the text editors updating settings"""
        for index in range(self.count()):
            item = self.widget(index)
            if item.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                  MainWindowTabWidgetBase.VCSAnnotateViewer]:
                item.getEditor().updateSettings()
                if item.isDiskFileModified():
                    # This will make the modification markers re-drawn
                    # properly for the case when auto line wrap toggled
                    item.resizeBars()

    def resetTextSearchMatchCache(self):
        """Resets all the buffers match cache"""
        for index in range(self.count()):
            item = self.widget(index)
            if item.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                  MainWindowTabWidgetBase.VCSAnnotateViewer]:
                item.getEditor().resetMatchCache()

    def updateCFEditorsSettings(self):
        """Visits all the visible CF editors"""
        for index in range(self.count()):
            item = self.widget(index)
            if item.getType() in [MainWindowTabWidgetBase.PlainTextEditor]:
                item.getCFEditor().updateSettings()

    def getWidgetByUUID(self, uuid):
        """Provides the widget found by the given UUID"""
        for index in range(self.count()):
            widget = self.widget(index)
            if uuid == widget.getUUID():
                return widget
        return None

    def getIndexByUUID(self, uuid):
        """Provides the tab index for the given uuid"""
        for index in range(self.count()):
            widget = self.widget(index)
            if uuid == widget.getUUID():
                return index
        return -1

    def getWidgetByIndex(self, index):
        """Provides the widget for the given index on None"""
        if index >= self.count():
            return None
        return self.widget(index)

    def getWidgetForFileName(self, fname):
        """Provides the widget found by the given file name"""
        for index in range(self.count()):
            widget = self.widget(index)
            if fname == widget.getFileName():
                return widget
        return None

    def checkOutsideFileChanges(self):
        """Checks all the tabs if the files were changed/disappeared outside"""
        for index in range(self.count()):
            if self.__welcomeWidget != self.widget(index):
                self._updateIconAndTooltip(index)

        currentWidget = self.currentWidget()
        if currentWidget is None:
            return

        if currentWidget.doesFileExist():
            if currentWidget.isDiskFileModified():
                if not currentWidget.getReloadDialogShown():
                    currentWidget.showOutsideChangesBar(
                        self.__countDiskModifiedUnchanged() > 1)

    def checkOutsidePathChange(self, path):
        """Checks outside changes for a certain path"""
        if path.endswith(os.path.sep):
            return

        for index in range(self.count()):
            widget = self.widget(index)
            fileName = widget.getFileName()
            if fileName == path:
                self._updateIconAndTooltip(index)
                currentWidget = self.currentWidget()
                if currentWidget == widget:
                    if widget.doesFileExist():
                        if not widget.getReloadDialogShown():
                            widget.showOutsideChangesBar(
                                self.__countDiskModifiedUnchanged() > 1)
                break

    def __countDiskModifiedUnchanged(self):
        """Returns the number of buffers with non modified
           content for which the disk file is modified
        """
        cnt = 0
        for index in range(self.count()):
            if not self.widget(index).isModified():
                if self.widget(index).isDiskFileModified():
                    cnt += 1
        return cnt

    def onReload(self):
        """Called when the current tab file should be reloaded"""
        self.reloadTab(self.currentIndex())

    def onTabRunChanged(self, enabled):
        """Triggered when an editor informs about changes of the run buttons"""
        self.sigTabRunChanged.emit(enabled)

    def reloadTab(self, index):
        """Reloads a single tab"""
        # This may happened for a text file or for a picture
        isTextEditor = self.widget(index).getType() == \
            MainWindowTabWidgetBase.PlainTextEditor

        try:
            if isTextEditor:
                editor = self.widget(index).getEditor()
                line, pos = editor.cursorPosition
                firstLine = editor.firstVisibleLine()

            self.widget(index).reload()

            if isTextEditor:
                editor.gotoLine(line + 1, pos + 1, firstLine + 1)
        except Exception as exc:
            # Error reloading the file, nothing to be changed
            logging.error(str(exc))
            return

        self._updateIconAndTooltip(index)

        if isTextEditor:
            self.history.tabClosed(self.widget(index).getUUID())
            if index == self.currentIndex():
                self.history.addCurrent()

    def onReloadAllNonModified(self):
        """Called when all the disk changed and not
           modified files should be reloaded
        """
        for index in range(self.count()):
            if not self.widget(index).isModified():
                if self.widget(index).isDiskFileModified():
                    self.reloadTab(index)

    def getModifiedList(self, projectOnly=False):
        """Prpovides a list of modified file names with their UUIDs"""
        result = []

        for index in range(self.count()):
            widget = self.widget(index)
            if widget.isModified():
                fileName = widget.getFileName()
                if projectOnly:
                    if not GlobalData().project.isProjectFile(fileName):
                        continue
                result.append([fileName, widget.getUUID()])
        return result

    def getOpenedList(self, projectOnly=False):
        """Provides a list of opened files"""
        result = []
        for index in range(self.count()):
            widget = self.widget(index)
            fileName = widget.getFileName()
            if projectOnly:
                if not GlobalData().project.isProjectFile(fileName):
                    continue
            result.append([fileName, widget.getUUID()])
        return result

    def isFileOpened(self, fileName):
        """True if the file is loaded"""
        for attrs in self.getOpenedList():
            if attrs[0] == fileName:
                return True
        return False

    def saveModified(self, projectOnly=False):
        """Saves the modified files. Stops on first error."""
        for index in range(self.count()):
            widget = self.widget(index)
            if widget.isModified():
                fileName = widget.getFileName()
                if projectOnly:
                    if not GlobalData().project.isProjectFile(fileName):
                        continue
                # Save the file
                try:
                    if not self.onSave(index):
                        return False
                    self.setTabText(index, widget.getShortName())
                except Exception as exc:
                    logging.error(str(exc))
                    return False
        return True

    def __onDebugMode(self, newState):
        """Triggered when the debug mode state is changed"""
        self.__debugMode = newState
        self.__createdWithinDebugSession = []
        if self.__debugMode:
            if not GlobalData().project.isLoaded():
                self.__debugScript = self.currentWidget().getFileName()
        else:
            self.__debugScript = ""

        for index in range(self.count()):
            self.setWidgetDebugMode(self.widget(index))

    def setWidgetDebugMode(self, widget):
        """Sets the widget debug mode"""
        fileName = widget.getFileName()
        if widget.getType() not in [MainWindowTabWidgetBase.PlainTextEditor]:
            return
        if not isPythonMime(widget.getMime()):
            return
        if fileName == "":
            return
        if fileName in self.__createdWithinDebugSession:
            return

        # Need to send the notification only to the python editors
        isPrjFile = GlobalData().project.isProjectFile(fileName)
        isDbgsScript = fileName == self.__debugScript

        widget.setDebugMode(self.__debugMode, isPrjFile or isDbgsScript)

    def zoomIn(self):
        """Called if main menu item is selected"""
        widget = self.currentWidget()
        if widget.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                MainWindowTabWidgetBase.VCSAnnotateViewer,
                                MainWindowTabWidgetBase.PictureViewer,
                                MainWindowTabWidgetBase.GeneratedDiagram,
                                MainWindowTabWidgetBase.ProfileViewer,
                                MainWindowTabWidgetBase.DiffViewer]:
            widget.onZoomIn()

    def zoomOut(self):
        """Called if main menu item is selected"""
        widget = self.currentWidget()
        if widget.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                MainWindowTabWidgetBase.VCSAnnotateViewer,
                                MainWindowTabWidgetBase.PictureViewer,
                                MainWindowTabWidgetBase.GeneratedDiagram,
                                MainWindowTabWidgetBase.ProfileViewer,
                                MainWindowTabWidgetBase.DiffViewer]:
            widget.onZoomOut()

    def zoomReset(self):
        """Called if main menu item is selected"""
        widget = self.currentWidget()
        if widget.getType() in [MainWindowTabWidgetBase.PlainTextEditor,
                                MainWindowTabWidgetBase.VCSAnnotateViewer,
                                MainWindowTabWidgetBase.PictureViewer,
                                MainWindowTabWidgetBase.GeneratedDiagram,
                                MainWindowTabWidgetBase.ProfileViewer,
                                MainWindowTabWidgetBase.DiffViewer]:
            widget.onZoomReset()

    def isCopyAvailable(self):
        """Checks if Ctrl+C works for the current widget"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType in [MainWindowTabWidgetBase.PlainTextEditor,
                          MainWindowTabWidgetBase.VCSAnnotateViewer]:
            return True
        if widgetType == MainWindowTabWidgetBase.HTMLViewer:
            return widget.getViewer().isCopyAvailable()
        if widgetType == MainWindowTabWidgetBase.GeneratedDiagram:
            return True
        if widgetType == MainWindowTabWidgetBase.ProfileViewer:
            return widget.isCopyAvailable()
        return False

    def onCopy(self):
        """Called when Ctrl+C is selected via main menu"""
        widget = self.currentWidget()
        widgetType = widget.getType()
        if widgetType in [MainWindowTabWidgetBase.PlainTextEditor,
                          MainWindowTabWidgetBase.VCSAnnotateViewer]:
            widget.getEditor().onCtrlC()
            return
        if widgetType == MainWindowTabWidgetBase.HTMLViewer:
            widget.getViewer().copy()
            return
        if widgetType in [MainWindowTabWidgetBase.GeneratedDiagram,
                          MainWindowTabWidgetBase.ProfileViewer]:
            widget.onCopy()
            return

    def setTooltips(self, switchOn):
        """Sets the tooltips mode"""
        del switchOn    # unused argument
        for index in range(self.count()):
            widget = self.widget(index)
            widgetType = widget.getType()
            if widgetType == MainWindowTabWidgetBase.PlainTextEditor:
                self._updateIconAndTooltip(index)

    def __onPluginActivated(self, plugin):
        """Triggered when a plugin is activated"""
        pluginName = plugin.getName()
        try:
            menu = QMenu(pluginName, self)
            plugin.getObject().populateBufferContextMenu(menu)
            if menu.isEmpty():
                menu = None
                return
            self.__pluginMenus[plugin.getPath()] = menu
            self.sigPluginContextMenuAdded.emit(menu, len(self.__pluginMenus))
        except Exception as exc:
            logging.error("Error populating " + pluginName +
                          " plugin buffer context menu: " +
                          str(exc) + ". Ignore and continue.")

    def __onPluginDeactivated(self, plugin):
        """Triggered when a plugin is deactivated"""
        try:
            path = plugin.getPath()
            if path in self.__pluginMenus:
                menu = self.__pluginMenus[path]
                del self.__pluginMenus[path]
                self.sigPluginContextMenuRemoved.emit(menu,
                                                      len(self.__pluginMenus))
                menu = None
        except Exception as exc:
            pluginName = plugin.getName()
            logging.error("Error removing " + pluginName +
                          " plugin buffer context menu: " +
                          str(exc) + ". Ignore and continue.")

    def getPluginMenus(self):
        """Provides a reference to the registered plugin menus map"""
        return self.__pluginMenus

    def __onVCSStatus(self, path, status):
        """Triggered when a status was updated"""
        for index in range(self.count()):
            widget = self.widget(index)
            allowedWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.PictureViewer]
            if widget.getType() in allowedWidgets:
                if widget.getFileName() == path:
                    widget.setVCSStatus(status)
                    if self.currentIndex() == index:
                        self.__mainWindow.sbVCSStatus.setVisible(True)
                        self.__mainWindow.vcsManager.drawStatus(
                            self.__mainWindow.sbVCSStatus, status)
                    break

    def sendAllTabsVCSStatusRequest(self):
        """Sends the status requests for all the opened TABS (text/picture)"""
        for index in range(self.count()):
            widget = self.widget(index)
            allowedWidgets = [MainWindowTabWidgetBase.PlainTextEditor,
                              MainWindowTabWidgetBase.PictureViewer]
            if widget.getType() in allowedWidgets:
                fileName = widget.getFileName()
                if os.path.isabs(fileName):
                    self.__mainWindow.vcsManager.requestStatus(fileName)

    def passFocusToEditor(self):
        """Passes the focus to the text editor if it is there"""
        widget = self.currentWidget()
        if widget:
            widget.setFocus()
            return True
        return False

    def passFocusToFlow(self):
        """Passes the focus to the flow UI if it is there"""
        widget = self.currentWidget()
        if widget:
            if widget.getType() in [MainWindowTabWidgetBase.PlainTextEditor]:
                return widget.passFocusToFlow()
        return False
