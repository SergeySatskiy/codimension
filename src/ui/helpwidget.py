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

""" Quick help screen """


import os.path
import sys
from htmltabwidget  import HTMLTabWidget


class QuickHelpWidget( HTMLTabWidget ):
    """ Quick help screen """

    def __init__( self, parent = None ):

        HTMLTabWidget.__init__( self, parent )
        pixmapPath = os.path.dirname( os.path.abspath( sys.argv[0] ) ) + \
                     os.path.sep + 'pixmaps' + os.path.sep
        logoPath = pixmapPath + 'logo.png'

        self.setHTML( \
"""
<body bgcolor="#ffffff">
<p>
<table cellspacing="1" cellpadding="3" width="100%"
       align="center" bgcolor="#004080" border="0">
<tr>
  <td bgcolor="#ffffff">
    <table style="WIDTH: 100%" cellspacing="1"
           cellpadding="3" bgcolor="#004080">
    <tr width="100%">
      <td style="WIDTH: 110px">
      <img border="0" align="left" src='file:""" + logoPath + """'
           width="100" height="75">
      </td>
      <td width="100%">
      <h1 align="center">
      <font color="#ffffff">Quick Shortcuts Reference</font>
      </h1>
      </td>
    </tr>
    </table>

    <p align="center">    The table below shows
        some of the Codimension hot keys.</p>

    <p align="center">
      <table border="1" cellspacing="0"
             cellpadding="1" width="80%" align="center">

        <tr>
          <td>Ctrl+T</td>
          <td>New tab</td>
          <td>Ctrl+Down</td>
          <td>Show definition</td></tr>
        <tr>
          <td>Ctrl+P</td>
          <td>Tag completion</td>
          <td>Ctrl+Up</td>
          <td>Search for callers</td></tr>
        <tr>
          <td>Alt+Left</td>
          <td>Back in history</td>
          <td>Ctrl+PgDown</td>
          <td>Previous tab</td></tr>
        <tr>
          <td>Alt+Right</td>
          <td>Forward in history</td>
          <td>Ctrl+PgUp or Ctrl+Tab</td>
          <td>Next tab</td></tr>
        <tr>
          <td>Ctrl+F</td>
          <td>Search in the current file</td>
          <td>Ctrl+Shift+F</td>
          <td>Search in files</td></tr>
        <tr>
          <td>Ctrl+R</td>
          <td>Replace in the current file</td>
          <td>Ctrl+Shift+R</td>
          <td>Replace in files</td></tr>
        <tr>
          <td>Ctrl++/-</td>
          <td>Zoom in/out</td>
          <td>Ctrl+Z</td>
          <td>Undo</td></tr>
        <tr>
          <td>Ctrl+0</td>
          <td>Reset zoom</td>
          <td>Ctrl+Shift+Z</td>
          <td>Redo</td></tr>
        <tr>
          <td>Ctrl+S</td>
          <td>Save</td>
          <td>Ctrl+O</td>
          <td>Open</td></tr>
        <tr>
          <td>Ctrl+Shift+S</td>
          <td>Save as</td>
          <td>Ctrl+A</td>
          <td>Select all</td></tr>
        <tr>
          <td>Ctrl+G</td>
          <td>Goto line</td>
          <td>Ctrl+M</td>
          <td>Toggle remark</td></tr>
        <tr>
          <td>Ctrl+D</td>
          <td>Toggle bookmark</td>
          <td>F1</td>
          <td>This reference</td></tr>
        <tr>
          <td>F11</td>
          <td>Shrink sidebars</td>
          <td>Ctrl+L</td>
          <td>Pylint for a file</td></tr>
        <tr>
          <td>F3</td>
          <td>Search next</td>
          <td>Shift+F3</td>
          <td>Search previous</td></tr>
        <tr>
          <td>Ctrl+K</td>
          <td>Pymetrics for a file</td>
          <td></td>
          <td></td></tr>
    </table>
    </p>
    <p align="center">
       Please direct your browser to
       <a href="http://satsky.spb.ru/codimension/codimensionEng.php">
          http://satsky.spb.ru/codimension/codimensionEng.php</a> for
       more Codimension documentation.
    </p>
    <p align="right"> Sergey Satskiy (c), 2010 &lt;sergey.satskiy@gmail.com&gt;
    </p></td></tr>
    <br><br>
  <tr>
<td >&nbsp;</td></tr></table></ P></p>
</body>
""" )

        self.setFileName( "" )
        self.setShortName( "Quick help" )
        return

    def setFocus( self ):
        " Sets the focus to the nested html displaying editor "
        HTMLTabWidget.setFocus( self )
        return

