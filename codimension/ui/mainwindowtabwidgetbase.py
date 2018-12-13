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

"""Base class for all the main window tab widgets"""

import uuid


class MainWindowTabWidgetBase():

    """Base class for all the main window tab widgets"""

    Unknown = -1
    PlainTextEditor = 0     # Text editor + may be a graphics widget
    PictureViewer = 1
    HTMLViewer = 2
    GeneratedDiagram = 3
    ProfileViewer = 4
    VCSAnnotateViewer = 5
    DiffViewer = 6
    MDViewer = 7

    def __init__(self):
        self.__uuid = str(uuid.uuid1())
        self.__tooltip = ""

    def isModified(self):
        """Tells if the file is modifed"""
        raise Exception("isModified() is not implemented")

    def getRWMode(self):
        """Tells the read/write mode"""
        return None

    def getType(self):
        """Tells the widget type"""
        raise Exception("getType() is not implemented")

    def getLanguage(self):
        """Tells the content language"""
        raise Exception("getLanguage() is not implemented")

    def getFileName(self):
        """Tells what file name of the widget"""
        return None

    def setFileName(self, path):
        """Sets the file name"""
        raise Exception("setFilename() is not implemented")

    def getEol(self):
        """Tells the EOL style"""
        return None

    def getLine(self):
        """Tells the cursor line"""
        return None

    def getPos(self):
        """Tells the cursor column"""
        return None

    def getEncoding(self):
        """Tells the content encoding"""
        return None

    def setEncoding(self, newEncoding):
        """Sets the encoding for the text document"""
        raise Exception("setEncoding() is not implemented")

    def getShortName(self):
        """Tells the display name"""
        raise Exception("getShortName() is not implemented")

    def setShortName(self, name):
        """Sets the display name"""
        raise Exception("setShortName() is not implemented")

    def getUUID(self):
        """Provides the widget unique ID"""
        return self.__uuid

    def isDiskFileModified(self):
        """Return True if the loaded file is modified"""
        return False

    def doesFileExist(self):
        """Returns True if the loaded file still exists"""
        return True

    def setReloadDialogShown(self, value=True):
        """Memorizes if the reloading dialogue has already been displayed"""
        pass

    def getReloadDialogShown(self):
        """Tells if the reload dialog has already been shown"""
        return True

    def showOutsideChangesBar(self, allEnabled):
        """Shows the outside changes bar"""
        pass

    def reload(self):
        """Reloads the widget content from the file"""
        pass

    def setTooltip(self, txt):
        """Saves the tab tooltip"""
        self.__tooltip = txt

    def getTooltip(self):
        """Returns the saved tooltip"""
        return self.__tooltip

    def setDebugMode(self, mode, isProjectFile):
        """Switches the widget to debug mode and back"""
        pass

    def getVCSStatus(self):
        """Provides the content VCS status"""
        return None
