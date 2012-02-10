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
from PyQt4.Qsci import QsciScintilla
from csscache import parseSingleCSS


def buildColor( colorAsString ):
    " Converts saved color into QColor object "
    colorAsString = colorAsString.strip()
    parts = colorAsString.split( ',' )
    if len( parts ) != 4:
        raise Exception( "Unexpected color format" )
    return QColor( int( parts[ 0 ] ), int( parts[ 1 ] ),
                   int( parts[ 2 ] ), int( parts[ 3 ] ) )

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
        self.name = "hard-coded"
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
        self.unmatchedBraceColor = QColor( 0, 0, 255, 255 )

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
            logging.error( "Cannot find " + appFile + \
                           ". No skin will be used." )
            self.__reset()
            return False

        generalFile = dirName + "general"
        if not os.path.exists( generalFile ):
            logging.error( "Cannot find " + generalFile + \
                           ". No skin will be used." )
            self.__reset()
            return False

        lexersFile = dirName + "lexers"
        if not os.path.exists( lexersFile ):
            logging.error( "Cannot find " + lexersFile + \
                           ". No skin will be used." )
            self.__reset()
            return False

        # All the files are in place. Load them
        if not self.__loadAppCSS( appFile ):
            self.__reset()
            return False
        if not self.__loadGeneral( generalFile ):
            self.__reset()
            return False
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
            logging.error( "Cannot read " + fName + ". No skin will be used." )
            return False
        return True

    def __loadGeneral( self, fName ):
        " Loads the general settings file "
        config = ConfigParser.ConfigParser()
        try:
            config.read( [ fName ] )
            self.marginPaper = buildColor( config.get( "general",
                                                       "marginpaper" ) )
            self.marginPaperDebug = buildColor( config.get( "general",
                                                            "marginpaperdebug" ) )
            self.marginColor = buildColor( config.get( "general",
                                                       "margincolor" ) )
            self.marginColorDebug = buildColor( config.get( "general",
                                                            "margincolordebug" ) )
            self.lineNumFont = buildFont( config.get( "general",
                                                      "linenumfont" ) )

            self.foldingPaper = buildColor( config.get( "general",
                                                        "foldingpaper" ) )
            self.foldingColor = buildColor( config.get( "general",
                                                        "foldingcolor" ) )

            self.searchMarkColor = buildColor( config.get( "general",
                                                           "searchmarkcolor" ) )
            self.searchMarkAlpha = config.getint( "general",
                                                  "searchmarkalpha" )
            self.matchMarkColor = buildColor( config.get( "general",
                                                          "matchmarkcolor" ) )
            self.matchMarkAlpha = config.getint( "general",
                                                 "matchmarkalpha" )
            self.spellingMarkColor = buildColor( config.get( "general",
                                                             "spellingmarkcolor" ) )
            self.spellingMarkAlpha = config.getint( "general",
                                                    "spellingmarkalpha" )

            self.nolexerPaper = buildColor( config.get( "general",
                                                        "nolexerpaper" ) )
            self.nolexerColor = buildColor( config.get( "general",
                                                        "nolexercolor" ) )
            self.nolexerFont = buildFont( config.get( "general",
                                                      "nolexerfont" ) )

            self.currentLinePaper = buildColor( config.get( "general",
                                                            "currentlinepaper" ) )
            self.edgeColor = buildColor( config.get( "general",
                                                     "edgecolor" ) )
            self.matchedBracePaper = buildColor( config.get( "general",
                                                             "matchedbracepaper" ) )
            self.matchedBraceColor = buildColor( config.get( "general",
                                                             "matchedbracecolor" ) )
            self.unmatchedBracePaper = buildColor( config.get( "general",
                                                               "unmatchedbracepaper" ) )
            self.unmatchedBraceColor = buildColor( config.get( "general",
                                                               "unmatchedbracecolor" ) )

            self.indentGuidePaper = buildColor( config.get( "general",
                                                            "indentguidepaper" ) )
            self.indentGuideColor = buildColor( config.get( "general",
                                                            "indentguidecolor" ) )
        except:
            logging.error( "Cannot read " + fName + ". No skin will be used." )
            return False
        return True

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

