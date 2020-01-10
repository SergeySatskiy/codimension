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

# pylint: disable=W0702
# pylint: disable=W0703

import sys
import os
import os.path
import importlib
from cdmpyparser import getBriefModuleInfoFromMemory
from ui.qt import QApplication
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


def __appendResult(value, result):
    """Appends to the results if it is unique"""
    if not value in result:
        result.append(value)


def __resolveImport(importObj, baseAndProjectPaths, result, errors):
    """Resolves imports like: 'import x'"""

    # import x.y
    # Could be (priority wise)
    # I:   <dir>/x/y/__init__.py
    # II:  <dir>/x/y.py

    oldSysPath = sys.path
    sys.path = GlobalData().originalSysPath + baseAndProjectPaths

    try:
        spec = importlib.util.find_spec(importObj.name)
        if spec:
            if spec.has_location:
                __appendResult([importObj.name, spec.origin, []], result)
                return
            if spec.loader is not None:
                if 'builtin' in spec.loader.__name__.lower():
                    __appendResult([importObj.name, 'built-in', []], result)
                    return

            # Something unknown; it's not clear what to do
    except:
        pass
    finally:
        sys.path = oldSysPath

    errors.append("Could not resolve 'import " + importObj.name +
                  "' at line " + str(importObj.line))


def __resolveFrom(importObj, importName, basePath, result, errors):
    """Common resolution imports like 'from [.]x import y"""
    try:
        spec = importlib.util.find_spec(importName, basePath)
        if spec:
            if spec.has_location:
                __appendResult([importObj.name, spec.origin,
                                [what.name for what in importObj.what]],
                               result)
                return

            # No location but it could be a builtin module
            if spec.loader is not None:
                if 'builtin' in spec.loader.__name__.lower():
                    __appendResult([importObj.name, 'built-in',
                                    [what.name for what in importObj.what]],
                                   result)
                    return

                # Unknown loader so not clear what to do
                errors.append("Could not resolve 'from " +
                              importObj.name + " import ..." +
                              "' at line " + str(importObj.line))
                return

            # Loader is None but found something. Maybe it is a submodule
            if spec.submodule_search_locations:
                for what in importObj.what:
                    impName = importName + '.' + what.name
                    found = False
                    try:
                        spec = importlib.util.find_spec(impName, basePath)
                        if spec:
                            visibleName = importObj.name + '.' + what.name
                            if spec.has_location:
                                __appendResult([visibleName, spec.origin, []],
                                               result)
                                found = True
                            elif spec.loader is not None:
                                if 'builtin' in spec.loader.__name__.lower():
                                    __appendResult(
                                        [visibleName, 'builtin module', []],
                                        result)
                                    found = True
                    except:
                        pass
                    if not found:
                        errors.append("Could not resolve 'from " +
                                      importObj.name + " import " +
                                      what.name + "' at line " +
                                      str(importObj.line))
                return
    except:
        pass

    errors.append("Could not resolve 'from " +
                  importObj.name + " import ...' at line " +
                  str(importObj.line))


def __resolveFromImport(importObj, basePath, baseAndProjectPaths,
                        result, errors):
    """Resolves imports like: 'from x import y'"""

    # from x.y import z
    # Could be (priority wise)
    # I:    <dir>/x/y/__init__.py  -> z
    # II:   <dir>/x/y.py  -> z
    # III:  <dir>/x/y/z/__init__.py
    # IV:   <dir>/x/y/z.py

    oldSysPath = sys.path
    sys.path = GlobalData().originalSysPath + baseAndProjectPaths

    __resolveFrom(importObj, importObj.name, basePath, result, errors)

    sys.path = oldSysPath


def __resolveRelativeImport(importObj, basePath, result, errors):
    """Resolves imports like: 'from ..x import y'"""

    # from ...x.y import z
    # Could be (priority wise)
    # I:    <dir>/x/y/__init__.py  -> z
    # II:   <dir>/x/y.py  -> z
    # III:  <dir>/x/y/z/__init__.py
    # IV:   <dir>/x/y/z.py

    if basePath is None:
        errors.append("Could not resolve 'from " + importObj.name +
                      " import ...' at line " + str(importObj.line) +
                      " because the editing buffer has not been saved yet")
    else:
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

        # This is a relative import so only one path needs to be searched
        oldSysPath = sys.path
        sys.path = [path]

        __resolveFrom(importObj, current, path, result, errors)

        sys.path = oldSysPath


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

    origImporterCacheKeys = set(sys.path_importer_cache.keys())
    origSysModulesKeys = set(sys.modules.keys())

    if fileName:
        basePath = os.path.dirname(fileName)    # no '/' at the end
        baseAndProjectPaths = [basePath]
    else:
        basePath = None
        baseAndProjectPaths = []

    project = GlobalData().project
    if project.isLoaded():
        for importDir in project.getImportDirsAsAbsolutePaths():
            if importDir not in baseAndProjectPaths:
                baseAndProjectPaths.append(importDir)

    for importObj in imports:
        if not importObj.what:
            # case 1: import x1, y1
            __resolveImport(importObj, baseAndProjectPaths, result, errors)
        elif not importObj.name.startswith('.'):
            # case 2: from i2 import x2, y2
            __resolveFromImport(importObj, basePath, baseAndProjectPaths,
                                result, errors)
        else:
            # case 3: from .i3 import x3, y3
            #      or from . import x4, y4
            __resolveRelativeImport(importObj, basePath, result, errors)

    importlib.invalidate_caches()

    newImporterCacheKeys = set(sys.path_importer_cache.keys())
    diff = newImporterCacheKeys - origImporterCacheKeys
    for key in diff:
        del sys.path_importer_cache[key]

    newSysModulesKeys = set(sys.modules.keys())
    diff = newSysModulesKeys - origSysModulesKeys
    for key in diff:
        del sys.modules[key]

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
