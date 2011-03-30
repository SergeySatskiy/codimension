#!/usr/bin/python
#
# File:   dumplexersettings.py
#
# Author: Sergey Satskiy
#
# Date:   Mar 24, 2011
#
# $Id$
#

from PyQt4.Qsci     import QsciLexerBash, QsciLexerBatch, QsciLexerCMake, \
                           QsciLexerCPP, QsciLexerCSharp, \
                           QsciLexerCSS, QsciLexerDiff, QsciLexerD, \
                           QsciLexerFortran77, QsciLexerFortran, \
                           QsciLexerHTML, QsciLexerIDL, QsciLexerJava, \
                           QsciLexerJavaScript, QsciLexerLua, \
                           QsciLexerMakefile, QsciLexerPascal, \
                           QsciLexerPerl, QsciLexerPostScript, \
                           QsciLexerPOV, QsciLexerProperties, \
                           QsciLexerPython, QsciLexerRuby, \
                           QsciLexerSQL, QsciLexerTCL, \
                           QsciLexerTeX, QsciLexerVHDL, QsciLexerXML, \
                           QsciLexerYAML

def colorToString( color ):
    " Converts the QColor to string "
    return str( color.red() ) + "," + \
           str( color.green() ) + "," + \
           str( color.blue() ) + "," + \
           str( color.alpha() )

def dumpLexer( lexer ):
    " Dumps a single lexer settings to the stdout "

    print "[" + lexer.language() + "]"

    indexes = []
    for style in range( 256 ):
        description = lexer.description( style )
        if description == "":
            continue
        print "description" + str( style ) + "=" + description

#        print "defaultColor" + str( style ) + "=" + colorToString( lexer.defaultColor( style ) )
#        print "defaultPaper" + str( style ) + "=" + colorToString( lexer.defaultPaper( style ) )
#        print "defaultEolFill" + str( style ) + "=" + str( lexer.defaultEolFill( style ) )
#        print "defaultFont" + str( style ) + "=" + lexer.defaultFont( style ).toString()

        print "color" + str( style ) + "=" + colorToString( lexer.color( style ) )
        print "paper" + str( style ) + "=" + colorToString( lexer.paper( style ) )
        print "eolFill" + str( style ) + "=" + str( lexer.eolFill( style ) )
        print "font" + str( style ) + "=" + lexer.font( style ).toString()
        indexes.append( str( style ) )

    print "indexes=" + ",".join( indexes )
    print ""
    return


dumpLexer( QsciLexerPython() )
dumpLexer( QsciLexerBash() )
dumpLexer( QsciLexerBatch() )
dumpLexer( QsciLexerCMake() )
dumpLexer( QsciLexerCPP() )
dumpLexer( QsciLexerCSharp() )
dumpLexer( QsciLexerCSS() )
dumpLexer( QsciLexerDiff() )
dumpLexer( QsciLexerD() )
dumpLexer( QsciLexerFortran77() )
dumpLexer( QsciLexerFortran() )
dumpLexer( QsciLexerHTML() )
dumpLexer( QsciLexerIDL() )
dumpLexer( QsciLexerJava() )
dumpLexer( QsciLexerJavaScript() )
dumpLexer( QsciLexerLua() )
dumpLexer( QsciLexerMakefile() )
dumpLexer( QsciLexerPascal() )
dumpLexer( QsciLexerPerl() )
dumpLexer( QsciLexerPostScript() )
dumpLexer( QsciLexerPOV() )
dumpLexer( QsciLexerProperties() )
dumpLexer( QsciLexerRuby() )
dumpLexer( QsciLexerSQL() )
dumpLexer( QsciLexerTCL() )
dumpLexer( QsciLexerTeX() )
dumpLexer( QsciLexerVHDL() )
dumpLexer( QsciLexerXML() )
dumpLexer( QsciLexerYAML() )

