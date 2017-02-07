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

"""Globals browser model"""

from os.path import basename, realpath
from utils.project import CodimensionProject
from utils.fileutils import isPythonFile
from .viewitems import TreeViewGlobalItem
from .browsermodelbase import BrowserModelBase


class GlobalsBrowserModel(BrowserModelBase):

    """Class implementing the globals browser model"""

    def __init__(self, parent=None):
        BrowserModelBase.__init__(self, ["Name", "File name", "Line"], parent)

        self.globalData.project.sigProjectChanged.connect(
            self.__onProjectChanged)

    def __populateModel(self):
        """Populates the project browser model"""
        self.clear()
        project = self.globalData.project
        cache = self.globalData.briefModinfoCache
        for fname in project.filesList:
            if isPythonFile(fname):
                info = cache.get(fname)
                for globalObj in info.globals:
                    item = TreeViewGlobalItem(self.rootItem, globalObj)
                    item.appendData([basename(fname), globalObj.line])
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
                if realpath(path) == realpath(item.getPath()):
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
            for globalObj in info.globals:
                needUpdate = True
                newItem = TreeViewGlobalItem(self.rootItem, globalObj)
                newItem.appendData([basename(path), globalObj.line])
                newItem.setPath(path)
                self.addTreeItem(self.rootItem, newItem)
        return needUpdate

    def onFileUpdated(self, fileName):
        """Triggered when a file was updated"""
        # Here: python file which belongs to the project
        info = self.globalData.briefModinfoCache.get(fileName)

        existingGlobals = []
        itemsToRemove = []
        needUpdate = False

        # For all root items
        path = realpath(fileName)
        for treeItem in self.rootItem.childItems:
            if realpath(treeItem.getPath()) != path:
                continue

            # Item belongs to the modified file
            name = treeItem.data(0)
            found = False
            for glob in info.globals:
                if glob.name == name:
                    found = True
                    existingGlobals.append(name)
                    if treeItem.data(2) != glob.line:
                        # Appearance has changed
                        treeItem.updateData(glob)
                        treeItem.setData(2, glob.line)
                        self.signalItemUpdated(treeItem)
                    else:
                        treeItem.updateData(glob)

            if not found:
                itemsToRemove.append(treeItem)

        for item in itemsToRemove:
            needUpdate = True
            self.removeTreeItem(item)

        # Add those which have been introduced
        for item in info.globals:
            if item.name not in existingGlobals:
                needUpdate = True
                newItem = TreeViewGlobalItem(self.rootItem, item)
                newItem.appendData([basename(fileName), item.line])
                newItem.setPath(fileName)
                self.addTreeItem(self.rootItem, newItem)

        return needUpdate
