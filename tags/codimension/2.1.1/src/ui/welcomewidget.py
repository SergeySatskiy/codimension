#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id: welcomewidget.py 1508 2013-06-11 16:15:57Z sergey.satskiy@gmail.com $
#

""" Welcome screen """


import os.path, sys
from htmltabwidget import HTMLTabWidget
from utils.globals import GlobalData
from utils.latestver import getLatestVersionFile
from distutils.version import StrictVersion


class WelcomeWidget( HTMLTabWidget ):
    """ Welcome screen """

    httpAddress = "http://satsky.spb.ru/codimension/"
    homePage = httpAddress + "codimensionEng.php"
    downloadPage = httpAddress + "downloadEng.php"

    def __init__( self, parent = None ):

        HTMLTabWidget.__init__( self, parent )
        pixmapPath = os.path.dirname( os.path.abspath( sys.argv[0] ) ) + \
                     os.path.sep + 'pixmaps' + os.path.sep
        logoPath = pixmapPath + 'logo-48x48.png'
        welcome = "  Codimension version " + str( GlobalData().version ) + \
                  " <font size=-2>(GPL v3)</font>"

        newerVersion = ""
        success, values = getLatestVersionFile()
        if success:
            if StrictVersion( values[ "LatestVersion" ] ) > \
               StrictVersion( GlobalData().version ):
                newerVersion = "<p aligh='left'>" \
                               "<b>Note</b>: version " + \
                               values[ "LatestVersion" ] + " is <a href='" + \
                               self.downloadPage + "'>available</a>"
                if "ReleaseDate" in values:
                    newerVersion += ", released on " + values[ "ReleaseDate" ]
                newerVersion += "</p>"
                if "ChangeLog" in values:
                    newerVersion += "Version " + values[ "LatestVersion" ] + \
                                    " change log:"
                    newerVersion += "<pre>" + values[ "ChangeLog" ] + "</pre>"


        self.setHTML( \
            """<body bgcolor="#d5d1cf">""" \
            """<p>""" \
            """<table cellspacing="0" cellpadding="8" width="100%" """ \
            """       align="left" bgcolor="#d5d1cf" border="0" style="width: 100%">""" \
            """<tr>""" \
            """  <td width="1%">""" \
            """      <a href='""" + self.homePage + """'>""" \
            """      <img border="0" align="left" src='file:""" + logoPath + \
            """' """ \
            """           width="48" height="48">""" \
            """      </a>&nbsp;""" \
            """  </td>""" \
            """  <td>""" \
            """      <h2 align="left" style="color: #666">""" + welcome + \
            """      </h2>""" \
            """  </td>""" \
            """</tr>""" \
            """</table>""" \
            """<table cellspacing="0" cellpadding="8" width="100%" """ \
            """       align="left" bgcolor="#d5d1cf" border="0" style="width: 100%">""" \
            """<tr>""" \
            """  <td>""" \
            """    <p align="left">Click <b>F1</b> for major shortcut reference or """ \
            """    <p align="left">""" \
            """       visit """ \
            """       <a """ \
            """          href="http://satsky.spb.ru/codimension/codimensionEng.php">""" \
            """          http://satsky.spb.ru/codimension/codimensionEng.php</a>""" \
            """          for more information.""" \
            """    </p>""" \
            """  </td>""" \
            """</tr>""" \
            """<tr>""" \
            """  <td><br>""" + newerVersion + """</td>""" \
            """</tr>""" \
            """</table></p>""" \
            """</body>""" )

        self.setFileName( "" )
        self.setShortName( "Welcome" )
        return

