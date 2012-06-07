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

" Wrappers for PythonTidy.py script "

import os.path
import difflib
import ConfigParser
import thirdparty.pythontidy.PythonTidy as PythonTidy
from tidysettings import TIDY_SETTINGS
from utils.globals import GlobalData
from utils.settings import Settings



def getPythonTidySettingFileName():
    " provides the .ini file name "
    if GlobalData().project.isLoaded():
        return GlobalData().project.userProjectDir + "pythontidy.ini"
    return Settings().settingsDir + "pythontidy.ini"


def getPythonTidySetting():
    " Provides the instance of the settings class "
    # Detect the file name where settings are to be stored
    fileName = getPythonTidySettingFileName()

    pythonTidySettings = PythonTidySetting()
    pythonTidySettings.setToDefault()
    if os.path.exists( fileName ):
        if pythonTidySettings.loadFromFile( fileName ):
            return pythonTidySettings

    # Loading problems, save the defaults
    pythonTidySettings.saveToFile( fileName )
    return pythonTidySettings



class PythonTidySetting:
    " Holds what can be configured in PythonTidy "

    def __init__( self ):
        self.settings = {}
        return

    def applyValues( self ):
        " Applies the settings to the PythonTidy.py global vars "
        for key in self.settings:
            typeName = TIDY_SETTINGS[ key ][ 1 ]
            if typeName == 'int':
                setattr( PythonTidy, key, int( self.settings[ key ] ) )
            elif typeName == 'bool':
                setattr( PythonTidy, key, bool( self.settings[ key ] ) )
            elif typeName == 'string':
                if self.__couldBeNone( key ) and self.settings[ key ] == '':
                    setattr( PythonTidy, key, None )
                else:
                    setattr( PythonTidy, key, str( self.settings[ key ] ) )
            else:
                raise Exception( "Unknown PythonTidy parameter type (" + \
                                 typeName + "). Parameter name: " + key )
        return

    @staticmethod
    def getDescription( name ):
        " Provides a parameter description "
        return TIDY_SETTINGS[ name ][ 0 ]

    def setToDefault( self ):
        " Sets all the values to default ones "
        self.settings = {}
        for key in TIDY_SETTINGS:
            self.settings[ key ] = self.getDefaultValue( key )
        return

    @staticmethod
    def getDefaultValue( name ):
        " Returns a default parameter value "
        typeName = TIDY_SETTINGS[ name ][ 1 ]
        value = TIDY_SETTINGS[ name ][ 2 ]
        if typeName == 'int':
            return value
        if typeName == 'bool':
            return value
        if typeName == 'string':
            if value is None:
                return ''
            return value
        raise Exception( "Unknown PythonTidy parameter type (" + \
                         typeName + "). Parameter name: " + name )

    def saveToFile( self, fileName ):
        " Saves the current settings to the given file "
        f = open( fileName, "w" )
        f.write( "# PythonTidy.py settings\n" )
        f.write( "# Automatically generated; avoid changing manually\n" )
        f.write( "[general]\n" )
        for key in self.settings:
            typeName = TIDY_SETTINGS[ key ][ 1 ]
            if typeName == 'string':
                value = self.settings[ key ].replace( '\n', '<CR><LF>' ) \
                                            .replace( "'", "\\'" )
                f.write( key + "='" + value + "'\n" )
            else:
                f.write( key + "=" + str( self.settings[ key ] ) + "\n" )
        f.close()
        return

    def loadFromFile( self, fileName ):
        " Loads settings from a file "
        self.settings = {}
        config = ConfigParser.ConfigParser()
        isOK = True
        try:
            config.read( fileName )
            for key in TIDY_SETTINGS:
                try:
                    value = conf.get( "general", key ).strip()
                    typeName = self.__getTypeName( key )
                    if typeName == 'int':
                        self.settings[ key ] = int( value )
                    elif typeName == 'bool':
                        self.settings[ key ] = bool( value )
                    elif typeName == 'string':
                        value = value[ 1 : -1 ]
                        value = value.replace( '<CR><LF>', '\n' ) \
                                     .replace( "\\'", "'" )
                        self.settings[ key ] = value
                    else:
                        raise Exception( "Unexpected type" )
                except:
                    self.settings[ key ] = self.getDefaultValue( key )
                    isOK = False
        except:
            # Really bad mistake in the config file, so use defaults
            self.setToDefault()
            return False
        return isOK

    @staticmethod
    def __couldBeNone( name ):
        " True if empty string should be applied as None "
        return TIDY_SETTINGS[ name ][ 2 ] is None

    @staticmethod
    def __getTypeName( name ):
        " Provides the type name for the given parameter "
        return TIDY_SETTINGS[ name ][ 1 ]



class PythonTidyDriver:
    " Wraps the source code beautifier "

    def __init__( self ):
        self.diff = None
        return

    def run( self, srcCode, settings ):
        " Runs the process using the given settings "
        self.diff = None
        settings.applyValues()

        class InputFileLikeDummy:
            def __init__( self, src ):
                self.src = src
            def read( self ):
                return self.src

        class OutputFileLikeDummy:
            def __init__( self ):
                self.buf = ""
            def write( self, what ):
                self.buf += what

        inputStream = InputFileLikeDummy( srcCode )
        outputStream = OutputFileLikeDummy()

        PythonTidy.tidy_up( inputStream, outputStream )
        if outputStream.buf == srcCode:
            return srcCode

        # There is a differense
        inpLines = srcCode.split( '\n' )
        outLines = outputStream.buf.split( '\n' )
        self.diff = difflib.unified_diff( inpLines, outLines )
        return outputStream.buf

    def getDiff( self ):
        " Provides the differences object "
        return self.diff


