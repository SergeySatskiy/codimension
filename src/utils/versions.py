#
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
# $Id$
#

""" Provides versions of various components used by codimension """

def getCodimensionVersion():
    " Provides the IDE version "
    from globals import GlobalData
    return GlobalData().version

def getPythonParserVersion():
    " Provides the python parser version "
    import cdmbriefparser
    return cdmbriefparser.getVersion()

def getControlFlowParserVersion():
    " Provides the python control flow version "
    import cdmcf
    return cdmcf.VERSION

def getPythonInterpreterVersion():
    " Provides the python interpreter version "
    import sys
    return ".".join( [ str( sys.version_info.major ),
                       str( sys.version_info.minor ),
                       str( sys.version_info.micro ) ] )

def getPyQtVersion():
    " Provides the PyQt4 version "
    import PyQt4.QtCore
    return str( PyQt4.QtCore.PYQT_VERSION_STR )

def getQtVersion():
    " Provides the Qt version "
    import PyQt4.QtCore
    return str( PyQt4.QtCore.QT_VERSION_STR )

def getSIPVersion():
    " Provides the SIP version "
    try:
        import sip
        return str( sip.SIP_VERSION_STR )
    except:
        try:
            from PyQt4.pyqtconfig import Configuration
            cfg = Configuration()
            return str( cfg.sip_version_str )
        except:
            pass
    return "unknown"

def getRopeVersion():
    " Provides the rope library version "
    import rope
    return rope.VERSION

def getPyFlakesVersion():
    " Provides the pyflakes library version "
    import thirdparty.pyflakes
    return thirdparty.pyflakes.__version__

def getPyMetricsVersion():
    " Provides pymetrics version "
    from pymetricsparser.pymetricsparser import PyMetrics
    from settings import thirdpartyDir
    import os.path
    try:
        path = thirdpartyDir + "pymetrics" + os.path.sep + "pymetrics.py"
        if os.path.exists( path ):
            metrics = PyMetrics( path )
        else:
            metrics = PyMetrics()
        version = metrics.getVersion()
        if version:
            return version
        return "could not determine"
    except:
        return "Not installed"

def getPyLintVersion():
    " Provides pylint version "
    from globals import GlobalData
    if not GlobalData().pylintAvailable:
        return "Not installed"

    from pylintparser.pylintparser import Pylint
    lint = Pylint()
    try:
        version = lint.getVersion()
        if version:
            return version
        return "could not determine"
    except:
        return "Not installed"

def getFileMagicVersion():
    " Provides the file magic library "
    from fileutils import MAGIC_AVAILABLE
    if not MAGIC_AVAILABLE:
        return "Not installed"
    import magic
    return magic.__version__

def getGraphvizVersion():
    " Provides the graphviz version "
    from globals import GlobalData
    if not GlobalData().graphvizAvailable:
        return "Not installed"

    from misc import safeRunWithStderr
    try:
        stdOut, stdErr = safeRunWithStderr( [ "dot", "-V" ] )
        for line in stdErr.splitlines():
            # E.g. dot - graphviz version 2.26.3 (20100126.1600)
            line = line.strip()
            if line.startswith( "dot - graphviz version " ):
                line = line.replace( "dot - graphviz version ", "" )
                parts = line.split( " " )
                if len( parts ) == 2 and parts[ 0 ][ 0 ].isdigit():
                    return parts[ 0 ]
    except:
        return "Not installed"
    return "could not determine"

def getGprof2dotVersion():
    " Provides gprof2dot version "
    from settings import thirdpartyDir
    from misc import safeRun
    import os.path
    gprof2dot = thirdpartyDir + "gprof2dot" + os.path.sep + "gprof2dot.py"
    try:
        for line in safeRun( [ gprof2dot, "--version" ] ).splitlines():
            # E.g. gprof2dot.py 1.0
            line = line.strip()
            if line.startswith( "gprof2dot" ):
                parts = line.split( " " )
                if len( parts ) == 2 and parts[ 1 ][ 0 ].isdigit():
                    return parts[ 1 ]
    except:
        return "Not installed"
    return "could not determine"

def getPythonTidyVersion():
    " Provides PythonTidy version "
    import thirdparty.pythontidy.PythonTidy as PythonTidy
    return PythonTidy.VERSION

def getQScintillaVersion():
    " Provides scintilla version "
    import PyQt4.Qsci
    return str( PyQt4.Qsci.QSCINTILLA_VERSION_STR )

