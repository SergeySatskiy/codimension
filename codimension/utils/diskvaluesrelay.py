# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Relay for values stored on the disk"""

# Some values could be stored for a project or for an IDE. This module
# provides a set of the functions to relay a call to the appropriate
# location

from os.path import relpath, dirname
from .globals import GlobalData
from .settings import Settings


def getCollapsedGroups(fileName):
    """Provides None if not found"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            return project.getFileGroups(key)
    return Settings().getFileGroups(fileName)


def setCollapsedGroups(fileName, groups):
    """Sets the file collapsed groups"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            project.setFileGroups(key, groups)
            return
    Settings().setFileGroups(fileName, groups)


def addCollapsedGroup(fileName, group):
    """Adds a group into a list collapsed group for a file"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            project.addFileGroup(key, group)
            return
    Settings().addFileGroup(fileName, group)


def removeCollapsedGroup(fileName, group):
    """Removes a group from a list of collapsed groups for a file"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            project.removeFileGroup(key, group)
            return
    Settings().removeFileGroup(fileName, group)


def getFileEncoding(fileName):
    """Provides None if not found"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            return project.getFileEncoding(key)
    return Settings().getFileEncoding(fileName)


def setFileEncoding(fileName, encoding):
    """Sets the encoding for the file"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            project.setFileEncoding(key, encoding)
            return
    Settings().setFileEncoding(fileName, encoding)


def getRunParameters(fileName):
    """Provides the run parameters"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            return project.getRunParameters(key)
    return Settings().getRunParameters(fileName)


def addRunParams(fileName, params):
    """Registers new latest run parameters"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            project.addRunParameters(key, params)
            return
    Settings().addRunParameters(fileName, params)


def getFilePosition(fileName):
    """Provides the position or (-1,-1,-1,-1,-1) if not found"""
    project = GlobalData().project
    if project.isLoaded():
        if project.isProjectFile(fileName):
            key = relpath(fileName, dirname(project.fileName))
            return project.getFilePosition(key)
    return Settings().getFilePosition(fileName)


def updateFilePosition(fileName, line, pos, firstLine,
                       horizontalPos, verticalPos):
    """Updates the position for the file"""
    if fileName:
        project = GlobalData().project
        if project.isLoaded():
            if project.isProjectFile(fileName):
                key = relpath(fileName, dirname(project.fileName))
                project.updateFilePosition(key, line, pos, firstLine,
                                           horizontalPos, verticalPos)
                return
        Settings().updateFilePosition(fileName, line, pos, firstLine,
                                      horizontalPos, verticalPos)


def getFindFileHistory():
    """Provides the find file history"""
    project = GlobalData().project
    if project.isLoaded():
        return project.findFileHistory
    return Settings().findFileHistory


def setFindFileHistory(values):
    """Updates the find file history"""
    project = GlobalData().project
    if project.isLoaded():
        project.findFileHistory = values
    else:
        Settings().findFileHistory = values


def getFindNameHistory():
    """Provides the find name history"""
    project = GlobalData().project
    if project.isLoaded():
        return project.findNameHistory
    return Settings().findNameHistory


def setFindNameHistory(values):
    """Updates the find name history"""
    project = GlobalData().project
    if project.isLoaded():
        project.findNameHistory = values
    else:
        Settings().findNameHistory = values


def getFindInFilesHistory():
    """Provides the find in files history"""
    project = GlobalData().project
    if project.isLoaded():
        return project.findInFilesHistory
    return Settings().findInFilesHistory


def setFindInFilesHistory(values):
    """Updates the find in files history"""
    project = GlobalData().project
    if project.isLoaded():
        project.findInFilesHistory = values
    else:
        Settings().findInFilesHistory = values


def getFindHistory():
    """Provides the find history"""
    project = GlobalData().project
    if project.isLoaded():
        return project.findHistory
    return Settings().findHistory


def setFindHistory(values):
    """Updates the find history"""
    project = GlobalData().project
    if project.isLoaded():
        project.findHistory = values
    else:
        Settings().findHistory = values


def addRecentFile(path):
    """Adds a recent file"""
    project = GlobalData().project
    if project.isLoaded():
        project.addRecentFile(path)
    else:
        Settings().addRecentFile(path)


def removeRecentFile(path):
    """Removes a recent file"""
    project = GlobalData().project
    if project.isLoaded():
        project.removeRecentFile(path)
    else:
        Settings().removeRecentFile(path)


def getRecentFiles():
    """Provides the recent files list"""
    project = GlobalData().project
    if project.isLoaded():
        return project.recentFiles
    return Settings().recentFiles




##DebuggerEnvironment
##SearchEnvironment
##FileSystemEnvironment
