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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#


""" Lexers for the various supported programming languages """


from PyQt4.QtCore    import QStringList
from PyQt4.QtGui     import QApplication
from utils.fileutils import ( PythonFileType, Python3FileType, RubyFileType,
                              DesignerFileType, DesignerHeaderFileType,
                              LinguistFileType, QTResourceFileType,
                              CodimensionProjectFileType, IDLFileType,
                              SVGFileType, DFileType, CFileType,
                              CHeaderFileType, CPPFileType, CPPHeaderFileType,
                              HTMLFileType, CSSFileType, XMLFileType,
                              MakefileType, ShellFileType, JavascriptFileType,
                              DiffFileType, JavaFileType, PascalFileType,
                              PerlFileType, TCLFileType, PropsFileType )


# The lexer registry
# Dictionary with the language name as key. Each entry is a list with
#       0. display string (QString)
#       1. dummy filename to derive lexer name (string)
#       2. reference to a function instantiating the specific lexer
#          This function must take a reference to the parent as argument.
#       3. list of open file filters (QStringList)
#       4. list of save file filters (QStringList)
#       5. default lexer associations (list of strings of filename wildcard
#          patterns to be associated with the lexer)
LexerRegistry = {}


def registerLexer( name, displayString, filenameSample, getLexerFunc,
                   openFilters = QStringList(), saveFilters = QStringList(),
                   defaultAssocs = [] ):
    """ Registers a custom QScintilla lexer """

    if name in LexerRegistry:
        raise KeyError( 'Lexer "%s" already registered.' % name )

    LexerRegistry[ name ] = [ displayString, filenameSample, getLexerFunc,
                              openFilters, saveFilters, defaultAssocs[:] ]
    return


def unregisterLexer( name ):
    """ Unregisters a custom QScintilla lexer """

    if name in LexerRegistry:
        del LexerRegistry[ name ]
    return


def getSupportedLanguages():
    """ Provides a dictionary of supported lexer languages """

    supportedLanguages = {
        "Bash"       : [ "Bash",         'dummy.sh' ],
        "Batch"      : [ "Batch",        'dummy.bat' ],
        "C++"        : [ "C/C++",        'dummy.cpp' ],
        "C#"         : [ "C#",           'dummy.cs' ],
        "CMake"      : [ "CMake",        'dummy.cmake' ],
        "CSS"        : [ "CSS",          'dummy.css' ],
        "D"          : [ "D",            'dummy.d' ],
        "Diff"       : [ "Diff",         'dummy.diff' ],
        "HTML"       : [ "HTML/PHP/XML", 'dummy.html' ],
        "IDL"        : [ "IDL",          'dummy.idl' ],
        "Java"       : [ "Java",         'dummy.java' ],
        "JavaScript" : [ "JavaScript",   'dummy.js' ],
        "Lua"        : [ "Lua",          'dummy.lua' ],
        "Makefile"   : [ "Makefile",     'dummy.mak' ],
        "Perl"       : [ "Perl",         'dummy.pl' ],
        "Povray"     : [ "Povray",       'dummy.pov' ],
        "Properties" : [ "Properties",   'dummy.ini' ],
        "Python"     : [ "Python",       'dummy.py' ],
        "Ruby"       : [ "Ruby",         'dummy.rb' ],
        "SQL"        : [ "SQL",          'dummy.sql' ],
        "TeX"        : [ "TeX",          'dummy.tex' ],
        "VHDL"       : [ "VHDL",         'dummy.vhd' ],
        "TCL"        : [ "TCL",          'dummy.tcl' ],
        "Fortran"    : [ "Fortran",      'dummy.f95' ],
        "Fortran77"  : [ "Fortran77",    'dummy.f' ],
        "Pascal"     : [ "Pascal",       'dummy.pas' ],
        "PostScript" : [ "PostScript",   'dummy.ps' ],
        "XML"        : [ "XML",          'dummy.xml' ],
        "YAML"       : [ "YAML",         'dummy.yml' ] }

    for name in LexerRegistry:
        supportedLanguages[ name ] = LexerRegistry[ name ][ :2 ]

    supportedLanguages[ "Guessed" ] = \
        [ "Pygments", 'dummy.pygments' ]

    return supportedLanguages

