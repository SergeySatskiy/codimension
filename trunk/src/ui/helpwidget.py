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
<html>
<body bgcolor="#ffffe6">

<table cellspacing="1" cellpadding="3" width="100%"
       align="left" border="0">
<tr>
  <td bgcolor="#ffffe6">
    <table style="WIDTH: 100%" cellspacing="1"
           cellpadding="3">
    <tr width="100%">
      <td style="WIDTH: 110px">
      <!--a href="http://satsky.spb.ru/codimension/codimensionEng.php">
      <img border="0" align="left" src='file:""" + logoPath + """'
           width="64" height="64">
      </a-->&nbsp;
      </td>
      <td width="100%">
        <h1 align="left" style="color: #666">Keyboard Shortcut Reference</h1>
      </td>
    </tr>
    </table>

    <p align="center">
      <table border="1" cellspacing="0"
             cellpadding="1" width="95%" align="center">

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
          <td>Alt+PgDown</td>
          <td>Back in history</td>
          <td>Ctrl+PgDown</td>
          <td>Previous tab</td></tr>
        <tr>
          <td>Alt+PgUp</td>
          <td>Forward in history</td>
          <td>Ctrl+PgUp</td>
          <td>Next tab</td></tr>
        <tr>
          <td>Ctrl+F</td>
          <td>Search in the current file</td>
          <td>Ctrl+Shift+F</td>
          <td>Search in files</td></tr>
        <tr>
          <td>Ctrl+R</td>
          <td>Replace in the current file</td>
          <td>Ctrl+K</td>
          <td>Pymetrics for a file</td></tr>
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
          <td>Alt+Shift+S</td>
          <td>Search a name</td>
          <td>Alt+Shift+O</td>
          <td>Search a file</td></tr>
        <tr>
          <td>Ctrl+N</td>
          <td>Highlight the current word</td>
          <td>Ctrl+TAB</td>
          <td>Switching between two recent tabs</td></tr>
        <tr>
        <tr>
          <td>Ctrl+I</td>
          <td>Open import/select import to open</td>
          <td>Ctrl+M</td>
          <td>Comment/uncomment a line or selected lines</td></tr>
        <tr>
        <tr>
          <td>Alt+Left</td>
          <td>Word part left</td>
          <td>Alt+Right</td>
          <td>Word part right</td></tr>
        <tr>
    </table>
    </p>
    <p align="center">
       More documentation is available at<br/>
       <a style="color: #666"
          href="http://satsky.spb.ru/codimension/codimensionEng.php">
          http://satsky.spb.ru/codimension/codimensionEng.php</a>.
    </p>
    <p align="right"> Sergey Satskiy (c), 2010 - 2011
        <a style="color: #666"
           href="mailto:sergey.satskiy@gmail.com">sergey.satskiy@gmail.com</a>
    </p></td></tr>

<p>
<tr>
<td >&nbsp;</td></tr></p></table>

</body>
</html>
""" )

        self.setFileName( "" )
        self.setShortName( "Quick help" )
        return

    def setFocus( self ):
        " Sets the focus to the nested html displaying editor "
        HTMLTabWidget.setFocus( self )
        return

