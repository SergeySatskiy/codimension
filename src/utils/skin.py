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

" Skins support "

import logging, os, ConfigParser
from PyQt4.QtGui import QColor, QFont
from csscache import parseSingleCSS


def buildColor( colorAsStr ):
    " Converts saved color into QColor object "
    colorAsStr = colorAsStr.strip()
    parts = colorAsStr.split( ',' )
    if len( parts ) != 4:
        raise Exception( "Unexpected color format" )
    return QColor( int( parts[ 0 ] ), int( parts[ 1 ] ),
                   int( parts[ 2 ] ), int( parts[ 3 ] ) )


def colorAsString( color ):
    " Converts the given color to a string "
    return ",".join( [ str( color.red() ),
                       str( color.green() ),
                       str( color.blue() ),
                       str( color.alpha() ) ] )


def buildFont( fontAsString ):
    " Converts saved font into QFont object "
    fontAsString = fontAsString.strip()
    font = QFont()
    font.fromString( fontAsString )
    return font


class StyleParameters:
    " Holds a description of one scintilla lexer style "

    def __init__( self ):
        self.description = "default"
        self.index = -1

        self.color = QColor( 0, 0, 0, 255 )
        self.paper = QColor( 255, 255, 230, 255 )
        self.eolFill = False
        self.font = buildFont( "Monospace,14,-1,5,50,0,0,0,0,0" )
        return


class LexerStyles:
    " Holds one lexer styles description "

    def __init__( self ):
        self.styles = []
        return

    def load( self, config, sec ):
        " Loads the available styles from the given config file section "

        indexes = config.get( sec, "indexes" ).split( ',' )
        for index in indexes:
            try:
                parameters = StyleParameters()
                parameters.index = int( index )

                key = "description" + index
                parameters.description = config.get( sec, key ).strip()

                key = "color" + index
                parameters.color = buildColor( config.get( sec, key ) )

                key = "paper" + index
                parameters.paper = buildColor( config.get( sec, key ) )

                key = "eolFill" + index
                parameters.eolFill = config.getboolean( sec, key )

                key = "font" + index
                parameters.font = buildFont( config.get( sec, key ) )

                self.styles.append( parameters )

            except ConfigParser.NoOptionError:
                logging.error( "Lexer skin description inconsistence " \
                               "detected. Absent entries for index " + index + \
                               " in section " + sec )
                continue
        return