from lexerpython import LexerPython
from lexerruby import LexerRuby
from lexerd import LexerD
from lexerhtml import LexerHTML
from lexercss import LexerCSS
from lexeridl import LexerIDL
from lexermakefile import LexerMakefile
from lexercpp import LexerCPP
from lexerxml import LexerXML
from lexerproperties import LexerProperties
from lexerbash import LexerBash
from lexerjavascript import LexerJavaScript
from lexerdiff import LexerDiff
from lexerjava import LexerJava
from lexerpascal import LexerPascal
from lexerperl import LexerPerl
from lexertcl import LexerTCL
from lexerproperties import LexerProperties

__lexers = { PythonFileType             : LexerPython(),
             Python3FileType            : LexerPython(),
             RubyFileType               : LexerRuby(),
             DFileType                  : LexerD(),
             HTMLFileType               : LexerHTML(),
             CSSFileType                : LexerCSS(),
             IDLFileType                : LexerIDL(),
             MakefileType               : LexerMakefile(),
             CFileType                  : LexerCPP( None, 0 ),
             CHeaderFileType            : LexerCPP( None, 0 ),
             CPPFileType                : LexerCPP( None, 0 ),
             CPPHeaderFileType          : LexerCPP( None, 0 ),
             DesignerHeaderFileType     : LexerCPP( None, 0 ),
             DesignerFileType           : LexerXML(),
             XMLFileType                : LexerXML(),
             LinguistFileType           : LexerXML(),
             QTResourceFileType         : LexerXML(),
             SVGFileType                : LexerXML(),
             CodimensionProjectFileType : LexerProperties(),
             ShellFileType              : LexerBash(),
             JavascriptFileType         : LexerJavaScript(),
             DiffFileType               : LexerDiff(),
             JavaFileType               : LexerJava(),
             PascalFileType             : LexerPascal(),
             PerlFileType               : LexerPerl(),
             TCLFileType                : LexerTCL(),
             PropsFileType              : LexerProperties() }

_skin = None

def getLexerByType( fileType, fileName, parent = None ):
    " Provides the lexer for the given file type "
    try:
        return __lexers[ fileType ]
    except:
        lexer = __getPygmentsLexerByFileName( parent, fileName )
        if lexer is not None:
            updateLexerStyle( lexer, _skin.getLexerStyles( "Guessed" ).styles )
        return lexer

def updateLexerStyle( lexer, styles ):
    " Updates a single lexer styles "
    for style in styles:
        lexer.setColor( style.color, style.index )
        lexer.setPaper( style.paper, style.index )
        lexer.setEolFill( style.eolFill, style.index )
        lexer.setFont( style.font, style.index )
    return

def updateLexersStyles( skin ):
    " updates the lexers styles in accordance with the given skin "
    global _skin
    _skin = skin
    for key in __lexers:
        lexer = __lexers[ key ]
        lexerStyles = skin.getLexerStyles( lexer.language() )
        updateLexerStyle( lexer, lexerStyles.styles )
    return



def getLexerByTypeObsolete( fileType, fileName, parent = None ):
    " Provides the lexer for the given file type "

    if fileType in [ PythonFileType, Python3FileType ]:
        from lexerpython import LexerPython
        return LexerPython( parent )
    if fileType == RubyFileType:
        from lexerruby import LexerRuby
        return LexerRuby( parent )
    if fileType == DFileType:
        from lexerd import LexerD
        return LexerD( parent )
    if fileType == HTMLFileType:
        from lexerhtml import LexerHTML
        return LexerHTML( parent )
    if fileType == CSSFileType:
        from lexercss import LexerCSS
        return LexerCSS( parent )
    if fileType == IDLFileType:
        from lexeridl import LexerIDL
        return LexerIDL( parent )
    if fileType == MakefileType:
        from lexermakefile import LexerMakefile
        return LexerMakefile( parent )
    if fileType in [ CFileType, CHeaderFileType,
                     CPPFileType, CPPHeaderFileType,
                     DesignerHeaderFileType ]:
        from lexercpp import LexerCPP
        return LexerCPP( parent, 0 )
    if fileType in [ DesignerFileType, XMLFileType,
                     LinguistFileType, QTResourceFileType,
                     SVGFileType ]:
        from lexerxml import LexerXML
        return LexerXML( parent )
    if fileType == CodimensionProjectFileType:
        from lexerproperties import LexerProperties
        return LexerProperties( parent )

    # FIXME: I guess fileName is not what the pygments lexer expects
    return __getPygmentsLexerByFileName( parent, fileName )




