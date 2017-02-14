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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Project browser with module browsing capabilities"""

import copy
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.project import CodimensionProject
from .qt import QApplication
from .projectbrowsermodel import ProjectBrowserModel
from .filesbrowserbase import FilesBrowser
from .viewitems import DirectoryItemType


class ProjectBrowser(FilesBrowser):

    """Project tree browser"""

    def __init__(self, parent):

        self.__mainWindow = parent
        FilesBrowser.__init__(self, ProjectBrowserModel(self.__mainWindow),
                              True, self.__mainWindow)

        self.setWindowTitle('Project browser')
        self.setWindowIcon(getIcon('icon.png'))

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)
        GlobalData().project.sigFSChanged.connect(self._onFSChanged)

        # VCS status support
        GlobalData().pluginManager.sigPluginDeactivated.connect(
            self.__onPluginDeactivated)
        self.__mainWindow.vcsManager.sigVCSFileStatus.connect(
            self.__onVCSFileStatus)
        self.__mainWindow.vcsManager.sigVCSDirStatus.connect(
            self.__onVCSDirStatus)

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.model().beginResetModel()
            self.model().endResetModel()

    def reload(self):
        """Reloads the projects view"""
        self.model().sourceModel().populateModel()
        self.model().beginResetModel()
        self.model().endResetModel()
        self.layoutDisplay()

    # Arguments: plugin
    def __onPluginDeactivated(self, _):
        """Triggered when a plugin is deactivated"""
        if self.__mainWindow.vcsManager.activePluginCount() == 0:
            for treeItem in self.model().sourceModel().rootItem.childItems:
                self.__resetVCSStatus(treeItem)

    def __resetVCSStatus(self, treeItem):
        """Recursively resets the VCS status if needed"""
        if treeItem.vcsStatus:
            treeItem.vcsStatus = None
            self._signalItemUpdated(treeItem)

        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                self.__resetVCSStatus(i)
            else:
                if i.vcsStatus:
                    i.vcsStatus = None
                    self._signalItemUpdated(i)

    def __onVCSFileStatus(self, path, status):
        """Triggered when a status was updated"""
        for treeItem in self.model().sourceModel().rootItem.childItems:
            self._updateVCSFileStatus(treeItem, path, status)

    def _updateVCSFileStatus(self, treeItem, path, status):
        """Updates the VCS status of an item"""
        # Due to symbolic links the whole tree must be checked, so there is
        # no limit here...
        updateSent = False
        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                self._updateVCSFileStatus(i, path, status)
            else:
                # It is a file
                if i.getRealPath() == path:
                    if i.vcsStatus != status:
                        i.vcsStatus = copy.deepcopy(status)
                        self._signalItemUpdated(i)
                        updateSent = True
        if updateSent:
            self.__focusFlip()

    def __onVCSDirStatus(self, path, status):
        """Triggered when a status is updated"""
        for treeItem in self.model().sourceModel().rootItem.childItems:
            self._updateVCSDirStatus(treeItem, path, status)

    def _updateVCSDirStatus(self, treeItem, path, status):
        """Updates the VCS status of an item"""
        # Due to symbolic links the whole tree must be checked, so there is
        # no limit here...
        updateSent = False
        if treeItem.getRealPath() == path:
            if treeItem.vcsStatus != status:
                treeItem.vcsStatus = copy.deepcopy(status)
                self._signalItemUpdated(treeItem)
                updateSent = True

        for i in treeItem.childItems:
            if i.itemType == DirectoryItemType:
                self._updateVCSDirStatus(i, path, status)

        if updateSent:
            self.__focusFlip()

    def __focusFlip(self):
        """Dirty trick utility function"""
        # QT does not update the left part of the item where
        # a tree part is drawn. It updates only the right part of the item
        # when a signal is sent. Qt however updates the tree part when
        # focus is received. So here is focus flipping below.
        currentFocus = QApplication.focusWidget()
        if currentFocus:
            if currentFocus == self:
                editorsManager = self.__mainWindow.editorsManager()
                currentWidget = editorsManager.currentWidget()
                if currentWidget:
                    currentWidget.setFocus()
                    self.setFocus()
            else:
                self.setFocus()
                currentFocus.setFocus()

    def drawBranches(self, painter, rect, index):
        """Helps to draw the solid highlight line for the project browser.

        This part is responsible for the beginning of the background line
        till +/- icon.
        See also the ProjectBrowserModel::data(...) method which draws
        the rest of the background
        http://stackoverflow.com/questions/14255224/
        changing-the-row-background-color-of-a-qtreeview-does-not-work
        """
        if index.isValid():
            if index != self.currentIndex():
                item = self.model().item(index)
                if item.vcsStatus:
                    vcsManager = self.__mainWindow.vcsManager
                    indicator = vcsManager.getStatusIndicator(item.vcsStatus)
                    if indicator and indicator.backgroundColor:
                        painter.fillRect(rect, indicator.backgroundColor)
        FilesBrowser.drawBranches(self, painter, rect, index)
