# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2018 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Provides the storage for the flow UI collapsed groups"""

import os.path
from .fileutils import loadJSON, saveJSON


class FlowUICollapsedGroups:

    """Loads/stores/saves the collapsed group list"""

    def __init__(self):
        # file name -> list of group ids
        self.__groups = {}
        self.__groupsFileName = None

    def reset(self):
        """Un-binds from the file system"""
        self.__groups = {}
        self.__groupsFileName = None

    def setup(self, dirName):
        """Binds the parameters to a disk file"""
        # Just in case - flush the previous data if they were bound
        FlowUICollapsedGroups.save(self)

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception('Directory name is expected for collapsed '
                            'groups. The given ' + dirName + ' is not.')

        self.__groupsFileName = dirName + 'collapsedgroups.json'
        if os.path.exists(self.__groupsFileName):
            FlowUICollapsedGroups.load(self)

    def load(self):
        """Loads the saved collapsed groups file"""
        if self.__groupsFileName:
            self.__groups = loadJSON(self.__groupsFileName,
                                     'collapsed groups', {})

    def save(self):
        """Saves the collapsed groups into a file"""
        if self.__groupsFileName:
            saveJSON(self.__groupsFileName, self.__groups, 'collapsed groups')

    def getFileGroups(self, fileName):
        """Provides None if not found"""
        return self.__groups.get(fileName, None)

    def setFileGroups(self, fileName, groups):
        """Sets the collapsed groups for the file"""
        if groups:
            self.__groups[fileName] = groups
            FlowUICollapsedGroups.save(self)
        else:
            if self.__groups.pop(fileName, None) is not None:
                FlowUICollapsedGroups.save(self)

    def addFileGroup(self, fileName, group):
        """Adds to a file group"""
        groups = self.__groups.get(fileName, None)
        if groups:
            if group not in groups:
                self.__groups[fileName].append(group)
                FlowUICollapsedGroups.save(self)
        else:
            self.__groups[fileName] = [group]
            FlowUICollapsedGroups.save(self)

    def removeFileGroup(self, fileName, group):
        """Removes from a file group"""
        groups = self.__groups.get(fileName, None)
        if groups:
            if group in groups:
                groups.remove(group)
                if groups:
                    self.__groups[fileName] = groups
                else:
                    self.__groups.pop(fileName, None)
                FlowUICollapsedGroups.save(self)
