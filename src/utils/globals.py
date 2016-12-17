#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Global data singleton"""

import sys
import os
from os.path import relpath, dirname, sep, realpath, isdir, exists, isfile
from subprocess import check_output, STDOUT
from distutils.version import StrictVersion
from plugins.manager.pluginmanager import CDMPluginManager
from .project import CodimensionProject
from .briefmodinfocache import BriefModuleInfoCache
from .settings import SETTINGS_DIR, Settings


# This function needs to have a rope project built smart
def getSubdirs(path, baseNamesOnly=True, excludePythonModulesDirs=True):
    " Provides a list of sub directories for the given path "
    subdirs = []
    try:
        path = realpath(path) + sep
        for item in os.listdir(path):
            candidate = path + item
            if isdir(candidate):
                if excludePythonModulesDirs:
                    modFile1 = candidate + sep + "__init__.py"
                    modFile2 = candidate + sep + "__init__.py3"
                    if exists(modFile1) or exists(modFile2):
                        continue
                if baseNamesOnly:
                    subdirs.append(item)
                else:
                    subdirs.append(candidate)
    except:
        pass
    return subdirs


class GlobalDataWrapper:

    """Global data singleton"""

    def __init__(self):
        self.application = None
        self.splash = None
        self.mainWindow = None
        self.skin = None
        self.screenWidth = 0
        self.screenHeight = 0
        self.version = "unknown"
        self.project = CodimensionProject()

        self.pluginManager = CDMPluginManager()

        self.briefModinfoCache = BriefModuleInfoCache()

        self.pylintAvailable = self.__checkPylint()
        self.graphvizAvailable = self.__checkGraphviz()

        self.pylintVersion = None
        if self.pylintAvailable:
            self.pylintVersion = self.__getPylintVersion()
            if self.pylintVersion is None:
                self.pylintAvailable = False

    def getRunParameters(self, fileName):
        """Provides the run parameters"""
        if self.project.isLoaded():
            if self.project.isProjectFile(fileName):
                key = relpath(fileName, dirname(self.project.fileName))
            else:
                key = fileName
            return self.project.getRunParameters(key)

        # No project loaded
        return Settings().getRunParameters(fileName)

    def addRunParams(self, fileName, params):
        """Registers new latest run parameters"""
        if self.project.isLoaded():
            if self.project.isProjectFile(fileName):
                key = relpath(fileName, dirname(self.project.fileName))
            else:
                key = fileName
            self.project.addRunParameters(key, params)
        else:
            # No project loaded
            Settings().addRunParameters(fileName, params)

    def getProfileOutputPath(self):
        """Provides the path to the profile output file"""
        if self.project.isLoaded():
            return self.project.userProjectDir + 'profile.out'

        # No project loaded
        return SETTINGS_DIR + 'profile.out'

    def getProjectImportDirs(self):
        """Provides a list of the project import dirs if so"""
        if not self.project.isLoaded():
            return []
        return self.project.getImportDirsAsAbsolutePaths()

    def isProjectScriptValid(self):
        """True if the project script valid"""
        scriptName = self.project.getProjectScript()
        if not exists(scriptName):
            return False
        if not isfile(scriptName):
            return False

        from .fileutils import getFileProperties
        mime, _, _, _ = getFileProperties(scriptName)
        return 'python' in mime

    def getFileLineDocstring(self, fName, line):
        """Provides a docstring if so for the given file and line"""
        from .fileutils import getFileProperties
        mime, _, _, _ = getFileProperties(fName)
        if 'python' not in mime:
            return ""

        infoCache = self.briefModinfoCache

        def checkFuncObject(obj, line):
            """Checks docstring for a function or a class"""
            if obj.line == line or obj.keywordLine == line:
                if obj.docstring is None:
                    return True, ''
                return True, obj.docstring.text
            for item in obj.classes + obj.functions:
                found, docstring = checkFuncObject(item, line)
                if found:
                    return True, docstring
            return False, ''

        try:
            info = infoCache.get(fName)
            for item in info.classes + info.functions:
                found, docstring = checkFuncObject(item, line)
                if found:
                    return docstring
        except:
            pass
        return ''

    def getModInfo(self, path):
        """Provides a module info for the given file"""
        from .fileutils import getFileProperties
        mime, _, _, _ = getFileProperties(path)

        if 'python' not in mime:
            raise Exception('Trying to parse non-python file: ' + path)
        return self.briefModinfoCache.get(path)

    @staticmethod
    def __checkGraphviz():
        """Checks if the graphviz available"""
        if 'win' in sys.platform.lower():
            return os.system('which dot > /NUL 2>&1') == 0
        return os.system('which dot > /dev/null 2>&1') == 0

    @staticmethod
    def __checkPylint():
        """Checks if pylint is available"""
        if 'win' in sys.platform.lower():
            return os.system('which pylint > /NUL 2>&1') == 0
        return os.system('which pylint > /dev/null 2>&1') == 0

    @staticmethod
    def __getPylintVersion():
        " Provides the pylint version "
        output = check_output("pylint --version; exit 0",
                              stderr=STDOUT, shell=True)
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("pylint "):
                version = line.replace("pylint", "").replace(",", "")
                try:
                    return StrictVersion(version.strip())
                except:
                    return None
        return None


globalsSingleton = GlobalDataWrapper()


def GlobalData():
    """Global singleton access"""
    return globalsSingleton
