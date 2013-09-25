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

" Menu provider for codimension subversion plugin "


def populateMainMenu( plugin, parentMenu ):
    " Populates subversion plugin main menu "
    parentMenu.addAction( "Configure", plugin.configure )
    return

def populateFileContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a file in a project browser "
    plugin.fileParentMenu = parentMenu
    parentMenu.addAction( "Info", plugin.fileInfo )
    return

def populateDirectoryContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a directory in a project browser "
    plugin.dirParentMenu = parentMenu
    parentMenu.addAction( "Info", plugin.dirInfo )
    return

def populateBufferContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a text editor or a viewer "
    parentMenu.addAction( "Configure", plugin.configure )
    parentMenu.addSeparator()
    parentMenu.addAction( "Info", plugin.bufferInfo )
    return

