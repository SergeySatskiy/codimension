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

"""Utilities to build completeion lists to suggest to the user"""


import os
import sys
import jedi
from utils.globals import GlobalData
from .listmodules import getSysModules, getModules
from .bufferutils import getEditorTags


__systemwideModules = {}
__systemwideInitialized = False


def buildSystemWideModulesList():
    """Builds a map for the system wide modules"""
    global __systemwideModules
    global __systemwideInitialized

    if not __systemwideInitialized:
        __systemwideModules = getSysModules()
        __systemwideInitialized = True


def getSystemWideModules():
    """Provides a list of system wide modules"""
    buildSystemWideModulesList()
    return __systemwideModules


def getProjectSpecificModules(path='', onlySpecified=False):
    """Provides a dictionary of the project specific modules"""
    specificModules = {}
    importDirs = []

    if not onlySpecified:
        importDirs = GlobalData().getProjectImportDirs()
        for importPath in importDirs:
            specificModules.update(getModules(importPath))

        projectFile = GlobalData().project.fileName
        if projectFile != "":
            basedir = os.path.dirname(projectFile)
            if basedir not in importDirs:
                importDirs.append(basedir)
                specificModules.update(getModules(basedir))

    if path and os.path.isabs(path):
        path = os.path.normpath(path)
        basedir = ""
        if os.path.isfile(path):
            basedir = os.path.dirname(path)
        elif os.path.isdir(path):
            basedir = path

        if basedir and basedir not in importDirs:
            specificModules.update(getModules(basedir))

    return specificModules


def getCalltipAndDoc(fileName, editor, position=None, tryQt=False):
    """Provides a calltip and docstring"""
    try:
        if position is None:
            position = editor.currentPosition()
        text = editor.text()

        calltip = None
        docstring = None

        # Note: should be replaced with jedi

        return calltip, docstring
    except:
        return None, None


def getDefinitions(editor, fileName):
    """Provides the definition location or None"""
    line, pos = editor.cursorPosition
    script = getJediScript(editor.text, line + 1, pos,
                           fileName if fileName else '')
    definitions = script.goto_definitions()

    # Filter out those on which there is no way to jump
    result = []
    for definition in definitions:
        path = definition.module_path
        if definition.line is None or definition.column is None:
            continue
        if path is None and definition.in_builtin_module():
            continue
        result.append([path if path else fileName,
                       definition.line, definition.column])
    return result


def _switchFileAndBuffer(fileName, editor):
    """Saves the original file under a temporary name and
       writes the content into the original file if needed
    """
    if editor.isModified():
        content = editor.text()
        dirName = os.path.dirname(fileName)
        fName = os.path.basename(fileName)
        temporaryName = dirName + os.path.sep + "." + fName + ".rope-temp"
        os.rename(fileName, temporaryName)

        f = open(fileName, "wb")
        try:
            f.write(content)
        except:
            # Revert the change back
            f.close()
            os.rename(temporaryName, fileName)
            raise
        f.close()
        return temporaryName

    # The file is not modified, no need to create a temporary one
    return fileName


def _restoreOriginalFile(fileName, temporaryName, editor):
    """Removes the temporary file and validete the project if needed"""
    if editor.isModified():
        if temporaryName != "":
            os.rename(temporaryName, fileName)

def _buildOccurrencesImplementationsResult(locations):
    """Cleans up the rope locations"""
    result = []
    for loc in locations:
        path = os.path.realpath(loc.resource.real_path)
        result.append([path, loc.lineno])
    return result


def getOccurrences(fileName, editorOrPosition, throwException=False):
    """Provides occurences for the current editor position or
       for a position in a file
    """
    if type(editorOrPosition) == type(1):
        # This is called for a position in the existing file
        return getOccurencesForFilePosition(fileName, editorOrPosition,
                                            throwException)
    return getOccurencesForEditor(fileName, editorOrPosition,
                                  throwException)


def getOccurencesForEditor(fileName, editor, throwException):
    """Provides a list of the current token occurences"""
    temporaryName = ""
    result = []
    nameToSearch = ""
    try:
        temporaryName = _switchFileAndBuffer(fileName, editor)
        position = editor.currentPosition()
        resource = path_to_resource(ropeProject, fileName)

        nameToSearch = worder.get_name_at(resource, position)
        result = find_occurrences(ropeProject, resource, position, True)
    except:
        if throwException:
            raise

    _restoreOriginalFile(fileName, temporaryName, editor)
    return nameToSearch, _buildOccurrencesImplementationsResult(result)


def getOccurencesForFilePosition(fileName, position, throwException):
    """Provides a list of the token at position occurences"""
    result = []
    try:
        # Note: replace with jedi implementation
        pass
    except:
        if throwException:
            raise
    return _buildOccurrencesImplementationsResult(result)


def getJediScript(source, line, column, srcPath):
    """Provides the jedi Script object considering the current project"""
    jedi.settings.additional_dynamic_modules = []

    project = GlobalData().project
    if not project.isLoaded:
        # Add the other opened files if so
        mainWindow = GlobalData().mainWindow
        for path in mainWindow.editorsManager().getOpenedList():
            if path[0]:
                if path[0].lower().endswith('.py'):
                    jedi.settings.additional_dynamic_modules.append(path[0])
        return jedi.Script(source, line, column, srcPath)

    # need to deal with sys.path
    paths = sys.path[:]
    for path in project.getImportDirsAsAbsolutePaths():
        if path not in paths:
            paths.append(path)
    projectDir = project.getProjectDir()
    if projectDir not in paths:
        paths.append(projectDir)

    return jedi.Script(source, line, column, sys_path=paths)


def getCompletionList(editor, fileName):
    """Provides a list for completion"""
    if not editor.isPythonBuffer():
        return list(getEditorTags(editor))

    line, pos = editor.cursorPosition
    script = getJediScript(editor.text, line + 1, pos,
                           fileName if fileName else '')

    items = []
    for item in script.completions():
        items.append(item.name)
    if items:
        return items

    # jedi provided nothing => last resort: words in the editor buffer
    return list(getEditorTags(editor))
