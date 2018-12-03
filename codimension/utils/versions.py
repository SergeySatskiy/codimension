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
from subprocess import getstatusoutput
import pkg_resources
import logging


def getPackageVersionAndLocation(name):
    """Provides a package version"""
    try:
        return pkg_resources.get_distribution(name).version, \
               pkg_resources.get_distribution(name).location
    except pkg_resources.DistributionNotFound as exc:
        logging.error(str(exc))
        return None, None


def getCodimensionVersion():
    """Provides the IDE version"""
    from .globals import GlobalData
    import sys
    return GlobalData().version, abspath(sys.argv[0])


def getPythonInterpreterVersion():
    """Provides the python interpreter version"""
    import sys
    return ".".join([str(sys.version_info.major),
                     str(sys.version_info.minor),
                     str(sys.version_info.micro)]), sys.executable


def getQtVersion():
    """Provides the Qt version"""
    from ui.qt import QT_VERSION_STR
    return QT_VERSION_STR


def getGraphvizVersion():
    """Provides the graphviz version"""
    from .globals import GlobalData
    if not GlobalData().graphvizAvailable:
        return "Not installed", None

    path = find_executable("dot")
    if not path:
        return "Not installed", None

    try:
        status, output = getstatusoutput(path + ' -V')
        if status != 0:
            return "Not installed", None

        for line in output.splitlines():
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
    version, path = getPackageVersionAndLocation('cdmpyparser')
    components.append(("Codimension python parser", version,
                       "http://codimension.org/", None,
                       "GPL-3.0",
                       "http://www.gnu.org/licenses/gpl-3.0.html",
                       path))
    version, path = getPackageVersionAndLocation('cdmcfparser')
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
    version, path = getPackageVersionAndLocation('PyQt5')
    components.append(("PyQt", version,
                       "http://www.riverbankcomputing.com/software/pyqt/intro",
                       None, "GPL-2.0/GPL-3.0/Commercial/Embedded",
                       "http://www.riverbankcomputing.com/software/pyqt/license",
                       path))
    version, path = getPackageVersionAndLocation('qutepart')
    components.append(("qutepart", version,
                       "https://github.com/andreikop/qutepart",
                       None,
                       "LGPL-2.1",
                       "http://www.gnu.org/licenses/lgpl-2.1.html",
                       path))
    components.append(("Qt", getQtVersion(),
                       "http://qt-project.org/", None,
                       "LGPL-2.1/Commercial",
                       "http://www.gnu.org/licenses/lgpl-2.1.html",
                       None))
    version, path = getPackageVersionAndLocation('pyflakes')
    components.append(("pyflakes", version,
                       "https://pypi.python.org/pypi/pyflakes", None,
                       "pyflakes license", "see the package",
                       path))
    version, path = getPackageVersionAndLocation('python-magic')
    components.append(("python-magic", version,
                       "https://pypi.python.org/pypi/python-magic/", None,
                       "MIT license",
                       "https://opensource.org/licenses/MIT",
                       path))
    version, path = getGraphvizVersion()
    components.append(("graphviz", version,
                       "http://www.graphviz.org/", None,
                       "Eclipse Public License 1.0",
                       "http://www.graphviz.org/License.php",
                       path))
    version, path = getPackageVersionAndLocation('gprof2dot')
    components.append(("gprof2dot", version,
                       "https://github.com/jrfonseca/gprof2dot", None,
                       "LGPL", "http://www.gnu.org/licenses/lgpl.html",
                       path))
    version, path = getPackageVersionAndLocation('yapsy')
    components.append(("yapsy", version,
                       "http://yapsy.sourceforge.net", None,
                       "BSD License",
                       "http://opensource.org/licenses/bsd-license.php",
                       path))
    version, path = getPackageVersionAndLocation('jedi')
    components.append(("jedi", version,
                       "http://jedi.readthedocs.io", None,
                       "MIT License",
                       "https://opensource.org/licenses/MIT",
                       path))
    version, path = getPackageVersionAndLocation('radon')
    components.append(("radon", version,
                       "https://radon.readthedocs.org/", None,
                       "MIT License",
                       "https://opensource.org/licenses/MIT",
                       path))
    version, path = getPackageVersionAndLocation('vulture')
    components.append(("vulture", version,
                       "https://github.com/jendrikseipp/vulture", None,
                       "MIT License",
                       "https://opensource.org/licenses/MIT",
                       path))
    version, path = getPackageVersionAndLocation('mistune')
    components.append(("mistune", version,
                       "https://github.com/lepture/mistune", None,
                       "BSD 3-Clause License",
                       "https://opensource.org/licenses/BSD-3-Clause",
                       path))
    return components