def getLexer( language, parent = None, pyname = "" ):
    """ Instantiates a lexer object for a given language """

    if not pyname:
        try:
            if language in [ "Python", "Python3" ]:
                from lexerpython import LexerPython
                return LexerPython( parent )
            if language == "C++":
                from lexercpp import LexerCPP
                return LexerCPP( parent, 0 )
            if language == "C#":
                from lexercsharp import LexerCSharp
                return LexerCSharp( parent )
            if language == "IDL":
                from lexeridl import LexerIDL
                return LexerIDL( parent )
            if language == "Java":
                from lexerjava import LexerJava
                return LexerJava( parent )
            if language == "JavaScript":
                from lexerjavascript import LexerJavaScript
                return LexerJavaScript( parent )
            if language == "SQL":
                from lexersql import LexerSQL
                return LexerSQL( parent )
            if language == "HTML":
                from lexerhtml import LexerHTML
                return LexerHTML( parent )
            if language == "Perl":
                from lexerperl import LexerPerl
                return LexerPerl( parent )
            if language == "Bash":
                from lexerbash import LexerBash
                return LexerBash( parent )
            if language == "Ruby":
                from lexerruby import LexerRuby
                return LexerRuby( parent )
            if language == "Lua":
                from lexerlua import LexerLua
                return LexerLua( parent )
            if language == "CSS":
                from lexercss import LexerCSS
                return LexerCSS( parent )
            if language == "TeX":
                from lexertex import LexerTeX
                return LexerTeX( parent )
            if language == "Diff":
                from lexerdiff import LexerDiff
                return LexerDiff( parent )
            if language == "Makefile":
                from lexermakefile import LexerMakefile
                return LexerMakefile( parent )
            if language == "Properties":
                from lexerproperties import LexerProperties
                return LexerProperties( parent )
            if language == "Batch":
                from lexerbatch import LexerBatch
                return LexerBatch( parent )
            if language == "D":
                from lexerd import LexerD
                return LexerD( parent )
            if language == "Povray":
                from lexerpov import LexerPOV
                return LexerPOV( parent )
            if language == "CMake":
                from lexercmake import LexerCMake
                return LexerCMake( parent )
            if language == "VHDL":
                from lexervhdl import LexerVHDL
                return LexerVHDL( parent )
            if language == "TCL":
                from lexertcl import LexerTCL
                return LexerTCL( parent )
            if language == "Fortran":
                from lexerfortran import LexerFortran
                return LexerFortran( parent )
            if language == "Fortran77":
                from lexerfortran77 import LexerFortran77
                return LexerFortran77( parent )
            if language == "Pascal":
                from lexerpascal import LexerPascal
                return LexerPascal( parent )
            if language == "PostScript":
                from lexerpostscript import LexerPostScript
                return LexerPostScript( parent )
            if language == "XML":
                from lexerxml import LexerXML
                return LexerXML( parent )
            if language == "YAML":
                from lexeryaml import LexerYAML
                return LexerYAML( parent )
            if language in LexerRegistry:
                return LexerRegistry[ language ][ 2 ]( parent )
            return __getPygmentsLexer( parent )
        except ImportError:
            return __getPygmentsLexer( parent )

    return __getPygmentsLexer( parent, name = pyname )


def __getPygmentsLexerByFileName( parent, fileName ):

    from lexerpygments import LexerPygments

    lexer = LexerPygments( parent, "", fileName )
    if lexer.canStyle():
        return lexer
    return None

def __getPygmentsLexer( parent, name = "" ):
    """ Instantiates a pygments lexer """

    from lexerpygments import LexerPygments

    lexer = LexerPygments( parent, name = name )
    if lexer.canStyle():
        return lexer

    return None


