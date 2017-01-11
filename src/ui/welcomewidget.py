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

"""Welcome screen"""


import os.path
import sys
from utils.globals import GlobalData
from .texttabwidget import TextTabWidget


class WelcomeWidget(TextTabWidget):

    """Welcome screen"""

    httpAddress = "http://codimension.org"
    homePage = httpAddress
    downloadPage = httpAddress + "/download/"

    def __init__(self, parent=None):

        TextTabWidget.__init__(self, parent)
        pixmapPath = os.path.dirname(os.path.realpath(sys.argv[0])) + \
            os.path.sep + 'pixmaps' + os.path.sep
        logoPath = pixmapPath + 'logo-48x48.png'
        welcome = "  Codimension version " + str(GlobalData().version) + \
            " <font size=-2>(GPL v3)</font>"

        self.setHTML("""
<body bgcolor="#d5d1cf">
<p>
<table cellspacing="0" cellpadding="8" width="100%"
       align="left" bgcolor="#d5d1cf" border="0" style="width: 100%">
<tr>
  <td width="1%" valign="middle">
      <a href="http://codimension.org">
      <img border="0" align="left" src='file:""" + logoPath + """'
           width="48" height="48">
      </a>
  </td>
  <td valign="middle">
      <h2 align="left">&nbsp;""" + welcome + """</h2>
  </td>
</tr>
</table>
<table cellspacing="0" cellpadding="8" width="100%"
       align="left" bgcolor="#d5d1cf" border="0" style="width: 100%">
<tr>
  <td>
    <p align="left">Click <b>F1</b> for Keyboard Shortcut Reference or
    <p align="left">
       visit
       <a href="http://codimension.org">
          http://codimension.org</a>
          for more information.
    </p>
  </td>
</tr>
</table></p>
</body>""")

        self.setFileName("")
        self.setShortName("Welcome")
