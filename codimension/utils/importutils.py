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
from ui.qt import QApplication
from cdmpyparser import (getBriefModuleInfoFromMemory,
                         getBriefModuleInfoFromFile)
from autocomplete.completelists import (getSystemWideModules,
                                        getProjectSpecificModules)
from .globals import GlobalData
from .fileutils import isPythonFile


def getImportsList(fileContent):
    """Parses a python file and provides a list imports in it"""
    result = []
    info = getBriefModuleInfoFromMemory(fileContent)
    for importObj in info.imports:
        if importObj.name not in result:
            result.append(importObj.name)
    return result


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


def resolveImport(basePath, importString):
    """Resolves a single import"""
    result = resolveImports(basePath, [importString])
    if result:
        return result[0][1]
    return ""


def resolveImports(basePath, imports):
    """Resolves a list of imports"""
    specificModules = getProjectSpecificModules(basePath)
    systemwideModules = getSystemWideModules()

    result = []
    for item in imports:
        if item.startswith('.'):
            # This is a relative import
            current = item[1:]
            path = basePath
            while current.startswith('.'):
                current = current[1:]
                path = os.path.dirname(path)
            if os.path.exists(path + os.path.sep + current + '.py'):
                result.append([item, path + os.path.sep + current + '.py'])
            continue

        try:
            path = specificModules[item]
            if path is not None:
                if os.path.isdir(path):
                    path += os.path.sep + "__init__.py"
                    if not os.path.exists(path):
                        continue
                else:
                    if not path.endswith(".py"):
                        continue
                result.append([item, path])
            continue
        except:
            pass

        try:
            path = systemwideModules[item]
            if path is not None:
                if os.path.isdir(path):
                    path += os.path.sep + "__init__.py"
                    if not os.path.exists(path):
                        continue
                else:
                    if not path.endswith(".py"):
                        continue
                result.append([item, path])
        except:
            pass
    return result


def getImportedNameDefinitionLine(path, name, info=None):
    """Searches for the given name in the given file and provides its
       line number. -1 if not found.
       Only top level names are searched through.
    """
    if info is None:
        mainWindow = GlobalData().mainWindow
        widget = mainWindow.getWidgetForFileName(os.path.realpath(path))
        if widget is None:
            # The file is not opened now
            info = getBriefModuleInfoFromFile(path)
        else:
            editor = widget.getEditor()
            info = getBriefModuleInfoFromMemory(editor.text())
    # Check the object names
    for classObj in info.classes:
        if classObj.name == name:
            return classObj.line
    for funcObj in info.functions:
        if funcObj.name == name:
            return funcObj.line
    for globalObj in info.globals:
        if globalObj.name == name:
            return globalObj.line
    return -1


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