def getOpenFileFiltersList( includeAll = False, asString = False ):
    """ Provides the file filter list for an open file operation """

    openFileFiltersList = QStringList() \
        << 'Python Files (*.py *.py3)' \
        << 'Python GUI Files (*.pyw *.pyw3)' \
        << 'Pyrex Files (*.pyx)' \
        << 'Quixote Template Files (*.ptl)' \
        << 'Ruby Files (*.rb)' \
        << 'IDL Files (*.idl)' \
        << 'C Files (*.h *.c)' \
        << 'C++ Files (*.h *.hpp *.hh *.cxx *.cpp *.cc)' \
        << 'C# Files (*.cs)' \
        << 'HTML Files (*.html *.htm *.asp *.shtml)' \
        << 'CSS Files (*.css)' \
        << 'QSS Files (*.qss)' \
        << 'PHP Files (*.php *.php3 *.php4 *.php5 *.phtml)' \
        << 'XML Files (*.xml *.xsl *.xslt *.dtd *.svg *.xul *.xsd)' \
        << 'Qt Resource Files (*.qrc)' \
        << 'D Files (*.d *.di)' \
        << 'Java Files (*.java)' \
        << 'JavaScript Files (*.js)' \
        << 'SQL Files (*.sql)' \
        << 'Docbook Files (*.docbook)' \
        << 'Perl Files (*.pl *.pm *.ph)' \
        << 'Lua Files (*.lua)' \
        << 'Tex Files (*.tex *.sty *.aux *.toc *.idx)' \
        << 'Shell Files (*.sh)' \
        << 'Batch Files (*.bat *.cmd)' \
        << 'Diff Files (*.diff *.patch)' \
        << 'Makefiles (*.mak)' \
        << 'Properties Files ' \
           '(*.properties *.ini *.inf *.reg *.cfg *.cnf *.rc)' \
        << 'Povray Files (*.pov)' \
        << 'CMake Files (CMakeLists.txt *.cmake *.ctest)' \
        << 'VHDL Files (*.vhd *.vhdl)' \
        << 'TCL/Tk Files (*.tcl *.tk)' \
        << 'Fortran Files (*.f90 *.f95 *.f2k)' \
        << 'Fortran77 Files (*.f *.for)' \
        << 'Pascal Files (*.dpr *.dpk *.pas *.dfm *.inc *.pp)' \
        << 'PostScript Files (*.ps)' \
        << 'YAML Files (*.yaml *.yml)'

    for name in LexerRegistry:
        openFileFiltersList << LexerRegistry[ name ][ 3 ]

    openFileFiltersList.sort()
    if includeAll:
        openFileFiltersList.append( 'All Files (*)' )

    if asString:
        return openFileFiltersList.join( ';;' )
    return openFileFiltersList


def getSaveFileFiltersList( includeAll = False, asString = False ):
    " Provides the file filter list for a save file operation "

    saveFileFiltersList = QStringList() \
        << "Python Files (*.py)" \
        << "Python3 Files (*.py3)" \
        << "Python GUI Files (*.pyw)" \
        << "Python3 GUI Files (*.pyw3)" \
        << "Pyrex Files (*.pyx)" \
        << "Quixote Template Files (*.ptl)" \
        << "Ruby Files (*.rb)" \
        << "IDL Files (*.idl)" \
        << "C Files (*.c)" \
        << "C++ Files (*.cpp)" \
        << "C++/C Header Files (*.h)" \
        << "C# Files (*.cs)" \
        << "HTML Files (*.html)" \
        << "PHP Files (*.php)" \
        << "ASP Files (*.asp)" \
        << "CSS Files (*.css)" \
        << "QSS Files (*.qss)" \
        << "XML Files (*.xml)" \
        << "XSL Files (*.xsl)" \
        << "DTD Files (*.dtd)" \
        << "Qt Resource Files (*.qrc)" \
        << "D Files (*.d)" \
        << "D Interface Files (*.di)" \
        << "Java Files (*.java)" \
        << "JavaScript Files (*.js)" \
        << "SQL Files (*.sql)" \
        << "Docbook Files (*.docbook)" \
        << "Perl Files (*.pl)" \
        << "Perl Module Files (*.pm)" \
        << "Lua Files (*.lua)" \
        << "Shell Files (*.sh)" \
        << "Batch Files (*.bat)" \
        << "TeX Files (*.tex)" \
        << "TeX Template Files (*.sty)" \
        << "Diff Files (*.diff)" \
        << "Make Files (*.mak)" \
        << "Properties Files (*.ini)" \
        << "Configuration Files (*.cfg)" \
        << 'Povray Files (*.pov)' \
        << 'CMake Files (CMakeLists.txt)' \
        << 'CMake Macro Files (*.cmake)' \
        << 'VHDL Files (*.vhd)' \
        << 'TCL Files (*.tcl)' \
        << 'Tk Files (*.tk)' \
        << 'Fortran Files (*.f95)' \
        << 'Fortran77 Files (*.f)' \
        << 'Pascal Files (*.pas)' \
        << 'PostScript Files (*.ps)' \
        << 'YAML Files (*.yml)'

    for name in LexerRegistry:
        saveFileFiltersList << LexerRegistry[ name ][ 4 ]

    saveFileFiltersList.sort()

    if includeAll:
        saveFileFiltersList.append( 'All Files (*)' )

    if asString:
        return saveFileFiltersList.join( ';;' )
    return saveFileFiltersList


