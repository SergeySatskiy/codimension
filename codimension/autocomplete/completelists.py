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
import logging
import jedi
from utils.globals import GlobalData
from utils.fileutils import getFileContent
from .bufferutils import getEditorTags


def getCallSignatures(editor, fileName):
    """Provides a list of call signatures"""
    line, pos = editor.cursorPosition
    try:
        script = getJediScript(editor.text, line + 1, pos,
                               fileName if fileName else '')
        return script.call_signatures()
    except Exception as exc:
        logging.error('jedi library failed to provide call signatures: ' +
                      str(exc))
    return []


def getDefinitions(editor, fileName):
    """Provides the definition location or None"""
    result = []
    line, pos = editor.cursorPosition

    try:
        script = getJediScript(editor.text, line + 1, pos,
                               fileName if fileName else '')
        definitions = script.goto_definitions()

        # Filter out those on which there is no way to jump
        for definition in definitions:
            path = definition.module_path
            if definition.line is None or definition.column is None:
                continue
            if path is None and definition.in_builtin_module():
                continue
            result.append([path if path else fileName,
                           definition.line, definition.column,
                           definition.type, definition.docstring(),
                           definition.module_name])
    except Exception as exc:
        logging.error('jedi library failed to provide definitions: ' +
                      str(exc))
    return result


def getOccurrences(editor, fileName, line=None, pos=None):
    """Provides occurences for the current editor position"""
    if editor is not None:
        line, pos = editor.cursorPosition
        line += 1
        text = editor.text
    else:
        if pos > 0:
            pos -= 1
        try:
            text = getFileContent(fileName)
        except Exception as exc:
            logging.error('Cannot read file ' + fileName + ': ' + str(exc))
            return []

    try:
        script = getJediScript(text, line, pos,
                               fileName if fileName else '', False)
        return script.usages()
    except Exception as exc:
        logging.error('jedi library failed to provide usages: ' +
                      str(exc))
    return []


def getJediScript(source, line, column, srcPath, needSysPath=True):
    """Provides the jedi Script object considering the current project"""
    jedi.settings.additional_dynamic_modules = []
    paths = sys.path[:] if needSysPath else []

    # This make relative imports resolvable
    if os.path.isabs(srcPath):
        dirName = os.path.dirname(srcPath)
        if dirName not in paths:
            paths.append(dirName)

    project = GlobalData().project
    if not project.isLoaded():
        # Add the other opened files if so
        mainWindow = GlobalData().mainWindow
        for path in mainWindow.editorsManager().getOpenedList():
            if path[0]:
                if path[0].lower().endswith('.py'):
                    jedi.settings.additional_dynamic_modules.append(path[0])
        return jedi.Script(source, line, column, srcPath, sys_path=paths)

    for path in project.getImportDirsAsAbsolutePaths():
        if path not in paths:
            paths.append(path)
    projectDir = project.getProjectDir()
    if projectDir not in paths:
        paths.append(projectDir)

    return jedi.Script(source, line, column, srcPath, sys_path=paths)


def getCompletionList(editor, fileName):
    """Provides a list for completion"""
    if not editor.isPythonBuffer():
        return list(getEditorTags(editor))

    items = []
    line, pos = editor.cursorPosition
    try:
        script = getJediScript(editor.text, line + 1, pos,
                               fileName if fileName else '')

        for item in script.completions():
            items.append(item.name)
    except Exception as exc:
        logging.error('jedi library could not provide completions: ' +
                      str(exc))

    if items:
        return items

    # jedi provided nothing => last resort: words in the editor buffer
    return list(getEditorTags(editor))
