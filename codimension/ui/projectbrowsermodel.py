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

"""Project browser model"""

from utils.globals import GlobalData
from utils.project import CodimensionProject
from utils.settings import Settings
from .qt import Qt
from .viewitems import TreeViewDirectoryItem
from .browsermodelbase import BrowserModelBase


class ProjectBrowserModel(BrowserModelBase):

    """Class implementing the project browser model"""

    def __init__(self, parent):
        self.__mainWindow = parent
        BrowserModelBase.__init__(self, "Name", self.__mainWindow)
        self.setTooltips(Settings()['projectTooltips'])
        self.populateModel()
        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

    def populateModel(self):
        """Populates the project browser model"""
        self.clear()
        project = self.globalData.project
        if project.isLoaded():
            projectDir = project.getProjectDir()
            newItem = TreeViewDirectoryItem(self.rootItem, projectDir)
            newItem.needVCSStatus = True
            self.addItem(newItem)

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.populateModel()

    def __tooltipRoleData(self, item, indicator):
        """Provides the data for the tooltip role"""
        docstringPart = None
        if self.showTooltips and item.toolTip != "":
            docstringPart = item.toolTip

        vcsPart = None
        if indicator:
            if item.vcsStatus.message:
                vcsPart = item.vcsStatus.message
            else:
                vcsPart = indicator.defaultTooltip

        if docstringPart and vcsPart:
            return docstringPart + "\n\nVCS status: " + vcsPart
        if docstringPart:
            return docstringPart
        if vcsPart:
            return "VCS status: " + vcsPart
        return None

    def data(self, index, role):
        """Extention to modify the background and tooltips for the browser"""
        if not index.isValid():
            return None

        item = index.internalPointer()
        if item.vcsStatus:
            indicator = self.__mainWindow.vcsManager.getStatusIndicator(
                item.vcsStatus)
            if role == Qt.TextColorRole:
                if indicator and indicator.foregroundColor:
                    return indicator.foregroundColor
            elif role == Qt.BackgroundColorRole:
                if indicator and indicator.backgroundColor:
                    return indicator.backgroundColor
            elif role == Qt.ToolTipRole:
                return self.__tooltipRoleData(item, indicator)

        return BrowserModelBase.data(self, index, role)
