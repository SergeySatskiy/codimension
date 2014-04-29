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
from PyQt4.QtGui import QColor, QFont, QFontComboBox
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


def getMonospaceFontList():
    " Provides a list of strings with the system installed monospace fonts "
    result = []
    combo = QFontComboBox()
    combo.setFontFilters( QFontComboBox.MonospacedFonts )
    for index in xrange( combo.count() ):
        face = str( combo.itemText( index ) )
        if face.lower() != "webdings":
            result.append( face )
    return result


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
                logging.error( "Lexer skin description inconsistence "
                               "detected. Absent entries for index " + index +
                               " in section " + sec )
                continue
        return


class GeneralSkinSetting:
    " Holds a single setting from a general skin config file "
    TYPE_INT = 0
    TYPE_COLOR = 1
    TYPE_FONT = 2
    TYPE_STRING = 3

    def __init__( self, name, sType, default ):
        self.name = name
        self.sType = sType
        self.default = default
        return


SKIN_SETTINGS = [
    GeneralSkinSetting( "marginPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 228, 228, 228, 255 ) ),
    GeneralSkinSetting( "marginPaperDebug", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 228, 228, 255 ) ),
    GeneralSkinSetting( "marginColor", GeneralSkinSetting.TYPE_COLOR, QColor( 128, 128, 128, 255 ) ),
    GeneralSkinSetting( "marginColorDebug", GeneralSkinSetting.TYPE_COLOR, QColor( 128, 128, 128, 255 ) ),
    GeneralSkinSetting( "revisionMarginPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 228, 228, 228, 255 ) ),
    GeneralSkinSetting( "revisionMarginColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 128, 0, 255 ) ),
    GeneralSkinSetting( "revisionAlterPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 238, 240, 241, 255 ) ),
    GeneralSkinSetting( "lineNumFont", GeneralSkinSetting.TYPE_FONT, buildFont( "Monospace,12,-1,5,50,0,0,0,0,0" ) ),
    GeneralSkinSetting( "foldingPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 255, 255 ) ),
    GeneralSkinSetting( "foldingColor", GeneralSkinSetting.TYPE_COLOR, QColor( 230, 230, 230, 255 ) ),
    GeneralSkinSetting( "searchMarkColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 255, 0, 255 ) ),
    GeneralSkinSetting( "searchMarkAlpha", GeneralSkinSetting.TYPE_INT, 100 ),
    GeneralSkinSetting( "searchMarkOutlineAlpha", GeneralSkinSetting.TYPE_INT, 100 ),
    GeneralSkinSetting( "searchMarkStyle", GeneralSkinSetting.TYPE_INT, 8 ),
    GeneralSkinSetting( "matchMarkColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 255, 255 ) ),
    GeneralSkinSetting( "matchMarkAlpha", GeneralSkinSetting.TYPE_INT, 100 ),
    GeneralSkinSetting( "matchMarkOutlineAlpha", GeneralSkinSetting.TYPE_INT, 100 ),
    GeneralSkinSetting( "matchMarkStyle", GeneralSkinSetting.TYPE_INT, 8 ),
    GeneralSkinSetting( "spellingMarkColor", GeneralSkinSetting.TYPE_COLOR, QColor( 139, 0, 0, 255 ) ),
    GeneralSkinSetting( "spellingMarkAlpha", GeneralSkinSetting.TYPE_INT, 100 ),
    GeneralSkinSetting( "nolexerPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 230, 255 ) ),
    GeneralSkinSetting( "nolexerColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "nolexerFont", GeneralSkinSetting.TYPE_FONT, buildFont( "Monospace,12,-1,5,50,0,0,0,0,0" ) ),
    GeneralSkinSetting( "currentLinePaper", GeneralSkinSetting.TYPE_COLOR, QColor( 232, 232, 255, 255 ) ),
    GeneralSkinSetting( "edgeColor", GeneralSkinSetting.TYPE_COLOR, QColor( 127, 127, 127, 255 ) ),
    GeneralSkinSetting( "matchedBracePaper", GeneralSkinSetting.TYPE_COLOR, QColor( 132, 117, 245, 255 ) ),
    GeneralSkinSetting( "matchedBraceColor", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 255, 255 ) ),
    GeneralSkinSetting( "unmatchedBracePaper", GeneralSkinSetting.TYPE_COLOR, QColor( 250, 89, 68, 255 ) ),
    GeneralSkinSetting( "unmatchedBraceColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 255, 255 ) ),
    GeneralSkinSetting( "indentGuidePaper", GeneralSkinSetting.TYPE_COLOR, QColor( 230, 230, 230, 255 ) ),
    GeneralSkinSetting( "indentGuideColor", GeneralSkinSetting.TYPE_COLOR, QColor( 127, 127, 127, 255 ) ),
    GeneralSkinSetting( "debugCurrentLineMarkerPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 127, 255 ) ),
    GeneralSkinSetting( "debugCurrentLineMarkerColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 255, 255 ) ),
    GeneralSkinSetting( "debugExcptLineMarkerPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 64, 64, 255 ) ),
    GeneralSkinSetting( "debugExcptLineMarkerColor", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 127, 255 ) ),
    GeneralSkinSetting( "calltipPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 220, 255, 220, 255 ) ),
    GeneralSkinSetting( "calltipColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "calltipHighColor", GeneralSkinSetting.TYPE_COLOR, QColor( 250, 89, 68, 255 ) ),
    GeneralSkinSetting( "outdatedOutlineColor", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 154, 154, 255 ) ),
    GeneralSkinSetting( "baseMonoFontFace", GeneralSkinSetting.TYPE_STRING, "Monospace" ),

    GeneralSkinSetting( "diffchanged2Color", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "diffchanged2Paper", GeneralSkinSetting.TYPE_COLOR, QColor( 247, 254, 0, 255 ) ),
    GeneralSkinSetting( "diffponctColor", GeneralSkinSetting.TYPE_COLOR, QColor( 166, 72, 72, 255 ) ),
    GeneralSkinSetting( "difflineColor", GeneralSkinSetting.TYPE_COLOR, QColor( 102, 102, 102, 255 ) ),
    GeneralSkinSetting( "diffthColor", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 255, 255 ) ),
    GeneralSkinSetting( "diffthPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 102, 102, 102, 255 ) ),
    GeneralSkinSetting( "diffaddedPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 197, 250, 175, 255 ) ),
    GeneralSkinSetting( "diffchangedColor", GeneralSkinSetting.TYPE_COLOR, QColor( 102, 102, 102, 255 ) ),
    GeneralSkinSetting( "diffchangedPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 244, 255, 221, 255 ) ),
    GeneralSkinSetting( "diffdeletedPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 204, 204, 255 ) ),
    GeneralSkinSetting( "diffhunkinfoColor", GeneralSkinSetting.TYPE_COLOR, QColor( 166, 72, 72, 255 ) ),
    GeneralSkinSetting( "diffhunkinfoPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 255, 255 ) ),
    GeneralSkinSetting( "diffunmodifiedColor", GeneralSkinSetting.TYPE_COLOR, QColor( 102, 102, 102, 255 ) ),
    GeneralSkinSetting( "diffunmodifiedPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 238, 238, 238, 255 ) ),

    GeneralSkinSetting( "ioconsolePaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 230, 255 ) ),
    GeneralSkinSetting( "ioconsoleColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "ioconsoleStdoutPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 230, 255 ) ),
    GeneralSkinSetting( "ioconsoleStdoutColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "ioconsoleStdoutBold", GeneralSkinSetting.TYPE_INT, 0 ),
    GeneralSkinSetting( "ioconsoleStdoutItalic", GeneralSkinSetting.TYPE_INT, 0 ),
    GeneralSkinSetting( "ioconsoleStdinPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 255, 230, 255 ) ),
    GeneralSkinSetting( "ioconsoleStdinColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "ioconsoleStdinBold", GeneralSkinSetting.TYPE_INT, 0 ),
    GeneralSkinSetting( "ioconsoleStdinItalic", GeneralSkinSetting.TYPE_INT, 0 ),
    GeneralSkinSetting( "ioconsoleStderrPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 255, 228, 228, 255 ) ),
    GeneralSkinSetting( "ioconsoleStderrColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 0, 255 ) ),
    GeneralSkinSetting( "ioconsoleStderrBold", GeneralSkinSetting.TYPE_INT, 0 ),
    GeneralSkinSetting( "ioconsoleStderrItalic", GeneralSkinSetting.TYPE_INT, 0 ),
    GeneralSkinSetting( "ioconsoleIDEMsgPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 228, 228, 228, 255 ) ),
    GeneralSkinSetting( "ioconsoleIDEMsgColor", GeneralSkinSetting.TYPE_COLOR, QColor( 0, 0, 255, 255 ) ),
    GeneralSkinSetting( "ioconsolemarginPaper", GeneralSkinSetting.TYPE_COLOR, QColor( 228, 228, 228, 255 ) ),
    GeneralSkinSetting( "ioconsolemarginColor", GeneralSkinSetting.TYPE_COLOR, QColor( 128, 128, 128, 255 ) ),
    GeneralSkinSetting( "ioconsolemarginFont", GeneralSkinSetting.TYPE_FONT, buildFont( "Monospace,12,-1,5,50,0,0,0,0,0" ) ),
                ]


class SkinData:
    " Bad excuse to have it due to __getattr__/__setattr__ in the Skin class "

    def __init__( self ):
        self.isOK = True
        self.dirName = None
        self.name = ""
        self.lexerStyles = {}   # name -> LexerStyles
        self.appCSS = ""

        self.values = {}
        return



class Skin:
    " Holds the definitions for a skin "

    def __init__( self ):
        # That's a trick to be able to implement getattr/setattr
        self.__dict__[ "data" ] = SkinData()
        self.__reset()
        return

    def __reset( self ):
        " Resets all the values to the default "
        self.data.name = "default"
        self.data.lexerStyles = {}
        self.data.appCSS = """
            QStatusBar::item
            { border: 0px solid black }
            QToolTip
            { font-size: 11px;
              border: 1px solid gray;
              border-radius: 3px;
              background: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #eef, stop: 1 #ccf );
            }
            QTreeView
            { alternate-background-color: #eef0f1;
              background-color: #ffffe6; }
            QLineEdit
            { background-color: #ffffe6; }
            QComboBox
            { background-color: #ffffe6; color: black; }
            QComboBox QAbstractItemView
            { outline: 0px; }
            QTextEdit
            { background-color: #ffffe6; }
            QListView
            { background-color: #ffffe6; }
            """

        for setting in SKIN_SETTINGS:
            self.data.values[ setting.name ] = setting.default
        return


    def load( self, dirName ):
        " Loads the skin description from the given directory "
        self.data.dirName = os.path.abspath( dirName )
        self.data.name = os.path.basename( dirName )

        # Load the skin description
        self.data.dirName += os.path.sep
        appFile = self.data.dirName + "application.css"
        if not os.path.exists( appFile ):
            logging.warning( "Cannot find " + appFile +
                             ". Default skin will be used." )
            self.__reset()
            return False

        generalFile = self.data.dirName + "general"
        if not os.path.exists( generalFile ):
            logging.warning( "Cannot find " + generalFile +
                             ". Default skin will be used." )
            self.__reset()
            return False

        lexersFile = self.data.dirName + "lexers"
        if not os.path.exists( lexersFile ):
            logging.warning( "Cannot find " + lexersFile +
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
            self.data.appCSS = "".join( content )
        except:
            logging.warning( "Cannot read application CSS from " + fName +
                             ". The file will be updated with a default CSS." )
            return False
        return True

    def __getColor( self, config, section, value ):
        " Reads a value from the given section "
        try:
            return buildColor( config.get( section, value ) )
        except:
            self.data.isOK = False
            return None

    def __getFont( self, config, section, value ):
        " Reads a value from the given section "
        try:
            return buildFont( config.get( section, value ) )
        except:
            self.data.isOK = False
            return None

    def __getInt( self, config, section, value ):
        " Reads a value from the given section "
        try:
            return config.getint( section, value )
        except:
            self.data.isOK = False
            return None

    def __getString( self, config, section, value ):
        " Reads a string value from the given section "
        try:
            return config.get( section, value )
        except:
            self.data.isOK = False
            return None

    def __loadGeneral( self, fName ):
        " Loads the general settings file "
        config = ConfigParser.ConfigParser()
        try:
            config.read( [ fName ] )
        except:
            logging.warning( "Cannot read the skin file " + fName +
                             ". The file will be updated with default values." )
            return False

        for setting in SKIN_SETTINGS:
            if setting.sType == GeneralSkinSetting.TYPE_INT:
                val = self.__getInt( config, "general", setting.name.lower() )
                if val is not None:
                    self.data.values[ setting.name ] = val
            elif setting.sType == GeneralSkinSetting.TYPE_COLOR:
                val = self.__getColor( config, "general", setting.name.lower() )
                if val is not None:
                    self.data.values[ setting.name ] = val
            elif setting.sType == GeneralSkinSetting.TYPE_FONT:
                val = self.__getFont( config, "general", setting.name.lower() )
                if val is not None:
                    self.data.values[ setting.name ] = val
            elif setting.sType == GeneralSkinSetting.TYPE_STRING:
                val = self.__getString( config, "general", setting.name.lower() )
                if val is not None:
                    self.data.values[ setting.name ] = val
            else:
                raise Exception( "Unsupported setting type: " +
                                 str( setting.sType ) )
        return self.data.isOK

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
            self.data.lexerStyles[ section ] = lexerStyles
        return True

    def getLexerStyles( self, name ):
        " Provides the lexer style "
        try:
            return self.data.lexerStyles[ name ]
        except KeyError:
            # could not find the style, provide a substitute
            pass

        substitute = LexerStyles()
        substitute.styles.append( StyleParameters() )
        return substitute

    def clearLexerStyles( self ):
        " Cleans up memory taken by the lexer styles "
        self.data.lexerStyles = {}
        return

    def __saveGeneral( self, fName ):
        " Writes the general skin file "
        try:
            f = open( fName, "w" )
            f.write( "# Automatically updated due to missed or corrupted values\n" )
            f.write( "#\n" )
            f.write( "# Note: indicator style values (searchMarkStyle, matchMarkStyle) are described here:\n" )
            f.write( "# http://www.scintilla.org/ScintillaDoc.html#SCI_INDICSETSTYLE\n" )
            f.write( "[general]\n" )
            f.write( "name=" + self.data.name + "\n\n" )

            for setting in SKIN_SETTINGS:
                if setting.sType == GeneralSkinSetting.TYPE_INT:
                    f.write( setting.name.lower() + "=" +
                             str( self.data.values[ setting.name ] ) + "\n" )
                elif setting.sType == GeneralSkinSetting.TYPE_COLOR:
                    f.write( setting.name.lower() + "=" +
                             colorAsString( self.data.values[ setting.name ] ) + "\n" )
                elif setting.sType == GeneralSkinSetting.TYPE_FONT:
                    f.write( setting.name.lower() + "=" +
                             self.data.values[ setting.name ].toString() + "\n" )
                elif setting.sType == GeneralSkinSetting.TYPE_STRING:
                    f.write( setting.name.lower() + "=" +
                             self.data.values[ setting.name ] + "\n" )
                else:
                    raise Exception( "Unsupported setting type: " +
                                     str( setting.sType ) )

            f.close()
        except:
            logging.warning( "Could not write skin file " + fName )
        return

    def __saveAppCSS( self, appFile ):
        " Writes the application CSS "
        try:
            f = open( appFile, "w" )
            f.write( self.data.appCSS + "\n" )
            f.close()
        except:
            logging.warning( "Could not write skin CSS file " + appFile )
        return

    def setMainEditorFont( self, font ):
        """ Updates what is stored in the lexers and general settings.
            The only font family and font size are respected """

        def replaceFontWith( line, family, size ):
            " Replaces the font face and size in line from a config file "
            parts = line.split( '=' )
            identifier = parts[ 0 ]
            value = parts[ 1 ]

            parts = value.split( ',' )
            parts[ 0 ] = family
            parts[ 1 ] = size

            return identifier + '=' + ','.join( parts )


        if self.data.dirName is None:
            raise Exception( "The skin is not loaded" )

        lexersFile = self.data.dirName + "lexers"
        if not os.path.exists( lexersFile ):
            raise Exception( "Cannot find the lexers file. Expected here: " +
                             lexersFile )

        f = open( lexersFile, "r" )
        content = f.read()
        f.close()

        fontAsString = str( font.toString() ).split( "," )
        family = fontAsString[ 0 ]
        size = fontAsString[ 1 ]

        updatedContent = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith( "font" ):
                updatedContent.append( replaceFontWith( line, family, size ) )
            else:
                updatedContent.append( line )

        f = open( lexersFile, "w" )
        f.write( "\n".join( updatedContent ) )
        f.close()
        f = None

        generalFile = self.data.dirName + "general"
        if not os.path.exists( generalFile ):
            raise Exception( "Cannot find the general skin file. Expected here: " +
                             generalFile )

        f = open( generalFile, "r" )
        content = f.read()
        f.close()

        updatedContent = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith( "nolexerfont" ):
                updatedContent.append( replaceFontWith( line, family, size ) )
            elif line.startswith( "linenumfont" ):
                updatedContent.append( replaceFontWith( line, family, size ) )
            elif line.startswith( "ioconsolemarginfont" ):
                updatedContent.append( replaceFontWith( line, family, size ) )
            else:
                updatedContent.append( line )

        f = open( generalFile, "w" )
        f.write( "\n".join( updatedContent ) )
        f.close()
        f = None
        return

    def setBaseMonoFontFace( self, fontFace ):
        " Updates the base mono font face "
        if self.data.dirName is None:
            raise Exception( "The skin is not loaded" )

        generalFile = self.data.dirName + "general"
        if not os.path.exists( generalFile ):
            raise Exception( "Cannot find the general skin file. Expected here: " +
                             generalFile )

        f = open( generalFile, "r" )
        content = f.read()
        f.close()

        updatedContent = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith( "basemonofontface" ):
                updatedContent.append( "basemonofontface=" +fontFace )
            else:
                updatedContent.append( line )

        f = open( generalFile, "w" )
        f.write( "\n".join( updatedContent ) )
        f.close()
        f = None
        return

    def __getattr__( self, aAttr ):
        if hasattr( self.data, aAttr ):
            return getattr( self.data, aAttr )
        return self.data.values[ aAttr ]

    def __setattr__( self, aAttr, aValue ):
        if hasattr( self.data, aAttr ):
            setattr( self.data, aAttr, aValue )
        else:
            self.data.values[ aAttr ] = aValue
        return

