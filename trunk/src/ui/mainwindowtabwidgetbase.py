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

" Base class for all the main window tab widgets "


import uuid


class MainWindowTabWidgetBase():
    " Base class for all the main window tab widgets "

    Unknown              = -1
    PlainTextEditor      = 0    # Text only editor (including python)
    PythonGraphicsEditor = 1    # Text/graphics python only editor widget
    PictureViewer        = 2
    HTMLViewer           = 3
    GeneratedDiagram     = 4
    ProfileViewer        = 5
    DisassemblerViewer   = 6

    def __init__( self ):
        self.__uuid = uuid.uuid1()
        self.__tooltip = ""
        return

    def isModified( self ):
        " Tells if the file is modifed "
        raise Exception( "isModified() is not implemented" )

    def getRWMode( self ):
        """ Tells the read/write mode
            Should return 'N/A', 'RW' or 'RO'
        """
        raise Exception( "getRWMode() is not implemented" )

    def getType( self ):
        " Tells the widget type "
        raise Exception( "getType() is not implemented" )

    def getLanguage( self ):
        " Tells the content language "
        raise Exception( "getLanguage() is not implemented" )

    def getFileName( self ):
        " Tells what file name of the widget "
        raise Exception( "getFilename() is not implemented" )

    def setFileName( self, name ):
        " Sets the file name "
        raise Exception( "setFilename() is not implemented" )

    def getEol( self ):
        " Tells the EOL style "
        raise Exception( "getEol() is not implemented" )

    def getLine( self ):
        " Tells the cursor line "
        raise Exception( "getLine() is not implemented" )

    def getPos( self ):
        " Tells the cursor column "
        raise Exception( "getPos() is not implemented" )

    def getEncoding( self ):
        " Tells the content encoding "
        raise Exception( "getEncoding() is not implemented" )

    def setEncoding( self, newEncoding ):
        " Sets the encoding for the text document "
        raise Exception( "setEncoding() is not implemented" )

    def getShortName( self ):
        " Tells the display name "
        raise Exception( "getShortName() is not implemented" )

    def setShortName( self, name ):
        " Sets the display name "
        raise Exception( "setShortName() is not implemented" )

    def getUUID( self ):
        " Provides the widget unique ID "
        return self.__uuid

    def isDiskFileModified( self ):
        " Return True if the loaded file is modified "
        return False

    def doesFileExist( self ):
        " Returns True if the loaded file still exists "
        return True

    def setReloadDialogShown( self, value = True ):
        """ Sets the new value of the flag which tells if the reloading
            dialogue has already been displayed """
        return

    def getReloadDialogShown( self ):
        " Tells if the reload dialog has already been shown "
        return True

    def showOutsideChangesBar( self, allEnabled ):
        " Shows the outside changes bar "
        return

    def reload( self ):
        " Reloads the widget content from the file "
        return

    def setTooltip( self, txt ):
        " Saves the tab tooltip "
        self.__tooltip = txt
        return

    def getTooltip( self ):
        " Returns the saved tooltip "
        return self.__tooltip

    def setDebugMode( self, mode, isProjectFile ):
        " Switches the widget to debug mode and back "
        return

    def getVCSStatus( self ):
        " Provides the content VCS status "
        return None
