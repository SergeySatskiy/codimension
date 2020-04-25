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
import os.path
import sys
import logging
import jedi
from jedi.api.project import Project
from utils.globals import GlobalData
from utils.fileutils import getFileContent
from ui.qt import QDir
from .bufferutils import getEditorTags


# Global variables to avoid creating a jedi project every time
jediProject = None

def getJediProject(force=False):
    """Provides a jedi project"""
    global jediProject

    if force or jediProject is None:
        project = GlobalData().project
        if project.isLoaded():
            jPath = project.getProjectDir()

            addedPaths = []
            for path in project.getImportDirsAsAbsolutePaths():
                if path not in addedPaths:
                    addedPaths.append(path)
            projectDir = project.getProjectDir()
            if projectDir not in addedPaths:
                addedPaths.append(projectDir)

        else:
            jPath = os.path.realpath(QDir.homePath())
            addedPaths = ()

        jediProject = Project(jPath,
                              sys_path=GlobalData().originalSysPath[:],
                              added_sys_path=addedPaths)

    return jediProject


def getJediScript(code, srcPath):
    """Provides the jedi Script object considering the current project"""
    if not os.path.isabs(srcPath):
        # Pretend it is in the user home dir
        srcPath = os.path.realpath(QDir.homePath()) + os.path.sep + srcPath
    return jedi.Script(code=code, path=srcPath, project=getJediProject())


def getCallSignatures(editor, fileName):
    """Provides a list of call signatures"""
    line, pos = editor.cursorPosition
    try:
        script = getJediScript(editor.text, fileName)
        return script.get_signatures(line=line + 1, column=pos)
    except Exception as exc:
        logging.error('jedi library failed to provide call signatures: ' +
                      str(exc))
    return []


def getDefinitions(editor, fileName):
    """Provides the definition location or None"""
    result = []
    line, pos = editor.cursorPosition

    try:
        script = getJediScript(editor.text, fileName)
        definitions = script.infer(line=line + 1, column=pos)

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
        script = getJediScript(text, fileName)
        return script.get_references(line=line, column=pos)
    except Exception as exc:
        logging.error('jedi library failed to provide usages: ' +
                      str(exc))
    return []


def getCompletionList(editor, fileName):
    """Provides a list for completion"""
    if not editor.isPythonBuffer():
        return list(getEditorTags(editor))

    items = []
    line, pos = editor.cursorPosition
    try:
        script = getJediScript(editor.text, fileName)

        for item in script.complete(line=line + 1, column=pos):
            items.append(item.name)
    except Exception as exc:
        logging.error('jedi library could not provide completions: ' +
                      str(exc))

    if items:
        return items

    # jedi provided nothing => last resort: words in the editor buffer
    return list(getEditorTags(editor))