def getDefaultLexerAssociations():
    """ Makes the default associations """

    assocs = {
        '*.sh'              : "Bash",
        '*.bash'            : "Bash",
        "*.bat"             : "Batch",
        "*.cmd"             : "Batch",
        '*.cpp'             : "C++",
        '*.cxx'             : "C++",
        '*.cc'              : "C++",
        '*.c'               : "C++",
        '*.hpp'             : "C++",
        '*.hh'              : "C++",
        '*.h'               : "C++",
        '*.cs'              : "C#",
        'CMakeLists.txt'    : "CMake",
        '*.cmake'           : "CMake",
        '*.cmake.in'        : "CMake",
        '*.ctest'           : "CMake",
        '*.ctest.in'        : "CMake",
        '*.css'             : "CSS",
        '*.qss'             : "CSS",
        "*.d"               : "D",
        "*.di"              : "D",
        "*.diff"            : "Diff",
        "*.patch"           : "Diff",
        '*.html'            : "HTML",
        '*.htm'             : "HTML",
        '*.asp'             : "HTML",
        '*.shtml'           : "HTML",
        '*.php'             : "HTML",
        '*.php3'            : "HTML",
        '*.php4'            : "HTML",
        '*.php5'            : "HTML",
        '*.phtml'           : "HTML",
        '*.docbook'         : "HTML",
        '*.ui'              : "HTML",
        '*.ts'              : "HTML",
        '*.qrc'             : "HTML",
        '*.e3d'             : "HTML",
        '*.e3k'             : "HTML",
        '*.e3p'             : "HTML",
        '*.e3s'             : "HTML",
        '*.e3t'             : "HTML",
        '*.e4d'             : "HTML",
        '*.e4k'             : "HTML",
        '*.e4m'             : "HTML",
        '*.e4p'             : "HTML",
        '*.e4q'             : "HTML",
        '*.e4s'             : "HTML",
        '*.e4t'             : "HTML",
        '*.kid'             : "HTML",
        '*.idl'             : "IDL",
        '*.java'            : "Java",
        '*.js'              : "JavaScript",
        '*.lua'             : "Lua",
        "*makefile"         : "Makefile",
        "Makefile*"         : "Makefile",
        "*.mak"             : "Makefile",
        '*.pl'              : "Perl",
        '*.pm'              : "Perl",
        '*.ph'              : "Perl",
        '*.pov'             : "Povray",
        "*.properties"      : "Properties",
        "*.ini"             : "Properties",
        "*.inf"             : "Properties",
        "*.reg"             : "Properties",
        "*.cfg"             : "Properties",
        "*.cnf"             : "Properties",
        "*.rc"              : "Properties",
        '*.py'              : "Python",
        '*.pyw'             : "Python",
        '*.pyx'             : "Python",
        '*.ptl'             : "Python",
        '*.rb'              : "Ruby",
        '*.rbw'             : "Ruby",
        '*.sql'             : "SQL",
        "*.tex"             : "TeX",
        "*.sty"             : "TeX",
        "*.aux"             : "TeX",
        "*.toc"             : "TeX",
        "*.idx"             : "TeX",
        '*.vhd'             : "VHDL",
        '*.vhdl'            : "VHDL",
        "*.tcl"             : "TCL",
        "*.tk"              : "TCL",
        "*.f"               : "Fortran77",
        "*.for"             : "Fortran77",
        "*.f90"             : "Fortran",
        "*.f95"             : "Fortran",
        "*.f2k"             : "Fortran",
        "*.dpr"             : "Pascal",
        "*.dpk"             : "Pascal",
        "*.pas"             : "Pascal",
        "*.dfm"             : "Pascal",
        "*.inc"             : "Pascal",
        "*.pp"              : "Pascal",
        "*.ps"              : "PostScript",
        "*.xml"             : "XML",
        "*.xsl"             : "XML",
        "*.svg"             : "XML",
        "*.xsd"             : "XML",
        "*.xslt"            : "XML",
        "*.dtd"             : "XML",
        "*.rdf"             : "XML",
        "*.xul"             : "XML",
        "*.yaml"            : "YAML",
        "*.yml"             : "YAML" }

    for name in LexerRegistry:
        for pattern in LexerRegistry[ name ][ 5 ]:
            assocs[ pattern ] = name

    return assocs

