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

"""Classes browser model"""

import os.path
from os.path import basename
from utils.fileutils import getFileProperties, isPythonMime
from utils.settings import Settings
from utils.project import CodimensionProject
from .viewitems import TreeViewClassItem
from .browsermodelbase import BrowserModelBase


class ClassesBrowserModel(BrowserModelBase):

    """Class implementing the project browser model"""

    def __init__(self, parent=None):
        BrowserModelBase.__init__(self, ["Name", "File name", "Line"], parent)
        self.setTooltips(Settings()['classesTooltips'])
        self.globalData.project.sigProjectChanged.connect(
            self.__onProjectChanged)

    def __populateModel(self):
        """Populates the project browser model"""
        self.clear()
        project = self.globalData.project
        cache = self.globalData.briefModinfoCache
        for fname in project.filesList:
            mime, _, _ = getFileProperties(fname)
            if isPythonMime(mime):
                info = cache.get(fname)
                for classObj in info.classes:
                    item = TreeViewClassItem(self.rootItem, classObj)
                    item.appendData([basename(fname), classObj.line])
                    item.setPath(fname)
                    self.rootItem.appendChild(item)

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.__populateModel()

    def onFSChanged(self, addedPythonFiles, deletedPythonFiles):
        """Triggered when some files appeared or disappeared"""
        needUpdate = False
        itemsToDelete = []
        for path in deletedPythonFiles:
            for item in self.rootItem.childItems:
                if os.path.realpath(path) == \
                   os.path.realpath(item.getPath()):
                    itemsToDelete.append(item)

        for item in itemsToDelete:
            needUpdate = True
            self.removeTreeItem(item)

        for path in addedPythonFiles:
            try:
                info = self.globalData.briefModinfoCache.get(path)
            except:
                # It could be that a file was created and deleted straight
                # away. In this case the cache will generate an exception.
                continue
            for classObj in info.classes:
                needUpdate = True
                newItem = TreeViewClassItem(self.rootItem, classObj)
                newItem.appendData([basename(path), classObj.line])
                newItem.setPath(path)
                self.addTreeItem(self.rootItem, newItem)
        return needUpdate

    def onFileUpdated(self, fileName):
        """Triggered when a file was updated"""
        # Here: python file which belongs to the project
        info = self.globalData.briefModinfoCache.get(fileName)

        existingClasses = []
        itemsToRemove = []
        needUpdate = False

        # For all root items
        path = os.path.realpath(fileName)
        for treeItem in self.rootItem.childItems:
            if os.path.realpath(treeItem.getPath()) != path:
                continue

            # Item belongs to the modified file
            name = treeItem.sourceObj.name
            found = False
            for cls in info.classes:
                if cls.name == name:
                    found = True
                    existingClasses.append(name)
                    treeItem.updateData(cls)
                    treeItem.setData(2, cls.line)
                    self.signalItemUpdated(treeItem)
                    self.updateSingleClassItem(treeItem, cls)
                    break
            if not found:
                itemsToRemove.append(treeItem)

        for item in itemsToRemove:
            needUpdate = True
            self.removeTreeItem(item)

        # Add those which have been introduced
        for item in info.classes:
            if item.name not in existingClasses:
                needUpdate = True
                newItem = TreeViewClassItem(self.rootItem, item)
                newItem.appendData([basename(fileName), item.line])
                newItem.setPath(fileName)
                self.addTreeItem(self.rootItem, newItem)
        return needUpdate