def getPygmentsVersion():
    " Provides pygments version "
    import pygments
    return pygments.__version__

def getYapsyVersion():
    " Provides yapsy version "
    import yapsy
    return yapsy.__version__


def getComponentInfo():
    " Provides major codimension components information "
    components = []
    # Each item contains: <pretty name>, <version>,
    #                     <url>, <patched>, <license name>,
    #                     <license url>
    # A list is used to have some kind of priority ordering
    components.append( ("Codimension IDE", getCodimensionVersion(),
                        "http://satsky.spb.ru/codimension/", None,
                        "GPL-3.0",
                        "http://www.gnu.org/licenses/gpl-3.0.html") )
    components.append( ("Codimension python parser", getPythonParserVersion(),
                        "http://satsky.spb.ru/codimension/", None,
                        "GPL-3.0",
                        "http://www.gnu.org/licenses/gpl-3.0.html") )
    components.append( ("Codimension python control flow parser",
                        getControlFlowParserVersion(),
                        "http://satsky.spb.ru/codimension/", None,
                        "GPL-3.0",
                        "http://www.gnu.org/licenses/gpl-3.0.html") )
    components.append( ("Python interpreter", getPythonInterpreterVersion(),
                        "http://www.python.org/", None,
                        "Open source license",
                        "http://www.python.org/psf/license/") )
    components.append( ("PyQt", getPyQtVersion(),
                        "http://www.riverbankcomputing.com/software/pyqt/intro",
                        None, "GPL-2.0/GPL-3.0/Commercial/Embedded",
                        "http://www.riverbankcomputing.com/software/pyqt/license" ) )
    components.append( ("Qt", getQtVersion(),
                        "http://qt-project.org/", None,
                        "LGPL-2.1/Commercial",
                        "http://www.gnu.org/licenses/lgpl-2.1.html") )
    components.append( ("SIP", getSIPVersion(),
                        "http://www.riverbankcomputing.com/software/sip/intro",
                        None, "SIP license/GPL-2.0/GPL-3.0",
                        "http://www.riverbankcomputing.com/software/sip/license") )
    components.append( ("rope", getRopeVersion(),
                        "http://rope.sourceforge.net/",
                        True,
                        "GPL-2.0", "http://www.gnu.org/licenses/gpl-2.0.html") )
    components.append( ("pyflakes", getPyFlakesVersion(),
                        "https://pypi.python.org/pypi/pyflakes", True,
                        "pyflakes license", "see the package") )
    components.append( ("pymetrics", getPyMetricsVersion(),
                        "http://pymetrics.sourceforge.net/", None,
                        "GPL-2.0", "http://www.gnu.org/licenses/gpl-2.0.html") )
    components.append( ("pylint", getPyLintVersion(),
                        "http://www.pylint.org/", None,
                        "GPL-2.0", "http://www.gnu.org/licenses/gpl-2.0.html") )
    components.append( ("filemagic", getFileMagicVersion(),
                        "https://pypi.python.org/pypi/filemagic/", None,
                        "Apache License 2.0",
                        "http://www.apache.org/licenses/LICENSE-2.0.html") )
    components.append( ("graphviz", getGraphvizVersion(),
                        "http://www.graphviz.org/", None,
                        "Eclipse Public License 1.0",
                        "http://www.graphviz.org/License.php") )
    components.append( ("gprof2dot", getGprof2dotVersion(),
                        "http://freecode.com/projects/gprof2dot_py", True,
                        "LGPL", "http://www.gnu.org/licenses/lgpl.html") )
    components.append( ("pythontidy", getPythonTidyVersion(),
                        "https://pypi.python.org/pypi/PythonTidy", None,
                        "GPL-2.0", "http://www.gnu.org/licenses/gpl-2.0.html") )
    components.append( ("QScintilla", getQScintillaVersion(),
                        "http://www.riverbankcomputing.com/software/qscintilla/intro",
                        None, "GPL-2.0/GPL-3.0/Commercial",
                        "http://www.riverbankcomputing.com/software/qscintilla/license") )
    components.append( ("pygments", getPygmentsVersion(),
                        "http://pygments.org/", None,
                        "BSD License",
                        "http://opensource.org/licenses/bsd-license.php") )
    components.append( ("yapsy", getYapsyVersion(),
                        "http://yapsy.sourceforge.net", True,
                        "BSD License",
                        "http://opensource.org/licenses/bsd-license.php") )
    return components
