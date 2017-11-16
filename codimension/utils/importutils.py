# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""import utility functions"""

import os
import os.path
import importlib
from ui.qt import QApplication
from cdmpyparser import getBriefModuleInfoFromMemory
from .globals import GlobalData
from .fileutils import isPythonFile


def getImportsList(fileContent):
    """Parses a python file and provides a list imports in it"""
    info = getBriefModuleInfoFromMemory(fileContent)
    return info.imports


def getImportsInLine(fileContent, lineNumber):
    """Provides a list of imports in in the given import line"""
    imports = []
    importsWhat = []
    info = getBriefModuleInfoFromMemory(str(fileContent))
    for importObj in info.imports:
        if importObj.line == lineNumber:
            if importObj.name not in imports:
                imports.append(importObj.name)
            for whatObj in importObj.what:
                if whatObj.name not in importsWhat:
                    importsWhat.append(whatObj.name)
    return imports, importsWhat


def __scanDir(prefix, path, infoLabel=None):
    """Recursive scan for modules"""
    if infoLabel is not None:
        infoLabel.setText("Scanning " + path + "...")
        QApplication.processEvents()

    result = []
    for item in os.listdir(path):
        if item in [".svn", ".cvs", ".git", ".hg"]:
            continue
        if os.path.isdir(path + item):
            result += __scanDir(prefix + item + ".",
                                path + item + os.path.sep,
                                infoLabel)
            continue

        if not isPythonFile(path + item):
            continue
        if item.startswith('__init__.'):
            if prefix != "":
                result.append(prefix[: -1])
            continue

        nameParts = item.split('.')
        result.append(prefix + nameParts[0])
    return result


def buildDirModules(path, infoLabel=None):
    """Builds a list of modules how they may appear in the import statements"""
    abspath = os.path.abspath(path)
    if not os.path.exists(abspath):
        raise Exception("Cannot build list of modules for not "
                        "existed dir (" + path + ")")
    if not os.path.isdir(abspath):
        raise Exception("Cannot build list of modules. The path " + path +
                        " is not a directory.")
    if not abspath.endswith(os.path.sep):
        abspath += os.path.sep
    return __scanDir("", abspath, infoLabel)



def __resolveImport(importObj, baseAndProjectPaths, result, errors):
    """Resolves imports like: 'import x'"""
    try:
        try:
            spec = importlib.util.find_spec(importObj.name)
            if spec:
                # Found system wide or in venv
                result.append([importObj.name, spec.origin, []])
                return
        except:
            pass

        # Try in the base path and the project imports if so
        spec = importlib.machinery.PathFinder.find_spec(importObj.name,
                                                        baseAndProjectPaths)
        if spec:
            result.append([importObj.name, spec.origin, []])
        else:
            errors.append("Could not resolve 'import " + importObj.name +
                          "' at line " + str(importObj.line))
    except:
        errors.append("Could not resolve 'import " + importObj.name +
                      "' at line " + str(importObj.line))


def __resolveFromImport(importObj, basePath, baseAndProjectPaths,
                        result, errors):
    """Resolves imports like: 'from x import y'"""
    try:
        try:
            spec = importlib.util.find_spec(importObj.name)
            if spec:
                # Found system wide or in venv
                result.append([importObj.name, spec.origin,
                               [what.name for what in importObj.what]])
                return
        except:
            pass

        # Try in the base path and the project imports if so
        try:
            spec = importlib.machinery.PathFinder.find_spec(
                importObj.name, baseAndProjectPaths)
            if spec:
                result.append([importObj.name, spec.origin,
                               [what.name for what in importObj.what]])
                return
        except:
            pass

        # try the name as a directory name
        project = GlobalData().project
        importNameAsPath = importObj.name.replace('.', os.path.sep)
        pathsToSearch = [os.path.normpath(basePath + os.path.sep +
                                          importNameAsPath)]
        if project.isLoaded():
            for importPath in project.getImportDirsAsAbsolutePaths():
                pathsToSearch.append(
                    os.path.normpath(importPath + os.path.sep +
                                     importNameAsPath))

        for what in importObj.what:
            spec = importlib.machinery.PathFinder.find_spec(
                what.name, pathsToSearch)
            if spec:
                result.append([what.name, spec.origin, []])
            else:
                errors.append("Could not resolve 'from " +
                              importObj.name + " import " + what.name +
                              "' at line " + str(what.line))
    except:
        errors.append("Could not resolve 'from " +
                      importObj.name + " import ...' at line " +
                      str(importObj.line))