class Skin:
    " Holds the definitions for a skin "

    def __init__( self ):
        self.__isOK = True
        self.name = ""
        self.lexerStyles = {}   # name -> LexerStyles
        self.appCSS = ""

        self.marginPaper = None
        self.marginPaperDebug = None
        self.marginColor = None
        self.marginColorDebug = None
        self.lineNumFont = None

        self.foldingPaper = None
        self.foldingColor = None

        self.searchMarkColor = None
        self.searchMarkAlpha = 0
        self.matchMarkColor = None
        self.matchMarkAlpha = 0
        self.spellingMarkColor = None
        self.spellingMarkAlpha = 0

        self.nolexerPaper = None
        self.nolexerColor = None
        self.nolexerFont = None

        self.currentLinePaper = None
        self.edgeColor = None

        self.matchedBracePaper = None
        self.matchedBraceColor = None
        self.unmatchedBracePaper = None
        self.unmatchedBraceColor = None
        self.indentGuidePaper = None
        self.indentGuideColor = None

        self.__reset()
        return

    def __reset( self ):
        " Resets all the values to the default "
        self.name = "default"
        self.lexerStyles = {}
        self.appCSS = """
            QStatusBar::item
            { border: 0px solid black }
            QToolTip
            { font-size: 11px;
              border: 1px solid gray;
              border-radius: 3px;
              background: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #eef, stop: 1 #ccf );
            }
            QTreeView
            { alternate-background-color: #eef0f1; } """

        self.marginPaper = QColor( 228, 228, 228, 255 )
        self.marginPaperDebug = QColor( 255, 228, 228, 255 )
        self.marginColor = QColor( 128, 128, 128, 255 )
        self.marginColorDebug = QColor( 128, 128, 128, 255 )
        self.lineNumFont = buildFont( "Sans Serif,12,-1,5,50,0,0,0,0,0" )

        self.foldingPaper = QColor( 255, 255, 255, 255 )
        self.foldingColor = QColor( 230, 230, 230, 255 )

        self.searchMarkColor = QColor( 0, 255, 0, 255 )
        self.searchMarkAlpha = 100
        self.matchMarkColor = QColor( 0, 0, 255, 255 )
        self.matchMarkAlpha = 100
        self.spellingMarkColor = QColor( 139, 0, 0, 255 )
        self.spellingMarkAlpha = 100

        self.nolexerPaper = QColor( 255, 255, 230, 255 )
        self.nolexerColor = QColor( 0, 0, 0, 255 )
        self.nolexerFont = buildFont( "Monospace,14,-1,5,50,0,0,0,0,0" )

        self.currentLinePaper = QColor( 232, 232, 255, 255 )
        self.edgeColor = QColor( 127, 127, 127, 255 )

        self.matchedBracePaper = QColor( 255, 255, 255, 255 )
        self.matchedBraceColor = QColor( 0, 0, 255, 255 )
        self.unmatchedBracePaper = QColor( 127, 0, 0, 255 )
        self.unmatchedBraceColor = QColor( 255, 255, 255, 255 )

        self.indentGuidePaper = QColor( 230, 230, 230, 255 )
        self.indentGuideColor = QColor( 127, 127, 127, 255 )
        return


    def load( self, dirName ):
        " Loads the skin description from the given directory "
        dirName = os.path.abspath( dirName )
        self.name = os.path.basename( dirName )

        # Load the skin description
        dirName += os.path.sep
        appFile = dirName + "application.css"
        if not os.path.exists( appFile ):
            logging.warning( "Cannot find " + appFile + \
                             ". Default skin will be used." )
            self.__reset()
            return False

        generalFile = dirName + "general"
        if not os.path.exists( generalFile ):
            logging.warning( "Cannot find " + generalFile + \
                             ". Default skin will be used." )
            self.__reset()
            return False

        lexersFile = dirName + "lexers"
        if not os.path.exists( lexersFile ):
            logging.warning( "Cannot find " + lexersFile + \
                             ". Default skin will be used." )
            self.__reset()
            return False

        # All the files are in place. Load them
        if not self.__loadAppCSS( appFile ):
            self.__saveAppCSS( appFile )
        if not self.__loadGeneral( generalFile ):
            self.__saveGeneral( generalFile )
        if not self.__loadLexers( lexersFile ):
            self.__reset()
            return False

        return True

    def __loadAppCSS( self, fName ):
        " Loads the application CSS file "
        try:
            content = []
            parseSingleCSS( fName, content )
            self.appCSS = "".join( content )
        except:
            logging.warning( "Cannot read application CSS from " + fName + \
                             ". The file will be updated with a default CSS." )
            return False
        return True

    def __getColor( self, config, section, value ):
        " Reads a value from the given section "
        try:
            return buildColor( config.get( section, value ) )
        except:
            logging.warning( "Cannot read the [" + section + "]/" + \
                             value + " value from the skin file. " \
                             "The file will be updated with a default value." )
            self.__isOK = False
            return None

    def __getFont( self, config, section, value ):
        " Reads a value from the given section "
        try:
            return buildFont( config.get( section, value ) )
        except:
            logging.warning( "Cannot read the [" + section + "]/" + \
                             value + " value from the skin file. " \
                             "The file will be updated with a default value." )
            self.__isOK = False
            return None

    def __getInt( self, config, section, value ):
        " Reads a value from the given section "
        try:
            return config.getint( section, value )
        except:
            logging.warning( "Cannot read the [" + section + "]/" + \
                             value + " value from the skin file. " \
                             "The file will be updated with a default value." )
            self.__isOK = False
            return None

    def __loadGeneral( self, fName ):
        " Loads the general settings file "
        config = ConfigParser.ConfigParser()
        try:
            config.read( [ fName ] )
        except:
            logging.warning( "Cannot read the skin file " + fName + \
                             ". The file will be updated with default values." )
            return False

        val = self.__getColor( config, "general", "marginpaper" )
        if val is not None:
            self.marginPaper = val
        val = self.__getColor( config, "general", "marginpaperdebug" )
        if val is not None:
            self.marginPaperDebug = val
        val = self.__getColor( config, "general", "margincolor" )
        if val is not None:
            self.marginColor = val
        val = self.__getColor( config, "general", "margincolordebug" )
        if val is not None:
            self.marginColorDebug = val
        val = self.__getFont( config, "general", "linenumfont" )
        if val is not None:
            self.lineNumFont = val

        val = self.__getColor( config, "general", "foldingpaper" )
        if val is not None:
            self.foldingPaper = val
        val = self.__getColor( config, "general", "foldingcolor" )
        if val is not None:
            self.foldingColor = val

        val = self.__getColor( config, "general", "searchmarkcolor" )
        if val is not None:
            self.searchMarkColor = val
        val = self.__getInt( config, "general", "searchmarkalpha" )
        if val is not None:
            self.searchMarkAlpha = val
        val = self.__getColor( config, "general", "matchmarkcolor" )
        if val is not None:
            self.matchMarkColor = val
        val = self.__getInt( config, "general", "matchmarkalpha" )
        if val is not None:
            self.matchMarkAlpha = val
        val = self.__getColor( config, "general", "spellingmarkcolor" )
        if val is not None:
            self.spellingMarkColor = val
        val = self.__getInt( config, "general", "spellingmarkalpha" )
        if val is not None:
            self.spellingMarkAlpha = val

        val = self.__getColor( config, "general", "nolexerpaper" )
        if val is not None:
            self.nolexerPaper = val
        val = self.__getColor( config, "general", "nolexercolor" )
        if val is not None:
            self.nolexerColor = val
        val = self.__getFont( config, "general", "nolexerfont" )
        if val is not None:
            self.nolexerFont = val

        val = self.__getColor( config, "general", "currentlinepaper" )
        if val is not None:
            self.currentLinePaper = val
        val = self.__getColor( config, "general", "edgecolor" )
        if val is not None:
            self.edgeColor = val
        val = self.__getColor( config, "general", "matchedbracepaper" )
        if val is not None:
            self.matchedBracePaper = val
        val = self.__getColor( config, "general", "matchedbracecolor" )
        if val is not None:
            self.matchedBraceColor = val
        val = self.__getColor( config, "general", "unmatchedbracepaper" )
        if val is not None:
            self.unmatchedBracePaper = val
        val = self.__getColor( config, "general", "unmatchedbracecolor" )
        if val is not None:
            self.unmatchedBraceColor = val

        val = self.__getColor( config, "general", "indentguidepaper" )
        if val is not None:
            self.indentGuidePaper = val
        val = self.__getColor( config, "general", "indentguidecolor" )
        if val is not None:
            self.indentGuideColor = val
        return self.__isOK

    def __loadLexers( self, fName ):
        " Loads the lexers settings file "
        config = ConfigParser.ConfigParser()
        try:
            config.read( [ fName ] )
        except:
            logging.error( "Cannot read " + fName + ". No skin will be used." )
            return False

        for section in config.sections():
            lexerStyles = LexerStyles()
            lexerStyles.load( config, section )
            self.lexerStyles[ section ] = lexerStyles
        return True

    def getLexerStyles( self, name ):
        " Provides the lexer style "
        try:
            return self.lexerStyles[ name ]
        except KeyError:
            # could not find the style, provide a substitute
            pass

        substitute = LexerStyles()
        substitute.styles.append( StyleParameters() )
        return substitute

    def clearLexerStyles( self ):
        " Cleans up memory taken by the lexer styles "
        self.lexerStyles = {}
        return

    def __saveGeneral( self, fName ):
        " Writes the general skin file "
        try:
            f = open( fName, "w" )
            f.write( "# Automatically updated due to missed or corrupted values\n" )
            f.write( "[general]\n" )
            f.write( "name=" + self.name + "\n\n" )

            f.write( "marginpaper=" + colorAsString( self.marginPaper ) + "\n" )
            f.write( "marginpaperdebug=" + colorAsString( self.marginPaperDebug ) + "\n" )
            f.write( "margincolor=" + colorAsString( self.marginColor ) + "\n" )
            f.write( "margincolordebug=" + colorAsString( self.marginColorDebug ) + "\n" )
            f.write( "linenumfont=" + self.lineNumFont.toString() + "\n\n" )

            f.write( "foldingpaper=" + colorAsString( self.foldingPaper ) + "\n" )
            f.write( "foldingcolor=" + colorAsString( self.foldingColor ) + "\n" )

            f.write( "searchmarkcolor=" + colorAsString( self.searchMarkColor ) + "\n" )
            f.write( "searchmarkalpha=" + str( self.searchMarkAlpha ) + "\n\n" )

            f.write( "matchmarkcolor=" + colorAsString( self.matchMarkColor ) + "\n" )
            f.write( "matchmarkalpha=" + str( self.matchMarkAlpha ) + "\n\n" )

            f.write( "spellingmarkcolor=" + colorAsString( self.spellingMarkColor ) + "\n" )
            f.write( "spellingmarkalpha=" + str( self.spellingMarkAlpha ) + "\n\n" )

            f.write( "nolexerpaper=" + colorAsString( self.nolexerPaper ) + "\n" )
            f.write( "nolexercolor=" + colorAsString( self.nolexerColor ) + "\n" )
            f.write( "nolexerfont=" + self.nolexerFont.toString() + "\n\n" )

            f.write( "currentlinepaper=" + colorAsString( self.currentLinePaper ) + "\n" )
            f.write( "edgecolor=" + colorAsString( self.edgeColor ) + "\n\n" )

            f.write( "matchedbracepaper=" + colorAsString( self.matchedBracePaper ) + "\n" )
            f.write( "matchedbracecolor=" + colorAsString( self.matchedBraceColor ) + "\n" )
            f.write( "unmatchedbracepaper=" + colorAsString( self.unmatchedBracePaper ) + "\n" )
            f.write( "unmatchedbracecolor=" + colorAsString( self.unmatchedBraceColor ) + "\n\n" )

            f.write( "indentguidepaper=" + colorAsString( self.indentGuidePaper ) + "\n" )
            f.write( "indentguidecolor=" + colorAsString( self.indentGuideColor ) + "\n" )
            f.close()
        except:
            logging.warning( "Could not write skin file " + fName )
        return

    def __saveAppCSS( self, appFile ):
        " Writes the application CSS "
        try:
            f = open( appFile, "w" )
            f.write( self.appCSS + "\n" )
            f.close()
        except:
            logging.warning( "Could not write skin CSS file " + appFile )
        return


