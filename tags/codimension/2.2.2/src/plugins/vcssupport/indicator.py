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

"""
VCS plugin support: indicators for the status bar and project viewer
"""

import os.path, sys
from PyQt4.QtGui import QColor, QPixmap, QFrame, QLabel, QPalette
from PyQt4.QtCore import QSize, Qt


MAX_TEXT_INDICATOR_LENGTH = 2
MAX_PIXMAP_INDICATOR_WIDTH = 16
MAX_PIXMAP_INDICATOR_HEIGHT = 16
BROKEN_INDICATOR = "??"


def buildColor( colorAsStr ):
    " Converts saved color into QColor object "
    colorAsStr = colorAsStr.strip()
    parts = colorAsStr.split( ',' )

    length = len( parts )
    if length == 3:
        return QColor( int( parts[ 0 ] ), int( parts[ 1 ] ),
                       int( parts[ 2 ] ) )
    if length == 4:
        return QColor( int( parts[ 0 ] ), int( parts[ 1 ] ),
                       int( parts[ 2 ] ), int( parts[ 3 ] ) )
    raise Exception( "Unexpected color format" )


class VCSIndicator:
    " Holds an indicator properties "

    def __init__( self, configLine ):
        """ Config line looks as follows:
            id:::pathOrString:::ForegroundColor:::BackgroundColor:::Tooltip
            It comes from a config file or from a plugin
        """
        self.identifier = None
        self.pixmap = None
        self.text = None
        self.backgroundColor = None
        self.foregroundColor = None
        self.defaultTooltip = ""

        self.__parseConfigLine( configLine )
        return

    def __parseConfigLine( self, configLine ):
        " Fills the members "
        if type( configLine ) == tuple or type( configLine ) == list:
            # Came from a plugin
            self.__parsePluginProvidedTuple( configLine )
        else:
            # Came from a config file
            self.__parseConfigFileProvidedString( configLine )
        self.__scalePixmap()
        return

    def __setBrokenIndicator( self, msg ):
        " Sets the indicator to the broken state "
        self.text = BROKEN_INDICATOR
        self.backgroundColor = QColor( 0, 255, 255 )
        self.foregroundColor = QColor( 255, 0, 0 )
        self.defaultTooltip = msg
        return

    def __parseConfigFileProvidedString( self, configLine ):
        " Parses config file provided values "
        parts = configLine.split( ":::" )
        if len( parts ) != 5:
            raise Exception( "Unexpected format of an indicator "
                             "description. Expected 5 values." )
        # ID field
        self.identifier = int( parts[ 0 ] )

        # path or text field
        if os.path.isabs( parts[ 1 ] ):
            # That must be a path to the pixmap
            try:
                self.pixmap = QPixmap( parts[ 1 ] )
            except:
                self.__setBrokenIndicator( "Failed to load pixmap from " +
                                           parts[ 1 ] )
                return
        else:
            # Try to find the pixmap in the standard pixmap directory
            candidate = parts[ 1 ].strip()
            searchPath = os.path.dirname( os.path.abspath( sys.argv[0] ) ) + \
                         os.path.sep + 'pixmaps' + os.path.sep + candidate
            if candidate != "" and os.path.exists( searchPath ):
                try:
                    self.pixmap = QPixmap( searchPath )
                except:
                    self.__setBrokenIndicator( "Failed to load pixmap from " +
                                               parts[ 1 ] )
                    return
            else:
                # It is just a text. Cut it to up to 2 letters
                self.__setText( parts[ 1 ] )

        # Foreground color
        if parts[ 2 ].lower() == "none":
            self.foregroundColor = None
        else:
            self.foregroundColor = buildColor( parts[ 2 ] )

        # Background color
        if parts[ 3 ].lower() == "none":
            self.backgroundColor = None
        else:
            self.backgroundColor = buildColor( parts[ 3 ] )

        # Default tooltip
        if parts[ 4 ].lower() == "none":
            self.defaultTooltip = ""
        else:
            self.defaultTooltip = str( parts[ 4 ] ).strip()
        return

    def __parsePluginProvidedTuple( self, pluginIndicator ):
        " Checks what plugin provided "
        if len( pluginIndicator ) != 5:
            raise Exception( "Unexpected format of an indicator "
                             "description. Expected 5 values." )
        # ID field
        self.identifier = int( pluginIndicator[ 0 ] )

        # Pixmap/text field
        if type( pluginIndicator[ 1 ] ) == str:
            self.__setText( pluginIndicator[ 1 ] )
        else:
            try:
                self.pixmap = QPixmap( pluginIndicator[ 1 ] )
            except:
                self.__setBrokenIndicator( "Failed to get plugin indicator "
                                           "pixmap. Indicator id: " +
                                           str( self.identifier ) )
                return

        # Foreground color
        if pluginIndicator[ 2 ] is None:
            self.foregroundColor = None
        else:
            if type( pluginIndicator[ 2 ] ) == str:
                self.foregroundColor = buildColor( pluginIndicator[ 2 ] )
            else:
                self.foregroundColor = QColor( pluginIndicator[ 2 ] )

        # Background color
        if pluginIndicator[ 3 ] is None:
            self.backgroundColor = None
        else:
            if type( pluginIndicator[ 3 ] ) == str:
                self.backgroundColor = buildColor( pluginIndicator[ 3 ] )
            else:
                self.backgroundColor = QColor( pluginIndicator[ 3 ] )

        # Default tooltip
        if pluginIndicator[ 4 ] is None:
            self.defaultTooltip = ""
        else:
            self.defaultTooltip = str( pluginIndicator[ 4 ] ).strip()
        return

    def __setText( self, value ):
        " Sets the indicator text "
        if len( value ) > MAX_TEXT_INDICATOR_LENGTH:
            self.text = value[ : MAX_TEXT_INDICATOR_LENGTH ]
        else:
            self.text = value
        self.text = self.text.strip()
        return

    def __scalePixmap( self ):
        " Scales the pixmap if necessary "
        if self.pixmap is None:
            return

        if self.pixmap.width() > MAX_PIXMAP_INDICATOR_WIDTH or \
           self.pixmap.height() > MAX_PIXMAP_INDICATOR_HEIGHT:
            maxSize = QSize( MAX_PIXMAP_INDICATOR_WIDTH,
                             MAX_PIXMAP_INDICATOR_HEIGHT )
            self.pixmap = self.pixmap.scaled( maxSize, Qt.KeepAspectRatio )
        return

    def isPixmap( self ):
        " True if it is a pixmap label "
        return self.pixmap is not None

    def draw( self, label ):
        " Draws the indicator as members tell. label is QLabel "
        label.setPalette( QLabel().palette() )
        if self.isPixmap():
            label.setAutoFillBackground( False )
            label.setFrameStyle( QLabel().frameStyle() )
            label.setPixmap( self.pixmap )
        else:
            label.setFrameStyle( QFrame.StyledPanel )
            label.setAutoFillBackground( True )
            palette = label.palette()
            if self.backgroundColor is not None:
                palette.setColor( QPalette.Background, self.backgroundColor )
            if self.foregroundColor is not None:
                palette.setColor( QPalette.Foreground, self.foregroundColor )
            label.setPalette( palette )
            label.setText( self.text )
        return
