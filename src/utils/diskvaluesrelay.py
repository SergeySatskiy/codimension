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
            project.setFileEncoding(fileName, encoding)
            return
    Settings().setFileEncoding(fileName, encoding)


def getRunParameters(fileName):
    """Provides the run parameters"""
    project = GlobalData().project
    if project.isLoaded():
        if self.project.isProjectFile(fileName):
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



##DebuggerEnvironment
##SearchEnvironment
##FileSystemEnvironment
##RunParametersCache
##FilePositions