def __resolveRelativeImport(importObj, basePath, result, errors):
    """Resolves imports like: 'from ..x import y'"""
    try:
        path = basePath
        current = importObj.name[1:]
        error = False
        while current.startswith('.'):
            if not path:
                error = True
                break
            current = current[1:]
            path = os.path.dirname(path)
        if error:
            errors.append("Could not resolve 'from " +
                          importObj.name + " import ...' at line " +
                          str(importObj.line))
            return

        if not path:
            path = os.path.sep  # reached the root directory

        try:
            spec = importlib.machinery.PathFinder.find_spec(
                current, [os.path.normpath(path)])
            if spec:
                result.append([importObj.name, spec.origin,
                               [what.name for what in importObj.what]])
                return
        except:
            pass

        # try the name as a directory name
        importNameAsPath = current.replace('.', os.path.sep)
        pathsToSearch = [os.path.normpath(path + os.path.sep +
                                          importNameAsPath)]

        for what in importObj.what:
            spec = importlib.machinery.PathFinder.find_spec(what.name,
                                                            pathsToSearch)
            if spec:
                result.append([what.name, spec.origin, []])
            else:
                errors.append("Could not resolve 'from " +
                              importObj.name + " import " + what.name +
                              "' at line " + str(what.line))
    except:
        errors.append("Could not resolve 'from " +
                      importObj.name + " import ...' at line " +
                      str(importObj.line))


def resolveImports(fileName, imports):
    """Resolves a list of imports.

    fileName: the file where the imports come from
    imports: a list of the Import classes coming from the cdmpyparser module

    return: ([resolved imports], [errors])
    Each resolved import is a triple [name, path, [what imported]]
        path could be .py or .so or None or 'built-in'
    errors is a list of strings
    """
    errors = []
    result = []

    basePath = os.path.dirname(fileName)    # no '/' at the end
    project = GlobalData().project

    baseAndProjectPaths = [basePath]
    if project.isLoaded():
        baseAndProjectPaths += project.getImportDirsAsAbsolutePaths()

    for importObj in imports:
        if not importObj.what:
            # case 1: import x1, y1
            __resolveImport(importObj, baseAndProjectPaths, result, errors)
        elif not importObj.name.startswith('.'):
            # case 2: from i2 import x2, y2
            __resolveFromImport(importObj, baseAndProjectPaths, basePath,
                                result, errors)
        else:
            # case 3: from .i3 import x3, y3
            #      or from . import x4, y4
            __resolveRelativeImport(importObj, basePath, result, errors)

    return result, errors


def isImportModule(info, name):
    """Returns the list of really matched modules"""
    matches = []
    for item in info.imports:
        # We are interested here in those which import a module
        if item.what:
            continue

        if item.alias == "":
            if item.name == name:
                if name not in matches:
                    matches.append(name)
        else:
            if item.alias == name:
                if item.name not in matches:
                    matches.append(item.name)
    return matches


def isImportedObject(info, name):
    """Returns a list of matched modules with the real name"""
    matches = []
    for item in info.imports:
        # We are interested here in those which import an object
        if not item.what:
            continue

        for whatItem in item.what:
            if whatItem.alias == "":
                if whatItem.name == name:
                    if name not in matches:
                        matches.append([item.name, name])
            else:
                if whatItem.alias == name:
                    if whatItem.name not in matches:
                        matches.append([item.name, whatItem.name])
    return matches
