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


from htmltabwidget          import HTMLTabWidget


class WelcomeWidget( HTMLTabWidget ):
    """ Welcome screen """

    def __init__( self, parent = None ):

        HTMLTabWidget.__init__( self, parent )
        self.setHTML( \
            """<body bgcolor="#ffffff">""" \
            """<p>""" \
            """<table cellspacing="1" cellpadding="3" width="100%" """ \
            """       align="center" bgcolor="#004080" border="0">""" \
            """<tr>""" \
            """  <td bgcolor="#ffffff">""" \
            """    <table style="WIDTH: 100%" cellspacing="1" """ \
            """           cellpadding="3" bgcolor="#004080">""" \
            """    <tr width="100%">""" \
            """      <td style="WIDTH: 110px">""" \
            """      <img border="0" align="left" src="pixmaps/logo.png" """ \
            """           width="100" height="75">""" \
            """      </td>""" \
            """      <td width="100%">""" \
            """      <h1 align="center">""" \
            """      <font color="#ffffff">Welcome to codimension</font>""" \
            """      </h1>""" \
            """      </td>""" \
            """    </tr>""" \
            """    </table>""" \
            """    <p align="center"> Codimension is a two way text and """ \
            """        graphics python code editor and analyser.</p>""" \
            """    <p align="center"> The codimension IDE lacks the main """ \
            """        menu and the features are available via [context] """ \
            """        toolbar buttons, context menues or via keyboard """ \
            """        hot keys (click F1 for a quick reference).</p>""" \
            """    <p align="center">  Some information is available via """ \
            """        hovering mouse cursor over certain UI elements.</p>""" \
            """    <p align="center">Enjoy using codimension!</p>""" \
            """    <p align="center"> If you have bug reports, comments, """ \
            """        ideas how to improve codimension or [better] want """ \
            """        to join developing it please contact me at """ \
            """        <a href="mailto:sergey.satskiy@gmail.com">""" \
            """        sergey.satskiy@gmail.com</a>""" \
            """    </p></td></tr>""" \
            """    <br><br>""" \
            """  <tr>""" \
            """<td >&nbsp;</td></tr></table></ P></p>""" \
            """</body>""" )

        self.setFileName( "" )
        self.setShortName( "Welcome" )
        return

