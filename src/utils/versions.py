# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

""" Provides versions of various components used by codimension """

from os.path import abspath
from distutils.spawn import find_executable


def getCodimensionVersion():
    """Provides the IDE version"""
    from globals import GlobalData
    import sys
    return GlobalData().version, abspath(sys.argv[0])


def getPythonParserVersion():
    """Provides the python parser version"""
    import cdmbriefparser
    return cdmbriefparser.getVersion(), abspath(cdmbriefparser.__file__)


def getControlFlowParserVersion():
    """Provides the python control flow version"""
    import cdmcf
    return cdmcf.VERSION, abspath(cdmcf.__file__)


def getPythonInterpreterVersion():
    """Provides the python interpreter version"""
    import sys
    return ".".join([str(sys.version_info.major),
                     str(sys.version_info.minor),
                     str(sys.version_info.micro)]), sys.executable


def getPyQtVersion():
    """Provides the PyQt version"""
    import PyQt5.QtCore
    return str(PyQt5.QtCore.PYQT_VERSION_STR), abspath(PyQt5.QtCore.__file__)


def getQtVersion():
    """Provides the Qt version"""
    from ui.qt import QT_VERSION_STR
    return QT_VERSION_STR


def getPyFlakesVersion():
    """Provides the pyflakes library version"""
    import pyflakes
    return pyflakes.__version__, abspath(pyflakes.__file__)


def getFileMagicVersion():
    """Provides the file magic library"""
    import magic
    return "Unknown", abspath(magic.__file__)


def getGraphvizVersion():
    """Provides the graphviz version"""
    from globals import GlobalData
    if not GlobalData().graphvizAvailable:
        return "Not installed", None

    path = find_executable("dot")
    if not path:
        return "Not installed", None

    from misc import safeRunWithStderr
    try:
        stdOut, stdErr = safeRunWithStderr( [ path, "-V" ] )
        for line in stdErr.splitlines():
            # E.g. dot - graphviz version 2.26.3 (20100126.1600)
            line = line.strip()
            if line.startswith("dot - graphviz version "):
                line = line.replace("dot - graphviz version ", "")
                parts = line.split(" ")
                if len(parts) == 2 and parts[0][0].isdigit():
                    return parts[0], path
    except:
        return "Not installed", None
    return "could not determine", path


def getGprof2dotVersion():
    """Provides gprof2dot version"""
    from settings import thirdpartyDir
    from misc import safeRun
    import os.path
    gprof2dot = thirdpartyDir + "gprof2dot" + os.path.sep + "gprof2dot.py"
    try:
        for line in safeRun([gprof2dot, "--version"]).splitlines():
            # E.g. gprof2dot.py 1.0
            line = line.strip()
            if line.startswith("gprof2dot"):
                parts = line.split(" ")
                if len(parts) == 2 and parts[1][0].isdigit():
                    return parts[1], gprof2dot
    except:
        return "Not installed", None
    return "could not determine", gprof2dot


def getYapsyVersion():
    """Provides yapsy version"""
    import yapsy
    return yapsy.__version__, abspath(yapsy.__file__)


def getComponentInfo():
    """Provides major codimension components information"""
    components = []
    # Each item contains: <pretty name>, <version>,
    #                     <url>, <patched>, <license name>,
    #                     <license url>
    # A list is used to have some kind of priority ordering
    version, path = getCodimensionVersion()
    components.append(("Codimension IDE", version,
                       "http://codimension.org/", None,
                       "GPL-3.0",
                       "http://www.gnu.org/licenses/gpl-3.0.html",
                       path))
    version, path = getPythonParserVersion()
    components.append(("Codimension python parser", version,
                       "http://codimension.org/", None,
                       "GPL-3.0",
                       "http://www.gnu.org/licenses/gpl-3.0.html",
                       path))
    version, path = getControlFlowParserVersion()
    components.append(("Codimension python control flow parser",
                       version,
                       "http://codimension.org/", None,
                       "GPL-3.0",
                       "http://www.gnu.org/licenses/gpl-3.0.html",
                       path))
    version, path = getPythonInterpreterVersion()
    components.append(("Python interpreter", version,
                       "http://www.python.org/", None,
                       "Open source license",
                       "http://www.python.org/psf/license/",
                       path))
    version, path = getPyQtVersion()
    components.append(("PyQt", version,
                       "http://www.riverbankcomputing.com/software/pyqt/intro",
                       None, "GPL-2.0/GPL-3.0/Commercial/Embedded",
                       "http://www.riverbankcomputing.com/software/pyqt/license",
                       path))
    components.append(("Qt", getQtVersion(),
                       "http://qt-project.org/", None,
                       "LGPL-2.1/Commercial",
                       "http://www.gnu.org/licenses/lgpl-2.1.html",
                       None))
    version, path = getPyFlakesVersion()
    components.append(("pyflakes", version,
                       "https://pypi.python.org/pypi/pyflakes", None,
                       "pyflakes license", "see the package",
                       path))
    version, path = getFileMagicVersion()
    components.append(("filemagic", version,
                       "https://pypi.python.org/pypi/filemagic/", None,
                       "Apache License 2.0",
                       "http://www.apache.org/licenses/LICENSE-2.0.html",
                       path))
    version, path = getGraphvizVersion()
    components.append(("graphviz", version,
                       "http://www.graphviz.org/", None,
                       "Eclipse Public License 1.0",
                       "http://www.graphviz.org/License.php",
                       path))
    version, path = getGprof2dotVersion()
    components.append(("gprof2dot", version,
                       "http://freecode.com/projects/gprof2dot_py", True,
                       "LGPL", "http://www.gnu.org/licenses/lgpl.html",
                       path))
    version, path = getYapsyVersion()
    components.append(("yapsy", version,
                       "http://yapsy.sourceforge.net", None,
                       "BSD License",
                       "http://opensource.org/licenses/bsd-license.php",
                       path))
    return components
