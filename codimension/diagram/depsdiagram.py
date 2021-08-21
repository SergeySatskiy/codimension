# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2020 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Dependencies diagram"""

import sys
import os.path
from utils.importutils import getImportsList, getImportResolutions
from utils.globals import GlobalData


def __isLocalOrProject(fName, resolvedPath):
    """True if the module is a project one or is in the nested dirs"""
    if GlobalData().project.isProjectFile(resolvedPath):
        return True

    resolvedDir = os.path.dirname(resolvedPath)
    baseDir = os.path.dirname(fName)
    return resolvedDir.startswith(baseDir)


def __isSystem(resolvedPath):
    """True if the module belongs to the system or venv path"""
    # This check must be done after checking for local/project
    # because a project may insert its paths into sys.path.
    resolvedDir = os.path.dirname(resolvedPath)
    for path in sys.path:
        if path:
            if resolvedDir.startswith(path):
                return True
    return False


def collectImportResolutions(content, fileName):
    """Provides classified import information and errors if so"""
    depClasses = {'system': [],
                  'project': [],
                  'other': [],
                  'unresolved': [],
                  'totalCount': 0,
                  'errors': []}
    try:
        for resolution in getImportResolutions(fileName,
                                               getImportsList(content)):
            if resolution.isResolved():
                if resolution.builtIn:
                    depClasses['system'].append(resolution)
                elif __isLocalOrProject(fileName, resolution.path):
                    depClasses['project'].append(resolution)
                elif __isSystem(resolution.path):
                    depClasses['system'].append(resolution)
                else:
                    depClasses['unresolved'].append(resolution)
            else:
                depClasses['unresolved'].append(resolution)

            depClasses['totalCount'] += 1
    except Exception as exc:
        depClasses['errors'].append(str(exc))

    return depClasses

