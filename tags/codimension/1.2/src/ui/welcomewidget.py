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
# $Id$
#

""" Welcome screen """


import os.path, sys
from htmltabwidget      import HTMLTabWidget
from utils.globals      import GlobalData
from utils.latestver    import getLatestVersionFile


class WelcomeWidget( HTMLTabWidget ):
    """ Welcome screen """

    homePage = "http://satsky.spb.ru/codimension/codimensionEng.php"

    def __init__( self, parent = None ):

        HTMLTabWidget.__init__( self, parent )
        pixmapPath = os.path.dirname( os.path.abspath( sys.argv[0] ) ) + \
                     os.path.sep + 'pixmaps' + os.path.sep
        logoPath = pixmapPath + 'logo.png'
        welcome = "Welcome to Codimension v." + str( GlobalData().version )

        newerVersion = ""
        success, values = getLatestVersionFile()
        if success:
            if float( values[ "LatestVersion" ] ) > \
               float( GlobalData().version ):
                newerVersion = "<p aligh='left'>" \
                               "Note: version " + \
                               values[ "LatestVersion" ] + " is <a href='" + \
                               self.homePage + "'>available</a>"
                if values.has_key( "ReleaseDate" ):
                    newerVersion += ", released on " + values[ "ReleaseDate" ]
                newerVersion += "</p>"
                if values.has_key( "ChangeLog" ):
                    newerVersion += "Version " + values[ "LatestVersion" ] + \
                                    " change log:"
                    newerVersion += "<pre>" + values[ "ChangeLog" ] + "</pre>"


        self.setHTML( \
            """<body bgcolor="#ffffe6">""" \
            """<p>""" \
            """<table cellspacing="0" cellpadding="16" width="100%" """ \
            """       align="left" bgcolor="#ffffe6" border="0" style="width: 100%">""" \
            """<tr>""" \
            """  <td width="1%">""" \
            """      <!--a href='""" + self.homePage + """'>""" \
            """      <img border="0" align="left" src='file:""" + logoPath + \
            """' """ \
            """           width="64" height="64">""" \
            """      </a-->&nbsp;""" \
            """  </td>""" \
            """  <td>""" \
            """      <h1 align="left" style="color: #666">""" + welcome + \
            """      </h1>""" \
            """  </td>""" \
            """</tr>""" \
            """<tr>""" \
            """  <td bgcolor="#ffffe6">&nbsp;</td>""" \
            """  <td bgcolor="#ffffe6">""" \
            """    <p align="left">Codimension is yet another free """ \
            """                      experimental Python IDE licensed """ \
            """                      under GPL v3.</p> """ \
            """    <p align="left">Codimension aims to provide an """ \
            """                      integrated system for:""" \
            """    <li>traditional text-based code editing, and</li>""" \
            """    <li>diagram-based code analysis.</li></p>""" \
            """    <p align="left">Codimension lacks the main """ \
            """        menu and all the functionality is available via """ \
            """        toolbar buttons, context menues or via keyboard """ \
            """        hot keys (click F1 for a quick reference).</p>""" \
            """    <p align="left">""" \
            """       Please visit """ \
            """       <a style="color: #666" """ \
            """          href="http://satsky.spb.ru/codimension/codimensionEng.php">""" \
            """          http://satsky.spb.ru/codimension/codimensionEng.php</a>""" \
            """          for more information on Codimension.""" \
            """    </p>""" \
            """    <p align="left">If you want to contribute to """ \
            """        the project in any way, please """ \
            """        contact:""" \
            """    <li>Sergey Satskiy at """ \
            """        <a style="color: #666" """ \
            """           href="mailto:sergey.satskiy@gmail.com">""" \
            """                 sergey.satskiy@gmail.com</a></li>""" \
            """    <li>Dmitry Kazimirov at """ \
            """        <a style="color: #666" """ \
            """           href="mailto:dk@revl.org">""" \
            """                 dk@revl.org</a></li></p>""" \
            """    <p align="left">We hope you enjoy using Codimension.</p>""" \
            """  </td>""" \
            """</tr>""" \
            """<tr>""" \
            """<td bgcolor="#ffffe6" colspan="2">&nbsp;</td></tr>""" \
            """</table></p>"""  + newerVersion + \
            """</body>""" )

        self.setFileName( "" )
        self.setShortName( "Welcome" )
        return

